# Phase 5 -- Data Quality & Reconciliation Report

Generated (UTC): 2026-11-08T22:27:39+00:00

**14 checks — 13 passed, 0 error(s), 1 warning(s).**

Each check is a query that returns the rows breaking a rule: no rows = pass. `error` checks stop the pipeline; `warn` checks flag changes for a human to review.

| # | Check | Severity | Status | Failing rows |
|---|---|---|---|---:|
| 1 | For every month, raw rows = warehouse rows + excluded rows. | error | ✅ PASS | 0 |
| 2 | For every month, raw total_amount = warehouse total_amount + excluded total_amount, to the cent. | error | ✅ PASS | 0 |
| 3 | Every analysis view adds back up to the fact table (row counts and, where stored exactly, amounts). | error | ✅ PASS | 0 |
| 4 | trip_id is unique in fact_trips. | error | ✅ PASS | 0 |
| 5 | Columns every metric depends on are never NULL. | error | ✅ PASS | 0 |
| 6 | Every foreign key in fact_trips exists in its dimension (no orphan keys). | error | ✅ PASS | 0 |
| 7 | No trip in the warehouse breaks any Phase 2 exclusion rule. | error | ✅ PASS | 0 |
| 8 | dim_date has every calendar day between its first and last date, with no gaps or duplicates. | error | ✅ PASS | 0 |
| 9 | Every date in the study period has at least one trip. | warn | ✅ PASS | 0 |
| 10 | No day falls below 0.6 x the median of the same weekday in the same month. | warn | ✅ PASS | 0 |
| 11 | No large tip-eligible vendor x rate-code segment records tips on fewer than 5.0% of trips. | warn | ✅ PASS | 0 |
| 12 | No quality flag's share of trips moves more than 5.0 percentage points from one month to the next. | warn | ⚠️ WARN | 2 |
| 13 | Cleaning removes no more than 5.0% of any month's raw rows. | warn | ✅ PASS | 0 |
| 14 | No more than 3.0% of a month's trips start or end in catch-all zones 264/265. | warn | ✅ PASS | 0 |

## 12_flag_rate_shifts (warn)

**Check:** No quality flag's share of trips moves more than 5.0 percentage points from one month to the next.  
**Why it matters:** A sudden shift (like Flex Fare in March 2024) changes how reliable some metrics are; it may be real, but it must be explained before month-to-month comparisons are trusted.

| flag | year_month | pct_of_trips | change_pp |
|---|---|---|---|
| flex_fare_incomplete | 2024-03 | 11.81 | 5.65 |
| passenger_unknown | 2024-03 | 12.97 | 5.64 |
