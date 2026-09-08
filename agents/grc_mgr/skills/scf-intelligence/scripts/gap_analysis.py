"""Map a client inventory to the SCF and emit a gap report.

Two matching paths, chosen per claim:

  A. Direct path — `claim.framework_slug` set
     Reverse-lookup via scf_lookup.lookup_controls_for_client_locator,
     which applies locator_normalize (HIPAA prefix-expand, NIST/FedRAMP
     zero-pad, CMMC translate, SOC 2 POF expand, GDPR Article prefix,
     PCI DSS sub-requirement expand). Confidence = 1.0.

  B. Semantic path — `claim.framework_slug` is None
     FTS5 keyword match against SCF control title + statement. Top-K
     ranked candidates per claim, confidence proportional to BM25 rank
     (best match higher). Used for Cynomi questionnaire prose.

Aggregation per SCF control: any 'met' claim → met; else any 'partial'
→ partial; else 'missing'. Claims with status 'na' or 'unknown' do not
contribute (they don't strengthen NOR weaken coverage).

Scope expansion: when `scope_framework` is set, the report scopes to
SCF controls mapped to that framework. SCF controls in scope but
un-attached by any claim become missing-by-omission rows so an
auditor sees the *complete* PCI DSS / HIPAA / etc. picture.
"""

from __future__ import annotations

import pathlib
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scf_lookup  # noqa: E402
from ingest_client_data import ClientClaim  # noqa: E402, F401

GapStatus = Literal["met", "partial", "missing"]


class GapRow(TypedDict, total=False):
    control_id: str
    domain_id: str
    title: str
    weight: int | None
    status: GapStatus
    confidence: float
    matched_claim_text: str | None
    matched_claim_ids: list[str]
    match_strategy: str | None
    matched_locators: list[str]


@dataclass
class GapReport:
    scope: str  # "full-scf" or a framework slug
    claims_in: int
    by_status: dict[str, int]
    rows: list[GapRow]
    unmatched_claims: list[ClientClaim] = field(default_factory=list)


# --- internal aggregation helpers ----------------------------------------


def _status_priority(status: str) -> int:
    """Higher value wins when aggregating multiple claims per control."""
    return {"met": 3, "partial": 2, "missing": 1, "na": 0, "unknown": 0}.get(status, 0)


def _aggregate_status(claim_statuses: list[str]) -> GapStatus | None:
    """Take the strongest claim status. Returns None if all were na/unknown."""
    best = max((s for s in claim_statuses), key=_status_priority, default=None)
    if best is None or _status_priority(best) == 0:
        return None
    return best  # type: ignore[return-value]


# --- public API -----------------------------------------------------------


def analyze(
    claims: list[ClientClaim],
    *,
    scope_framework: str | None = None,
    min_confidence: float = 0.3,
    fts_top_k: int = 3,
) -> GapReport:
    """Produce a GapReport over the provided claims.

    Args:
        claims: client inventory from any ingest_client_data path.
        scope_framework: when set, restricts the report to SCF controls
            mapped to this framework slug and adds missing-by-omission
            rows for un-attached scoped controls.
        min_confidence: drop semantic-match candidates below this
            confidence. Direct (framework_slug) matches always count.
        fts_top_k: number of candidate SCF controls returned per
            Cynomi-style prose claim.
    """
    # control_id → aggregated row state
    matches: dict[str, dict] = {}
    unmatched: list[ClientClaim] = []

    for claim in claims:
        slug = claim.get("framework_slug")
        cid_or_text = claim.get("claim_id", "")
        text = claim.get("claim_text", "") or ""
        status = claim.get("status", "unknown")

        attached_any = False

        if slug:
            # Direct path. Status "unknown" still informs scope (we know
            # the client's framework references this control) but does
            # not flip the coverage state.
            res = scf_lookup.lookup_controls_for_client_locator(slug, cid_or_text)
            for ctrl in res["controls"]:
                _attach(
                    matches,
                    ctrl,
                    claim,
                    confidence=1.0,
                    strategy=res["strategy"],
                    matched_locators=res["matched_locators"],
                )
                attached_any = True
        else:
            # Semantic path — skip wholly-unactionable claims to avoid
            # FTS-matching purely metadata text.
            if status in ("na", "unknown") or len(text) < 12:
                continue
            fts = scf_lookup.lookup_by_keyword(text, limit=fts_top_k)
            # BM25 from SQLite is negative; smaller is better. Convert
            # rank index to a coarse confidence so the report can show
            # "high/medium/low" downstream.
            for i, ctrl in enumerate(fts):
                conf = 0.7 - 0.15 * i  # 0.70, 0.55, 0.40, …
                if conf < min_confidence:
                    continue
                _attach(
                    matches,
                    ctrl,
                    claim,
                    confidence=conf,
                    strategy="fts",
                    matched_locators=[],
                )
                attached_any = True

        if not attached_any and status not in ("na", "unknown"):
            unmatched.append(claim)

    # Build rows from aggregated matches.
    rows: list[GapRow] = []
    for cid, agg in matches.items():
        rolled = _aggregate_status([c["status"] for c in agg["claims"]])
        if rolled is None:
            continue
        rows.append(
            GapRow(
                control_id=cid,
                domain_id=agg["domain_id"],
                title=agg["title"],
                weight=agg["weight"],
                status=rolled,
                confidence=max(agg["confidences"]) if agg["confidences"] else 0.0,
                matched_claim_text=agg["claims"][0].get("claim_text"),
                matched_claim_ids=[c.get("claim_id", "") for c in agg["claims"]],
                match_strategy=agg["strategy"],
                matched_locators=agg["matched_locators"],
            )
        )

    # Scope expansion — when a framework scope is set, every SCF
    # control mapped to that framework should appear in the report.
    # In-scope controls without positive coverage evidence (no claim,
    # or only na/unknown claims like a status-less PDF) become
    # missing-by-omission. We preserve any matched_locators we did
    # attach so the reviewer can still see the framework-locator
    # context for an omission.
    if scope_framework:
        in_scope = {r["id"]: r for r in scf_lookup.lookup_by_framework(scope_framework, limit=10000)}
        covered = {r["control_id"] for r in rows}
        for cid, ctrl in in_scope.items():
            if cid in covered:
                continue
            existing = matches.get(cid, {})
            rows.append(
                GapRow(
                    control_id=cid,
                    domain_id=ctrl["domain_id"],
                    title=ctrl["title"],
                    weight=ctrl.get("weight"),
                    status="missing",
                    confidence=1.0,
                    matched_claim_text=None,
                    matched_claim_ids=[c.get("claim_id", "") for c in existing.get("claims", [])],
                    match_strategy="scope-omission" if not existing else "unknown-only",
                    matched_locators=existing.get("matched_locators", []),
                )
            )
        rows = [r for r in rows if r["control_id"] in in_scope]

    by_status: dict[str, int] = defaultdict(int)
    for r in rows:
        by_status[r["status"]] += 1

    rows.sort(key=lambda r: (r["domain_id"], -(r.get("weight") or 0), r["control_id"]))

    return GapReport(
        scope=scope_framework or "full-scf",
        claims_in=len(claims),
        by_status=dict(by_status),
        rows=rows,
        unmatched_claims=unmatched,
    )


def _attach(
    matches: dict[str, dict],
    ctrl: dict,
    claim: ClientClaim,
    *,
    confidence: float,
    strategy: str,
    matched_locators: list[str],
) -> None:
    """Record one (claim → SCF control) match."""
    cid = ctrl["id"]
    entry = matches.setdefault(
        cid,
        {
            "domain_id": ctrl.get("domain_id", ""),
            "title": ctrl.get("title", ""),
            "weight": ctrl.get("weight"),
            "claims": [],
            "confidences": [],
            "strategy": strategy,
            "matched_locators": list(matched_locators),
        },
    )
    entry["claims"].append(claim)
    entry["confidences"].append(confidence)
    # Preserve the strongest strategy tag (direct wins over FTS).
    if entry["strategy"] == "fts" and strategy != "fts":
        entry["strategy"] = strategy
    for loc in matched_locators:
        if loc not in entry["matched_locators"]:
            entry["matched_locators"].append(loc)


# --- markdown rendering ---------------------------------------------------


_STATUS_GLYPH = {"met": "[OK]", "partial": "[~]", "missing": "[X]"}


def format_markdown(report: GapReport, *, max_per_domain: int = 25) -> str:
    """Render a GapReport as the markdown shape described in SKILL.md.

    `max_per_domain` truncates very long domain sections; the count of
    truncated rows is shown.
    """
    lines: list[str] = []
    lines.append("## SCF Gap Report")
    lines.append("")
    lines.append(f"- **Scope:** {report.scope}")
    lines.append(f"- **Claims analyzed:** {report.claims_in}")
    if report.unmatched_claims:
        lines.append(f"- **Unmatched claims (no SCF mapping found):** {len(report.unmatched_claims)}")
    lines.append("")

    lines.append("### Summary")
    lines.append("")
    lines.append("| Status   | Count | Weighted total |")
    lines.append("|----------|------:|---------------:|")
    weighted_totals: dict[str, int] = {"met": 0, "partial": 0, "missing": 0}
    for r in report.rows:
        weighted_totals[r["status"]] += r.get("weight") or 0
    for s in ("met", "partial", "missing"):
        n = report.by_status.get(s, 0)
        w = weighted_totals[s]
        lines.append(f"| {s.title():8s} | {n:>5d} | {w:>14d} |")
    lines.append("")

    priorities = sorted(
        (r for r in report.rows if r["status"] in ("missing", "partial")),
        key=lambda r: (-(r.get("weight") or 0), r["control_id"]),
    )[:10]
    if priorities:
        lines.append("### Top remediation priorities (by SCF weight)")
        lines.append("")
        for i, r in enumerate(priorities, 1):
            w = r.get("weight") if r.get("weight") is not None else "?"
            lines.append(
                f"{i}. **[w={w}] {r['control_id']}** — {r['title']}  "
                f"_({r['status']}, {r.get('match_strategy', '?')})_"
            )
        lines.append("")

    by_domain: dict[str, list[GapRow]] = defaultdict(list)
    for r in report.rows:
        by_domain[r["domain_id"]].append(r)

    lines.append("### By Domain")
    lines.append("")
    for dom_id in sorted(by_domain):
        dom_rows = by_domain[dom_id]
        gaps = sum(1 for r in dom_rows if r["status"] != "met")
        lines.append(f"#### {dom_id}  ({len(dom_rows)} in scope, {gaps} gap{'s' if gaps != 1 else ''})")
        lines.append("")
        for r in dom_rows[:max_per_domain]:
            glyph = _STATUS_GLYPH[r["status"]]
            w = r.get("weight") if r.get("weight") is not None else "?"
            extras = []
            if r["status"] != "missing" or r.get("match_strategy") != "scope-omission":
                if r.get("match_strategy"):
                    extras.append(r["match_strategy"])
                if r.get("matched_locators"):
                    extras.append("locator: " + ", ".join(r["matched_locators"][:3]))
            extra_str = f"  _({'; '.join(extras)})_" if extras else ""
            lines.append(f"- {glyph} **{r['control_id']}** (w={w}) — {r['title']}{extra_str}")
        if len(dom_rows) > max_per_domain:
            lines.append(f"- _... {len(dom_rows) - max_per_domain} more rows_")
        lines.append("")

    if report.unmatched_claims:
        lines.append("### Unmatched claims")
        lines.append("")
        lines.append(
            f"_{len(report.unmatched_claims)} client claims found no SCF mapping. "
            "Likely causes: framework outside SCF coverage, claim too vague for FTS, "
            "or the framework crosswalk omits the cited locator._"
        )
        lines.append("")
        for c in report.unmatched_claims[:10]:
            text = (c.get("claim_text") or "")[:120]
            slug = c.get("framework_slug") or "(no framework)"
            lines.append(f"- `{slug}` :: `{c.get('claim_id')}` — {text}")
        if len(report.unmatched_claims) > 10:
            lines.append(f"- _... {len(report.unmatched_claims) - 10} more_")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Run SCF gap analysis on a claims JSON file.")
    ap.add_argument("claims_json", help="Path to JSON list of ClientClaim records")
    ap.add_argument("--scope", help="Framework slug to scope the analysis", default=None)
    ap.add_argument("--markdown", action="store_true", help="Render markdown report")
    ap.add_argument("--min-confidence", type=float, default=0.3)
    args = ap.parse_args()

    with open(args.claims_json) as fh:
        claims = json.load(fh)
    report = analyze(claims, scope_framework=args.scope, min_confidence=args.min_confidence)
    if args.markdown:
        print(format_markdown(report))
    else:
        print(json.dumps(report.__dict__, indent=2, default=str))
