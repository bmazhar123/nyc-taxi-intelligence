"""
Phase 4 tests: run every view and analysis query on a tiny warehouse whose
correct answers were worked out by hand, so metric DEFINITIONS are tested,
not just "the SQL didn't crash".
"""
from datetime import datetime

import duckdb
import pyarrow.parquet as pq
import pytest

from src import build_warehouse as bw
from src import config, run_sql
from src.clean import run as clean_run
from tests.test_phase1 import make_trips

D = datetime


def trip(day, hour=8, **kw):
    """A trip on 2024-01-<day> at <hour>, between two ordinary (non-airport) zones."""
    base = {"tpep_pickup_datetime": D(2024, 1, day, hour),
            "tpep_dropoff_datetime": D(2024, 1, day, hour, 20),
            "PULocationID": 2, "DOLocationID": 3}
    return {**base, **kw}


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("p4")
    raw, proc, rep, docs = (tmp / x for x in ("raw", "processed", "reports", "docs"))
    raw.mkdir()
    rows = [
        # Wednesday 2024-01-10 -- the day the metric tests check by hand
        trip(10, payment_type=1, fare_amount=10.0, tip_amount=2.0, trip_distance=2.0, total_amount=13.0),
        trip(10, payment_type=1, fare_amount=20.0, tip_amount=6.0, trip_distance=4.0, total_amount=27.0),
        trip(10, payment_type=2, fare_amount=30.0, tip_amount=0.0, trip_distance=3.0, total_amount=31.0),  # cash
        trip(10, RatecodeID=2, payment_type=1, fare_amount=70.0, tip_amount=0.0, trip_distance=0.0,
             total_amount=75.0, DOLocationID=132),                                                          # JFK flat
        # Mondays: two normal (Jan 8, Jan 22) and MLK Day (Jan 15)
        trip(8), trip(8, hour=9), trip(22), trip(22, hour=17),
        trip(15),
        # Saturday: one normal card trip, one rate-code-99 card trip with no tip recorded
        trip(13, hour=23),
        trip(13, hour=22, VendorID=1, RatecodeID=99, payment_type=1, fare_amount=20.0,
             tip_amount=0.0, total_amount=21.0),
    ]
    pq.write_table(make_trips(rows), raw / "yellow_tripdata_2024-01.parquet")
    (raw / "taxi_zone_lookup.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "2,Queens,Jamaica Bay,Boro Zone\n3,Bronx,Allerton,Boro Zone\n"
        "132,Queens,JFK Airport,Airports\n264,Unknown,N/A,N/A\n265,N/A,Outside of NYC,N/A\n")
    clean_run(raw, proc, rep)
    db = tmp / "taxi.duckdb"
    bw.run(processed_dir=proc, raw_dir=raw, warehouse_path=db, reports_dir=rep, docs_dir=docs)
    res = run_sql.run(warehouse_path=db, sql_dir=config.SQL_DIR,
                      results_dir=rep / "sql_results", reports_dir=rep)
    return {r["name"]: r for r in res}, db, rep


def as_dicts(r):
    return [dict(zip(r["cols"], row)) for row in r["rows"]]


def test_every_query_runs_and_is_documented(results):
    res, _, rep = results
    files = sorted(p.stem for p in (config.SQL_DIR / "analysis").glob("*.sql"))
    assert len(files) >= 12 and sorted(res) == files
    for r in res.values():
        assert {"Question", "Technique", "Caveat"} <= set(r["meta"]), r["name"]
        assert (rep / "sql_results" / f"{r['name']}.csv").exists()
    assert (rep / "phase4_sql_results.md").read_text(encoding="utf-8").count("**Question:**") == len(files)


def test_tip_rate_uses_credit_card_only_and_fare_per_mile_uses_standard_rate(results):
    _, db, _ = results
    con = duckdb.connect(str(db), read_only=True)
    trips, tip_pct, fpm = con.execute(
        "SELECT trips, tip_pct_of_fare, fare_per_mile FROM v_daily_kpis WHERE pickup_date = DATE '2024-01-10'"
    ).fetchone()
    assert trips == 4
    # card trips only: (2 + 6) / (10 + 20 + 70 JFK card fare) -- cash trip excluded
    assert tip_pct == pytest.approx(100 * 8 / 100, abs=0.01)
    # standard rate, distance > 0: (10 + 20 + 30) / (2 + 4 + 3); JFK flat fare excluded
    assert fpm == pytest.approx(60 / 9, abs=0.01)


def test_weekday_weekend_divides_by_days_not_rows(results):
    res, *_ = results
    rows = {r["day_type"]: r for r in as_dicts(res["02_weekday_vs_weekend"])}
    assert rows["Weekend"]["days"] == 1 and rows["Weekend"]["avg_trips_per_day"] == 2
    # weekdays with trips: Jan 8 (2), 10 (4), 15 (1), 22 (2) -> 9 trips / 4 days
    assert rows["Weekday"]["days"] == 4
    assert rows["Weekday"]["avg_trips_per_day"] == round(9 / 4)


def test_holiday_compared_with_same_weekday_baseline(results):
    res, *_ = results
    (mlk,) = as_dicts(res["12_holidays_vs_typical_day"])
    assert mlk["holiday_name"] == "Martin Luther King Jr. Day"
    assert mlk["trips"] == 1 and mlk["typical_trips_same_weekday"] == 2
    assert mlk["pct_vs_typical"] == -50.0


def test_airport_classification(results):
    res, *_ = results
    types = {r["trip_type"]: r["trips"] for r in as_dicts(res["08_airport_vs_other"])}
    assert types == {"Non-airport": 10, "To airport": 1}


def test_rate_code_99_excluded_from_tip_rate(results):
    _, db, _ = results
    con = duckdb.connect(str(db), read_only=True)
    tip_pct, card_trips = con.execute(
        "SELECT tip_pct_of_fare, card_trips FROM v_daily_kpis WHERE pickup_date = DATE '2024-01-13'").fetchone()
    assert card_trips == 1                 # the rate-code-99 trip is not tip-eligible
    assert tip_pct == pytest.approx(20.0)  # 3 / 15, not 3 / 35
