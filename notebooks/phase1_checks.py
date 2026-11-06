import duckdb

con = duckdb.connect()
con.execute("CREATE VIEW t AS SELECT * FROM 'data/raw/yellow_tripdata_2024-01.parquet'")

print("1) Rows where ALL five columns are null at once:")
print(con.sql("""
    SELECT COUNT(*) AS rows_all_five_null FROM t
    WHERE passenger_count IS NULL AND RatecodeID IS NULL AND store_and_fwd_flag IS NULL
      AND congestion_surcharge IS NULL AND Airport_fee IS NULL
"""))

print("2) Those null rows by vendor and payment type:")
print(con.sql("""
    SELECT VendorID, payment_type, COUNT(*) AS n FROM t
    WHERE passenger_count IS NULL GROUP BY ALL ORDER BY n DESC
"""))

print("3) Negative total_amount rows by payment type:")
print(con.sql("""
    SELECT payment_type, COUNT(*) AS n FROM t
    WHERE total_amount < 0 GROUP BY ALL ORDER BY n DESC
"""))

print("4) Pickups outside January:")
print(con.sql("""
    SELECT tpep_pickup_datetime, tpep_dropoff_datetime, trip_distance, total_amount FROM t
    WHERE tpep_pickup_datetime < '2024-01-01' OR tpep_pickup_datetime >= '2024-02-01'
    ORDER BY 1
"""))

print("5) Catch-all zones in the lookup:")
print(con.sql("SELECT * FROM 'data/raw/taxi_zone_lookup.csv' WHERE LocationID >= 264"))