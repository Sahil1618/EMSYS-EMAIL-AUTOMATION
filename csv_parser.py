"""
csv_parser.py — reads the "Schedule Template" style CSV exported for NRLDC/WRLDC
punching, regardless of which plant/entity it belongs to.

Layout observed (works across regions/plants):
    Row 1        : "Schedule Template for <entity_key> and revision <REV>"
    Row 2        : ,Scheduling entity,<entity_key>,...
    Row 3        : ,Date,<dd-mm-yyyy>,...
    Row 4        : ,Revision No,<revision>,...
    (a few more optional meta rows: Avc Validation, Hybrid Validation Limit)
    (blank row)
    several header rows (POS Name, Down Stream Name, Energy Type, RE Generator
        Name, Capacity, ...) — these describe each data column
    "Block" row  : column headers for the data table (Block, Schedule, Schedule, ...)
    96 data rows : block number 1..96 with values for each column
"""

import csv
import io
from dataclasses import dataclass, field


@dataclass
class ParsedSchedule:
    entity_key: str
    date_str: str
    revision: str
    column_headers: list          # header text per data column (excluding "Block")
    column_labels: list           # friendlier labels (header + generator/POS if available)
    blocks: dict                  # block_num -> list of values (str), aligned to column_headers
    raw_bytes: bytes
    filename: str
    rows: list = field(default_factory=list)      # all raw CSV rows (for rebuilding output)
    block_header_idx: int = 0                      # index into `rows` of the "Block" header row
    pos_names: list = field(default_factory=list)      # distinct POS Name values found in file
    energy_types: list = field(default_factory=list)   # distinct Energy Type values found in file


def _clean_rows(raw_bytes: bytes):
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader]


def parse_schedule_csv(raw_bytes: bytes, filename: str) -> ParsedSchedule:
    rows = _clean_rows(raw_bytes)

    entity_key = None
    date_str = None
    revision = None
    block_header_idx = None

    meta_rows = {}  # label (col0) -> list of remaining cells, for friendly labels later

    for i, row in enumerate(rows):
        if not row:
            continue
        label = (row[0] or "").strip()

        if label.lower() == "block":
            block_header_idx = i
            break

        if len(row) > 1:
            key = (row[1] or "").strip().lower()
            if key == "scheduling entity":
                entity_key = (row[2] or "").strip()
            elif key == "date":
                date_str = (row[2] or "").strip()
            elif key == "revision no":
                revision = (row[2] or "").strip()

        if label:
            meta_rows[label] = row[1:]

    if block_header_idx is None:
        raise ValueError(
            "Could not find the 'Block' header row in this CSV — is this a "
            "standard schedule template export?"
        )
    if not entity_key:
        raise ValueError(
            "Could not find a 'Scheduling entity' value in this file — cannot "
            "identify which plant this belongs to."
        )

    header_row = rows[block_header_idx]
    column_headers = [c.strip() for c in header_row[1:] if c is not None]
    n_cols = len(column_headers)

    # Build friendlier per-column labels using RE Generator Name / Down Stream
    # Name / POS Name rows when available, to disambiguate repeated "Schedule"
    # columns that belong to different generators/buyers.
    def label_source(*keys):
        for k in keys:
            for meta_label, values in meta_rows.items():
                if meta_label.lower() == k:
                    return values
        return None

    gen_names = label_source("buyer name", "stu name", "re generator name",
                              "down stream name", "pos name")

    def distinct_values(*keys):
        for k in keys:
            for meta_label, values in meta_rows.items():
                if meta_label.lower() == k:
                    seen = []
                    for v in values:
                        v = (v or "").strip()
                        if v and v not in seen:
                            seen.append(v)
                    return seen
        return []

    pos_names = distinct_values("pos name")
    energy_types = distinct_values("energy type")

    column_labels = []
    for idx, h in enumerate(column_headers):
        extra = None
        if gen_names and idx < len(gen_names):
            v = (gen_names[idx] or "").strip()
            if v:
                extra = v
        column_labels.append(f"{h} ({extra})" if extra else f"{h} [col {idx + 1}]")

    blocks = {}
    for row in rows[block_header_idx + 1:]:
        if not row or not (row[0] or "").strip():
            continue
        try:
            block_num = int(row[0].strip())
        except ValueError:
            continue
        values = row[1:1 + n_cols]
        # pad if the row is short
        values = values + [""] * (n_cols - len(values))
        blocks[block_num] = values

    return ParsedSchedule(
        entity_key=entity_key,
        date_str=date_str or "",
        revision=revision or "",
        column_headers=column_headers,
        column_labels=column_labels,
        blocks=blocks,
        raw_bytes=raw_bytes,
        filename=filename,
        rows=rows,
        block_header_idx=block_header_idx,
        pos_names=pos_names,
        energy_types=energy_types,
    )


def rebuild_csv_bytes(parsed: ParsedSchedule, merged_blocks: dict) -> bytes:
    """
    Rebuilds the CSV file: keeps every header/meta row exactly as uploaded
    (title, scheduling entity, date, revision, POS/generator meta rows, the
    'Block' header row), but writes the 96 data rows from `merged_blocks`
    instead of whatever was in the uploaded file — this is how already-punched
    blocks get protected from being overwritten.
    """
    n_cols = len(parsed.column_headers)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")

    for row in parsed.rows[: parsed.block_header_idx + 1]:
        writer.writerow(row)

    for bn in range(1, 97):
        values = merged_blocks.get(bn)
        if values is None:
            values = parsed.blocks.get(bn, [""] * n_cols)
        values = list(values) + [""] * (n_cols - len(values))
        writer.writerow([bn] + values[:n_cols])

    text = out.getvalue()
    return ("\ufeff" + text).encode("utf-8")


def validate_schedule_sums(parsed: ParsedSchedule, tolerance: float = 0.5):
    """
    For every block, the sum of all 'Schedule' columns should equal the
    file's declared total (the first column whose header starts with
    'Declared' — e.g. 'Declared Forecast' or 'Declared Plant Schedule').

    Returns a list of mismatches: [{"block": n, "declared": x, "schedule_sum": y, "diff": d}, ...]
    Empty list means everything checks out.
    """
    declared_idx = None
    for idx, h in enumerate(parsed.column_headers):
        if h.strip().lower().startswith("declared"):
            declared_idx = idx
            break

    schedule_indices = [
        idx for idx, h in enumerate(parsed.column_headers) if h.strip().lower() == "schedule"
    ]

    if declared_idx is None or not schedule_indices:
        # Can't validate this file's layout — don't block, just skip silently.
        return []

    mismatches = []
    for bn in sorted(parsed.blocks):
        values = parsed.blocks[bn]

        def to_float(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        declared_val = to_float(values[declared_idx]) if declared_idx < len(values) else 0.0
        schedule_sum = sum(
            to_float(values[i]) for i in schedule_indices if i < len(values)
        )
        diff = abs(declared_val - schedule_sum)
        allowed = max(tolerance, 0.01 * abs(declared_val))
        if diff > allowed:
            mismatches.append({
                "block": bn,
                "declared": declared_val,
                "schedule_sum": schedule_sum,
                "diff": diff,
            })
    return mismatches


def blocks_table_text(parsed: ParsedSchedule, block_nums: list) -> str:
    """Plain-text table of the given block numbers' values, for the email body."""
    lines = []
    for bn in block_nums:
        values = parsed.blocks.get(bn)
        if values is None:
            lines.append(f"  Block {bn}: (not found in file)")
            continue
        parts = [f"{label}={val}" for label, val in zip(parsed.column_labels, values)]
        lines.append(f"  Block {bn}: " + ", ".join(parts))
    return "\n".join(lines)


def blocks_table_html(parsed: ParsedSchedule, block_nums: list) -> str:
    header_cells = "".join(f"<th style='padding:4px 8px;border:1px solid #ccc'>{h}</th>"
                            for h in parsed.column_labels)
    rows_html = ""
    for bn in block_nums:
        values = parsed.blocks.get(bn)
        if values is None:
            continue
        cells = "".join(f"<td style='padding:4px 8px;border:1px solid #ccc'>{v}</td>"
                         for v in values)
        rows_html += (f"<tr><td style='padding:4px 8px;border:1px solid #ccc;"
                      f"font-weight:bold'>{bn}</td>{cells}</tr>")
    return (
        "<table style='border-collapse:collapse;font-family:sans-serif;font-size:13px'>"
        f"<tr><th style='padding:4px 8px;border:1px solid #ccc'>Block</th>{header_cells}</tr>"
        f"{rows_html}</table>"
    )