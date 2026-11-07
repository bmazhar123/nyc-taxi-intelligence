"""
Phase 2 tests: tiny hand-made files where we know exactly which rows each
rule should catch. They test the cleaning LOGIC, not the real TLC data.
"""
from datetime import datetime

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.clean import run
from tests.test_phase1 import make_trips

D = datetime


@pytest.fixture
def cleaned(tmp_path):
    raw, proc, rep = tmp_path / "raw", tmp_path / "processed", tmp_path / "reports"
    raw.mkdir()

    jan = make_trips([
        {},                                                         # 0 clean, kept
        {"tpep_pickup_datetime": D(2024, 1, 11, 9), "tpep_dropoff_datetime": D(2024, 1, 11, 9, 30)},  # 1 clean
        {},                                                         # 2 exact duplicate of row 0
        # 3 + 4: reversal pair (same key, opposite totals)
        {"tpep_pickup_datetime": D(2024, 1, 12, 8), "tpep_dropoff_datetime": D(2024, 1, 12, 8, 10),
         "total_amount": 10.5, "fare_amount": 7.0},
        {"tpep_pickup_datetime": D(2024, 1, 12, 8), "tpep_dropoff_datetime": D(2024, 1, 12, 8, 10),
         "total_amount": -10.5, "fare_amount": -7.0, "mta_tax": -0.5, "improvement_surcharge": -1.0,
         "payment_type": 4},
        # 5: negative with NO matching positive (amount differs) -> unmatched negative
        {"tpep_pickup_datetime": D(2024, 1, 13, 8), "tpep_dropoff_datetime": D(2024, 1, 13, 8, 10),
         "total_amount": -11.0, "fare_amount": -8.0},
        {"tpep_dropoff_datetime": D(2024, 1, 10, 7)},               # 6 dropoff before pickup
        {"tpep_dropoff_datetime": D(2024, 1, 12, 9)},               # 7 > 24 hours
        {"tpep_pickup_datetime": D(2009, 1, 1, 0, 24),
         "tpep_dropoff_datetime": D(2009, 1, 1, 1, 13)},            # 8 outside month (bad clock)
        {"trip_distance": 50.0, "tpep_dropoff_datetime": D(2024, 1, 10, 8, 10)},  # 9 300 mph
        {"payment_type": 0, "passenger_count": None, "RatecodeID": None},  # 10 flex fare: kept + flagged
        {"trip_distance": 0.0},                                     # 11 zero distance: kept + flagged
        {"PULocationID": 264},                                      # 12 catch-all zone: kept + flagged
        # 13: also outside month AND negative -> must count ONCE, under the first rule
        {"tpep_pickup_datetime": D(2023, 12, 31, 23, 50), "tpep_dropoff_datetime": D(2024, 1, 1, 0, 5),
         "total_amount": -5.0},
    ])
    pq.write_table(jan, raw / "yellow_tripdata_2024-01.parquet")

    # February: different capitalisation, float passenger_count, an extra column
    feb = make_trips(
        [{"tpep_pickup_datetime": D(2024, 2, 3, 8), "tpep_dropoff_datetime": D(2024, 2, 3, 8, 20)}],
        vendor_col="vendorid", passenger_type=pa.float64(), extra_cols={"mystery_col": ["x"]},
    )
    pq.write_table(feb, raw / "yellow_tripdata_2024-02.parquet")

    log = run(raw, proc, rep)
    return log, proc


def removed(log, rule):
    return next(r["rows_removed"] for r in log["rules"] if r["rule"] == rule)


def test_each_rule_catches_exactly_its_rows(cleaned):
    log, _ = cleaned
    assert removed(log, "outside_file_month") == 2      # rows 8 and 13
    assert removed(log, "exact_duplicate") == 1
    assert removed(log, "reversal_pair") == 2           # both halves of the pair
    assert removed(log, "nonpositive_duration") == 1
    assert removed(log, "duration_over_limit") == 1
    assert removed(log, "unmatched_negative_amount") == 1
    assert removed(log, "implausible_speed") == 1


def test_row_counts_reconcile(cleaned):
    log, _ = cleaned
    assert log["raw_rows"] == 15
    assert log["kept_rows"] == 6                         # rows 0, 1, 10, 11, 12 + February
    assert log["raw_rows"] == log["kept_rows"] + log["excluded_rows"]
    assert all(log["reconciliation"].values())


def test_overlapping_row_counted_once_under_first_rule(cleaned):
    log, _ = cleaned
    neg = next(r for r in log["rules"] if r["rule"] == "unmatched_negative_amount")
    # Rows 4, 5 and 13 all contain negative amounts, but row 4 was already removed as a
    # reversal_pair and row 13 as outside_file_month -- so only row 5 is charged to this rule.
    assert neg["rows_matching_any_order"] == 3
    assert neg["rows_removed"] == 1


def test_reversal_matching_requires_exact_opposite_amount(cleaned):
    log, _ = cleaned
    assert log["reversal_matching"]["negative_total_rows"] == 3   # rows 4, 5, 13
    assert log["reversal_matching"]["negative_rows_paired"] == 1  # only row 4


def test_flags_on_kept_rows(cleaned):
    log, _ = cleaned
    f = log["flags_on_kept_rows"]
    assert f["flag_flex_fare_incomplete"] == 1
    assert f["flag_zero_distance"] == 1
    assert f["flag_catchall_zone"] == 1


def test_schema_harmonised_across_months(cleaned):
    log, proc = cleaned
    feb = next(e for e in log["schema_events"] if "2024-02" in e["file"])
    assert {"dictionary": "VendorID", "file": "vendorid"} in feb["renamed_by_case"]
    assert feb["dropped_unexpected"] == ["mystery_col"]
    assert "cbd_congestion_fee" in feb["filled_with_null"]

    con = duckdb.connect()
    cols = {r[0]: r[1] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{(proc / 'trips_clean.parquet').as_posix()}')").fetchall()}
    assert cols["passenger_count"] == "INTEGER"
    assert "vendor_id" in cols and "mystery_col" not in cols
    assert con.execute(f"SELECT COUNT(DISTINCT trip_id) = COUNT(*) FROM "
                       f"read_parquet('{(proc / 'trips_clean.parquet').as_posix()}')").fetchone()[0]


def test_excluded_file_is_auditable(cleaned):
    _, proc = cleaned
    con = duckdb.connect()
    reasons = dict(con.execute(
        f"SELECT exclusion_reason, COUNT(*) FROM read_parquet('{(proc / 'trips_excluded.parquet').as_posix()}') "
        f"GROUP BY 1").fetchall())
    assert sum(reasons.values()) == 9
    assert None not in reasons
