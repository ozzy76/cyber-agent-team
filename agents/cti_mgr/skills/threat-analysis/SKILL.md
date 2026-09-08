---
name: threat-analysis
description: Analyze cyber threat data to identify adversary TTPs, assess client exposure, and produce actionable threat assessments. Use when evaluating indicators of compromise, analyzing malware behavior, mapping adversary techniques to the environment, or assessing the relevance of a threat to a specific client vertical.
metadata:
  nice-work-role: AN-TWA-001
  nice-tasks: T0567, T0573, T0641
---

## Overview

Ingest raw threat data and produce a structured assessment of adversary tactics, techniques, and procedures (TTPs), mapped to the client's environment and expressed in terms of business risk.

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `lookup_indicator(indicator, indicator_type)` — query threat intel platforms for context on an IP, domain, hash, or URL
- `map_ttps_to_attack(ttp_descriptions)` — map described behaviors to MITRE ATT&CK techniques and sub-techniques
- `assess_client_exposure(technique_ids, environment_profile)` — determine whether the client's environment is susceptible to specified ATT&CK techniques

## Steps

1. **Triage the threat data**
   - Identify the type of input: IOCs (IPs, domains, hashes), behavioral descriptions, malware samples, incident data
   - Determine the client vertical and relevant threat actors for that sector

2. **Enrich indicators**
   - Run `lookup_indicator` for each IOC to retrieve: threat scores, associated campaigns, related infrastructure, and historical context
   - Note confidence level and source reliability for each result (use the Admiralty Scale: A1–F6)

3. **Map to MITRE ATT&CK**
   - Run `map_ttps_to_attack` to identify matching techniques and sub-techniques
   - Identify the relevant ATT&CK Enterprise, ICS, or Mobile matrix based on client environment
   - Note tactic phase: Reconnaissance → Initial Access → Execution → Persistence → … → Impact

4. **Assess client exposure**
   - Run `assess_client_exposure` to evaluate whether the client's controls address observed techniques
   - Identify detection gaps (no visibility) vs. prevention gaps (visible but not blocked)
   - Prioritize gaps by technique prevalence in the relevant threat actor's playbook

5. **Produce threat assessment**
   - State the threat actor (if attributed), campaign, and targeting rationale
   - List confirmed and suspected TTPs with ATT&CK IDs
   - Rate overall threat severity for this client: Critical / High / Medium / Low
   - Provide prioritized defensive recommendations

## Output format

```
## Threat Assessment: [Threat Actor / Campaign / Incident]

### Threat Summary
Actor: | Campaign: | Targeted sector: | Assessment date:
Overall severity for [Client]: Critical / High / Medium / Low

### TTP Analysis

| ATT&CK ID | Technique | Tactic | Client Exposure | Detection Gap |
|-----------|-----------|--------|----------------|---------------|
| T1566.001 | Spearphishing Attachment | Initial Access | Yes | Partial |

### Indicator Summary

| Indicator | Type | Score | Context | Confidence |
|-----------|------|-------|---------|------------|

### Recommendations
[Prioritized defensive actions mapped to ATT&CK mitigations]
```

## Reference material

For MITRE ATT&CK technique reference and Admiralty Scale (A1–F6) source-reliability tagging, work from your training; ask the user when a specific technique ID, sub-technique, or campaign name is unclear.
