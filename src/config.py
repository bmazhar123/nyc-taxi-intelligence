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

# --------------------------------------------------------------------------
# Phase 2 -- harmonised schema and cleaning thresholds
# --------------------------------------------------------------------------
# Dictionary name -> (clean snake_case name, target type). Every month is
# forced into exactly this shape, whatever capitalisation or numeric type
# the raw file used. Order here is the column order of the cleaned output.
HARMONIZED_SCHEMA = {
    "VendorID": ("vendor_id", "INTEGER"),
    "tpep_pickup_datetime": ("pickup_datetime", "TIMESTAMP"),
    "tpep_dropoff_datetime": ("dropoff_datetime", "TIMESTAMP"),
    "passenger_count": ("passenger_count", "INTEGER"),
    "trip_distance": ("trip_distance", "DOUBLE"),
    "RatecodeID": ("ratecode_id", "INTEGER"),
    "store_and_fwd_flag": ("store_and_fwd_flag", "VARCHAR"),
    "PULocationID": ("pu_location_id", "INTEGER"),
    "DOLocationID": ("do_location_id", "INTEGER"),
    "payment_type": ("payment_type", "INTEGER"),
    "fare_amount": ("fare_amount", "DOUBLE"),
    "extra": ("extra", "DOUBLE"),
    "mta_tax": ("mta_tax", "DOUBLE"),
    "tip_amount": ("tip_amount", "DOUBLE"),
    "tolls_amount": ("tolls_amount", "DOUBLE"),
    "improvement_surcharge": ("improvement_surcharge", "DOUBLE"),
    "total_amount": ("total_amount", "DOUBLE"),
    "congestion_surcharge": ("congestion_surcharge", "DOUBLE"),
    "airport_fee": ("airport_fee", "DOUBLE"),
    "cbd_congestion_fee": ("cbd_congestion_fee", "DOUBLE"),
}
# Without these the pipeline cannot work at all, so a file missing one of
# them stops the run. Any other missing column is filled with NULL and logged.
CORE_COLUMNS = [
    "tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID",
    "trip_distance", "fare_amount", "total_amount",
]
CLEAN_MONEY_COLUMNS = [HARMONIZED_SCHEMA[c][0] for c in MONEY_COLUMNS] + ["cbd_congestion_fee"]

MAX_DURATION_HOURS = 24     # longer than a day is not a single taxi trip
MAX_SPEED_MPH = 100         # average speed above this is physically implausible in NYC
CATCHALL_ZONE_IDS = (264, 265)  # "Unknown" and "Outside of NYC" in the zone lookup
# Implausible-amount rule (added after the six-month run found a $334,145 trip).
# The legitimate expensive trips reviewed ran $3.6-$25.5 per mile (long
# Nassau/Westchester and negotiated trips). The floor keeps normal flat-rate
# airport and zero-distance fares (avg $62-$70) well clear of the rule.
AMOUNT_REVIEW_FLOOR = 250       # only trips charging more than this are tested
MAX_AMOUNT_PER_MILE = 50        # ~2x the highest plausible rate seen

# --------------------------------------------------------------------------
# Phase 3 -- warehouse
# --------------------------------------------------------------------------
WAREHOUSE_PATH = WAREHOUSE_DIR / "taxi.duckdb"
DOCS_DIR = PROJECT_ROOT / "docs"
ZONE_LOOKUP_PATH = RAW_DIR / "taxi_zone_lookup.csv"
# Phase 2 showed 99.9% of kept trips finish within ~2 hours, yet some run
# almost 24h (likely meters left running). They stay in the data but are
# flagged so duration metrics can exclude them.
LONG_DURATION_MINUTES = 180
UNKNOWN_KEY = -1  # dimension row used when a code is NULL ("Not recorded")

# --------------------------------------------------------------------------
# Phase 4 -- SQL analysis
# --------------------------------------------------------------------------
SQL_DIR = PROJECT_ROOT / "sql"
SQL_RESULTS_DIR = REPORTS_DIR / "sql_results"
