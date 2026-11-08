-- Check: trip_id is unique in fact_trips.
-- Severity: error
-- Why: trip_id is the fact table's key; a duplicate means a trip is counted twice in every metric.
SELECT trip_id, COUNT(*) AS copies
FROM fact_trips
GROUP BY trip_id
HAVING COUNT(*) > 1
LIMIT 20;
