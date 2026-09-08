---
name: secure-design
description: Design and recommend security measures to address identified security architecture gaps. Use when developing security architectures, remediating design weaknesses, specifying security controls, or producing secure design documentation for client systems.
metadata:
  nice-work-role: SP-ARC-001
  nice-tasks: T0051, T0071, T0082, T0084
---

## Overview

Translate identified security gaps and requirements into concrete security architecture designs, control specifications, and implementation guidance for client systems.

## Steps

1. **Understand the design context**
   - Review architecture assessment findings or stated security requirements
   - Identify the client's risk tolerance, compliance obligations, and operational constraints
   - Clarify the scope: new system design vs. remediation of existing architecture

2. **Select applicable security patterns**
   - Map requirements to established security design patterns (zero trust, micro-segmentation, secure-by-default)
   - Identify candidate security controls from NIST SP 800-53, CIS Controls, or CSA CCM
   - Consider compensating controls where ideal controls are operationally infeasible

3. **Design the security architecture**
   - Produce logical and physical security architecture diagrams (trust zones, security boundaries, data flows)
   - Specify authentication and authorization mechanisms (MFA, RBAC, ABAC, PAM)
   - Define encryption requirements: algorithms, key management, certificate lifecycle
   - Address network segmentation, ingress/egress filtering, and monitoring integration points

4. **Validate the design**
   - Confirm the design addresses all identified findings and stated requirements
   - Review against threat model to ensure controls mitigate relevant threats
   - Check for compliance alignment and document any residual gaps

5. **Document and deliver**
   - Produce an Architecture Design Record (ADR) or Security Architecture Document
   - Include rationale for key design decisions and trade-offs
   - Provide implementation guidance with phasing and prioritization

## Output format

```
## Secure Design: [System/Engagement Name]

### Design Objectives
[Security requirements and gaps being addressed]

### Architecture Overview
[Narrative description + reference to diagrams]

### Security Controls

| Control | Type | Implementation | Rationale |
|---------|------|----------------|-----------|
| ...     | ...  | ...            | ...       |

### Implementation Guidance
[Phased rollout, configuration notes, dependencies]

### Residual Risks
[Accepted risks and rationale]
```
