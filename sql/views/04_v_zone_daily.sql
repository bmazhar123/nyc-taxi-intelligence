-- =====================================================================
-- v_zone_daily: one row per date x pickup zone (excluding catch-all
-- zones 264/265, which are not real places). Feeds the map and zone
-- ranking visuals.
-- =====================================================================
CREATE OR REPLACE VIEW v_zone_daily AS
SELECT
    pickup_date,
    year_month,
    is_weekend,
    pu_location_id AS location_id,
    pu_borough     AS borough,
    pu_zone        AS zone,
    pu_is_airport  AS is_airport,
    COUNT(*)                                                     AS pickups,
    SUM(total_amount)                                            AS total_amount_sum,
    SUM(fare_amount)                                             AS fare_amount_sum,
    SUM(trip_distance)                                           AS distance_sum,
    SUM(tip_amount)  FILTER (WHERE tip_rate_eligible)            AS tip_sum_card,
    SUM(fare_amount) FILTER (WHERE tip_rate_eligible)            AS fare_sum_card
FROM v_trips
WHERE NOT pu_is_catchall
GROUP BY ALL;
