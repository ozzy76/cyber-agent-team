"""``before_model_callback`` that keeps a long session from saturating the
context window.

The failure this guards against (session bea050f4): a CTI report session
loaded two skills, ran four ``web_search`` calls, and produced two long
drafts. By the time the user asked for the 5–12 page Threat Landscape
Briefing, the prompt had grown to ~the full ``num_ctx`` and the model
returned an empty completion — no tokens left to generate.

Raising ``num_ctx`` and reserving ``num_predict`` (see agent.yaml) fixes the
acute case, but a busy session still creeps toward the ceiling. The biggest,
safest thing to reclaim is **stale search output**: once the model has read a
``web_search`` result and written it into a draft, the raw snippets rarely
need to sit in context for the rest of the session.

So: keep the most recent ``_KEEP_RECENT`` results of each bulky tool in full;
replace older ones with a compact stub that preserves the query (for
traceability) and tells the model to re-run the search if it needs the data
again. Loaded skill instructions and ordinary chat turns are left untouched —
they carry guidance the model still needs.

Design ref: ADK before_model_callback context-management pattern —
https://adk.dev/callbacks/design-patterns-and-best-practices/
"""

from __future__ import annotations

import logging

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types

logger = logging.getLogger("bateam.context")

# Tool responses that are bulky and safe to elide once superseded. These are
# retrieval results the model reasons over once, not standing guidance —
# unlike load_skill, whose instructions must persist for the active skill.
_BULKY_TOOLS = frozenset({"web_search"})

# How many of the most recent responses per bulky tool to keep in full.
_KEEP_RECENT = 1


def _response_query(resp) -> str | None:
    """Best-effort pull of the originating query from a function_response."""
    if isinstance(resp, dict):
        q = resp.get("query")
        if isinstance(q, str):
            return q
    return None


async def compact_history_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> None:
    """Elide stale bulky tool results from the outbound request.

    Observer-only: mutates ``llm_request.contents`` in place, returns ``None``,
    and swallows its own exceptions so a compaction bug can never break the
    agent loop.
    """
    try:
        # Locate every bulky-tool function_response part, in order.
        hits: list[tuple[types.Content, int, str, object]] = []
        for content in llm_request.contents or []:
            for i, part in enumerate(content.parts or []):
                fr = getattr(part, "function_response", None)
                if fr is None:
                    continue
                name = getattr(fr, "name", None)
                if name in _BULKY_TOOLS:
                    hits.append((content, i, name, fr))

        # Group by tool and keep the last _KEEP_RECENT of each in full.
        by_tool: dict[str, list[int]] = {}
        for idx, (_, _, name, _fr) in enumerate(hits):
            by_tool.setdefault(name, []).append(idx)
        keep: set[int] = set()
        for name, idxs in by_tool.items():
            for idx in idxs[-_KEEP_RECENT:]:
                keep.add(idx)

        elided = 0
        for idx, (content, i, name, fr) in enumerate(hits):
            if idx in keep:
                continue
            query = _response_query(getattr(fr, "response", None))
            stub = {
                "elided": True,
                "note": (
                    f"{name} results from earlier in this session were removed "
                    "to conserve context. Re-run the tool if you need them again."
                ),
            }
            if query:
                stub["query"] = query
            content.parts[i] = types.Part(
                function_response=types.FunctionResponse(
                    id=getattr(fr, "id", None),
                    name=name,
                    response=stub,
                )
            )
            elided += 1

        if elided:
            logger.info("Compacted %d stale bulky tool result(s) from request.", elided)
    except Exception:
        # Defensive: never break the turn over a compaction failure.
        pass
    return None
