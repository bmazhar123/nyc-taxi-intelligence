-- =====================================================================
-- v_hourly_demand: one row per date x hour (days x 24). Feeds the
-- demand heatmap (day of week x hour) and staffing analysis.
-- Hours with zero trips simply have no row; queries that average per
-- hour must divide by the number of DAYS, not the number of rows.
-- =====================================================================
CREATE OR REPLACE VIEW v_hourly_demand AS
SELECT
    pickup_date,
    day_of_week,
    day_name,
    is_weekend,
    is_us_federal_holiday,
    pickup_hour AS hour,
    hour_label,
    time_band,
    time_band_order,
    COUNT(*)                                            AS trips,
    SUM(total_amount)                                   AS total_amount_sum,
    median(trip_duration_minutes) FILTER (WHERE duration_eligible) AS median_duration_min
FROM v_trips
GROUP BY ALL;
