-- Question: How long do trips take from each borough at different times of day (median and 90th percentile)?
-- Technique: Ordered-set aggregates (median, quantile_cont) grouped by two dimensions.
-- Caveat: Long-duration trips (likely meters left running) excluded; medians used because durations are right-skewed.
SELECT pu_borough, time_band,
       COUNT(*)                                                     AS trips,
       ROUND(median(trip_duration_minutes), 1)                      AS median_min,
       ROUND(quantile_cont(trip_duration_minutes, 0.9), 1)          AS p90_min,
       ROUND(median(trip_distance), 2)                              AS median_miles
FROM v_trips
WHERE duration_eligible AND NOT pu_is_catchall
GROUP BY ALL
HAVING COUNT(*) >= 1000
ORDER BY pu_borough, MIN(time_band_order);
