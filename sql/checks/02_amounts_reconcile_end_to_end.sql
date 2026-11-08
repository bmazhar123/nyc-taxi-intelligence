-- Check: For every month, raw total_amount = warehouse total_amount + excluded total_amount, to the cent.
-- Severity: error
-- Why: Proves no money was lost or invented. Amounts are summed as DECIMAL so the comparison is exact, with no floating-point rounding drift.
WITH raw AS (
    SELECT regexp_extract(filename, 'yellow_tripdata_(\d{4}-\d{2})', 1) AS month,
           SUM(CAST(total_amount AS DECIMAL(18, 2))) AS raw_amount
    FROM read_parquet('{raw_glob}', union_by_name = true, filename = true)
    GROUP BY 1
), kept AS (
    SELECT source_month AS month, SUM(CAST(total_amount AS DECIMAL(18, 2))) AS kept_amount
    FROM fact_trips GROUP BY 1
), excl AS (
    SELECT source_month AS month, SUM(CAST(total_amount AS DECIMAL(18, 2))) AS excluded_amount
    FROM read_parquet('{excluded_parquet}') GROUP BY 1
)
SELECT month, raw_amount, COALESCE(kept_amount, 0) AS kept_amount, COALESCE(excluded_amount, 0) AS excluded_amount,
       raw_amount - COALESCE(kept_amount, 0) - COALESCE(excluded_amount, 0) AS difference
FROM raw FULL JOIN kept USING (month) FULL JOIN excl USING (month)
WHERE COALESCE(raw_amount, 0) <> COALESCE(kept_amount, 0) + COALESCE(excluded_amount, 0)
ORDER BY month;
