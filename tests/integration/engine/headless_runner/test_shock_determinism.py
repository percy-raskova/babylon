"""Spec-102 SLICE B: scheduled bloc shocks are deterministic.

Drives the real headless runner twice with an IDENTICAL shock_schedule
(same seed, different session ids — Postgres requires session isolation
per run) and asserts both the hex-level economic state AND the shocked
bloc's DRAIN_EDGE (Φ distribution) trajectory reproduce byte-identically
between the two runs.

Correction (2026-07-04, empirical — supersedes an earlier draft of this
test and spec.md D5's original framing): neither of the two
"determinism hash" tables in this codebase is directly comparable across
two DIFFERENT session ids:

- ``tick_commit.determinism_hash`` is
  ``sha256(f"{session_id}:{tick}:{random_seed}")`` (``_tick_loop`` in
  ``runner.py``) — it bakes in ``session_id`` BY CONSTRUCTION, so it can
  NEVER match across two sessions regardless of determinism.
- ``conservation_audit_log.determinism_hash`` is computed by
  ``compute_determinism_hash(tick, rng_seed, hex_rows, action_list)``
  (``ConservationAuditor.evaluate()``), which looks state-pure on its
  signature — but ``hex_rows`` are ``DynamicHexState``-shaped Pydantic
  models that themselves carry a ``session_id`` field, and
  ``compute_determinism_hash`` hashes ``row.model_dump(mode="json")``
  verbatim. ``session_id`` therefore leaks into the "state hash" too.
  Verified empirically: running the UNMODIFIED spec-101 baseline (empty
  ``shock_schedule``) twice ALSO produces a diverging
  ``conservation_audit_log.determinism_hash`` sequence — this is a
  pre-existing latent gap in the determinism-hash instrumentation,
  unrelated to spec-102's shock-scheduling code (out of scope to fix
  here — same class of "flagged, not remediated" finding as the STEP-0
  hex_spatial_map guard's deferred session-scoping half).

Given that, this test proves reproducibility the direct way: comparing
the actual persisted VALUES (hex-level ``c``/``v``/``s``/``k`` from
``v_hex_state_asof``, and per-bloc DRAIN_EDGE magnitudes from
``boundary_flow_register``) between the two runs, which is exactly what a
"hash chain" would be a proxy for if the session-id leak did not exist.

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


def _run_with_shock_schedule() -> str:
    """Run the tri-county headless sim once with a scheduled china shock.

    Returns:
        The session id (str) of the completed run.
    """
    from babylon.engine.headless_runner.models import (
        ExitReason,
        ScheduledBlocShock,
        SimulationRunConfig,
    )
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    os.environ.setdefault("BABYLON_TEST_PG_DSN", _DSN)
    sc = resolve_scope("detroit-tri-county")
    out = Path(tempfile.mkdtemp(prefix="sim_shock_determinism_"))
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
        shock_schedule=(ScheduledBlocShock(tick=2, bloc="china", phi_multiplier=2.5),),
    )
    result = runner_run(config)
    assert result.exit_reason == ExitReason.COMPLETED, result.exit_reason
    return str(result.session_id)


@pytest.fixture(scope="module")
def two_shock_runs() -> tuple[str, str]:
    """Run the identical shock-schedule scenario twice; yield both session ids."""
    sid_a = _run_with_shock_schedule()
    sid_b = _run_with_shock_schedule()
    return sid_a, sid_b


def _hex_state_sequence(session_id: str) -> list[tuple[int, str, float, float, float, float]]:
    import psycopg

    with psycopg.connect(_DSN) as conn:
        rows = conn.execute(
            "SELECT tick, h3_index, c, v, s, k FROM v_hex_state_asof "
            "WHERE session_id = %s ORDER BY tick, h3_index",
            (session_id,),
        ).fetchall()
    return [
        (int(tick), str(h3), float(c), float(v), float(s), float(k))
        for tick, h3, c, v, s, k in rows
    ]


def _drain_sequence(session_id: str) -> list[tuple[str, int, float]]:
    import psycopg

    with psycopg.connect(_DSN) as conn:
        rows = conn.execute(
            "SELECT source_node_id, tick, SUM(magnitude) FROM boundary_flow_register "
            "WHERE session_id = %s AND flow_type = 'drain_edge' "
            "GROUP BY source_node_id, tick ORDER BY source_node_id, tick",
            (session_id,),
        ).fetchall()
    return [(str(node), int(tick), float(mag)) for node, tick, mag in rows]


def test_hex_economic_state_reproduces_across_shocked_runs(
    two_shock_runs: tuple[str, str],
) -> None:
    sid_a, sid_b = two_shock_runs
    hex_a = _hex_state_sequence(sid_a)
    hex_b = _hex_state_sequence(sid_b)

    assert hex_a, "no v_hex_state_asof rows for run A — determinism check is vacuous"
    assert len(hex_a) == len(hex_b), f"hex row count differs: {len(hex_a)} vs {len(hex_b)}"
    assert hex_a == hex_b, (
        "hex-level (tick, h3_index, c, v, s, k) sequence diverged between two "
        "runs of the identical shock_schedule — the shock-scheduling code "
        "introduced nondeterminism into the tick loop"
    )


def test_shocked_bloc_drain_trajectory_reproduces_across_runs(
    two_shock_runs: tuple[str, str],
) -> None:
    sid_a, sid_b = two_shock_runs
    drain_a = _drain_sequence(sid_a)
    drain_b = _drain_sequence(sid_b)

    assert drain_a, "no DRAIN_EDGE rows for run A — determinism check is vacuous"
    assert [(n, t) for n, t, _m in drain_a] == [(n, t) for n, t, _m in drain_b], (
        "DRAIN_EDGE (bloc, tick) coverage differs between the two runs"
    )
    for (node_a, tick_a, mag_a), (node_b, tick_b, mag_b) in zip(drain_a, drain_b, strict=True):
        assert node_a == node_b and tick_a == tick_b
        assert mag_a == pytest.approx(mag_b, rel=1e-8), (
            f"DRAIN_EDGE magnitude for bloc={node_a} tick={tick_a} diverged "
            f"between the two identical-shock-schedule runs: {mag_a} vs {mag_b}"
        )
