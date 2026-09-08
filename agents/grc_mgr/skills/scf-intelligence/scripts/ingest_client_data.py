"""Normalize client control inventories into a common shape for gap analysis.

Two input shapes seen in practice (samples in /Users/biuser/Library/
CloudStorage/.../Project/2026 Add SCF for GRC agent/):

A. Cynomi questionnaire CSV
   Columns: "Questionnaire name", "Question", "Response", "Note"
   Response values: Yes / No / Partially / N/A / I don't know /
                    free-text multi-select
   No control IDs in the input — `Questionnaire name` is the SCF-adjacent
   domain bucket (e.g., "Third-Party Management", "Logging and
   Monitoring") and the question text must be semantically mapped to
   SCF control statements.

B. Framework-status report (CSV / XLSX / PDF)
   Columns: Control ID, Name, Status
   Example: PCI DSS 4.0.1 readiness with rows like "1.1 / Processes and
   mechanisms for installing… / Not Implemented".
   Status values: Implemented / Partially / Not Implemented / N/A
   These rows carry framework-native IDs (PCI 1.1, ISO 27001 5.1, etc.)
   which map cleanly to SCF via `control_frameworks` reverse-lookup.

Output (both shapes normalize to):
    [
      {
        "claim_id": "<framework-native id or generated UUID>",
        "framework_slug": "<slug or None>",
        "domain_hint": "<questionnaire bucket or framework section>",
        "claim_text": "<original question or control name>",
        "status": "met" | "partial" | "missing" | "na" | "unknown",
        "note": "<optional free text>"
      },
      ...
    ]

Stub — module shape and type signatures are final; bodies are skeletons.
Implementation order recommended:
  1. cynomi_questionnaire_csv (most common client format)
  2. framework_status_csv     (Cynomi's CSV report export)
  3. framework_status_xlsx    (openpyxl already in deps)
  4. pdf_extract              (pypdf, only when CSV/XLSX not available)
"""

from __future__ import annotations

import csv
import pathlib
import re
import uuid
from typing import Literal, TypedDict

ClaimStatus = Literal["met", "partial", "missing", "na", "unknown"]


class ClientClaim(TypedDict, total=False):
    claim_id: str
    framework_slug: str | None
    domain_hint: str | None
    claim_text: str
    status: ClaimStatus
    note: str


# Cynomi Yes/No/Partially/N/A vocabulary → normalized status.
_CYNOMI_STATUS = {
    "yes": "met",
    "implemented": "met",
    "partially": "partial",
    "partial": "partial",
    "no": "missing",
    "not implemented": "missing",
    "n/a": "na",
    "na": "na",
    "i don't know": "unknown",
    "i don’t know": "unknown",  # smart-quote variant
    "unknown": "unknown",
}


def normalize_status(raw: str) -> ClaimStatus:
    """Map raw response text → normalized status enum.

    Multi-select responses (e.g., "Anti-malware, DMARC/DKIM/SPF, Anti-spam")
    are evidence of an *implementation* — treated as 'met' when truthy.
    Cynomi uses '' (empty) for unanswered.
    """
    if not raw:
        return "unknown"
    key = raw.strip().lower()
    if key in _CYNOMI_STATUS:
        return _CYNOMI_STATUS[key]
    # Free-text / multi-select with positive content implies "met".
    return "met"


# Cynomi questionnaire sections that hold environmental Q&A (industry,
# user count, IT management, regulations needed, etc.) rather than
# control claims. Excluded from gap analysis by default.
_NON_CLAIM_SECTIONS = {"Onboarding"}


def ingest_cynomi_questionnaire_csv(
    path: pathlib.Path | str,
    *,
    include_sections: set[str] | None = None,
) -> list[ClientClaim]:
    """Cynomi all-assessments export — questionnaire format.

    Columns: Questionnaire name, Question, Response, Note
    Each row becomes one ClientClaim. No framework_slug — the SCF
    mapping happens in gap_analysis via FTS semantic matching against
    SCF control statements.

    The "Onboarding" section is skipped by default — its rows are
    environmental metadata (industry, headcount, regulations needed)
    rather than control claims. Pass `include_sections={"Onboarding"}`
    to override.
    """
    path = pathlib.Path(path)
    claims: list[ClientClaim] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            section = (row.get("Questionnaire name") or "").strip()
            if section in _NON_CLAIM_SECTIONS and (
                include_sections is None or section not in include_sections
            ):
                continue
            question = (row.get("Question") or "").strip()
            if not question:
                continue
            claims.append(
                {
                    "claim_id": f"cynomi-{uuid.uuid4().hex[:8]}",
                    "framework_slug": None,
                    "domain_hint": section or None,
                    "claim_text": question,
                    "status": normalize_status(row.get("Response") or ""),
                    "note": (row.get("Note") or "").strip(),
                }
            )
    return claims


def ingest_framework_status_csv(
    path: pathlib.Path | str,
    framework_slug: str,
    *,
    id_column: str = "Control",
    name_column: str = "Name",
    status_column: str = "Status",
) -> list[ClientClaim]:
    """Framework-status CSV (PCI DSS readiness, NIST CSF self-assessment, …).

    Column names vary by client — caller specifies them. Defaults
    match the Cynomi-style header.
    """
    path = pathlib.Path(path)
    claims: list[ClientClaim] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = (row.get(id_column) or "").strip()
            name = (row.get(name_column) or "").strip()
            status_raw = (row.get(status_column) or "").strip()
            if not cid:
                continue
            claims.append(
                {
                    "claim_id": cid,
                    "framework_slug": framework_slug,
                    "domain_hint": None,
                    "claim_text": name,
                    "status": normalize_status(status_raw),
                    "note": "",
                }
            )
    return claims


def ingest_framework_status_xlsx(
    path: pathlib.Path | str,
    framework_slug: str,
    *,
    sheet_name: str | None = None,
    id_column: str = "Control",
    name_column: str = "Name",
    status_column: str = "Status",
) -> list[ClientClaim]:
    """Framework-status XLSX. First row is the header; column-name match
    is case-insensitive and ignores surrounding whitespace.
    """
    from openpyxl import load_workbook

    path = pathlib.Path(path)
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active
    rows = ws.iter_rows(values_only=True)
    header = next(rows, None)
    if not header:
        return []

    def find_col(target: str) -> int | None:
        target_n = target.strip().lower()
        for i, h in enumerate(header):
            if h is None:
                continue
            if str(h).strip().lower() == target_n:
                return i
        return None

    id_idx = find_col(id_column)
    name_idx = find_col(name_column)
    status_idx = find_col(status_column)
    if id_idx is None:
        raise ValueError(
            f"Required column {id_column!r} not found in sheet header. "
            f"Available: {[h for h in header if h is not None]}"
        )

    claims: list[ClientClaim] = []
    for r in rows:
        cid_raw = r[id_idx] if id_idx < len(r) else None
        if cid_raw is None:
            continue
        cid = str(cid_raw).strip()
        if not cid:
            continue
        name = (
            str(r[name_idx]).strip()
            if name_idx is not None and name_idx < len(r) and r[name_idx] is not None
            else ""
        )
        status_raw = (
            str(r[status_idx]).strip()
            if status_idx is not None and status_idx < len(r) and r[status_idx] is not None
            else ""
        )
        claims.append(
            {
                "claim_id": cid,
                "framework_slug": framework_slug,
                "domain_hint": None,
                "claim_text": name,
                "status": normalize_status(status_raw),
                "note": "",
            }
        )
    return claims


# Page-header / page-footer text we drop from PDF row reconstruction.
_PDF_NOISE_PREFIXES = (
    "Compliance Report",
    "Detailed Report",
    "This report details",
    "evaluation. This status",
)
_PDF_NOISE_EXACT = {"CONTROL", "NAME", "CONTROL STATUS"}

# Layout columns observed in Cynomi compliance PDFs (page 3+):
#   x ≈ 69  → control ID
#   x ≈ 133 → control name (wraps over multiple Y rows)
#   x ≈ 460 → status badge (rendered as graphic; not text-extractable)
_PDF_ID_X_RANGE = (60.0, 95.0)
_PDF_NAME_X_RANGE = (120.0, 250.0)
# Control IDs we accept across Cynomi report types. Covers PCI DSS
# (1.1, 12.10, A1.1), GDPR (5.1, 12.5(b)), HIPAA-ish (164.308(a)(1)),
# NIST CSF (GV.OC-01), ISO 27001 (5.1, 5.1(a)).
_PDF_CTRL_ID_RE = re.compile(
    r"^[A-Z]{0,4}\d+(?:\.\d+){0,3}(?:\.[A-Z][A-Z]?-?\d*)?(?:\([a-zA-Z0-9]+\))*$"
)


def ingest_framework_status_pdf(
    path: pathlib.Path | str,
    framework_slug: str,
) -> list[ClientClaim]:
    """Extract control IDs and names from a Cynomi-style PDF report.

    Cynomi renders status as colored badges (graphics) — pypdf can't
    text-extract them. So this returns claims with `status="unknown"`
    and the note explains the limitation. Use the questionnaire CSV
    (which carries Yes/No/Partially) for status; use this PDF parse
    to define the framework scope.

    For status-bearing inputs, request a CSV/XLSX export from Cynomi
    (or use ingest_framework_status_csv / xlsx directly).
    """
    from pypdf import PdfReader

    path = pathlib.Path(path)
    reader = PdfReader(str(path))

    rows: list[tuple[str, str]] = []
    for page in reader.pages:
        chunks: list[tuple[float, float, str]] = []

        def visitor(text, cm, tm, font, font_size, _bucket=chunks):
            if text and text.strip():
                if not tm:
                    return
                x, y = tm[4], tm[5]
                t = text.strip()
                if t in _PDF_NOISE_EXACT:
                    return
                if any(t.startswith(p) for p in _PDF_NOISE_PREFIXES):
                    return
                _bucket.append((y, x, t))

        page.extract_text(visitor_text=visitor)

        # Cynomi vertically-centers the control ID, so name fragments
        # appear both above and below the ID's Y. Assign each name
        # fragment to the closest ID by absolute Y distance, then sort
        # fragments by Y desc to preserve reading order.
        ids = [
            (y, t) for (y, x, t) in chunks
            if _PDF_ID_X_RANGE[0] <= x <= _PDF_ID_X_RANGE[1]
        ]
        names = [
            (y, t) for (y, x, t) in chunks
            if _PDF_NAME_X_RANGE[0] <= x <= _PDF_NAME_X_RANGE[1]
        ]
        if not ids:
            continue

        ids.sort(key=lambda yt: -yt[0])
        buckets: dict[float, list[tuple[float, str]]] = {y: [] for y, _ in ids}
        for y_n, t_n in names:
            closest_y = min((y for y, _ in ids), key=lambda y: abs(y - y_n))
            buckets[closest_y].append((y_n, t_n))

        for y_id, t_id in ids:
            parts = sorted(buckets[y_id], key=lambda yt: -yt[0])
            name = " ".join(t for _, t in parts).strip()
            rows.append((t_id, name))

    claims: list[ClientClaim] = []
    note = "Status not extracted (Cynomi renders status badges as graphics, not text)."
    for cid, name in rows:
        if not _PDF_CTRL_ID_RE.match(cid):
            continue
        claims.append(
            {
                "claim_id": cid,
                "framework_slug": framework_slug,
                "domain_hint": None,
                "claim_text": name,
                "status": "unknown",
                "note": note,
            }
        )
    return claims


def ingest_free_text(
    text: str, domain_hint: str | None = None
) -> list[ClientClaim]:
    """One ClientClaim per sentence/bullet — coarsest possible ingest.

    Used when the client describes their controls in prose. Status is
    'met' by default since the user is asserting they have these
    controls; gap_analysis will validate via SCF semantic matching.
    """
    # Split on sentence terminators and bullet markers. Robust enough
    # for short prose descriptions; not a full NLP sentence splitter.
    chunks = re.split(r"(?:\r?\n+|(?<=[.!?])\s+|^\s*[-•*]\s+)", text.strip(), flags=re.MULTILINE)
    claims: list[ClientClaim] = []
    for c in chunks:
        c = c.strip()
        if len(c) < 8:  # drop noise / fragments
            continue
        claims.append(
            {
                "claim_id": f"free-{uuid.uuid4().hex[:8]}",
                "framework_slug": None,
                "domain_hint": domain_hint,
                "claim_text": c,
                "status": "met",
                "note": "",
            }
        )
    return claims


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Ingest client compliance data → ClientClaim[]")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_cynomi = sub.add_parser("cynomi", help="Cynomi questionnaire CSV")
    p_cynomi.add_argument("path")

    p_csv = sub.add_parser("framework-csv", help="Framework-status CSV")
    p_csv.add_argument("path")
    p_csv.add_argument("--framework", required=True)
    p_csv.add_argument("--id-col", default="Control")
    p_csv.add_argument("--name-col", default="Name")
    p_csv.add_argument("--status-col", default="Status")

    p_xlsx = sub.add_parser("framework-xlsx", help="Framework-status XLSX")
    p_xlsx.add_argument("path")
    p_xlsx.add_argument("--framework", required=True)
    p_xlsx.add_argument("--sheet")
    p_xlsx.add_argument("--id-col", default="Control")
    p_xlsx.add_argument("--name-col", default="Name")
    p_xlsx.add_argument("--status-col", default="Status")

    p_pdf = sub.add_parser("framework-pdf", help="Framework-status PDF (Cynomi style)")
    p_pdf.add_argument("path")
    p_pdf.add_argument("--framework", required=True)

    args = ap.parse_args()
    if args.cmd == "cynomi":
        out = ingest_cynomi_questionnaire_csv(args.path)
    elif args.cmd == "framework-csv":
        out = ingest_framework_status_csv(
            args.path,
            args.framework,
            id_column=args.id_col,
            name_column=args.name_col,
            status_column=args.status_col,
        )
    elif args.cmd == "framework-xlsx":
        out = ingest_framework_status_xlsx(
            args.path,
            args.framework,
            sheet_name=args.sheet,
            id_column=args.id_col,
            name_column=args.name_col,
            status_column=args.status_col,
        )
    elif args.cmd == "framework-pdf":
        out = ingest_framework_status_pdf(args.path, args.framework)
    else:
        raise SystemExit(2)
    print(json.dumps(out[:10], indent=2))
    print(f"... ({len(out)} total)")
