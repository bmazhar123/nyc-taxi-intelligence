"""
The warehouse data dictionary, kept as code.

Why code instead of a hand-written document?
  * build_warehouse.py writes every description below into DuckDB itself
    (COMMENT ON TABLE / COLUMN), so anyone browsing the database sees them.
  * It also generates docs/data_dictionary.md from this file.
  * A test fails if any warehouse column is missing a description, so the
    documentation can never silently fall out of date.
"""
from src import config

LIMIT_TOTAL = ("Amount charged to the passenger as recorded by the meter vendor. Includes "
               "taxes, surcharges and tolls; excludes cash tips. NOT driver income, profit, "
               "or net revenue.")

TABLES = {
    "fact_trips": {
        "description": "One row per cleaned yellow-taxi trip (Phase 2 output).",
        "grain": "One trip",
        "columns": {
            "trip_id": "Unique trip key: source month (YYYYMM) followed by the row's position in its raw file.",
            "pickup_datetime": "When the meter was engaged (local NYC time, as recorded).",
            "dropoff_datetime": "When the meter was disengaged.",
            "pickup_date_key": "FK to dim_date (YYYYMMDD of pickup).",
            "pickup_hour": "FK to dim_time: hour of pickup, 0-23.",
            "pu_location_id": "FK to dim_zone: taxi zone where the meter was engaged.",
            "do_location_id": "FK to dim_zone: taxi zone where the meter was disengaged.",
            "vendor_key": f"FK to dim_vendor. {config.UNKNOWN_KEY} = not recorded.",
            "ratecode_key": f"FK to dim_ratecode. {config.UNKNOWN_KEY} = not recorded (all Flex Fare trips).",
            "payment_type_key": f"FK to dim_payment_type. {config.UNKNOWN_KEY} = not recorded.",
            "store_and_fwd_flag": "Y = record held in vehicle memory before sending (no connection); N = sent live. NULL for Flex Fare trips.",
            "passenger_count": "Driver-entered passenger count. NULL for Flex Fare trips; 0 values are unreliable.",
            "trip_distance": "Miles reported by the taximeter.",
            "trip_duration_minutes": "Drop-off minus pickup, in minutes.",
            "fare_amount": "Time-and-distance fare calculated by the meter.",
            "extra": "Miscellaneous extras and surcharges.",
            "mta_tax": "MTA tax triggered by the metered rate in use.",
            "tip_amount": "Tip. Automatically populated for credit-card tips only; cash tips are NOT recorded.",
            "tolls_amount": "Total tolls paid during the trip.",
            "improvement_surcharge": "Improvement surcharge assessed at the flag drop.",
            "congestion_surcharge": "NYS congestion surcharge. NULL = not recorded (not $0).",
            "airport_fee": "Fee for pickups at LaGuardia and JFK. NULL = not recorded (not $0).",
            "cbd_congestion_fee": "MTA Congestion Relief Zone charge (2025+ files only); NULL before 2025.",
            "total_amount": LIMIT_TOTAL,
            "is_credit_card": "True when payment_type = 1. Tip-rate metrics should use only these trips.",
            "flag_flex_fare_incomplete": "Flex Fare trip (payment_type 0) reported without passenger count, rate code and some surcharges.",
            "flag_zero_distance": "Meter recorded 0 miles. Often legitimate for flat-rate fares (JFK, negotiated).",
            "flag_passenger_unknown": "passenger_count is NULL or 0; exclude from per-passenger metrics.",
            "flag_catchall_zone": "Pickup or drop-off zone is 264 (Unknown) or 265 (Outside of NYC).",
            "flag_zero_total": "total_amount is exactly 0.",
            "flag_long_duration": f"Trip longer than {config.LONG_DURATION_MINUTES} minutes; likely a meter left running. Exclude from duration metrics.",
            "source_month": "Monthly raw file the trip came from (YYYY-MM).",
        },
    },
    "dim_date": {
        "description": "Calendar dates covering the study period.",
        "grain": "One calendar day",
        "columns": {
            "date_key": "Primary key, YYYYMMDD.",
            "full_date": "The date.",
            "year": "Calendar year.",
            "quarter": "Calendar quarter, 1-4.",
            "month": "Month number, 1-12.",
            "month_name": "Month name, e.g. January.",
            "year_month": "YYYY-MM, useful for monthly trend axes.",
            "day_of_month": "Day of the month, 1-31.",
            "day_of_week": "ISO day of week: 1 = Monday ... 7 = Sunday.",
            "day_name": "Day name, e.g. Monday.",
            "is_weekend": "True on Saturday and Sunday.",
            "iso_week": "ISO week number.",
            "is_us_federal_holiday": "True on the OBSERVED date of a US federal holiday.",
            "holiday_name": "Holiday name, or NULL.",
        },
    },
    "dim_time": {
        "description": "Hours of the day with operations-friendly groupings.",
        "grain": "One hour (0-23)",
        "columns": {
            "hour": "Primary key, 0-23.",
            "hour_label": "Display label, e.g. 08:00.",
            "time_band": "Overnight (0-5), AM peak (6-9), Midday (10-15), PM peak (16-19), Evening (20-23). Project-defined bands, not an official TLC definition.",
            "time_band_order": "Sort order for time_band.",
        },
    },
    "dim_zone": {
        "description": "TLC taxi zones from the official zone lookup CSV.",
        "grain": "One taxi zone",
        "columns": {
            "location_id": "Primary key: TLC LocationID.",
            "borough": "Borough (or EWR / Unknown / N/A).",
            "zone": "Zone name.",
            "service_zone": "TLC service zone (e.g. Yellow Zone, Boro Zone, Airports, EWR).",
            "is_catchall": "True for 264 (Unknown) and 265 (Outside of NYC): valid codes but not real places.",
            "is_airport": "True when service_zone is 'Airports' or 'EWR' (JFK, LaGuardia, Newark).",
        },
    },
    "dim_vendor": {
        "description": "Technology providers that submit trip records (data dictionary codes).",
        "grain": "One vendor code",
        "columns": {"vendor_key": "Primary key: VendorID code, or -1 for not recorded.",
                    "vendor_name": "Provider name from the data dictionary."},
    },
    "dim_ratecode": {
        "description": "Final rate code in effect at the end of the trip.",
        "grain": "One rate code",
        "columns": {"ratecode_key": "Primary key: RatecodeID, or -1 for not recorded.",
                    "ratecode_name": "Rate description from the data dictionary.",
                    "is_flat_rate": "True for JFK (2) and Negotiated fare (5), where distance does not set the fare."},
    },
    "dim_payment_type": {
        "description": "How the passenger paid.",
        "grain": "One payment code",
        "columns": {"payment_type_key": "Primary key: payment_type code, or -1 for not recorded.",
                    "payment_type_name": "Description from the data dictionary.",
                    "tips_recorded": "True only for credit card (1): the only method whose tips appear in the data."},
    },
    "meta_source_files": {
        "description": "Lineage: every raw file the warehouse was built from (from data/raw/manifest.json).",
        "grain": "One downloaded file",
        "columns": {"file_name": "Local file name.", "source_url": "Official download URL.",
                    "size_bytes": "File size.", "sha256": "SHA-256 checksum at download.",
                    "downloaded_at_utc": "Download time (UTC)."},
    },
    "meta_cleaning_rules": {
        "description": "Rows removed by each Phase 2 cleaning rule (from reports/phase2_cleaning_log.json).",
        "grain": "One cleaning rule",
        "columns": {"rule_order": "Order the rule was applied.", "rule": "Rule name.",
                    "rows_removed": "Rows assigned to this rule.",
                    "total_amount_removed": "Sum of total_amount on those rows.",
                    "why": "Reason for the rule."},
    },
    "meta_build": {
        "description": "One row describing this warehouse build.",
        "grain": "One build",
        "columns": {"built_at_utc": "When the warehouse was built.",
                    "months_loaded": "Comma-separated source months.",
                    "fact_rows": "Rows in fact_trips.",
                    "fact_total_amount": "Sum of total_amount in fact_trips."},
    },
}


def to_markdown() -> str:
    lines = ["# Data Dictionary — NYC Taxi Intelligence Warehouse", "",
             "Generated from `src/data_dictionary.py` by `src/build_warehouse.py`; do not edit by hand.",
             "Source field definitions follow the official TLC Yellow Taxi data dictionary.", "",
             "**Star schema:** `fact_trips` joins to `dim_date` (pickup_date_key → date_key), "
             "`dim_time` (pickup_hour → hour), `dim_zone` twice (pu_location_id and do_location_id → location_id), "
             "`dim_vendor`, `dim_ratecode`, `dim_payment_type`.", ""]
    for name, t in TABLES.items():
        lines += [f"## `{name}`", "", t["description"], "", f"**Grain:** {t['grain']}", "",
                  "| Column | Description |", "|---|---|"]
        lines += [f"| `{c}` | {d} |" for c, d in t["columns"].items()]
        lines.append("")
    return "\n".join(lines)
