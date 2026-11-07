-- Question: How did the mix of payment methods change month to month (including the Flex Fare shift)?
-- Technique: Grouped counts with share-of-month via SUM() OVER (PARTITION BY year_month).
-- Caveat: Flex Fare is an upfront app-quoted price (TLC pilot); the data shows WHEN its share changed, not WHY.
SELECT year_month, payment_type_name,
       COUNT(*)                                                                    AS trips,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY year_month), 2)   AS pct_of_month
FROM v_trips
GROUP BY year_month, payment_type_name
ORDER BY year_month, trips DESC;
