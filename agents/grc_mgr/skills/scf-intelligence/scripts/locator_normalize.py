"""Normalize client-supplied framework locators to match SCF's canonical form.

Different framework publishers use different conventions for hierarchical
identifiers. The SCF catalog stores one canonical form per framework;
clients (and Cynomi reports, framework-status CSVs, free-text) often
write a different form. Without normalization, exact-match lookups miss.

Examples we've seen empirically against scf.db:

  HIPAA Security Rule
    SCF stores: 164.308(a)(1)(i), 164.308(a)(1)(ii)(A), ...
    Client writes: 164.308(a)(1)        (parent rule)
    Strategy: prefix-expand

  NIST 800-53 R5 / FedRAMP R5 baselines / NIST CSF 2.0
    SCF stores: AC-02, AC-02(01), DE.AE-02
    Client writes: AC-2, AC-2(1), DE.AE-2
    Strategy: zero-pad single-digit numbers

  CMMC 2.0 Level 2
    SCF stores: ACL2.-3.1.1
    Client writes: AC.L2-3.1.1           (official CMMC 2.0 format)
    Strategy: translate (drop dot, insert '.-' before NIST ref)

  CMMC 2.0 Level 3
    SCF stores: AC.L3-3.1.2E
    Client writes: AC.L3-3.1.2e
    Strategy: uppercase E suffix

  AICPA TSC 2017:2022 (SOC 2)
    SCF stores: CC1.1, CC1.1-POF1, CC1.1-POF2, ...   (POF = Point of Focus)
    Client writes: CC1.1
    Strategy: expand to include all POFs

  EU GDPR
    SCF stores: Article 24.2
    Client writes: Art. 24.2  |  Article 24(2)  |  24.2
    Strategy: prepend 'Article ' if missing

  PCI DSS 4.0.1
    SCF stores: 1.1, 1.1.1, 1.1.2, 12.1, 12.1.1, ...
    Client writes (per Cynomi readiness): 1.1, 12.1, A1.1  (top-level)
    Strategy: exact + prefix-expand for sub-requirements

The module is pure — no DB access. It emits exact-match candidates and
SQL LIKE patterns; the caller (typically scf_lookup.lookup_controls_for_
client_locator) executes the actual query.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NormalizedLocator:
    """Result of normalize(slug, client_locator).

    Attributes:
        framework_slug: The framework slug as passed in.
        original: The client's input, unchanged.
        exact: Locators to query with `f.locator = ?`. Always includes
            `original` plus any transformed form (e.g., zero-padded).
        like_patterns: SQL LIKE patterns for prefix / wildcard match.
            Used for HIPAA prefix-expand and SOC 2 POF expansion.
        strategy: Diagnostic tag — e.g., "exact", "zero-padded",
            "prefix-expand", "cmmc-l2-translate", "pof-expand",
            "gdpr-article-prepend".
        notes: Short human explanation of what was transformed; shown
            in gap reports so reviewers know why a match landed.
    """

    framework_slug: str
    original: str
    exact: tuple[str, ...] = field(default_factory=tuple)
    like_patterns: tuple[str, ...] = field(default_factory=tuple)
    strategy: str = "exact"
    notes: str | None = None


# ---- Per-family normalizers ----------------------------------------------

# Single digit after `-`, NOT followed by another digit (so we don't
# eat the leading digit of a two-digit number).
_NIST_DASH_DIGIT = re.compile(r"-(\d)(?!\d)")
# Single digit between parens — used for control enhancements like (1)→(01).
_NIST_PAREN_DIGIT = re.compile(r"\((\d)\)")


def _zero_pad_nist(s: str) -> str:
    """AC-2 → AC-02, AC-2(1) → AC-02(01), DE.AE-2 → DE.AE-02."""
    s = _NIST_DASH_DIGIT.sub(lambda m: f"-0{m.group(1)}", s)
    s = _NIST_PAREN_DIGIT.sub(lambda m: f"(0{m.group(1)})", s)
    return s


def _normalize_nist_family(slug: str, original: str) -> NormalizedLocator:
    padded = _zero_pad_nist(original)
    if padded == original:
        return NormalizedLocator(slug, original, exact=(original,), strategy="exact")
    return NormalizedLocator(
        slug,
        original,
        exact=(padded, original),
        strategy="zero-padded",
        notes=f"NIST-style zero-padded: {original!r} → {padded!r}",
    )


def _normalize_hipaa(slug: str, original: str) -> NormalizedLocator:
    """Always exact + prefix-expand for HIPAA.

    HIPAA sub-rules nest by parens: 164.308(a)(1) is the parent of
    164.308(a)(1)(i), 164.308(a)(1)(ii)(A), etc. Clients typically
    cite the parent and expect all descendants to count. Adding the
    prefix patterns is harmless when the input is already a leaf —
    the extra patterns just match nothing.
    """
    return NormalizedLocator(
        slug,
        original,
        exact=(original,),
        like_patterns=(f"{original}(%", f"{original}.%"),
        strategy="prefix-expand",
        notes=f"HIPAA parent→child expansion: {original!r} also matches sub-rules",
    )


_CMMC_L2_CLIENT = re.compile(r"^([A-Z]+)\.L2-(.+)$")
_CMMC_L3_LOWERCASE_E = re.compile(r"^([A-Z]+\.L3-.+?)e$")


def _normalize_cmmc(slug: str, original: str) -> NormalizedLocator:
    # L2: AC.L2-3.1.1 → ACL2.-3.1.1
    m = _CMMC_L2_CLIENT.match(original)
    if m:
        translated = f"{m.group(1)}L2.-{m.group(2)}"
        return NormalizedLocator(
            slug,
            original,
            exact=(translated, original),
            strategy="cmmc-l2-translate",
            notes=f"CMMC L2 client→SCF: {original!r} → {translated!r}",
        )
    # L3: AC.L3-3.1.2e → AC.L3-3.1.2E
    m = _CMMC_L3_LOWERCASE_E.match(original)
    if m:
        upper = f"{m.group(1)}E"
        return NormalizedLocator(
            slug,
            original,
            exact=(upper, original),
            strategy="cmmc-l3-uppercase",
            notes=f"CMMC L3 uppercase E suffix: {original!r} → {upper!r}",
        )
    # L1 uses Roman-numeral form (AC.L1-B.1.VII) — no auto-translation
    # from decimal NIST 800-171 refs without a lookup table. Pass through.
    return NormalizedLocator(slug, original, exact=(original,), strategy="exact")


def _normalize_aicpa_tsc(slug: str, original: str) -> NormalizedLocator:
    """SOC 2 / AICPA TSC: include Points of Focus alongside the criterion.

    A client asserting they meet CC1.1 generally means they meet the
    criterion *and* its POFs. Surface both.
    """
    # If the client already specified a POF (e.g., CC1.1-POF3), exact only.
    if "-POF" in original:
        return NormalizedLocator(slug, original, exact=(original,), strategy="exact")
    return NormalizedLocator(
        slug,
        original,
        exact=(original,),
        like_patterns=(f"{original}-POF%",),
        strategy="pof-expand",
        notes=f"AICPA TSC: also matching {original}-POF* (Points of Focus)",
    )


_GDPR_ARTICLE_PREFIXED = re.compile(r"^[Aa]rt(?:icle)?\.?\s+", re.UNICODE)


def _normalize_gdpr(slug: str, original: str) -> NormalizedLocator:
    """SCF stores 'Article 24.2'; client may write 'Art. 24.2' or '24.2'."""
    if original.startswith("Article "):
        return NormalizedLocator(slug, original, exact=(original,), strategy="exact")
    # Strip any 'Art.' / 'Art ' / 'article ' prefix variants, then prepend canonical.
    body = _GDPR_ARTICLE_PREFIXED.sub("", original).strip()
    canonical = f"Article {body}"
    if canonical == original:
        return NormalizedLocator(slug, original, exact=(original,), strategy="exact")
    return NormalizedLocator(
        slug,
        original,
        exact=(canonical, original),
        strategy="gdpr-article-prepend",
        notes=f"GDPR canonical: {original!r} → {canonical!r}",
    )


def _normalize_pci_dss(slug: str, original: str) -> NormalizedLocator:
    """PCI DSS clients (Cynomi readiness) use top-level requirements.

    `12.1` should match the requirement AND all sub-requirements
    (`12.1.1`, `12.1.2`, …). Cynomi readiness reports stop at the
    second level; SCF stores down to the fourth (e.g., `12.10.4.1`).
    """
    return NormalizedLocator(
        slug,
        original,
        exact=(original,),
        like_patterns=(f"{original}.%",),
        strategy="prefix-expand",
        notes=f"PCI DSS: {original!r} also matches sub-requirements",
    )


# ---- Dispatch ------------------------------------------------------------

# Slugs that follow the NIST 800-53 / NIST CSF 2.0 zero-padded convention.
_NIST_FAMILY_SLUGS: set[str] = {
    "nist-csf-2-0",
    "nist-800-53-r4",
    "nist-800-53-r5",
    "nist-800-53b-r5-low",
    "nist-800-53b-r5-moderate",
    "nist-800-53b-r5-high",
    "nist-800-53b-r5-privacy",
    "us-fedramp-r5-low",
    "us-fedramp-r5-moderate",
    "us-fedramp-r5-high",
    "us-fedramp-r5-li-saas",
}


def normalize(framework_slug: str, client_locator: str) -> NormalizedLocator:
    """Per-framework dispatch. Unknown frameworks fall through to exact match.

    The dispatch is by slug (not regex on locator content) so the
    behavior is deterministic for each framework — a `1.1` against
    PCI DSS does prefix-expand, the same `1.1` against an unknown
    framework does exact match only.
    """
    s = client_locator.strip()
    if not s:
        return NormalizedLocator(framework_slug, client_locator, exact=(), strategy="empty")

    if framework_slug in _NIST_FAMILY_SLUGS:
        return _normalize_nist_family(framework_slug, s)
    if framework_slug.startswith("us-hipaa-"):
        return _normalize_hipaa(framework_slug, s)
    if framework_slug.startswith("us-cmmc-"):
        return _normalize_cmmc(framework_slug, s)
    if framework_slug == "aicpa-tsc-2017-2022-used-for-soc-2":
        return _normalize_aicpa_tsc(framework_slug, s)
    if framework_slug == "emea-eu-gdpr":
        return _normalize_gdpr(framework_slug, s)
    if framework_slug.startswith("pci-dss-"):
        return _normalize_pci_dss(framework_slug, s)

    return NormalizedLocator(framework_slug, client_locator, exact=(s,), strategy="exact")


def build_where_clause(norm: NormalizedLocator) -> tuple[str, list[str]]:
    """Build a (sql_fragment, params) pair for use after `f.framework_slug = ?`.

    Returns a fragment like `(f.locator = ? OR f.locator = ? OR f.locator LIKE ?)`
    and the parameter list in the same order. Callers JOIN this onto
    their own query.

    Empty NormalizedLocator (no exact + no patterns) yields a no-op
    clause that matches nothing (`1=0`).
    """
    parts: list[str] = []
    params: list[str] = []
    for e in norm.exact:
        parts.append("f.locator = ?")
        params.append(e)
    for p in norm.like_patterns:
        parts.append("f.locator LIKE ?")
        params.append(p)
    if not parts:
        return "(1=0)", []
    return "(" + " OR ".join(parts) + ")", params


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(
        description="Show how a client locator normalizes for a given SCF framework slug."
    )
    ap.add_argument("framework_slug")
    ap.add_argument("client_locator")
    args = ap.parse_args()
    norm = normalize(args.framework_slug, args.client_locator)
    print(json.dumps(
        {
            "framework_slug": norm.framework_slug,
            "original": norm.original,
            "exact": list(norm.exact),
            "like_patterns": list(norm.like_patterns),
            "strategy": norm.strategy,
            "notes": norm.notes,
        },
        indent=2,
    ))
