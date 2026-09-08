---
name: soc-operations
description: Advise on Security Operations Center design, process maturity, tooling selection, and operational metrics. Use when designing a new SOC, assessing SOC maturity, developing playbooks or runbooks, optimizing shift operations, or producing SOC performance reporting for a client.
metadata:
  nice-work-role: OM-OPS-001
  nice-tasks: T0259, T0292, T0395
---

## Overview

Provide expert advisory on building, running, and maturing a SOC function — from organizational model and tooling architecture through analyst workflows, runbooks, metrics, and continuous improvement. Applies equally to in-house, managed, or hybrid SOC models.

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `get_alert_metrics(project_id, time_range)` — retrieve SOC performance metrics from Chronicle and SCC
- `generate_playbook(incident_type, platform, detail_level)` — produce a structured incident response playbook
- `assess_soc_maturity(questionnaire_responses)` — score SOC maturity against the SOC-CMM or similar framework
- `get_analyst_workload_metrics(time_range)` — retrieve alert queue depth, analyst handle times, and escalation rates

## SOC advisory areas

### SOC model design

| Model | Best for | Tradeoffs |
|-------|----------|-----------|
| In-house 24×7 | Large enterprise, high-risk environments | High cost; requires deep bench |
| Business-hours + on-call | Mid-market, lower threat profile | Coverage gaps overnight |
| Managed SOC (MSSP) | Organizations without security headcount | Shared analyst pool; context-switching risk |
| Hybrid (MSSP L1 + in-house L2/L3) | Growing security programs | Balances cost and control |
| Virtual SOC | Distributed teams, cloud-native | Requires strong tooling and process discipline |

### Analyst tier model

| Tier | Role | Responsibilities |
|------|------|-----------------|
| L1 | Alert analyst | Triage, classify, escalate; follow playbooks |
| L2 | Incident responder | Investigate escalations; contain and remediate |
| L3 | Threat hunter / senior analyst | Proactive hunting; rule development; complex IR |
| L4 | SOC lead / engineer | Tooling, process design, metrics, escalation authority |

## Steps

### SOC maturity assessment

1. **Collect operational data**
   - Run `get_alert_metrics` and `get_analyst_workload_metrics` for the past 90 days
   - Interview SOC leadership on: tool stack, coverage model, escalation process, training, and metrics program

2. **Score against SOC-CMM**
   - Run `assess_soc_maturity` with questionnaire responses
   - Score across five domains: Business, People, Process, Technology, Services
   - Identify the current maturity level (1–5) per domain and the target state

3. **Produce improvement roadmap**
   - Identify top-3 maturity gaps with highest risk/effort ratio
   - Recommend capability investments: tooling, process, headcount, or training

### Playbook development

1. **Select the scenario**
   - Common playbook types: phishing response, ransomware, account compromise, DDoS, insider threat, data exfiltration

2. **Build the playbook**
   - Run `generate_playbook` for the scenario and target platform (Chronicle / PagerDuty / Jira)
   - Structure: trigger → triage checklist → investigation steps → containment actions → escalation criteria → communication templates → closure steps
   - Include decision branches for common variations (e.g., phishing with vs. without credential harvest)

3. **Test and validate**
   - Tabletop the playbook with L1 analysts
   - Time the process end-to-end; identify bottlenecks
   - Automate repetitive steps (lookups, notifications) via SOAR integration where available

### SOC metrics program

Recommended KPIs:

| Metric | Target | Frequency |
|--------|--------|-----------|
| Mean Time to Detect (MTTD) | < 24 hrs (ideally < 1 hr for P1) | Weekly |
| Mean Time to Respond (MTTR) | P1 < 4 hrs, P2 < 24 hrs | Weekly |
| Alert-to-Incident conversion rate | Baseline + trend | Weekly |
| False positive rate | < 20% per rule | Monthly |
| SLA compliance | > 95% | Monthly |
| Analyst utilization | 60–75% on investigations | Monthly |
| Runbook coverage | % of alert types with playbooks | Quarterly |

## Output format

```
## SOC Operations Report: [Client]

### Current State Summary
Coverage model: | Headcount: | Primary tooling: | Alerts/day (avg):

### Maturity Assessment
| Domain | Current Level | Target Level | Key Gap |
|--------|--------------|--------------|---------|

### Performance Metrics (Period: [dates])
| Metric | Value | Target | Trend |
|--------|-------|--------|-------|

### Recommendations
| Priority | Recommendation | Category | Effort | Impact |
|----------|---------------|----------|--------|--------|

### Playbooks Delivered / Updated
[List with links or references]
```
