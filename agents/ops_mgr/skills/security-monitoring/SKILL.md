---
name: security-monitoring
description: Design, configure, and optimize security monitoring, alerting, and SIEM operations for client environments. Use when reviewing detection coverage, building or tuning detection rules, assessing SIEM health, designing monitoring architecture, or analyzing security event data to identify threats.
metadata:
  nice-work-role: OM-ANA-001
  nice-tasks: T0259, T0058, T0292
---

## Overview

Ensure clients have comprehensive, well-tuned visibility into security-relevant events across their environment. This skill covers both the operational analysis of security events and the strategic design of monitoring programs.

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `query_chronicle(udm_query, time_range)` — execute a UDM (Unified Data Model) query against Chronicle Security Operations
- `get_scc_findings(project_id, category, state)` — retrieve Security Command Center findings by category and state
- `analyze_log_coverage(project_id)` — assess which GCP log sources are enabled and flowing to Chronicle
- `create_detection_rule(rule_name, logic_description, platform)` — generate a YARA-L2 (Chronicle) or Sigma detection rule
- `get_alert_metrics(project_id, time_range)` — retrieve alert volume, MTTD, and false positive rate metrics

## Steps

### Event analysis

1. **Scope the investigation**
   - Identify the time range, source systems, and event types of interest
   - Run `analyze_log_coverage` to confirm relevant log sources are available

2. **Query and correlate**
   - Run `query_chronicle` with targeted UDM queries:
     - Authentication events: `metadata.event_type = "USER_LOGIN" AND security_result.action = "BLOCK"`
     - Lateral movement: correlate logon events across multiple hosts in short windows
     - Data exfiltration: large outbound transfers to unusual destinations
   - Run `get_scc_findings` to correlate SIEM alerts with SCC vulnerability/threat findings

3. **Triage and classify**
   - Classify each event: True Positive / False Positive / Benign True Positive
   - For true positives: escalate to the `incident-response` skill
   - For false positives: document and tune the detection rule to reduce noise

### Detection rule development

1. **Define the detection objective**
   - State the threat or behavior to detect (reference ATT&CK technique ID if applicable)
   - Identify the log source(s) that contain the relevant signal

2. **Develop and test the rule**
   - Run `create_detection_rule` with the threat description and target platform (Chronicle/YARA-L2 or Sigma)
   - Test against known-good and known-bad data; measure false positive rate
   - Tune thresholds and exceptions to achieve acceptable signal-to-noise ratio

3. **Document and deploy**
   - Document: ATT&CK technique covered, data sources required, expected alert rate, triage guidance
   - Add to detection rule library; assign severity and response SLA

### Monitoring program review

1. **Assess coverage**
   - Run `analyze_log_coverage` to map enabled log sources against the ATT&CK data source matrix
   - Identify gaps: which tactics/techniques lack detection coverage?

2. **Review alert health**
   - Run `get_alert_metrics` to assess: alert volume, MTTD (mean time to detect), false positive rate
   - Flag rules generating > 20% false positive rate for immediate tuning

3. **Produce coverage report**
   - Map current detection rules to ATT&CK techniques
   - Highlight coverage gaps by tactic
   - Recommend priority rules to develop based on threat actor TTPs from the CTI Manager

## Output format

```
## Security Monitoring Report: [Client / Scope]

### Coverage Assessment
Log sources active: | ATT&CK techniques covered: | Coverage gaps by tactic:

### Alert Health
Total alerts (period): | True positive rate: | MTTD: | False positive rate:

### Top Findings
[Summary of significant events or detections]

### Detection Gaps
| ATT&CK Tactic | Technique | Gap Type | Priority | Recommended Rule |

### Tuning Recommendations
[Rules requiring adjustment with rationale]
```
