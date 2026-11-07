# Phase 1 -- Raw Data Inspection Report

Generated (UTC): 2026-11-07T01:40:09+00:00  
Total rows across files: 20,332,093  
Zone lookup present: True (265 zones)

All numbers below are counts measured from the raw files. Nothing has been removed yet.

## Schema vs. data dictionary

- **2024-01**: missing=none, unexpected=none, case differences=['Airport_fee'], optional present=none
- **2024-02**: missing=none, unexpected=none, case differences=['Airport_fee'], optional present=none
- **2024-03**: missing=none, unexpected=none, case differences=['Airport_fee'], optional present=none
- **2024-04**: missing=none, unexpected=none, case differences=['Airport_fee'], optional present=none
- **2024-05**: missing=none, unexpected=none, case differences=['Airport_fee'], optional present=none
- **2024-06**: missing=none, unexpected=none, case differences=['Airport_fee'], optional present=none

## Type drift between months

- None detected.

## Volume and coverage

| Month | Rows | Min pickup | Max pickup | Pickups outside month |
|---|---:|---|---|---:|
| 2024-01 | 2,964,624 | 2002-12-31 22:59:39 | 2024-02-01 00:01:15 | 18 (0.00%) |
| 2024-02 | 3,007,526 | 2008-12-31 22:52:49 | 2024-03-01 00:01:37 | 15 (0.00%) |
| 2024-03 | 3,582,628 | 2002-12-31 22:17:10 | 2024-04-01 00:34:55 | 23 (0.00%) |
| 2024-04 | 3,514,289 | 2002-12-31 22:10:04 | 2024-05-01 00:02:36 | 9 (0.00%) |
| 2024-05 | 3,723,833 | 2002-12-31 16:46:07 | 2024-06-01 23:54:14 | 33 (0.00%) |
| 2024-06 | 3,539,193 | 2008-12-31 00:00:00 | 2026-06-26 23:53:12 | 51 (0.00%) |

## Data-quality signals (count and % of month)

| Check | 2024-01 | 2024-02 | 2024-03 | 2024-04 | 2024-05 | 2024-06 |
|---|---:|---:|---:|---:|---:|---:|
| exact_duplicate_rows | 0 (0.00%) | 1 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| DOLocationID_not_in_zone_lookup | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| PULocationID_not_in_zone_lookup | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| distance_negative | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| distance_zero | 60,371 (2.04%) | 68,225 (2.27%) | 87,168 (2.43%) | 45,813 (1.30%) | 49,791 (1.34%) | 52,954 (1.50%) |
| dropoff_not_after_pickup | 870 (0.03%) | 803 (0.03%) | 1,128 (0.03%) | 1,089 (0.03%) | 1,147 (0.03%) | 1,140 (0.03%) |
| duration_over_24h | 16 (0.00%) | 12 (0.00%) | 20 (0.00%) | 26 (0.00%) | 15 (0.00%) | 20 (0.00%) |
| negative_airport_fee | 4,921 (0.17%) | 4,801 (0.16%) | 6,547 (0.18%) | 6,983 (0.20%) | 7,677 (0.21%) | 7,766 (0.22%) |
| negative_congestion_surcharge | 28,825 (0.97%) | 29,866 (0.99%) | 36,422 (1.02%) | 35,390 (1.01%) | 39,980 (1.07%) | 39,893 (1.13%) |
| negative_extra | 17,548 (0.59%) | 18,097 (0.60%) | 22,219 (0.62%) | 22,072 (0.63%) | 24,776 (0.67%) | 24,140 (0.68%) |
| negative_fare_amount | 37,448 (1.26%) | 40,655 (1.35%) | 58,464 (1.63%) | 57,568 (1.64%) | 59,947 (1.61%) | 61,665 (1.74%) |
| negative_improvement_surcharge | 35,502 (1.20%) | 36,078 (1.20%) | 44,304 (1.24%) | 43,749 (1.24%) | 48,966 (1.31%) | 48,555 (1.37%) |
| negative_mta_tax | 34,434 (1.16%) | 35,052 (1.17%) | 42,921 (1.20%) | 42,299 (1.20%) | 47,271 (1.27%) | 46,864 (1.32%) |
| negative_tip_amount | 102 (0.00%) | 109 (0.00%) | 119 (0.00%) | 153 (0.00%) | 114 (0.00%) | 108 (0.00%) |
| negative_tolls_amount | 2,035 (0.07%) | 2,260 (0.08%) | 3,291 (0.09%) | 3,362 (0.10%) | 3,931 (0.11%) | 3,872 (0.11%) |
| negative_total_amount | 35,504 (1.20%) | 36,080 (1.20%) | 44,311 (1.24%) | 43,749 (1.24%) | 48,992 (1.32%) | 48,795 (1.38%) |
| passenger_count_zero | 31,465 (1.06%) | 34,094 (1.13%) | 40,372 (1.13%) | 39,591 (1.13%) | 39,748 (1.07%) | 35,839 (1.01%) |
| pickup_outside_file_month | 18 (0.00%) | 15 (0.00%) | 23 (0.00%) | 9 (0.00%) | 33 (0.00%) | 51 (0.00%) |
| total_amount_zero | 416 (0.01%) | 438 (0.01%) | 438 (0.01%) | 417 (0.01%) | 379 (0.01%) | 316 (0.01%) |
| undocumented_RatecodeID | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| undocumented_VendorID | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| undocumented_payment_type | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| undocumented_store_and_fwd_flag | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |

## Null counts

- **2024-01**: passenger_count=140,162, RatecodeID=140,162, store_and_fwd_flag=140,162, congestion_surcharge=140,162, Airport_fee=140,162
- **2024-02**: passenger_count=185,610, RatecodeID=185,610, store_and_fwd_flag=185,610, congestion_surcharge=185,610, Airport_fee=185,610
- **2024-03**: passenger_count=426,190, RatecodeID=426,190, store_and_fwd_flag=426,190, congestion_surcharge=426,190, Airport_fee=426,190
- **2024-04**: passenger_count=408,576, RatecodeID=408,576, store_and_fwd_flag=408,576, congestion_surcharge=408,576, Airport_fee=408,576
- **2024-05**: passenger_count=404,666, RatecodeID=404,666, store_and_fwd_flag=404,666, congestion_surcharge=404,666, Airport_fee=404,666
- **2024-06**: passenger_count=410,781, RatecodeID=410,781, store_and_fwd_flag=410,781, congestion_surcharge=410,781, Airport_fee=410,781
