-- Check: Every analysis view adds back up to the fact table (row counts and, where stored exactly, amounts).
-- Severity: error
-- Why: A view with a wrong JOIN can silently drop or duplicate trips; this catches it before a dashboard does.
WITH f AS (
    SELECT COUNT(*) AS n, SUM(CAST(total_amount AS DECIMAL(18, 2))) AS amt FROM fact_trips
), objs AS (
    SELECT 'v_trips' AS object, (SELECT COUNT(*) FROM v_trips) AS n,
           (SELECT SUM(CAST(total_amount AS DECIMAL(18, 2))) FROM v_trips) AS amt
    UNION ALL SELECT 'v_daily_kpis (sum of trips)', (SELECT SUM(trips) FROM v_daily_kpis), NULL
    UNION ALL SELECT 'v_hourly_demand (sum of trips)', (SELECT SUM(trips) FROM v_hourly_demand), NULL
    UNION ALL SELECT 'v_zone_daily + catch-all pickups',
                     (SELECT SUM(pickups) FROM v_zone_daily) + (SELECT COUNT(*) FROM v_trips WHERE pu_is_catchall), NULL
)
SELECT o.object, o.n AS object_rows, f.n AS fact_rows, o.amt AS object_amount, f.amt AS fact_amount
FROM objs o, f
WHERE o.n <> f.n OR (o.amt IS NOT NULL AND o.amt <> f.amt);
