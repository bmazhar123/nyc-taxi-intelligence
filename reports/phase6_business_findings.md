# NYC Taxi Intelligence — Business Findings

**Audience:** a hypothetical NYC transportation operations team planning driver supply and staffing. This is a portfolio simulation and is not affiliated with the NYC Taxi & Limousine Commission (TLC).

**Data:** official TLC yellow-taxi trip records, January–June 2024. That's 20,332,093 raw trips, of which 19,778,764 (97.3%) passed cleaning. Every removed row is logged by reason in `reports/phase2_cleaning_log.md`, and 14 automated checks reconcile rows and dollars from raw files to warehouse (`reports/phase5_quality_report.md`).

**Every number below comes from a query in `sql/analysis/`**, cited as (Q01), (Q02) and so on. `tests/test_findings.py` re-checks the key figures against the query results, so this document fails a test if the data changes and the text doesn't.

**Read these definitions first:**
- **"Recorded charges"** means `total_amount`: what passengers were charged, including taxes, tolls and surcharges. It is **not** revenue, profit or driver income.
- **Tip figures cover credit-card trips only.** Cash tips are not recorded.
- **Trips are served demand.** People who wanted a taxi and didn't get one leave no record.
- **This is yellow taxis only.** Uber, Lyft and green taxis are not included, so this is not total NYC ride demand.

---

## Summary

| # | Question | Short answer |
|---|---|---|
| 1 | When should supply peak? | Weekday evenings: 4–8 PM carries 27% of weekday trips, and 6 PM is the busiest hour six days a week. |
| 2 | Where is demand? | Highly concentrated: 15 of 260 zones produce half of all pickups. |
| 3 | How important are airports? | 9.6% of trips but 26.8% of recorded charges, and trips leave airports 3.5× as often as they arrive. |
| 4 | What does congestion cost? | Average speed falls from 21.0 mph at 5 AM to 9.3 mph at 5 PM. |
| 5 | Is demand growing? | Trips per day rose 25% from January to May, but six months can't separate growth from seasonality. |
| 6 | What changed in how people pay? | Flex Fare (upfront app pricing) more than doubled its share in March 2024, mostly at the expense of card payments. |
| 7 | Can tipping be compared across boroughs? | Only after excluding one segment that records no tips at all. It's 65% of Brooklyn's and 90% of the Bronx's card data. |

---

## 1. When should driver supply peak?

**Answer:** on weekday evenings, with a second, different peak late on weekend nights.

**Evidence**
- On an average weekday, the busiest hour is **6 PM with 8,249 trips**, versus **344 at 3 AM**. That's a 24-fold swing within one day (Q03).
- The four hours from **4 to 8 PM carry 27.2% of all weekday trips** (Q03).
- 6 PM is the single busiest hour **every day from Monday to Saturday**. On Sunday the busiest hour is **midnight** (Q04), which is Saturday night carrying over.
- At midnight, weekends average **6,011 trips versus 1,956 on weekdays**, about 3× as many (Q03).
- Total daily volume barely differs: **109,643 trips per weekday vs 106,252 per weekend day**, only 3.1% lower (Q02). Weekends aren't quieter; their demand is shaped differently.

**Recommendation**
- Plan the largest supply window for **roughly 3–8 PM on weekdays**, using overlapping shifts so coverage builds up before 4 PM instead of starting at it.
- Plan a separate **Friday and Saturday late-night window** that runs past midnight. A weekday schedule copied onto the weekend would be understaffed exactly when weekend demand peaks.

**Uncertainty and alternative explanations**
- These are *served* trips. If evening peaks are already capped by too few available cabs, true demand at 6 PM is higher than 8,249, and the case for more evening supply is stronger than this shows.
- These are averages across 26 weeks. Weather, events and holidays move individual days a lot (Q11).

---

## 2. Where is demand concentrated?

**Answer:** in a small part of Manhattan, plus the two airports.

**Evidence**
- **15 of the 260 zones** with pickups produce **50%** of all pickups, **31 zones produce 80%**, and **48 produce 95%** (Q06).
- **84.8% of all trips start and end in Manhattan** (Q07).
- The four busiest pickup zones are **Midtown Center (930,722 pickups), Upper East Side South, Upper East Side North, and JFK Airport** (Q05).

**Recommendation**
- Focus positioning and real-time rebalancing on the top ~15 zones, where half of all trips start.
- Treat the outer boroughs as a separate question. This data can't show whether demand there is low or simply served by other services.

**Uncertainty and alternative explanations**
- **Concentration partly reflects where yellow taxis operate, not only where people want rides.** Yellow cabs historically cruise Manhattan, while green taxis and app services serve much of the outer boroughs. That traffic isn't in this dataset.
- Zones vary greatly in size, so a large zone collects more pickups simply by covering more ground.
- Pickups count where trips *start*. An airport's high count partly reflects its taxi line.

---

## 3. How important are airport trips?

**Answer:** they're a small share of trips but a large share of recorded charges, and they're lopsided in direction.

**Evidence**
- Airport trips (to or from JFK, LaGuardia or Newark) are **9.6% of trips but 26.8% of recorded charges** (Q08).
- An average trip **from** an airport records **$76.59**, and one **to** an airport **$84.76**, versus **$22.82** for other trips (Q08).
- **1,483,211 trips left airports, but only 423,201 went to them: a 3.5 to 1 ratio** (Q08).
- Airport trips take **37–40 minutes** on average, versus **13.9** for other trips (Q08).

**Recommendation**
- Judge airport work **per vehicle-hour, not per trip.** A $77 trip that also needs a long taxi-line wait and an empty return drive may earn less per hour than several Manhattan trips.
- The data for that comparison (queue time, empty miles) isn't in the trip records, so **collecting it is the next step** before deciding how many vehicles to send to the airports.

**Uncertainty and alternative explanations**
- The 3.5:1 imbalance is plausibly because airports have dedicated taxi lines that guarantee pickups, while travelers heading *to* the airport use other options (app services, transit, private cars). **This data cannot confirm that**, since other services aren't included.
- Recorded charges include tolls and airport fees that pass through to third parties. That's another reason not to treat them as income.

---

## 4. What does congestion cost?

**Answer:** at the evening peak, trips move at less than half their early-morning speed.

**Evidence** (standard metered-rate trips only)
- Average speed is **21.0 mph at 5 AM** and falls to **9.3 mph at 5 PM** (Q10).
- Fare per mile rises from **$4.69 at 5 AM to $6.81 at 5 PM**, a 45% increase (Q10).
- Peak trips are also shorter: the average 5 PM trip covers about **2.4 miles**, versus **3.9 miles at 5 AM** (Q10, average fare divided by fare per mile).

**Recommendation**
- Plan peak capacity in **trips per vehicle-hour**, not vehicles alone. At peak speeds, each vehicle completes fewer miles per hour, so matching a 6 PM demand peak takes proportionally more vehicles than the trip count suggests.

**Uncertainty and alternative explanations**
- **The 45% rise in fare per mile is not all congestion.** Every trip pays a fixed starting charge, and on a shorter trip that charge is spread over fewer miles. Peak trips are shorter, so part of the rise is trip length, not traffic. The two effects aren't separated here.
- Speed is meter distance divided by meter time. It's a proxy for congestion, not a traffic measurement.

---

## 5. Is demand growing?

**Answer:** it rose through spring, but six months of data can't tell growth apart from seasonality.

**Evidence**
- Trips per day went from **93,365 in January to 116,731 in May (+25.0%)**, then eased to **114,417 in June** (Q01). Using trips per day avoids the effect of months having different lengths.
- Average fare rose from **$18.61 in January to $20.22 in May** (Q01).
- Federal holidays reduced demand compared with the same weekday in the same month (Q12):

| Holiday | Change vs a typical same weekday |
|---|---:|
| Memorial Day | −32.5% |
| Juneteenth | −20.8% |
| Presidents' Day | −14.7% |
| Martin Luther King Jr. Day | −7.5% |
| New Year's Day | −3.4% |

**Recommendation**
- Plan holiday supply as a **reduction from the normal weekday plan**, deepest for Memorial Day and Juneteenth.
- **Get January–June 2023 data before calling the rise "growth."** Comparing the same months year over year is the only way to separate a trend from the normal seasonal cycle.

**Uncertainty and alternative explanations**
- January is typically a slow month (winter weather, post-holiday travel), so a spring rise is expected even with no underlying growth.
- The higher average fare could reflect longer trips, more airport trips, or price changes. This analysis doesn't separate them.
- Each holiday's comparison rests on only **3 normal days**, so treat the percentages as indicative. New Year's Day's small drop may be because early January is low overall.

---

## 6. What changed in how passengers pay?

**Answer:** a sharp, lasting shift to Flex Fare in March 2024.

**Evidence**
- Flex Fare's share of trips was **4.77% in January, 6.16% in February, then 11.81% in March**, and stayed between **10.9% and 11.6%** through June (Q13).
- Over the same January-to-March change, **credit card fell from 80.10% to 74.54%** while **cash moved much less, from 14.61% to 13.13%** (Q13). This pattern suggests Flex Fare mainly replaced card payments, which fits since both run through apps.
- The TLC describes Flex Fare as an **upfront price quoted through a licensed e-hail app**; the meter doesn't set the fare ([TLC](https://www.nyc.gov/site/tlc/about/flex-fare-pilot-passengers.page)). It ran as a TLC pilot from **June 2018 to September 2024** ([TLC](https://nyc.gov:443/site/tlc/about/pilot-programs.page)).
- **Every Flex Fare trip is missing passenger count and rate code** (Phase 2). As a result, the share of trips with unknown passenger count rose from **5.85% to 12.97%** (Q16). The automated quality checks flag this shift (check 12).

**Recommendation**
- **Track app-booked share as its own monthly KPI.** A channel that doubled in one month changes how passengers find cabs.
- **Label coverage on any passenger-count or rate-code metric.** From March onward, those metrics describe only about 87% of trips.

**Uncertainty and alternative explanations**
- **The data shows when the shift happened, not why.** Possible causes include a new app partner, a marketing push, a pricing change, or a change in how vendors report these trips. Confirming the cause needs TLC or vendor information.
- Because the pilot ended in September 2024, these patterns may not continue after the study period.

---

## 7. Can tipping be compared across boroughs?

**Answer:** only after fixing a recording gap that would otherwise make the outer boroughs look like they barely tip.

**Evidence**
- **213,158 credit-card trips** from one vendor (Creative Mobile Technologies) with rate code 99 record **a tip on 0.0% of trips** (Q17). Real passengers don't produce exactly zero across 200,000 trips. **Tips are simply not recorded for this segment.**
- Citywide, that's only **1.41% of card trips** (Q17). But it's concentrated: **64.6% of Brooklyn's** card trips and **89.6% of the Bronx's**, versus **0.5% of Manhattan's** (Q18).
- Excluding the gap changes the outer-borough picture completely (Q18):

| Borough | Card trips with a tip: with gap → without | Tip as % of fare: with gap → without |
|---|---|---|
| Manhattan | 95.8% → **96.2%** | 23.4% → **23.6%** |
| Queens | 91.2% → **93.9%** | 20.2% → **20.6%** |
| Brooklyn | 30.7% → **86.8%** | 6.1% → **19.1%** |
| Bronx | 5.1% → **49.0%** | 1.3% → **11.9%** |

- **Brooklyn moves most of the way toward Manhattan** once the gap is removed, though it stays somewhat lower.
- **The Bronx stays well below the other boroughs even after the fix**, but that rests on only about 3,400 remaining card trips.

**Recommendation**
- **Exclude the gap from every tip metric.** This is now built into the metric definition (`tip_rate_eligible` in `sql/views/01_v_trips.sql`), and check 11 warns automatically if a new gap appears.
- **Don't use these trips for any driver-earnings analysis**, since their tips are missing.
- **Ask the vendor** whether tips on these trips are recorded somewhere else.
- **Don't report a Bronx tip rate as a finding yet.** With about 3,400 reliable card trips, it can't be broken down by time of day, and its lower rate needs checking for a second, smaller recording issue first.

**Uncertainty and alternative explanations**
- The data cannot say *why* tips are missing for this segment. It could be a contract or account program, a payment-flow difference, or how the vendor submits these records.
- **The Bronx's remaining gap has two possible explanations:** real differences in tipping, or another partial recording issue. Phase 4 found one vendor's standard-rate Bronx card trips recording a tip on only about 20% of trips (about 1,300 trips). The data can't tell these apart.
- **Tip figures describe card payers only.** Cash is 13–15% of trips and its tips are invisible, so these figures say nothing about how cash passengers tip.

---

## What this analysis cannot tell you

- **Unmet demand:** trips record rides that happened, not people who couldn't find a cab.
- **Driver earnings or company revenue:** recorded charges include taxes, tolls and surcharges, and don't cover costs, queue time or empty miles.
- **Total NYC ride demand:** app-based services and green taxis aren't included.
- **Causes:** this is observational data. It shows *when* and *where* things changed, not *why*.
- **Year-over-year trends:** six months can't separate growth from seasonality.
