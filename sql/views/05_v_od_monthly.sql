-- =====================================================================
-- v_od_monthly: origin -> destination trip flows by month at zone level.
-- Feeds "where do trips from X go?" drill-through analysis.
-- =====================================================================
CREATE OR REPLACE VIEW v_od_monthly AS
SELECT
    year_month,
    pu_location_id, pu_borough, pu_zone,
    do_location_id, do_borough, do_zone,
    COUNT(*)              AS trips,
    SUM(total_amount)     AS total_amount_sum,
    AVG(trip_distance)    AS avg_distance
FROM v_trips
WHERE NOT pu_is_catchall AND NOT do_is_catchall
GROUP BY ALL;
