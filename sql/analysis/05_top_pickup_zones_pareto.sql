-- Question: Which pickup zones generate the most trips, and how concentrated is demand?
-- Technique: Aggregation + running total with SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING) for a Pareto view.
-- Caveat: Excludes catch-all zones 264/265. Pickup counts measure where trips START, not where demand originates (e.g. airport queues).
WITH z AS (
    SELECT zone, borough, SUM(pickups) AS pickups, SUM(total_amount_sum) AS total_amount
    FROM v_zone_daily GROUP BY ALL
)
SELECT zone, borough, pickups,
       ROUND(100.0 * pickups / SUM(pickups) OVER (), 2)                                   AS pct_of_pickups,
       ROUND(100.0 * SUM(pickups) OVER (ORDER BY pickups DESC ROWS UNBOUNDED PRECEDING)
             / SUM(pickups) OVER (), 1)                                                   AS cumulative_pct,
       ROUND(total_amount / pickups, 2)                                                   AS avg_total_amount
FROM z
ORDER BY pickups DESC
LIMIT 20;
