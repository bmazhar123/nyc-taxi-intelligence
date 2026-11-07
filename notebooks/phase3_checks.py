import duckdb

con = duckdb.connect()
con.execute("CREATE VIEW k AS SELECT * FROM 'data/processed/trips_clean.parquet'")

print("1) How many kept trips are above each total_amount level?")
print(con.sql("""
    SELECT COUNT(*) FILTER (WHERE total_amount > 500)   AS over_500,
           COUNT(*) FILTER (WHERE total_amount > 1000)  AS over_1000,
           COUNT(*) FILTER (WHERE total_amount > 5000)  AS over_5000
    FROM k
"""))

print("2) The 15 most expensive kept trips:")
print(con.sql("""
    SELECT pickup_datetime, trip_distance, round(trip_duration_minutes, 1) AS minutes,
           ratecode_id, payment_type, fare_amount, tip_amount, total_amount,
           round(fare_amount / NULLIF(trip_distance, 0), 1) AS fare_per_mile
    FROM k ORDER BY total_amount DESC LIMIT 15
"""))

print("3) Flex Fare share by month:")
print(con.sql("""
    SELECT source_month,
           round(100.0 * COUNT(*) FILTER (WHERE payment_type = 0) / COUNT(*), 2) AS flex_fare_pct
    FROM k GROUP BY 1 ORDER BY 1
"""))