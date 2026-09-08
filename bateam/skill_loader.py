"""Helpers for loading agentskills.io-spec SKILL.md directories into ADK Skill objects.

ADK ships with `google.adk.skills.load_skill_from_dir` which already follows the spec —
this module is a thin wrapper that:

  * Loads every skill subdirectory under a given `skills/` parent.
  * Skips skills that don't yet have a `SKILL.md` (defensive).
  * Surfaces a clear error if a skill's frontmatter `name` doesn't match its directory.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Iterable

from google.adk.skills import load_skill_from_dir
from google.adk.skills.models import Skill

logger = logging.getLogger("bateam.skill_loader")


def load_skills_from_agent(agent_dir: pathlib.Path | str) -> list[Skill]:
    """Load every skill under `<agent_dir>/skills/`.

    Returns the loaded `Skill` objects in deterministic (alphabetical) order so that
    agent prompts stay stable across runs.
    """
    agent_dir = pathlib.Path(agent_dir).resolve()
    skills_root = agent_dir / "skills"
    if not skills_root.is_dir():
        logger.warning("No skills/ directory under %s", agent_dir)
        return []

    skills: list[Skill] = []
    for child in sorted(skills_root.iterdir()):
        if not child.is_dir():
            continue
        skill_md = child / "SKILL.md"
        if not skill_md.exists():
            logger.warning("Skipping %s: no SKILL.md found", child)
            continue
        try:
            skills.append(load_skill_from_dir(child))
        except ValueError as e:
            raise ValueError(
                f"Failed to load skill at {child}: {e}. "
                f"Frontmatter `name` must match the directory name exactly."
            ) from e

    return skills


def skill_summary(skills: Iterable[Skill]) -> str:
    """Build a one-line-per-skill summary suitable for an agent's `instruction` block.

    The full SKILL.md body is loaded by ADK on demand (progressive disclosure);
    this summary just nudges the LLM toward the right skill.
    """
    lines: list[str] = []
    for s in skills:
        lines.append(f"- `{s.frontmatter.name}`: {s.frontmatter.description.strip()}")
    return "\n".join(lines)
