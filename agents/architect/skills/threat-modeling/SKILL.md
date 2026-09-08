---
name: threat-modeling
description: Conduct structured threat modeling sessions using STRIDE, PASTA, or LINDDUN to identify design-level threats, attack surfaces, and trust boundary violations. Use when designing new systems, reviewing existing architectures, or preparing security requirements for development teams.
metadata:
  nice-work-role: SP-ARC-001
  nice-tasks: T0071, T0095
---

## Overview

Apply a structured threat modeling methodology to identify threats, rank risks, and drive mitigating security requirements before systems are built or significantly changed.

## Methodology selection

| Methodology | Best for |
|-------------|----------|
| **STRIDE** | General system/application threat enumeration |
| **PASTA** | Risk-centric, attacker-focused analysis for high-value systems |
| **LINDDUN** | Privacy threat analysis for systems processing personal data |

Default to STRIDE unless privacy requirements or attacker-centric analysis is requested.

## Steps (STRIDE)

1. **Define scope and create DFD**
   - Draw a Data Flow Diagram (DFD): identify processes, data stores, external entities, and data flows
   - Mark trust boundaries where data crosses security zones
   - Note the assets being protected and their value/sensitivity

2. **Enumerate threats by STRIDE category**
   For each element in the DFD, consider applicable threats:
   - **S**poofing: Can an attacker impersonate a user, service, or component?
   - **T**ampering: Can data in transit or at rest be modified without detection?
   - **R**epudiation: Can a user or service deny performing an action?
   - **I**nformation Disclosure: Can sensitive data be accessed by unauthorized parties?
   - **D**enial of Service: Can availability of the system or data be disrupted?
   - **E**levation of Privilege: Can an attacker gain higher-level access than authorized?

3. **Rate each threat**
   Use DREAD or a simplified severity × likelihood rating:
   - **Critical**: High severity + likely to be exploited, no current mitigation
   - **High**: Significant impact or easily exploited
   - **Medium**: Moderate impact, requires some effort
   - **Low**: Limited impact or unlikely

4. **Define mitigations**
   - Map each threat to one or more security controls or design changes
   - Link mitigations to security requirements (use `security-requirements` skill for formal output)
   - Identify accepted risks with documented rationale

5. **Validate and hand off**
   - Review results with the development/engineering team
   - Integrate findings into security requirements backlog or architecture ADRs
   - Schedule re-modeling for significant design changes

## Output format

```
## Threat Model: [System Name]

### Scope
[System description, assets, trust boundaries]

### DFD Elements
[List of processes, data stores, external entities, data flows]

### Threat Enumeration

| ID  | Element | STRIDE Category | Threat Description | Severity | Mitigation |
|-----|---------|----------------|-------------------|----------|------------|
| T01 | Login API | Spoofing | Attacker replays stolen session token | High | Implement token binding + short expiry |

### Accepted Risks
[Threats accepted with rationale]

### Security Requirements Generated
[Cross-reference to SR-IDs from security-requirements output]
```
