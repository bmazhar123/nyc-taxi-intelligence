-- Check: Columns every metric depends on are never NULL.
-- Severity: error
-- Why: NULL keys drop trips from joins; NULL amounts or times silently shrink sums and averages.
WITH c AS (
    SELECT COUNT(*) FILTER (WHERE trip_id IS NULL)          AS trip_id,
           COUNT(*) FILTER (WHERE pickup_datetime IS NULL)  AS pickup_datetime,
           COUNT(*) FILTER (WHERE dropoff_datetime IS NULL) AS dropoff_datetime,
           COUNT(*) FILTER (WHERE pickup_date_key IS NULL)  AS pickup_date_key,
           COUNT(*) FILTER (WHERE pickup_hour IS NULL)      AS pickup_hour,
           COUNT(*) FILTER (WHERE pu_location_id IS NULL)   AS pu_location_id,
           COUNT(*) FILTER (WHERE do_location_id IS NULL)   AS do_location_id,
           COUNT(*) FILTER (WHERE vendor_key IS NULL)       AS vendor_key,
           COUNT(*) FILTER (WHERE ratecode_key IS NULL)     AS ratecode_key,
           COUNT(*) FILTER (WHERE payment_type_key IS NULL) AS payment_type_key,
           COUNT(*) FILTER (WHERE trip_distance IS NULL)    AS trip_distance,
           COUNT(*) FILTER (WHERE fare_amount IS NULL)      AS fare_amount,
           COUNT(*) FILTER (WHERE total_amount IS NULL)     AS total_amount
    FROM fact_trips
)
SELECT column_name, null_rows
FROM (UNPIVOT c ON COLUMNS(*) INTO NAME column_name VALUE null_rows)
WHERE null_rows > 0;
