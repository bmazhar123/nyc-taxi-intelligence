-- Question: How did trips, recorded charges and average fare change month over month?
-- Technique: CTE + LAG window function for month-over-month % change.
-- Caveat: total_amount is the amount charged to passengers (incl. taxes, tolls, surcharges), not revenue or driver income. Months have different numbers of days, so trips per day is the fairer comparison.
WITH m AS (
    SELECT year_month,
           COUNT(DISTINCT pickup_date)   AS days,
           SUM(trips)                    AS trips,
           SUM(total_amount_sum)         AS total_amount,
           SUM(fare_amount_sum) / SUM(trips) AS avg_fare
    FROM v_daily_kpis
    GROUP BY year_month
)
SELECT year_month,
       days,
       trips,
       ROUND(trips / days)                                                         AS trips_per_day,
       ROUND(100.0 * (trips / days) / LAG(trips / days) OVER (ORDER BY year_month) - 100, 1) AS trips_per_day_mom_pct,
       ROUND(total_amount, 0)                                                      AS total_amount,
       ROUND(100.0 * total_amount / LAG(total_amount) OVER (ORDER BY year_month) - 100, 1)   AS total_amount_mom_pct,
       ROUND(avg_fare, 2)                                                          AS avg_fare
FROM m
ORDER BY year_month;
