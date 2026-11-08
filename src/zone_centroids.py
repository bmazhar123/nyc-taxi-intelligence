"""
Phase 7 -- One map point (latitude/longitude) per TLC taxi zone.

Power BI map visuals need coordinates, but the trip data only has zone IDs.
The TLC publishes the zone boundaries as a shapefile, so this script:

  1. Downloads taxi_zones.zip from the TLC (recorded in data/raw/manifest.json).
  2. Reads each zone's polygon(s).
  3. Computes the area-weighted centroid (the polygon's "centre of mass").
  4. Converts it from the shapefile's coordinate system to latitude/longitude.

Output: data/processed/zone_centroids.csv  (location_id, latitude, longitude)

Why compute the centroid BEFORE converting to lat/long?
  The shapefile uses a flat, feet-based map projection (New York State Plane),
  where ordinary geometry is correct. Lat/long is curved, so averaging there
  would be slightly wrong.

Usage:  python -m src.zone_centroids
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path

import shapefile                      # pyshp
from pyproj import CRS, Transformer

from src import config
from src.download import download_file, load_manifest, manifest_entry


def ring_area_centroid(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """
    Signed area and centroid of one polygon ring (shoelace formula).
    The sign depends on the ring's direction: shapefile outer rings and holes
    run in opposite directions, so adding signed areas subtracts holes automatically.
    """
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a /= 2.0
    if a == 0:
        return 0.0, 0.0, 0.0
    return a, cx / (6 * a), cy / (6 * a)


def shape_area_centroid(shape) -> tuple[float, float, float]:
    """Area-weighted centroid of every ring in a (possibly multi-part) polygon."""
    bounds = list(shape.parts) + [len(shape.points)]
    total = sx = sy = 0.0
    for start, end in zip(bounds, bounds[1:]):
        a, cx, cy = ring_area_centroid([tuple(p[:2]) for p in shape.points[start:end]])
        total += a
        sx += a * cx
        sy += a * cy
    return total, sx / total, sy / total


def compute_centroids(shp_path: Path) -> list[dict]:
    prj = shp_path.with_suffix(".prj")
    if not prj.exists():
        raise FileNotFoundError(f"{prj} missing: cannot tell which coordinate system the shapefile uses.")
    to_wgs84 = Transformer.from_crs(CRS.from_wkt(prj.read_text()), CRS.from_epsg(4326), always_xy=True)

    reader = shapefile.Reader(str(shp_path))
    names = {f[0].lower(): f[0] for f in reader.fields[1:]}
    id_field = names.get("locationid")
    if id_field is None:
        raise ValueError(f"No LocationID field in {shp_path.name}; fields are {list(names.values())}")

    # Some zones appear as several records (e.g. islands); combine them per LocationID.
    acc: dict[int, list[float]] = {}
    for sr in reader.iterShapeRecords():
        loc = int(sr.record[id_field])
        a, cx, cy = shape_area_centroid(sr.shape)
        s = acc.setdefault(loc, [0.0, 0.0, 0.0])
        s[0] += a
        s[1] += a * cx
        s[2] += a * cy

    rows = []
    for loc, (a, sx, sy) in sorted(acc.items()):
        lon, lat = to_wgs84.transform(sx / a, sy / a)
        rows.append({"location_id": loc, "latitude": round(lat, 6), "longitude": round(lon, 6)})
    return rows


def run(zip_path: Path = config.ZONE_SHAPEFILE_ZIP, out_path: Path = config.ZONE_CENTROIDS_PATH,
        download: bool = True) -> list[dict]:
    if download and not zip_path.exists():
        download_file(config.ZONE_SHAPEFILE_URL, zip_path)
        manifest = load_manifest(config.MANIFEST_PATH)
        manifest.setdefault("files", {})[zip_path.name] = manifest_entry(
            config.ZONE_SHAPEFILE_URL, zip_path, True, None)
        config.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    extract_dir = zip_path.with_suffix("")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(extract_dir)
    shp_files = sorted(extract_dir.rglob("*.shp"))
    if len(shp_files) != 1:
        raise ValueError(f"Expected one .shp inside {zip_path.name}, found {len(shp_files)}")

    rows = compute_centroids(shp_files[0])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["location_id", "latitude", "longitude"])
        w.writeheader()
        w.writerows(rows)
    print(f"  {len(rows)} zone centroids written to {out_path}")
    return rows


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Compute a lat/long point for every taxi zone.").parse_args(argv)
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
