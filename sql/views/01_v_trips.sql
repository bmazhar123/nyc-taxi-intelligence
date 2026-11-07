-- =====================================================================
-- v_trips: every fact row joined to all dimensions, plus metric
-- eligibility flags. Every other view and analysis query builds on this,
-- so metric rules are defined ONCE here, not re-invented per query.
--
-- Eligibility rules (why each metric uses only some trips):
--   fare_per_mile_eligible: standard metered rate only (ratecode 1), distance > 0,
--       not a long-duration trip. Flat rates (JFK, negotiated) don't scale with
--       distance, and Flex Fare has no meter, so they would distort $/mile.
--   tip_rate_eligible: credit card only (the data dictionary says cash tips are
--       not recorded), fare > 0 so the ratio is defined, and NOT rate code 99.
--       Phase 4 found rate-code-99 card trips record a tip on 0.0% of trips across
--       tens of thousands of rows (query 17): tips are not captured for that
--       segment, so including it would understate tipping.
--   duration_eligible: excludes trips over the long-duration threshold
--       (likely meters left running).
-- =====================================================================
CREATE OR REPLACE VIEW v_trips AS
SELECT
    f.*,
    d.full_date              AS pickup_date,
    d.year_month,
    d.month                  AS month_num,
    d.month_name,
    d.day_of_week,
    d.day_name,
    d.is_weekend,
    d.is_us_federal_holiday,
    d.holiday_name,
    t.hour_label,
    t.time_band,
    t.time_band_order,
    pz.borough               AS pu_borough,
    pz.zone                  AS pu_zone,
    pz.is_airport            AS pu_is_airport,
    pz.is_catchall           AS pu_is_catchall,
    dz.borough               AS do_borough,
    dz.zone                  AS do_zone,
    dz.is_airport            AS do_is_airport,
    dz.is_catchall           AS do_is_catchall,
    p.payment_type_name,
    r.ratecode_name,
    r.is_flat_rate,
    v.vendor_name,
    (pz.is_airport OR dz.is_airport)                                        AS is_airport_trip,
    (f.ratecode_key = 1 AND f.trip_distance > 0 AND NOT f.flag_long_duration) AS fare_per_mile_eligible,
    (f.is_credit_card AND f.fare_amount > 0 AND f.ratecode_key <> 99)       AS tip_rate_eligible,
    (NOT f.flag_long_duration AND f.trip_duration_minutes > 0)              AS duration_eligible
FROM fact_trips f
JOIN dim_date         d  ON f.pickup_date_key  = d.date_key
JOIN dim_time         t  ON f.pickup_hour      = t.hour
JOIN dim_zone         pz ON f.pu_location_id   = pz.location_id
JOIN dim_zone         dz ON f.do_location_id   = dz.location_id
JOIN dim_payment_type p  ON f.payment_type_key = p.payment_type_key
JOIN dim_ratecode     r  ON f.ratecode_key     = r.ratecode_key
JOIN dim_vendor       v  ON f.vendor_key       = v.vendor_key;
