"""
Phase 1 tests. These use TINY HAND-MADE fixture files with problems we
inserted on purpose, so we know the exact right answer for every count.
They test that the code measures correctly -- they say nothing about the
real TLC data.

Run:  pytest -q
"""
from datetime import datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src import config
from src.download import validate_months
from src.inspect_data import compare_schema, inspect, type_drift


def make_trips(rows: list[dict], vendor_col: str = "VendorID",
               passenger_type=pa.int64(), extra_cols: dict | None = None) -> pa.Table:
    """Build an Arrow table with the dictionary's columns, filling defaults."""
    base = {
        "tpep_pickup_datetime": datetime(2024, 1, 10, 8, 0),
        "tpep_dropoff_datetime": datetime(2024, 1, 10, 8, 20),
        "passenger_count": 1, "trip_distance": 3.0, "RatecodeID": 1,
        "store_and_fwd_flag": "N", "PULocationID": 1, "DOLocationID": 2,
        "payment_type": 1, "fare_amount": 15.0, "extra": 0.0, "mta_tax": 0.5,
        "tip_amount": 3.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0,
        "total_amount": 19.5, "congestion_surcharge": 0.0, "airport_fee": 0.0,
    }
    full = [{vendor_col: 2, **base, **r} for r in rows]
    cols = {k: [r[k] for r in full] for k in full[0]}
    arrays = {k: pa.array(v, type=passenger_type) if k == "passenger_count" else pa.array(v)
              for k, v in cols.items()}
    if extra_cols:
        arrays.update({k: pa.array(v) for k, v in extra_cols.items()})
    return pa.table(arrays)


@pytest.fixture
def raw_dir(tmp_path):
    # January: 6 rows with known problems
    jan = make_trips([
        {},                                                    # clean
        {},                                                    # exact duplicate of row 0
        {"tpep_dropoff_datetime": datetime(2024, 1, 10, 7, 0)},  # dropoff before pickup
        {"trip_distance": 0.0, "fare_amount": -5.0},           # zero distance + negative fare
        {"tpep_pickup_datetime": datetime(2023, 12, 31, 23, 0),
         "tpep_dropoff_datetime": datetime(2023, 12, 31, 23, 10)},  # outside file month
        {"payment_type": 9, "PULocationID": 999, "passenger_count": None},  # bad codes + null
    ])
    pq.write_table(jan, tmp_path / "yellow_tripdata_2024-01.parquet")

    # February: different capitalisation + passenger_count as DOUBLE (type drift)
    feb = make_trips(
        [{"tpep_pickup_datetime": datetime(2024, 2, 1, 9, 0),
          "tpep_dropoff_datetime": datetime(2024, 2, 2, 10, 0)}],  # > 24h
        vendor_col="vendorid", passenger_type=pa.float64(),
    )
    pq.write_table(feb, tmp_path / "yellow_tripdata_2024-02.parquet")

    (tmp_path / "taxi_zone_lookup.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n1,EWR,Newark Airport,EWR\n2,Queens,Jamaica Bay,Boro Zone\n"
    )
    return tmp_path


def test_validate_months_rejects_bad_format():
    with pytest.raises(ValueError):
        validate_months(["2024-13"])
    assert validate_months(["2024-02", "2024-01", "2024-01"]) == ["2024-01", "2024-02"]


def test_compare_schema_is_case_insensitive_and_flags_extras():
    cols = [c.lower() for c in config.EXPECTED_COLUMNS] + ["mystery_col", "cbd_congestion_fee"]
    res = compare_schema(cols)
    assert res["missing"] == []
    assert res["unexpected"] == ["mystery_col"]
    assert res["optional_present"] == ["cbd_congestion_fee"]
    assert {"dictionary": "VendorID", "file": "vendorid"} in res["case_diffs"]


def test_compare_schema_reports_missing():
    res = compare_schema([c for c in config.EXPECTED_COLUMNS if c != "airport_fee"])
    assert res["missing"] == ["airport_fee"]


def test_type_drift_detected():
    drift = type_drift({"2024-01": {"passenger_count": "BIGINT"},
                        "2024-02": {"passenger_count": "DOUBLE"}})
    assert drift[0]["column"] == "passenger_count"


def test_inspect_counts_match_injected_problems(raw_dir):
    result = inspect(raw_dir)
    jan, feb = result["months"]
    assert result["total_rows"] == 7
    assert jan["row_count"] == 6
    assert jan["exact_duplicate_rows"] == 1
    assert jan["checks"]["dropoff_not_after_pickup"] == 1
    assert jan["checks"]["distance_zero"] == 1
    assert jan["checks"]["negative_fare_amount"] == 1
    assert jan["checks"]["pickup_outside_file_month"] == 1
    assert jan["checks"]["undocumented_payment_type"] == 1
    assert jan["checks"]["PULocationID_not_in_zone_lookup"] == 1
    assert jan["nulls"] == {"passenger_count": 1}
    assert feb["checks"]["duration_over_24h"] == 1
    assert feb["schema_vs_dictionary"]["case_diffs"] == [{"dictionary": "VendorID", "file": "vendorid"}]
    assert any(d["column"] == "passenger_count" for d in result["type_drift"])
