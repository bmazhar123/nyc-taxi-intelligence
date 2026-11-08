-- Check: dim_date has every calendar day between its first and last date, with no gaps or duplicates.
-- Severity: error
-- Why: A missing date makes daily trend lines skip days and makes "per day" averages divide by the wrong number.
SELECT MIN(full_date) AS first_date, MAX(full_date) AS last_date, COUNT(*) AS rows_in_dim,
       date_diff('day', MIN(full_date), MAX(full_date)) + 1 AS expected_rows,
       COUNT(DISTINCT full_date) AS distinct_dates
FROM dim_date
HAVING COUNT(*) <> date_diff('day', MIN(full_date), MAX(full_date)) + 1
    OR COUNT(*) <> COUNT(DISTINCT full_date);
