---
name: risk-assessment
description: Conduct structured security risk assessments to identify, analyze, and prioritize risks to client information assets. Use when scoping a new risk program, performing periodic risk reviews, assessing a specific system or business process, or preparing a risk register for executive or board reporting.
metadata:
  nice-work-role: SP-RSK-001
  nice-tasks: T0177, T0078, T0087
---

## Overview

Execute a rigorous, framework-aligned risk assessment that produces a prioritized risk register with quantified or qualified risk ratings, mapped to the client's business context and applicable regulatory requirements.

## Framework selection

| Framework | Best for |
|-----------|----------|
| **NIST RMF** (SP 800-37) | US federal systems, FISMA compliance, FedRAMP |
| **NIST SP 800-30** | General IT risk assessments aligned to NIST CSF |
| **ISO/IEC 27005** | ISO 27001-aligned risk programs |
| **FAIR** (Factor Analysis of Info Risk) | Quantitative risk, board-level financial reporting |

Default to NIST SP 800-30 unless the client has a specific framework requirement.

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `scan_scc_findings(project_id, severity_filter)` — pull Security Command Center findings for GCP-hosted assets
- `generate_risk_register(assets, threats, vulnerabilities, framework)` — produce a structured risk register
- `calculate_risk_score(likelihood, impact, methodology)` — compute a risk rating using the specified methodology
- `map_risks_to_controls(risk_register, control_framework)` — map identified risks to applicable controls

## Steps

1. **Establish scope and context**
   - Define assessment boundary: enterprise-wide, specific system, business process, or regulatory scope
   - Identify information assets: systems, data stores, processes, and their classification (Confidentiality/Integrity/Availability)
   - Confirm applicable regulatory frameworks (HIPAA, PCI-DSS, SOX, GDPR, NIST CSF)
   - Identify key stakeholders: asset owners, system administrators, legal/compliance

2. **Identify threats and vulnerabilities**
   - Use threat catalogs: NIST SP 800-30 Appendix D/E, ATT&CK Enterprise
   - Run `scan_scc_findings` for GCP-hosted assets to pull verified vulnerability data
   - Interview stakeholders and review security assessment findings (pen test results, audit reports)
   - Document threat sources (adversarial, accidental, environmental, structural) and threat events

3. **Analyze likelihood and impact**
   - For each threat-vulnerability pairing, assess:
     - **Likelihood**: probability of threat exploitation given existing controls (Almost certain / Very likely / Likely / Even chance / Unlikely / Very unlikely / Almost no chance)
     - **Impact**: business consequence if the risk materializes across CIA dimensions (Critical / Major / Moderate / Minor / Insignificant)
   - Run `calculate_risk_score` to produce composite ratings
   - For FAIR assessments, estimate loss event frequency and magnitude in monetary terms

4. **Prioritize and categorize**
   - Map scores to risk levels: Critical / High / Medium / Low / Informational
   - Group related risks; identify root causes that drive multiple risk scenarios
   - Note risks that breach regulatory thresholds requiring mandatory disclosure or immediate action

5. **Develop treatment recommendations**
   - For each risk: recommend Mitigate / Transfer / Accept / Avoid
   - Run `map_risks_to_controls` to identify applicable control mappings (NIST 800-53, ISO 27002, CIS Controls)
   - Define residual risk after proposed treatment
   - Assign owners and target remediation timelines

6. **Produce risk register and executive summary**
   - Run `generate_risk_register` to produce the structured output
   - Prepare executive summary with top-10 risks and recommended treatment plan

## Output format

```
## Risk Assessment: [Client / System / Scope]

### Assessment Overview
Framework: | Scope: | Date: | Regulatory context:

### Risk Register

| Risk ID | Asset | Threat | Vulnerability | Likelihood | Impact | Rating | Treatment | Owner | Target Date |
|---------|-------|--------|---------------|------------|--------|--------|-----------|-------|-------------|
| R-01    | ...   | ...    | ...           | High       | Severe | High   | Mitigate  | ...   | ...         |

### Top Risks Summary
[Narrative of top 5–10 risks with business context]

### Treatment Roadmap
[Phased remediation plan with resource estimates]

### Residual Risk Statement
[Risks remaining after treatment, accepted by risk owner]
```

## Reference material

For likelihood/impact scales, NIST SP 800-30 / 800-37 threat catalogs, and FAIR loss-magnitude tables, work from your training and confirm scale boundaries with the user before scoring.
