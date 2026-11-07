-- Question: How many of the city's taxi zones account for half, 80% and 95% of all pickups?
-- Technique: CTE with cumulative share window, then conditional aggregation.
-- Caveat: Zones differ greatly in size, so concentration partly reflects geography, not only demand.
WITH z AS (
    SELECT location_id, SUM(pickups) AS pickups FROM v_zone_daily GROUP BY 1
), c AS (
    SELECT location_id,
           SUM(pickups) OVER (ORDER BY pickups DESC ROWS UNBOUNDED PRECEDING) / SUM(pickups) OVER () AS cum_share
    FROM z
)
SELECT COUNT(*)                                   AS zones_with_pickups,
       LEAST(COUNT(*) FILTER (WHERE cum_share <= 0.50) + 1, COUNT(*)) AS zones_for_50pct,
       LEAST(COUNT(*) FILTER (WHERE cum_share <= 0.80) + 1, COUNT(*)) AS zones_for_80pct,
       LEAST(COUNT(*) FILTER (WHERE cum_share <= 0.95) + 1, COUNT(*)) AS zones_for_95pct
FROM c;
