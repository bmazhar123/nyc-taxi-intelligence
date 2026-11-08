-- Check: No day falls below {daily_drop_ratio} x the median of the same weekday in the same month.
-- Severity: warn
-- Why: A sudden collapse in volume is more often a data problem (partial file, vendor outage) than real demand; holidays and storms are legitimate exceptions to review.
WITH d AS (
    SELECT pickup_date, year_month, day_name, holiday_name, trips,
           median(trips) OVER (PARTITION BY year_month, day_of_week) AS typical
    FROM v_daily_kpis
)
SELECT pickup_date, day_name, holiday_name, trips, ROUND(typical) AS typical_same_weekday,
       ROUND(trips / typical, 2) AS ratio
FROM d
WHERE trips < {daily_drop_ratio} * typical
ORDER BY pickup_date;
