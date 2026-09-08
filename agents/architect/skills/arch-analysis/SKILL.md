---
name: arch-analysis
description: Assess an organization's cybersecurity architecture to identify systems, components, and data flows designed without adequate security controls. Use when reviewing existing client infrastructure, evaluating security posture, or scoping a remediation engagement.
metadata:
  nice-work-role: SP-ARC-001
  nice-tasks: T0050, T0095
---

## Overview

Conduct a structured assessment of a client's existing security architecture to surface gaps, missing controls, and design weaknesses that expose the organization to risk.

## Steps

1. **Gather architecture artifacts**
   - Request network diagrams, data flow diagrams, system inventories, and existing security documentation
   - Identify system boundaries, trust zones, and data classifications in use

2. **Map the current state**
   - Enumerate systems, services, and integrations; document owner, purpose, and data sensitivity
   - Document authentication and authorization mechanisms across all components
   - Identify data stores, transmission paths, and external interfaces

3. **Evaluate against security design principles**
   - Apply defense-in-depth and least-privilege analysis
   - Check for segmentation between trust zones (e.g., production vs. dev, PCI cardholder data environment vs. out-of-scope)
   - Identify single points of failure and implicit trust relationships
   - Assess encryption coverage in transit and at rest

4. **Map findings to frameworks**
   - Align gaps to NIST CSF functions (Identify, Protect, Detect, Respond, Recover)
   - Cross-reference with applicable compliance requirements (PCI-DSS, HIPAA, SOX, GDPR)
   - Reference relevant CIS Controls or NIST SP 800-53 control families

5. **Produce findings report**
   - Document each gap: affected system, risk description, potential impact, recommended remediation
   - Prioritize findings: Critical / High / Medium / Low / Info
   - Provide an executive summary suitable for CISO briefing

## Output format

```
## Architecture Assessment: [Client Name]

### Executive Summary
[2-3 sentences on overall posture and top risks]

### Findings

| # | Finding | Affected Component | Severity | Recommendation |
|---|---------|-------------------|----------|----------------|
| 1 | ...     | ...               | High     | ...            |

### Detailed Findings
[Per-finding: description, evidence, risk rationale, remediation steps]

### Compliance Mapping
[Map findings to specific regulatory controls where applicable]
```
