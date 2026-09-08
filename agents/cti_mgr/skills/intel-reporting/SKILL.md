---
name: intel-reporting
description: Produce finished intelligence products including threat briefings, strategic assessments, and tactical intelligence reports for client and executive audiences. Use when converting raw analysis into a deliverable, preparing a client briefing, drafting a threat advisory, or producing a periodic threat landscape report.
metadata:
  nice-work-role: AN-TWA-001
  nice-tasks: T0588, T0591
---

## Overview

Transform analyzed threat data into polished, audience-appropriate intelligence products that enable informed security decisions. Products range from technical tactical reports (for SOC/engineering teams) to strategic briefings (for CISOs and executives).

## Intelligence product types

| Product | Audience | Cadence | Length |
|---------|----------|---------|--------|
| Threat Advisory | SOC, IR team | Event-driven | 1–3 pages |
| Tactical Intelligence Report | Security engineers | Weekly/event | 3–8 pages |
| Threat Landscape Briefing | CISO, security leadership | Monthly/quarterly | 5–12 pages |
| Executive Threat Summary | C-suite, board | Quarterly | 1–2 pages |
| Vulnerability Intelligence Alert | Patch/ops teams | Event-driven | 1 page |

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `generate_report(report_type, analysis_data, audience, classification)` — produce a structured intelligence product from analysis input
- `format_for_audience(content, audience_level)` — reformat technical content for executive or technical audiences

## Producing the deliverable — write it to a file

A finished intelligence product is a **document, not a chat message**. Anything
longer than a one-pager — a Tactical Intelligence Report or a **Threat Landscape
Briefing (5–12 pages)** — must be written to disk with `write_file`, not dribbled
into the reply. Trying to emit a multi-page product as a single chat turn is the
failure mode that leaves you with an empty or truncated answer.

Workflow when the user asks for a formal product:

1. **Load the full template.** The inline templates below are a skeleton. For the
   Threat Landscape Briefing, pull the complete house-style template first:

   ```
   load_skill_resource(file_path="assets/templates/threat-landscape-briefing.md")
   ```

2. **Write the product to a file.** Fill the template with your analysis and save
   it, e.g. `write_file(path="threat_landscape_briefing.md", content="...")`. Use a
   descriptive, dated filename.

3. **Reply with the BLUF + where you saved it** — a short summary and the file
   path — not the entire document pasted back.

Do not treat `generate_report`, `write_file`, or the template as a reason to stop
at an outline: the deliverable is the finished, saved document.

## Steps

1. **Identify product requirements**
   - Determine the product type, target audience, and classification level
   - Confirm key intelligence questions the product must answer (PIRs: Priority Intelligence Requirements)
   - Establish the scope: single threat actor, CVE, campaign, or landscape overview

2. **Structure the product**
   - Use the appropriate template for the product type (see below)
   - Lead with the key judgment and bottom line up front (BLUF)
   - Support assertions with evidence; caveat confidence levels explicitly
   - Use the Admiralty Scale for source reliability (A–F) and information credibility (1–6)

3. **Write for the audience**
   - **Technical**: include IOCs, ATT&CK IDs, YARA/Sigma rules, specific CVEs, and remediation steps
   - **CISO/leadership**: focus on business impact, risk to specific assets, and strategic recommendations
   - **Executive/board**: 1-page maximum; threat in plain language; link to business outcomes (revenue, regulatory, reputational)

4. **Apply information controls**
   - Mark classification: TLP:RED, TLP:AMBER, TLP:GREEN, or TLP:CLEAR
   - Include handling instructions for shared products
   - Remove or sanitize client-specific details before external sharing

5. **QA and finalize**
   - Verify all ATT&CK IDs, CVEs, and IOCs are accurate
   - Ensure key judgments are clearly separated from assumptions
   - Confirm recommendations are actionable and assigned to a responsible team

## Threat Advisory template

```
## Threat Advisory: [Title]
TLP: AMBER | Date: | Severity: Critical/High/Medium/Low

### BLUF
[2-sentence bottom line: what happened, what it means for the client]

### Key Judgments
- [Judgment 1] (Confidence: High/Medium/Low)
- [Judgment 2] (Confidence: High/Medium/Low)

### Threat Overview
[Narrative: actor, campaign, targeting, TTPs]

### Indicators of Compromise
| Type | Value | Context |

### Recommendations
| Priority | Action | Owner | Timeline |
```

## Threat Landscape Briefing template

```
## Threat Landscape Briefing: [Period / Sector]
TLP: AMBER | Date: | Prepared for: [CISO / Client]

### Executive Summary
### Threat Actor Spotlight
### Emerging TTPs
### Vulnerability Trends
### Sector-Specific Risks
### Recommendations
### Appendix: Supporting Data
```
