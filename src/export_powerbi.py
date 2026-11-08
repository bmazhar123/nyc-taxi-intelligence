"""
Phase 7 -- Export compact, reconciled tables for Power BI.

Why not load the 19.8M-row fact table into Power BI directly?
  A laptop CAN do it, but the file gets large and slow, and every metric
  rule (tip eligibility, fare-per-mile eligibility...) would have to be
  re-written in DAX, where it could drift from the SQL definitions.

Instead this script pre-aggregates trips to one row per
  date x hour x pickup zone x payment type x airport direction
and stores numerators and denominators (not ratios), so DAX can divide
them correctly at ANY level: a day, a zone, a month, the whole period.
Eligibility rules come from v_trips, so Power BI and SQL use the exact
same definitions.

Outputs (dashboards/data/, git-ignored, rebuild any time):
  agg_trips_hourly.parquet   main fact table for the dashboard
  agg_od_monthly.parquet     origin -> destination flows (zone drill-through)
  dim_date / dim_time / dim_zone / dim_dropoff_zone / dim_payment_type .parquet
  export_summary.json        row counts and reconciliation results
Also writes reports/phase7_dashboard_validation.md: the numbers the finished
dashboard must show, so you can verify every visual against SQL.

Usage:
  python -m src.export_powerbi           # Parquet (recommended)
  python -m src.export_powerbi --csv     # also write CSV copies, if Parquet won't load
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from src import config

DEC = "DECIMAL(18, 2)"


def money(expr: str) -> str:
    """Exact cent-level sum; NULLs (e.g. Flex Fare surcharges) count as 0.
    Cast back to DECIMAL(18,2) because DuckDB widens sums to 38 digits, which Power BI handles less cleanly."""
    return f"CAST(SUM(CAST(COALESCE({expr}, 0) AS {DEC})) AS {DEC})"


TABLES = {
    "agg_trips_hourly": f"""
        SELECT pickup_date_key,
               CAST(pickup_hour AS INTEGER)                               AS pickup_hour,
               CAST(pu_location_id AS INTEGER)                            AS pu_location_id,
               CAST(payment_type_key AS INTEGER)                          AS payment_type_key,
               CASE WHEN pu_is_airport THEN 'From airport'
                    WHEN do_is_airport THEN 'To airport'
                    ELSE 'Non-airport' END                                AS airport_direction,
               COUNT(*)                                                   AS trips,
               {money('total_amount')}                                    AS total_amount_sum,
               {money('fare_amount')}                                     AS fare_amount_sum,
               {money('tip_amount')}                                      AS tip_amount_sum,
               {money('tolls_amount')}                                    AS tolls_amount_sum,
               CAST({money('extra')} + {money('mta_tax')} + {money('improvement_surcharge')}
                 + {money('congestion_surcharge')} + {money('airport_fee')}
                 + {money('cbd_congestion_fee')} AS {DEC})                AS taxes_surcharges_sum,
               SUM(trip_distance)                                         AS distance_sum,
               COALESCE(SUM(trip_duration_minutes) FILTER (WHERE duration_eligible), 0)        AS duration_min_sum,
               COUNT(*) FILTER (WHERE duration_eligible)                                       AS duration_trips,
               COALESCE(SUM(fare_amount)   FILTER (WHERE fare_per_mile_eligible), 0)          AS fpm_fare_sum,
               COALESCE(SUM(trip_distance) FILTER (WHERE fare_per_mile_eligible), 0)          AS fpm_distance_sum,
               COALESCE(SUM(trip_duration_minutes) FILTER (WHERE fare_per_mile_eligible), 0)  AS fpm_minutes_sum,
               COALESCE(SUM(tip_amount)  FILTER (WHERE tip_rate_eligible), 0)                 AS tip_card_sum,
               COALESCE(SUM(fare_amount) FILTER (WHERE tip_rate_eligible), 0)                 AS fare_card_sum,
               COUNT(*) FILTER (WHERE tip_rate_eligible)                                       AS card_trips_eligible,
               COUNT(*) FILTER (WHERE tip_rate_eligible AND tip_amount > 0)                    AS card_trips_tipped,
               COUNT(*) FILTER (WHERE flag_passenger_unknown)                                  AS passenger_unknown_trips,
               COUNT(*) FILTER (WHERE flag_long_duration)                                      AS long_duration_trips,
               COUNT(*) FILTER (WHERE flag_zero_distance)                                      AS zero_distance_trips,
               COUNT(*) FILTER (WHERE flag_catchall_zone)                                      AS catchall_zone_trips
        FROM v_trips
        GROUP BY ALL
    """,
    "agg_od_monthly": f"""
        SELECT CAST(date_trunc('month', pickup_datetime) AS DATE)         AS month_start,
               CAST(pu_location_id AS INTEGER)                            AS pu_location_id,
               CAST(do_location_id AS INTEGER)                            AS do_location_id,
               COUNT(*)                                                   AS trips,
               {money('total_amount')}                                    AS total_amount_sum,
               SUM(trip_distance)                                         AS distance_sum
        FROM fact_trips
        GROUP BY ALL
    """,
    "dim_date": """
        SELECT date_key, full_date, year, quarter, month, month_name, year_month,
               day_of_month, day_of_week, day_name,
               is_weekend, CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
               iso_week, is_us_federal_holiday, holiday_name
        FROM dim_date
    """,
    "dim_time": "SELECT * FROM dim_time",
    "dim_payment_type": "SELECT * FROM dim_payment_type",
    # dim_zone and dim_dropoff_zone come from build_zone_tables(), which joins in the map points
}


def build_zone_tables(con, centroids: Path) -> tuple[dict, bool]:
    has_points = centroids.exists()
    if has_points:
        con.execute(f"""CREATE OR REPLACE TEMP TABLE zone_points AS
                        SELECT CAST(location_id AS INTEGER) AS location_id,
                               CAST(latitude AS DOUBLE) AS latitude, CAST(longitude AS DOUBLE) AS longitude
                        FROM read_csv_auto('{centroids.as_posix()}')""")
    else:
        con.execute("""CREATE OR REPLACE TEMP TABLE zone_points
                       (location_id INTEGER, latitude DOUBLE, longitude DOUBLE)""")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE zone_export AS
        SELECT z.location_id, z.borough, z.zone, z.service_zone, z.is_catchall, z.is_airport,
               p.latitude, p.longitude
        FROM dim_zone z LEFT JOIN zone_points p USING (location_id)
    """)
    zone_tables = {
        "dim_zone": "SELECT * FROM zone_export",
        "dim_dropoff_zone": """
            SELECT location_id AS do_location_id, borough AS do_borough, zone AS do_zone,
                   is_catchall AS do_is_catchall, is_airport AS do_is_airport
            FROM zone_export
        """,
    }
    return zone_tables, has_points


def reconcile(con, out: Path) -> dict[str, bool]:
    """Exported tables must add back up to the warehouse exactly (rows and cents)."""
    p = lambda name: f"read_parquet('{(out / f'{name}.parquet').as_posix()}')"
    one = lambda sql: con.execute(sql).fetchone()
    fact_rows, fact_cents = one(f"SELECT COUNT(*), SUM(CAST(total_amount AS {DEC})) FROM fact_trips")
    agg_rows, agg_cents = one(f"SELECT SUM(trips), SUM(total_amount_sum) FROM {p('agg_trips_hourly')}")
    od_rows, od_cents = one(f"SELECT SUM(trips), SUM(total_amount_sum) FROM {p('agg_od_monthly')}")
    parts_diff = one(f"""SELECT SUM(total_amount_sum) - SUM(fare_amount_sum + tip_amount_sum + tolls_amount_sum
                                                            + taxes_surcharges_sum)
                          FROM {p('agg_trips_hourly')}""")[0]
    orphans = one(f"""SELECT COUNT(*) FROM {p('agg_trips_hourly')} a
                      ANTI JOIN {p('dim_date')} d ON a.pickup_date_key = d.date_key""")[0]
    return {
        "agg_trips_hourly trips = fact rows": agg_rows == fact_rows,
        "agg_trips_hourly total_amount = fact total_amount (cents)": agg_cents == fact_cents,
        "agg_od_monthly trips = fact rows": od_rows == fact_rows,
        "agg_od_monthly total_amount = fact total_amount (cents)": od_cents == fact_cents,
        "every agg date exists in dim_date": orphans == 0,
        "_info: total_amount minus its itemised components ($)": float(parts_diff or 0),
    }


def expected_values(con, out: Path) -> str:
    """Numbers the dashboard must reproduce -- computed from the exported files, like Power BI will."""
    p = lambda name: f"read_parquet('{(out / f'{name}.parquet').as_posix()}')"
    one = lambda sql: con.execute(sql).fetchone()
    a, d, z, pt = p("agg_trips_hourly"), p("dim_date"), p("dim_zone"), p("dim_payment_type")
    t = one(f"""SELECT SUM(trips), SUM(total_amount_sum), SUM(fare_amount_sum) / SUM(trips),
                       SUM(duration_min_sum) / SUM(duration_trips), SUM(fpm_fare_sum) / SUM(fpm_distance_sum),
                       SUM(fpm_distance_sum) / (SUM(fpm_minutes_sum) / 60), SUM(tip_card_sum) / SUM(fare_card_sum),
                       SUM(card_trips_tipped) / SUM(card_trips_eligible), SUM(trips) / (SELECT COUNT(*) FROM {d})
                FROM {a}""")
    monthly = con.execute(f"""
        -- "per day" divides by EVERY calendar day in the month (as the DAX measure does),
        -- not only the days that happen to have trips
        WITH days AS (SELECT year_month, COUNT(*) AS n_days FROM {d} GROUP BY 1)
        SELECT d.year_month, SUM(a.trips) / MAX(days.n_days) AS per_day,
               100.0 * SUM(a.trips) FILTER (WHERE a.payment_type_key = 0) / SUM(a.trips) AS flex
        FROM {a} a JOIN {d} d ON a.pickup_date_key = d.date_key JOIN days USING (year_month)
        GROUP BY 1 ORDER BY 1""").fetchall()
    daytype = con.execute(f"""
        SELECT d.day_type, SUM(a.trips) / (SELECT COUNT(*) FROM {d} x WHERE x.day_type = d.day_type)
        FROM {a} a JOIN {d} d ON a.pickup_date_key = d.date_key GROUP BY 1 ORDER BY 1""").fetchall()
    boroughs = con.execute(f"""
        SELECT z.borough, SUM(a.trips), 100 * SUM(a.tip_card_sum) / NULLIF(SUM(a.fare_card_sum), 0)
        FROM {a} a JOIN {z} z ON a.pu_location_id = z.location_id
        GROUP BY 1 ORDER BY 2 DESC""").fetchall()
    peak = one(f"""SELECT SUM(fpm_distance_sum) / (SUM(fpm_minutes_sum) / 60), SUM(fpm_fare_sum) / SUM(fpm_distance_sum)
                   FROM {a} WHERE pickup_hour = 17""")
    airport = con.execute(f"""SELECT airport_direction, SUM(trips), 100.0 * SUM(total_amount_sum) /
                                     (SELECT SUM(total_amount_sum) FROM {a})
                              FROM {a} GROUP BY 1 ORDER BY 2 DESC""").fetchall()

    f = lambda v, n=2: f"{v:,.{n}f}" if v is not None else "(blank)"
    L = ["# Phase 7 -- Dashboard Validation Values", "",
         f"Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')} from `dashboards/data/`.", "",
         "After building the dashboard, **clear all slicers** and compare each visual with these numbers. "
         "They are computed from the same exported files Power BI loads, using the same formulas as the DAX "
         "measures, so they should match exactly (allowing for display rounding). A mismatch means a "
         "relationship or measure is wrong.", "",
         "## KPI cards (no filters)", "", "| Measure | Expected |", "|---|---:|",
         f"| Trips | {t[0]:,} |", f"| Recorded Charges | ${f(t[1])} |", f"| Avg Fare | ${f(t[2])} |",
         f"| Avg Duration (min) | {f(t[3], 1)} |", f"| Fare per Mile (std rate) | ${f(t[4])} |",
         f"| Avg Speed (mph) | {f(t[5], 1)} |", f"| Tip % of Fare (card) | {f(100 * t[6], 1)}% |",
         f"| % Card Trips Tipped | {f(100 * t[7], 1)}% |", f"| Trips per Day | {f(t[8], 0)} |", "",
         "## By month", "", "| Month | Trips per Day | Flex Fare Share |", "|---|---:|---:|"]
    L += [f"| {m} | {f(pd, 0)} | {f(fl)}% |" for m, pd, fl in monthly]
    L += ["", "## Day type (Trips per Day)", "", "| Day type | Trips per Day |", "|---|---:|"]
    L += [f"| {dt} | {f(v, 0)} |" for dt, v in daytype]
    L += ["", "## Pickup borough", "", "| Borough | Trips | Tip % of Fare (card) |", "|---|---:|---:|"]
    L += [f"| {b} | {n:,} | {f(tp, 1)}% |" for b, n, tp in boroughs]
    L += ["", "## Airport direction", "", "| Direction | Trips | % of Recorded Charges |", "|---|---:|---:|"]
    L += [f"| {dname} | {n:,} | {f(pc, 1)}% |" for dname, n, pc in airport]
    L += ["", "## 5 PM (hour 17)", "", f"- Avg Speed: {f(peak[0], 1)} mph", f"- Fare per Mile: ${f(peak[1])}", ""]
    return "\n".join(L)


def run(warehouse_path: Path = config.WAREHOUSE_PATH, out: Path = config.POWERBI_DATA_DIR,
        reports_dir: Path = config.REPORTS_DIR, centroids: Path = config.ZONE_CENTROIDS_PATH,
        views_dir: Path = config.SQL_DIR / "views", csv: bool = False) -> dict:
    if not warehouse_path.exists():
        raise FileNotFoundError(f"{warehouse_path} not found. Build the warehouse first.")
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        apply_views_temp(con, views_dir)
        zone_tables, has_points = build_zone_tables(con, centroids)
        counts = {}
        for name, sql in {**TABLES, **zone_tables}.items():
            target = out / f"{name}.parquet"
            con.execute(f"COPY ({sql}) TO '{target.as_posix()}' (FORMAT PARQUET, COMPRESSION SNAPPY)")
            if csv:
                con.execute(f"COPY ({sql}) TO '{(out / f'{name}.csv').as_posix()}' (HEADER)")
            counts[name] = con.execute(f"SELECT COUNT(*) FROM read_parquet('{target.as_posix()}')").fetchone()[0]
            print(f"  {name}: {counts[name]:,} rows")
        checks = reconcile(con, out)
        failed = [k for k, ok in checks.items() if not k.startswith("_info") and not ok]
        if failed:
            raise AssertionError(f"Export does not reconcile with the warehouse: {failed}")
        validation = expected_values(con, out)
    finally:
        con.close()

    summary = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "row_counts": counts, "reconciliation": checks, "zone_map_points": has_points}
    (out / "export_summary.json").write_text(json.dumps(summary, indent=2))
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase7_dashboard_validation.md").write_text(validation, encoding="utf-8")
    if not has_points:
        print("  NOTE: no zone map points (run `python -m src.zone_centroids`); latitude/longitude are blank.")
    print(f"  reconciliation passed; files in {out}")
    return summary


def apply_views_temp(con, views_dir: Path) -> None:
    """The warehouse is opened read-only here, so create the views as TEMP views in this session."""
    for path in sorted(views_dir.glob("*.sql")):
        sql = path.read_text(encoding="utf-8").replace("CREATE OR REPLACE VIEW", "CREATE OR REPLACE TEMP VIEW")
        con.execute(sql)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export reconciled tables for Power BI.")
    p.add_argument("--csv", action="store_true", help="also write CSV copies")
    a = p.parse_args(argv)
    run(csv=a.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
