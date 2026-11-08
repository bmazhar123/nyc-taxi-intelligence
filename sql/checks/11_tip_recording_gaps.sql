-- Check: No large tip-eligible vendor x rate-code segment records tips on fewer than {min_pct_tipped}% of trips.
-- Severity: warn
-- Why: Phase 4 found rate code 99 records no tips at all. This check catches the NEXT gap like it automatically, instead of relying on someone spotting an odd chart.
SELECT vendor_name, ratecode_name,
       COUNT(*)                                                            AS tip_eligible_trips,
       ROUND(100.0 * COUNT(*) FILTER (WHERE tip_amount > 0) / COUNT(*), 1) AS pct_tipped
FROM v_trips
WHERE tip_rate_eligible
GROUP BY vendor_name, ratecode_name
HAVING COUNT(*) >= {min_segment_trips}
   AND 100.0 * COUNT(*) FILTER (WHERE tip_amount > 0) / COUNT(*) < {min_pct_tipped}
ORDER BY tip_eligible_trips DESC;
