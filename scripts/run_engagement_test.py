"""One-shot engagement test driver.

Sends a single user prompt through the BATeam orchestrator and prints every
event (transfers, model calls, final answer) to stdout. Intended for sanity
checking the wiring against a live Ollama instance.

Usage:
    bistaff/bin/python scripts/run_engagement_test.py "<prompt>"
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Quiet ADK's experimental-feature noise.
os.environ.setdefault("PYTHONWARNINGS", "ignore")

import warnings  # noqa: E402
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from agents.project_mgr.agent import root_agent  # noqa: E402


async def run(prompt: str) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="bateam")
    user_id = "test-user"
    session = await runner.session_service.create_session(
        app_name="bateam", user_id=user_id
    )

    print(f"\n=== Engagement test ===")
    print(f"Prompt: {prompt}")
    print(f"Root agent: {root_agent.name}")
    print("=" * 70)

    new_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

    started = time.monotonic()
    event_n = 0
    final_text_parts: list[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=new_message,
    ):
        event_n += 1
        elapsed = time.monotonic() - started
        author = event.author or "?"
        kinds: list[str] = []
        text_parts: list[str] = []
        fc_parts: list[str] = []
        fr_parts: list[str] = []

        if event.content and event.content.parts:
            for p in event.content.parts:
                if p.text:
                    text_parts.append(p.text)
                if p.function_call:
                    fc_parts.append(f"{p.function_call.name}({dict(p.function_call.args or {})})")
                if p.function_response:
                    fr_parts.append(f"{p.function_response.name} -> {p.function_response.response}")

        if text_parts:
            kinds.append("text")
        if fc_parts:
            kinds.append("function_call")
        if fr_parts:
            kinds.append("function_response")
        if event.actions and event.actions.transfer_to_agent:
            kinds.append(f"transfer→{event.actions.transfer_to_agent}")

        print(f"[{elapsed:6.1f}s] #{event_n:02d} author={author:14s} kinds={','.join(kinds) or '(none)'}")
        for fc in fc_parts:
            print(f"           function_call: {fc}")
        for fr in fr_parts:
            print(f"           function_response: {fr[:300]}")
        for t in text_parts:
            print(f"           text: {t[:1500]}")
            if event.is_final_response():
                final_text_parts.append(t)

    print("=" * 70)
    print(f"Total events: {event_n}  Total time: {time.monotonic()-started:.1f}s")
    print()
    print("FINAL RESPONSE:")
    print("-" * 70)
    print("".join(final_text_parts) if final_text_parts else "(no final text emitted)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_engagement_test.py \"<prompt>\"", file=sys.stderr)
        sys.exit(2)
    asyncio.run(run(sys.argv[1]))
