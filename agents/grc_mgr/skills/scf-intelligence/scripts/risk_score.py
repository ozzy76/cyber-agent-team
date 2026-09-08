"""Aggregate SCF risk weights and maturity over a control set or gap report.

Weights live on `controls.weight` (integer 0..10 in SCF 2026.1).
Maturity criteria (SCR-CMM Level 0..5) live in `maturity_criteria`
after augment_from_spreadsheet.py runs — surfaced via scf_lookup
when querying a control, used here only for completeness checks.
"""

from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scf_lookup  # noqa: E402, F401  (sibling script — see sys.path injection)
from gap_analysis import GapReport  # noqa: E402

DEFAULT_DB = pathlib.Path("~/.local/share/bateam/grc/scf.db").expanduser()


def _db_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("BATEAM_SCF_DB", str(DEFAULT_DB))).expanduser()


class DomainRisk(TypedDict):
    domain_id: str
    weight_missing: int
    weight_partial: int
    weight_met: int
    weight_total: int


@dataclass
class RiskSummary:
    total_weight_missing: int
    total_weight_partial: int
    total_weight_met: int
    by_domain: list[DomainRisk]
    top_priorities: list[dict] = field(default_factory=list)


def score_gap_report(report: GapReport, *, top_n: int = 10) -> RiskSummary:
    """Aggregate a gap report into a domain roll-up + top-N priority list.

    Top-N picks the highest-weight missing or partial controls — that's
    where remediation budget produces the most risk reduction per
    control.
    """
    domain_buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"missing": 0, "partial": 0, "met": 0}
    )
    totals = {"missing": 0, "partial": 0, "met": 0}

    for r in report.rows:
        w = r.get("weight") or 0
        status = r["status"]
        domain_buckets[r["domain_id"]][status] += w
        totals[status] += w

    by_domain: list[DomainRisk] = []
    for dom_id, buckets in domain_buckets.items():
        by_domain.append(
            DomainRisk(
                domain_id=dom_id,
                weight_missing=buckets["missing"],
                weight_partial=buckets["partial"],
                weight_met=buckets["met"],
                weight_total=buckets["missing"] + buckets["partial"] + buckets["met"],
            )
        )
    # Sort: highest open-risk first.
    by_domain.sort(key=lambda d: -(d["weight_missing"] + d["weight_partial"]))

    priorities = sorted(
        (r for r in report.rows if r["status"] in ("missing", "partial")),
        key=lambda r: (-(r.get("weight") or 0), r["control_id"]),
    )[:top_n]

    return RiskSummary(
        total_weight_missing=totals["missing"],
        total_weight_partial=totals["partial"],
        total_weight_met=totals["met"],
        by_domain=by_domain,
        top_priorities=[dict(r) for r in priorities],
    )


def score_control_set(control_ids: list[str]) -> int:
    """Sum of SCF weights for an arbitrary set of controls."""
    if not control_ids:
        return 0
    placeholders = ",".join("?" * len(control_ids))
    with sqlite3.connect(_db_path()) as conn:
        result = conn.execute(
            f"SELECT COALESCE(SUM(weight), 0) FROM controls WHERE id IN ({placeholders})",
            control_ids,
        ).fetchone()
    return int(result[0]) if result else 0


if __name__ == "__main__":
    raise SystemExit(
        "risk_score is consumed by gap_analysis output formatters, "
        "not run standalone. Use scripts/scf_lookup.py for ad-hoc queries."
    )
