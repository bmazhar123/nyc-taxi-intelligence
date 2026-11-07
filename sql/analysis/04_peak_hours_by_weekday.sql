-- Question: Which three hours are busiest on each day of the week?
-- Technique: RANK() window function partitioned by weekday, filtered with QUALIFY.
-- Caveat: Based on average pickups per hour across all weeks in the period.
WITH by_dow AS (
    SELECT day_of_week, day_name, hour_label,
           SUM(trips) / COUNT(DISTINCT pickup_date) AS avg_trips
    FROM v_hourly_demand
    GROUP BY ALL
)
SELECT day_name, hour_label, ROUND(avg_trips) AS avg_trips,
       RANK() OVER (PARTITION BY day_of_week ORDER BY avg_trips DESC) AS rank_in_day
FROM by_dow
QUALIFY rank_in_day <= 3
ORDER BY day_of_week, rank_in_day;
