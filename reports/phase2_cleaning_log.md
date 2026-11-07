# Phase 2 -- Cleaning Log

Generated (UTC): 2026-11-07T00:28:00+00:00

- Raw rows: **2,964,624**
- Kept: **2,894,474** (97.6338%)
- Excluded: **70,150**
- Raw total_amount: $79,456,384.28 | kept $79,475,586.74 | excluded $-19,202.46

## Exclusion rules (applied in this order; each row counted once)

| # | Rule | Rows removed | % of raw | Rows matching in any order | total_amount removed | Why |
|---|---|---:|---:|---:|---:|---|
| 1 | `outside_file_month` | 18 | 0.0006% | 18 | $442.78 | Pickup is not in the month the file covers. Phase 1 found bad clocks (2002, 2009) and boundary trips that belong to the previous/next month; keeping them would double-count once neighbouring months are loaded. |
| 2 | `exact_duplicate` | 0 | 0.0% | 0 | $0.00 | Every field identical to an earlier row. The first copy is kept. |
| 3 | `reversal_pair` | 61,342 | 2.0691% | 61,344 | $0.00 | A negative row that exactly cancels a positive row (same vendor, times, zones, distance, and opposite total_amount), e.g. the -$10.50/+$10.50 pair in Phase 1. BOTH rows are removed: the charge was reversed, so the trip contributed no money, and keeping only the positive row would overstate revenue. |
| 4 | `nonpositive_duration` | 862 | 0.0291% | 870 | $42,009.59 | Drop-off at or before pickup is physically impossible. |
| 5 | `duration_over_limit` | 14 | 0.0005% | 16 | $2,683.06 | Longer than 24 hours is not a single taxi trip. |
| 6 | `unmatched_negative_amount` | 6,903 | 0.2328% | 37,578 | $-112,574.01 | A negative money value with no matching original charge. It cannot be interpreted (refund of what?), and mixing it into sums would understate amounts. |
| 7 | `implausible_speed` | 1,011 | 0.0341% | 1,024 | $48,236.12 | Average speed above 100 mph: distance and/or times are wrong. |

## Reconciliation

- PASS — rows: raw = kept + excluded
- PASS — rows: excluded = sum of rule counts
- PASS — amount: raw = kept + excluded (cents)
- PASS — every kept row has a pickup in its file month

## Rows per month

| Month | Raw | Kept |
|---|---:|---:|
| 2024-01 | 2,964,624 | 2,894,474 |

## Kept-but-flagged rows

These are real trips with incomplete or unusual fields. They stay in the data; each metric decides whether to include them.

- `flag_flex_fare_incomplete`: 137,921
- `flag_zero_distance`: 53,135
- `flag_passenger_unknown`: 169,194
- `flag_catchall_zone`: 29,618
- `flag_zero_total`: 346

## Open questions from Phase 1, now measured

- Negative total_amount rows: 35,504; matched to a positive twin: 30,672 (86.39%).
- payment_type 0 (Flex Fare) rows: 140,162; of these, rows that DO have passenger_count: 0.

## Distributions of kept rows

| Column | p50 | p95 | p99 | p99.9 | max |
|---|---:|---:|---:|---:|---:|
| trip_distance | 1.69 | 13.6 | 19.97 | 29.3 | 233.25 |
| trip_duration_minutes | 11.7 | 37.98 | 60.52 | 115.38 | 1439.98 |
| fare_amount | 12.8 | 61.8 | 75.8 | 143.4 | 1616.5 |
| total_amount | 20.16 | 80.45 | 103.36 | 174.79 | 1617.5 |

## Zero-distance kept trips by RatecodeID

| RatecodeID | Rows | Avg fare |
|---|---:|---:|
| None | 22,746 | 20.21 |
| 1 | 17,328 | 10.27 |
| 5 | 9,267 | 61.87 |
| 2 | 1,972 | 69.86 |
| 99 | 1,485 | 33.78 |
| 3 | 309 | 24.57 |
| 4 | 26 | 8.9 |
| 6 | 2 | 3.0 |

## Schema harmonisation

- **yellow_tripdata_2024-01.parquet**: renamed=['Airport_fee→airport_fee'], dropped=none, filled NULL=['cbd_congestion_fee'], type casts={'passenger_count': 'BIGINT', 'RatecodeID': 'BIGINT', 'payment_type': 'BIGINT'}
