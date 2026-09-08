---
name: thirdparty-audit
description: Assess whether new and existing vendor or third-party services comply with applicable privacy and data security obligations including PCI-DSS, Sarbanes-Oxley, HIPAA, HITRUST, GDPR, and GLBA. Use when onboarding new vendors, performing periodic vendor reviews, or responding to third-party risk events.
metadata:
  nice-work-role: SP-RSK-001
  nice-tasks: T0177, T0028
---

## Overview

Evaluate the security and compliance posture of third-party vendors and service providers to determine whether they meet the client's contractual, regulatory, and risk requirements.

## Steps

1. **Scope the audit**
   - Identify the vendor's services and the data/systems they access or process
   - Determine applicable regulatory frameworks based on data type (PII, PHI, cardholder data, financial records)
   - Classify vendor tier by risk exposure (e.g., critical, high, medium, low)

2. **Gather vendor evidence**
   - Request security questionnaire responses (SIG, CAIQ, or client-specific)
   - Collect third-party attestations: SOC 2 Type II, ISO 27001 certificate, PCI-DSS AOC, HITRUST CSF
   - Review contract terms: DPA, BAA, SLA, right-to-audit clauses, breach notification requirements

3. **Assess against frameworks**
   - **PCI-DSS**: Verify scope, segmentation, and AOC validity for cardholder data handlers
   - **HIPAA/HITECH**: Confirm BAA in place, PHI safeguards, and breach notification procedures
   - **SOX**: Review financial system controls and change management processes
   - **GDPR**: Validate DPA, data subject rights support, cross-border transfer mechanisms (SCCs, BCRs)
   - **GLBA**: Check Safeguards Rule compliance for financial data processors
   - **HITRUST**: Review CSF certification scope and control maturity

4. **Identify and rate findings**
   - Document gaps between vendor posture and required controls
   - Rate each finding: Critical / High / Medium / Low
   - Note findings that create regulatory exposure for the client

5. **Produce audit report and recommendations**
   - Summarize vendor's overall compliance posture
   - List required remediation items and timeline expectations
   - Recommend onboarding approval, conditional approval with remediation plan, or rejection

## Output format

```
## Third-Party Audit: [Vendor Name]

### Vendor Profile
Service: | Data Classification: | Risk Tier: | Frameworks in Scope:

### Compliance Assessment

| Framework | Status | Key Findings | Remediation Required |
|-----------|--------|-------------|----------------------|
| PCI-DSS   | ...    | ...         | ...                  |

### Findings

| # | Finding | Severity | Framework | Recommendation |
|---|---------|----------|-----------|----------------|

### Recommendation
[Approve / Conditional Approval / Reject — with rationale]
```
