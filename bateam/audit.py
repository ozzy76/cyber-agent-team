"""Structured audit logging for every tool invocation on a BATeam agent.

Plugged in as an ADK ``after_tool_callback`` (see
https://adk.dev/callbacks/design-patterns-and-best-practices/ — Pattern #3:
"Logging and Monitoring"). One JSONL record per call, captured for any tool
the agent invokes — MCP, FunctionTool, SkillToolset, built-in bash.

Design constraints (from ADK callback docs):
  * Callbacks run synchronously on the agent loop → use ``logging.FileHandler``
    (buffered) instead of raw ``open().write()``.
  * Callbacks must never crash the agent → wrap the whole body in try/except.
  * The audit channel must not echo back into anything the LLM can see →
    dedicated logger with ``propagate=False``.

Default sink: ``$XDG_STATE_HOME/bateam/audit.jsonl`` (i.e.
``~/.local/state/bateam/audit.jsonl``). Override with ``BATEAM_AUDIT_LOG``.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import time
from typing import Any

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext

_DEFAULT_LOG = pathlib.Path("~/.local/state/bateam/audit.jsonl").expanduser()
_AUDIT_LOG_PATH = pathlib.Path(
    os.getenv("BATEAM_AUDIT_LOG", str(_DEFAULT_LOG))
).expanduser()

# Keys whose values must not be persisted in plaintext. Length-only redaction
# preserves the audit signal (something was passed) without leaking content or
# credentials. Matched case-insensitively.
_REDACT_KEYS = frozenset(
    {
        "content_base64",
        "content",
        "data",
        "raw",
        "access_token",
        "refresh_token",
        "id_token",
        "client_secret",
        "authorization",
        "api_key",
        "password",
    }
)
_MAX_VALUE_BYTES = 512

_logger = logging.getLogger("bateam.audit")


def _install_handler_once() -> None:
    if _logger.handlers:
        return
    _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(_AUDIT_LOG_PATH, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in _REDACT_KEYS:
                length = len(v) if hasattr(v, "__len__") else None
                out[k] = f"<redacted len={length}>"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    if isinstance(value, str) and len(value) > _MAX_VALUE_BYTES:
        return value[:_MAX_VALUE_BYTES] + f"...[truncated {len(value)} chars]"
    return value


def mcp_audit_callback(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> None:
    """ADK ``after_tool_callback`` — append one JSONL audit record per call.

    Returns ``None`` always: this is an observer, never a response mutator
    (Pattern #3, not Pattern #5). Any exception is swallowed so an audit
    failure never breaks the agent's tool loop.
    """
    try:
        _install_handler_once()
        record = {
            "ts": time.time(),
            "invocation_id": getattr(tool_context, "invocation_id", None),
            "agent": getattr(tool_context, "agent_name", None),
            "tool": getattr(tool, "name", type(tool).__name__),
            "args": _redact(args),
            "response": _redact(tool_response)
            if isinstance(tool_response, (dict, list))
            else _redact(str(tool_response)),
        }
        _logger.info(json.dumps(record, default=str, ensure_ascii=False))
    except Exception:
        pass
    return None
