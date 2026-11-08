-- Check: No quality flag's share of trips moves more than {max_flag_shift_pp} percentage points from one month to the next.
-- Severity: warn
-- Why: A sudden shift (like Flex Fare in March 2024) changes how reliable some metrics are; it may be real, but it must be explained before month-to-month comparisons are trusted.
WITH m AS (
    SELECT year_month,
           100.0 * AVG(flag_flex_fare_incomplete::INT) AS flex_fare_incomplete,
           100.0 * AVG(flag_passenger_unknown::INT)    AS passenger_unknown,
           100.0 * AVG(flag_zero_distance::INT)        AS zero_distance,
           100.0 * AVG(flag_catchall_zone::INT)        AS catchall_zone,
           100.0 * AVG(flag_long_duration::INT)        AS long_duration
    FROM v_trips GROUP BY year_month
), long AS (
    UNPIVOT m ON COLUMNS(* EXCLUDE (year_month)) INTO NAME flag VALUE pct
), shifts AS (
    SELECT flag, year_month, pct,
           pct - LAG(pct) OVER (PARTITION BY flag ORDER BY year_month) AS change_pp
    FROM long
)
SELECT flag, year_month, ROUND(pct, 2) AS pct_of_trips, ROUND(change_pp, 2) AS change_pp
FROM shifts
WHERE ABS(change_pp) > {max_flag_shift_pp}
ORDER BY flag, year_month;
