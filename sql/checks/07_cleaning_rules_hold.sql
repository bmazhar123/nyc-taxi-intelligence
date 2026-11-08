-- Check: No trip in the warehouse breaks any Phase 2 exclusion rule.
-- Severity: error
-- Why: Re-tests the cleaning output independently, so a bug in the cleaning code cannot let impossible trips through unnoticed.
SELECT * FROM (
    SELECT 'pickup outside its file month' AS rule, COUNT(*) AS violating_rows FROM fact_trips
    WHERE strftime(pickup_datetime, '%Y-%m') <> source_month
    UNION ALL SELECT 'drop-off at or before pickup', COUNT(*) FROM fact_trips
    WHERE dropoff_datetime <= pickup_datetime
    UNION ALL SELECT 'duration over {max_duration_hours} hours', COUNT(*) FROM fact_trips
    WHERE trip_duration_minutes > {max_duration_hours} * 60
    UNION ALL SELECT 'negative money value', COUNT(*) FROM fact_trips
    WHERE fare_amount < 0 OR extra < 0 OR mta_tax < 0 OR tip_amount < 0 OR tolls_amount < 0
       OR improvement_surcharge < 0 OR total_amount < 0 OR congestion_surcharge < 0
       OR airport_fee < 0 OR cbd_congestion_fee < 0
    UNION ALL SELECT 'average speed over {max_speed_mph} mph', COUNT(*) FROM fact_trips
    WHERE trip_distance > 0 AND trip_duration_minutes > 0
      AND trip_distance / (trip_duration_minutes / 60.0) > {max_speed_mph}
    UNION ALL SELECT 'implausible amount for distance', COUNT(*) FROM fact_trips
    WHERE total_amount > {amount_floor}
      AND (trip_distance <= 0 OR total_amount / trip_distance > {max_amount_per_mile})
)
WHERE violating_rows > 0;
