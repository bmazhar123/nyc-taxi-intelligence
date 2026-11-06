"""
Phase 1 -- Raw data inspection (profiling). READ-ONLY: nothing is deleted
or changed here. We only MEASURE problems so that Phase 2 cleaning rules
are based on evidence, not guesses.

For every monthly Parquet file it reports:
  1. Schema: column names + types, compared case-insensitively against the
     official data dictionary (missing, unexpected, renamed-by-case, and
     type drift between months).
  2. Volume and date coverage: row count, min/max pickup time, and how many
     rows fall OUTSIDE the month the file is named for.
  3. Data-quality signals (counts only): nulls per column, exact duplicate
     rows, non-positive or > 24h durations, zero/negative distances,
     negative money values, codes not in the data dictionary, and zone IDs
     missing from the zone lookup.

Outputs:
  reports/phase1_inspection.json   machine-readable (used by tests / later phases)
  reports/phase1_inspection.md     human-readable summary

Usage:
  python -m src.inspect_data                 # inspects every yellow_tripdata_*.parquet in data/raw
  python -m src.inspect_data --raw-dir path  # inspect another folder
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from src import config

FILE_PATTERN = re.compile(r"yellow_tripdata_(\d{4}-\d{2})\.parquet$")


# --------------------------------------------------------------------------
# Schema helpers
# --------------------------------------------------------------------------
def read_schema(con: duckdb.DuckDBPyConnection, path: Path) -> dict[str, str]:
    """Return {column_name: duckdb_type} for a Parquet file without loading rows."""
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path.as_posix()}')").fetchall()
    return {r[0]: r[1] for r in rows}


def compare_schema(actual_cols: list[str]) -> dict:
    """
    Compare actual column names to the data dictionary, ignoring case.

    Returns:
      column_map   canonical dictionary name -> actual name in this file
      missing      dictionary columns not present at all
      unexpected   columns in the file that are not in the dictionary
      case_diffs   columns present but capitalised differently
      optional_present  documented optional columns found (e.g. cbd_congestion_fee)
    """
    lower_to_actual = {c.lower(): c for c in actual_cols}
    known = config.EXPECTED_COLUMNS + config.OPTIONAL_COLUMNS
    known_lower = {c.lower() for c in known}

    column_map, missing, case_diffs, optional_present = {}, [], [], []
    for canonical in known:
        actual = lower_to_actual.get(canonical.lower())
        if actual is None:
            if canonical in config.EXPECTED_COLUMNS:
                missing.append(canonical)
            continue
        column_map[canonical] = actual
        if actual != canonical:
            case_diffs.append({"dictionary": canonical, "file": actual})
        if canonical in config.OPTIONAL_COLUMNS:
            optional_present.append(canonical)

    unexpected = [c for c in actual_cols if c.lower() not in known_lower]
    return {
        "column_map": column_map,
        "missing": missing,
        "unexpected": unexpected,
        "case_diffs": case_diffs,
        "optional_present": optional_present,
    }


def type_drift(schemas: dict[str, dict[str, str]]) -> list[dict]:
    """
    Find columns whose type differs between months, e.g. passenger_count
    stored as DOUBLE one month and BIGINT another. Compared case-insensitively.
    """
    by_col: dict[str, dict[str, str]] = {}
    for month, schema in schemas.items():
        for col, typ in schema.items():
            by_col.setdefault(col.lower(), {})[month] = typ
    return [
        {"column": col, "types_by_month": types}
        for col, types in sorted(by_col.items())
        if len(set(types.values())) > 1
    ]


# --------------------------------------------------------------------------
# Profiling
# --------------------------------------------------------------------------
def q(name: str) -> str:
    """Quote an identifier for SQL (handles mixed case like 'VendorID')."""
    return '"' + name.replace('"', '""') + '"'


def profile_file(con, path: Path, month: str, colmap: dict[str, str],
                 zone_ids: set[int] | None) -> dict:
    """Run all count-only quality checks for one month's file."""
    src = f"read_parquet('{path.as_posix()}')"
    con.execute(f"CREATE OR REPLACE TEMP VIEW t AS SELECT * FROM {src}")
    c = {k: q(v) for k, v in colmap.items()}  # canonical -> quoted actual name

    def scalar(sql: str):
        return con.execute(sql).fetchone()[0]

    out: dict = {"month": month, "file": path.name}
    out["row_count"] = scalar("SELECT COUNT(*) FROM t")

    # Nulls per column (one pass using COUNT(col) which skips NULLs)
    cols = list(read_schema(con, path).keys())
    null_sql = ", ".join(f"COUNT(*) - COUNT({q(x)}) AS {q(x)}" for x in cols)
    null_row = con.execute(f"SELECT {null_sql} FROM t").fetchone()
    out["nulls"] = {col: int(n) for col, n in zip(cols, null_row) if n}

    # Exact duplicate rows (every column identical)
    out["exact_duplicate_rows"] = scalar(
        "SELECT (SELECT COUNT(*) FROM t) - (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM t))"
    )

    checks: dict[str, int] = {}
    pu, do = c.get("tpep_pickup_datetime"), c.get("tpep_dropoff_datetime")
    if pu and do:
        start = f"DATE '{month}-01'"
        end = f"({start} + INTERVAL 1 MONTH)"
        row = con.execute(f"""
            SELECT MIN({pu}), MAX({pu}),
                   COUNT(*) FILTER (WHERE {pu} < {start} OR {pu} >= {end}),
                   COUNT(*) FILTER (WHERE {do} <= {pu}),
                   COUNT(*) FILTER (WHERE {do} - {pu} > INTERVAL 24 HOUR)
            FROM t
        """).fetchone()
        out["min_pickup"] = str(row[0])
        out["max_pickup"] = str(row[1])
        checks["pickup_outside_file_month"] = row[2]
        checks["dropoff_not_after_pickup"] = row[3]
        checks["duration_over_24h"] = row[4]

    if "trip_distance" in c:
        checks["distance_zero"] = scalar(f"SELECT COUNT(*) FROM t WHERE {c['trip_distance']} = 0")
        checks["distance_negative"] = scalar(f"SELECT COUNT(*) FROM t WHERE {c['trip_distance']} < 0")
    if "passenger_count" in c:
        checks["passenger_count_zero"] = scalar(f"SELECT COUNT(*) FROM t WHERE {c['passenger_count']} = 0")

    for m in config.MONEY_COLUMNS:
        if m in c:
            checks[f"negative_{m}"] = scalar(f"SELECT COUNT(*) FROM t WHERE {c[m]} < 0")
    if "total_amount" in c:
        checks["total_amount_zero"] = scalar(f"SELECT COUNT(*) FROM t WHERE {c['total_amount']} = 0")

    # Codes not documented in the data dictionary (NULLs are counted separately above)
    for col, codes in [("VendorID", config.VENDOR_CODES),
                       ("RatecodeID", config.RATECODE_CODES),
                       ("payment_type", config.PAYMENT_TYPE_CODES)]:
        if col in c:
            allowed = ", ".join(str(k) for k in codes)
            checks[f"undocumented_{col}"] = scalar(
                f"SELECT COUNT(*) FROM t WHERE {c[col]} IS NOT NULL AND {c[col]} NOT IN ({allowed})"
            )
    if "store_and_fwd_flag" in c:
        checks["undocumented_store_and_fwd_flag"] = scalar(
            f"SELECT COUNT(*) FROM t WHERE {c['store_and_fwd_flag']} IS NOT NULL "
            f"AND {c['store_and_fwd_flag']} NOT IN ('Y','N')"
        )

    # Zone IDs that are not in the official lookup
    if zone_ids:
        ids = ", ".join(str(z) for z in sorted(zone_ids))
        for col in ("PULocationID", "DOLocationID"):
            if col in c:
                checks[f"{col}_not_in_zone_lookup"] = scalar(
                    f"SELECT COUNT(*) FROM t WHERE {c[col]} NOT IN ({ids})"
                )

    out["checks"] = {k: int(v) for k, v in checks.items()}
    return out


def load_zone_ids(con, raw_dir: Path) -> set[int] | None:
    path = raw_dir / "taxi_zone_lookup.csv"
    if not path.exists():
        return None
    rows = con.execute(f"SELECT LocationID FROM read_csv_auto('{path.as_posix()}')").fetchall()
    return {int(r[0]) for r in rows}


# --------------------------------------------------------------------------
# Orchestration + reporting
# --------------------------------------------------------------------------
def find_trip_files(raw_dir: Path) -> dict[str, Path]:
    files = {}
    for p in sorted(raw_dir.glob("yellow_tripdata_*.parquet")):
        m = FILE_PATTERN.search(p.name)
        if m:
            files[m.group(1)] = p
    return files


def inspect(raw_dir: Path) -> dict:
    con = duckdb.connect()  # in-memory: inspection never writes a database
    files = find_trip_files(raw_dir)
    if not files:
        raise FileNotFoundError(f"No yellow_tripdata_*.parquet files in {raw_dir}. Run src.download first.")

    zone_ids = load_zone_ids(con, raw_dir)
    schemas, months = {}, []
    for month, path in files.items():
        schema = read_schema(con, path)
        schemas[month] = schema
        cmp = compare_schema(list(schema))
        prof = profile_file(con, path, month, cmp["column_map"], zone_ids)
        prof["schema"] = schema
        prof["schema_vs_dictionary"] = {k: v for k, v in cmp.items() if k != "column_map"}
        months.append(prof)
        print(f"  inspected {path.name}: {prof['row_count']:,} rows")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "zone_lookup_found": zone_ids is not None,
        "zone_count": len(zone_ids) if zone_ids else None,
        "total_rows": sum(m["row_count"] for m in months),
        "type_drift": type_drift(schemas),
        "months": months,
    }


def pct(n: int, total: int) -> str:
    return f"{(100 * n / total):.2f}%" if total else "n/a"


def to_markdown(result: dict) -> str:
    lines = ["# Phase 1 -- Raw Data Inspection Report", "",
             f"Generated (UTC): {result['generated_at_utc']}  ",
             f"Total rows across files: {result['total_rows']:,}  ",
             f"Zone lookup present: {result['zone_lookup_found']} "
             f"({result['zone_count']} zones)" if result["zone_lookup_found"] else
             "Zone lookup present: False", "",
             "All numbers below are counts measured from the raw files. Nothing has been removed yet.", ""]

    lines += ["## Schema vs. data dictionary", ""]
    for m in result["months"]:
        s = m["schema_vs_dictionary"]
        lines.append(f"- **{m['month']}**: missing={s['missing'] or 'none'}, "
                     f"unexpected={s['unexpected'] or 'none'}, "
                     f"case differences={[d['file'] for d in s['case_diffs']] or 'none'}, "
                     f"optional present={s['optional_present'] or 'none'}")
    lines += ["", "## Type drift between months", ""]
    if result["type_drift"]:
        for d in result["type_drift"]:
            lines.append(f"- `{d['column']}`: {d['types_by_month']}")
    else:
        lines.append("- None detected.")

    lines += ["", "## Volume and coverage", "",
              "| Month | Rows | Min pickup | Max pickup | Pickups outside month |",
              "|---|---:|---|---|---:|"]
    for m in result["months"]:
        out = m["checks"].get("pickup_outside_file_month", 0)
        lines.append(f"| {m['month']} | {m['row_count']:,} | {m.get('min_pickup')} | "
                     f"{m.get('max_pickup')} | {out:,} ({pct(out, m['row_count'])}) |")

    lines += ["", "## Data-quality signals (count and % of month)", ""]
    check_names = sorted({k for m in result["months"] for k in m["checks"]})
    header = "| Check | " + " | ".join(m["month"] for m in result["months"]) + " |"
    lines += [header, "|---|" + "---:|" * len(result["months"])]
    for name in ["exact_duplicate_rows"] + check_names:
        cells = []
        for m in result["months"]:
            n = m["exact_duplicate_rows"] if name == "exact_duplicate_rows" else m["checks"].get(name, 0)
            cells.append(f"{n:,} ({pct(n, m['row_count'])})")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    lines += ["", "## Null counts", ""]
    for m in result["months"]:
        nulls = ", ".join(f"{k}={v:,}" for k, v in m["nulls"].items()) or "none"
        lines.append(f"- **{m['month']}**: {nulls}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Profile raw TLC yellow taxi Parquet files.")
    p.add_argument("--raw-dir", type=Path, default=config.RAW_DIR)
    p.add_argument("--out-dir", type=Path, default=config.REPORTS_DIR)
    args = p.parse_args(argv)

    result = inspect(args.raw_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "phase1_inspection.json").write_text(json.dumps(result, indent=2, default=str))
    (args.out_dir / "phase1_inspection.md").write_text(to_markdown(result))
    print(f"Reports written to {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
