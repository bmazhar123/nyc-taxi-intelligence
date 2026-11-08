-- Check: No more than {max_catchall_pct}% of a month's trips start or end in catch-all zones 264/265.
-- Severity: warn
-- Why: Catch-all zones are excluded from maps and zone rankings, so if their share grows, geographic results quietly cover less of the data.
SELECT year_month, COUNT(*) AS trips,
       ROUND(100.0 * COUNT(*) FILTER (WHERE flag_catchall_zone) / COUNT(*), 2) AS pct_catchall
FROM v_trips
GROUP BY year_month
HAVING 100.0 * COUNT(*) FILTER (WHERE flag_catchall_zone) / COUNT(*) > {max_catchall_pct}
ORDER BY year_month;
