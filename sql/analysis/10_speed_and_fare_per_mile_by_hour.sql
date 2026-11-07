-- Question: When is traffic slowest, and does that change what passengers pay per mile?
-- Technique: Aggregation over eligible standard-rate trips; average speed as total miles / total hours.
-- Caveat: Standard metered rate only (flat and Flex fares excluded). Speed is meter distance over meter time, a proxy for congestion, not a traffic measurement.
SELECT hour_label, time_band,
       COUNT(*)                                                            AS std_rate_trips,
       ROUND(SUM(trip_distance) / (SUM(trip_duration_minutes) / 60.0), 1)  AS avg_speed_mph,
       ROUND(SUM(fare_amount) / SUM(trip_distance), 2)                     AS fare_per_mile,
       ROUND(SUM(fare_amount) / COUNT(*), 2)                               AS avg_fare
FROM v_trips
WHERE fare_per_mile_eligible AND duration_eligible
GROUP BY ALL
ORDER BY hour_label;
