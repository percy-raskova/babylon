"""Spec-101: boundary-flow trade circuit is live end-to-end.

Drives the real headless runner for a few tri-county ticks and asserts, against
the runtime Postgres, that:

- every tick emits ``DRAIN_EDGE`` boundary rows for each external bloc with
  attributed Φ > 0 (the dormant seam is wired — FR-101-1);
- the per-bloc conservation identity ``Σ DRAIN_EDGE ≡ Φ_week`` holds within ε
  (FR-101-5), both directly over ``boundary_flow_register`` and via the
  ``imperial_rent_phi_week_distribution`` audit rows (all OK severity);
- blocs with Φ = 0 (india, latin_america — no grounded bloc, D3) emit no rows.

RED-first evidence: with the runner→TickContext wiring reverted the Φ
distribution silently no-ops (``_invoke_phi_distribution_if_wired`` returns early
without the four context keys) and NO ``drain_edge`` rows exist — these
assertions fail. Gated like the other live-bridge tests: requires the local
Postgres test DB and the canonical SQLite reference DB.
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


_TICKS = 4  # tick 0 + ticks 1..3 carry DRAIN rows
_WEEKS_PER_YEAR = 52.0


@pytest.fixture(scope="module")
def trade_run():  # type: ignore[no-untyped-def]
    """Run the tri-county headless sim once; yield (session_id, phi_map, drain, audit)."""
    import psycopg

    from babylon.engine.headless_runner.models import ExitReason, SimulationRunConfig
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    os.environ.setdefault("BABYLON_TEST_PG_DSN", _DSN)
    sc = resolve_scope("detroit-tri-county")
    out = Path(tempfile.mkdtemp(prefix="sim_trade_"))
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
    )
    result = runner_run(config)
    assert result.exit_reason == ExitReason.COMPLETED, result.exit_reason
    sid = str(result.session_id)

    with psycopg.connect(_DSN) as conn:
        phi_map = {
            str(n): float(p)
            for n, p in conn.execute(
                "SELECT node_id, phi_year_inflow FROM dynamic_external_node_state "
                "WHERE session_id = %s AND tick = 0",
                (sid,),
            ).fetchall()
        }
        drain = conn.execute(
            "SELECT source_node_id, tick, SUM(magnitude) "
            "FROM boundary_flow_register "
            "WHERE session_id = %s AND flow_type = 'drain_edge' "
            "GROUP BY source_node_id, tick",
            (sid,),
        ).fetchall()
        audit = conn.execute(
            "SELECT scale, severity, computed_value "
            "FROM conservation_audit_log "
            "WHERE session_id = %s AND invariant_name = 'imperial_rent_phi_week_distribution'",
            (sid,),
        ).fetchall()
    return sid, phi_map, drain, audit


def test_attribution_gives_some_nonzero_phi(trade_run) -> None:
    _sid, phi_map, _drain, _audit = trade_run
    positive = {n: p for n, p in phi_map.items() if p > 0}
    # spec-101 D3: 6 international blocs receive attributed Φ; india/latin_america = 0.
    assert positive, "no external bloc received attributed Φ — attribution regressed"
    assert phi_map.get("india", 0.0) == 0.0
    assert phi_map.get("latin_america", 0.0) == 0.0


def test_drain_rows_every_tick_for_positive_phi_blocs(trade_run) -> None:
    _sid, phi_map, drain, _audit = trade_run
    positive_blocs = {n for n, p in phi_map.items() if p > 0}
    ticks_with_drain: dict[str, set[int]] = {}
    for node, tick, _mag in drain:
        ticks_with_drain.setdefault(str(node), set()).add(int(tick))
    expected_ticks = set(range(1, _TICKS))  # ticks 1..3
    for bloc in positive_blocs:
        assert ticks_with_drain.get(bloc, set()) >= expected_ticks, (
            f"bloc {bloc} missing DRAIN_EDGE rows on some tick: {ticks_with_drain.get(bloc)}"
        )
    # Zero-Φ blocs emit nothing (FR-020).
    zero_blocs = {n for n, p in phi_map.items() if p == 0}
    assert zero_blocs.isdisjoint(ticks_with_drain), "a zero-Φ bloc emitted DRAIN rows"


def test_conservation_identity_holds_per_bloc(trade_run) -> None:
    _sid, phi_map, drain, _audit = trade_run
    # Spec-101 review fix #4: without this non-emptiness guard the test
    # passes VACUOUSLY when ``drain`` is empty (e.g. the wiring-reverted
    # regression this test's docstring claims to catch) — the ``for`` loop
    # below simply never executes and the assertion inside it never runs.
    positive_blocs = {n for n, p in phi_map.items() if p > 0}
    assert drain, (
        "no DRAIN_EDGE rows at all — boundary rows must exist for the "
        f"positive-Φ blocs {sorted(positive_blocs)}; a wiring regression "
        "would silently make this test pass with an empty loop body"
    )
    drained_blocs = {str(node) for node, _tick, _mag in drain}
    assert drained_blocs == positive_blocs, (
        f"DRAIN rows cover {sorted(drained_blocs)} but positive-Φ blocs are "
        f"{sorted(positive_blocs)} — missing or spurious bloc coverage"
    )
    for node, _tick, mag in drain:
        phi_week = phi_map[str(node)] / _WEEKS_PER_YEAR
        assert mag == pytest.approx(phi_week, rel=1e-9), (
            f"Σ DRAIN for {node} = {mag} != Φ_week {phi_week}"
        )


def test_conservation_audit_rows_all_ok(trade_run) -> None:
    _sid, phi_map, _drain, audit = trade_run
    assert audit, "no imperial_rent_phi_week_distribution audit rows were written"
    for scale, severity, computed in audit:
        assert severity == "ok", f"{scale}: severity={severity} (residual out of ε)"
        assert computed == pytest.approx(1.0, rel=1e-9), f"{scale}: ratio={computed}"
