# Phase 1 -- Raw Data Inspection Report

Generated (UTC): 2026-11-06T23:48:09+00:00  
Total rows across files: 2,964,624  
Zone lookup present: True (265 zones)

All numbers below are counts measured from the raw files. Nothing has been removed yet.

## Schema vs. data dictionary

- **2024-01**: missing=none, unexpected=none, case differences=['Airport_fee'], optional present=none

## Type drift between months

- None detected.

## Volume and coverage

| Month | Rows | Min pickup | Max pickup | Pickups outside month |
|---|---:|---|---|---:|
| 2024-01 | 2,964,624 | 2002-12-31 22:59:39 | 2024-02-01 00:01:15 | 18 (0.00%) |

## Data-quality signals (count and % of month)

| Check | 2024-01 |
|---|---:|
| exact_duplicate_rows | 0 (0.00%) |
| DOLocationID_not_in_zone_lookup | 0 (0.00%) |
| PULocationID_not_in_zone_lookup | 0 (0.00%) |
| distance_negative | 0 (0.00%) |
| distance_zero | 60,371 (2.04%) |
| dropoff_not_after_pickup | 870 (0.03%) |
| duration_over_24h | 16 (0.00%) |
| negative_airport_fee | 4,921 (0.17%) |
| negative_congestion_surcharge | 28,825 (0.97%) |
| negative_extra | 17,548 (0.59%) |
| negative_fare_amount | 37,448 (1.26%) |
| negative_improvement_surcharge | 35,502 (1.20%) |
| negative_mta_tax | 34,434 (1.16%) |
| negative_tip_amount | 102 (0.00%) |
| negative_tolls_amount | 2,035 (0.07%) |
| negative_total_amount | 35,504 (1.20%) |
| passenger_count_zero | 31,465 (1.06%) |
| pickup_outside_file_month | 18 (0.00%) |
| total_amount_zero | 416 (0.01%) |
| undocumented_RatecodeID | 0 (0.00%) |
| undocumented_VendorID | 0 (0.00%) |
| undocumented_payment_type | 0 (0.00%) |
| undocumented_store_and_fwd_flag | 0 (0.00%) |

## Null counts

- **2024-01**: passenger_count=140,162, RatecodeID=140,162, store_and_fwd_flag=140,162, congestion_surcharge=140,162, Airport_fee=140,162
