"""
One command to rebuild everything, in order:

    download -> inspect -> clean -> build warehouse -> SQL analysis -> quality checks

Examples (from the project root):
  python -m src.pipeline --full                 # Jan-Jun 2024, end to end
  python -m src.pipeline --skip-download        # rebuild from files already in data/raw
  python -m src.pipeline --months 2024-01 2024-02

Each step stops the run if its own checks fail, so a broken step can never
feed bad data into the next one.
"""
from __future__ import annotations

import argparse
import sys
import time

from src import build_warehouse, clean, config, download, inspect_data, quality_checks, run_sql


def step(name: str, fn) -> None:
    print(f"\n=== {name} ===")
    t0 = time.perf_counter()
    fn()
    print(f"    done in {time.perf_counter() - t0:.1f}s")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rebuild the NYC Taxi Intelligence pipeline end to end.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--full", action="store_true", help=f"use all months: {', '.join(config.MONTHS_FULL)}")
    g.add_argument("--months", nargs="+", help="explicit months, e.g. 2024-01 2024-02")
    p.add_argument("--skip-download", action="store_true", help="use files already in data/raw")
    a = p.parse_args(argv)

    if not a.skip_download:
        months = a.months or (config.MONTHS_FULL if a.full else config.MONTHS_SAMPLE)
        step("1/6 download", lambda: download.run(months))
    step("2/6 inspect raw files", lambda: inspect_data.main([]))
    step("3/6 clean", lambda: clean.run(config.RAW_DIR, config.PROCESSED_DIR, config.REPORTS_DIR))
    step("4/6 build warehouse", lambda: build_warehouse.run())
    step("5/6 SQL views + analysis", lambda: run_sql.run())
    step("6/6 data-quality checks", lambda: quality_checks.run())   # stops here if an error-level check fails
    print("\nPipeline complete. See reports/ for the inspection, cleaning, warehouse, SQL and quality reports.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
