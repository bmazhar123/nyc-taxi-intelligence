-- Question: How do airport trips (JFK, LaGuardia, Newark) compare with all other trips?
-- Technique: CASE classification on joined zone attributes; ratio-of-sums metrics with FILTER.
-- Caveat: Airport trips include flat-rate JFK fares, so average fare differences partly reflect pricing rules, not only distance.
SELECT CASE WHEN pu_is_airport THEN 'From airport'
            WHEN do_is_airport THEN 'To airport'
            ELSE 'Non-airport' END                                                      AS trip_type,
       COUNT(*)                                                                         AS trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                               AS pct_of_trips,
       ROUND(100.0 * SUM(total_amount) / SUM(SUM(total_amount)) OVER (), 1)             AS pct_of_total_amount,
       ROUND(AVG(total_amount), 2)                                                      AS avg_total_amount,
       ROUND(AVG(trip_distance), 2)                                                     AS avg_distance_mi,
       ROUND(AVG(trip_duration_minutes) FILTER (WHERE duration_eligible), 1)            AS avg_duration_min,
       ROUND(100 * SUM(tip_amount) FILTER (WHERE tip_rate_eligible)
             / SUM(fare_amount) FILTER (WHERE tip_rate_eligible), 1)                    AS tip_pct_of_fare_card
FROM v_trips
GROUP BY 1
ORDER BY trips DESC;
