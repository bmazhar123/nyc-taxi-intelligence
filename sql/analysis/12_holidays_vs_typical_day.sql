-- Question: How much does demand drop on federal holidays compared with a typical day of the same weekday in the same month?
-- Technique: Self-referencing CTE: baseline = average of non-holiday days sharing the month and weekday, joined back to each holiday.
-- Caveat: Few holidays in six months; a baseline built from ~3-4 days is noisy. Treat as indicative.
WITH baseline AS (
    SELECT year_month, day_of_week, AVG(trips) AS typical_trips, COUNT(*) AS baseline_days
    FROM v_daily_kpis
    WHERE NOT is_us_federal_holiday
    GROUP BY ALL
)
SELECT h.pickup_date, h.holiday_name, h.day_name, h.trips,
       ROUND(b.typical_trips)                                 AS typical_trips_same_weekday,
       b.baseline_days,
       ROUND(100.0 * h.trips / b.typical_trips - 100, 1)      AS pct_vs_typical
FROM v_daily_kpis h
JOIN baseline b USING (year_month, day_of_week)
WHERE h.is_us_federal_holiday
ORDER BY h.pickup_date;
