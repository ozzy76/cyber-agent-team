---
name: scf-intelligence
description: >
  Natural-language Q&A and gap analysis over the Secure Controls Framework
  (SCF) catalog. Loads the SCF OSCAL JSON into a local SQLite database
  (1,468 controls across 33 domains, framework crosswalks, assessment
  objectives, SCF risk weights). Use when the user asks about a specific
  SCF control ID (GOV-03, AST-01, etc.), wants to know which SCF controls
  satisfy a framework requirement (HIPAA, PCI DSS, ISO 27001, NIST CSF,
  SOC 2, GDPR, FedRAMP), needs a gap report against a client control
  inventory (Cynomi questionnaire CSV, framework-status CSV/XLSX, or
  free-text), or wants risk-weighted remediation prioritization. Cites
  every SCF control ID in responses. All client data stays on-device.
metadata:
  version: "0.1.0"
  source_catalog: scf-full-2026.1 + scf-spreadsheet-2026.1.1
  source_format: full-scf + xlsx-augmentation
  scf_version: "2026.1.1"
  domains: 33
  controls: 1468
  framework_mappings: "~108k (XLSX-augmented)"
  frameworks_covered: 249
  db_default: ~/.local/share/bateam/grc/scf.db
  env_overrides:
    - BATEAM_SCF_DB
    - BATEAM_SCF_JSON
    - BATEAM_SCF_XLSX
  model_routing: local
  inputs_supported:
    - cynomi_questionnaire_csv
    - framework_status_csv
    - framework_status_xlsx
    - free_text
  downstream_skills:
    - risk-assessment
    - compliance-monitoring
    - thirdparty-audit
---

## Overview

The Secure Controls Framework (SCF) is a free metaframework mapping
~1,400 unified controls to global laws, regulations, and standards.
This skill turns the **full SCF JSON release** (NOT the OSCAL export —
see "Source catalog choice" below) into a queryable local SQLite store
so the agent can:

- Answer "what is GOV-03?" with the control statement, assessment
  objectives, weight, evidence references, and framework crosswalks.
- Answer "which SCF controls satisfy PCI DSS 4.0.1 §1.1?" via direct
  reverse-lookup on the framework crosswalk table.
- Produce a gap report from a client control inventory (Cynomi
  questionnaire, framework-status CSV/XLSX, or free text).
- Rank gaps by SCF risk weight to drive remediation priorities.

The full JSON is ~13 MB — too large for any model context. The
preprocess step normalizes it into SQLite once; runtime tools query the
DB and return ≤5,000 tokens per response.

## Source catalogs (two-pass ingest)

SCF publishes the same control set in three formats; we use two of
them in a layered build because each carries different data:

| Aspect | OSCAL release | Full JSON | **Spreadsheet (Authoritative)** |
|---|---|---|---|
| Size | 30 MB | 13 MB | 3.6 MB |
| Controls / domains / AOs | 1,468 / 33 / 5,776 | same | same |
| External framework crosswalks | 0 | 25k across 67 | **108k+ across 249** |
| Evidence references (E-*) | absent | 446 controls | same |
| Risk threats | unstructured | `(category, value)` | as JSON |
| Maturity criteria (SCR-CMM 0-5) | absent | absent | **populated for ~all controls** |
| Framework metadata (geo, publisher, URL) | absent | absent | **Authoritative Sources sheet** |
| Parse speed | fast | fast | slow (~30 s) |

Build order: **JSON first, then XLSX augmentation.**

```bash
# Step 1 — base catalog (controls, AOs, risk threats, evidence refs)
BATEAM_SCF_JSON=path/to/scf-full-2026.1.json \
    python scripts/preprocess_scf.py

# Step 2 — phase 1.5 augmentation (full framework coverage,
#          maturity criteria, framework metadata)
BATEAM_SCF_XLSX=path/to/scf-2026-1-1.xlsx \
    python scripts/augment_from_spreadsheet.py
```

The augmenter is idempotent. It wipes and rebuilds the tables it owns
(`control_frameworks`, `framework_metadata`, `maturity_criteria`) and
does not touch JSON-owned tables.

## Framework coverage (after XLSX augmentation)

249 frameworks across these regions:

| Geography | Frameworks |
|---|---:|
| General (cross-jurisdiction) | 91 |
| US (federal + state) | 68 |
| EMEA | 51 |
| APAC | 29 |
| Americas | 11 |

The previously-missing frameworks the PRD called out are all now
covered:

| Framework | Slug | Controls |
|---|---|---:|
| HIPAA Admin Simplification | `us-hipaa-administrative-simplification-2013` | 170 |
| HIPAA Security Rule | `us-hipaa-security-rule-nist-sp-800-66-r2` | 136 |
| SOC 2 (AICPA TSC) | `aicpa-tsc-2017-2022-used-for-soc-2` | 412 |
| GDPR (EU) | `emea-eu-gdpr` | 42 |
| CCPA / CPRA (CA) | `us-ca-ccpa-2025` | 258 |
| CMMC 2.0 Level 1 / 2 / 3 | `us-cmmc-2-0-level-{1,2,3}` | 52 / 198 / 55 |
| FedRAMP R5 Low / Mod / High / LI-SaaS | `us-fedramp-r5-{low,moderate,high,li-saas}` | 383 / 491 / 561 / 383 |
| PCI DSS 4.0.1 (+ 9 SAQs) | `pci-dss-4-0-1*` | covered |
| NIST CSF 2.0 | `nist-csf-2-0` | covered |
| ISO 27001/2/17/18/701 | `iso-27001-2022`, etc. | covered |
| CIS CSC 8.1 (+ IG1/2/3) | `cis-csc-8-1*` | covered |

Call `scf_lookup.framework_slugs()` for the live list.

## Authoritative Sources metadata

`framework_metadata` carries the Authoritative Sources sheet content:
geography, publisher, full title, public URL, and STRM URL (the
externally hosted Set Theory Relationship Mapping file SCF publishes
for each crosswalk). Use `scf_lookup.framework_info(slug)` to surface
"who maintains this framework, where can I read the spec" alongside a
gap report.

## Tools

These are real Python entry points under `scripts/`. Invoke via
`run_skill_script` for one-shot operations (preprocess, gap report) and
via ADK FunctionTool for conversational lookups (control Q&A).

| Script | Purpose | Phase |
|---|---|---|
| `preprocess_scf.py` | One-shot: parse full-SCF JSON → SQLite base (controls, AOs, evidence refs, risk threats). | setup |
| `augment_from_spreadsheet.py` | One-shot (after preprocess): adds 249-framework crosswalk coverage, SCR-CMM 0-5 maturity criteria, and Authoritative Sources metadata. | setup |
| `scf_lookup.py` | Runtime: lookup by control ID, domain, framework, framework-locator (reverse exact or client-normalized), or FTS5 keyword. Also `framework_info()` for Authoritative-Sources metadata. | per-query |
| `locator_normalize.py` | Pure transform: client framework-native ID → SCF-canonical candidates + LIKE patterns. Handles HIPAA prefix-expand, NIST/FedRAMP/CSF zero-padding, CMMC L2 translation + L3 case fix, SOC 2 POF expansion, GDPR article-prefix normalization, PCI DSS sub-requirement expansion. | per-query (helper) |
| `gap_analysis.py` | Map client inventory → SCF; emit gap report grouped by domain. | per-engagement |
| `risk_score.py` | Aggregate SCF weights + maturity across a control set or gap report. | per-engagement |
| `ingest_client_data.py` | Normalize Cynomi CSV / framework-status CSV / XLSX into a common inventory shape. | per-engagement |

### Client-locator lookup

For framework-status report ingest (Cynomi PCI DSS readiness,
NIST CSF self-assessment, etc.), use `lookup_controls_for_client_locator(
slug, client_locator)` instead of the exact-match
`lookup_controls_for_framework_locator`. The client variant runs the
input through `locator_normalize.normalize()` first so HIPAA parent
rules expand to children, `AC-2` matches `AC-02`, `AC.L2-3.1.1`
translates to `ACL2.-3.1.1`, etc.

The return shape includes `strategy` and `notes` fields — show those
in the gap report so reviewers can audit *why* a control attached to
a given client claim.

## Storage

- Default DB path: `~/.local/share/bateam/grc/scf.db` (override with
  `BATEAM_SCF_DB`).
- Default source JSON: `$BATEAM_SCF_JSON` (no in-repo default — the
  13 MB catalog is not committed).
- Phase 2: swap SQLite for MongoDB Atlas without changing skill code —
  the lookup module exposes a single `Backend` interface.

## Steps

### Control Q&A

1. Identify whether the query is a control ID (e.g., `GOV-03`), a
   framework reference (e.g., "HIPAA access control"), a domain (e.g.,
   "asset management"), or a free-text concept.
2. Call `scf_lookup` with the appropriate mode: `id`, `framework`,
   `domain`, or `keyword`.
3. Cite the SCF control ID(s) returned. Include statement, top 3
   assessment objectives, weight, and matched framework crosswalks.
4. If the query matched nothing, say so plainly; do not invent control
   IDs.

### Gap analysis

1. Identify the input shape: Cynomi questionnaire CSV, framework-status
   CSV/XLSX, or free text.
2. Call `ingest_client_data` to normalize the input into a list of
   `{claim_id, claim_text, status}` records.
3. Call `gap_analysis` with the inventory and an optional framework
   scope ("only show me PCI DSS 4.0.1 gaps").
4. Output the gap report:
   - **Missing**: SCF controls in scope with no matching client claim
   - **Partial**: client status is `Partially` or equivalent
   - **Met**: client status is `Implemented` / `Yes`
5. Group by SCF domain. Rank within each domain by SCF weight.

### Evidence guidance

1. For each control of interest, call `scf_lookup id=<CTRL> --include
   assessment_objectives`.
2. Surface AOs as the evidence checklist; each AO maps to a specific
   piece of evidence the auditor will request.

### Risk scoring

1. Run gap analysis to get the set of missing / partial controls.
2. Call `risk_score` over that set — returns weighted total, breakdown
   by domain, and a top-N priority list.

## Output format

```
## SCF Control Lookup: <Query>

### Control
| ID | Title | Domain | Weight |
|----|-------|--------|--------|
| GOV-03 | … | Governance | 8 |

### Statement
…

### Assessment Objectives (top 3 of N)
- GOV-03_A01 — …
- GOV-03_A02 — …
- GOV-03_A03 — …

### Framework Crosswalks
- HIPAA: 164.308(a)(1)(i)
- PCI DSS 4.0.1: 12.1
- ISO 27001:2022: 5.1
```

```
## SCF Gap Report: <Client>  (Scope: <Framework or "Full SCF">)

### Summary
| Status        | Count | Weighted total |
|---------------|------:|---------------:|
| Met           |    23 |            187 |
| Partial       |    12 |            104 |
| Missing       |    41 |            498 |

### Top remediation priorities (by SCF weight)
1. [Weight 10] GOV-01 — Security, Compliance & Resilience Program
2. [Weight 9]  AST-02 — Asset Inventory
…

### By Domain
#### Governance, Compliance & Resilience  (12 controls in scope, 8 gaps)
- ❌ GOV-01 — …
- ⚠️  GOV-03 — Partially: …
- ✅ GOV-05 — Met
…
```

## References

- `references/scf-domains.md` — 33 SCF domain codes and titles.
- `references/scf-frameworks.md` — Framework slugs that appear in the
  OSCAL `risk-threat.*` crosswalk namespace.

## Authority and safety

- The SCF catalog is the **authoritative** source — never paraphrase a
  control statement from training data. Always quote from `scf_lookup`.
- Client compliance data must not leave the device during Phase 1. All
  ingest is local; lookup tools query local SQLite only.
- Include the SCF catalog version (from `catalog_meta`) in every
  audit-bound response.
