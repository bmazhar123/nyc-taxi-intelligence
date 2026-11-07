-- Question: How do weekdays and weekends differ in volume, fare, duration and tipping?
-- Technique: Aggregate daily rows first (so "per day" divides by real day counts), then compare groups; ratio-of-sums for rates.
-- Caveat: Holidays are counted under their weekday; tip % uses credit-card trips only because cash tips are not recorded.
SELECT CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END                AS day_type,
       COUNT(*)                                                               AS days,
       ROUND(AVG(trips))                                                      AS avg_trips_per_day,
       ROUND(SUM(fare_amount_sum) / SUM(trips), 2)                            AS avg_fare,
       ROUND(SUM(distance_sum) / SUM(trips), 2)                               AS avg_distance_mi,
       ROUND(SUM(duration_minutes_sum) / SUM(duration_trips), 1)              AS avg_duration_min,
       ROUND(SUM(fpm_fare_sum) / SUM(fpm_distance_sum), 2)                    AS fare_per_mile_std_rate,
       ROUND(100 * SUM(tip_sum_card) / SUM(fare_sum_card), 1)                 AS tip_pct_of_fare_card,
       ROUND(100.0 * SUM(airport_trips) / SUM(trips), 1)                      AS airport_trip_pct
FROM v_daily_kpis
GROUP BY ALL
ORDER BY day_type DESC;
