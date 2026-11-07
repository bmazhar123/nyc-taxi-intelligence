"""
Phase 4 -- Apply the SQL views and run every analysis query.

  1. Creates (or replaces) every view in sql/views/ inside the warehouse,
     in file-name order (later views build on earlier ones).
  2. Runs every query in sql/analysis/ and saves each result to
     reports/sql_results/<query_name>.csv
  3. Writes reports/phase4_sql_results.md: for each query, the business
     question, technique, caveat (read from the query's header comments),
     run time, and the result table.

The SQL files are the source of truth -- this script only runs them, so
every query can also be opened and run by hand in any DuckDB client.

Usage:  python -m src.run_sql
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import duckdb

from src import config

HEADER_KEYS = ("Question", "Technique", "Caveat")
MAX_MD_ROWS = 25


def parse_header(sql: str) -> dict[str, str]:
    """Read '-- Question: ...' style comment lines at the top of a query file."""
    meta = {}
    for line in sql.splitlines():
        line = line.strip()
        if not line.startswith("--"):
            break
        body = line.lstrip("-").strip()
        for key in HEADER_KEYS:
            if body.startswith(key + ":"):
                meta[key] = body[len(key) + 1:].strip()
    return meta


def apply_views(con, views_dir: Path) -> list[str]:
    applied = []
    for path in sorted(views_dir.glob("*.sql")):
        try:
            con.execute(path.read_text(encoding="utf-8"))
        except duckdb.Error as e:
            raise RuntimeError(f"View {path.name} failed: {e}") from e
        applied.append(path.stem)
    return applied


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:,.2f}" if abs(v) < 1e15 else str(v)
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}"
    return str(v)


def md_table(cols: list[str], rows: list[tuple]) -> list[str]:
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows[:MAX_MD_ROWS]]
    if len(rows) > MAX_MD_ROWS:
        out.append(f"\n_{len(rows) - MAX_MD_ROWS} more rows in the CSV._")
    return out


def run_queries(con, analysis_dir: Path, out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for path in sorted(analysis_dir.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        t0 = time.perf_counter()
        try:
            cur = con.execute(sql)
            rows = cur.fetchall()
        except duckdb.Error as e:
            raise RuntimeError(f"Query {path.name} failed: {e}") from e
        cols = [d[0] for d in cur.description]
        secs = time.perf_counter() - t0
        with (out_dir / f"{path.stem}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
        results.append({"name": path.stem, "meta": parse_header(sql), "cols": cols,
                        "rows": rows, "seconds": secs})
        print(f"  {path.stem}: {len(rows)} row(s) in {secs:.1f}s")
    return results


def to_markdown(views: list[str], results: list[dict]) -> str:
    L = ["# Phase 4 -- SQL Analysis Results", "",
         f"Views applied: {', '.join(f'`{v}`' for v in views)}", "",
         f"{len(results)} queries. Full results are in `reports/sql_results/*.csv`; "
         f"query source is in `sql/analysis/`.", ""]
    for r in results:
        m = r["meta"]
        L += [f"## {r['name']}", "",
              f"**Question:** {m.get('Question', '')}  ",
              f"**Technique:** {m.get('Technique', '')}  ",
              f"**Caveat:** {m.get('Caveat', '')}  ",
              f"_Ran in {r['seconds']:.1f}s, {len(r['rows'])} row(s)._", ""]
        L += md_table(r["cols"], r["rows"]) + [""]
    return "\n".join(L)


def run(warehouse_path: Path = config.WAREHOUSE_PATH, sql_dir: Path = config.SQL_DIR,
        results_dir: Path = config.SQL_RESULTS_DIR, reports_dir: Path = config.REPORTS_DIR) -> list[dict]:
    if not warehouse_path.exists():
        raise FileNotFoundError(f"{warehouse_path} not found. Run src.build_warehouse first.")
    con = duckdb.connect(str(warehouse_path))
    try:
        views = apply_views(con, sql_dir / "views")
        print(f"  applied {len(views)} view(s)")
        results = run_queries(con, sql_dir / "analysis", results_dir)
    finally:
        con.close()
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "phase4_sql_results.md").write_text(to_markdown(views, results), encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Apply SQL views and run analysis queries.").parse_args(argv)
    run()
    print(f"Results in {config.SQL_RESULTS_DIR} and reports/phase4_sql_results.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
