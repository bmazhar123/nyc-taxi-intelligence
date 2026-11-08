-- Check: Every date in the study period has at least one trip.
-- Severity: warn
-- Why: A day with zero trips in a city taxi dataset almost certainly means a missing or truncated source file, not a real absence of demand.
SELECT d.full_date, d.day_name
FROM dim_date d
ANTI JOIN fact_trips f ON f.pickup_date_key = d.date_key
ORDER BY d.full_date;
