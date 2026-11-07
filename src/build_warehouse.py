"""
Phase 3 -- Build the DuckDB analytical warehouse (star schema).

Input : data/processed/trips_clean.parquet   (Phase 2)
        data/raw/taxi_zone_lookup.csv        (official zone lookup)
        data/raw/manifest.json, reports/phase2_cleaning_log.json (lineage)
Output: data/warehouse/taxi.duckdb
        reports/phase3_warehouse_summary.md
        docs/data_dictionary.md

Star schema
                     dim_date      dim_time
                         \\           /
   dim_zone (pickup) -- fact_trips -- dim_zone (drop-off)
                       /     |     \\
              dim_vendor dim_ratecode dim_payment_type

Every build is a FULL rebuild into a temporary file that replaces the old
database only after all integrity checks pass, so a failed build never
leaves you with a half-built warehouse.

Usage:  python -m src.build_warehouse
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb

from src import config
from src.data_dictionary import TABLES, to_markdown

U = config.UNKNOWN_KEY


# --------------------------------------------------------------------------
# US federal holidays (rule-based, so it works for any year)
# --------------------------------------------------------------------------
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-th given weekday of a month (weekday: Mon=0). n = -1 means last."""
    if n > 0:
        d = date(year, month, 1)
        d += timedelta(days=(weekday - d.weekday()) % 7)
        return d + timedelta(weeks=n - 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    d = nxt - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    """Fixed-date holidays on Saturday are observed Friday, on Sunday the Monday after."""
    return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d


def us_federal_holidays(year: int) -> dict[date, str]:
    fixed = [(1, 1, "New Year's Day"), (6, 19, "Juneteenth"), (7, 4, "Independence Day"),
             (11, 11, "Veterans Day"), (12, 25, "Christmas Day")]
    out = {_observed(date(year, m, d)): name for m, d, name in fixed}
    out.update({
        _nth_weekday(year, 1, 0, 3): "Martin Luther King Jr. Day",
        _nth_weekday(year, 2, 0, 3): "Presidents' Day",
        _nth_weekday(year, 5, 0, -1): "Memorial Day",
        _nth_weekday(year, 9, 0, 1): "Labor Day",
        _nth_weekday(year, 10, 0, 2): "Columbus Day",
        _nth_weekday(year, 11, 3, 4): "Thanksgiving Day",
    })
    return out


# --------------------------------------------------------------------------
# Dimensions
# --------------------------------------------------------------------------
def code_dim(con, table: str, key: str, name_col: str, codes: dict, extra: str = "") -> None:
    """Small lookup dimension from a data-dictionary code map, plus an 'unknown' row."""
    rows = [(U, "Not recorded")] + sorted(codes.items())
    con.execute(f"CREATE TABLE {table} ({key} INTEGER PRIMARY KEY, {name_col} VARCHAR NOT NULL)")
    con.executemany(f"INSERT INTO {table} VALUES (?, ?)", rows)
    if extra:
        con.execute(extra)


def build_dimensions(con, zone_csv: Path, months: list[str]) -> None:
    # Zones
    con.execute(f"""
        CREATE TABLE dim_zone AS
        SELECT CAST(LocationID AS INTEGER) AS location_id, Borough AS borough, Zone AS zone,
               service_zone,
               LocationID IN {config.CATCHALL_ZONE_IDS} AS is_catchall,
               service_zone IN ('Airports', 'EWR') AS is_airport
        FROM read_csv_auto('{zone_csv.as_posix()}')
    """)
    con.execute("ALTER TABLE dim_zone ADD PRIMARY KEY (location_id)")

    # Code dimensions straight from the data dictionary
    code_dim(con, "dim_vendor", "vendor_key", "vendor_name", config.VENDOR_CODES)
    code_dim(con, "dim_ratecode", "ratecode_key", "ratecode_name", config.RATECODE_CODES,
             "ALTER TABLE dim_ratecode ADD COLUMN is_flat_rate BOOLEAN;"
             "UPDATE dim_ratecode SET is_flat_rate = ratecode_key IN (2, 5)")
    code_dim(con, "dim_payment_type", "payment_type_key", "payment_type_name", config.PAYMENT_TYPE_CODES,
             "ALTER TABLE dim_payment_type ADD COLUMN tips_recorded BOOLEAN;"
             "UPDATE dim_payment_type SET tips_recorded = payment_type_key = 1")

    # Dates: every day from the first to the last month loaded
    start = date.fromisoformat(f"{min(months)}-01")
    last = date.fromisoformat(f"{max(months)}-01")
    end = date(last.year + (last.month == 12), last.month % 12 + 1, 1) - timedelta(days=1)
    con.execute("CREATE TEMP TABLE holidays (holiday_date DATE, name VARCHAR)")
    hol = [(d, n) for y in range(start.year, end.year + 1) for d, n in us_federal_holidays(y).items()]
    con.executemany("INSERT INTO holidays VALUES (?, ?)", hol)
    con.execute(f"""
        CREATE TABLE dim_date AS
        SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
               CAST(d AS DATE)              AS full_date,
               year(d)                      AS year,
               quarter(d)                   AS quarter,
               month(d)                     AS month,
               monthname(d)                 AS month_name,
               strftime(d, '%Y-%m')         AS year_month,
               day(d)                       AS day_of_month,
               isodow(d)                    AS day_of_week,
               dayname(d)                   AS day_name,
               isodow(d) IN (6, 7)          AS is_weekend,
               weekofyear(d)                AS iso_week,
               h.name IS NOT NULL           AS is_us_federal_holiday,
               h.name                       AS holiday_name
        FROM range(DATE '{start}', DATE '{end}' + INTERVAL 1 DAY, INTERVAL 1 DAY) r(d)
        LEFT JOIN holidays h ON h.holiday_date = CAST(r.d AS DATE)
        ORDER BY 1
    """)
    con.execute("ALTER TABLE dim_date ADD PRIMARY KEY (date_key)")

    # Hours
    con.execute("""
        CREATE TABLE dim_time AS
        SELECT h AS hour,
               lpad(CAST(h AS VARCHAR), 2, '0') || ':00' AS hour_label,
               CASE WHEN h < 6 THEN 'Overnight' WHEN h < 10 THEN 'AM peak'
                    WHEN h < 16 THEN 'Midday'   WHEN h < 20 THEN 'PM peak' ELSE 'Evening' END AS time_band,
               CASE WHEN h < 6 THEN 1 WHEN h < 10 THEN 2 WHEN h < 16 THEN 3
                    WHEN h < 20 THEN 4 ELSE 5 END AS time_band_order
        FROM range(24) t(h)
    """)
    con.execute("ALTER TABLE dim_time ADD PRIMARY KEY (hour)")


# --------------------------------------------------------------------------
# Fact table
# --------------------------------------------------------------------------
def build_fact(con, clean_parquet: Path) -> None:
    con.execute(f"""
        CREATE TABLE fact_trips AS
        SELECT trip_id,
               pickup_datetime, dropoff_datetime,
               CAST(strftime(pickup_datetime, '%Y%m%d') AS INTEGER) AS pickup_date_key,
               hour(pickup_datetime)                                AS pickup_hour,
               pu_location_id, do_location_id,
               COALESCE(vendor_id, {U})    AS vendor_key,
               COALESCE(ratecode_id, {U})  AS ratecode_key,
               COALESCE(payment_type, {U}) AS payment_type_key,
               store_and_fwd_flag, passenger_count, trip_distance, trip_duration_minutes,
               fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge,
               congestion_surcharge, airport_fee, cbd_congestion_fee, total_amount,
               payment_type = 1 AS is_credit_card,
               flag_flex_fare_incomplete, flag_zero_distance, flag_passenger_unknown,
               flag_catchall_zone, flag_zero_total,
               trip_duration_minutes > {config.LONG_DURATION_MINUTES} AS flag_long_duration,
               source_month
        FROM read_parquet('{clean_parquet.as_posix()}')
    """)
    # No PRIMARY KEY index here on purpose: on ~18M rows it costs a lot of laptop
    # memory. Uniqueness of trip_id is verified in integrity_checks() instead.


# --------------------------------------------------------------------------
# Lineage tables
# --------------------------------------------------------------------------
def build_meta(con, manifest: Path, cleaning_log: Path) -> None:
    con.execute("CREATE TABLE meta_source_files (file_name VARCHAR, source_url VARCHAR, "
                "size_bytes BIGINT, sha256 VARCHAR, downloaded_at_utc VARCHAR)")
    if manifest.exists():
        files = json.loads(manifest.read_text()).get("files", {})
        con.executemany("INSERT INTO meta_source_files VALUES (?, ?, ?, ?, ?)",
                        [(k, v.get("source_url"), v.get("size_bytes"), v.get("sha256"),
                          v.get("downloaded_at_utc")) for k, v in files.items()])

    con.execute("CREATE TABLE meta_cleaning_rules (rule_order INTEGER, rule VARCHAR, "
                "rows_removed BIGINT, total_amount_removed DOUBLE, why VARCHAR)")
    if cleaning_log.exists():
        rules = json.loads(cleaning_log.read_text()).get("rules", [])
        con.executemany("INSERT INTO meta_cleaning_rules VALUES (?, ?, ?, ?, ?)",
                        [(i, r["rule"], r["rows_removed"], r["total_amount_removed"], r["why"])
                         for i, r in enumerate(rules, 1)])

    built = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute(f"""
        CREATE TABLE meta_build AS
        SELECT '{built}' AS built_at_utc,
               string_agg(DISTINCT source_month, ',' ORDER BY source_month) AS months_loaded,
               COUNT(*) AS fact_rows,
               ROUND(SUM(total_amount), 2) AS fact_total_amount
        FROM fact_trips
    """)


def apply_comments(con) -> None:
    """Write the data dictionary into the database itself."""
    esc = lambda s: s.replace("'", "''")
    for table, t in TABLES.items():
        con.execute(f"COMMENT ON TABLE {table} IS '{esc(t['description'])}'")
        for col, desc in t["columns"].items():
            con.execute(f"COMMENT ON COLUMN {table}.{col} IS '{esc(desc)}'")


# --------------------------------------------------------------------------
# Integrity checks -- the build fails if any of these fail
# --------------------------------------------------------------------------
def integrity_checks(con, clean_parquet: Path) -> dict[str, bool]:
    one = lambda sql: con.execute(sql).fetchone()[0]
    src_rows, src_cents = con.execute(
        f"SELECT COUNT(*), ROUND(SUM(total_amount) * 100) FROM read_parquet('{clean_parquet.as_posix()}')").fetchone()
    fact_rows, fact_cents = con.execute("SELECT COUNT(*), ROUND(SUM(total_amount) * 100) FROM fact_trips").fetchone()

    orphan = lambda col, dim, key: one(
        f"SELECT COUNT(*) FROM fact_trips f ANTI JOIN {dim} d ON f.{col} = d.{key}")
    return {
        "fact rows = cleaned rows": src_rows == fact_rows,
        "trip_id is unique": one("SELECT COUNT(*) - COUNT(DISTINCT trip_id) FROM fact_trips") == 0,
        "fact total_amount = cleaned total_amount (cents)": src_cents == fact_cents,
        "no orphan pickup dates": orphan("pickup_date_key", "dim_date", "date_key") == 0,
        "no orphan pickup hours": orphan("pickup_hour", "dim_time", "hour") == 0,
        "no orphan pickup zones": orphan("pu_location_id", "dim_zone", "location_id") == 0,
        "no orphan drop-off zones": orphan("do_location_id", "dim_zone", "location_id") == 0,
        "no orphan vendors": orphan("vendor_key", "dim_vendor", "vendor_key") == 0,
        "no orphan rate codes": orphan("ratecode_key", "dim_ratecode", "ratecode_key") == 0,
        "no orphan payment types": orphan("payment_type_key", "dim_payment_type", "payment_type_key") == 0,
        "every warehouse column is documented": one(
            "SELECT COUNT(*) FROM duckdb_columns() WHERE schema_name = 'main' AND NOT internal "
            "AND database_name <> 'temp' "
            "AND (comment IS NULL OR comment = '')") == 0,
    }


def summary_markdown(con, checks: dict[str, bool]) -> str:
    counts = con.execute("""
        SELECT table_name, estimated_size FROM duckdb_tables()
        WHERE schema_name = 'main' AND NOT temporary ORDER BY table_name
    """).fetchall()
    exact = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t, _ in counts}
    b = con.execute("SELECT * FROM meta_build").fetchone()
    L = ["# Phase 3 -- Warehouse Build Summary", "",
         f"Built (UTC): {b[0]}  ", f"Months loaded: {b[1]}  ",
         f"fact_trips rows: {b[2]:,}  ", f"fact_trips total_amount: ${b[3]:,.2f}", "",
         "## Integrity checks", ""]
    L += [f"- {'PASS' if ok else 'FAIL'} — {name}" for name, ok in checks.items()]
    L += ["", "## Tables", "", "| Table | Rows |", "|---|---:|"]
    L += [f"| `{t}` | {n:,} |" for t, n in exact.items()]
    flags = con.execute("""
        SELECT SUM(flag_flex_fare_incomplete::INT), SUM(flag_zero_distance::INT), SUM(flag_passenger_unknown::INT),
               SUM(flag_catchall_zone::INT), SUM(flag_zero_total::INT), SUM(flag_long_duration::INT)
        FROM fact_trips""").fetchone()
    names = ["flex_fare_incomplete", "zero_distance", "passenger_unknown", "catchall_zone",
             "zero_total", "long_duration"]
    L += ["", "## Flags in fact_trips", ""] + [f"- `flag_{n}`: {v:,}" for n, v in zip(names, flags)]
    holidays = con.execute("SELECT full_date, holiday_name FROM dim_date WHERE is_us_federal_holiday ORDER BY 1").fetchall()
    L += ["", "## Holidays in dim_date", ""] + [f"- {d}: {n}" for d, n in holidays] + [""]
    return "\n".join(L)


# --------------------------------------------------------------------------
def run(processed_dir: Path = config.PROCESSED_DIR, raw_dir: Path = config.RAW_DIR,
        warehouse_path: Path = config.WAREHOUSE_PATH, reports_dir: Path = config.REPORTS_DIR,
        docs_dir: Path = config.DOCS_DIR) -> dict[str, bool]:
    clean = processed_dir / "trips_clean.parquet"
    zones = raw_dir / "taxi_zone_lookup.csv"
    for p in (clean, zones):
        if not p.exists():
            raise FileNotFoundError(f"Missing {p}. Run src.download and src.clean first.")

    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = warehouse_path.with_suffix(".building.duckdb")
    tmp.unlink(missing_ok=True)

    con = duckdb.connect(str(tmp))
    months = [r[0] for r in con.execute(
        f"SELECT DISTINCT source_month FROM read_parquet('{clean.as_posix()}') ORDER BY 1").fetchall()]
    build_dimensions(con, zones, months)
    build_fact(con, clean)
    build_meta(con, raw_dir / "manifest.json", reports_dir / "phase2_cleaning_log.json")
    apply_comments(con)
    checks = integrity_checks(con, clean)
    summary = summary_markdown(con, checks)
    con.close()

    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise AssertionError(f"Warehouse integrity checks failed: {failed}. "
                             f"The previous warehouse was left untouched; inspect {tmp}.")

    try:
        tmp.replace(warehouse_path)  # swap in only after every check passed
    except PermissionError:
        raise PermissionError(f"Could not replace {warehouse_path}. Close any program using it "
                              f"(Power BI, DBeaver, another Python window) and run again.")

    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase3_warehouse_summary.md").write_text(summary, encoding="utf-8")
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "data_dictionary.md").write_text(to_markdown(), encoding="utf-8")
    print(f"  warehouse built: {warehouse_path}  ({len(months)} month(s), all {len(checks)} checks passed)")
    return checks


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Build the DuckDB star-schema warehouse.").parse_args(argv)
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
