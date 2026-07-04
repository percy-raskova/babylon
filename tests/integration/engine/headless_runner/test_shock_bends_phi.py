"""Spec-102 SLICE B: a scheduled shock visibly bends a bloc's Φ trajectory.

Drives the real headless runner with a shock scheduled at tick 3 that
multiplies ``china``'s ``phi_year_inflow`` by 2.5x, and asserts — via the
per-tick ``boundary_flow_register`` DRAIN_EDGE sums (the same observable
spec-101's ``test_trade_circuit.py`` uses for its conservation-identity
check) — that:

- ticks BEFORE the scheduled tick show the bloc's unshocked (base) weekly
  drain;
- ticks AT/AFTER the scheduled tick show the drain scaled by the
  configured multiplier (level-set semantics — the shock persists);
- an unrelated bloc's drain is unaffected at every tick (the shock is
  scoped to its one declared bloc).

Gated like ``test_trade_circuit.py``: requires the local Postgres test DB
and the canonical SQLite reference DB.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_SQLITE = Path("data/sqlite/marxist-data-3NF.sqlite")
_DSN = "dbname=babylon_test host=localhost port=5433 user=test password=test"

pytestmark = [pytest.mark.integration, pytest.mark.ledger, pytest.mark.slow]

if not _SQLITE.exists():  # pragma: no cover - environment guard
    pytest.skip("live reference DB absent", allow_module_level=True)


def _pg_reachable() -> bool:
    try:
        import psycopg

        psycopg.connect(_DSN, connect_timeout=3).close()
    except Exception:
        return False
    return True


if not _pg_reachable():  # pragma: no cover - environment guard
    pytest.skip("local Postgres test DB unavailable", allow_module_level=True)


_TICKS = 6
_SHOCK_TICK = 3
_SHOCKED_BLOC = "china"
_MULTIPLIER = 2.5
_RELATIVE_TOLERANCE = 1e-6


@pytest.fixture(scope="module")
def shock_run():  # type: ignore[no-untyped-def]
    """Run the tri-county headless sim once with a scheduled china shock.

    Returns:
        ``(session_id, drain_by_bloc_tick)`` where ``drain_by_bloc_tick``
        is ``{(bloc, tick): summed_magnitude}``.
    """
    import psycopg

    from babylon.engine.headless_runner.models import (
        ExitReason,
        ScheduledBlocShock,
        SimulationRunConfig,
    )
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    os.environ.setdefault("BABYLON_TEST_PG_DSN", _DSN)
    sc = resolve_scope("detroit-tri-county")
    out = Path(tempfile.mkdtemp(prefix="sim_shock_bends_phi_"))
    config = SimulationRunConfig(
        ticks=_TICKS,
        start_year=2010,
        random_seed=2010,
        scope_name="detroit-tri-county",
        scope_fips=sc.scope_fips,
        external_node_ids=sc.external_node_ids,
        sqlite_reference_path=_SQLITE,
        output_dir=out,
        strict=False,
        shock_schedule=(
            ScheduledBlocShock(tick=_SHOCK_TICK, bloc=_SHOCKED_BLOC, phi_multiplier=_MULTIPLIER),
        ),
    )
    result = runner_run(config)
    assert result.exit_reason == ExitReason.COMPLETED, result.exit_reason
    sid = str(result.session_id)

    with psycopg.connect(_DSN) as conn:
        rows = conn.execute(
            "SELECT source_node_id, tick, SUM(magnitude) "
            "FROM boundary_flow_register "
            "WHERE session_id = %s AND flow_type = 'drain_edge' "
            "GROUP BY source_node_id, tick",
            (sid,),
        ).fetchall()
    drain_by_bloc_tick = {(str(node), int(tick)): float(mag) for node, tick, mag in rows}
    return sid, drain_by_bloc_tick


def test_shocked_bloc_unaffected_before_scheduled_tick(shock_run) -> None:  # type: ignore[no-untyped-def]
    _sid, drain = shock_run
    pre_shock_ticks = [t for (bloc, t) in drain if bloc == _SHOCKED_BLOC and t < _SHOCK_TICK]
    assert pre_shock_ticks, "no pre-shock china DRAIN_EDGE rows — cannot establish a baseline"
    # All pre-shock ticks should carry the SAME (unshocked, static base Φ)
    # weekly drain, since external_nodes_phi is otherwise constant per tick
    # (modulo Postgres SUM() summation-order float noise — see the
    # docstring on test_unshocked_bloc_unaffected_across_all_ticks).
    reference = drain[(_SHOCKED_BLOC, pre_shock_ticks[0])]
    for t in pre_shock_ticks[1:]:
        actual = drain[(_SHOCKED_BLOC, t)]
        assert actual == pytest.approx(reference, rel=1e-8), (
            f"pre-shock china drain is not constant across ticks: "
            f"tick {pre_shock_ticks[0]}={reference} vs tick {t}={actual}"
        )


def test_shocked_bloc_scales_by_multiplier_at_and_after_scheduled_tick(shock_run) -> None:  # type: ignore[no-untyped-def]
    _sid, drain = shock_run
    pre_shock_tick = _SHOCK_TICK - 1
    baseline = drain[(_SHOCKED_BLOC, pre_shock_tick)]
    assert baseline > 0.0, "baseline china drain must be positive for a meaningful shock test"

    expected_shocked = baseline * _MULTIPLIER
    post_shock_ticks = [t for (bloc, t) in drain if bloc == _SHOCKED_BLOC and t >= _SHOCK_TICK]
    assert post_shock_ticks, "no post-shock china DRAIN_EDGE rows"
    for t in post_shock_ticks:
        actual = drain[(_SHOCKED_BLOC, t)]
        assert actual == pytest.approx(expected_shocked, rel=_RELATIVE_TOLERANCE), (
            f"tick {t}: china drain {actual} does not match expected "
            f"shocked value {expected_shocked} (baseline {baseline} x {_MULTIPLIER})"
        )


def test_unshocked_bloc_unaffected_across_all_ticks(shock_run) -> None:  # type: ignore[no-untyped-def]
    """Other blocs' drain stays within float-summation noise across ticks.

    Postgres' SUM() aggregation order is unspecified, so tick-to-tick
    values for an unshocked (constant Φ) bloc can differ by IEEE-754
    summation-order noise at the ~1e-10 relative level — this is
    pre-existing float non-associativity, not evidence of shock leakage.
    A real multiplier leak (e.g. 2.5x) would be many orders of magnitude
    larger than this tolerance.
    """
    _sid, drain = shock_run
    other_blocs = {bloc for (bloc, _t) in drain if bloc != _SHOCKED_BLOC}
    assert other_blocs, "no other blocs recorded drain — cannot verify shock scoping"
    for bloc in other_blocs:
        ticks_for_bloc = sorted(t for (b, t) in drain if b == bloc)
        reference = drain[(bloc, ticks_for_bloc[0])]
        for t in ticks_for_bloc[1:]:
            actual = drain[(bloc, t)]
            assert actual == pytest.approx(reference, rel=1e-8), (
                f"bloc {bloc!r} (not the shocked bloc) shows drain variation "
                f"across ticks beyond float noise — the shock may have leaked "
                f"outside its declared bloc: tick {ticks_for_bloc[0]}={reference} "
                f"vs tick {t}={actual}"
            )
