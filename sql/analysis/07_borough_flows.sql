-- Question: Where do trips go? Borough-to-borough flow matrix with each origin's destination mix.
-- Technique: JOIN to the zone dimension twice (pickup and drop-off roles) via v_trips; share within origin using a partitioned window.
-- Caveat: Catch-all zones excluded. Borough is the zone lookup's borough (EWR = Newark Airport).
SELECT pu_borough, do_borough,
       COUNT(*)                                                                         AS trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)                               AS pct_of_all_trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY pu_borough), 1)        AS pct_of_origin_trips
FROM v_trips
WHERE NOT pu_is_catchall AND NOT do_is_catchall
GROUP BY pu_borough, do_borough
ORDER BY trips DESC
LIMIT 20;
