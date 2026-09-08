# SCF Domains

The Secure Controls Framework organizes ~1,400 controls into 33
domains. The domain id is the OSCAL group `id` (kebab-case) used by
`scf_lookup.lookup_by_domain(...)`. Domain titles are the human-readable
labels from `groups[*].title` in the OSCAL catalog.

Source of truth: the `domains` table in
`~/.local/share/bateam/grc/scf.db`. To dump the live list:

```bash
python agents/grc_mgr/skills/scf-intelligence/scripts/scf_lookup.py domains
```

The 33 known domain prefixes (control-ID stems, not OSCAL ids):

```
AAT  Artificial Intelligence & Autonomous Technologies
AST  Asset Management
BCD  Business Continuity & Disaster Recovery
CAP  Capacity & Performance Planning
CFG  Configuration Management
CHG  Change Management
CLD  Cloud Security
CPL  Compliance
CRY  Cryptographic Protections
DCH  Data Classification & Handling
EDM  Embedded Technology
END  Endpoint Security
GOV  Security, Compliance & Resilience Governance
HRS  Human Resources Security
IAC  Identification & Authentication
IAO  Information Assurance
INC  Incident Response
IRO  Information Resource Oversight
MDM  Mobile Device Management
MON  Monitoring
NET  Network Security
OPS  Operations Security
PES  Physical & Environmental Security
PRI  Privacy
PRJ  Project & Resource Management
PRM  Project Management
RSK  Risk Management
SAT  Security Awareness & Training
SCM  Supply Chain Risk Management
SEA  Secure Engineering & Architecture
TDA  Technology Development & Acquisition
TPM  Third-Party Management
VPM  Vulnerability & Patch Management
WEB  Web Security
```

Notes:
- The OSCAL group `id` is the kebab-case domain name (e.g.,
  `asset-management`), not the three-letter stem (e.g., `AST`).
- Control IDs follow the pattern `<STEM>-<NN>` (e.g., `GOV-01`,
  `AST-02`). Within OSCAL the control `id` field is just `GOV-01` — the
  domain stem is implicit.
- Domains are stable across SCF versions; control IDs are also stable
  but new controls are added and a few are deprecated each release.
