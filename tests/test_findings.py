"""
Fact-check reports/phase6_business_findings.md against the real query
results in reports/sql_results/*.csv.

Each CLAIM below is a number quoted in the findings document, together with
the CSV row and column it came from. If the data changes and the document
is not updated (or a number was mistyped), this test fails and names the
claim. Skipped when the real results have not been generated yet.
"""
import csv
import math

import pytest

from src import config

RESULTS = config.SQL_RESULTS_DIR
FINDINGS = config.REPORTS_DIR / "phase6_business_findings.md"

pytestmark = pytest.mark.skipif(
    not (RESULTS / "18_tip_gap_by_borough.csv").exists(),
    reason="real SQL results not generated; run `python -m src.run_sql` first",
)

# (query, row filter, column, value quoted in the findings, tolerance)
CLAIMS = [
    ("01_monthly_kpis_mom", {"year_month": "2024-01"}, "trips_per_day", 93365, 0.5),
    ("01_monthly_kpis_mom", {"year_month": "2024-05"}, "trips_per_day", 116731, 0.5),
    ("01_monthly_kpis_mom", {"year_month": "2024-06"}, "trips_per_day", 114417, 0.5),
    ("01_monthly_kpis_mom", {"year_month": "2024-01"}, "avg_fare", 18.61, 0.005),
    ("01_monthly_kpis_mom", {"year_month": "2024-05"}, "avg_fare", 20.22, 0.005),
    ("02_weekday_vs_weekend", {"day_type": "Weekday"}, "avg_trips_per_day", 109643, 0.5),
    ("02_weekday_vs_weekend", {"day_type": "Weekend"}, "avg_trips_per_day", 106252, 0.5),
    ("03_hourly_demand_profile", {"day_type": "Weekday", "hour_label": "18:00"}, "avg_trips", 8249, 0.5),
    ("03_hourly_demand_profile", {"day_type": "Weekday", "hour_label": "03:00"}, "avg_trips", 344, 0.5),
    ("03_hourly_demand_profile", {"day_type": "Weekday", "hour_label": "00:00"}, "avg_trips", 1956, 0.5),
    ("03_hourly_demand_profile", {"day_type": "Weekend", "hour_label": "00:00"}, "avg_trips", 6011, 0.5),
    ("05_top_pickup_zones_pareto", {"zone": "Midtown Center"}, "pickups", 930722, 0.5),
    ("06_zone_concentration", {}, "zones_with_pickups", 260, 0),
    ("06_zone_concentration", {}, "zones_for_50pct", 15, 0),
    ("06_zone_concentration", {}, "zones_for_80pct", 31, 0),
    ("06_zone_concentration", {}, "zones_for_95pct", 48, 0),
    ("07_borough_flows", {"pu_borough": "Manhattan", "do_borough": "Manhattan"}, "pct_of_all_trips", 84.76, 0.005),
    ("08_airport_vs_other", {"trip_type": "From airport"}, "trips", 1483211, 0),
    ("08_airport_vs_other", {"trip_type": "To airport"}, "trips", 423201, 0),
    ("08_airport_vs_other", {"trip_type": "From airport"}, "avg_total_amount", 76.59, 0.005),
    ("08_airport_vs_other", {"trip_type": "To airport"}, "avg_total_amount", 84.76, 0.005),
    ("08_airport_vs_other", {"trip_type": "Non-airport"}, "avg_total_amount", 22.82, 0.005),
    ("08_airport_vs_other", {"trip_type": "Non-airport"}, "avg_duration_min", 13.9, 0.05),
    ("10_speed_and_fare_per_mile_by_hour", {"hour_label": "05:00"}, "avg_speed_mph", 21.0, 0.05),
    ("10_speed_and_fare_per_mile_by_hour", {"hour_label": "17:00"}, "avg_speed_mph", 9.3, 0.05),
    ("10_speed_and_fare_per_mile_by_hour", {"hour_label": "05:00"}, "fare_per_mile", 4.69, 0.005),
    ("10_speed_and_fare_per_mile_by_hour", {"hour_label": "17:00"}, "fare_per_mile", 6.81, 0.005),
    ("12_holidays_vs_typical_day", {"holiday_name": "Memorial Day"}, "pct_vs_typical", -32.5, 0.05),
    ("12_holidays_vs_typical_day", {"holiday_name": "Juneteenth"}, "pct_vs_typical", -20.8, 0.05),
    ("12_holidays_vs_typical_day", {"holiday_name": "Presidents' Day"}, "pct_vs_typical", -14.7, 0.05),
    ("12_holidays_vs_typical_day", {"holiday_name": "Martin Luther King Jr. Day"}, "pct_vs_typical", -7.5, 0.05),
    ("12_holidays_vs_typical_day", {"holiday_name": "New Year's Day"}, "pct_vs_typical", -3.4, 0.05),
    ("13_payment_mix_by_month", {"year_month": "2024-01", "payment_type_name": "Flex Fare trip"}, "pct_of_month", 4.77, 0.005),
    ("13_payment_mix_by_month", {"year_month": "2024-02", "payment_type_name": "Flex Fare trip"}, "pct_of_month", 6.16, 0.005),
    ("13_payment_mix_by_month", {"year_month": "2024-03", "payment_type_name": "Flex Fare trip"}, "pct_of_month", 11.81, 0.005),
    ("13_payment_mix_by_month", {"year_month": "2024-01", "payment_type_name": "Credit card"}, "pct_of_month", 80.10, 0.005),
    ("13_payment_mix_by_month", {"year_month": "2024-03", "payment_type_name": "Credit card"}, "pct_of_month", 74.54, 0.005),
    ("13_payment_mix_by_month", {"year_month": "2024-01", "payment_type_name": "Cash"}, "pct_of_month", 14.61, 0.005),
    ("13_payment_mix_by_month", {"year_month": "2024-03", "payment_type_name": "Cash"}, "pct_of_month", 13.13, 0.005),
    ("16_data_quality_by_month", {"year_month": "2024-01"}, "pct_passenger_unknown", 5.85, 0.005),
    ("16_data_quality_by_month", {"year_month": "2024-03"}, "pct_passenger_unknown", 12.97, 0.005),
]


def load(name):
    with (RESULTS / f"{name}.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find(name, match):
    rows = [r for r in load(name) if all(r[k] == v for k, v in match.items())]
    assert len(rows) == 1, f"{name} {match}: expected 1 row, found {len(rows)}"
    return rows[0]


@pytest.mark.parametrize("name,match,col,expected,tol", CLAIMS,
                         ids=[f"{c[0][:2]}-{c[2]}-{'-'.join(c[1].values())}" for c in CLAIMS])
def test_quoted_number_matches_results(name, match, col, expected, tol):
    actual = float(find(name, match)[col])
    assert math.isclose(actual, expected, abs_tol=tol), f"findings say {expected}, {name}.csv says {actual}"


def test_derived_figures():
    # 4-8 PM share of weekday trips: "27.2%"
    pm = sum(float(r["pct_of_day"]) for r in load("03_hourly_demand_profile")
             if r["day_type"] == "Weekday" and r["hour_label"] in ("16:00", "17:00", "18:00", "19:00"))
    assert math.isclose(pm, 27.2, abs_tol=0.05)

    # airports: "9.6% of trips but 26.8% of recorded charges", "3.5 to 1"
    air = [r for r in load("08_airport_vs_other") if r["trip_type"] != "Non-airport"]
    assert math.isclose(sum(float(r["pct_of_trips"]) for r in air), 9.6, abs_tol=0.05)
    assert math.isclose(sum(float(r["pct_of_total_amount"]) for r in air), 26.8, abs_tol=0.05)
    assert round(1483211 / 423201, 1) == 3.5

    # "+25.0%" trips per day, January to May
    assert round(100 * (116731 / 93365 - 1), 1) == 25.0

    # peak trips shorter: avg distance = avg fare / fare per mile -> "2.4" vs "3.9" miles
    q10 = {r["hour_label"]: r for r in load("10_speed_and_fare_per_mile_by_hour")}
    dist = lambda h: float(q10[h]["avg_fare"]) / float(q10[h]["fare_per_mile"])
    assert round(dist("17:00"), 1) == 2.4 and round(dist("05:00"), 1) == 3.9


def test_peak_hour_claims():
    top = {r["day_name"]: r["hour_label"] for r in load("04_peak_hours_by_weekday") if r["rank_in_day"] == "1"}
    assert all(top[d] == "18:00" for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"))
    assert top["Sunday"] == "00:00"


def test_tip_gap_claims():
    gap = [r for r in load("17_tip_recording_gap")
           if r["vendor_name"].startswith("Creative Mobile") and r["ratecode_name"] == "Null/unknown"]
    assert sum(int(r["card_trips"]) for r in gap) == 213158
    assert all(float(r["pct_tipped"]) == 0.0 for r in gap)
    assert math.isclose(sum(float(r["pct_of_all_card_trips"]) for r in gap), 1.41, abs_tol=0.02)

    q18 = {r["pu_borough"]: r for r in load("18_tip_gap_by_borough")}
    quoted = {  # borough: (pct_in_gap, tipped incl, tipped excl, % of fare incl, % of fare excl)
        "Manhattan": (0.5, 95.8, 96.2, 23.4, 23.6),
        "Queens":    (2.9, 91.2, 93.9, 20.2, 20.6),
        "Brooklyn":  (64.6, 30.7, 86.8, 6.1, 19.1),
        "Bronx":     (89.6, 5.1, 49.0, 1.3, 11.9),
    }
    cols = ("pct_in_gap", "pct_tipped_incl_gap", "pct_tipped_excl_gap",
            "tip_pct_of_fare_incl_gap", "tip_pct_of_fare_excl_gap")
    for borough, values in quoted.items():
        for col, v in zip(cols, values):
            assert math.isclose(float(q18[borough][col]), v, abs_tol=0.05), f"{borough} {col}"
    remaining_bronx = int(q18["Bronx"]["card_trips"]) - int(q18["Bronx"]["gap_trips"])
    assert round(remaining_bronx, -2) == 3400                       # "about 3,400 remaining card trips"


def test_findings_document_exists_and_cites_queries():
    text = FINDINGS.read_text(encoding="utf-8")
    for q in ("Q01", "Q03", "Q06", "Q08", "Q10", "Q12", "Q13", "Q17", "Q18"):
        assert f"({q}" in text or f"{q})" in text, q
