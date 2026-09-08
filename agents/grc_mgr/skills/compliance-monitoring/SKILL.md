---
name: compliance-monitoring
description: Monitor and report on client adherence to regulatory requirements and security control frameworks. Use when performing a compliance gap assessment, preparing for an audit, generating compliance evidence, tracking remediation of compliance findings, or producing periodic compliance status reports.
metadata:
  nice-work-role: SP-RSK-001
  nice-tasks: T0054, T0265, T0177
---

## Overview

Provide continuous or point-in-time visibility into a client's compliance posture across one or more regulatory frameworks. Identify gaps, track remediation, and produce audit-ready evidence.

## Supported frameworks

| Framework | Regulatory scope | Key control areas |
|-----------|-----------------|-------------------|
| **PCI-DSS v4.0** | Payment card data | Network security, access control, encryption, testing |
| **HIPAA / HITECH** | Protected health information | Safeguards, BAAs, breach notification |
| **SOX (ITGC)** | Financial reporting systems | Change management, access control, availability |
| **GDPR / UK GDPR** | EU/UK personal data | Lawful basis, data subject rights, DPIA, breach notification |
| **GLBA Safeguards Rule** | Financial services | Risk assessment, access controls, incident response |
| **HITRUST CSF** | Healthcare and cross-sector | 19 control categories, maturity scoring |
| **NIST CSF 2.0** | Cross-sector voluntary | Govern, Identify, Protect, Detect, Respond, Recover |
| **ISO/IEC 27001:2022** | Cross-sector | 93 controls across 4 themes |
| **FedRAMP / FISMA** | US federal cloud | NIST SP 800-53 control baselines |

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `get_scc_compliance_posture(project_id, framework)` — pull Security Command Center compliance dashboard data for the specified framework
- `query_audit_logs(project_id, time_range, filter_expr)` — query Cloud Audit Logs for compliance-relevant events
- `generate_compliance_report(findings, framework, audience)` — produce a formatted compliance status report
- `track_remediation_status(finding_ids)` — check current status of open compliance findings

## Steps

1. **Define compliance scope**
   - Confirm the framework(s) in scope and the applicable compliance baseline (e.g., PCI-DSS SAQ-D, HIPAA Security Rule, ISO 27001 Annex A)
   - Identify systems, data types, and processes within the compliance boundary
   - Confirm the assessment trigger: initial gap assessment, pre-audit readiness, or periodic monitoring

2. **Collect compliance evidence**
   - Run `get_scc_compliance_posture` for GCP-hosted systems to pull automated control validation results
   - Run `query_audit_logs` to gather evidence for access control, change management, and availability requirements
   - Request manual evidence for controls not covered by automated scanning: policies, training records, vendor contracts (BAAs, DPAs), penetration test results

3. **Assess control implementation**
   - For each required control, determine implementation status:
     - **Compliant**: control implemented and evidence sufficient
     - **Partially Compliant**: control implemented but gaps or documentation deficiencies exist
     - **Non-Compliant**: control not implemented or materially deficient
     - **Not Applicable**: control excluded from scope with documented rationale

4. **Identify and prioritize gaps**
   - Document each non-compliant or partially compliant control
   - Assess the regulatory consequence of each gap: audit finding, reportable breach, penalty exposure
   - Prioritize by regulatory risk and implementation effort

5. **Track and report**
   - Run `track_remediation_status` on any previously identified findings to update progress
   - Run `generate_compliance_report` for the client's audience (auditors, CISO, board)
   - Flag any findings requiring immediate action or executive notification

## Output format

```
## Compliance Assessment: [Client] — [Framework] — [Date]

### Compliance Posture Summary
Framework version: | Scope: | Assessment type: | Overall status:

### Control Status Summary
| Status | Count | Percentage |
|--------|-------|------------|
| Compliant | ... | ...% |
| Partially Compliant | ... | ...% |
| Non-Compliant | ... | ...% |

### Non-Compliant / Partial Findings

| Control ID | Description | Status | Gap | Risk | Remediation | Owner | Target |
|------------|-------------|--------|-----|------|-------------|-------|--------|

### Remediation Roadmap
[Phased plan: immediate (0–30 days), short-term (30–90 days), long-term (90+ days)]

### Audit Readiness Statement
[Summary of readiness for formal audit or regulatory examination]
```
