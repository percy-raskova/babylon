"""Schema-parity test for view_runtime_trace_emission (T015, spec-064).

Asserts the migration's column list matches the 22 trace columns
declared in ``contracts/trace_csv_schema.yaml``. This is the II.11
schema-drift tripwire: when a subsystem table renames or drops a column
that the view selects, this test fails immediately.

Gated on Postgres availability — runs as part of integration CI, skipped
in fast-gate ``mise run check``.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

PG_DSN = os.environ.get("BABYLON_TEST_PG_DSN")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        PG_DSN is None,
        reason="BABYLON_TEST_PG_DSN env var not set",
    ),
]

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "064-headless-sim-runner"
    / "contracts"
    / "trace_csv_schema.yaml"
)


@pytest.fixture
def pg_pool():  # type: ignore[no-untyped-def]
    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(PG_DSN, min_size=1, max_size=2, open=True)
    yield pool
    pool.close()


@pytest.fixture
def view_applied(pg_pool):  # type: ignore[no-untyped-def]
    """Apply every numbered migration so the view is present.

    Self-healing (task #77): delegates to the shared
    ``conftest.apply_migrations_healing`` so a shared ``babylon_test`` DB left
    mid-migration by a killed background pytest run is healed loudly with one
    retry instead of erroring fixture setup — see conftest.py docstring.
    """
    from tests.integration.persistence.migration_healing import apply_migrations_healing

    apply_migrations_healing(pg_pool)


def test_view_columns_match_trace_csv_contract(pg_pool, view_applied) -> None:  # type: ignore[no-untyped-def]
    """View columns = session_id + (contract columns minus simulated_year).

    ``simulated_year`` is computed in Python (``start_year + tick/52.0``);
    it is the only contract column not exposed by the view. Everything
    else MUST line up exactly so an LLM consumer can rely on the column
    dictionary in manifest.json without ad-hoc reordering.
    """
    contract = yaml.safe_load(CONTRACT_PATH.read_text())
    contract_columns = [c["name"] for c in contract["columns"]]
    contract_minus_simyear = [c for c in contract_columns if c != "simulated_year"]
    with pg_pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM view_runtime_trace_emission WHERE session_id = %s LIMIT 0",
            (str(uuid4()),),
        )
        view_columns = [d.name for d in cur.description]
    expected = ["session_id", *contract_minus_simyear]
    assert view_columns == expected, f"Trace view drift: view={view_columns}, expected={expected}"
