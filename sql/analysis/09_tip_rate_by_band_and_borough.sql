-- Question: Where and when do credit-card passengers tip the most?
-- Technique: Filtered aggregation (credit-card trips only), ratio of sums, plus the share of card trips with any tip.
-- Caveat: Cash tips are not recorded, so these rates describe card payers only and say nothing about cash tipping.
SELECT pu_borough, time_band,
       COUNT(*)                                                       AS card_trips,
       ROUND(100 * SUM(tip_amount) / SUM(fare_amount), 1)             AS tip_pct_of_fare,
       ROUND(100.0 * COUNT(*) FILTER (WHERE tip_amount > 0) / COUNT(*), 1) AS pct_trips_tipped,
       ROUND(median(tip_amount), 2)                                   AS median_tip
FROM v_trips
WHERE tip_rate_eligible AND NOT pu_is_catchall
GROUP BY ALL
HAVING COUNT(*) >= 1000          -- avoid rates computed on tiny samples
ORDER BY pu_borough, MIN(time_band_order);
