---
name: security-requirements
description: Develop formal, traceable security requirements for systems, components, and services. Use when scoping a new system design, preparing a Statement of Work, or establishing security acceptance criteria for a client build or procurement.
metadata:
  nice-work-role: SP-ARC-001
  nice-tasks: T0082, T0084
---

## Overview

Elicit, document, and validate security requirements that define what a system must do to protect confidentiality, integrity, and availability, and to satisfy applicable regulatory and business obligations.

## Steps

1. **Establish context**
   - Identify the system or component in scope and its purpose
   - Determine the data classification and sensitivity of information processed
   - Identify applicable regulatory requirements (PCI-DSS, HIPAA, SOX, GDPR, NIST 800-53)
   - Review threat model and architecture findings if available

2. **Elicit requirements**
   - Interview stakeholders: system owners, operations, legal/compliance, business leads
   - Review existing policies, standards, and baseline security requirements
   - Map regulatory control mandates to specific system behaviors

3. **Structure requirements**
   Use the format: **[ID] The system SHALL/SHALL NOT [capability] in order to [security objective]**

   Categories to cover:
   - **Authentication & Access Control**: identity verification, MFA, RBAC, session management
   - **Data Protection**: encryption at rest and in transit, key management, data masking
   - **Audit & Logging**: audit trail, log integrity, retention, SIEM integration
   - **Network Security**: segmentation, firewall rules, TLS versions, API security
   - **Vulnerability Management**: patching cadence, SAST/DAST requirements, dependency scanning
   - **Availability & Resilience**: RTO/RPO, failover, backup and recovery
   - **Incident Response**: detection requirements, alerting thresholds, response SLAs

4. **Validate and trace**
   - Map each requirement to a business driver, risk, or regulatory control
   - Review with stakeholders for completeness and feasibility
   - Confirm requirements are testable and measurable

5. **Deliver requirements document**
   - Assign unique IDs for traceability through design, build, and test phases
   - Indicate requirement priority: Mandatory / High / Medium / Low

## Output format

```
## Security Requirements: [System Name]

### Context
Data classification: | Regulatory scope: | Risk tier:

### Requirements

| ID    | Requirement | Category | Priority | Regulatory Mapping |
|-------|-------------|----------|----------|--------------------|
| SR-01 | The system SHALL enforce MFA for all privileged access | Authentication | Mandatory | NIST 800-53 IA-2 |

### Traceability Matrix
[Maps each requirement to its source risk, control, or regulation]
```
