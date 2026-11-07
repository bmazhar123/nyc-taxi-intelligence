-- Question: Which pickup zones moved up or down the rankings most between the first and last month?
-- Technique: RANK() per month, then conditional aggregation (MAX ... FILTER) to pivot first vs last month side by side.
-- Caveat: Limited to zones in the top 50 in either month, so small zones with big percentage swings don't dominate.
WITH bounds AS (
    SELECT MIN(year_month) AS first_m, MAX(year_month) AS last_m FROM v_zone_daily
), ranked AS (
    SELECT year_month, zone, borough, SUM(pickups) AS pickups,
           RANK() OVER (PARTITION BY year_month ORDER BY SUM(pickups) DESC) AS rnk
    FROM v_zone_daily
    GROUP BY year_month, zone, borough
), pivoted AS (
    SELECT zone, borough,
           MAX(rnk)     FILTER (WHERE year_month = first_m) AS rank_first,
           MAX(rnk)     FILTER (WHERE year_month = last_m)  AS rank_last,
           MAX(pickups) FILTER (WHERE year_month = first_m) AS pickups_first,
           MAX(pickups) FILTER (WHERE year_month = last_m)  AS pickups_last
    FROM ranked, bounds
    GROUP BY zone, borough
)
SELECT zone, borough, rank_first, rank_last,
       rank_first - rank_last                                   AS places_gained,
       pickups_first, pickups_last,
       ROUND(100.0 * pickups_last / pickups_first - 100, 1)     AS pickups_change_pct
FROM pivoted
WHERE rank_first <= 50 OR rank_last <= 50
ORDER BY ABS(rank_first - rank_last) DESC NULLS LAST
LIMIT 15;
