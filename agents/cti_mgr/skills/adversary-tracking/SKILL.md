---
name: adversary-tracking
description: Track threat actor groups, their campaigns, infrastructure, and evolving TTPs over time. Use when building or updating a threat actor profile, monitoring for new activity from a known group, correlating infrastructure across campaigns, or supporting attribution analysis.
metadata:
  nice-work-role: AN-TWA-001
  nice-tasks: T0573, T0574, T0641
---

## Overview

Maintain persistent tracking of threat actors and campaigns relevant to the client's sector, continuously updating profiles as new intelligence emerges. Supports proactive defense and informed incident attribution.

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `get_actor_profile(actor_name)` — retrieve current profile for a named threat actor from Chronicle and configured intel feeds
- `correlate_infrastructure(indicators)` — identify shared infrastructure, hosting patterns, or tooling across campaigns
- `query_threat_feeds(actor_name, since_date)` — pull recent activity for a tracked actor from TAXII/STIX feeds
- `update_actor_profile(actor_name, new_intelligence)` — persist updated actor intelligence to the tracking store

## Steps

1. **Identify the actor or campaign to track**
   - Confirm naming convention: use primary vendor name + aliases (e.g., APT29 / Cozy Bear / Midnight Blizzard)
   - Retrieve the existing profile via `get_actor_profile` if one exists

2. **Collect current intelligence**
   - Run `query_threat_feeds` to pull recent activity from configured STIX/TAXII sources
   - Search Chronicle for related IOCs and behaviors in client telemetry if available
   - Review public reporting from vendor intelligence teams

3. **Build or update the actor profile**
   - Update motivation, attribution confidence, and targeted sectors
   - Refresh TTP list: map current techniques to MITRE ATT&CK, noting any new or deprecated techniques
   - Document known tooling (malware families, exploits, post-exploitation frameworks)
   - Record infrastructure characteristics: hosting providers, TLD patterns, certificate patterns

4. **Correlate across campaigns**
   - Run `correlate_infrastructure` on new IOCs to identify overlaps with prior campaigns
   - Note shared malware code, infrastructure reuse, or operational security patterns
   - Assess whether new activity represents the same cluster or a new sub-group

5. **Assess relevance to clients**
   - Map actor's targeting criteria against each relevant client: sector, geography, technology stack
   - Flag clients at elevated risk and recommend proactive hunts or control validation

6. **Persist and disseminate**
   - Run `update_actor_profile` to commit new intelligence
   - Produce a threat actor update via the `intel-reporting` skill if activity warrants client notification

## Actor profile structure

```
## Threat Actor Profile: [Name]

### Identity
Primary name: | Aliases: | Attribution: [Nation-state / Criminal / Hacktivist / Unknown]
Attributed to: | Confidence: High/Medium/Low | First observed:

### Targeting
Sectors: | Geographies: | Motivation: [Espionage / Financial / Disruption / Ideology]

### TTPs (Current)
| ATT&CK ID | Technique | Tactic | Tool/Variant | Last observed |
|-----------|-----------|--------|--------------|---------------|

### Tooling
| Tool | Type | Notes |

### Infrastructure Patterns
[Hosting ASNs, TLD patterns, certificate characteristics, IP ranges]

### Recent Activity
[Chronological log of observed campaigns and incidents]

### Client Relevance
| Client | Risk Level | Rationale | Recommended Action |
```

## Reference material

When the user asks for actor naming convention cross-reference (Mandiant APT## ↔ Microsoft ↔ CrowdStrike) or STIX/TAXII feed configuration, draw on your training and ask the user for any specifics you cannot infer.
