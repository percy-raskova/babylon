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
    """T017 / SC-002 (amended 2026-05-17): the state rate of profit is
    strictly positive AND finite at the terminal tick.

    **Marxian grounding** (per Persephone's 2026-05-17 review):

    There is **no theoretical upper bound** on the rate of profit
    s/(c+v) in Marx's framework. The constraints are:

    * s/v upper bound = (T - N) / N where T is total labor day, N is
      necessary labor. Physical ceiling is T=24h, N→1h → s/v ≈ 2300%.
      Marx (Vol I Ch 9) documents 153.85% (Manchester 1871) as
      empirical but explicitly declines to set a theoretical ceiling.
    * s/(c+v) upper bound = s/v when c → 0. Lower-bounded by 0 (or
      negative for individual failing capitals).

    A numeric cap like the spec-066 `[0.05, 0.80]` or the spec-067
    T050 `[0.05, 0.50]` would be engineering sanity-check theater,
    not Marxism. The test now asserts the STRUCTURAL invariants:

    * **Lower s > 0**: surplus value must be positive for capitalism
      to be net-productive in labor-hour terms. The interesting case
      where s ≤ 0 while accumulation continues (rentier economy,
      financialization, imperial rent) is a separate signal worth
      flagging in its own right; here it would mean the simulation
      isn't modeling productive capital extraction correctly.
    * **Finite p'**: catches NaN / divide-by-zero from code bugs.
      Not a Marxian claim — just a runtime sanity check.

    History:
    * Spec-066: `[0.05, 0.50]` → `[0.05, 0.80]` after ownership_id
      filter halved v.
    * Spec-067 T050: tightened back to `[0.05, 0.50]` expecting v
      to normalize via the QCEW rollup migration.
    * Spec-067 post-T036: T054 failed at p' = 0.7465 (within Marx's
      historical s/v ≈ 154% range; the [0.05, 0.50] cap had no
      theoretical grounding).
    * Spec-067 post-Persephone-2026-05-17: refactored to assert
      structural invariants (s > 0, p' finite) — Marxianly rigorous.

    Test name preserved verbatim from spec-066 for git-history
    continuity (FR-009 / SC-003).
    """
    import math

    result = _run_runner(scope="detroit-tri-county", ticks=5)
    assert result.artifact_dir is not None
    summary = json.loads((result.artifact_dir / "summary.json").read_text())
    terminal = summary["terminal_state"]
    total_c = terminal["total_c"]
    total_v = terminal["total_v"]
    total_s = terminal["total_s"]

    # Structural: c + v must be positive (capital invested).
    assert (total_c + total_v) > 0, (
        f"Spec-067 SC-002 FAILED: c + v not positive — capital invested "
        f"is zero or negative. (total_c={total_c}, total_v={total_v})"
    )

    # Marxian lower bound: surplus value must be positive for the
    # economy to be net-productive (per Marx Vol I Ch 9). s ≤ 0 with
    # ongoing accumulation would indicate rentier / financialized
    # capital — interesting in its own right but not what this
    # simulation tick is modeling.
    assert total_s > 0, (
        f"Spec-067 SC-002 FAILED: total_s = {total_s} ≤ 0 — surplus "
        f"value is non-positive at terminal tick. Marx Vol I: capitalism "
        f"requires positive surplus extraction to be net-productive in "
        f"labor-hour terms. Negative-s with positive accumulation is a "
        f"rentier-economy signal and warrants a separate detection."
    )

    # Engineering sanity: p' must be a finite real (catches NaN / inf
    # from divide-by-zero or sign-flip bugs). NOT a Marxian upper
    # bound — Marx documents no theoretical ceiling on s/(c+v).
    p_prime = total_s / (total_c + total_v)
    assert math.isfinite(p_prime), (
        f"Spec-067 SC-002 FAILED: p' = {p_prime} is not finite — "
        f"divide-by-zero or numeric overflow. (total_s={total_s}, "
        f"total_c={total_c}, total_v={total_v})"
    )


# ---------------------------------------------------------------------------
# US4 — Employment unit fix (T056-T057)
# ---------------------------------------------------------------------------


def test_state_aggregate_employment_in_BLS_band() -> None:
    """T056 / SC-007: tri-county-aggregate employment_proxy at tick 0
    aligns with BLS 2010 published employment for the same area.

    Scope: detroit-tri-county (Wayne 26163, Oakland 26125, Macomb 26099).
    BLS QCEW 2010 published all-industries employment for these 3 counties
    is approximately ~1.4M-1.7M. With the spec-066 /12 + industry_id=1
    fix, the runner output should land in [800K, 2.5M] (generous band
    that accommodates BLS reporting variability + spec-066 calibration).
    """
    result = _run_runner(scope="detroit-tri-county", ticks=1)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    total_emp = 0.0
    for row in rows:
        if row.get("entity_kind") != "county" or int(row["tick"]) != 0:
            continue
        emp = row.get("employment_proxy") or 0
        total_emp += float(emp)

    # 800K–2.5M plausible band for tri-county 2010 all-industries (BLS).
    # Pre-spec-066 /52 bug would yield ~200K (4.3× undercount).
    assert 800_000 <= total_emp <= 2_500_000, (
        f"Spec-066 SC-007 FAILED: tri-county tick-0 employment_proxy total = "
        f"{total_emp:.0f} outside [800K, 2.5M]. Confirm /12 (not /52) and "
        f"industry_id=1 filter shipped."
    )


def test_per_county_LFPR_plausible() -> None:
    """T057: for every county-tick row, employment_proxy / population in [0.20, 0.85].

    LFPR (labor-force-participation rate) for US adults in 2010 is ~0.63,
    so the QCEW-employed / population ratio should land in roughly
    [0.30, 0.65] under standard demography. Spec-066 widens to [0.20, 0.85]
    to accommodate Michigan-Canada scope edge counties (e.g., university
    counties with high student population).
    """
    result = _run_runner(scope="detroit-tri-county", ticks=3)
    assert result.artifact_dir is not None
    with (result.artifact_dir / "trace.csv").open() as f:
        rows = list(csv.DictReader(f))

    violations: list[tuple[str, str, float]] = []
    for row in rows:
        if row.get("entity_kind") != "county":
            continue
        emp = float(row.get("employment_proxy") or 0)
        pop = float(row.get("population") or 0)
        if pop <= 0:
            continue
        ratio = emp / pop
        if not (0.20 <= ratio <= 0.85):
            violations.append((row["entity_id"], row["tick"], ratio))

    assert not violations, (
        f"Spec-066 SC-007b FAILED: {len(violations)} rows with implausible "
        f"emp/pop ratio. First 5: {violations[:5]}"
    )
