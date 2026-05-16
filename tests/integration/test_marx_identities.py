"""Integration tests for the Marx accounting identities (spec-066 US1 + US4).

Spec: 066-marx-coherence-fixes (T015-T017, T056-T057).

These tests verify that the persisted county-tick rows produced by the
bridged runner satisfy Marx's value-added identity GDP = v + s, that the
implied state rate of profit lies in the relaxed [0.05, 0.50] band per
Clarifications Q1, and that the employment-proxy unit fix lands the
state-aggregate value in the BLS [3.5M, 4.8M] band.

Requires a live Postgres test DB (``BABYLON_TEST_PG_DSN``; falls back to
the canonical localhost:5433 test container) and the SQLite reference DB
at ``data/sqlite/marxist-data-3NF.sqlite``.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

PG_DSN_ENV = "BABYLON_TEST_PG_DSN"
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")
DEFAULT_DSN = "dbname=babylon_test host=localhost port=5433 user=test password=test"


def _postgres_reachable() -> bool:
    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    try:
        import psycopg

        conn = psycopg.connect(dsn, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _postgres_reachable(),
        reason="Postgres test DB not reachable",
    ),
    pytest.mark.skipif(
        not SQLITE_REF.exists(),
        reason=f"SQLite reference DB missing at {SQLITE_REF}.",
    ),
]


def _ensure_pg_dsn_env() -> None:
    os.environ.setdefault(PG_DSN_ENV, DEFAULT_DSN)


def _run_runner(
    *,
    scope: str = "detroit-tri-county",
    ticks: int = 5,
    seed: int = 2010,
    output_dir: Path | None = None,
) -> Any:
    _ensure_pg_dsn_env()

    from babylon.engine.headless_runner.models import SimulationRunConfig
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    sc = resolve_scope(scope)
    out_dir = output_dir or Path(tempfile.mkdtemp(prefix=f"sim_{scope}_"))
    config = SimulationRunConfig(
        ticks=ticks,
        start_year=2010,
        random_seed=seed,
        scope_name=scope,
        scope_fips=sc.scope_fips,
        external_node_ids=sc.external_node_ids,
        sqlite_reference_path=SQLITE_REF,
        output_dir=out_dir,
    )
    return runner_run(config)


# ---------------------------------------------------------------------------
# US1 — Surplus value strictly positive + value-added identity (T015-T017)
# ---------------------------------------------------------------------------


def test_total_s_strictly_positive_5tick_tri_county() -> None:
    """T015 / SC-001: total_s > 0 at the terminal tick of a 5-tick tri-county run."""
    result = _run_runner(scope="detroit-tri-county", ticks=5)
    assert result.artifact_dir is not None
    summary = json.loads((result.artifact_dir / "summary.json").read_text())
    total_s = summary["terminal_state"]["total_s"]
    assert total_s > 0, (
        f"Spec-066 SC-001 FAILED: total_s = {total_s} (expected > 0). "
        f"Check that hex_hydrator.py:373 uses s = max(0, GDP/52 - v), not - v - c."
    )


def test_value_added_identity_per_county_per_tick() -> None:
    """T016 / SC-004: |v + s - GDP/52| / (GDP/52) <= 0.05 for every county-tick row.

    Derives GDP/52 from c via the hex_hydrator invariant
    ``c = 0.5 * GDP/52``, so GDP/52 = 2*c.
    """
    result = _run_runner(scope="detroit-tri-county", ticks=5)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    violations: list[tuple[str, str, float]] = []
    for row in rows:
        if row.get("entity_kind") != "county":
            continue
        c = float(row["c"] or 0)
        v = float(row["v"] or 0)
        s = float(row["s"] or 0)
        gdp_implied = 2 * c
        if gdp_implied <= 0:
            continue
        rel_err = abs((v + s) - gdp_implied) / gdp_implied
        if rel_err > 0.05:
            violations.append((row["entity_id"], row["tick"], rel_err))

    assert not violations, (
        f"Spec-066 SC-004 FAILED: {len(violations)} rows violate v + s = GDP ± 5%. "
        f"First 5: {violations[:5]}"
    )


def test_state_rate_of_profit_in_relaxed_band() -> None:
    """T017 / SC-002: 0.05 <= total_s / (total_c + total_v) <= 0.50 at terminal tick.

    Relaxed from Vol III Ch 13's [0.20, 0.67] illustrative range to accommodate
    BEA-broad v (QCEW total compensation) per Clarifications Q1.
    """
    result = _run_runner(scope="detroit-tri-county", ticks=5)
    assert result.artifact_dir is not None
    summary = json.loads((result.artifact_dir / "summary.json").read_text())
    terminal = summary["terminal_state"]
    total_c = terminal["total_c"]
    total_v = terminal["total_v"]
    total_s = terminal["total_s"]
    assert (total_c + total_v) > 0, "expected positive c+v denominator"
    p_prime = total_s / (total_c + total_v)
    assert 0.05 <= p_prime <= 0.50, (
        f"Spec-066 SC-002 FAILED: state rate of profit p' = {p_prime:.4f} "
        f"outside [0.05, 0.50]. (total_s={total_s}, total_c={total_c}, total_v={total_v})"
    )


# ---------------------------------------------------------------------------
# US4 — Employment unit fix (T056-T057)
# ---------------------------------------------------------------------------


def test_state_aggregate_employment_in_BLS_band() -> None:
    """T056 / SC-007: sum of employment_proxy across 83 Michigan counties at tick 0
    falls in [3,500,000, 4,800,000] (BLS QCEW 2010 Michigan band)."""
    pytest.skip("WIP — implemented in spec-066 US4 phase (T058 fixes /52 -> /12)")


def test_per_county_LFPR_plausible() -> None:
    """T057: for every county-tick row, employment_proxy / population in [0.30, 0.65]."""
    pytest.skip("WIP — implemented in spec-066 US4 phase (T058 fixes /52 -> /12)")
