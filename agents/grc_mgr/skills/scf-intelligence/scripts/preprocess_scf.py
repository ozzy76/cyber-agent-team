"""Parse the SCF full-catalog JSON into a local SQLite database.

One-shot setup step. Run at install time and on every SCF version bump.

Source : the `scf-full-*.json` release from https://tools.scfconnectlabs.com
         (the 13 MB "Complete SCF catalog including all control data,
         maturity criteria, framework mappings, risk/threat information,
         and assessment objectives" — explicitly NOT OSCAL).

Why not OSCAL? The OSCAL export carries only SCF's *internal* risk
catalog under `risk-threat.*` props — it has zero external framework
crosswalks. The full-catalog JSON carries all 25k+ framework mappings
(PCI DSS, NIST 800-53, ISO 27001, CIS CSC, etc.). Same control set,
strictly more usable data.

Default DB     : ~/.local/share/bateam/grc/scf.db (override BATEAM_SCF_DB)
Default source : $BATEAM_SCF_JSON (no in-repo default — the 13 MB
                 catalog is not committed)

Usage:
    python preprocess_scf.py                     # uses env vars / defaults
    python preprocess_scf.py --source PATH       # override source JSON
    python preprocess_scf.py --db PATH           # override DB location
    python preprocess_scf.py --stats             # just print DB stats

Field-naming gotcha: in the full-catalog JSON, `statement` is the short
title and `description` is the long control prose. We store the long
prose in `controls.statement` (sourced from `description`) because that
is what the SCF audience and the OSCAL spec mean by "statement".
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sqlite3
import sys
from typing import Any

DEFAULT_DB = pathlib.Path("~/.local/share/bateam/grc/scf.db").expanduser()

SCHEMA = """
CREATE TABLE catalog_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE domains (
    id    TEXT PRIMARY KEY,   -- slugified domain name (e.g., 'security-compliance-resilience-governance')
    title TEXT NOT NULL        -- original 'name' field
);

CREATE TABLE controls (
    id        TEXT PRIMARY KEY,
    domain_id TEXT NOT NULL REFERENCES domains(id),
    title     TEXT NOT NULL,
    statement TEXT,            -- sourced from full-SCF `description` field
    weight    INTEGER
);
CREATE INDEX idx_controls_domain ON controls(domain_id);
CREATE INDEX idx_controls_weight ON controls(weight DESC);

CREATE TABLE assessment_objectives (
    id         TEXT PRIMARY KEY,
    control_id TEXT NOT NULL REFERENCES controls(id),
    seq        INTEGER NOT NULL,
    prose      TEXT NOT NULL
);
CREATE INDEX idx_aos_control ON assessment_objectives(control_id);

CREATE TABLE control_frameworks (
    control_id     TEXT NOT NULL REFERENCES controls(id),
    framework_slug TEXT NOT NULL,
    framework_name TEXT NOT NULL,
    locator        TEXT NOT NULL
);
CREATE INDEX idx_frameworks_slug    ON control_frameworks(framework_slug);
CREATE INDEX idx_frameworks_control ON control_frameworks(control_id);
CREATE INDEX idx_frameworks_locator ON control_frameworks(framework_slug, locator);

CREATE TABLE control_evidence_refs (
    control_id   TEXT NOT NULL REFERENCES controls(id),
    seq          INTEGER NOT NULL,
    evidence_ref TEXT NOT NULL
);
CREATE INDEX idx_evidence_control ON control_evidence_refs(control_id);

CREATE TABLE control_risk_threats (
    control_id TEXT NOT NULL REFERENCES controls(id),
    category   TEXT NOT NULL,
    value      TEXT NOT NULL
);
CREATE INDEX idx_risk_control  ON control_risk_threats(control_id);
CREATE INDEX idx_risk_category ON control_risk_threats(category);

CREATE VIRTUAL TABLE controls_fts USING fts5(
    id UNINDEXED,
    title,
    statement,
    tokenize = 'porter unicode61'
);
"""

# Framework names in full-SCF contain literal CR+LF as word separators
# (the source was an Excel spreadsheet with multi-line column headers).
# We normalize for both display and slug derivation.
_WS_RE = re.compile(r"\s+")


def norm_text(s: str) -> str:
    """Collapse all whitespace runs (incl. \\r\\n) to single spaces."""
    return _WS_RE.sub(" ", s.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")).strip()


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(s: str) -> str:
    s = norm_text(s).lower()
    s = _SLUG_RE.sub("-", s).strip("-")
    return s


# Risk-threat `value` fields pack multiple IDs separated by CR+LF.
def split_risk_values(raw: str) -> list[str]:
    parts = re.split(r"[\r\n]+", raw)
    return [p.strip() for p in parts if p.strip()]


def resolve_source(arg: str | None) -> pathlib.Path:
    if arg:
        return pathlib.Path(arg).expanduser()
    env = os.environ.get("BATEAM_SCF_JSON") or os.environ.get("BATEAM_SCF_OSCAL_JSON")
    if env:
        return pathlib.Path(env).expanduser()
    sys.exit(
        "error: SCF JSON not specified.\n"
        "  Pass --source PATH, or set BATEAM_SCF_JSON.\n"
        "  Download the 'Full SCF' JSON (NOT the OSCAL one) from\n"
        "  https://tools.scfconnectlabs.com"
    )


def resolve_db(arg: str | None) -> pathlib.Path:
    if arg:
        return pathlib.Path(arg).expanduser()
    return pathlib.Path(os.environ.get("BATEAM_SCF_DB", str(DEFAULT_DB))).expanduser()


def parse_weight(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def init_db(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def load_catalog(conn: sqlite3.Connection, source: pathlib.Path) -> dict[str, int]:
    with source.open() as fh:
        data = json.load(fh)

    fmt = data.get("metadata", {}).get("format")
    if fmt != "full-scf":
        sys.exit(
            f"error: source format is {fmt!r}, expected 'full-scf'.\n"
            "  Download the 'Full SCF' JSON release, not the OSCAL one."
        )

    meta = data["metadata"]
    stats = data.get("statistics", {})
    meta_rows = [
        ("source_uuid", meta.get("uuid", "")),
        ("title", meta.get("title", "")),
        ("scf_version", meta.get("scfVersion", "")),
        ("source_format", meta.get("format", "")),
        ("generated_at", meta.get("generatedAt", "")),
        ("source_path", str(source)),
        ("source_total_controls", str(stats.get("totalControls", ""))),
        ("source_total_framework_mappings", str(stats.get("totalFrameworkMappings", ""))),
        ("source_total_risk_threats", str(stats.get("totalRiskThreats", ""))),
    ]
    conn.executemany(
        "INSERT INTO catalog_meta(key, value) VALUES (?, ?)", meta_rows
    )

    counts = {
        "domains": 0,
        "controls": 0,
        "aos": 0,
        "frameworks": 0,
        "evidence_refs": 0,
        "risk_threats": 0,
    }

    for domain in data["domains"]:
        domain_title = domain["name"]
        domain_id = slugify(domain_title)
        conn.execute(
            "INSERT INTO domains(id, title) VALUES (?, ?)", (domain_id, domain_title)
        )
        counts["domains"] += 1

        for ctrl in domain.get("controls", []):
            cid = ctrl["scfId"]
            title = ctrl.get("statement") or ctrl.get("title") or cid
            # `description` is the actual control prose; `statement` in
            # this JSON is the short title (mislabeled in the source).
            statement = ctrl.get("description") or None
            weight = parse_weight(ctrl.get("weight"))

            conn.execute(
                "INSERT INTO controls(id, domain_id, title, statement, weight) "
                "VALUES (?, ?, ?, ?, ?)",
                (cid, domain_id, title, statement, weight),
            )
            counts["controls"] += 1

            ao_rows = [
                (ao["id"], cid, seq, ao["text"])
                for seq, ao in enumerate(ctrl.get("assessmentObjectives") or [], start=1)
                if ao.get("id") and ao.get("text")
            ]
            if ao_rows:
                conn.executemany(
                    "INSERT INTO assessment_objectives(id, control_id, seq, prose) "
                    "VALUES (?, ?, ?, ?)",
                    ao_rows,
                )
                counts["aos"] += len(ao_rows)

            fw_rows: list[tuple[str, str, str, str]] = []
            for fm in ctrl.get("frameworkMappings") or []:
                raw_name = fm.get("framework") or ""
                framework_name = norm_text(raw_name)
                framework_slug = slugify(raw_name)
                for locator in fm.get("ids") or []:
                    fw_rows.append((cid, framework_slug, framework_name, str(locator)))
            if fw_rows:
                conn.executemany(
                    "INSERT INTO control_frameworks(control_id, framework_slug, framework_name, locator) "
                    "VALUES (?, ?, ?, ?)",
                    fw_rows,
                )
                counts["frameworks"] += len(fw_rows)

            ev_rows = [
                (cid, seq, ref)
                for seq, ref in enumerate(ctrl.get("evidenceReferences") or [], start=1)
                if isinstance(ref, str) and ref.strip()
            ]
            if ev_rows:
                conn.executemany(
                    "INSERT INTO control_evidence_refs(control_id, seq, evidence_ref) "
                    "VALUES (?, ?, ?)",
                    ev_rows,
                )
                counts["evidence_refs"] += len(ev_rows)

            rt_rows: list[tuple[str, str, str]] = []
            for rt in ctrl.get("riskThreats") or []:
                category = norm_text(rt.get("category", ""))
                for v in split_risk_values(rt.get("value", "")):
                    rt_rows.append((cid, category, v))
            if rt_rows:
                conn.executemany(
                    "INSERT INTO control_risk_threats(control_id, category, value) "
                    "VALUES (?, ?, ?)",
                    rt_rows,
                )
                counts["risk_threats"] += len(rt_rows)

            conn.execute(
                "INSERT INTO controls_fts(id, title, statement) VALUES (?, ?, ?)",
                (cid, title, statement or ""),
            )

    conn.commit()
    return counts


def print_stats(conn: sqlite3.Connection) -> None:
    rows = {
        "catalog_meta": conn.execute("SELECT COUNT(*) FROM catalog_meta").fetchone()[0],
        "domains": conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0],
        "controls": conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0],
        "assessment_objectives": conn.execute(
            "SELECT COUNT(*) FROM assessment_objectives"
        ).fetchone()[0],
        "control_frameworks": conn.execute(
            "SELECT COUNT(*) FROM control_frameworks"
        ).fetchone()[0],
        "framework_slugs (distinct)": conn.execute(
            "SELECT COUNT(DISTINCT framework_slug) FROM control_frameworks"
        ).fetchone()[0],
        "control_evidence_refs": conn.execute(
            "SELECT COUNT(*) FROM control_evidence_refs"
        ).fetchone()[0],
        "control_risk_threats": conn.execute(
            "SELECT COUNT(*) FROM control_risk_threats"
        ).fetchone()[0],
        "controls_fts": conn.execute("SELECT COUNT(*) FROM controls_fts").fetchone()[0],
    }
    meta = dict(conn.execute("SELECT key, value FROM catalog_meta").fetchall())
    print("SCF catalog:")
    for k in ("title", "scf_version", "source_format", "generated_at"):
        if meta.get(k):
            print(f"  {k:14s} {meta[k]}")
    print("Row counts:")
    for k, v in rows.items():
        print(f"  {k:30s} {v:>8d}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", help="Path to SCF full-catalog JSON")
    ap.add_argument("--db", help=f"Path to SQLite DB (default: {DEFAULT_DB})")
    ap.add_argument("--stats", action="store_true", help="Print stats and exit")
    args = ap.parse_args()

    db_path = resolve_db(args.db)

    if args.stats:
        if not db_path.exists():
            sys.exit(f"error: DB does not exist at {db_path}")
        with sqlite3.connect(db_path) as conn:
            print_stats(conn)
        return 0

    source = resolve_source(args.source)
    if not source.exists():
        sys.exit(f"error: source JSON not found at {source}")

    print(f"Source: {source}")
    print(f"DB:     {db_path}")
    conn = init_db(db_path)
    try:
        counts = load_catalog(conn, source)
    finally:
        conn.close()
    print("Loaded:")
    for k, v in counts.items():
        print(f"  {k:14s} {v:>8d}")
    with sqlite3.connect(db_path) as conn:
        print_stats(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
