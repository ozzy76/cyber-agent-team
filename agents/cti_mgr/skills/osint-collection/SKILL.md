---
name: osint-collection
description: Collect and process open-source intelligence (OSINT) to support threat assessments, infrastructure reconnaissance, dark web monitoring, and exposure analysis. Use when gathering context on threat actors, investigating exposed assets, monitoring for data leakage, or profiling adversary infrastructure.
metadata:
  nice-work-role: AN-TWA-001
  nice-tasks: T0567, T0574
---

## Overview

Systematically collect intelligence from open and publicly accessible sources to enrich threat assessments and support proactive security decisions. All collection must stay within legal and ethical boundaries — passive collection only; no active exploitation of systems.

## Operations

Use these analytical operations as the conceptual steps of the workflow. They are not callable Python — do not attempt `run_skill_script` or `load_skill_resource` for them. Reason about each step, request the inputs you need from the user, and produce the result directly.

- `search_passive_dns(domain_or_ip)` — query passive DNS history for a domain or IP
- `lookup_shodan(query)` — retrieve internet-exposed asset data and banners from Shodan
- `lookup_greynoise(ip)` — determine if an IP is benign scanner or malicious actor background noise
- `search_paste_sites(keywords)` — monitor paste sites for leaked credentials, source code, or PII
- `lookup_certificate_transparency(domain)` — enumerate subdomains and certificates via CT logs
- `search_threat_actor_infrastructure(actor_name)` — aggregate infrastructure data for a known actor

## Collection source categories

| Category | Sources | Use case |
|----------|---------|----------|
| Network intelligence | Shodan, Censys, Fofa, ZoomEye | Exposed services, banners, certs |
| DNS/IP history | PassiveDNS, SecurityTrails, RiskIQ | Infrastructure tracking, pivoting |
| Noise classification | GreyNoise, Shodan Trends | Separate targeted from background |
| Credential exposure | HaveIBeenPwned, paste sites, breach DBs | Data leakage, credential stuffing risk |
| Certificate transparency | crt.sh, Censys | Subdomain enumeration, cert patterns |
| Dark/deep web | Monitored feeds (via Secret Manager) | Data leakage, actor communications |
| Code repositories | GitHub, GitLab public repos | Accidental credential commits, research |

## Steps

1. **Define collection requirements**
   - State the intelligence question: actor infrastructure? client exposure? leaked credentials?
   - Identify the target: threat actor name, client domain, IP range, keyword, or product name
   - Confirm ethical and legal scope: collection is passive only; never interact with or access target systems

2. **Execute collection**
   - Run the appropriate tool(s) based on the intelligence question
   - For infrastructure pivoting: start with known IOC → passive DNS → related IPs → Shodan banners → certificate data
   - For client exposure: start with domain → CT logs for subdomains → Shodan for exposed services → paste site search for credentials

3. **Validate and filter**
   - Cross-reference results across at least two sources before treating as confirmed
   - Run `lookup_greynoise` on IP addresses to filter background internet scanners from targeted activity
   - Note data freshness — passive DNS and Shodan data can be weeks or months stale

4. **Document findings with provenance**
   - Record the source, collection date, and query used for each data point
   - Apply Admiralty Scale confidence rating
   - Flag any findings that may contain personal data (PII) — handle per applicable privacy regulations

5. **Feed into analysis**
   - Pass infrastructure findings to `adversary-tracking` for actor profile updates
   - Pass exposure findings to the Operations Manager for remediation action
   - Pass credential exposure findings directly to the affected client as a priority alert

## Output format

```
## OSINT Collection: [Target / Intelligence Question]

### Collection Summary
Target: | Date: | Sources used: | Query scope:

### Findings

| Finding | Source | Date collected | Confidence | Action required |
|---------|--------|---------------|------------|-----------------|

### Infrastructure Map (if applicable)
[Domain → IPs → Hosting ASN → Related domains/certificates]

### Exposure Summary (if client-focused)
[Exposed services, leaked credentials, data leakage findings]

### Recommended Actions
[Prioritized by urgency]
```

## Operational security

- Never use client credentials or networks for collection — use dedicated collection infrastructure
- Rotate collection IPs to avoid attribution back to the client or firm
- Log all collection activity with timestamps for legal defensibility
