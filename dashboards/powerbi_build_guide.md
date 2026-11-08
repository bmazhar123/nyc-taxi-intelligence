# Power BI Build Guide — NYC Taxi Intelligence

This guide builds a four-page dashboard plus a zone drill-through page in **Power BI Desktop** (free, Windows). Follow the sections in order. Expect about 3–5 hours the first time.

> **Status:** this repository contains the data, model design, measures and layouts. A `.pbix` file exists only once you've built and saved it yourself.

**Pages**
1. Executive Overview
2. Revenue & Fares
3. Demand & Geography
4. Operational Insights
5. Zone Detail (hidden; opened by drill-through)

---

## 0. Before you start

1. Install **Power BI Desktop** from the Microsoft Store.
2. From the project folder, with the virtual environment active, generate the dashboard data:
   ```
   python -m src.zone_centroids     # one-time: downloads zone boundaries, makes map points
   python -m src.export_powerbi     # writes dashboards/data/*.parquet
   ```
3. Confirm `dashboards/data/` contains 7 `.parquet` files and `export_summary.json`.
4. Keep `reports/phase7_dashboard_validation.md` open. You'll check the finished dashboard against it.

**What you're loading**

| Table | Grain (one row per…) | Purpose |
|---|---|---|
| `agg_trips_hourly` | date × hour × pickup zone × payment type × airport direction | Main fact table; every page uses it |
| `agg_od_monthly` | month × pickup zone × drop-off zone | Top destinations on the Zone Detail page |
| `dim_date` | calendar day | Date slicers, weekday/weekend, holidays |
| `dim_time` | hour | Hour labels and time bands |
| `dim_zone` | taxi zone | Borough, zone name, airport flag, map points |
| `dim_dropoff_zone` | taxi zone | Drop-off side of origin → destination flows |
| `dim_payment_type` | payment code | Payment method names |

The fact table stores **sums and counts, not ratios** (for example tip dollars and fare dollars for tip-eligible trips). The DAX measures divide them at whatever level you're looking at, which is the only way a ratio stays correct when you filter or drill.

---

## 1. Load the data (Power Query)

### 1.1 Create a folder parameter
**Home → Transform data** opens Power Query. Then:

1. **Manage Parameters → New Parameter**
2. **Name:** `DataFolder`
3. **Type:** Text
4. **Current Value:** your full path, ending with a backslash. For example:
   `C:\Users\Bilal\Downloads\nyc-taxi-intelligence-phase1\nyc-taxi-intelligence\dashboards\data\`

Using a parameter means that if you ever move the project, you change one value instead of seven queries.

### 1.2 Add one query per table
For each table name in the list below:
1. **New Source → Blank Query**
2. **Advanced Editor**, then paste the code (changing the file name)
3. Rename the query to the table name

```m
let
    Source = Parquet.Document(File.Contents(DataFolder & "agg_trips_hourly.parquet"))
in
    Source
```

The seven names are: `agg_trips_hourly`, `agg_od_monthly`, `dim_date`, `dim_time`, `dim_zone`, `dim_dropoff_zone`, `dim_payment_type`.

### 1.3 Check the column types
Parquet keeps the types from the export, but confirm these before closing:

| Columns | Type |
|---|---|
| Key columns: `*_key`, `*_location_id`, `pickup_hour`, `hour` | Whole Number |
| Money columns: `*_amount_sum`, `taxes_surcharges_sum` | Fixed Decimal Number |
| `full_date`, `month_start` | Date |
| `latitude`, `longitude` | Decimal Number |

Then **Home → Close & Apply**.

> If `Parquet.Document` gives an error, see Troubleshooting (section 9) for the CSV route.

---

## 2. Build the model

### 2.1 Relationships
Go to **Model view**. Delete any relationships Power BI auto-detected, then create these. Every one is **many-to-one (\*:1)** with **single** cross-filter direction:

| From (many side) | To (one side) |
|---|---|
| `agg_trips_hourly[pickup_date_key]` | `dim_date[date_key]` |
| `agg_trips_hourly[pickup_hour]` | `dim_time[hour]` |
| `agg_trips_hourly[pu_location_id]` | `dim_zone[location_id]` |
| `agg_trips_hourly[payment_type_key]` | `dim_payment_type[payment_type_key]` |
| `agg_od_monthly[pu_location_id]` | `dim_zone[location_id]` |
| `agg_od_monthly[do_location_id]` | `dim_dropoff_zone[do_location_id]` |
| `agg_od_monthly[month_start]` | `dim_date[full_date]` |

**Why single direction?** Filters should flow from dimensions (the things you slice by) into facts (the numbers). Two-way filtering can create ambiguous paths and wrong totals.

**Known limitation:** `agg_od_monthly` is monthly. A date-range slicer includes a month's flows if the month's 1st day is inside the range. Say so in the visual's subtitle.

### 2.2 Mark the date table
Select `dim_date`, then **Table tools → Mark as date table → Date column: `full_date`**. This is required for the time-intelligence measures (month-over-month change, 7-day average).

### 2.3 Sort-by columns
These make days, months and bands appear in the right order instead of alphabetically.

| Column | Sort by column |
|---|---|
| `dim_date[day_name]` | `dim_date[day_of_week]` |
| `dim_date[month_name]` | `dim_date[month]` |
| `dim_time[hour_label]` | `dim_time[hour]` |
| `dim_time[time_band]` | `dim_time[time_band_order]` |

### 2.4 Tidy up
- **Hide** all key and ID columns (`*_key`, `*_location_id`, `pickup_hour`) and every raw sum column in the fact tables. Report builders should use measures, not raw columns.
- In `dim_zone`, set `latitude` → Data category **Latitude**, and `longitude` → **Longitude**.
- Set `dim_zone[borough]` → Data category **County**. This is optional.

### 2.5 A table for measures
**Home → Enter data**, name the table `_Measures`, and click **Load**. After you've added the measures below, delete its default column. Power BI then shows it at the top of the field list with a calculator icon.

---

## 3. DAX measures

Create each one with **New measure** on `_Measures`. Set the format shown in brackets with **Measure tools → Format**.

### Volume
```dax
Trips = SUM ( agg_trips_hourly[trips] )                                  -- [Whole number, thousands separator]

Days = COUNTROWS ( dim_date )                                            -- [Whole number]

Trips per Day = DIVIDE ( [Trips], [Days] )                               -- [Whole number]

Trips 7-day Avg =                                                        -- [Whole number]
AVERAGEX (
    DATESINPERIOD ( dim_date[full_date], MAX ( dim_date[full_date] ), -7, DAY ),
    [Trips]
)

Trips per Day PM =
CALCULATE ( [Trips per Day], DATEADD ( dim_date[full_date], -1, MONTH ) )

Trips per Day MoM % =                                                    -- [Percentage, 1 decimal]
DIVIDE ( [Trips per Day] - [Trips per Day PM], [Trips per Day PM] )
```
**Why `Days = COUNTROWS(dim_date)`?** "Per day" must divide by every calendar day in the selection, including days when a zone had no trips. Weekday and weekend selections then divide by the right number of days (130 vs 52), exactly like SQL query 02.

### Money (recorded charges, not revenue)
```dax
Recorded Charges = SUM ( agg_trips_hourly[total_amount_sum] )            -- [Currency, 0 decimals]

Avg Recorded Charge = DIVIDE ( [Recorded Charges], [Trips] )             -- [Currency, 2 decimals]

Avg Fare = DIVIDE ( SUM ( agg_trips_hourly[fare_amount_sum] ), [Trips] ) -- [Currency, 2 decimals]

Fare Charges = SUM ( agg_trips_hourly[fare_amount_sum] )                 -- [Currency, 0 decimals]
Tip Charges = SUM ( agg_trips_hourly[tip_amount_sum] )                   -- [Currency, 0 decimals]
Toll Charges = SUM ( agg_trips_hourly[tolls_amount_sum] )                -- [Currency, 0 decimals]
Taxes & Surcharges = SUM ( agg_trips_hourly[taxes_surcharges_sum] )      -- [Currency, 0 decimals]

Other Charges =                                                          -- [Currency, 0 decimals]
[Recorded Charges] - [Fare Charges] - [Tip Charges] - [Toll Charges] - [Taxes & Surcharges]

Fare per Mile =                                                          -- [Currency, 2 decimals]
DIVIDE (
    SUM ( agg_trips_hourly[fpm_fare_sum] ),
    SUM ( agg_trips_hourly[fpm_distance_sum] )
)
```
`Other Charges` is the part of `total_amount` that the itemized columns don't explain. Showing it, rather than hiding it, keeps the chart honest. `Fare per Mile` uses **standard-rate trips only**: flat JFK and negotiated fares, and Flex Fare, don't scale with distance.

### Tipping (credit card only, excluding the recording gap)
```dax
Tip % of Fare =                                                          -- [Percentage, 1 decimal]
DIVIDE (
    SUM ( agg_trips_hourly[tip_card_sum] ),
    SUM ( agg_trips_hourly[fare_card_sum] )
)

% Card Trips Tipped =                                                    -- [Percentage, 1 decimal]
DIVIDE (
    SUM ( agg_trips_hourly[card_trips_tipped] ),
    SUM ( agg_trips_hourly[card_trips_eligible] )
)

Card Trips (tip-eligible) = SUM ( agg_trips_hourly[card_trips_eligible] ) -- [Whole number]
```

### Trip characteristics
```dax
Avg Distance (mi) =                                                      -- [Decimal, 2]
DIVIDE ( SUM ( agg_trips_hourly[distance_sum] ), [Trips] )

Avg Duration (min) =                                                     -- [Decimal, 1]
DIVIDE (
    SUM ( agg_trips_hourly[duration_min_sum] ),
    SUM ( agg_trips_hourly[duration_trips] )
)

Avg Speed (mph) =                                                        -- [Decimal, 1]
DIVIDE (
    SUM ( agg_trips_hourly[fpm_distance_sum] ),
    SUM ( agg_trips_hourly[fpm_minutes_sum] ) / 60
)
```
`Avg Duration` excludes trips over 180 minutes (likely meters left running). The median duration by borough is in SQL query 15; Power BI can't compute a true median from pre-aggregated data.

### Shares and data quality
```dax
Share of Trips =                                                         -- [Percentage, 1 decimal]
DIVIDE ( [Trips], CALCULATE ( [Trips], REMOVEFILTERS ( agg_trips_hourly[airport_direction] ) ) )

Share of Charges =                                                       -- [Percentage, 1 decimal]
DIVIDE ( [Recorded Charges],
         CALCULATE ( [Recorded Charges], REMOVEFILTERS ( agg_trips_hourly[airport_direction] ) ) )

Airport Trip Share =                                                     -- [Percentage, 1 decimal]
DIVIDE (
    CALCULATE ( [Trips], agg_trips_hourly[airport_direction] <> "Non-airport" ),
    CALCULATE ( [Trips], REMOVEFILTERS ( agg_trips_hourly[airport_direction] ) )
)

Flex Fare Share =                                                        -- [Percentage, 1 decimal]
DIVIDE (
    CALCULATE ( [Trips], dim_payment_type[payment_type_key] = 0 ),
    CALCULATE ( [Trips], REMOVEFILTERS ( dim_payment_type ) )
)

Passenger Unknown % =                                                    -- [Percentage, 1 decimal]
DIVIDE ( SUM ( agg_trips_hourly[passenger_unknown_trips] ), [Trips] )

Long Duration % =                                                        -- [Percentage, 2 decimals]
DIVIDE ( SUM ( agg_trips_hourly[long_duration_trips] ), [Trips] )

Catch-all Zone % =                                                       -- [Percentage, 1 decimal]
DIVIDE ( SUM ( agg_trips_hourly[catchall_zone_trips] ), [Trips] )
```

### Origin → destination (Zone Detail page)
```dax
OD Trips = SUM ( agg_od_monthly[trips] )                                 -- [Whole number]

OD Share of Zone Trips =                                                 -- [Percentage, 1 decimal]
DIVIDE ( [OD Trips], CALCULATE ( [OD Trips], REMOVEFILTERS ( dim_dropoff_zone ) ) )
```

**`CALCULATE` and `REMOVEFILTERS` in one sentence:** `CALCULATE` re-computes a measure under changed filters. `REMOVEFILTERS(x)` clears the filter on `x`. So `Share of Trips` means "trips here ÷ trips across all airport directions, with every other filter (date, borough…) still applied."

---

## 4. Theme and canvas

1. **View → Themes → Browse for themes** and select `dashboards/nyc_taxi_theme.json`.
2. **Format page → Canvas settings:** Type **16:9**, which is 1280 × 720.
3. **View → Gridlines** and **Snap to grid** on.

**Header band (every page)**
- A **rectangle** at x 0, y 0, w 1280, h 64, fill `#1F3A5F`.
- A **text box** on top, in white:
  - Title, 20 pt Segoe UI Semibold, for example *"Executive Overview"*.
  - Subtitle, 10 pt: *"NYC yellow taxi · Jan–Jun 2024 · 19.8M trips · Recorded charges are amounts charged to passengers, not revenue"*.

**Slicer row (pages 1–4)**, at y 72, h 56, four slicers each about 305 wide:
1. `dim_date[full_date]`, style **Between**
2. `dim_date[day_type]`, style **Tile**
3. `dim_zone[borough]`, style **Dropdown**, multi-select. Add a visual-level filter `dim_zone[is_catchall] = False`.
4. `dim_payment_type[payment_type_name]`, style **Dropdown**

Then **View → Sync slicers** and sync all four across pages 1–4, so a selection follows you between pages.

Positions below are x, y, width, height on the 1280 × 720 canvas. Give every visual a clear title, and add **alt text** (Format → General → Alt text) describing what it shows.

---

## 5. Page layouts

### Page 1 — Executive Overview
*Purpose: the five-second view of volume, money and mix.*

| Visual | Fields | Position |
|---|---|---|
| 6 × **Card** | `Trips`, `Trips per Day`, `Recorded Charges`, `Avg Fare`, `Avg Duration (min)`, `Tip % of Fare` | y 140, h 100, w 200 each, x 10, 222, 434, 646, 858, 1070 |
| **Line chart**, "Daily trips and 7-day average" | X `dim_date[full_date]`; Y `Trips`, `Trips 7-day Avg` | 10, 252, 760, 220 |
| **Clustered bar**, "Trips by pickup borough" | Y `dim_zone[borough]`; X `Trips`; filter `is_catchall = False` | 782, 252, 488, 220 |
| **Clustered column**, "Trips per day by month" | X `dim_date[year_month]`; Y `Trips per Day`; tooltip `Trips per Day MoM %` | 10, 484, 500, 226 |
| **Clustered column**, "Airports: share of trips vs share of charges" | X `airport_direction`; Y `Share of Trips`, `Share of Charges` | 522, 484, 380, 226 |
| **Text box**, "Key findings" | 3 bullets copied from `reports/phase6_business_findings.md` (sections 1, 3, 6) | 914, 484, 356, 226 |

### Page 2 — Revenue & Fares
*Purpose: what passengers are charged, and why per-trip amounts differ.*

| Visual | Fields | Position |
|---|---|---|
| 4 × **Card** | `Recorded Charges`, `Avg Recorded Charge`, `Fare per Mile`, `Tip % of Fare` | y 140, h 100, w 305 each |
| **Stacked column**, "What passengers were charged, by month" | X `year_month`; Y `Fare Charges`, `Tip Charges`, `Toll Charges`, `Taxes & Surcharges`, `Other Charges` | 10, 252, 620, 226 |
| **Line chart**, "Fare per mile vs speed by hour (standard rate)" | X `dim_time[hour_label]`; Y `Fare per Mile`; secondary Y `Avg Speed (mph)` | 642, 252, 628, 226 |
| **Clustered bar**, "Average recorded charge by trip type" | Y `airport_direction`; X `Avg Recorded Charge` | 10, 490, 400, 220 |
| **Table**, "Card tipping by pickup borough" | `dim_zone[borough]`, `Tip % of Fare`, `% Card Trips Tipped`, `Card Trips (tip-eligible)`; filter `is_catchall = False` | 422, 490, 420, 220 |
| **100% stacked column**, "Payment mix by month" | X `year_month`; Y `Trips`; Legend `payment_type_name` | 854, 490, 416, 220 |

Under the tipping table, add a small text box: *"Credit-card trips only (cash tips are not recorded). Excludes 213K card trips whose tips are not recorded (rate code 99). Bronx figure rests on ~3,400 trips; see findings §7."*

### Page 3 — Demand & Geography
*Purpose: when and where trips happen.*

| Visual | Fields | Position |
|---|---|---|
| **Matrix**, "Average trips per hour, by weekday" | Rows `dim_date[day_name]`; Columns `dim_time[hour_label]`; Values `Trips per Day` | 10, 140, 760, 290 |
| **Azure Maps** (bubble layer), "Pickups by zone" | Latitude `dim_zone[latitude]`; Longitude `dim_zone[longitude]`; Size `Trips`; Tooltips `zone`, `borough`, `Avg Recorded Charge`; filter `is_catchall = False` | 782, 140, 488, 290 |
| **Clustered bar**, "Top 15 pickup zones" | Y `dim_zone[zone]`; X `Trips`; filter **Top N = 15 by Trips** | 10, 442, 440, 268 |
| **Line chart**, "Hourly demand: weekday vs weekend" | X `dim_time[hour_label]`; Y `Trips per Day`; Legend `dim_date[day_type]` | 462, 442, 440, 268 |
| **Text box**, "How concentrated is demand?" | *"15 of 260 zones produce 50% of pickups; 48 produce 95% (SQL query 06)."* plus the caveat about yellow-cab coverage | 914, 442, 356, 268 |

**Making the matrix a heatmap:** select `Trips per Day` in the Values well, then **Conditional formatting → Background color → Gradient** (lowest `#F1F5F9`, highest `#1F3A5F`). Also set **Font color**: white for high values. Turn off row and column subtotals.

**Why `Trips per Day` and not `Trips` in the heatmap?** Each cell then shows *average trips in that hour on that weekday*, which is what a staffing planner needs. It matches SQL query 04.

### Page 4 — Operational Insights
*Purpose: congestion, trip times, airports, and how reliable the data is.*

| Visual | Fields | Position |
|---|---|---|
| 4 × **Card** | `Avg Speed (mph)`, `Avg Duration (min)`, `Flex Fare Share`, `Passenger Unknown %` | y 140, h 100, w 305 each |
| **Line chart**, "Average speed by hour" | X `dim_time[hour_label]`; Y `Avg Speed (mph)`; Legend `day_type` | 10, 252, 620, 226 |
| **Clustered column**, "Average trip duration by time band and borough" | X `dim_time[time_band]`; Y `Avg Duration (min)`; Legend `dim_zone[borough]`; filter `is_catchall = False` and borough in Manhattan, Queens, Brooklyn, Bronx | 642, 252, 628, 226 |
| **Clustered column**, "Airport departures vs arrivals by month" | X `year_month`; Y `Trips`; Legend `airport_direction`; filter out *Non-airport* | 10, 490, 420, 220 |
| **Line chart**, "Flex Fare share and data coverage" | X `year_month`; Y `Flex Fare Share`, `Passenger Unknown %` | 442, 490, 420, 220 |
| **Text box**, "Data notes" | 4 bullets: served demand only; recorded charges ≠ revenue; tip-recording gap excluded; Flex Fare trips lack passenger count and rate code | 874, 490, 396, 220 |

---

## 6. Drill-through page — Zone Detail

1. Add a page called **Zone Detail**. Right-click its tab and choose **Hide page**.
2. In the **Visualizations → Drill through** well, add `dim_zone[zone]`. Power BI adds a back button automatically.
3. Build:

| Visual | Fields | Position |
|---|---|---|
| **Text box** title | Use a card with measure `Selected Zone = SELECTEDVALUE ( dim_zone[zone], "Multiple zones" )` | 0, 0, 1280, 64 (header band) |
| 4 × **Card** | `Trips`, `Trips per Day`, `Avg Recorded Charge`, `Tip % of Fare` | y 80, h 100 |
| **Line chart**, "Hourly profile" | X `hour_label`; Y `Trips per Day`; Legend `day_type` | 10, 192, 620, 250 |
| **Clustered bar**, "Top 10 destinations (monthly data)" | Y `dim_dropoff_zone[do_zone]`; X `OD Trips`; tooltip `OD Share of Zone Trips`; Top N = 10 | 642, 192, 628, 250 |
| **Clustered bar**, "Payment mix" | Y `payment_type_name`; X `Trips` | 10, 454, 620, 256 |
| **Card**, "Airport trip share" | `Airport Trip Share` | 642, 454, 300, 120 |

**Test it:** on page 3, right-click a zone in the Top 15 bar and choose **Drill through → Zone Detail**. Every visual should now show only that zone.

---

## 7. Validate before you trust it

Clear all slicers and compare against `reports/phase7_dashboard_validation.md`:

- [ ] `Trips`, `Recorded Charges`, `Avg Fare`, `Avg Duration`, `Fare per Mile`, `Avg Speed`, `Tip % of Fare`, `Trips per Day` cards match the KPI table
- [ ] "Trips per day by month" matches the month table
- [ ] Setting the day-type slicer to **Weekday**, then **Weekend**, makes `Trips per Day` match the day-type table
- [ ] Borough trips and tip % match the borough table
- [ ] The airport chart matches the airport-direction table
- [ ] Filtering hour to 17 (5 PM) makes `Avg Speed` and `Fare per Mile` match the 5 PM values

These numbers also tie back to the SQL results (for example May trips per day = 116,731 in query 01), so a match proves the dashboard, the export and the SQL all agree.

**If a number is off:**
- Totals too high → a relationship is many-to-many or bidirectional.
- `Trips per Day` wrong → the date table isn't marked, or the `day_type` slicer isn't synced.
- Tip % wrong → you used `tip_amount_sum` instead of `tip_card_sum`.

---

## 8. Save, capture, and commit

1. **Save** as `dashboards/nyc_taxi_intelligence.pbix`.
2. **Screenshots** of each page (Win + Shift + S): save as `images/dashboard_1_overview.png`, `_2_revenue.png`, `_3_demand.png`, `_4_operations.png`, `_5_zone_detail.png`. Phase 8 uses these in the README.
3. **PDF:** **File → Export → Export to PDF**, then save as `dashboards/nyc_taxi_intelligence.pdf`. Anyone can view it without Power BI.
4. **Check the .pbix size** before committing. GitHub rejects files over 100 MB and warns above 50 MB. If yours is over 50 MB, don't commit it. Commit the screenshots and PDF, and attach the `.pbix` to a GitHub **Release** instead.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `Parquet.Document` error | Run `python -m src.export_powerbi --csv`, then use `Csv.Document(File.Contents(DataFolder & "agg_trips_hourly.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv])`, add a **Use First Row as Headers** step, and set types as in 1.3 |
| No **Azure Maps** visual | **File → Options → Preview features / Security** and enable map visuals, or use the built-in **Map** visual with the same Latitude/Longitude/Size fields. Last resort: keep the Top 15 bar as the geographic view |
| Map points all blank | `dashboards/data/export_summary.json` shows `"zone_map_points": false`. Run `python -m src.zone_centroids`, then re-export |
| Data changed after a pipeline rebuild | **Home → Refresh**. Then re-check section 7 with the newly generated validation file |
| Slow visuals | Make sure visuals use measures, not raw columns, and that no relationship is bidirectional |
