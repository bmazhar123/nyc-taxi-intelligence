# Phase 2 -- Cleaning Log

Generated (UTC): 2026-11-07T01:43:07+00:00

- Raw rows: **20,332,093**
- Kept: **19,778,764** (97.2785%)
- Excluded: **553,329**
- Raw total_amount: $557,830,247.45 | kept $557,310,587.49 | excluded $519,659.96

## Exclusion rules (applied in this order; each row counted once)

| # | Rule | Rows removed | % of raw | Rows matching in any order | total_amount removed | Why |
|---|---|---:|---:|---:|---:|---|
| 1 | `outside_file_month` | 149 | 0.0007% | 149 | $4,375.06 | Pickup is not in the month the file covers. Phase 1 found bad clocks (2002, 2009) and boundary trips that belong to the previous/next month; keeping them would double-count once neighbouring months are loaded. |
| 2 | `exact_duplicate` | 1 | 0.0% | 1 | $23.16 | Every field identical to an earlier row. The first copy is kept. |
| 3 | `reversal_pair` | 445,977 | 2.1935% | 445,982 | $5.50 | A negative row that exactly cancels a positive row (same vendor, times, zones, distance, and opposite total_amount), e.g. the -$10.50/+$10.50 pair in Phase 1. BOTH rows are removed: the charge was reversed, so the trip contributed no money, and keeping only the positive row would overstate revenue. |
| 4 | `nonpositive_duration` | 6,147 | 0.0302% | 6,177 | $258,949.63 | Drop-off at or before pickup is physically impossible. |
| 5 | `duration_over_limit` | 107 | 0.0005% | 109 | $6,117.44 | Longer than 24 hours is not a single taxi trip. |
| 6 | `unmatched_negative_amount` | 93,759 | 0.4611% | 316,784 | $-720,089.72 | A negative money value with no matching original charge. It cannot be interpreted (refund of what?), and mixing it into sums would understate amounts. |
| 7 | `implausible_speed` | 6,155 | 0.0303% | 6,266 | $261,415.31 | Average speed above 100 mph: distance and/or times are wrong. |
| 8 | `implausible_amount` | 1,034 | 0.0051% | 1,153 | $708,863.58 | Charged over $250 with zero distance or more than $50/mile (e.g. $334,145 for a 0-mile, 3-minute trip). Legitimate expensive trips reviewed ran $3.6-$25.5/mile. |

## Reconciliation

- PASS — rows: raw = kept + excluded
- PASS — rows: excluded = sum of rule counts
- PASS — amount: raw = kept + excluded (cents)
- PASS — every kept row has a pickup in its file month

## Rows per month

| Month | Raw | Kept |
|---|---:|---:|
| 2024-01 | 2,964,624 | 2,894,313 |
| 2024-02 | 3,007,526 | 2,933,729 |
| 2024-03 | 3,582,628 | 3,483,155 |
| 2024-04 | 3,514,289 | 3,416,395 |
| 2024-05 | 3,723,833 | 3,618,654 |
| 2024-06 | 3,539,193 | 3,432,518 |

## Kept-but-flagged rows

These are real trips with incomplete or unusual fields. They stay in the data; each metric decides whether to include them.

- `flag_flex_fare_incomplete`: 1,914,903
- `flag_zero_distance`: 313,264
- `flag_passenger_unknown`: 2,134,141
- `flag_catchall_zone`: 194,831
- `flag_zero_total`: 1,970

## Open questions from Phase 1, now measured

- Negative total_amount rows: 257,431; matched to a positive twin: 222,991 (86.62%).
- payment_type 0 (Flex Fare) rows: 1,975,985; of these, rows that DO have passenger_count: 0.

## Distributions of kept rows

| Column | p50 | p95 | p99 | p99.9 | max |
|---|---:|---:|---:|---:|---:|
| trip_distance | 1.76 | 13.3 | 19.82 | 29.1 | 382.5 |
| trip_duration_minutes | 12.63 | 42.15 | 68.58 | 120.02 | 1439.98 |
| fare_amount | 13.5 | 61.8 | 76.5 | 140.0 | 1616.5 |
| total_amount | 21.0 | 80.94 | 104.63 | 172.2 | 1617.5 |

## Zero-distance kept trips by RatecodeID

| RatecodeID | Rows | Avg fare |
|---|---:|---:|
| None | 122,507 | 19.71 |
| 1 | 106,078 | 9.56 |
| 5 | 60,017 | 58.25 |
| 2 | 12,597 | 69.74 |
| 99 | 9,653 | 34.03 |
| 3 | 2,247 | 24.2 |
| 4 | 153 | 11.35 |
| 6 | 12 | 14.22 |

## Schema harmonisation

- **yellow_tripdata_2024-01.parquet**: renamed=['Airport_fee→airport_fee'], dropped=none, filled NULL=['cbd_congestion_fee'], type casts={'passenger_count': 'BIGINT', 'RatecodeID': 'BIGINT', 'payment_type': 'BIGINT'}
- **yellow_tripdata_2024-02.parquet**: renamed=['Airport_fee→airport_fee'], dropped=none, filled NULL=['cbd_congestion_fee'], type casts={'passenger_count': 'BIGINT', 'RatecodeID': 'BIGINT', 'payment_type': 'BIGINT'}
- **yellow_tripdata_2024-03.parquet**: renamed=['Airport_fee→airport_fee'], dropped=none, filled NULL=['cbd_congestion_fee'], type casts={'passenger_count': 'BIGINT', 'RatecodeID': 'BIGINT', 'payment_type': 'BIGINT'}
- **yellow_tripdata_2024-04.parquet**: renamed=['Airport_fee→airport_fee'], dropped=none, filled NULL=['cbd_congestion_fee'], type casts={'passenger_count': 'BIGINT', 'RatecodeID': 'BIGINT', 'payment_type': 'BIGINT'}
- **yellow_tripdata_2024-05.parquet**: renamed=['Airport_fee→airport_fee'], dropped=none, filled NULL=['cbd_congestion_fee'], type casts={'passenger_count': 'BIGINT', 'RatecodeID': 'BIGINT', 'payment_type': 'BIGINT'}
- **yellow_tripdata_2024-06.parquet**: renamed=['Airport_fee→airport_fee'], dropped=none, filled NULL=['cbd_congestion_fee'], type casts={'passenger_count': 'BIGINT', 'RatecodeID': 'BIGINT', 'payment_type': 'BIGINT'}
