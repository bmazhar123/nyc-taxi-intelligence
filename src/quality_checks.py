"""
Phase 5 -- Automated data-quality and reconciliation checks.

Every file in sql/checks/ is a query that returns the rows that BREAK a rule.
  * 0 rows  -> PASS
  * >0 rows -> FAIL (the returned rows show exactly what is wrong)

Each file declares a severity in its header:
  * error -- the warehouse cannot be trusted. The run exits with code 1 and
             the pipeline stops.
  * warn  -- something changed that a human should look at (e.g. a sudden
             shift in a quality flag). Reported, but does not stop the run.

Thresholds live in config.CHECK_PARAMS and are written into the SQL via
{placeholders}, so the same number appears in the check and in its report.

Outputs: reports/phase5_quality_report.md and .json

Usage:  python -m src.quality_checks
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from src import config
from src.run_sql import apply_views, md_table

MAX_FAILING_ROWS_SHOWN = 10


def default_params(raw_dir: Path = config.RAW_DIR, processed_dir: Path = config.PROCESSED_DIR) -> dict:
    p = {
        "raw_glob": (raw_dir / "yellow_tripdata_*.parquet").as_posix(),
        "excluded_parquet": (processed_dir / "trips_excluded.parquet").as_posix(),
        "max_duration_hours": config.MAX_DURATION_HOURS,
        "max_speed_mph": config.MAX_SPEED_MPH,
        "amount_floor": config.AMOUNT_REVIEW_FLOOR,
        "max_amount_per_mile": config.MAX_AMOUNT_PER_MILE,
    }
    p.update(config.CHECK_PARAMS)
    return p


def parse_check(sql: str) -> dict[str, str]:
    meta = {}
    for line in sql.splitlines():
        if not line.strip().startswith("--"):
            break
        body = line.strip().lstrip("-").strip()
        for key in ("Check", "Severity", "Why"):
            if body.startswith(key + ":"):
                meta[key.lower()] = body[len(key) + 1:].strip()
    if meta.get("severity") not in ("error", "warn"):
        raise ValueError(f"Check header must declare 'Severity: error' or 'Severity: warn' (got {meta.get('severity')!r})")
    return meta


def fill(text: str, params: dict) -> str:
    """Replace {name} placeholders. Plain replace (not str.format) so regex braces like \\d{4} are left alone."""
    for k, v in params.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def run_check(con, path: Path, params: dict) -> dict:
    raw_sql = path.read_text(encoding="utf-8")
    meta = parse_check(raw_sql)
    t0 = time.perf_counter()
    try:
        cur = con.execute(fill(raw_sql, params))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        status = "PASS" if not rows else "FAIL"
        error = None
    except duckdb.Error as e:          # a check that cannot run counts as a failure
        rows, cols, status, error = [], [], "FAIL", str(e)
    return {"name": path.stem, "check": fill(meta.get("check", ""), params), "severity": meta["severity"],
            "why": meta.get("why", ""), "status": status, "failing_rows": len(rows),
            "cols": cols, "rows": rows, "error": error, "seconds": time.perf_counter() - t0}


def to_markdown(results: list[dict]) -> str:
    n_err = sum(r["status"] == "FAIL" and r["severity"] == "error" for r in results)
    n_warn = sum(r["status"] == "FAIL" and r["severity"] == "warn" for r in results)
    L = ["# Phase 5 -- Data Quality & Reconciliation Report", "",
         f"Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         f"**{len(results)} checks — {len(results) - n_err - n_warn} passed, "
         f"{n_err} error(s), {n_warn} warning(s).**", "",
         "Each check is a query that returns the rows breaking a rule: no rows = pass. "
         "`error` checks stop the pipeline; `warn` checks flag changes for a human to review.", "",
         "| # | Check | Severity | Status | Failing rows |", "|---|---|---|---|---:|"]
    for i, r in enumerate(results, 1):
        icon = "✅ PASS" if r["status"] == "PASS" else ("❌ FAIL" if r["severity"] == "error" else "⚠️ WARN")
        L.append(f"| {i} | {r['check']} | {r['severity']} | {icon} | {r['failing_rows']:,} |")
    for r in results:
        if r["status"] == "PASS":
            continue
        L += ["", f"## {r['name']} ({r['severity']})", "", f"**Check:** {r['check']}  ", f"**Why it matters:** {r['why']}", ""]
        if r["error"]:
            L += [f"Check could not run: `{r['error']}`"]
        else:
            L += md_table(r["cols"], r["rows"][:MAX_FAILING_ROWS_SHOWN])
    L.append("")
    return "\n".join(L)


def run(warehouse_path: Path = config.WAREHOUSE_PATH, checks_dir: Path = config.CHECKS_DIR,
        views_dir: Path = config.SQL_DIR / "views", reports_dir: Path = config.REPORTS_DIR,
        params: dict | None = None, fail_on_error: bool = True) -> list[dict]:
    if not warehouse_path.exists():
        raise FileNotFoundError(f"{warehouse_path} not found. Build the warehouse first.")
    params = params or default_params()
    con = duckdb.connect(str(warehouse_path))
    try:
        apply_views(con, views_dir)   # checks test the views too, so make sure they are current
        results = [run_check(con, p, params) for p in sorted(checks_dir.glob("*.sql"))]
    finally:
        con.close()

    for r in results:
        mark = "PASS" if r["status"] == "PASS" else ("FAIL" if r["severity"] == "error" else "WARN")
        print(f"  [{mark}] {r['name']}" + (f"  ({r['failing_rows']} row(s))" if r["failing_rows"] else "")
              + (f"  ERROR: {r['error']}" if r["error"] else ""))

    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase5_quality_report.md").write_text(to_markdown(results), encoding="utf-8")
    (reports_dir / "phase5_quality_report.json").write_text(json.dumps(
        [{k: v for k, v in r.items() if k not in ("rows", "cols")} for r in results], indent=2, default=str))

    failed = [r["name"] for r in results if r["status"] == "FAIL" and r["severity"] == "error"]
    if failed and fail_on_error:
        raise AssertionError(f"{len(failed)} error-level check(s) failed: {failed}. "
                             f"See reports/phase5_quality_report.md")
    return results


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run data-quality and reconciliation checks.").parse_args(argv)
    try:
        results = run()
    except AssertionError as e:
        print(f"\n{e}")
        return 1
    warns = sum(r["status"] == "FAIL" for r in results)
    print(f"\nAll error-level checks passed ({warns} warning(s)). Report: reports/phase5_quality_report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
