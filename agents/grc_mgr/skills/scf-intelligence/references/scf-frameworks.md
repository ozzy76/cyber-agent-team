# SCF Framework Crosswalks

The SCF full-catalog JSON carries every external framework mapping
under each control's `frameworkMappings[]` array:

```json
{
  "framework": "PCI DSS\r\n4.0.1",
  "ids": ["1.1", "1.1.1", "12.1"]
}
```

Framework names in the source contain literal `\r\n` (the source was an
Excel spreadsheet with multi-line column headers). We normalize to
single spaces for `framework_name` and slugify for `framework_slug` at
preprocess time.

To dump the live list of slugs known to the current SCF version:

```bash
python agents/grc_mgr/skills/scf-intelligence/scripts/scf_lookup.py frameworks
```

## Coverage in SCF 2026.1 (67 frameworks)

### PCI DSS (your KITY engagement uses these)

- `pci-dss-4-0-1` — full PCI DSS 4.0.1
- `pci-dss-4-0-1-saq-a`
- `pci-dss-4-0-1-saq-a-ep`
- `pci-dss-4-0-1-saq-b`
- `pci-dss-4-0-1-saq-b-ip`
- `pci-dss-4-0-1-saq-c`
- `pci-dss-4-0-1-saq-c-vt`
- `pci-dss-4-0-1-saq-d-merchant`
- `pci-dss-4-0-1-saq-d-service-provider`
- `pci-dss-4-0-1-saq-p2pe`

### NIST

- `nist-csf-2-0`
- `nist-csf-function-grouping` (Govern / Identify / Protect / Detect / Respond / Recover)
- `nist-800-53-r5`, `nist-800-53-r4`
- `nist-800-53b-r5-high`, `nist-800-53b-r5-moderate`, `nist-800-53b-r5-low`, `nist-800-53b-r5-privacy`
- `nist-800-171-r3`, `nist-800-171-r2`
- `nist-800-171a`, `nist-800-171a-r3`
- `nist-800-172`
- `nist-800-37-r2`
- `nist-800-39`
- `nist-800-66-r2`
- `nist-800-82-r3` (with HIGH / MODERATE / LOW OT overlays)
- `nist-800-160-vol2-r1`
- `nist-800-161-r1` (with C-SCRM Baseline, Flow Down, Level 1/2/3)
- `nist-800-207` (zero trust)
- `nist-800-218` (SSDF)
- `nist-ai-100-1-ai-rmf-1-0`, `nist-ai-600-1`
- `nist-privacy-framework-1-0`

### ISO / IEC

- `iso-27001-2022`, `iso-27002-2022`
- `iso-27017-2015`, `iso-27018-2025`, `iso-27701-2025`
- `iso-22301-2019` (BCMS)
- `iso-29100-2024` (privacy framework)
- `iso-31000-2018`, `iso-31010-2009` (risk management)
- `iso-42001-2023` (AI management)
- `iso-sae-21434-2021` (automotive)
- `iec-62443-2-1-2024`, `iec-62443-3-3-2013`, `iec-62443-4-1-2018`, `iec-62443-4-2-2019`
- `iec-tr-60601-4-5-2021` (medical device)

### CIS Critical Security Controls

- `cis-csc-8-1`
- `cis-csc-8-1-ig1` (Implementation Group 1 — small org baseline)
- `cis-csc-8-1-ig2` (mid-tier)
- `cis-csc-8-1-ig3` (mature)

### Other

- `cobit-2019`
- `coso-2013`
- `csa-ccm-4-1-0` (Cloud Controls Matrix)
- `csa-iot-scf-2`
- `owasp-top-10-2025`

## Filled by Phase 1.5 spreadsheet augmentation

After running `augment_from_spreadsheet.py`, all of these are populated:

| Framework | Slug | Notes |
|---|---|---|
| HIPAA Admin Simplification | `us-hipaa-administrative-simplification-2013` | 170 controls |
| HIPAA Security Rule | `us-hipaa-security-rule-nist-sp-800-66-r2` | 136 controls, mapped via NIST SP 800-66 R2 |
| SOC 2 (AICPA TSC 2017:2022) | `aicpa-tsc-2017-2022-used-for-soc-2` | 412 controls — header literally says "(used for SOC 2)" |
| GDPR | `emea-eu-gdpr` | 42 controls, locators are `Article 24.2`-style |
| CCPA / CPRA | `us-ca-ccpa-2025` | 258 controls, locators are CFR section style (e.g., `7123(b)(1)`) |
| CMMC 2.0 Level 1 | `us-cmmc-2-0-level-1` | 52 controls |
| CMMC 2.0 Level 1 AOs | `us-cmmc-2-0-level-1-aos` | 16 controls (assessment-objective variant) |
| CMMC 2.0 Level 2 | `us-cmmc-2-0-level-2` | 198 controls |
| CMMC 2.0 Level 3 | `us-cmmc-2-0-level-3` | 55 controls |
| FedRAMP R5 Low | `us-fedramp-r5-low` | 383 controls |
| FedRAMP R5 Moderate | `us-fedramp-r5-moderate` | 491 controls |
| FedRAMP R5 High | `us-fedramp-r5-high` | 561 controls |
| FedRAMP R5 LI-SaaS | `us-fedramp-r5-li-saas` | 383 controls |
| AICPA Privacy Mgmt Framework | `aicpa-privacy-management-framework-pmf` | populated |
| APEC Privacy Framework | `apec-privacy-framework-2015` | populated |
| ...plus 230+ more | run `scf_lookup.framework_slugs()` for the live list |

## Still NOT in any SCF release

These show up in client conversations but appear in neither the JSON
nor the spreadsheet:

- **SOX** (Sarbanes-Oxley) — SCF treats SOX coverage as derived via
  COBIT 2019 + AICPA TSC 2017 mappings; no direct SOX-section column.
- **PIPEDA** (Canada) — present in Authoritative Sources but coverage
  varies by version.
- Newer / niche state privacy laws (Colorado CPA, Virginia VCDPA, etc.)
  may not be individually mapped.

When a client asks about a framework not in `framework_slugs()`:

1. Check `framework_slugs()` for an adjacent framework (e.g., SOX →
   COBIT 2019; FERPA → NIST 800-53B Privacy baseline).
2. Never invent a mapping from training data — flag the gap explicitly.

## Lookup patterns

### Forward lookup — controls for a framework

```python
from scf_lookup import lookup_by_framework
lookup_by_framework("pci-dss-4-0-1")
# → [{"id": "GOV-01", "title": "...", "weight": 10,
#     "locators": "12.1; 12.1.1; 12.1.2"}, ...]
```

### Reverse lookup — given a framework-native ID, find the SCF controls

```python
from scf_lookup import lookup_controls_for_framework_locator
lookup_controls_for_framework_locator("pci-dss-4-0-1", "1.1")
# → [{"id": "NET-01", "title": "...", "statement": "...", "weight": 9}, ...]
```

This is the direct path for ingesting a Cynomi framework-status report
(no semantic matching needed when the input already carries
framework-native IDs).
