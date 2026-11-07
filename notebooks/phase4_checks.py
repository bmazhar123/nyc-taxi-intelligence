import duckdb

con = duckdb.connect("data/warehouse/taxi.duckdb", read_only=True)

print("Outer-borough card trips: who are the non-tippers?")
print(con.sql("""
    SELECT pu_borough, time_band, vendor_name, ratecode_name, do_borough,
           COUNT(*)                                                         AS card_trips,
           ROUND(100 * SUM(tip_amount) / SUM(fare_amount), 1)               AS tip_pct,
           ROUND(100.0 * COUNT(*) FILTER (WHERE tip_amount > 0) / COUNT(*), 1) AS pct_tipped,
           ROUND(MEDIAN(trip_distance), 1)                                  AS median_miles
    FROM v_trips
    WHERE tip_rate_eligible AND pu_borough IN ('Bronx', 'Brooklyn')
    GROUP BY ALL
    HAVING COUNT(*) >= 500
    ORDER BY card_trips DESC
    LIMIT 20
"""))