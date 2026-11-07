-- Question: What does a typical day's demand curve look like, hour by hour, on weekdays vs weekends?
-- Technique: Average trips per hour (divided by number of days), plus each hour's share of the day using SUM() OVER (PARTITION BY ...).
-- Caveat: Averages hide variation between individual days; see query 11 for day-level trends.
WITH days AS (
    SELECT is_weekend, COUNT(DISTINCT pickup_date) AS n_days FROM v_hourly_demand GROUP BY ALL
), hourly AS (
    SELECT h.is_weekend, h.hour, h.hour_label, h.time_band,
           SUM(h.trips) / MAX(d.n_days) AS avg_trips
    FROM v_hourly_demand h JOIN days d USING (is_weekend)
    GROUP BY ALL
)
SELECT CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       hour_label, time_band,
       ROUND(avg_trips)                                                            AS avg_trips,
       ROUND(100 * avg_trips / SUM(avg_trips) OVER (PARTITION BY is_weekend), 2)   AS pct_of_day
FROM hourly
ORDER BY day_type, hour_label;
