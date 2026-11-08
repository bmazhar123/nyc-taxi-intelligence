-- Check: Every foreign key in fact_trips exists in its dimension (no orphan keys).
-- Severity: error
-- Why: An orphan key makes a trip vanish from any chart that uses that dimension, so totals disagree between pages.
SELECT * FROM (
    SELECT 'pickup_date_key -> dim_date' AS relationship, COUNT(*) AS orphan_rows
    FROM fact_trips f ANTI JOIN dim_date d ON f.pickup_date_key = d.date_key
    UNION ALL SELECT 'pickup_hour -> dim_time', COUNT(*)
    FROM fact_trips f ANTI JOIN dim_time t ON f.pickup_hour = t.hour
    UNION ALL SELECT 'pu_location_id -> dim_zone', COUNT(*)
    FROM fact_trips f ANTI JOIN dim_zone z ON f.pu_location_id = z.location_id
    UNION ALL SELECT 'do_location_id -> dim_zone', COUNT(*)
    FROM fact_trips f ANTI JOIN dim_zone z ON f.do_location_id = z.location_id
    UNION ALL SELECT 'vendor_key -> dim_vendor', COUNT(*)
    FROM fact_trips f ANTI JOIN dim_vendor v ON f.vendor_key = v.vendor_key
    UNION ALL SELECT 'ratecode_key -> dim_ratecode', COUNT(*)
    FROM fact_trips f ANTI JOIN dim_ratecode r ON f.ratecode_key = r.ratecode_key
    UNION ALL SELECT 'payment_type_key -> dim_payment_type', COUNT(*)
    FROM fact_trips f ANTI JOIN dim_payment_type p ON f.payment_type_key = p.payment_type_key
)
WHERE orphan_rows > 0;
