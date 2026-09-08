"""Model factory for BATeam.

Local development: direct HTTP to Ollama (no LiteLlm dependency).
Production: ADK-native model strings resolved by the registry (Vertex AI / Gemini / Anthropic).

The factory is driven by the `BATEAM_MODEL_OVERRIDE` env var, with a per-agent fallback.
At deploy time, set e.g. `BATEAM_MODEL_OVERRIDE=gemini-2.5-pro` to force every agent
onto a managed model.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
from typing import Any, AsyncGenerator

import httpx
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing_extensions import override

logger = logging.getLogger("bateam.models")

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_TIMEOUT_S = 600.0  # qwen2.5:72b cold-start can be slow


class OllamaLlm(BaseLlm):
    """ADK BaseLlm adapter for local Ollama via Ollama's native /api/chat endpoint.

    Recognised model strings: `ollama/<tag>` (e.g. `ollama/mistral-small3.2:24b`,
    `ollama/dr-ry/foundation-sec-8b-instruct-chat-GGUF`). The `ollama/` prefix
    is stripped before the request is sent to Ollama.

    Optional per-instance defaults — `num_ctx`, `num_predict`, `temperature`,
    `top_p`, `top_k` — map to Ollama's `options` block. ADK's per-call
    `GenerateContentConfig` overrides any value set here.

    `num_predict` reserves a hard output-token budget so a prompt that grows
    to fill `num_ctx` can never crowd generation down to zero tokens (the
    empty-completion failure mode on long-form deliverables).

    `think` controls Ollama's top-level thinking flag (NOT an `options` key).
    Reasoning models such as gemma4 emit their chain-of-thought in
    `message.thinking` and the answer in `message.content`. Counter-intuitively,
    these models need thinking ON to answer non-trivial prompts at all: with
    `think=False` gemma4 returns an empty completion for anything beyond a
    trivial ask. So we default to `None` (omit the flag; use the model's own
    default, which is thinking-on for gemma4) rather than forcing it off. The
    real failure mode — thinking eating the whole `num_predict` budget so
    `content` comes back empty — is handled by (a) reserving enough budget
    (num_ctx/num_predict in agent.yaml) and (b) the empty-completion guard in
    `_ollama_to_llm_response`. Set `think=False` only for a model you've
    confirmed answers without it.
    """

    model: str = "ollama/llama3.1:8b"
    num_ctx: int | None = None
    num_predict: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    think: bool | None = None

    @classmethod
    @override
    def supported_models(cls) -> list[str]:
        return [r"ollama/.*"]

    def _ollama_host(self) -> str:
        return os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")

    def _ollama_tag(self) -> str:
        return self.model.removeprefix("ollama/")

    def _instance_options(self) -> dict:
        opts: dict = {}
        if self.num_ctx is not None:
            opts["num_ctx"] = self.num_ctx
        if self.num_predict is not None:
            opts["num_predict"] = self.num_predict
        if self.temperature is not None:
            opts["temperature"] = self.temperature
        if self.top_p is not None:
            opts["top_p"] = self.top_p
        if self.top_k is not None:
            opts["top_k"] = self.top_k
        return opts

    def __repr__(self) -> str:
        return f'OllamaLlm(model="{self.model}", host="{self._ollama_host()}")'

    @override
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        messages = _to_ollama_messages(llm_request)
        tools = _to_ollama_tools(llm_request)

        payload: dict = {
            "model": self._ollama_tag(),
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        options = _to_ollama_options(llm_request, instance_defaults=self._instance_options())
        if options:
            payload["options"] = options
        if self.think is not None:
            payload["think"] = self.think

        url = f"{self._ollama_host()}/api/chat"
        logger.debug("Ollama request → %s model=%s msgs=%d tools=%d stream=%s think=%s",
                     url, payload["model"], len(messages), len(tools or []), stream, payload.get("think"))

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S) as client:
            if not stream:
                # A model that doesn't support the `think` flag 400s on it;
                # drop it and retry once so non-thinking models still work.
                for attempt in (1, 2):
                    resp = await client.post(url, json=payload)
                    if attempt == 1 and "think" in payload and _think_unsupported(resp):
                        payload.pop("think")
                        continue
                    break
                if resp.status_code >= 400:
                    _log_ollama_error(resp, payload)
                resp.raise_for_status()
                yield _ollama_to_llm_response(resp.json(), partial=False)
                return

            for attempt in (1, 2):
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code >= 400:
                        await resp.aread()
                        if attempt == 1 and "think" in payload and _think_unsupported(resp):
                            payload.pop("think")
                            continue
                        _log_ollama_error(resp, payload)
                        resp.raise_for_status()
                    accumulated_text = ""
                    accumulated_thinking = ""
                    accumulated_tool_calls: list[dict] = []
                    final_meta: dict = {}
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            logger.warning("Ollama returned non-JSON stream line: %r", line[:200])
                            continue

                        msg = chunk.get("message") or {}
                        delta_text = msg.get("content") or ""
                        if delta_text:
                            accumulated_text += delta_text
                            yield LlmResponse(
                                content=types.Content(
                                    role="model",
                                    parts=[types.Part.from_text(text=delta_text)],
                                ),
                                partial=True,
                            )

                        # Accumulate (but don't stream) reasoning so the
                        # empty-completion guard can fall back to it.
                        if delta_think := msg.get("thinking") or "":
                            accumulated_thinking += delta_think

                        if tcs := msg.get("tool_calls"):
                            accumulated_tool_calls.extend(tcs)

                        if chunk.get("done"):
                            final_meta = chunk
                            break

                    # Final aggregated response
                    merged = {
                        "message": {
                            "role": "assistant",
                            "content": accumulated_text,
                            "thinking": accumulated_thinking,
                            "tool_calls": accumulated_tool_calls,
                        },
                        "model": final_meta.get("model"),
                        "done_reason": final_meta.get("done_reason"),
                    }
                    yield _ollama_to_llm_response(merged, partial=False)
                    return


def _json_default(o: Any) -> Any:
    if isinstance(o, (datetime.date, datetime.datetime, datetime.time)):
        return o.isoformat()
    return str(o)


def _log_ollama_error(resp: httpx.Response, payload: dict) -> None:
    """Log the Ollama error body and a payload summary on 4xx/5xx.

    Without this, raise_for_status() discards the body that names the actual
    cause (Ollama returns `{"error": "..."}`). Summary at WARNING; full payload
    at DEBUG so it's available on demand without polluting normal logs.
    """
    try:
        body = resp.text
    except Exception as e:  # noqa: BLE001
        body = f"<unreadable: {e!r}>"

    msgs = payload.get("messages") or []
    summary = []
    for i, m in enumerate(msgs):
        role = m.get("role")
        content = m.get("content")
        clen = len(content) if isinstance(content, str) else -1
        tcs = len(m.get("tool_calls") or [])
        name = m.get("name")
        summary.append(
            f"[{i}] role={role} content_len={clen} tool_calls={tcs}"
            + (f" name={name}" if name else "")
        )

    logger.warning(
        "Ollama %d on %s — body=%r; model=%s msgs=%d tools=%d; messages: %s",
        resp.status_code,
        resp.request.url if resp.request else "?",
        body[:2000],
        payload.get("model"),
        len(msgs),
        len(payload.get("tools") or []),
        " | ".join(summary),
    )
    logger.debug("Ollama failing payload: %s",
                 json.dumps(payload, default=_json_default)[:8000])


def _to_ollama_messages(llm_request: LlmRequest) -> list[dict]:
    """Translate ADK Content list + system_instruction into Ollama chat messages."""
    messages: list[dict] = []

    sys = (llm_request.config.system_instruction
           if llm_request.config and llm_request.config.system_instruction
           else None)
    if sys:
        # ADK's system_instruction can be string | Content | list[Content]
        if isinstance(sys, str):
            messages.append({"role": "system", "content": sys})
        elif isinstance(sys, types.Content):
            messages.append({"role": "system", "content": _content_to_text(sys)})
        elif isinstance(sys, list):
            for c in sys:
                messages.append({"role": "system", "content": _content_to_text(c)})

    for content in llm_request.contents or []:
        ollama_role = _adk_role_to_ollama(content.role)
        text = _content_to_text(content)
        tool_calls = _extract_tool_calls(content)
        tool_responses = _extract_tool_responses(content)

        if tool_responses:
            for tr in tool_responses:
                messages.append({
                    "role": "tool",
                    "content": tr["response"] if isinstance(tr["response"], str) else json.dumps(tr["response"], default=_json_default),
                    "name": tr["name"],
                })
            continue

        msg: dict = {"role": ollama_role}
        if text:
            msg["content"] = text
        else:
            msg["content"] = ""
        if tool_calls:
            msg["tool_calls"] = tool_calls
        messages.append(msg)

    return messages


def _adk_role_to_ollama(role: str | None) -> str:
    if role == "model":
        return "assistant"
    if role == "user":
        return "user"
    return role or "user"


def _content_to_text(content: types.Content) -> str:
    parts: list[str] = []
    for p in content.parts or []:
        if p.text:
            parts.append(p.text)
    return "".join(parts)


def _extract_tool_calls(content: types.Content) -> list[dict]:
    out: list[dict] = []
    for p in content.parts or []:
        if fc := p.function_call:
            out.append({
                "function": {
                    "name": fc.name,
                    "arguments": fc.args or {},
                }
            })
    return out


def _extract_tool_responses(content: types.Content) -> list[dict]:
    out: list[dict] = []
    for p in content.parts or []:
        if fr := p.function_response:
            out.append({"name": fr.name, "response": fr.response})
    return out


def _to_ollama_tools(llm_request: LlmRequest) -> list[dict]:
    tools_out: list[dict] = []
    if not llm_request.config or not llm_request.config.tools:
        return tools_out
    for tool_item in llm_request.config.tools:
        if isinstance(tool_item, types.Tool) and tool_item.function_declarations:
            for fn in tool_item.function_declarations:
                tools_out.append({
                    "type": "function",
                    "function": {
                        "name": fn.name,
                        "description": fn.description or "",
                        "parameters": _schema_to_dict(fn.parameters) if fn.parameters else {"type": "object", "properties": {}},
                    },
                })
    return tools_out


def _schema_to_dict(schema) -> dict:
    """genai.types.Schema → JSON-Schema dict for Ollama."""
    try:
        return json.loads(schema.model_dump_json(exclude_none=True))
    except AttributeError:
        return dict(schema) if schema else {}


def _to_ollama_options(
    llm_request: LlmRequest,
    *,
    instance_defaults: dict | None = None,
) -> dict:
    """Map ADK GenerateContentConfig + per-instance defaults to Ollama options.

    Per-call config (from ADK) wins over per-instance defaults (set on the
    OllamaLlm subclass); per-instance defaults win over Ollama's built-in
    defaults.
    """
    opts: dict = dict(instance_defaults or {})
    cfg = llm_request.config
    if not cfg:
        return opts
    if cfg.temperature is not None:
        opts["temperature"] = cfg.temperature
    if cfg.top_p is not None:
        opts["top_p"] = cfg.top_p
    if cfg.top_k is not None:
        opts["top_k"] = cfg.top_k
    if cfg.max_output_tokens is not None:
        opts["num_predict"] = cfg.max_output_tokens
    if cfg.stop_sequences:
        opts["stop"] = list(cfg.stop_sequences)
    return opts


def _think_unsupported(resp: httpx.Response) -> bool:
    """True if Ollama rejected the request because the model can't think.

    Ollama returns 400 with a body like ``{"error":"... does not support
    thinking"}`` when the `think` flag is sent to a non-reasoning model.
    """
    if resp.status_code != 400:
        return False
    try:
        return "think" in (resp.text or "").lower()
    except Exception:  # noqa: BLE001 — body may already be consumed
        return False


def _ollama_to_llm_response(payload: dict, *, partial: bool) -> LlmResponse:
    msg = payload.get("message") or {}
    parts: list[types.Part] = []

    text = msg.get("content")
    tool_calls = msg.get("tool_calls") or []
    if not text and not tool_calls:
        # Empty-completion guard. A reasoning model can return no `content`
        # (e.g. it spent the whole num_predict budget on `thinking`, so
        # done_reason == "length"). Never emit a silently blank turn: fall
        # back to the reasoning text so the generation isn't wholly lost, and
        # log loudly so the budget shortfall is visible.
        thinking = msg.get("thinking")
        if thinking:
            logger.warning(
                "Ollama returned empty content with %d chars of thinking "
                "(done_reason=%s). Surfacing reasoning as the answer — raise "
                "num_predict/num_ctx so the model has room to finish thinking "
                "AND write the answer.",
                len(thinking), payload.get("done_reason"),
            )
            text = thinking
        else:
            logger.warning(
                "Ollama returned an empty completion (no content, no thinking, "
                "no tool calls; done_reason=%s).", payload.get("done_reason"),
            )

    if text:
        parts.append(types.Part.from_text(text=text))

    for tc in tool_calls:
        fn = tc.get("function") or {}
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_raw": args}
        parts.append(types.Part(function_call=types.FunctionCall(
            name=fn.get("name", ""),
            args=args,
        )))

    if not parts:
        parts.append(types.Part.from_text(text=""))

    return LlmResponse(
        content=types.Content(role="model", parts=parts),
        partial=partial,
        model_version=payload.get("model"),
    )


# ---------------------------------------------------------------------------
# Factory: env-var driven model selection
# ---------------------------------------------------------------------------

def resolve_model(
    default_local: str,
    default_prod: str | None = None,
    *,
    num_ctx: int | None = None,
    num_predict: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    think: bool | None = None,
):
    """Return a model handle for ADK LlmAgent based on env vars.

    Resolution order:
      1. `BATEAM_MODEL_OVERRIDE` — global override (e.g. `gemini-2.5-pro`).
      2. `BATEAM_ENV` == `prod` and `default_prod` set → return `default_prod` (string).
      3. Otherwise → return an `OllamaLlm` instance for `default_local`.

    `default_local` should be an Ollama tag (e.g. `mistral-small3.2:24b`) or a
    namespaced tag (e.g. `dr-ry/foundation-sec-8b-instruct-chat-GGUF`); the
    `ollama/` prefix is added automatically when missing.
    `default_prod` should be an ADK-native model string like `gemini-2.5-pro`.

    Sampling kwargs (`num_ctx`, `num_predict`, `temperature`, `top_p`, `top_k`,
    `think`) only apply to the Ollama path — they are ignored when a managed
    model string is returned (those are configured via ADK's
    GenerateContentConfig at call time). `think` is unset here (None) so the
    OllamaLlm default applies (omit the flag; use the model's own default,
    which is thinking-on for gemma4) unless an agent overrides it.
    """
    ollama_kwargs = {
        k: v for k, v in (
            ("num_ctx", num_ctx),
            ("num_predict", num_predict),
            ("temperature", temperature),
            ("top_p", top_p),
            ("top_k", top_k),
            ("think", think),
        ) if v is not None
    }

    override = os.getenv("BATEAM_MODEL_OVERRIDE")
    if override:
        if override.startswith("ollama/"):
            return OllamaLlm(model=override, **ollama_kwargs)
        return override

    if os.getenv("BATEAM_ENV", "").lower() == "prod" and default_prod:
        return default_prod

    tag = default_local if default_local.startswith("ollama/") else f"ollama/{default_local}"
    return OllamaLlm(model=tag, **ollama_kwargs)
