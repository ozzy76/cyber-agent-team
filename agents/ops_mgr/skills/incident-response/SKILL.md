---
name: incident-response
description: Lead and manage security incident response from initial detection through containment, eradication, recovery, and post-incident review. Use when triaging a suspected security incident, directing response actions, drafting containment or remediation steps, producing an incident timeline, or preparing post-incident reports.
metadata:
  nice-work-role: PR-INF-001
  nice-tasks: T0161, T0163, T0175, T0230
---

## Overview

Execute or advise on structured incident response following the NIST SP 800-61 lifecycle (Preparation → Detection → Containment → Eradication → Recovery → Post-Incident). Provide clear, prioritized actions to minimize dwell time and business impact.

## Incident severity matrix

| Severity | Criteria | Response SLA | Escalation |
|----------|----------|-------------|------------|
| P1 – Critical | Active compromise, data exfiltration, ransomware, C2 confirmed | Immediate (< 15 min) | CISO, legal, executive |
| P2 – High | Confirmed malicious activity, no confirmed exfiltration | < 1 hour | CISO |
| P3 – Medium | Suspicious activity, possible compromise | < 4 hours | Security manager |
| P4 – Low | Policy violation, unconfirmed anomaly | < 24 hours | SOC lead |

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `query_chronicle(udm_query, time_range)` — query Chronicle for events related to the incident
- `get_scc_findings(project_id, category, state)` — retrieve SCC findings for affected GCP assets
- `isolate_instance(project_id, zone, instance_name)` — remove all firewall rules and isolate a GCP Compute instance (requires approval)
- `revoke_iam_access(project_id, principal, role)` — revoke a compromised IAM binding (requires approval)
- `collect_forensic_evidence(project_id, instance_name, artifact_type)` — preserve disk image, memory, or logs to GCS for forensic analysis
- `generate_timeline(incident_id, event_data)` — produce a structured incident timeline from event data

## Response phases

### 1. Detection and triage
- Confirm the alert is a true positive via `query_chronicle` for corroborating events
- Assign initial severity using the matrix above
- Identify affected assets, accounts, and data; determine if exfiltration or persistence is present
- Open incident ticket and notify required stakeholders per severity level

### 2. Containment
- **Short-term**: Isolate affected systems immediately to stop lateral movement
  - Run `isolate_instance` for affected GCP Compute instances (get approval first)
  - Run `revoke_iam_access` for compromised service accounts or user credentials
  - Block malicious IPs/domains at perimeter and Cloud Armor
- **Long-term**: Implement stable containment while investigation continues
  - Replace temporary blocks with permanent controls
  - Maintain business continuity — identify alternate systems if needed

### 3. Evidence preservation
- Run `collect_forensic_evidence` before any remediation that would overwrite data
- Preserve: disk images, memory dumps, network captures, log exports
- Maintain chain of custody documentation for any evidence that may support legal action

### 4. Eradication
- Identify and remove all attacker artifacts: malware, backdoors, persistence mechanisms, rogue accounts
- Patch or mitigate the exploited vulnerability
- Reset all credentials associated with the compromised scope
- Validate eradication by re-querying Chronicle for attacker TTPs after remediation

### 5. Recovery
- Restore systems from known-good backups or clean builds
- Re-enable services incrementally; monitor closely for re-compromise
- Validate system integrity before returning to production
- Confirm with affected business units that operations are restored

### 6. Post-incident review
- Run `generate_timeline` to produce the incident timeline for the post-incident report
- Conduct post-incident review within 5 business days of resolution
- Produce post-incident report (see template below)

## Post-incident report template

```
## Post-Incident Report: [Incident ID]

### Executive Summary
[2–3 sentences: what happened, business impact, resolution]

### Incident Timeline
| Date/Time (UTC) | Event | Source | Actor |

### Root Cause Analysis
[Technical root cause; contributing factors]

### Impact Assessment
Systems affected: | Data at risk: | Business impact: | Regulatory notification required: Y/N

### Response Actions Taken
[Chronological summary of containment, eradication, and recovery steps]

### Lessons Learned
[What worked well; what needs improvement]

### Remediation Items
| # | Finding | Recommendation | Owner | Due Date |

### Detection Gaps Identified
[Pass to Security Monitoring for rule development]
```
