"""
Phase 3 tests: build the warehouse from a tiny cleaned dataset and check the
star schema is complete, consistent and documented.
"""
from datetime import date, datetime

import duckdb
import pyarrow.parquet as pq
import pytest

from src import build_warehouse as bw
from src.clean import run as clean_run
from src.data_dictionary import TABLES
from tests.test_phase1 import make_trips

D = datetime


@pytest.fixture
def warehouse(tmp_path):
    raw, proc, rep, docs = (tmp_path / x for x in ("raw", "processed", "reports", "docs"))
    raw.mkdir()
    pq.write_table(make_trips([
        {},                                                                          # weekday, 08:00
        {"tpep_pickup_datetime": D(2024, 1, 13, 23), "tpep_dropoff_datetime": D(2024, 1, 13, 23, 30)},  # Saturday
        {"tpep_pickup_datetime": D(2024, 1, 15, 9), "tpep_dropoff_datetime": D(2024, 1, 15, 9, 20)},    # MLK Day
        {"payment_type": 0, "passenger_count": None, "RatecodeID": None},             # Flex Fare -> unknown ratecode
        {"tpep_dropoff_datetime": D(2024, 1, 10, 12, 30)},                           # 4.5h -> long duration flag
        {"PULocationID": 264},
    ]), raw / "yellow_tripdata_2024-01.parquet")
    pq.write_table(make_trips([
        {"tpep_pickup_datetime": D(2024, 2, 19, 7), "tpep_dropoff_datetime": D(2024, 2, 19, 7, 15)},    # Presidents' Day
    ]), raw / "yellow_tripdata_2024-02.parquet")
    (raw / "taxi_zone_lookup.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "1,EWR,Newark Airport,EWR\n2,Queens,Jamaica Bay,Boro Zone\n"
        "132,Queens,JFK Airport,Airports\n264,Unknown,N/A,N/A\n265,N/A,Outside of NYC,N/A\n")

    clean_run(raw, proc, rep)
    db = tmp_path / "warehouse" / "taxi.duckdb"
    checks = bw.run(processed_dir=proc, raw_dir=raw, warehouse_path=db, reports_dir=rep, docs_dir=docs)
    con = duckdb.connect(str(db), read_only=True)
    yield con, checks, rep, docs
    con.close()


def test_all_integrity_checks_pass(warehouse):
    _, checks, _, _ = warehouse
    assert checks and all(checks.values()), checks


def test_star_schema_tables_exist_and_fact_is_complete(warehouse):
    con, *_ = warehouse
    tables = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    assert set(TABLES) <= tables
    assert con.execute("SELECT COUNT(*) FROM fact_trips").fetchone()[0] == 7


def test_dim_date_covers_both_months_with_holidays_and_weekends(warehouse):
    con, *_ = warehouse
    n, lo, hi = con.execute("SELECT COUNT(*), MIN(full_date), MAX(full_date) FROM dim_date").fetchone()
    assert (n, lo, hi) == (60, date(2024, 1, 1), date(2024, 2, 29))      # 2024 is a leap year
    hol = dict(con.execute("SELECT full_date, holiday_name FROM dim_date WHERE is_us_federal_holiday").fetchall())
    assert hol == {date(2024, 1, 1): "New Year's Day", date(2024, 1, 15): "Martin Luther King Jr. Day",
                   date(2024, 2, 19): "Presidents' Day"}
    assert con.execute("SELECT is_weekend, day_name FROM dim_date WHERE date_key = 20240113").fetchone() == (True, "Saturday")


def test_unknown_codes_join_to_not_recorded_row(warehouse):
    con, *_ = warehouse
    name = con.execute("""SELECT r.ratecode_name FROM fact_trips f JOIN dim_ratecode r USING (ratecode_key)
                          WHERE f.flag_flex_fare_incomplete""").fetchone()[0]
    assert name == "Not recorded"


def test_flags_and_dimension_attributes(warehouse):
    con, *_ = warehouse
    assert con.execute("SELECT COUNT(*) FROM fact_trips WHERE flag_long_duration").fetchone()[0] == 1
    assert con.execute("SELECT is_airport FROM dim_zone WHERE location_id = 132").fetchone()[0]
    assert con.execute("SELECT is_catchall FROM dim_zone WHERE location_id = 264").fetchone()[0]
    assert con.execute("SELECT time_band FROM dim_time WHERE hour = 8").fetchone()[0] == "AM peak"


def test_every_column_is_documented_in_db_and_markdown(warehouse):
    con, _, rep, docs = warehouse
    undocumented = con.execute("""SELECT table_name, column_name FROM duckdb_columns()
                                  WHERE schema_name = 'main' AND NOT internal
                                  AND (comment IS NULL OR comment = '')""").fetchall()
    assert undocumented == []
    md = (docs / "data_dictionary.md").read_text(encoding="utf-8")
    assert "`fact_trips`" in md and "`pickup_date_key`" in md
    assert (rep / "phase3_warehouse_summary.md").exists()


@pytest.mark.parametrize("year,expected", [
    (2021, {date(2021, 7, 5): "Independence Day", date(2021, 12, 24): "Christmas Day"}),   # Sun -> Mon, Sat -> Fri
    (2024, {date(2024, 5, 27): "Memorial Day", date(2024, 6, 19): "Juneteenth",
            date(2024, 11, 28): "Thanksgiving Day"}),
])
def test_holiday_rules(year, expected):
    hol = bw.us_federal_holidays(year)
    for d, name in expected.items():
        assert hol[d] == name
