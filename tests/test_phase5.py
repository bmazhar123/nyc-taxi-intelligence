"""
Phase 5 tests: prove the quality checks PASS on a correct warehouse and
FAIL when we deliberately break it. A check that never fails is useless,
so the "tamper" test is the important one.
"""
import shutil
from datetime import datetime

import duckdb
import pyarrow.parquet as pq
import pytest

from src import build_warehouse as bw
from src import config, quality_checks as qc, run_sql
from src.clean import run as clean_run
from tests.test_phase1 import make_trips

D = datetime


def trip(day, hour=8, **kw):
    return {"tpep_pickup_datetime": D(2024, 1, day, hour), "tpep_dropoff_datetime": D(2024, 1, day, hour, 20),
            "PULocationID": 2, "DOLocationID": 3, **kw}


@pytest.fixture(scope="module")
def mini(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("p5")
    raw, proc, rep, docs = (tmp / x for x in ("raw", "processed", "reports", "docs"))
    raw.mkdir()
    rows = [trip(d) for d in range(1, 32)]                                       # one trip every day of January
    rows += [trip(10, hour=h, VendorID=6, payment_type=1, tip_amount=0.0) for h in (9, 10)]   # a NEW tip gap
    rows += [trip(11, hour=h, VendorID=1, RatecodeID=99, payment_type=1, tip_amount=0.0) for h in (9, 10)]  # known gap
    rows += [trip(12, tip_amount=-1.0, total_amount=-5.0)]                       # removed in cleaning
    pq.write_table(make_trips(rows), raw / "yellow_tripdata_2024-01.parquet")
    (raw / "taxi_zone_lookup.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n2,Queens,Jamaica Bay,Boro Zone\n3,Bronx,Allerton,Boro Zone\n"
        "264,Unknown,N/A,N/A\n265,N/A,Outside of NYC,N/A\n")
    clean_run(raw, proc, rep)
    db = tmp / "taxi.duckdb"
    bw.run(processed_dir=proc, raw_dir=raw, warehouse_path=db, reports_dir=rep, docs_dir=docs)
    params = {**qc.default_params(raw, proc), "min_segment_trips": 1}
    return db, rep, params


def by_name(results):
    return {r["name"]: r for r in results}


def test_all_error_checks_pass_on_a_correct_warehouse(mini):
    db, rep, params = mini
    res = qc.run(warehouse_path=db, reports_dir=rep, params=params)   # would raise if any error check failed
    errors = [r for r in res if r["severity"] == "error"]
    assert len(errors) >= 8 and all(r["status"] == "PASS" for r in errors)
    assert (rep / "phase5_quality_report.md").exists()


def test_tip_gap_warning_flags_new_gap_but_not_the_excluded_one(mini):
    db, rep, params = mini
    gap = by_name(qc.run(warehouse_path=db, reports_dir=rep, params=params))["11_tip_recording_gaps"]
    assert gap["status"] == "FAIL" and gap["severity"] == "warn"
    vendors = {row[0] for row in gap["rows"]}
    assert vendors == {"Myle Technologies Inc"}       # vendor 6 flagged; rate code 99 already excluded


def test_checks_catch_a_tampered_warehouse(mini, tmp_path):
    db, rep, params = mini
    bad = tmp_path / "bad.duckdb"
    shutil.copy(db, bad)
    con = duckdb.connect(str(bad))
    con.execute("INSERT INTO fact_trips SELECT * FROM fact_trips ORDER BY trip_id LIMIT 1")   # duplicate a trip
    con.execute("UPDATE fact_trips SET pu_location_id = 999 "
                "WHERE trip_id = (SELECT MAX(trip_id) FROM fact_trips)")                     # orphan zone
    con.execute("UPDATE fact_trips SET trip_distance = 0.01, total_amount = 900 "
                "WHERE trip_id = (SELECT MIN(trip_id) + 1 FROM fact_trips)")                 # breaks a cleaning rule
    con.close()

    res = by_name(qc.run(warehouse_path=bad, reports_dir=tmp_path, params=params, fail_on_error=False))
    for name in ("01_rows_reconcile_end_to_end", "02_amounts_reconcile_end_to_end", "03_views_reconcile_with_fact",
                 "04_trip_id_unique", "06_foreign_keys", "07_cleaning_rules_hold"):
        assert res[name]["status"] == "FAIL", name
    assert res["05_required_fields_not_null"]["status"] == "PASS"

    with pytest.raises(AssertionError, match="error-level check"):
        qc.run(warehouse_path=bad, reports_dir=tmp_path, params=params)


def test_every_check_file_declares_severity_and_reason():
    for path in sorted(config.CHECKS_DIR.glob("*.sql")):
        meta = qc.parse_check(path.read_text(encoding="utf-8"))
        assert meta["severity"] in ("error", "warn") and meta.get("why"), path.name


def test_placeholder_fill_leaves_regex_braces_alone():
    assert qc.fill(r"x > {max_speed_mph} AND '\d{4}'", {"max_speed_mph": 100}) == r"x > 100 AND '\d{4}'"
