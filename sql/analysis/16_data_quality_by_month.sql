-- Question: How much of each month's data carries a quality flag, so readers know how reliable each metric is?
-- Technique: Conditional aggregation over boolean flags, expressed as % of the month.
-- Caveat: Flags mark trips that are kept but limited for some metrics; cleaning removals are reported in reports/phase2_cleaning_log.md.
SELECT year_month,
       COUNT(*)                                                                     AS trips,
       ROUND(100.0 * COUNT(*) FILTER (WHERE flag_flex_fare_incomplete) / COUNT(*), 2) AS pct_flex_fare_incomplete,
       ROUND(100.0 * COUNT(*) FILTER (WHERE flag_passenger_unknown)    / COUNT(*), 2) AS pct_passenger_unknown,
       ROUND(100.0 * COUNT(*) FILTER (WHERE flag_zero_distance)        / COUNT(*), 2) AS pct_zero_distance,
       ROUND(100.0 * COUNT(*) FILTER (WHERE flag_catchall_zone)        / COUNT(*), 2) AS pct_catchall_zone,
       ROUND(100.0 * COUNT(*) FILTER (WHERE flag_long_duration)        / COUNT(*), 3) AS pct_long_duration,
       ROUND(100.0 * COUNT(*) FILTER (WHERE tip_rate_eligible)         / COUNT(*), 1) AS pct_tip_rate_eligible,
       ROUND(100.0 * COUNT(*) FILTER (WHERE fare_per_mile_eligible)    / COUNT(*), 1) AS pct_fare_per_mile_eligible
FROM v_trips
GROUP BY ALL
ORDER BY year_month;
