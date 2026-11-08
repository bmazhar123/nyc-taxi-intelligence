-- Check: Cleaning removes no more than {max_removal_pct}% of any month's raw rows.
-- Severity: warn
-- Why: Removal rates have been about 2-3%; a jump means either a much dirtier source file or a cleaning rule misbehaving.
WITH kept AS (SELECT source_month, COUNT(*) AS kept FROM fact_trips GROUP BY 1),
excl AS (SELECT source_month, COUNT(*) AS removed FROM read_parquet('{excluded_parquet}') GROUP BY 1)
SELECT source_month, kept, removed, ROUND(100.0 * removed / (kept + removed), 2) AS pct_removed
FROM kept JOIN excl USING (source_month)
WHERE 100.0 * removed / (kept + removed) > {max_removal_pct}
ORDER BY source_month;
