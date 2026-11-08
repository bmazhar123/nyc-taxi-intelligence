-- Question: How much of each borough's credit-card data falls in the tip-recording gap, and how do tipping figures change once it is excluded?
-- Technique: Conditional aggregation computing the same metric with and without a segment, side by side (a before/after comparison in one pass).
-- Caveat: The gap (rate code 99) is small citywide but concentrated in the outer boroughs; tip figures describe card payers only, since cash tips are not recorded.
SELECT pu_borough,
       COUNT(*)                                                                      AS card_trips,
       COUNT(*) FILTER (WHERE ratecode_key = 99)                                     AS gap_trips,
       ROUND(100.0 * COUNT(*) FILTER (WHERE ratecode_key = 99) / COUNT(*), 1)         AS pct_in_gap,
       ROUND(100.0 * COUNT(*) FILTER (WHERE tip_amount > 0) / COUNT(*), 1)            AS pct_tipped_incl_gap,
       ROUND(100.0 * COUNT(*) FILTER (WHERE tip_amount > 0 AND ratecode_key <> 99)
             / NULLIF(COUNT(*) FILTER (WHERE ratecode_key <> 99), 0), 1)              AS pct_tipped_excl_gap,
       ROUND(100 * SUM(tip_amount) / SUM(fare_amount), 1)                             AS tip_pct_of_fare_incl_gap,
       ROUND(100 * SUM(tip_amount) FILTER (WHERE ratecode_key <> 99)
             / NULLIF(SUM(fare_amount) FILTER (WHERE ratecode_key <> 99), 0), 1)      AS tip_pct_of_fare_excl_gap
FROM v_trips
WHERE is_credit_card AND fare_amount > 0 AND NOT pu_is_catchall
GROUP BY pu_borough
ORDER BY card_trips DESC;
