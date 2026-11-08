-- Check: For every month, raw rows = warehouse rows + excluded rows.
-- Severity: error
-- Why: Proves the pipeline neither lost nor duplicated a single row between the downloaded files and the warehouse.
WITH raw AS (
    SELECT regexp_extract(filename, 'yellow_tripdata_(\d{4}-\d{2})', 1) AS month, COUNT(*) AS raw_rows
    FROM read_parquet('{raw_glob}', union_by_name = true, filename = true)
    GROUP BY 1
), kept AS (
    SELECT source_month AS month, COUNT(*) AS kept_rows FROM fact_trips GROUP BY 1
), excl AS (
    SELECT source_month AS month, COUNT(*) AS excluded_rows FROM read_parquet('{excluded_parquet}') GROUP BY 1
)
SELECT month, COALESCE(raw_rows, 0) AS raw_rows, COALESCE(kept_rows, 0) AS kept_rows,
       COALESCE(excluded_rows, 0) AS excluded_rows
FROM raw FULL JOIN kept USING (month) FULL JOIN excl USING (month)
WHERE COALESCE(raw_rows, 0) <> COALESCE(kept_rows, 0) + COALESCE(excluded_rows, 0)
ORDER BY month;
