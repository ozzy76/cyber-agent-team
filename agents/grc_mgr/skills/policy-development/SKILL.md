---
name: policy-development
description: Develop, review, and maintain security policies, standards, and procedures for client organizations. Use when a client needs a new policy, when existing policies must be updated for regulatory alignment, when a gap analysis reveals missing documentation, or when building out a security policy program from scratch.
metadata:
  nice-work-role: SP-RSK-001
  nice-tasks: T0028, T0084, T0265
---

## Overview

Produce security governance documentation — policies, standards, baselines, and procedures — that are legally defensible, operationally practical, and aligned to the client's regulatory obligations and risk tolerance.

## Document hierarchy

```
Policy          "What must be done" — senior leadership approved, mandatory
  └── Standard  "How it must be done" — specific technical or process requirements
        └── Baseline  "Minimum configuration" — system-specific hardening specs
        └── Procedure "Step-by-step instructions" — operational how-to guides
              └── Guideline  "Recommended practices" — non-mandatory best practices
```

## Common policy types

| Policy | Regulatory drivers | Core content |
|--------|--------------------|--------------|
| Information Security Policy | ISO 27001, SOC 2 | Scope, roles, objectives, enforcement |
| Access Control Policy | PCI-DSS Req 7–8, HIPAA §164.312(a) | Least privilege, MFA, PAM, account lifecycle |
| Data Classification Policy | GDPR Art. 5, HIPAA, PCI-DSS | Classification tiers, handling requirements |
| Acceptable Use Policy | SOC 2, ISO 27001 | Authorized use, monitoring, consequences |
| Incident Response Policy | HIPAA §164.308(a)(6), NIST CSF RS | Roles, escalation, notification timelines |
| Business Continuity Policy | SOC 2 Availability, ISO 22301 | RTO/RPO objectives, testing requirements |
| Cryptography Policy | PCI-DSS Req 3–4, NIST SP 800-175 | Approved algorithms, key management |
| Third-Party Risk Policy | PCI-DSS Req 12.8, GDPR Art. 28 | Vendor tiers, due diligence, contractual requirements |
| Vulnerability Management Policy | PCI-DSS Req 6, NIST CSF ID.RA | Scanning cadence, CVSS thresholds, SLA by severity |

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `generate_policy(policy_type, organization_profile, frameworks)` — produce a draft policy document
- `review_policy_gaps(existing_policy_text, target_framework)` — identify gaps between an existing policy and a framework's requirements
- `map_policy_to_controls(policy_text, control_framework)` — produce a traceability matrix from policy statements to controls

## Steps

1. **Establish requirements**
   - Identify the policy type needed and the trigger (new regulation, gap finding, audit requirement)
   - Confirm the organization's regulatory frameworks in scope
   - Review existing policies to avoid duplication; note superseded documents

2. **Draft the document**
   - Run `generate_policy` with the organization profile and applicable frameworks
   - Ensure mandatory sections are present (see template below)
   - Write policy statements in normative language: SHALL, SHALL NOT, MUST, MUST NOT
   - Avoid prescribing technology specifics in policies — reserve those for standards and baselines

3. **Align to regulatory requirements**
   - Run `map_policy_to_controls` to produce a control traceability matrix
   - Ensure every mandatory regulatory control is addressed by at least one policy statement
   - Run `review_policy_gaps` if updating an existing policy

4. **Review and approve**
   - Route for stakeholder review: legal/compliance, IT/security leadership, business owners
   - Document review comments and resolutions
   - Obtain formal approval from appropriate authority (CISO, CTSO, or executive sponsor)

5. **Publish and maintain**
   - Assign a document ID, version number, effective date, and next review date
   - Define exception and waiver process
   - Establish the review cadence (typically annual or triggered by material change)

## Policy document template

```
## [Policy Name]
Document ID: | Version: | Effective Date: | Review Date: | Approved by:
Classification: Internal / Confidential

### 1. Purpose
[Why this policy exists and what it protects]

### 2. Scope
[Who and what this policy applies to; explicit exclusions]

### 3. Policy Statements
3.1 [Statement] — The organization SHALL...
3.2 [Statement] — All employees MUST...

### 4. Roles and Responsibilities
| Role | Responsibility |

### 5. Compliance and Enforcement
[Consequences of non-compliance; monitoring and audit mechanisms]

### 6. Exceptions
[How to request an exception; approval authority; maximum exception duration]

### 7. Related Documents
[Cross-references to supporting standards, procedures, guidelines]

### 8. Regulatory Mapping
| Requirement | Policy Section |

### 9. Revision History
| Version | Date | Author | Change Summary |
```
