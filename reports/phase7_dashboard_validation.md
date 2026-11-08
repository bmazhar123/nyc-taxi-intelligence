# Phase 7 -- Dashboard Validation Values

Generated (UTC): 2026-11-08T23:13:37+00:00 from `dashboards/data/`.

After building the dashboard, **clear all slicers** and compare each visual with these numbers. They are computed from the same exported files Power BI loads, using the same formulas as the DAX measures, so they should match exactly (allowing for display rounding). A mismatch means a relationship or measure is wrong.

## KPI cards (no filters)

| Measure | Expected |
|---|---:|
| Trips | 19,778,764 |
| Recorded Charges | $557,310,587.49 |
| Avg Fare | $19.40 |
| Avg Duration (min) | 16.2 |
| Fare per Mile (std rate) | $6.20 |
| Avg Speed (mph) | 11.0 |
| Tip % of Fare (card) | 22.8% |
| % Card Trips Tipped | 96.0% |
| Trips per Day | 108,675 |

## By month

| Month | Trips per Day | Flex Fare Share |
|---|---:|---:|
| 2024-01 | 93,365 | 4.77% |
| 2024-02 | 101,163 | 6.16% |
| 2024-03 | 112,360 | 11.81% |
| 2024-04 | 113,880 | 11.54% |
| 2024-05 | 116,731 | 10.87% |
| 2024-06 | 114,417 | 11.57% |

## Day type (Trips per Day)

| Day type | Trips per Day |
|---|---:|
| Weekday | 109,643 |
| Weekend | 106,252 |

## Pickup borough

| Borough | Trips | Tip % of Fare (card) |
|---|---:|---:|
| Manhattan | 17,660,335 | 23.6% |
| Queens | 1,737,626 | 20.6% |
| Brooklyn | 247,399 | 19.1% |
| Unknown | 63,826 | 22.0% |
| Bronx | 57,751 | 11.9% |
| N/A | 8,879 | 12.3% |
| EWR | 2,349 | 14.0% |
| Staten Island | 599 | 18.1% |

## Airport direction

| Direction | Trips | % of Recorded Charges |
|---|---:|---:|
| Non-airport | 17,872,352 | 73.2% |
| From airport | 1,483,211 | 20.4% |
| To airport | 423,201 | 6.4% |

## 5 PM (hour 17)

- Avg Speed: 9.3 mph
- Fare per Mile: $6.81
