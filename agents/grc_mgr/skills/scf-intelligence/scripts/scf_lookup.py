"""Runtime lookup against the SCF SQLite database.

Four query modes — pick the one that matches the user's question:

    scf_lookup.lookup_by_id("GOV-03")
    scf_lookup.lookup_by_domain("asset-management")
    scf_lookup.lookup_by_framework("pci-dss-4-0-1")
    scf_lookup.lookup_by_keyword("incident response plan")

Every result is a dict with at least: `id`, `title`, `domain_id`,
`statement`, `weight`. Use `include_aos=True` for evidence-guidance
queries; otherwise AOs are excluded to keep responses under the 5,000
token target.

Stub — wiring shape is final; query bodies are skeletons with TODOs.
"""

from __future__ import annotations

import os
import pathlib
import sqlite3
from typing import Any

DEFAULT_DB = pathlib.Path("~/.local/share/bateam/grc/scf.db").expanduser()


def db_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("BATEAM_SCF_DB", str(DEFAULT_DB))).expanduser()


def _connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise FileNotFoundError(
            f"SCF DB not found at {path}. Run scripts/preprocess_scf.py first."
        )
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _control_row(conn: sqlite3.Connection, control_id: str, include_aos: bool) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, domain_id, title, statement, weight FROM controls WHERE id = ?",
        (control_id,),
    ).fetchone()
    if not row:
        return None
    out = dict(row)
    if include_aos:
        out["assessment_objectives"] = [
            dict(r)
            for r in conn.execute(
                "SELECT id, seq, prose FROM assessment_objectives "
                "WHERE control_id = ? ORDER BY seq",
                (control_id,),
            ).fetchall()
        ]
    out["frameworks"] = [
        dict(r)
        for r in conn.execute(
            "SELECT framework_slug, framework_name, locator "
            "FROM control_frameworks WHERE control_id = ? "
            "ORDER BY framework_slug, locator",
            (control_id,),
        ).fetchall()
    ]
    out["evidence_refs"] = [
        r[0]
        for r in conn.execute(
            "SELECT evidence_ref FROM control_evidence_refs "
            "WHERE control_id = ? ORDER BY seq",
            (control_id,),
        ).fetchall()
    ]
    out["risk_threats"] = [
        dict(r)
        for r in conn.execute(
            "SELECT category, value FROM control_risk_threats "
            "WHERE control_id = ? ORDER BY category, value",
            (control_id,),
        ).fetchall()
    ]
    out["maturity_criteria"] = [
        dict(r)
        for r in conn.execute(
            "SELECT cmm_level, criteria_text FROM maturity_criteria "
            "WHERE control_id = ? ORDER BY cmm_level",
            (control_id,),
        ).fetchall()
    ]
    return out


def lookup_by_id(control_id: str, *, include_aos: bool = False) -> dict[str, Any] | None:
    """Exact match on a control ID (e.g., GOV-03, AST-02)."""
    with _connect() as conn:
        return _control_row(conn, control_id, include_aos)


def lookup_by_domain(domain_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    """All controls in a domain, ordered by weight desc.

    `domain_id` is the slugified domain name (e.g., `asset-management`).
    For human-readable input ("asset management"), call slugify() upstream.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, domain_id, title, weight FROM controls "
            "WHERE domain_id = ? ORDER BY weight DESC NULLS LAST, id LIMIT ?",
            (domain_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def lookup_by_framework(framework_slug: str, *, limit: int = 500) -> list[dict[str, Any]]:
    """Controls mapped to a framework slug (e.g., `pci-dss-4-0-1`).

    See references/scf-frameworks.md for the catalog of slugs.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.domain_id, c.title, c.weight,
                   GROUP_CONCAT(f.locator, '; ') AS locators
            FROM controls c
            JOIN control_frameworks f ON f.control_id = c.id
            WHERE f.framework_slug = ?
            GROUP BY c.id
            ORDER BY c.weight DESC NULLS LAST, c.id
            LIMIT ?
            """,
            (framework_slug, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def lookup_controls_for_framework_locator(
    framework_slug: str, locator: str
) -> list[dict[str, Any]]:
    """Reverse lookup: given a framework-native ID (e.g., PCI DSS 4.0.1
    locator '12.1'), return the SCF controls that satisfy it.

    Exact-match only. Use lookup_controls_for_client_locator() for
    client-supplied locators that may need normalization (HIPAA prefix
    expansion, NIST zero-padding, CMMC translation, etc.).
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.domain_id, c.title, c.statement, c.weight
            FROM controls c
            JOIN control_frameworks f ON f.control_id = c.id
            WHERE f.framework_slug = ? AND f.locator = ?
            ORDER BY c.weight DESC NULLS LAST, c.id
            """,
            (framework_slug, locator),
        ).fetchall()
        return [dict(r) for r in rows]


def lookup_controls_for_client_locator(
    framework_slug: str, client_locator: str
) -> dict[str, Any]:
    """Reverse lookup for client-supplied locators with normalization.

    Applies locator_normalize.normalize() to transform the client's
    input (e.g., 'AC-2' → 'AC-02', '164.308(a)(1)' → all child rules)
    before querying. Returns a dict with the normalized form, the
    matched controls, and per-control matched locators so the gap
    report can show *why* each control was attached.

    Returns:
        {
            "framework_slug": str,
            "client_locator": str,
            "strategy": str,
            "notes": str | None,
            "matched_locators": list[str],   # distinct locators that matched
            "controls": list[ControlRow],    # SCF controls (deduped by id)
        }
    """
    from locator_normalize import build_where_clause, normalize

    norm = normalize(framework_slug, client_locator)
    where_sql, where_params = build_where_clause(norm)
    sql = (
        "SELECT DISTINCT c.id, c.domain_id, c.title, c.statement, c.weight, "
        "                f.locator AS matched_locator "
        "FROM controls c "
        "JOIN control_frameworks f ON f.control_id = c.id "
        f"WHERE f.framework_slug = ? AND {where_sql} "
        "ORDER BY c.weight DESC NULLS LAST, c.id, f.locator"
    )
    with _connect() as conn:
        rows = conn.execute(sql, (framework_slug, *where_params)).fetchall()

    # Dedupe by control id, collecting all matched locators per control.
    controls_by_id: dict[str, dict[str, Any]] = {}
    matched_locators: list[str] = []
    seen_locator: set[str] = set()
    for r in rows:
        d = dict(r)
        loc = d.pop("matched_locator")
        if loc not in seen_locator:
            matched_locators.append(loc)
            seen_locator.add(loc)
        existing = controls_by_id.get(d["id"])
        if existing is None:
            d["matched_locators"] = [loc]
            controls_by_id[d["id"]] = d
        else:
            existing["matched_locators"].append(loc)

    return {
        "framework_slug": framework_slug,
        "client_locator": client_locator,
        "strategy": norm.strategy,
        "notes": norm.notes,
        "matched_locators": matched_locators,
        "controls": list(controls_by_id.values()),
    }


_FTS_TOKEN_RE = __import__("re").compile(r"[A-Za-z][A-Za-z0-9]+")
# Common high-frequency words that add noise to FTS ranking without
# improving recall on Cynomi-style questionnaire prose.
_FTS_STOPWORDS = frozenset(
    {
        "the", "and", "for", "are", "that", "with", "you", "your", "yours",
        "this", "from", "has", "have", "had", "all", "any", "but", "not",
        "use", "used", "uses", "using", "does", "doing", "done",
        "what", "when", "where", "which", "who", "how", "why",
        "been", "being", "into", "onto", "out", "over", "under", "within",
        "across", "between", "more", "less", "such", "than", "then", "there",
        "these", "those", "would", "could", "should", "shall", "must", "may",
        "via", "per", "ensure", "ensures", "ensuring", "include", "includes",
        "including", "such",
    }
)


def _fts_sanitize(query: str) -> str | None:
    """Convert free text → an FTS5-safe OR-joined token query.

    FTS5 interprets punctuation as operators. Cynomi questionnaire text
    (questions, multi-select options) contains plenty of special chars
    that crash the parser. Strategy: extract alphanumeric tokens, drop
    short and stop-word tokens, OR-join the rest. BM25 still ranks docs
    by term overlap so high-relevance matches surface despite the OR.
    """
    tokens = [t.lower() for t in _FTS_TOKEN_RE.findall(query)]
    tokens = [t for t in tokens if len(t) >= 4 and t not in _FTS_STOPWORDS]
    if not tokens:
        return None
    # Cap to avoid pathological queries (200-word prose); keep first N
    # since the early tokens of a Cynomi question carry the topic.
    return " OR ".join(tokens[:20])


def lookup_by_keyword(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Full-text search over title + statement (SQLite FTS5).

    Free-text queries are sanitized to drop FTS5 operator characters
    (Cynomi prose contains many) and stop-words; tokens are OR-joined
    so partial matches still appear, ranked by BM25.
    """
    fts_query = _fts_sanitize(query)
    if fts_query is None:
        return []
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.domain_id, c.title, c.statement, c.weight,
                   bm25(controls_fts) AS rank
            FROM controls_fts
            JOIN controls c ON c.id = controls_fts.id
            WHERE controls_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def catalog_version() -> dict[str, str]:
    """Returns scf_version + last_modified — include in audit-bound responses."""
    with _connect() as conn:
        return dict(conn.execute("SELECT key, value FROM catalog_meta").fetchall())


def domains() -> list[dict[str, str]]:
    with _connect() as conn:
        return [dict(r) for r in conn.execute("SELECT id, title FROM domains ORDER BY id")]


def framework_slugs() -> list[dict[str, Any]]:
    """Distinct (slug, display name) pairs with control-count.

    Useful for autocompletion and for showing the user which frameworks
    the current catalog actually covers. When framework_metadata is
    populated (post-spreadsheet augmentation) the geography column is
    included so we can group by region in agent responses.
    """
    with _connect() as conn:
        has_meta = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='framework_metadata'"
        ).fetchone()
        if has_meta:
            return [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT cf.framework_slug,
                           MIN(cf.framework_name) AS framework_name,
                           fm.geography,
                           fm.publisher,
                           COUNT(DISTINCT cf.control_id) AS controls
                    FROM control_frameworks cf
                    LEFT JOIN framework_metadata fm ON fm.slug = cf.framework_slug
                    GROUP BY cf.framework_slug
                    ORDER BY cf.framework_slug
                    """
                )
            ]
        return [
            dict(r)
            for r in conn.execute(
                """
                SELECT framework_slug,
                       MIN(framework_name) AS framework_name,
                       COUNT(DISTINCT control_id) AS controls
                FROM control_frameworks
                GROUP BY framework_slug
                ORDER BY framework_slug
                """
            )
        ]


def framework_info(slug: str) -> dict[str, Any] | None:
    """Geography, publisher, full name, URL, STRM URL for a framework slug.

    Returns None when the slug is unknown OR when framework_metadata has
    not yet been populated (i.e., augment_from_spreadsheet.py has not
    been run).
    """
    with _connect() as conn:
        has_meta = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='framework_metadata'"
        ).fetchone()
        if not has_meta:
            return None
        row = conn.execute(
            "SELECT slug, fdi, geography, publisher, full_name, title, url, strm_url "
            "FROM framework_metadata WHERE slug = ?",
            (slug,),
        ).fetchone()
        return dict(row) if row else None


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Ad-hoc SCF lookups (debug CLI).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    sub.add_parser("domains")
    sub.add_parser("frameworks")
    p_id = sub.add_parser("id")
    p_id.add_argument("control_id")
    p_id.add_argument("--aos", action="store_true")
    p_d = sub.add_parser("domain")
    p_d.add_argument("domain_id")
    p_f = sub.add_parser("framework")
    p_f.add_argument("slug")
    p_finfo = sub.add_parser("framework-info")
    p_finfo.add_argument("slug")
    p_locator = sub.add_parser("locator", help="Exact framework-native ID lookup")
    p_locator.add_argument("slug")
    p_locator.add_argument("locator")
    p_client = sub.add_parser(
        "client-locator", help="Normalized client-locator lookup (handles HIPAA, NIST padding, etc.)"
    )
    p_client.add_argument("slug")
    p_client.add_argument("locator")
    p_k = sub.add_parser("keyword")
    p_k.add_argument("query")
    args = ap.parse_args()

    if args.cmd == "version":
        print(json.dumps(catalog_version(), indent=2))
    elif args.cmd == "domains":
        print(json.dumps(domains(), indent=2))
    elif args.cmd == "frameworks":
        print(json.dumps(framework_slugs(), indent=2))
    elif args.cmd == "id":
        print(json.dumps(lookup_by_id(args.control_id, include_aos=args.aos), indent=2))
    elif args.cmd == "domain":
        print(json.dumps(lookup_by_domain(args.domain_id), indent=2))
    elif args.cmd == "framework":
        print(json.dumps(lookup_by_framework(args.slug), indent=2))
    elif args.cmd == "framework-info":
        print(json.dumps(framework_info(args.slug), indent=2))
    elif args.cmd == "locator":
        print(
            json.dumps(
                lookup_controls_for_framework_locator(args.slug, args.locator), indent=2
            )
        )
    elif args.cmd == "client-locator":
        print(
            json.dumps(
                lookup_controls_for_client_locator(args.slug, args.locator), indent=2
            )
        )
    elif args.cmd == "keyword":
        print(json.dumps(lookup_by_keyword(args.query), indent=2))
