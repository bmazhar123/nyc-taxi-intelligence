# Phase 4 -- SQL Analysis Results

Views applied: `01_v_trips`, `02_v_daily_kpis`, `03_v_hourly_demand`, `04_v_zone_daily`, `05_v_od_monthly`

17 queries. Full results are in `reports/sql_results/*.csv`; query source is in `sql/analysis/`.

## 01_monthly_kpis_mom

**Question:** How did trips, recorded charges and average fare change month over month?  
**Technique:** CTE + LAG window function for month-over-month % change.  
**Caveat:** total_amount is the amount charged to passengers (incl. taxes, tolls, surcharges), not revenue or driver income. Months have different numbers of days, so trips per day is the fairer comparison.  
_Ran in 0.3s, 6 row(s)._

| year_month | days | trips | trips_per_day | trips_per_day_mom_pct | total_amount | total_amount_mom_pct | avg_fare |
|---|---|---|---|---|---|---|---|
| 2024-01 | 31 | 2,894,313 | 93,365.00 |  | 79,419,818.00 |  | 18.61 |
| 2024-02 | 29 | 2,933,729 | 101,163.00 | 8.40 | 80,047,868.00 | 0.80 | 18.50 |
| 2024-03 | 31 | 3,483,155 | 112,360.00 | 11.10 | 97,143,697.00 | 21.40 | 19.23 |
| 2024-04 | 30 | 3,416,395 | 113,880.00 | 1.40 | 96,599,150.00 | -0.60 | 19.52 |
| 2024-05 | 31 | 3,618,654 | 116,731.00 | 2.50 | 105,272,244.00 | 9.00 | 20.22 |
| 2024-06 | 30 | 3,432,518 | 114,417.00 | -2.00 | 98,827,811.00 | -6.10 | 20.03 |

## 02_weekday_vs_weekend

**Question:** How do weekdays and weekends differ in volume, fare, duration and tipping?  
**Technique:** Aggregate daily rows first (so "per day" divides by real day counts), then compare groups; ratio-of-sums for rates.  
**Caveat:** Holidays are counted under their weekday; tip % uses credit-card trips only because cash tips are not recorded.  
_Ran in 0.5s, 2 row(s)._

| day_type | days | avg_trips_per_day | avg_fare | avg_distance_mi | avg_duration_min | fare_per_mile_std_rate | tip_pct_of_fare_card | airport_trip_pct |
|---|---|---|---|---|---|---|---|---|
| Weekend | 52 | 106,252.00 | 19.18 | 3.35 | 15.10 | 5.96 | 22.10 | 9.20 |
| Weekday | 130 | 109,643.00 | 19.48 | 3.29 | 16.70 | 6.30 | 23.00 | 9.80 |

## 03_hourly_demand_profile

**Question:** What does a typical day's demand curve look like, hour by hour, on weekdays vs weekends?  
**Technique:** Average trips per hour (divided by number of days), plus each hour's share of the day using SUM() OVER (PARTITION BY ...).  
**Caveat:** Averages hide variation between individual days; see query 11 for day-level trends.  
_Ran in 0.4s, 48 row(s)._

| day_type | hour_label | time_band | avg_trips | pct_of_day |
|---|---|---|---|---|
| Weekday | 00:00 | Overnight | 1,956.00 | 1.78 |
| Weekday | 01:00 | Overnight | 927.00 | 0.85 |
| Weekday | 02:00 | Overnight | 513.00 | 0.47 |
| Weekday | 03:00 | Overnight | 344.00 | 0.31 |
| Weekday | 04:00 | Overnight | 382.00 | 0.35 |
| Weekday | 05:00 | Overnight | 725.00 | 0.66 |
| Weekday | 06:00 | AM peak | 1,787.00 | 1.63 |
| Weekday | 07:00 | AM peak | 3,736.00 | 3.41 |
| Weekday | 08:00 | AM peak | 5,071.00 | 4.63 |
| Weekday | 09:00 | AM peak | 5,129.00 | 4.68 |
| Weekday | 10:00 | Midday | 5,091.00 | 4.64 |
| Weekday | 11:00 | Midday | 5,327.00 | 4.86 |
| Weekday | 12:00 | Midday | 5,736.00 | 5.23 |
| Weekday | 13:00 | Midday | 5,908.00 | 5.39 |
| Weekday | 14:00 | Midday | 6,505.00 | 5.93 |
| Weekday | 15:00 | Midday | 6,738.00 | 6.15 |
| Weekday | 16:00 | PM peak | 6,776.00 | 6.18 |
| Weekday | 17:00 | PM peak | 7,697.00 | 7.02 |
| Weekday | 18:00 | PM peak | 8,249.00 | 7.52 |
| Weekday | 19:00 | PM peak | 7,111.00 | 6.49 |
| Weekday | 20:00 | Evening | 6,503.00 | 5.93 |
| Weekday | 21:00 | Evening | 6,788.00 | 6.19 |
| Weekday | 22:00 | Evening | 6,194.00 | 5.65 |
| Weekday | 23:00 | Evening | 4,449.00 | 4.06 |
| Weekend | 00:00 | Overnight | 6,011.00 | 5.66 |

_23 more rows in the CSV._

## 04_peak_hours_by_weekday

**Question:** Which three hours are busiest on each day of the week?  
**Technique:** RANK() window function partitioned by weekday, filtered with QUALIFY.  
**Caveat:** Based on average pickups per hour across all weeks in the period.  
_Ran in 0.2s, 21 row(s)._

| day_name | hour_label | avg_trips | rank_in_day |
|---|---|---|---|
| Monday | 18:00 | 6,594.00 | 1 |
| Monday | 17:00 | 6,435.00 | 2 |
| Monday | 15:00 | 6,000.00 | 3 |
| Tuesday | 18:00 | 8,165.00 | 1 |
| Tuesday | 17:00 | 7,562.00 | 2 |
| Tuesday | 21:00 | 7,117.00 | 3 |
| Wednesday | 18:00 | 8,805.00 | 1 |
| Wednesday | 17:00 | 8,269.00 | 2 |
| Wednesday | 21:00 | 7,667.00 | 3 |
| Thursday | 18:00 | 9,395.00 | 1 |
| Thursday | 17:00 | 8,577.00 | 2 |
| Thursday | 19:00 | 8,030.00 | 3 |
| Friday | 18:00 | 8,286.00 | 1 |
| Friday | 19:00 | 7,642.00 | 2 |
| Friday | 17:00 | 7,642.00 | 3 |
| Saturday | 18:00 | 7,551.00 | 1 |
| Saturday | 19:00 | 7,383.00 | 2 |
| Saturday | 17:00 | 7,287.00 | 3 |
| Sunday | 00:00 | 6,242.00 | 1 |
| Sunday | 14:00 | 6,192.00 | 2 |
| Sunday | 13:00 | 6,041.00 | 3 |

## 05_top_pickup_zones_pareto

**Question:** Which pickup zones generate the most trips, and how concentrated is demand?  
**Technique:** Aggregation + running total with SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING) for a Pareto view.  
**Caveat:** Excludes catch-all zones 264/265. Pickup counts measure where trips START, not where demand originates (e.g. airport queues).  
_Ran in 0.3s, 20 row(s)._

| zone | borough | pickups | pct_of_pickups | cumulative_pct | avg_total_amount |
|---|---|---|---|---|---|
| Midtown Center | Manhattan | 930,722 | 4.72 | 4.70 | 24.93 |
| Upper East Side South | Manhattan | 926,691 | 4.70 | 9.40 | 20.55 |
| Upper East Side North | Manhattan | 863,767 | 4.38 | 13.80 | 21.05 |
| JFK Airport | Queens | 857,399 | 4.35 | 18.20 | 82.68 |
| Midtown East | Manhattan | 685,442 | 3.48 | 21.60 | 24.32 |
| Times Sq/Theatre District | Manhattan | 664,067 | 3.37 | 25.00 | 28.48 |
| Lincoln Square East | Manhattan | 650,198 | 3.30 | 28.30 | 22.07 |
| Penn Station/Madison Sq West | Manhattan | 639,839 | 3.25 | 31.60 | 25.26 |
| LaGuardia Airport | Queens | 623,463 | 3.16 | 34.70 | 68.12 |
| Upper West Side South | Manhattan | 571,324 | 2.90 | 37.60 | 22.00 |
| Midtown North | Manhattan | 568,720 | 2.89 | 40.50 | 24.73 |
| Murray Hill | Manhattan | 567,467 | 2.88 | 43.40 | 24.15 |
| Union Sq | Manhattan | 531,920 | 2.70 | 46.10 | 22.69 |
| East Chelsea | Manhattan | 527,986 | 2.68 | 48.80 | 25.84 |
| Clinton East | Manhattan | 500,793 | 2.54 | 51.30 | 23.99 |
| East Village | Manhattan | 472,293 | 2.40 | 53.70 | 22.91 |
| West Village | Manhattan | 466,950 | 2.37 | 56.10 | 22.95 |
| Lenox Hill West | Manhattan | 457,315 | 2.32 | 58.40 | 20.93 |
| Midtown South | Manhattan | 445,893 | 2.26 | 60.70 | 24.78 |
| Gramercy | Manhattan | 402,304 | 2.04 | 62.70 | 22.35 |

## 06_zone_concentration

**Question:** How many of the city's taxi zones account for half, 80% and 95% of all pickups?  
**Technique:** CTE with cumulative share window, then conditional aggregation.  
**Caveat:** Zones differ greatly in size, so concentration partly reflects geography, not only demand.  
_Ran in 0.3s, 1 row(s)._

| zones_with_pickups | zones_for_50pct | zones_for_80pct | zones_for_95pct |
|---|---|---|---|
| 260 | 15 | 31 | 48 |

## 07_borough_flows

**Question:** Where do trips go? Borough-to-borough flow matrix with each origin's destination mix.  
**Technique:** JOIN to the zone dimension twice (pickup and drop-off roles) via v_trips; share within origin using a partitioned window.  
**Caveat:** Catch-all zones excluded. Borough is the zone lookup's borough (EWR = Newark Airport).  
_Ran in 0.1s, 20 row(s)._

| pu_borough | do_borough | trips | pct_of_all_trips | pct_of_origin_trips |
|---|---|---|---|---|
| Manhattan | Manhattan | 16,599,099 | 84.76 | 94.40 |
| Queens | Manhattan | 1,013,971 | 5.18 | 60.10 |
| Manhattan | Queens | 527,038 | 2.69 | 3.00 |
| Queens | Queens | 382,569 | 1.95 | 22.70 |
| Manhattan | Brooklyn | 361,693 | 1.85 | 2.10 |
| Queens | Brooklyn | 251,367 | 1.28 | 14.90 |
| Brooklyn | Brooklyn | 128,970 | 0.66 | 52.30 |
| Brooklyn | Manhattan | 82,483 | 0.42 | 33.40 |
| Manhattan | Bronx | 54,114 | 0.28 | 0.30 |
| Manhattan | EWR | 46,548 | 0.24 | 0.30 |
| Queens | Bronx | 35,229 | 0.18 | 2.10 |
| Brooklyn | Queens | 29,377 | 0.15 | 11.90 |
| Bronx | Manhattan | 26,371 | 0.13 | 45.90 |
| Bronx | Bronx | 21,076 | 0.11 | 36.70 |
| Brooklyn | Bronx | 5,292 | 0.03 | 2.10 |
| Bronx | Brooklyn | 5,042 | 0.03 | 8.80 |
| Bronx | Queens | 4,982 | 0.03 | 8.70 |
| EWR | EWR | 2,147 | 0.01 | 97.40 |
| Queens | Staten Island | 1,920 | 0.01 | 0.10 |
| Queens | EWR | 1,779 | 0.01 | 0.10 |

## 08_airport_vs_other

**Question:** How do airport trips (JFK, LaGuardia, Newark) compare with all other trips?  
**Technique:** CASE classification on joined zone attributes; ratio-of-sums metrics with FILTER.  
**Caveat:** Airport trips include flat-rate JFK fares, so average fare differences partly reflect pricing rules, not only distance.  
_Ran in 0.3s, 3 row(s)._

| trip_type | trips | pct_of_trips | pct_of_total_amount | avg_total_amount | avg_distance_mi | avg_duration_min | tip_pct_of_fare_card |
|---|---|---|---|---|---|---|---|
| Non-airport | 17,872,352 | 90.40 | 73.20 | 22.82 | 2.23 | 13.90 | 23.60 |
| From airport | 1,483,211 | 7.50 | 20.40 | 76.59 | 13.20 | 37.20 | 20.60 |
| To airport | 423,201 | 2.10 | 6.40 | 84.76 | 13.84 | 40.20 | 21.70 |

## 09_tip_rate_by_band_and_borough

**Question:** Where and when do credit-card passengers tip the most?  
**Technique:** Filtered aggregation (credit-card trips only), ratio of sums, plus the share of card trips with any tip.  
**Caveat:** Cash tips are not recorded, so these rates describe card payers only and say nothing about cash tipping.  
_Ran in 0.3s, 15 row(s)._

| pu_borough | time_band | card_trips | tip_pct_of_fare | pct_trips_tipped | median_tip |
|---|---|---|---|---|---|
| Brooklyn | Overnight | 7,982 | 19.30 | 85.10 | 3.80 |
| Brooklyn | AM peak | 6,523 | 17.80 | 84.00 | 4.34 |
| Brooklyn | Midday | 9,839 | 17.60 | 81.80 | 3.70 |
| Brooklyn | PM peak | 9,155 | 20.10 | 89.70 | 3.78 |
| Brooklyn | Evening | 11,386 | 20.60 | 91.40 | 3.76 |
| Manhattan | Overnight | 1,002,978 | 22.60 | 92.30 | 3.00 |
| Manhattan | AM peak | 1,608,832 | 23.00 | 96.70 | 2.90 |
| Manhattan | Midday | 4,362,467 | 23.00 | 96.70 | 3.05 |
| Manhattan | PM peak | 3,679,436 | 24.70 | 96.50 | 3.30 |
| Manhattan | Evening | 2,827,747 | 23.90 | 96.20 | 3.14 |
| Queens | Overnight | 83,737 | 18.90 | 92.00 | 10.29 |
| Queens | AM peak | 132,916 | 19.80 | 93.10 | 11.98 |
| Queens | Midday | 416,618 | 20.90 | 94.00 | 12.00 |
| Queens | PM peak | 345,505 | 21.20 | 94.20 | 12.13 |
| Queens | Evening | 325,123 | 20.40 | 94.40 | 10.99 |

## 10_speed_and_fare_per_mile_by_hour

**Question:** When is traffic slowest, and does that change what passengers pay per mile?  
**Technique:** Aggregation over eligible standard-rate trips; average speed as total miles / total hours.  
**Caveat:** Standard metered rate only (flat and Flex fares excluded). Speed is meter distance over meter time, a proxy for congestion, not a traffic measurement.  
_Ran in 0.1s, 24 row(s)._

| hour_label | time_band | std_rate_trips | avg_speed_mph | fare_per_mile | avg_fare |
|---|---|---|---|---|---|
| 00:00 | Overnight | 442,741 | 14.90 | 5.31 | 17.15 |
| 01:00 | Overnight | 294,586 | 14.40 | 5.41 | 15.66 |
| 02:00 | Overnight | 195,451 | 14.60 | 5.42 | 15.07 |
| 03:00 | Overnight | 124,987 | 15.60 | 5.25 | 15.45 |
| 04:00 | Overnight | 70,578 | 18.50 | 4.87 | 17.67 |
| 05:00 | Overnight | 74,334 | 21.00 | 4.69 | 18.09 |
| 06:00 | AM peak | 191,947 | 17.10 | 5.08 | 15.90 |
| 07:00 | AM peak | 430,902 | 13.20 | 5.71 | 15.33 |
| 08:00 | AM peak | 620,397 | 11.00 | 6.28 | 15.62 |
| 09:00 | AM peak | 720,533 | 10.70 | 6.38 | 16.27 |
| 10:00 | Midday | 789,691 | 10.50 | 6.42 | 16.68 |
| 11:00 | Midday | 852,938 | 9.80 | 6.69 | 16.57 |
| 12:00 | Midday | 922,122 | 9.80 | 6.71 | 16.60 |
| 13:00 | Midday | 945,054 | 9.90 | 6.62 | 16.77 |
| 14:00 | Midday | 1,011,697 | 9.70 | 6.63 | 17.14 |
| 15:00 | Midday | 1,038,758 | 9.50 | 6.68 | 17.08 |
| 16:00 | PM peak | 1,050,374 | 9.50 | 6.68 | 16.93 |
| 17:00 | PM peak | 1,156,015 | 9.30 | 6.81 | 16.26 |
| 18:00 | PM peak | 1,216,970 | 10.00 | 6.58 | 15.61 |
| 19:00 | PM peak | 1,065,009 | 11.30 | 6.14 | 15.65 |
| 20:00 | Evening | 959,690 | 12.30 | 5.84 | 15.99 |
| 21:00 | Evening | 975,665 | 12.70 | 5.73 | 16.29 |
| 22:00 | Evening | 879,980 | 13.10 | 5.63 | 16.84 |
| 23:00 | Evening | 650,944 | 14.40 | 5.38 | 17.74 |

## 11_daily_trend_rolling

**Question:** What is the underlying daily trend once weekly cycles are smoothed out, and how does each day compare with the same weekday a week earlier?  
**Technique:** 7-day moving average (AVG OVER ROWS BETWEEN 6 PRECEDING) and week-over-week change (LAG 7).  
**Caveat:** The first 6 days have a partial window; holidays create one-off dips that also affect the following week's comparison.  
_Ran in 0.2s, 182 row(s)._

| pickup_date | day_name | trips | trips_7day_avg | trips_same_day_last_week | wow_pct | holiday_name |
|---|---|---|---|---|---|---|
| 2024-01-01 | Monday | 78,606 | 78,606.00 |  |  | New Year's Day |
| 2024-01-02 | Tuesday | 73,429 | 76,018.00 |  |  |  |
| 2024-01-03 | Wednesday | 80,253 | 77,429.00 |  |  |  |
| 2024-01-04 | Thursday | 100,439 | 83,182.00 |  |  |  |
| 2024-01-05 | Friday | 100,654 | 86,676.00 |  |  |  |
| 2024-01-06 | Saturday | 94,710 | 88,015.00 |  |  |  |
| 2024-01-07 | Sunday | 65,678 | 84,824.00 |  |  |  |
| 2024-01-08 | Monday | 78,012 | 84,739.00 | 78,606 | -0.80 |  |
| 2024-01-09 | Tuesday | 91,898 | 87,378.00 | 73,429 | 25.20 |  |
| 2024-01-10 | Wednesday | 93,029 | 89,203.00 | 80,253 | 15.90 |  |
| 2024-01-11 | Thursday | 102,710 | 89,527.00 | 100,439 | 2.30 |  |
| 2024-01-12 | Friday | 101,334 | 89,624.00 | 100,654 | 0.70 |  |
| 2024-01-13 | Saturday | 102,241 | 90,700.00 | 94,710 | 8.00 |  |
| 2024-01-14 | Sunday | 92,051 | 94,468.00 | 65,678 | 40.20 |  |
| 2024-01-15 | Monday | 75,271 | 94,076.00 | 78,012 | -3.50 | Martin Luther King Jr. Day |
| 2024-01-16 | Tuesday | 91,097 | 93,962.00 | 91,898 | -0.90 |  |
| 2024-01-17 | Wednesday | 107,993 | 96,100.00 | 93,029 | 16.10 |  |
| 2024-01-18 | Thursday | 107,987 | 96,853.00 | 102,710 | 5.10 |  |
| 2024-01-19 | Friday | 93,648 | 95,755.00 | 101,334 | -7.60 |  |
| 2024-01-20 | Saturday | 106,196 | 96,320.00 | 102,241 | 3.90 |  |
| 2024-01-21 | Sunday | 82,283 | 94,925.00 | 92,051 | -10.60 |  |
| 2024-01-22 | Monday | 83,519 | 96,103.00 | 75,271 | 11.00 |  |
| 2024-01-23 | Tuesday | 97,664 | 97,041.00 | 91,097 | 7.20 |  |
| 2024-01-24 | Wednesday | 102,845 | 96,306.00 | 107,993 | -4.80 |  |
| 2024-01-25 | Thursday | 107,928 | 96,298.00 | 107,987 | -0.10 |  |

_157 more rows in the CSV._

## 12_holidays_vs_typical_day

**Question:** How much does demand drop on federal holidays compared with a typical day of the same weekday in the same month?  
**Technique:** Self-referencing CTE: baseline = average of non-holiday days sharing the month and weekday, joined back to each holiday.  
**Caveat:** Few holidays in six months; a baseline built from ~3-4 days is noisy. Treat as indicative.  
_Ran in 0.2s, 5 row(s)._

| pickup_date | holiday_name | day_name | trips | typical_trips_same_weekday | baseline_days | pct_vs_typical |
|---|---|---|---|---|---|---|
| 2024-01-01 | New Year's Day | Monday | 78,606 | 81,354.00 | 3 | -3.40 |
| 2024-01-15 | Martin Luther King Jr. Day | Monday | 75,271 | 81,354.00 | 3 | -7.50 |
| 2024-02-19 | Presidents' Day | Monday | 73,982 | 86,739.00 | 3 | -14.70 |
| 2024-05-27 | Memorial Day | Monday | 70,191 | 103,961.00 | 3 | -32.50 |
| 2024-06-19 | Juneteenth | Wednesday | 100,060 | 126,350.00 | 3 | -20.80 |

## 13_payment_mix_by_month

**Question:** How did the mix of payment methods change month to month (including the Flex Fare shift)?  
**Technique:** Grouped counts with share-of-month via SUM() OVER (PARTITION BY year_month).  
**Caveat:** Flex Fare is an upfront app-quoted price (TLC pilot); the data shows WHEN its share changed, not WHY.  
_Ran in 0.1s, 30 row(s)._

| year_month | payment_type_name | trips | pct_of_month |
|---|---|---|---|
| 2024-01 | Credit card | 2,318,231 | 80.10 |
| 2024-01 | Cash | 422,823 | 14.61 |
| 2024-01 | Flex Fare trip | 137,920 | 4.77 |
| 2024-01 | No charge | 8,577 | 0.30 |
| 2024-01 | Dispute | 6,762 | 0.23 |
| 2024-02 | Credit card | 2,341,280 | 79.81 |
| 2024-02 | Cash | 396,195 | 13.50 |
| 2024-02 | Flex Fare trip | 180,858 | 6.16 |
| 2024-02 | No charge | 8,365 | 0.29 |
| 2024-02 | Dispute | 7,031 | 0.24 |
| 2024-03 | Credit card | 2,596,241 | 74.54 |
| 2024-03 | Cash | 457,227 | 13.13 |
| 2024-03 | Flex Fare trip | 411,460 | 11.81 |
| 2024-03 | No charge | 9,917 | 0.28 |
| 2024-03 | Dispute | 8,310 | 0.24 |
| 2024-04 | Credit card | 2,554,780 | 74.78 |
| 2024-04 | Cash | 449,945 | 13.17 |
| 2024-04 | Flex Fare trip | 394,224 | 11.54 |
| 2024-04 | No charge | 9,401 | 0.28 |
| 2024-04 | Dispute | 8,045 | 0.24 |
| 2024-05 | Credit card | 2,727,118 | 75.36 |
| 2024-05 | Cash | 479,311 | 13.25 |
| 2024-05 | Flex Fare trip | 393,202 | 10.87 |
| 2024-05 | No charge | 10,047 | 0.28 |
| 2024-05 | Dispute | 8,976 | 0.25 |

_5 more rows in the CSV._

## 14_zone_rank_movers

**Question:** Which pickup zones moved up or down the rankings most between the first and last month?  
**Technique:** RANK() per month, then conditional aggregation (MAX ... FILTER) to pivot first vs last month side by side.  
**Caveat:** Limited to zones in the top 50 in either month, so small zones with big percentage swings don't dominate.  
_Ran in 0.6s, 15 row(s)._

| zone | borough | rank_first | rank_last | places_gained | pickups_first | pickups_last | pickups_change_pct |
|---|---|---|---|---|---|---|---|
| Lenox Hill East | Manhattan | 18 | 23 | -5 | 64,815 | 63,331 | -2.30 |
| Financial District North | Manhattan | 48 | 43 | 5 | 11,852 | 22,306 | 88.20 |
| Meatpacking/West Village West | Manhattan | 39 | 35 | 4 | 23,282 | 39,612 | 70.10 |
| Lincoln Square West | Manhattan | 33 | 36 | -3 | 34,902 | 38,410 | 10.10 |
| Lenox Hill West | Manhattan | 16 | 19 | -3 | 72,438 | 74,619 | 3.00 |
| East Harlem South | Manhattan | 41 | 44 | -3 | 17,786 | 21,325 | 19.90 |
| Morningside Heights | Manhattan | 44 | 47 | -3 | 13,534 | 14,897 | 10.10 |
| Kips Bay | Manhattan | 35 | 38 | -3 | 32,177 | 35,937 | 11.70 |
| Gramercy | Manhattan | 23 | 20 | 3 | 58,158 | 69,464 | 19.40 |
| East Village | Manhattan | 19 | 16 | 3 | 64,522 | 82,000 | 27.10 |
| Upper West Side South | Manhattan | 10 | 13 | -3 | 86,949 | 94,527 | 8.70 |
| Bloomingdale | Manhattan | 49 | 52 | -3 | 7,698 | 8,784 | 14.10 |
| Murray Hill | Manhattan | 12 | 10 | 2 | 81,306 | 100,942 | 24.20 |
| Greenwich Village North | Manhattan | 30 | 32 | -2 | 39,741 | 47,560 | 19.70 |
| LaGuardia Airport | Queens | 9 | 7 | 2 | 87,674 | 112,571 | 28.40 |

## 15_duration_by_borough_band

**Question:** How long do trips take from each borough at different times of day (median and 90th percentile)?  
**Technique:** Ordered-set aggregates (median, quantile_cont) grouped by two dimensions.  
**Caveat:** Long-duration trips (likely meters left running) excluded; medians used because durations are right-skewed.  
_Ran in 0.7s, 20 row(s)._

| pu_borough | time_band | trips | median_min | p90_min | median_miles |
|---|---|---|---|---|---|
| Bronx | Overnight | 6,140 | 21.70 | 53.80 | 5.98 |
| Bronx | AM peak | 18,838 | 33.20 | 74.40 | 6.30 |
| Bronx | Midday | 19,308 | 33.00 | 77.00 | 6.00 |
| Bronx | PM peak | 7,843 | 26.10 | 72.90 | 4.60 |
| Bronx | Evening | 5,534 | 17.60 | 36.30 | 4.68 |
| Brooklyn | Overnight | 37,257 | 18.80 | 36.70 | 4.35 |
| Brooklyn | AM peak | 57,776 | 30.90 | 73.90 | 5.14 |
| Brooklyn | Midday | 70,029 | 29.00 | 70.40 | 4.10 |
| Brooklyn | PM peak | 38,757 | 23.40 | 56.50 | 3.48 |
| Brooklyn | Evening | 43,299 | 18.90 | 34.10 | 3.78 |
| Manhattan | Overnight | 1,392,198 | 10.40 | 22.20 | 1.93 |
| Manhattan | AM peak | 2,144,835 | 10.80 | 24.20 | 1.60 |
| Manhattan | Midday | 5,689,464 | 12.50 | 28.40 | 1.50 |
| Manhattan | PM peak | 4,713,326 | 12.00 | 26.60 | 1.52 |
| Manhattan | Evening | 3,710,354 | 11.40 | 23.40 | 1.80 |
| Queens | Overnight | 125,131 | 23.90 | 41.10 | 11.11 |
| Queens | AM peak | 198,505 | 36.30 | 68.70 | 11.29 |
| Queens | Midday | 554,118 | 37.80 | 65.90 | 10.62 |
| Queens | PM peak | 446,060 | 37.90 | 64.20 | 11.50 |
| Queens | Evening | 411,814 | 27.00 | 44.80 | 11.29 |

## 16_data_quality_by_month

**Question:** How much of each month's data carries a quality flag, so readers know how reliable each metric is?  
**Technique:** Conditional aggregation over boolean flags, expressed as % of the month.  
**Caveat:** Flags mark trips that are kept but limited for some metrics; cleaning removals are reported in reports/phase2_cleaning_log.md.  
_Ran in 0.2s, 6 row(s)._

| year_month | trips | pct_flex_fare_incomplete | pct_passenger_unknown | pct_zero_distance | pct_catchall_zone | pct_long_duration | pct_tip_rate_eligible | pct_fare_per_mile_eligible |
|---|---|---|---|---|---|---|---|---|
| 2024-01 | 2,894,313 | 4.77 | 5.85 | 1.83 | 1.02 | 0.07 | 79.10 | 89.30 |
| 2024-02 | 2,933,729 | 6.16 | 7.32 | 2.08 | 0.92 | 0.07 | 78.80 | 88.30 |
| 2024-03 | 3,483,155 | 11.81 | 12.97 | 2.26 | 0.95 | 0.06 | 73.50 | 82.30 |
| 2024-04 | 3,416,395 | 11.54 | 12.69 | 1.08 | 0.97 | 0.07 | 73.60 | 82.40 |
| 2024-05 | 3,618,654 | 10.87 | 11.95 | 1.11 | 1.00 | 0.06 | 74.20 | 83.00 |
| 2024-06 | 3,432,518 | 11.57 | 12.60 | 1.26 | 1.05 | 0.06 | 73.80 | 82.30 |

## 17_tip_recording_gap

**Question:** Are tips recorded consistently across vendors and rate codes for credit-card trips?  
**Technique:** Grouped aggregation with conditional counts, used as a data-reliability check rather than a behaviour metric.  
**Caveat:** A 0% tipped rate across thousands of trips means tips are not captured for that segment, not that passengers never tip. The data cannot say why. This is why tip_rate_eligible excludes rate code 99.  
_Ran in 0.2s, 20 row(s)._

| vendor_name | ratecode_name | pu_borough | card_trips | pct_tipped | tip_pct_of_fare | pct_of_all_card_trips |
|---|---|---|---|---|---|---|
| Creative Mobile Technologies, LLC | Null/unknown | Brooklyn | 81,880 | 0.00 | 0.00 | 0.54 |
| Creative Mobile Technologies, LLC | Null/unknown | Manhattan | 62,336 | 0.00 | 0.00 | 0.41 |
| Creative Mobile Technologies, LLC | Null/unknown | Queens | 39,432 | 0.00 | 0.00 | 0.26 |
| Creative Mobile Technologies, LLC | Null/unknown | Bronx | 29,510 | 0.00 | 0.00 | 0.20 |
| Creative Mobile Technologies, LLC | Standard rate | Bronx | 1,296 | 20.10 | 4.50 | 0.01 |
| Curb Mobility, LLC | Negotiated fare | N/A | 4,555 | 65.10 | 10.40 | 0.03 |
| Curb Mobility, LLC | Negotiated fare | EWR | 1,784 | 68.90 | 12.30 | 0.01 |
| Curb Mobility, LLC | Negotiated fare | Brooklyn | 3,454 | 72.40 | 13.20 | 0.02 |
| Creative Mobile Technologies, LLC | Standard rate | Brooklyn | 9,821 | 72.80 | 15.60 | 0.07 |
| Curb Mobility, LLC | Standard rate | Bronx | 1,272 | 75.30 | 23.10 | 0.01 |
| Creative Mobile Technologies, LLC | Negotiated fare | Manhattan | 9,863 | 79.60 | 15.30 | 0.07 |
| Curb Mobility, LLC | Negotiated fare | Manhattan | 48,035 | 80.90 | 15.60 | 0.32 |
| Creative Mobile Technologies, LLC | Negotiated fare | Queens | 4,035 | 82.40 | 14.50 | 0.03 |
| Curb Mobility, LLC | Negotiated fare | Queens | 31,348 | 84.10 | 15.10 | 0.21 |
| Curb Mobility, LLC | Negotiated fare | Unknown | 1,143 | 84.40 | 15.20 | 0.01 |
| Creative Mobile Technologies, LLC | Nassau or Westchester | Queens | 3,787 | 85.90 | 14.80 | 0.03 |
| Curb Mobility, LLC | Nassau or Westchester | Queens | 20,221 | 87.00 | 14.70 | 0.13 |
| Curb Mobility, LLC | Nassau or Westchester | Manhattan | 5,171 | 87.00 | 16.80 | 0.03 |
| Curb Mobility, LLC | Newark | Queens | 4,179 | 88.80 | 17.00 | 0.03 |
| Creative Mobile Technologies, LLC | Newark | Manhattan | 8,275 | 92.20 | 19.80 | 0.05 |
