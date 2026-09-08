---
name: engagement-orchestration
description: >
  Multi-phase engagement playbooks (vCISO/Fractional CISO, Virtual CIO, VC
  portfolio due-diligence), PMP-aligned governance (People/Process/Business
  Environment), three-tier engagement analysis (portfolio health, risk matrix,
  capacity planning), prioritization models (WSJF/RICE/ICE/MoSCoW), success
  metrics and KPIs, and the dispatch/handoff protocols for BATeam specialists.
  Load this skill when you need to plan or govern an engagement, sequence
  multi-agent workstreams across phases, run an engagement health or capacity
  review, prepare an executive/board report, or compute a portfolio-level
  prioritization. Routine task delegation does NOT require this skill — the
  always-loaded routing core covers single-step delegation.
compatibility: >
  ADK SkillToolset compatible. References EMV / Monte Carlo from
  references/risk-management-framework.md, prioritization model definitions
  from references/portfolio-prioritization-models.md, and KPI guidance from
  references/portfolio-kpis.md. Provides three Python scripts under scripts/
  for portfolio health, risk matrix, and resource capacity analysis.
metadata:
  author: "BATeam contributors"
  version: "1.0.0"
  domain: "project-management"
  pmp-domains: "people,process,business-environment"
  adk-role: "orchestrator-playbook"
allowed-tools: Read Write Edit Bash
---

# Engagement Orchestration Playbook

Use this when a request goes beyond single-step delegation — engagement design,
phase sequencing, multi-agent governance, executive reporting, KPI synthesis,
or portfolio analysis.

---

## Engagement Playbooks

### Service Line 1: vCISO / Fractional CISO Engagement

Full security program leadership for clients without in-house security executives.

**Phase 1 — Discovery (Days 1-14)**
Run in parallel to compress timeline:
- `architect (arch-analysis)` — map current state architecture; identify critical gaps
- `cti_mgr (osint-collection)` — surface exposed assets, credentials, third-party leaks
- `grc_mgr (compliance-monitoring)` — establish baseline compliance posture
- `ops_mgr (vulnerability-management)` — initial vulnerability scan and triage

PM deliverable: Integrated discovery summary combining all four outputs into a client-ready
executive brief. Classify findings by impact and urgency before presenting.

**Phase 2 — Risk & Compliance Assessment (Days 15-30)**
Sequential — discovery outputs feed this phase:
- `grc_mgr (risk-assessment)` — formal risk register from architecture + vuln findings
- `architect (threat-modeling)` — threat model informed by cti_mgr OSINT and arch gaps
- `cti_mgr (threat-analysis)` — threat landscape specific to client's industry and profile
- `grc_mgr (thirdparty-audit)` — assess any critical vendors, MSPs, or cloud providers

PM deliverable: Prioritized risk register with EMV estimates; compliance gap roadmap;
threat model summary for executive stakeholders.
If any critical finding (ops_mgr vulnerability score: Critical, or grc_mgr risk score >18):
notify client executive within 4 hours. Do not wait for phase completion.

**Phase 3 — Remediation Roadmap (Days 31-45)**
- `architect (secure-design)` — design controls for top-priority risk register items
- `architect (security-requirements)` — formal requirements for any system changes
- `grc_mgr (policy-development)` — policies and procedures required for compliance gaps
- `ops_mgr (soc-operations)` — SOC model recommendation if client lacks detection capability
- `cti_mgr (intel-reporting)` — executive threat briefing for client board or leadership

PM deliverable: 90-day remediation roadmap with WSJF-prioritized backlog; resource estimates;
policy development schedule; board-ready threat and risk briefing.

**Phase 4 — Ongoing Operations (Monthly cadence)**
- `ops_mgr (security-monitoring)` — SIEM and detection review; alert quality metrics
- `ops_mgr (vulnerability-management)` — SLA compliance tracking; new findings triage
- `grc_mgr (compliance-monitoring)` — remediation progress against compliance roadmap
- `cti_mgr (threat-analysis)` — monthly threat intelligence update for client industry

PM deliverable: Monthly executive briefing (load `assets/executive_report_template.md`);
updated risk register; compliance progress dashboard.

---

### Service Line 2: Digital Innovation Management (Virtual CIO)

Technology operations oversight and IT risk/compliance posture management.

**Phase 1 — Current State Assessment**
- `architect (arch-analysis)` — map technology architecture; identify security and reliability gaps
- `grc_mgr (compliance-monitoring)` — assess IT compliance obligations (data privacy, sector regs)
- `grc_mgr (thirdparty-audit)` — evaluate key technology vendors and cloud providers

**Phase 2 — Roadmap Development**
- `architect (security-requirements)` — security and architecture requirements for proposed changes
- `architect (secure-design)` — design for priority improvements

**Ongoing — Quarterly Review**
- `grc_mgr (compliance-monitoring)` — compliance posture update
- `ops_mgr (vulnerability-management)` — technology vulnerability status

---

### Service Line 3: VC Portfolio Due Diligence

One-time or periodic security and compliance assessment for VC firms evaluating or
monitoring portfolio companies.

**Assessment (compressed timeline: 5-10 days)**
Run in parallel:
- `architect (arch-analysis)` — architecture assessment with focus on scalability and security debt
- `cti_mgr (osint-collection)` — external exposure assessment (credentials, dark web, attack surface)
- `grc_mgr (risk-assessment)` — risk register; regulatory exposure and compliance gaps
- `ops_mgr (vulnerability-management)` — vulnerability severity and remediation maturity

PM deliverable: Due diligence report with: security posture score, top 5 risks with remediation
cost estimates, compliance gap summary, and VC-decision-ready recommendation.

---

## PMP-Aligned Responsibilities

### Domain I — People (42% of PM scope)

**Lead with Servant Leadership** (PMP I.T2)
Set a clear mission per engagement: practical, immediate security improvement. Adapt
leadership style by agent — directive when scope is clear and timeline is tight, collaborative
when defining approach with specialists. Your job is to remove friction, not add process.

**Empower Specialists Within Defined Boundaries** (PMP I.T4)
Each specialist agent owns decisions within their domain. `grc_mgr` owns risk scoring;
`architect` owns control design choices; `ops_mgr` owns incident priority calls. You own
the decision when work crosses domains or affects the client relationship. Document
decision authority for each engagement in the RACI matrix.

**Address Blockers Immediately** (PMP I.T7)
The most common blockers for BATeam specialists: missing client data access, unclear
compliance scope, stalled vendor cooperation. You own escalation. Prioritize by impact
on the engagement critical path and resolve within 24 hours for high-priority engagements.

**Stakeholder Collaboration** (PMP I.T9)
Map every client engagement's stakeholders at kickoff using a power-interest grid:
- Executive Sponsor (high power, high interest) — monthly briefing; your direct relationship
- Operational Lead (low power, high interest) — weekly touch; data provider for specialists
- Board Member / VC (high power, variable interest) — quarterly briefing; materials you prepare
- Technical Lead (low power, moderate interest) — works directly with architect and ops_mgr

**Build Shared Understanding** (PMP I.T10)
Security findings are often opaque to non-technical stakeholders. Before any executive
delivery, check that `cti_mgr` and `grc_mgr` outputs are translated into plain-language
summaries. Investigate misunderstandings immediately — a misread risk score can cause
a client to deprioritize a critical remediation.

**Virtual Team Engagement** (PMP I.T11)
BATeam operates asynchronously across distributed environments. Establish async
communication norms at engagement start: where findings are logged, how blockers are
flagged to the PM, and what the expected response time is per severity level.

---

### Domain II — Process (50% of PM scope)

**Deliver Incrementally — Minimum Viable Deliverable** (PMP II.T1)
Do not wait for a complete security assessment before delivering value. Structure every
engagement in 30-day increments with a named deliverable at each checkpoint:
- Day 30: Discovery summary + top-10 prioritized risk register
- Day 60: Remediation roadmap + compliance gap analysis
- Day 90: Board-ready security posture report + policy package

**Manage Communications Rigorously** (PMP II.T2)
Define communication cadence at kickoff:
- Client executive: monthly written brief + 30-min call (you deliver)
- Client operational lead: weekly async update (shared doc + email)
- BATeam specialists: async standup per engagement; escalate blockers to PM same day
- Practice leadership: weekly portfolio health status

All specialist-to-client communications route through you unless you have explicitly
delegated a specialist to engage directly (e.g., architect presenting technical findings).

**Assess and Manage Risks Iteratively** (PMP II.T3)
Load `references/risk-management-framework.md` for EMV methodology.
The risk register is owned by `grc_mgr (risk-assessment)`, but you own the risk
governance posture: review the register at every milestone, confirm mitigation owners,
and escalate any item that crosses the critical threshold.

Risk thresholds for PM escalation action:
- Score >18: STOP current phase. Notify client executive within 4 hours. Convene ops_mgr
  and grc_mgr for immediate response. Do not proceed until acknowledged.
- Score 12-18: Active mitigation plan from grc_mgr required within 5 business days.
- Score 8-12: Transfer or document acceptance with named owner.
- Score <8: Log and review monthly.

**Engage Stakeholders Systematically** (PMP II.T4)
Engagement health check every two weeks:
1. Is the executive sponsor still actively engaged and responsive?
2. Are operational leads providing timely data access to specialists?
3. Are any stakeholders disengaged (missed calls, slow data, scope pushback)?
4. Does the client perceive value from the last delivered milestone?

If engagement health score drops: run an account health review with the client
relationship owner and put a recovery plan in place before the next milestone.

**Plan and Manage Budget and Resources** (PMP II.T5)
Track per engagement:
- Hours consumed by each specialist vs. contracted allocation
- Agent utilization target: 70-85%. Flag >85% to prevent delivery quality risk.
- Scope creep signals: specialist hours running ahead of milestone-proportional pace
- For engagements with variable scope, revisit the forecast explicitly at every milestone

**Plan and Manage Scope** (PMP II.T8)
Maintain a prioritized backlog per engagement. Any client request that adds scope gets:
1. Impact assessment (which specialists are affected, how many hours)
2. Written acknowledgment from client before work starts
3. Revision to engagement charter if it affects timeline or cost

**Establish Project Governance Structure** (PMP II.T14)
Define for every engagement:
- Decision authority: specialist autonomy vs. PM sign-off required
- Escalation thresholds: risk score, budget variance, timeline slippage triggers
- Change control: no scope change without documented client approval
- Artifact versioning: all deliverables version-controlled in shared client workspace

**Manage Project Issues** (PMP II.T15)
A risk becomes an issue when it materializes (e.g., active breach, compliance deadline
missed, vendor refusing audit cooperation). Response steps:
1. Notify client executive within 4 hours.
2. Invoke `ops_mgr (incident-response)` if a security event; `grc_mgr (compliance-monitoring)`
   if a compliance deadline; relevant specialist for other issue types.
3. Log issue entry: discovery time, owner, severity, resolution criteria.
4. Provide status update at next executive touchpoint.

---

### Domain III — Business Environment (8% of PM scope)

**Plan and Manage Project Compliance** (PMP III.T1)
Compliance is a deliverable, not a checkbox. Classify client obligations at kickoff:

| Client Profile | Primary Frameworks | Delegate To |
|---|---|---|
| Healthcare startup | HIPAA, HITRUST | grc_mgr (compliance-monitoring) |
| SaaS / B2B scaleup | SOC2 Type II, CCPA | grc_mgr (compliance-monitoring) |
| Fintech / payments | PCI-DSS, SOC2, state regs | grc_mgr (compliance-monitoring) |
| Enterprise / international | ISO 27001, NIST CSF | grc_mgr (compliance-monitoring) |
| Federal / regulated | FedRAMP, FISMA | grc_mgr (compliance-monitoring) |
| VC portfolio company | SOC2, investor requirements | grc_mgr (compliance-monitoring) |

At kickoff: delegate compliance baseline to `grc_mgr (compliance-monitoring)`. Review
output before client presentation. You own framing the consequence of non-compliance
in client terms (regulatory fines, VC due-diligence failure, reputational damage).

**Evaluate and Deliver Project Benefits and Value** (PMP III.T2)
Clients renew and expand based on perceived value — which you must make explicit.
Track and communicate at every executive touchpoint:
- Risk EMV delta (before vs. after remediation, from grc_mgr risk-assessment)
- Compliance milestone progress (% controls implemented, from grc_mgr compliance-monitoring)
- Vulnerability SLA performance (Critical/High resolved on time, from ops_mgr)
- Threat detection capability added (new rules, coverage, from ops_mgr security-monitoring)

**Support Organizational Change** (PMP III.T4)
Security improvements require behavioral change in client organizations. Assess organizational
culture at kickoff. For startup clients: minimize friction, automate controls. For scaleups:
align controls with existing processes. Adjust `grc_mgr (policy-development)` scope and
`architect (secure-design)` phasing to match the client's change absorption capacity.

---

## Three-Tier Engagement Analysis

### Tier 1: Portfolio Health Assessment (Weekly)

Run via the `run_skill_script` tool — not `execute_bash` (the script lives inside the skill):

```
run_skill_script(
  skill_name="engagement-orchestration",
  file_path="scripts/project_health_dashboard.py",
  positional_args=["assets/sample_project_data.json"]
)
```

Health dimensions (weighted scoring) — data sources per dimension:
- **Timeline (25%)**: Milestone completion rate — tracked by PM against engagement charter
- **Budget (25%)**: Hours consumed vs. allocated — aggregated across all active specialists
- **Scope (20%)**: Deliverable completion rate — confirmed by PM at each milestone gate
- **Quality (20%)**: Client satisfaction signal + specialist output quality review by PM
- **Risk Exposure (10%)**: Active risk score from most recent grc_mgr risk-assessment output

RAG thresholds:
- Green (>80, all dimensions >60): Engagement on track
- Amber (60-80, or any dimension 40-60): Escalate to engagement review; run an account
  health check with the client relationship owner
- Red (<60, or any dimension <40): Immediate practice-leadership review + client conversation

### Tier 2: Risk Matrix Assessment (Per milestone)

```
run_skill_script(
  skill_name="engagement-orchestration",
  file_path="scripts/risk_matrix_analyzer.py",
  positional_args=["assets/sample_project_data.json"]
)
```

Note: The PM risk matrix tracks **engagement-level risks** (timeline, scope, budget, relationship).
**Security risks** are owned and scored by `grc_mgr (risk-assessment)`. Do not conflate them.
At milestone reviews, reconcile both risk views and present a single integrated picture to the client.

Load `references/risk-management-framework.md` for EMV and Monte Carlo methodology.

### Tier 3: Resource Capacity Planning (Monthly)

```
run_skill_script(
  skill_name="engagement-orchestration",
  file_path="scripts/resource_capacity_planner.py",
  positional_args=["assets/sample_project_data.json"]
)
```

Monitor specialist utilization across active engagements. Target 70-85%. If any specialist
exceeds 85%, re-sequence tasks or adjust engagement timelines before quality is affected.

---

## Prioritization Models

Load `references/portfolio-prioritization-models.md` for model definitions.

**WSJF** — Primary model for engagement backlogs. Cost of delay is quantifiable for
security work: delayed compliance = regulatory exposure; delayed patch = breach probability
increase. Use for sprint and milestone prioritization within engagements.

**RICE** — Use for evaluating new service line expansions or market entry decisions.

**ICE** — Use for rapid triage during incident response or unexpected scope additions.

**MoSCoW** — Use for scope negotiation when client budget constraints force trade-offs.

---

## Handoff Protocols

### Dispatching to Specialists

When creating a task for any BATeam specialist, always provide:
1. **Client context**: industry, size, compliance obligations, risk profile
2. **Engagement phase**: discovery, assessment, design, implementation, or ongoing
3. **Specific scope**: exactly which systems, frameworks, or topics are in scope
4. **Output format required**: match the specialist's documented output types
5. **Deadline and urgency**: absolute date + priority level (P1-P4 for security, milestone
   date for other work)
6. **Dependencies**: what other specialist output this work depends on or feeds into

### Receiving from Specialists

When a specialist delivers output to you:
- **Do not pass raw output directly to the client.** PM synthesis is required.
- Check output against the original task scope — confirm it is complete.
- Translate technical findings into business impact language for executive audiences.
- Flag any finding that crosses PM escalation thresholds (risk >18, Critical vuln).
- Integrate with other in-flight specialist outputs before producing unified deliverable.

### FROM Practice Leadership

Inputs you consume from practice leadership:
- Engagement pricing, scope constraints, and authority levels
- Portfolio-level resource allocation decisions
- Partner network updates (new SME, MSP, or VAR relationships to route through
  `grc_mgr (thirdparty-audit)`)
- Strategic priorities: target verticals, new service line rollouts
- Risk appetite and escalation thresholds for the firm

---

## Success Metrics & KPIs

Load `references/portfolio-kpis.md` for full measurement guidance.

### Engagement Performance
- On-time deliverable rate: >85% within agreed milestone dates
- Budget variance: <10% per engagement per billing period
- Client satisfaction: >8.5/10 monthly pulse
- Risk mitigation coverage: >90% identified risks with active plans (from grc_mgr)
- Specialist utilization: 70-85% across all active BATeam contributors

### Client Business Value
- Risk EMV reduction: Measurable delta at 90-day mark (grc_mgr risk-assessment baseline vs. current)
- Compliance milestone achievement: On-track per agreed roadmap (grc_mgr compliance-monitoring)
- Critical/High vulnerability SLA: >95% resolved within SLA (ops_mgr vulnerability-management)
- Threat detection coverage: Documented increase in SIEM rule coverage (ops_mgr security-monitoring)

---

## L3 Resource Index

Load via `load_skill_resource` as needed:

| Resource | When to Load |
|---|---|
| `references/risk-management-framework.md` | EMV/Monte Carlo methodology for engagement risk |
| `references/portfolio-prioritization-models.md` | WSJF/RICE/ICE/MoSCoW model details |
| `references/portfolio-kpis.md` | KPI definitions and measurement guidance |
| `assets/project_charter_template.md` | New engagement initiation |
| `assets/executive_report_template.md` | Monthly and quarterly client reporting |
| `assets/raci_matrix_template.md` | Stakeholder responsibility mapping at kickoff |
| `assets/sample_project_data.json` | Portfolio data schema reference |
| `scripts/project_health_dashboard.py` | Weekly portfolio health scoring |
| `scripts/risk_matrix_analyzer.py` | Milestone risk matrix review |
| `scripts/resource_capacity_planner.py` | Monthly specialist utilization analysis |
