# cyber-agent-team — BATeam Multi-Agent Team

Local-first build of the [BATeam](https://google.github.io/adk-docs/) multi-agent
system. Five agents — one orchestrator (`project_mgr`) plus four security
specialists — wired with [Google ADK](https://adk.dev/) and
[agentskills.io](https://agentskills.io/specification)-spec skills.

Local model serving is **direct HTTP to Ollama** (no LiteLlm). Production swaps
to Vertex AI / Gemini / Claude via a single env-var flip.

---

## Layout

```
cyber-agent-team/
├── bateam/                          # shared library
│   ├── models.py                    # OllamaLlm BaseLlm + resolve_model() factory
│   ├── agent_config.py              # yaml-as-source-of-truth loader + validator
│   ├── agent_builder.py             # build_specialist(...) used by every specialist
│   ├── skill_loader.py              # wraps google.adk.skills.load_skill_from_dir
│   ├── builtin_tools.py             # read_file / write_file / edit_file / execute_bash / run_skill_script
│   ├── artifact_tools.py            # list_artifacts / read_artifact (chat-upload decoders)
│   ├── artifact_notice.py           # auto-saves chat uploads; injects per-turn artifact awareness
│   └── audit.py                     # MCP audit-log callback (no credential echo)
├── agents/
│   ├── project_mgr/                 # root orchestrator (sub_agents = the other 4)
│   │   ├── INSTRUCTION.md           # lean routing core, always-loaded as instruction
│   │   ├── agent.py
│   │   ├── agent.yaml
│   │   └── skills/
│   │       └── engagement-orchestration/   # on-demand: phases, PMP, KPIs, prioritization
│   ├── architect/
│   ├── cti_mgr/
│   ├── grc_mgr/
│   └── ops_mgr/
├── scripts/
│   └── run_engagement_test.py       # one-shot CLI driver for an end-to-end test
└── bistaff/                         # local virtualenv (gitignored)
```

Each specialist agent directory follows ADK's expected layout:

```
agents/<agent_name>/
├── agent.py          # exports root_agent
├── agent.yaml        # descriptive metadata
├── __init__.py       # re-exports root_agent
└── skills/
    └── <skill-name>/
        ├── SKILL.md  # agentskills.io frontmatter + body
        ├── scripts/
        ├── references/
        └── assets/
```

The **orchestrator** is the only agent that splits its instruction across two
files: a small always-loaded `INSTRUCTION.md` for routing, and a
loaded-on-demand `engagement-orchestration` skill for the deep playbook
content. See [Why the orchestrator is split](#why-the-orchestrator-is-split)
below.

---

## Models per agent

Single-model local stack — all five agents share `gemma4:12b` (GGUF) via
direct Ollama HTTP. Production swaps each agent to a different managed
model via a single env-var flip; see [Switching between local and production](#switching-between-local-and-production).

| Agent          | Local (Ollama)        | num_ctx | temp  | Production              |
|----------------|-----------------------|---------|-------|-------------------------|
| `project_mgr`  | [`gemma4:12b`][gemma] | 8192    | 0.15  | `gemini-2.5-pro`        |
| `architect`    | [`gemma4:12b`][gemma] | 16384   | 0.15  | `gemini-2.5-pro`        |
| `grc_mgr`      | [`gemma4:12b`][gemma] | 16384   | 0.15  | `claude-sonnet-4-6`     |
| `cti_mgr`      | [`gemma4:12b`][gemma] | 8192    | 0.10  | `gemini-2.5-flash`      |
| `ops_mgr`      | [`gemma4:12b`][gemma] | 8192    | 0.10  | `gemini-2.5-flash`      |

[gemma]: https://ollama.com/library/gemma4

`project_mgr`, `cti_mgr`, and `ops_mgr` run at `num_ctx=8192` (smaller than
the other specialists) because their work is short-input/short-output:
orchestrator routing for `project_mgr`, tight SecOps/TI reasoning for
`cti_mgr` and `ops_mgr`. A smaller KV cache means faster prefill on every
turn. `architect` and `grc_mgr` keep `num_ctx=16384` for longer narrative
output (threat models, policies, risk assessments). `cti_mgr` and `ops_mgr`
use `temperature=0.1, top_p=0.9` for tighter, more deterministic security
output; everyone else uses `temperature=0.15`.

Because every agent shares the same image, transfers between agents never
trigger an Ollama model swap — `OLLAMA_MAX_LOADED_MODELS=1` is safe and
keeps the image resident across the entire conversation.

**Model history.** Earlier iterations used `mistral-small3.2:24b` across
the board, and before that the `cti_mgr` / `ops_mgr` pair targeted the
[Cisco Foundation-Sec-8B](https://huggingface.co/fdtn-ai/Foundation-Sec-8B)
community GGUF port. The Foundation-Sec port shipped without a chat
template that renders `.Tools`, so Ollama's `/api/chat` rejected every
`SkillToolset` request with `400: does not support tools`. Mistral worked
fine but the 24B footprint at `num_ctx=16384` was tight on a 24 GB Apple
Silicon machine. `gemma4:12b` was chosen for a smaller resident footprint
while retaining tool-call quality across all five agents. The MLX build
(`gemma4:12b-mlx`) has a known tool-parser bug; the GGUF build does not.

### Hardware constraints (24 GB M4)

- `gemma4:12b` runtime footprint at `num_ctx=16384` ≈ **~8–9 GB RAM**;
  at `num_ctx=8192` ≈ **~7 GB RAM**.
- All five agents share the image, so only one model needs to stay
  resident → `OLLAMA_MAX_LOADED_MODELS=1` and no inter-agent model swaps.
- First load costs **~3–5 s**. `OLLAMA_KEEP_ALIVE=20m` prevents reloads
  inside the same conversation. Both env vars are set in
  [.env.example](.env.example).

### Switching between local and production

Driven by env vars in [.env.example](.env.example):

- `BATEAM_ENV=local` (default) → Ollama
- `BATEAM_ENV=prod` → production model strings (resolved by ADK's registry)
- `BATEAM_MODEL_OVERRIDE=<model>` → override for every agent

See [bateam/models.py:371](bateam/models.py#L371) (`resolve_model`).

---

## Quick start

### 1. Prerequisites

- Python ≥ 3.11
- [Ollama](https://ollama.com/download) installed and running
- ~15 GB free disk space for the model image

### 2. Clone and install

```bash
git clone https://github.com/ozzy76/cyber-agent-team.git
cd cyber-agent-team
python3 -m venv bistaff
source bistaff/bin/activate
pip install -e .
```

`pip install -e .` pulls in `google-adk`, which provides the `adk` command
used below (`adk web`).

### 3. Pull Ollama models

```bash
ollama pull gemma4:12b                                        # ~7 GB — all 5 agents
```

Use the GGUF build (the default tag above), not `gemma4:12b-mlx` — the MLX
build has a tool-parser bug that breaks `SkillToolset` calls. See
[Model history](#models-per-agent).

### 4. Configure

```bash
cp .env.example .env
# Defaults work for local Ollama at http://localhost:11434.
# Edit if Ollama runs elsewhere or you want a different keep-alive.
```

### 5. Start an interactive session

The fastest way to talk to the team is ADK's web UI:

```bash
adk web agents
```

Open <http://localhost:8000> and pick an agent from the dropdown:

- **`project_mgr`** — main entry point. Routes to specialists automatically.
- Any specialist (e.g. `grc_mgr`, `architect`) — bypass orchestration to talk
  to one agent directly. Useful for debugging or specialist-only work.

The orchestrator delegates via ADK's auto-injected `transfer_to_agent` tool;
the web UI shows transfers, function calls, and skill loads inline.

### 6. One-shot CLI test

For a non-interactive end-to-end run with full event tracing:

```bash
bistaff/bin/python scripts/run_engagement_test.py \
  "We're a healthcare company, we are not encrypting data at rest. what do we need to meet hipaa compliance?"
```

Prints every transfer, function call, function response, and the final
synthesized answer with elapsed timestamps.

### 7. Things to try

Once `adk web agents` is running, start with `project_mgr` and give it a
request that spans more than one specialist — that's the fastest way to see
`transfer_to_agent` and multi-agent synthesis in action:

> We're a healthcare startup, not encrypting data at rest, and a VC wants a
> security due-diligence summary before their Series A. Where do we stand?

Or talk to a specialist directly (pick it from the `adk web` dropdown) to see
a single skill without orchestration overhead:

| Agent | Try asking… |
|-------|--------------|
| `architect` | "Threat-model a public-facing API that handles PII for a B2B SaaS product." |
| `cti_mgr` | "What passive OSINT would you collect on a company's external attack surface before an engagement?" |
| `grc_mgr` | "Walk me through a SOC 2 Type II gap assessment for an early-stage startup." |
| `ops_mgr` | "We just found a critical CVE in a public-facing service — walk me through triage and response." |

Watch the `adk web` UI's event log while you do this — it shows each skill
load, tool call, and (for `project_mgr`) each `transfer_to_agent` hop, which
is the easiest way to build intuition for how progressive disclosure and
routing actually work before reading the sections below.

---

## How skills are wired (progressive disclosure)

ADK's native `SkillToolset` (≥ 1.31) understands the agentskills.io spec
directly. Each agent calls [bateam/skill_loader.py:load_skills_from_agent](bateam/skill_loader.py#L23),
which walks `agents/<name>/skills/` and yields `Skill` objects via
`google.adk.skills.load_skill_from_dir`.

Loading is three-tier:

| Tier | Content                          | Loaded when                               |
|------|----------------------------------|-------------------------------------------|
| L1   | Frontmatter (name, description)  | At startup, surfaced in agent instruction |
| L2   | SKILL.md body                    | When the LLM picks the skill              |
| L3   | `references/` `assets/` `scripts/` | On demand, by reference inside L2       |

Source-of-truth references:
- [adk.dev/skills](https://adk.dev/skills/)
- [agentskills.io/specification](https://agentskills.io/specification)

---

## Why the orchestrator is split

`project_mgr`'s instruction was a 33 KB SKILL.md covering routing rules
*and* the full engagement-orchestration playbook (vCISO/vCIO/VC due-dil
phases, PMP-aligned process, three-tier engagement analysis, KPIs,
prioritization models). At ~8K tokens of every-turn prefill, the
orchestrator's first decision (which specialist to delegate to) was
unusably slow.

Current split:

- **[INSTRUCTION.md](agents/project_mgr/INSTRUCTION.md)** (4.2 KB) — always
  loaded. Roster, task→agent routing table, escalation rules, synthesis
  rules, and a one-line directive on when to load the playbook skill.
- **[skills/engagement-orchestration/SKILL.md](agents/project_mgr/skills/engagement-orchestration/SKILL.md)**
  (22.5 KB) — loaded on demand via `SkillToolset`. The orchestrator pulls it
  in only when a request requires multi-phase engagement design, governance
  detail, KPI computation, or executive reporting.

After the split, first-hop latency dropped ~64% on the same HIPAA prompt
(measured originally on `mistral-small3.2:24b`: 165 s → 60 s; the
proportional gain holds on `gemma4:12b` though absolute numbers are
smaller).

ADK's `LlmAgent` accepts both `tools=[SkillToolset(...)]` and
`sub_agents=[...]` together — they're orthogonal. See
[agents/project_mgr/agent.py](agents/project_mgr/agent.py).

---

## Agent-to-agent

`project_mgr` is constructed with `sub_agents=[…]` so ADK auto-registers a
`transfer_to_agent` tool. The orchestrator's LLM decides which specialist
gets the request based on each sub-agent's `description` field. See
[agents/project_mgr/agent.py:119](agents/project_mgr/agent.py#L119).

A specialist that gets a request outside its lane sends control back up — its
role instruction tells it to hand off to `project_mgr`.

---

## Capabilities (skills by agent)

Skills are agentskills.io-spec progressive-disclosure units: frontmatter
loads at startup, body loads when the agent picks the skill, references
and scripts load on demand. Scripts now actually execute (via
`SkillToolset`'s `UnsafeLocalCodeExecutor` + `run_skill_script`), so a
skill can ship deterministic ETL alongside LLM reasoning.

| Agent | Skills |
|-------|--------|
| `project_mgr`   | `engagement-orchestration` (phases, PMP governance, KPIs, three-tier engagement analysis) |
| `architect`     | `arch-analysis`, `secure-design`, `security-requirements`, `threat-modeling` |
| `cti_mgr`       | `adversary-tracking`, `cve-prioritization`, `intel-reporting`, `osint-collection`, `threat-analysis` |
| `grc_mgr`       | `compliance-monitoring`, `policy-development`, `risk-assessment`, `scf-intelligence`, `thirdparty-audit` |
| `ops_mgr`       | `incident-response`, `security-monitoring`, `soc-operations`, `vulnerability-management` |

Notable script-backed skills:

- **`scf-intelligence`** (`grc_mgr`) — loads the full SCF catalog
  (~1,468 controls, ~108K framework mappings) into local SQLite. Answers
  framework-crosswalk questions ("which SCF controls satisfy PCI DSS 4.0.1
  §1.1?") and runs gap analysis against client control inventories
  (Cynomi questionnaire CSV, framework-status CSV/XLSX). All data stays
  on-device.
- **`cve-prioritization`** (`cti_mgr`) — takes a vulnerability scan
  (CSV/JSON) or a free-text CVE list, enriches each CVE against
  EPSS (FIRST.org), maps to ICD-203 Words-of-Estimative-Probability
  bands ("almost certain" → "almost no chance"), and combines with CVSS
  to assign action tiers P0–P4. Output is a board-readable Markdown
  report.
- **`engagement-orchestration`** (`project_mgr`) — the orchestrator's
  on-demand playbook for vCISO/vCIO/VC due-diligence engagements.

### Workspace tools (built-in, every agent)

Every agent has `read_file`, `write_file`, `edit_file`, `list_artifacts`,
`read_artifact`, `execute_bash`, and `run_skill_script` available without
having to load a skill. `read_artifact` decodes `.docx`/`.pdf`/`.xlsx`
uploads from the chat UI to plain text. Retrieved bytes from uploads or
MCP tools are treated as untrusted input — they cannot trigger destructive
actions or additional tool calls without explicit user confirmation.

### Web search (research tool, feature-flagged)

Research-driven skills (e.g. `osint-collection`) depend on live web search. Enable it with
`BATEAM_WEB_SEARCH=1`; the tool is registered only when the active provider's
credentials are also present (otherwise it logs a warning and registers
nothing — so the model is never offered a tool that always errors, and skills
fall back to a no-search path instead of stalling). Default provider is
**Gemini grounding with Google Search** (`BATEAM_SEARCH_PROVIDER=gemini_grounding`,
`GEMINI_API_KEY`) — Google's supported web-search path for new customers now
that the Custom Search JSON API is closed to new customers (2027-01-01 shutdown;
kept as the legacy `google_pse` provider for existing Custom Search projects).
The module is provider-pluggable — Tavily/Brave/SearXNG are a `_search_<provider>`
function plus an env flip away. Search results are treated as untrusted input.
See [bateam/web_tools.py](bateam/web_tools.py).

### Agent config is yaml-driven

Every agent's `agent.yaml` is the **single source of truth** for name,
description, model tag, sampling, declared skills, and sub-agents.
[bateam/agent_config.py](bateam/agent_config.py) loads and validates the
yaml at startup; [bateam/agent_builder.py](bateam/agent_builder.py)
consumes it. Specialist `agent.py` files are ~5-line wrappers around
`build_specialist(agent_dir=..., role_instruction=ROLE)`. To change a
model tag fleet-wide, edit five yaml files, not five Python files.

---

## Troubleshooting

### Connection refused / `httpx.ConnectError` on first request
Ollama isn't running. Start it:
```bash
ollama serve
```
Or, on macOS, launch the Ollama app once and it will run as a background
service.

### `model not found` from Ollama
Pull the missing tag explicitly:
```bash
ollama list                                   # see what's installed
ollama pull gemma4:12b
```

### Very slow first response after switching agents
The `gemma4:12b` image cold-loads in ~3–5 s and at 24 GB RAM only one
model needs to stay resident (`OLLAMA_MAX_LOADED_MODELS=1`). Since every
agent uses the same image, transfers between agents do not trigger
reloads. Subsequent turns against the warm model are fast.

If the slowness persists *within* the same agent, check that
`OLLAMA_KEEP_ALIVE` is set in `.env` (default `20m`). Without it Ollama's
default 5-minute timeout will evict between turns.

### Out-of-memory kills mid-conversation
`gemma4:12b` at `num_ctx=16384` uses ~8–9 GB; at `num_ctx=8192` ~7 GB.
On a 24 GB machine there's normally plenty of headroom, but if something
else on the host spikes (a browser, Docker), close memory hogs or
temporarily drop a specialist's `num_ctx` to 8192 in its `agent.yaml`.

### Ollama 400: `... does not support tools`
Ollama refuses any `/api/chat` payload with a `tools` array if the target
model's chat template doesn't declare `.Tools`. Every BATeam agent
attaches `SkillToolset` function declarations, so any model swap must
preserve tool-template support. The community Foundation-Sec GGUF port
(`dr-ry/foundation-sec-8b-instruct-chat-GGUF`) hits this; the
`gemma4:12b-mlx` build hits a related tool-parser bug. Stick with the
default `gemma4:12b` (GGUF). If you need a different model, either build
a local Modelfile with a tool-aware `TEMPLATE` block or point that agent
at a tool-capable image.

### `adk web` can't find an agent
The `agents` argument to `adk web` is a directory path. Run from the repo
root and pass the directory name:
```bash
cd /path/to/cyber-agent-team
adk web agents                              # loads all 5 agents
adk web agents --agent project_mgr          # entry point only
```
Each agent dir name must be a valid Python identifier (underscores, not
hyphens). Skill subdirectories may use hyphens.

### `ModuleNotFoundError: No module named 'agents'` from `adk web`
ADK's loader puts the *agents directory* on `sys.path` (not its parent), then
imports each subdir as a top-level module. So inside the agent code:
- `agents/<name>/__init__.py` must use a relative import: `from .agent import root_agent`.
- Cross-agent imports in `project_mgr/agent.py` must use sibling-package style:
  `from architect.agent import root_agent as architect_agent` — **not**
  `from agents.architect.agent import ...`.

If you see this error after pulling, also clear stale bytecode:
```bash
find agents -name __pycache__ -type d -exec rm -rf {} +
```

### `TypeError: Object of type date is not JSON serializable`
A SKILL.md frontmatter field like `updated: 2026-04-30` is parsed by PyYAML
as a `datetime.date`, which the local Ollama adapter then has to serialize
into a tool-result JSON payload. The adapter handles `date` / `datetime` /
`time` via `_json_default` in [bateam/models.py](bateam/models.py); if you
add a new YAML scalar type (e.g. `Decimal`) and see this error, extend that
helper rather than quoting the field.

### Skill load fails with "frontmatter `name` must match the directory name"
The agentskills.io spec requires `name:` in `SKILL.md` frontmatter to match
the parent directory. If you rename a skill, rename both.

### Cross-skill content bleeding into responses
A skill's response references tools or sections from a different skill. This
is a known issue tracked in [Roadmap](#roadmap) — the current mitigation is
to keep skill descriptions tightly scoped to a single intent.

---

## Production scale-up (later)

Key prod-time deltas from this local-first build:

- Cloud Run hosts `project_mgr` (stateless), inference moves to Vertex AI Model
  Garden — no Ollama in prod.
- Session state externalized to Firestore (custom ADK session service).
- Active offensive-security tooling (e.g. an authenticated scanner/exploitation
  MCP) with human-in-the-loop approval gates — **not wired in this build**
  (intentional MVP scope).

---

## Roadmap

The local stack is functional end-to-end. The next set of improvements, in
roughly the order they should be tackled:

### 1. Latency — phase 2
The orchestrator split (above) cut first-hop latency from 165 s to 60 s.
The remaining bottleneck is now **specialist synthesis time** (~177 s for
the HIPAA prompt's `grc_mgr` answer). Likely levers:
- Slim individual specialist SKILL.md bodies the same way (lean L1
  description, deep content in L3 references).
- Stream tokens to the UI so perceived latency tracks first-token, not
  final-token.
- Investigate Ollama prompt-cache reuse across orchestrator → specialist →
  orchestrator round trips.

### 2. Cross-skill leakage in `grc_mgr`
The HIPAA test produced a response referencing `get_scc_compliance_posture`
(a GCP-specific tool) and `track_remediation_status` — both come from a
different skill than the one the LLM said it was loading. Mitigations:
- Narrow each skill's `description` so the L1 metadata doesn't sound
  generic ("compliance work" → "compliance gap mapping for SOC2/HIPAA/PCI").
- Post-load, narrow the prompt context to only the loaded skill's body
  rather than keeping the full skill index visible.
- Audit all `grc_mgr` skills for tool-name collisions and rename where
  needed.

### 3. Production parity
The `BATEAM_ENV=prod` path exists in `resolve_model` but has not been run
end-to-end. Before deploy:
- Wire ADK's Vertex AI / Gemini paths and verify each agent's
  per-environment model string resolves correctly.
- Smoke-test that `transfer_to_agent` and `SkillToolset` behave the same
  under managed models as they do under Ollama.
- Confirm Anthropic Claude routes work for `grc_mgr` specifically (its prod
  model is `claude-sonnet-4-6`; the others are Gemini).

### 4. Foundation-Sec sanity check (deprioritized)
**Status:** deferred. `cti_mgr` and `ops_mgr` now run on `gemma4:12b`
alongside the rest of the team, which handles tool calling cleanly. The
original motivation (specialized SecOps reasoning from Cisco's
[Foundation-Sec-8B](https://huggingface.co/fdtn-ai/Foundation-Sec-8B))
still has merit if/when a tool-aware Modelfile lands or in-house
instruction-tuning is funded. The community GGUF port
(`dr-ry/foundation-sec-8b-instruct-chat-GGUF`) is blocked on a missing
`.Tools` block in its chat template — see
[Ollama 400: `... does not support tools`](#ollama-400-does-not-support-tools).

### ~~5. Code execution for skill scripts~~ (shipped)
Skill scripts now execute via ADK's `SkillToolset` with
`UnsafeLocalCodeExecutor`. The LLM invokes them through `run_skill_script`
(`skill_name`, `file_path="scripts/<file>.py"`, `positional_args`/`args`).
Used today by `scf-intelligence` (SCF catalog ingest, gap analysis) and
`cve-prioritization` (EPSS enrichment + ICD-203 banding).

### 6. Offensive-security MCP integration
Intentionally deferred. Adds active scanning/exploitation tooling under
human-in-the-loop approval gates — higher blast radius than the read-only
and passive-collection tools wired today, so it needs its own review before
landing.

### 7. Firestore session service
Required for prod multi-instance deployment. Local dev uses
`InMemoryRunner`/`InMemorySessionService` — fine for one-shot tests, not
for distributed Cloud Run.

### 8. Additional MCP integrations
No MCP servers are wired in this build (`build_specialist` accepts
`mcp_toolsets` as an extensibility point). Likely first candidates: a
vulnerability-scanner MCP for `ops_mgr` / `cve-prioritization` (so the
agent can pull scans directly instead of requiring upload), and a Slack
MCP for incident-response handoff.
