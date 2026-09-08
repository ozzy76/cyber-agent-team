"""Single source of truth for an agent's identity, model, sampling, and skills.

The runtime entry point is still `<agent_dir>/agent.py`, but it now reads
everything that isn't prompt prose from `<agent_dir>/agent.yaml`. ROLE text
stays in Python because it's prompt content, not configuration.

Before this module existed, `models.local` and `skills:` in agent.yaml were
both dead config — nothing read them. Updates to the model tag had to be made
in 8 separate `agent.py` files, and a half-deleted skill dir could persist
silently because no one validated yaml against disk. Both classes of foot-gun
are closed here.
"""

from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass
from typing import Any

import yaml

logger = logging.getLogger("bateam.agent_config")

_KNOWN_SAMPLING_KEYS = frozenset(
    {"num_ctx", "num_predict", "temperature", "top_p", "top_k", "think"}
)


@dataclass(frozen=True)
class AgentConfig:
    """Frozen view of an agent.yaml.

    `sampling` is a plain dict so adding a new Ollama option (e.g. `min_p`,
    `repeat_penalty`) only requires touching `_KNOWN_SAMPLING_KEYS` and the
    yaml — no consumer change.
    """

    name: str
    role: str
    description: str
    domain: str | None
    local_model: str
    prod_model: str | None
    sampling: dict[str, Any]
    declared_skills: tuple[str, ...]
    sub_agents: tuple[str, ...]
    operating_mode: str | None
    rag_pattern: str | None
    instruction_source: str | None
    raw: dict[str, Any]


def load_agent_config(agent_dir: pathlib.Path | str) -> AgentConfig:
    """Parse `<agent_dir>/agent.yaml` into an `AgentConfig`.

    Raises:
        FileNotFoundError: agent.yaml is missing.
        ValueError: required field missing or `name` is not a Python identifier.
    """
    agent_dir = pathlib.Path(agent_dir).resolve()
    yaml_path = agent_dir / "agent.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(
            f"Missing agent.yaml at {yaml_path}. Every agent under agents/<name>/ "
            "must declare its identity in agent.yaml."
        )

    with yaml_path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    name = raw.get("name")
    if not isinstance(name, str) or not name.isidentifier():
        raise ValueError(
            f"{yaml_path}: 'name' must be a Python identifier (no hyphens) — got {name!r}."
        )

    description = (raw.get("description") or "").strip()
    if not description:
        raise ValueError(
            f"{yaml_path}: 'description' is required — it drives ADK transfer routing."
        )

    models = raw.get("models") or {}
    local = models.get("local")
    if not isinstance(local, str) or not local.strip():
        raise ValueError(
            f"{yaml_path}: 'models.local' is required (e.g. 'ollama/gemma4:12b')."
        )

    sampling: dict[str, Any] = {}
    for k, v in (raw.get("sampling") or {}).items():
        if k in _KNOWN_SAMPLING_KEYS:
            sampling[k] = v
        else:
            logger.warning("%s: unknown sampling key %r ignored.", yaml_path, k)

    cfg = AgentConfig(
        name=name,
        role=(raw.get("role") or "").strip(),
        description=description,
        domain=raw.get("domain"),
        local_model=local.removeprefix("ollama/"),
        prod_model=models.get("prod"),
        sampling=sampling,
        declared_skills=tuple(raw.get("skills") or ()),
        sub_agents=tuple(raw.get("sub_agents") or ()),
        operating_mode=raw.get("operating_mode") or raw.get("default_mode"),
        rag_pattern=raw.get("rag_pattern"),
        instruction_source=raw.get("instruction_source"),
        raw=raw,
    )

    _warn_skill_drift(agent_dir, cfg)
    return cfg


def _warn_skill_drift(agent_dir: pathlib.Path, cfg: AgentConfig) -> None:
    """Warn if declared skills don't match the skills/ directory contents.

    Drift is non-fatal — the skill loader iterates the dir, not the yaml —
    but a divergence signals stale state in either direction. Caught the
    pricing-strategy empty-dir before; will catch the next one.
    """
    skills_root = agent_dir / "skills"
    if not skills_root.is_dir():
        if cfg.declared_skills:
            logger.warning(
                "%s declares skills %s but has no skills/ directory.",
                cfg.name, list(cfg.declared_skills),
            )
        return

    on_disk = {
        d.name for d in skills_root.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }
    declared = set(cfg.declared_skills)

    if missing := declared - on_disk:
        logger.warning(
            "%s declares skills not present (or missing SKILL.md): %s",
            cfg.name, sorted(missing),
        )
    if undeclared := on_disk - declared:
        logger.warning(
            "%s has skills on disk not declared in agent.yaml: %s",
            cfg.name, sorted(undeclared),
        )
