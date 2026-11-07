"""
Phase 2 -- Cleaning / ETL.

Turns the raw monthly Parquet files into ONE cleaned, consistently shaped
dataset, and writes a log explaining every row that was removed.

Design (each choice comes from a Phase 1 finding):

  1. HARMONISE the schema first. Each file is mapped onto the official
     data dictionary case-insensitively ("Airport_fee" -> airport_fee),
     cast to fixed types, and renamed to snake_case. Documented columns a
     file lacks (e.g. cbd_congestion_fee before 2025) become NULL. Columns
     not in the dictionary are dropped and logged.

  2. FLAG, don't silently delete. Every rule is evaluated on every row as
     an independent true/false column. Each removed row then gets exactly
     ONE exclusion_reason -- the first rule it fails, in a fixed order --
     so the per-rule counts add up exactly to the total removed.

  3. RECONCILE. raw rows = kept + excluded, and raw total_amount =
     kept + excluded (to the cent). If either fails, the run stops.

  4. KEEP-BUT-FLAG rows that are real trips with incomplete or odd data
     (Flex Fare trips with missing fields, zero distance, unknown passenger
     count, catch-all zones). Analysis can filter them per metric.

Outputs:
  data/processed/trips_clean.parquet      kept rows + quality flags
  data/processed/trips_excluded.parquet   removed rows + exclusion_reason (for audit)
  reports/phase2_cleaning_log.json / .md  every decision with row counts

Usage (from the project root):
  python -m src.clean
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from src import config
from src.inspect_data import compare_schema, find_trip_files, q, read_schema

# --------------------------------------------------------------------------
# Exclusion rules, in the order they are applied. A row that fails several
# rules is assigned to the FIRST one here.
# --------------------------------------------------------------------------
RULES = [
    {
        "name": "outside_file_month",
        "sql": "pickup_datetime < month_start OR pickup_datetime >= month_start + INTERVAL 1 MONTH",
        "why": "Pickup is not in the month the file covers. Phase 1 found bad clocks (2002, 2009) "
               "and boundary trips that belong to the previous/next month; keeping them would "
               "double-count once neighbouring months are loaded.",
    },
    {
        "name": "exact_duplicate",
        "sql": "dup_rn > 1",
        "why": "Every field identical to an earlier row. The first copy is kept.",
    },
    {
        "name": "reversal_pair",
        "sql": "in_reversal_pair",
        "why": "A negative row that exactly cancels a positive row (same vendor, times, zones, "
               "distance, and opposite total_amount), e.g. the -$10.50/+$10.50 pair in Phase 1. "
               "BOTH rows are removed: the charge was reversed, so the trip contributed no "
               "money, and keeping only the positive row would overstate revenue.",
    },
    {
        "name": "nonpositive_duration",
        "sql": "duration_sec <= 0",
        "why": "Drop-off at or before pickup is physically impossible.",
    },
    {
        "name": "duration_over_limit",
        "sql": f"duration_sec > {config.MAX_DURATION_HOURS * 3600}",
        "why": f"Longer than {config.MAX_DURATION_HOURS} hours is not a single taxi trip.",
    },
    {
        "name": "unmatched_negative_amount",
        "sql": " OR ".join(f"{c} < 0" for c in config.CLEAN_MONEY_COLUMNS),
        "why": "A negative money value with no matching original charge. It cannot be "
               "interpreted (refund of what?), and mixing it into sums would understate amounts.",
    },
    {
        "name": "implausible_speed",
        "sql": f"duration_sec > 0 AND trip_distance > 0 "
               f"AND trip_distance / (duration_sec / 3600.0) > {config.MAX_SPEED_MPH}",
        "why": f"Average speed above {config.MAX_SPEED_MPH} mph: distance and/or times are wrong.",
    },
    {
        "name": "implausible_amount",
        "sql": f"total_amount > {config.AMOUNT_REVIEW_FLOOR} AND (trip_distance <= 0 "
               f"OR total_amount / trip_distance > {config.MAX_AMOUNT_PER_MILE})",
        "why": f"Charged over ${config.AMOUNT_REVIEW_FLOOR} with zero distance or more than "
               f"${config.MAX_AMOUNT_PER_MILE}/mile (e.g. $334,145 for a 0-mile, 3-minute trip). "
               f"Legitimate expensive trips reviewed ran $3.6-$25.5/mile.",
    },
]

# Kept rows carry these flags so each metric can decide what to include.
FLAGS = {
    "flag_flex_fare_incomplete": "payment_type = 0 AND passenger_count IS NULL",
    "flag_zero_distance": "trip_distance = 0",
    "flag_passenger_unknown": "passenger_count IS NULL OR passenger_count = 0",
    "flag_catchall_zone": (f"pu_location_id IN {config.CATCHALL_ZONE_IDS} "
                           f"OR do_location_id IN {config.CATCHALL_ZONE_IDS}"),
    "flag_zero_total": "total_amount = 0",
}

DATA_COLS = [clean for clean, _ in config.HARMONIZED_SCHEMA.values()]
PAIR_KEY = ["vendor_id", "pickup_datetime", "dropoff_datetime",
            "pu_location_id", "do_location_id", "trip_distance"]


# --------------------------------------------------------------------------
# Step 1 -- harmonise each file into the same shape
# --------------------------------------------------------------------------
def harmonized_select(con, path: Path, month: str) -> tuple[str, dict]:
    """Build a SELECT that reads one raw file into the standard schema."""
    raw_schema = read_schema(con, path)
    cmp = compare_schema(list(raw_schema))
    missing_core = [c for c in config.CORE_COLUMNS if c not in cmp["column_map"]]
    if missing_core:
        raise ValueError(f"{path.name} is missing core columns {missing_core}; cannot clean it.")

    exprs, filled_null = [], []
    for canonical, (clean, typ) in config.HARMONIZED_SCHEMA.items():
        actual = cmp["column_map"].get(canonical)
        if actual is None:
            filled_null.append(canonical)
            exprs.append(f"CAST(NULL AS {typ}) AS {clean}")
        else:
            exprs.append(f"CAST({q(actual)} AS {typ}) AS {clean}")

    month_num = int(month.replace("-", ""))
    exprs += [
        # Deterministic ID: YYYYMM followed by the row's position in its file.
        f"CAST({month_num} AS BIGINT) * 100000000 + file_row_number AS trip_id",
        f"'{path.name}' AS source_file",
        f"'{month}' AS source_month",
        f"DATE '{month}-01' AS month_start",
    ]
    sql = (f"SELECT {', '.join(exprs)} "
           f"FROM read_parquet('{path.as_posix()}', file_row_number = true)")
    events = {
        "file": path.name,
        "raw_columns": len(raw_schema),
        "renamed_by_case": cmp["case_diffs"],
        "dropped_unexpected": cmp["unexpected"],
        "filled_with_null": filled_null,
        "type_casts": {c: raw_schema[a] for c, a in cmp["column_map"].items()
                       if raw_schema[a] != config.HARMONIZED_SCHEMA[c][1]},
    }
    return sql, events


# --------------------------------------------------------------------------
# Step 2 -- evaluate every rule on every row
# --------------------------------------------------------------------------
def annotate(con) -> None:
    """Create table `annotated`: harmonised rows + rule booleans + exclusion_reason + flags."""
    key = ", ".join(PAIR_KEY)
    pair_join = " AND ".join(f"n.{k} = p.{k}" for k in PAIR_KEY)
    con.execute(f"""
        CREATE OR REPLACE TABLE annotated AS
        WITH base AS (
            SELECT *, date_diff('second', pickup_datetime, dropoff_datetime) AS duration_sec
            FROM raw_union
        ),
        dups AS (
            SELECT trip_id,
                   ROW_NUMBER() OVER (PARTITION BY {', '.join(DATA_COLS)} ORDER BY trip_id) AS dup_rn
            FROM base
        ),
        -- Reversal matching: number negatives and positives within each identical
        -- trip key + amount in cents, then pair them 1-to-1 by that number.
        neg AS (
            SELECT trip_id, {key}, CAST(ROUND(-total_amount * 100) AS BIGINT) AS cents,
                   ROW_NUMBER() OVER (PARTITION BY {key}, ROUND(-total_amount * 100) ORDER BY trip_id) AS rn
            FROM base WHERE total_amount < 0
        ),
        pos AS (
            SELECT trip_id, {key}, CAST(ROUND(total_amount * 100) AS BIGINT) AS cents,
                   ROW_NUMBER() OVER (PARTITION BY {key}, ROUND(total_amount * 100) ORDER BY trip_id) AS rn
            FROM base WHERE total_amount > 0
        ),
        pairs AS (
            SELECT n.trip_id AS neg_id, p.trip_id AS pos_id
            FROM neg n JOIN pos p ON {pair_join} AND n.cents = p.cents AND n.rn = p.rn
        ),
        paired AS (
            SELECT neg_id AS trip_id FROM pairs UNION ALL SELECT pos_id FROM pairs
        )
        SELECT b.*, d.dup_rn, (pr.trip_id IS NOT NULL) AS in_reversal_pair
        FROM base b
        JOIN dups d USING (trip_id)
        LEFT JOIN paired pr USING (trip_id)
    """)

    rule_cols = ", ".join(f"COALESCE({r['sql']}, false) AS r_{r['name']}" for r in RULES)
    con.execute(f"CREATE OR REPLACE TABLE annotated AS SELECT *, {rule_cols} FROM annotated")

    case = " ".join(f"WHEN r_{r['name']} THEN '{r['name']}'" for r in RULES)
    flag_cols = ", ".join(f"COALESCE({sql}, false) AS {name}" for name, sql in FLAGS.items())
    con.execute(f"""
        CREATE OR REPLACE TABLE annotated AS
        SELECT *, CASE {case} END AS exclusion_reason,
               duration_sec / 60.0 AS trip_duration_minutes,
               {flag_cols}
        FROM annotated
    """)


# --------------------------------------------------------------------------
# Step 3 -- measure, reconcile, and write outputs
# --------------------------------------------------------------------------
def cents(x) -> int:
    return int(round((x or 0) * 100))


def build_log(con, schema_events: list[dict]) -> dict:
    one = lambda sql: con.execute(sql).fetchone()

    raw_rows, raw_cents = one("SELECT COUNT(*), SUM(total_amount) FROM annotated")
    kept_rows, kept_cents = one("SELECT COUNT(*), SUM(total_amount) FROM annotated WHERE exclusion_reason IS NULL")
    excl_rows, excl_cents = one("SELECT COUNT(*), SUM(total_amount) FROM annotated WHERE exclusion_reason IS NOT NULL")

    rules = []
    for r in RULES:
        n_seq, amt = one(f"SELECT COUNT(*), SUM(total_amount) FROM annotated WHERE exclusion_reason = '{r['name']}'")
        n_any = one(f"SELECT COUNT(*) FROM annotated WHERE r_{r['name']}")[0]
        rules.append({"rule": r["name"], "rows_removed": n_seq, "rows_matching_any_order": n_any,
                      "pct_of_raw": round(100 * n_seq / raw_rows, 4) if raw_rows else 0,
                      "total_amount_removed": round(amt or 0, 2), "why": r["why"]})

    flags = {name: one(f"SELECT COUNT(*) FROM annotated WHERE exclusion_reason IS NULL AND {name}")[0]
             for name in FLAGS}

    neg_total = one("SELECT COUNT(*) FROM annotated WHERE total_amount < 0")[0]
    neg_paired = one("SELECT COUNT(*) FROM annotated WHERE total_amount < 0 AND in_reversal_pair")[0]
    flex_total, flex_complete = one("""
        SELECT COUNT(*), COUNT(*) FILTER (WHERE passenger_count IS NOT NULL)
        FROM annotated WHERE payment_type = 0""")

    def pctiles(col: str) -> dict:
        vals = one(f"""SELECT quantile_cont({col}, [0.5, 0.95, 0.99, 0.999]), MAX({col})
                       FROM annotated WHERE exclusion_reason IS NULL""")
        labels = ["p50", "p95", "p99", "p99_9"]
        out = dict(zip(labels, [round(v, 2) for v in (vals[0] or [None] * 4) if v is not None]))
        out["max"] = round(vals[1], 2) if vals[1] is not None else None
        return out

    zero_dist_by_rate = con.execute("""
        SELECT ratecode_id, COUNT(*) AS n, ROUND(AVG(fare_amount), 2) AS avg_fare
        FROM annotated WHERE exclusion_reason IS NULL AND trip_distance = 0
        GROUP BY ALL ORDER BY n DESC LIMIT 8""").fetchall()

    per_month = con.execute("""
        SELECT source_month, COUNT(*) AS raw,
               COUNT(*) FILTER (WHERE exclusion_reason IS NULL) AS kept
        FROM annotated GROUP BY ALL ORDER BY 1""").fetchall()

    log = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raw_rows": raw_rows, "kept_rows": kept_rows, "excluded_rows": excl_rows,
        "pct_kept": round(100 * kept_rows / raw_rows, 4) if raw_rows else 0,
        "raw_total_amount": round(raw_cents or 0, 2),
        "kept_total_amount": round(kept_cents or 0, 2),
        "excluded_total_amount": round(excl_cents or 0, 2),
        "per_month": [{"month": m, "raw": r, "kept": k} for m, r, k in per_month],
        "rules": rules,
        "flags_on_kept_rows": flags,
        "reversal_matching": {"negative_total_rows": neg_total, "negative_rows_paired": neg_paired,
                              "pct_paired": round(100 * neg_paired / neg_total, 2) if neg_total else None},
        "flex_fare_check": {"payment_type_0_rows": flex_total,
                            "payment_type_0_with_passenger_count": flex_complete},
        "distributions_kept": {c: pctiles(c) for c in
                               ["trip_distance", "trip_duration_minutes", "fare_amount", "total_amount"]},
        "zero_distance_by_ratecode": [{"ratecode_id": r, "rows": n, "avg_fare": f}
                                      for r, n, f in zero_dist_by_rate],
        "schema_events": schema_events,
        "thresholds": {"max_duration_hours": config.MAX_DURATION_HOURS,
                       "max_speed_mph": config.MAX_SPEED_MPH,
                       "catchall_zone_ids": list(config.CATCHALL_ZONE_IDS)},
    }

    # ---- Reconciliation: stop the run if anything does not add up ----
    seq_sum = sum(r["rows_removed"] for r in rules)
    checks = {
        "rows: raw = kept + excluded": raw_rows == kept_rows + excl_rows,
        "rows: excluded = sum of rule counts": excl_rows == seq_sum,
        "amount: raw = kept + excluded (cents)": cents(raw_cents) == cents(kept_cents) + cents(excl_cents),
        "every kept row has a pickup in its file month": one(
            "SELECT COUNT(*) FROM annotated WHERE exclusion_reason IS NULL AND r_outside_file_month")[0] == 0,
    }
    log["reconciliation"] = checks
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise AssertionError(f"Reconciliation failed: {failed}")
    return log


def write_outputs(con, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    kept_cols = ", ".join(["trip_id"] + DATA_COLS + ["trip_duration_minutes", "source_month"] + list(FLAGS))
    excl_cols = ", ".join(["trip_id"] + DATA_COLS + ["source_file", "source_month", "exclusion_reason"])
    con.execute(f"""COPY (SELECT {kept_cols} FROM annotated WHERE exclusion_reason IS NULL)
                    TO '{(out_dir / 'trips_clean.parquet').as_posix()}' (FORMAT PARQUET)""")
    con.execute(f"""COPY (SELECT {excl_cols} FROM annotated WHERE exclusion_reason IS NOT NULL)
                    TO '{(out_dir / 'trips_excluded.parquet').as_posix()}' (FORMAT PARQUET)""")


def to_markdown(log: dict) -> str:
    n = log["raw_rows"]
    L = ["# Phase 2 -- Cleaning Log", "",
         f"Generated (UTC): {log['generated_at_utc']}", "",
         f"- Raw rows: **{n:,}**",
         f"- Kept: **{log['kept_rows']:,}** ({log['pct_kept']}%)",
         f"- Excluded: **{log['excluded_rows']:,}**",
         f"- Raw total_amount: ${log['raw_total_amount']:,.2f} | kept ${log['kept_total_amount']:,.2f} "
         f"| excluded ${log['excluded_total_amount']:,.2f}", "",
         "## Exclusion rules (applied in this order; each row counted once)", "",
         "| # | Rule | Rows removed | % of raw | Rows matching in any order | total_amount removed | Why |",
         "|---|---|---:|---:|---:|---:|---|"]
    for i, r in enumerate(log["rules"], 1):
        L.append(f"| {i} | `{r['rule']}` | {r['rows_removed']:,} | {r['pct_of_raw']}% | "
                 f"{r['rows_matching_any_order']:,} | ${r['total_amount_removed']:,.2f} | {r['why']} |")

    L += ["", "## Reconciliation", ""]
    L += [f"- {'PASS' if ok else 'FAIL'} — {k}" for k, ok in log["reconciliation"].items()]

    L += ["", "## Rows per month", "", "| Month | Raw | Kept |", "|---|---:|---:|"]
    L += [f"| {m['month']} | {m['raw']:,} | {m['kept']:,} |" for m in log["per_month"]]

    L += ["", "## Kept-but-flagged rows", "",
          "These are real trips with incomplete or unusual fields. They stay in the data; "
          "each metric decides whether to include them.", ""]
    L += [f"- `{k}`: {v:,}" for k, v in log["flags_on_kept_rows"].items()]

    rv, fx = log["reversal_matching"], log["flex_fare_check"]
    L += ["", "## Open questions from Phase 1, now measured", "",
          f"- Negative total_amount rows: {rv['negative_total_rows']:,}; matched to a positive twin: "
          f"{rv['negative_rows_paired']:,} ({rv['pct_paired']}%).",
          f"- payment_type 0 (Flex Fare) rows: {fx['payment_type_0_rows']:,}; of these, rows that DO have "
          f"passenger_count: {fx['payment_type_0_with_passenger_count']:,}."]

    L += ["", "## Distributions of kept rows", "", "| Column | p50 | p95 | p99 | p99.9 | max |",
          "|---|---:|---:|---:|---:|---:|"]
    for col, d in log["distributions_kept"].items():
        L.append(f"| {col} | {d.get('p50')} | {d.get('p95')} | {d.get('p99')} | {d.get('p99_9')} | {d.get('max')} |")

    L += ["", "## Zero-distance kept trips by RatecodeID", "", "| RatecodeID | Rows | Avg fare |", "|---|---:|---:|"]
    L += [f"| {z['ratecode_id']} | {z['rows']:,} | {z['avg_fare']} |" for z in log["zero_distance_by_ratecode"]]

    L += ["", "## Schema harmonisation", ""]
    for e in log["schema_events"]:
        L.append(f"- **{e['file']}**: renamed={[d['file'] + '→' + d['dictionary'] for d in e['renamed_by_case']] or 'none'}, "
                 f"dropped={e['dropped_unexpected'] or 'none'}, filled NULL={e['filled_with_null'] or 'none'}, "
                 f"type casts={e['type_casts'] or 'none'}")
    L.append("")
    return "\n".join(L)


def run(raw_dir: Path, processed_dir: Path, reports_dir: Path) -> dict:
    files = find_trip_files(raw_dir)
    if not files:
        raise FileNotFoundError(f"No yellow_tripdata_*.parquet in {raw_dir}. Run src.download first.")

    con = duckdb.connect()
    tmp = processed_dir / "_duckdb_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory = '{tmp.as_posix()}'")  # lets DuckDB spill to disk on a small laptop

    selects, events = [], []
    for month, path in files.items():
        sql, ev = harmonized_select(con, path, month)
        selects.append(sql)
        events.append(ev)
    con.execute("CREATE TABLE raw_union AS " + " UNION ALL ".join(selects))
    print(f"  harmonised {len(files)} file(s)")

    annotate(con)
    log = build_log(con, events)
    write_outputs(con, processed_dir)

    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase2_cleaning_log.json").write_text(json.dumps(log, indent=2, default=str))
    (reports_dir / "phase2_cleaning_log.md").write_text(to_markdown(log), encoding="utf-8")
    print(f"  kept {log['kept_rows']:,} of {log['raw_rows']:,} rows; reconciliation passed")
    return log


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Clean raw TLC yellow taxi files.")
    p.add_argument("--raw-dir", type=Path, default=config.RAW_DIR)
    p.add_argument("--processed-dir", type=Path, default=config.PROCESSED_DIR)
    p.add_argument("--reports-dir", type=Path, default=config.REPORTS_DIR)
    a = p.parse_args(argv)
    run(a.raw_dir, a.processed_dir, a.reports_dir)
    print(f"Outputs in {a.processed_dir} and {a.reports_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
