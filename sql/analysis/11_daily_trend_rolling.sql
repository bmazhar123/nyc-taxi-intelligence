-- Question: What is the underlying daily trend once weekly cycles are smoothed out, and how does each day compare with the same weekday a week earlier?
-- Technique: 7-day moving average (AVG OVER ROWS BETWEEN 6 PRECEDING) and week-over-week change (LAG 7).
-- Caveat: The first 6 days have a partial window; holidays create one-off dips that also affect the following week's comparison.
SELECT pickup_date, day_name, trips,
       ROUND(AVG(trips) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)) AS trips_7day_avg,
       LAG(trips, 7) OVER (ORDER BY pickup_date)                                             AS trips_same_day_last_week,
       ROUND(100.0 * trips / LAG(trips, 7) OVER (ORDER BY pickup_date) - 100, 1)             AS wow_pct,
       holiday_name
FROM v_daily_kpis
ORDER BY pickup_date;
