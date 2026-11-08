"""
Data tests against the REAL warehouse (data/warehouse/taxi.duckdb).

Each error-level check in sql/checks/ becomes one pytest test, so
`pytest -q` validates the actual 20M-row data, not just the code.
If the warehouse has not been built (e.g. a fresh clone), these tests are
skipped rather than failed.
"""
import duckdb
import pytest

from src import config, quality_checks as qc
from src.run_sql import apply_views

ERROR_CHECKS = [p for p in sorted(config.CHECKS_DIR.glob("*.sql"))
                if qc.parse_check(p.read_text(encoding="utf-8"))["severity"] == "error"]

needs_data = pytest.mark.skipif(
    not (config.WAREHOUSE_PATH.exists() and (config.PROCESSED_DIR / "trips_excluded.parquet").exists()),
    reason="real warehouse not built; run `python -m src.pipeline --full` first",
)


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(config.WAREHOUSE_PATH))
    apply_views(c, config.SQL_DIR / "views")
    yield c
    c.close()


@needs_data
@pytest.mark.parametrize("path", ERROR_CHECKS, ids=lambda p: p.stem)
def test_real_warehouse(con, path):
    r = qc.run_check(con, path, qc.default_params())
    assert r["error"] is None, r["error"]
    assert r["status"] == "PASS", f"{r['check']} -- {r['failing_rows']} failing row(s): {r['rows'][:5]}"
