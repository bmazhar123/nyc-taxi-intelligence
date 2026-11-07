# Phase 3 -- Warehouse Build Summary

Built (UTC): 2026-11-07T02:18:59+00:00  
Months loaded: 2024-01,2024-02,2024-03,2024-04,2024-05,2024-06  
fact_trips rows: 19,778,764  
fact_trips total_amount: $557,310,587.49

## Integrity checks

- PASS — fact rows = cleaned rows
- PASS — trip_id is unique
- PASS — fact total_amount = cleaned total_amount (cents)
- PASS — no orphan pickup dates
- PASS — no orphan pickup hours
- PASS — no orphan pickup zones
- PASS — no orphan drop-off zones
- PASS — no orphan vendors
- PASS — no orphan rate codes
- PASS — no orphan payment types
- PASS — every warehouse column is documented

## Tables

| Table | Rows |
|---|---:|
| `dim_date` | 182 |
| `dim_payment_type` | 8 |
| `dim_ratecode` | 8 |
| `dim_time` | 24 |
| `dim_vendor` | 5 |
| `dim_zone` | 265 |
| `fact_trips` | 19,778,764 |
| `meta_build` | 1 |
| `meta_cleaning_rules` | 8 |
| `meta_source_files` | 7 |

## Flags in fact_trips

- `flag_flex_fare_incomplete`: 1,914,903
- `flag_zero_distance`: 313,264
- `flag_passenger_unknown`: 2,134,141
- `flag_catchall_zone`: 194,831
- `flag_zero_total`: 1,970
- `flag_long_duration`: 12,654

## Holidays in dim_date

- 2024-01-01: New Year's Day
- 2024-01-15: Martin Luther King Jr. Day
- 2024-02-19: Presidents' Day
- 2024-05-27: Memorial Day
- 2024-06-19: Juneteenth
