-- =====================================================================
-- v_daily_kpis: one row per day. Small (one row per date), so it is the
-- main table for Power BI trend charts and KPI cards.
-- Ratios are stored as numerator + denominator columns so they can be
-- re-aggregated correctly to week/month (sum the parts, then divide);
-- averaging daily ratios would weight a quiet day the same as a busy one.
-- =====================================================================
CREATE OR REPLACE VIEW v_daily_kpis AS
SELECT
    pickup_date,
    pickup_date_key,
    year_month,
    month_name,
    day_of_week,
    day_name,
    is_weekend,
    is_us_federal_holiday,
    holiday_name,
    COUNT(*)                                                            AS trips,
    SUM(total_amount)                                                   AS total_amount_sum,
    SUM(fare_amount)                                                    AS fare_amount_sum,
    SUM(trip_distance)                                                  AS distance_sum,
    SUM(trip_duration_minutes) FILTER (WHERE duration_eligible)         AS duration_minutes_sum,
    COUNT(*) FILTER (WHERE duration_eligible)                           AS duration_trips,
    SUM(fare_amount)   FILTER (WHERE fare_per_mile_eligible)            AS fpm_fare_sum,
    SUM(trip_distance) FILTER (WHERE fare_per_mile_eligible)            AS fpm_distance_sum,
    SUM(tip_amount)    FILTER (WHERE tip_rate_eligible)                 AS tip_sum_card,
    SUM(fare_amount)   FILTER (WHERE tip_rate_eligible)                 AS fare_sum_card,
    COUNT(*) FILTER (WHERE tip_rate_eligible)                           AS card_trips,
    COUNT(*) FILTER (WHERE tip_rate_eligible AND tip_amount > 0)        AS card_trips_tipped,
    COUNT(*) FILTER (WHERE is_airport_trip)                             AS airport_trips,
    COUNT(*) FILTER (WHERE payment_type_key = 0)                        AS flex_fare_trips,
    ROUND(SUM(fare_amount) / COUNT(*), 2)                               AS avg_fare,
    ROUND(SUM(fare_amount) FILTER (WHERE fare_per_mile_eligible)
          / NULLIF(SUM(trip_distance) FILTER (WHERE fare_per_mile_eligible), 0), 2) AS fare_per_mile,
    ROUND(100 * SUM(tip_amount) FILTER (WHERE tip_rate_eligible)
          / NULLIF(SUM(fare_amount) FILTER (WHERE tip_rate_eligible), 0), 2)        AS tip_pct_of_fare
FROM v_trips
GROUP BY ALL;
