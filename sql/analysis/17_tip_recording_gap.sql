-- Question: Are tips recorded consistently across vendors and rate codes for credit-card trips?
-- Technique: Grouped aggregation with conditional counts, used as a data-reliability check rather than a behaviour metric.
-- Caveat: A 0% tipped rate across thousands of trips means tips are not captured for that segment, not that passengers never tip. The data cannot say why. This is why tip_rate_eligible excludes rate code 99.
SELECT vendor_name, ratecode_name, pu_borough,
       COUNT(*)                                                            AS card_trips,
       ROUND(100.0 * COUNT(*) FILTER (WHERE tip_amount > 0) / COUNT(*), 1) AS pct_tipped,
       ROUND(100 * SUM(tip_amount) / NULLIF(SUM(fare_amount), 0), 1)       AS tip_pct_of_fare,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)                  AS pct_of_all_card_trips
FROM v_trips
WHERE is_credit_card AND fare_amount > 0
GROUP BY vendor_name, ratecode_name, pu_borough
HAVING COUNT(*) >= 1000
ORDER BY pct_tipped, card_trips DESC
LIMIT 20;
