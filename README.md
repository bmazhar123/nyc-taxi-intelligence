# NYC Taxi Intelligence: Revenue, Demand & Operations Analytics

> **Status:** Phase 2 of 8 — ingestion, raw-data inspection, and logged cleaning. Findings, dashboard, and results will be added as they are actually produced.

A portfolio analytics project using official NYC TLC yellow-taxi trip records (January–June 2024) to analyse trip demand, recorded fare amounts, geographic patterns, and operational efficiency for a *hypothetical* operations team. This is a simulation and is not affiliated with the NYC Taxi & Limousine Commission.

**Stack:** Python · DuckDB · SQL · pytest · Power BI Desktop — free and fully local.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

pytest -q                      # unit tests (synthetic fixtures)
python -m src.download         # sample: January 2024 + zone lookup
python -m src.inspect_data     # writes reports/phase1_inspection.md
python -m src.clean            # writes data/processed/ + reports/phase2_cleaning_log.md
python -m src.download --full  # scale up to Jan–Jun 2024 when ready
```

## Data sources

- Trip records & zone lookup: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- Field definitions: [Yellow Taxi Data Dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf)
- Exact file URLs, sizes, and SHA-256 checksums: `data/raw/manifest.json` (generated on download)

## Project structure

```
src/          Python pipeline (config, download, inspection, cleaning)
sql/          Analytical SQL queries and views
tests/        pytest suite
notebooks/    Exploratory notebooks
reports/      Generated reports (inspection, cleaning log, findings)
dashboards/   Power BI file and build specification
images/       Screenshots and diagrams
docs/         Project plan, data dictionary
data/         raw/ processed/ warehouse/ (git-ignored except manifest)
```

See [`docs/project_plan.md`](docs/project_plan.md) for architecture, success criteria, and known data limitations.
