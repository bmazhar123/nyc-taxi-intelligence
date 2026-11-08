"""
Phase 7 tests: zone map points and the Power BI export.
"""
import csv
import json
from datetime import datetime

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapefile
from pyproj import CRS, Transformer

from src import build_warehouse as bw
from src import export_powerbi, zone_centroids
from src.clean import run as clean_run
from tests.test_phase1 import make_trips

STATE_PLANE = CRS.from_epsg(2263)    # the projection the TLC shapefile uses (NY Long Island, US feet)
TIMES_SQ = (-73.9855, 40.7580)       # lon, lat


def square(cx, cy, half, clockwise=True):
    pts = [(cx - half, cy - half), (cx - half, cy + half), (cx + half, cy + half), (cx + half, cy - half)]
    pts = pts if clockwise else pts[::-1]
    return pts + [pts[0]]


def write_zones(path, records):
    w = shapefile.Writer(str(path), shapeType=shapefile.POLYGON)
    w.field("LocationID", "N")
    w.field("zone", "C")
    for loc, parts in records:
        w.poly(parts)
        w.record(loc, f"zone {loc}")
    w.close()
    path.with_suffix(".prj").write_text(STATE_PLANE.to_wkt(version="WKT1_ESRI"))


def test_centroid_of_known_location_with_hole_and_split_zone(tmp_path):
    to_sp = Transformer.from_crs(CRS.from_epsg(4326), STATE_PLANE, always_xy=True)
    x, y = to_sp.transform(*TIMES_SQ)
    write_zones(tmp_path / "zones.shp", [
        # zone 1: a square centred on Times Square with a centred hole (centroid must not move)
        (1, [square(x, y, 1000), square(x, y, 200, clockwise=False)]),
        # zone 2 split into two records of equal area 10,000 ft east and west -> centroid in the middle
        (2, [square(x - 10000, y, 500)]),
        (2, [square(x + 10000, y, 500)]),
    ])
    pts = {r["location_id"]: r for r in zone_centroids.compute_centroids(tmp_path / "zones.shp")}
    assert set(pts) == {1, 2}
    for loc in (1, 2):
        assert pts[loc]["longitude"] == pytest.approx(TIMES_SQ[0], abs=1e-5)
        assert pts[loc]["latitude"] == pytest.approx(TIMES_SQ[1], abs=1e-5)


def test_ring_area_sign_and_value():
    a, cx, cy = zone_centroids.ring_area_centroid([(0, 0), (0, 2), (4, 2), (4, 0)])   # clockwise 4x2
    assert abs(a) == 8 and (cx, cy) == (2, 1)


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("p7")
    raw, proc, rep, docs, out = (tmp / x for x in ("raw", "processed", "reports", "docs", "out"))
    raw.mkdir()
    D = datetime
    rows = [
        {"tpep_pickup_datetime": D(2024, 1, d, h), "tpep_dropoff_datetime": D(2024, 1, d, h, 25),
         "PULocationID": pu, "DOLocationID": do, "payment_type": pay}
        for d, h, pu, do, pay in [(3, 8, 2, 3, 1), (3, 17, 132, 2, 1), (6, 23, 2, 132, 2),
                                  (10, 17, 3, 2, 0), (20, 9, 2, 264, 1)]
    ]
    rows[3].update(passenger_count=None, RatecodeID=None)                     # Flex Fare
    pq.write_table(make_trips(rows), raw / "yellow_tripdata_2024-01.parquet")
    (raw / "taxi_zone_lookup.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n2,Queens,Jamaica Bay,Boro Zone\n3,Bronx,Allerton,Boro Zone\n"
        "132,Queens,JFK Airport,Airports\n264,Unknown,N/A,N/A\n265,N/A,Outside of NYC,N/A\n")
    clean_run(raw, proc, rep)
    db = tmp / "taxi.duckdb"
    bw.run(processed_dir=proc, raw_dir=raw, warehouse_path=db, reports_dir=rep, docs_dir=docs)
    centroids = tmp / "zone_centroids.csv"
    centroids.write_text("location_id,latitude,longitude\n2,40.6,-73.8\n132,40.64,-73.78\n")
    summary = export_powerbi.run(warehouse_path=db, out=out, reports_dir=rep, centroids=centroids, csv=True)
    return summary, out, rep, db


def test_export_reconciles_with_warehouse(exported):
    summary, out, *_ = exported
    checks = {k: v for k, v in summary["reconciliation"].items() if not k.startswith("_info")}
    assert checks and all(checks.values())
    assert summary["row_counts"]["dim_date"] == 31 and summary["row_counts"]["dim_zone"] == 5
    assert json.loads((out / "export_summary.json").read_text())["zone_map_points"] is True


def test_airport_direction_and_map_points(exported):
    _, out, *_ = exported
    con = duckdb.connect()
    dirs = dict(con.execute(f"SELECT airport_direction, SUM(trips) FROM "
                            f"'{(out / 'agg_trips_hourly.parquet').as_posix()}' GROUP BY 1").fetchall())
    assert dirs == {"From airport": 1, "To airport": 1, "Non-airport": 3}
    lat = dict(con.execute(f"SELECT location_id, latitude FROM '{(out / 'dim_zone.parquet').as_posix()}'").fetchall())
    assert lat[132] == 40.64 and lat[3] is None          # zone without a point stays blank, not wrong


def test_parquet_types_power_bi_can_read(exported):
    _, out, *_ = exported
    for path in out.glob("*.parquet"):
        for field in pq.read_schema(path):
            t = field.type
            assert not (pa.types.is_decimal(t) and t.precision > 18), f"{path.name}.{field.name}: {t}"
            assert not pa.types.is_large_string(t) and not pa.types.is_dictionary(t), f"{path.name}.{field.name}: {t}"
    assert (out / "agg_trips_hourly.csv").exists()


def test_validation_report_matches_measures(exported):
    _, out, rep, db = exported
    text = (rep / "phase7_dashboard_validation.md").read_text(encoding="utf-8")
    assert "| Trips | 5 |" in text and "| 2024-01 |" in text
    # 5 trips over all 31 days of January (not just the 4 days with trips); Flex Fare 1 of 5
    assert "| 2024-01 | 0 | 20.00% |" in text
    assert "| Trips per Day | 0 |" in text      # 5 / 31 rounds to 0
