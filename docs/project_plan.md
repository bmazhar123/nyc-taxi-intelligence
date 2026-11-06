# Project Plan — NYC Taxi Intelligence

Portfolio simulation for a hypothetical NYC transportation operations team. Not affiliated with the NYC TLC.

## Architecture

```
NYC TLC (official)              Local laptop (free stack)
┌──────────────────┐   download   ┌────────────┐  inspect   ┌──────────────────────┐
│ Monthly Parquet  │ ───────────► │ data/raw/  │ ─────────► │ reports/phase1_*     │
│ Zone lookup CSV  │  + manifest  │ (immutable)│            │ (evidence for rules) │
└──────────────────┘              └─────┬──────┘            └──────────────────────┘
                                        │ clean (rule log: rows affected per rule)
                                        ▼
                                 ┌────────────────┐
                                 │ DuckDB         │  stg_trips → fact_trips
                                 │ warehouse.duckdb│  dim_zone, dim_date, dim_time,
                                 │                │  dim_payment, dim_ratecode, dim_vendor
                                 └───────┬────────┘  + SQL views (analysis layer)
                       ┌─────────────────┼──────────────────┐
                       ▼                 ▼                  ▼
                 sql/ analysis      pytest + SQL      Power BI Desktop
                 (12+ queries)      reconciliation    (4 pages, import mode
                                    checks            from exported views)
```

Why DuckDB: runs in-process (no server, no account), reads Parquet directly, handles tens of millions of rows on a laptop.

## Study period

- Sample run: **January 2024** (one month).
- Full run: **January–June 2024** (six consecutive months).
- Reason: fully published, and predates the `cbd_congestion_fee` column the TLC added for 2025 data, so the schema *should* be stable — Phase 1 verifies this rather than assuming it.

## Dataset inspection plan (Phase 1)

| Question | How we measure it |
|---|---|
| Do columns match the official dictionary? | Case-insensitive compare; report missing / unexpected / capitalisation differences |
| Do types change between months? | Compare DuckDB types per column per month |
| What dates does each file actually cover? | Min/max pickup; count of pickups outside the file's named month |
| How much data is missing? | Null count per column |
| Duplicates? | Exact duplicate rows (all columns identical) |
| Impossible trips? | Dropoff ≤ pickup; duration > 24h; zero/negative distance |
| Invalid money values? | Negative values per money column; zero total_amount |
| Undocumented codes? | VendorID, RatecodeID, payment_type, store_and_fwd_flag vs dictionary |
| Unknown zones? | PU/DO LocationID not in zone lookup |

Nothing is deleted in Phase 1. Cleaning rules in Phase 2 are chosen from these measurements.

## Known reporting limitations (from TLC documentation)

- `tip_amount` only captures **credit-card** tips; cash tips are not recorded. Tip rates are therefore only meaningful for credit-card trips.
- `total_amount` is the amount charged to passengers, excluding cash tips. It is **not** driver income, profit, or net revenue (it includes taxes, surcharges, tolls passed through).
- Records are submitted by technology providers; the TLC states it cannot guarantee their accuracy.
- Data is published with roughly a two-month lag and files may be revised; the manifest checksum detects revisions.
- Yellow taxis only — not green taxis or for-hire vehicles (Uber/Lyft), so this is not total NYC ride demand.
- Location is at taxi-zone level (≈260 zones), not exact coordinates.

## Success criteria

1. Anyone can rebuild everything from scratch with documented commands; source URLs and checksums recorded.
2. Every cleaning rule reports rows affected; raw row count = kept + removed, verified by an automated check.
3. Star schema in DuckDB with a written data dictionary.
4. ≥12 SQL queries (JOINs, CTEs, window functions, time comparisons) plus reusable views.
5. All tests pass; reconciliation checks pass (e.g., fact table totals equal cleaned staging totals).
6. 5–8 business questions answered with real numbers, uncertainty stated.
7. Four-page Power BI dashboard built by you (or a complete build spec if not yet built — never claimed otherwise).
8. README, executive summary, architecture diagram, screenshots, demo script, two truthful resume bullets.

## Phases

| Phase | Deliverable |
|---|---|
| 1 | Scaffold, reproducible download + manifest, raw inspection report, tests |
| 2 | Cleaning/ETL with rule log and row counts; schema harmonisation |
| 3 | DuckDB star schema + data dictionary + rebuild CLI |
| 4 | 12+ SQL analysis queries and views |
| 5 | Data-quality tests + SQL reconciliation checks |
| 6 | Business questions, findings, recommendations |
| 7 | Power BI model, DAX measures, page layouts, build instructions |
| 8 | README, executive summary, screenshots, demo script, resume bullets |
