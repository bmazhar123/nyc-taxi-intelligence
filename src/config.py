"""
Project configuration: the ONE place that defines the study period, file
locations, source URLs, and the expected schema from the official TLC data
dictionary (Yellow Taxi Trip Records, revision dated March 18, 2025).

Every other module imports from here, so changing the study period or a
path happens in exactly one place.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"                # untouched downloads (never edited)
PROCESSED_DIR = DATA_DIR / "processed"    # cleaned outputs (Phase 2)
WAREHOUSE_DIR = DATA_DIR / "warehouse"    # DuckDB database file (Phase 3)
REPORTS_DIR = PROJECT_ROOT / "reports"
MANIFEST_PATH = RAW_DIR / "manifest.json"

# --------------------------------------------------------------------------
# Study period
# --------------------------------------------------------------------------
# Fixed historical window. 2024 H1 is chosen because:
#   * it is fully published (TLC releases data with ~2-month delay),
#   * it predates the cbd_congestion_fee column (added for 2025 onward),
#     so all months should share one schema -- which we still VERIFY.
# Start small: MONTHS_SAMPLE for first runs, MONTHS_FULL once your laptop
# handles it. Pass --months on the command line to override.
MONTHS_SAMPLE = ["2024-01"]
MONTHS_FULL = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]

# --------------------------------------------------------------------------
# Official sources
# --------------------------------------------------------------------------
TLC_LANDING_PAGE = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"
DATA_DICTIONARY_URL = (
    "https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf"
)
# The download links on the landing page point at this CloudFront host.
TRIP_URL_TEMPLATE = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month}.parquet"
ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
ZONE_SHAPEFILE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"


def trip_url(month: str) -> str:
    """Return the official download URL for one month ('YYYY-MM')."""
    return TRIP_URL_TEMPLATE.format(month=month)


def trip_filename(month: str) -> str:
    return f"yellow_tripdata_{month}.parquet"


# --------------------------------------------------------------------------
# Expected schema (from the official data dictionary)
# --------------------------------------------------------------------------
# Field names exactly as the dictionary lists them. We compare columns
# CASE-INSENSITIVELY because published files have not always matched the
# dictionary's capitalisation -- the inspection step reports any mismatch
# rather than us assuming one.
EXPECTED_COLUMNS = [
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "store_and_fwd_flag",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
]
# Present only in 2025+ files; listed so the inspector recognises it as a
# known (documented) addition rather than an unknown column.
OPTIONAL_COLUMNS = ["cbd_congestion_fee"]

MONEY_COLUMNS = [
    "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee",
]

# Code lookups from the data dictionary (used for validity checks and,
# later, as dimension tables).
VENDOR_CODES = {
    1: "Creative Mobile Technologies, LLC",
    2: "Curb Mobility, LLC",
    6: "Myle Technologies Inc",
    7: "Helix",
}
RATECODE_CODES = {
    1: "Standard rate", 2: "JFK", 3: "Newark", 4: "Nassau or Westchester",
    5: "Negotiated fare", 6: "Group ride", 99: "Null/unknown",
}
PAYMENT_TYPE_CODES = {
    0: "Flex Fare trip", 1: "Credit card", 2: "Cash", 3: "No charge",
    4: "Dispute", 5: "Unknown", 6: "Voided trip",
}
STORE_AND_FWD_CODES = {"Y": "store and forward trip", "N": "not a store and forward trip"}
