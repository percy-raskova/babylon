"""Spec-065 T058-T062: end-game detection round-trip tests.

T058: --endgame-detector argparse acceptance (already covered by
      existing test_argparse_cli unit; redundant here).
T059: bridge.set_endgame_detector resolution unit (covered in
      test_bridge.py:TestBridgeUtilities; this module focuses on the
      end-to-end runner integration).
T061: Inject FireAtTick3 → exit early at tick 3. (ImperialCollapseAtTick250,
      the fixed-at-250 sibling detector, is exercised at the resolution-unit
      layer in test_endgame_resolution.py; this end-to-end test uses the
      fast-firing detector to keep the Postgres-backed round trip cheap.)
T062: Without --endgame-detector → run to completion, no end_game_event.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

PG_DSN_ENV = "BABYLON_TEST_PG_DSN"
SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")
DEFAULT_DSN = "dbname=babylon_test host=localhost port=5433 user=test password=test"


def _postgres_reachable() -> bool:
    dsn = os.environ.get(PG_DSN_ENV, DEFAULT_DSN)
    try:
        import psycopg

        psycopg.connect(dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _postgres_reachable(), reason="Postgres test DB not reachable"),
    pytest.mark.skipif(
        not SQLITE_REF.exists(), reason=f"SQLite reference DB missing at {SQLITE_REF}"
    ),
]


def _run(*, ticks: int, endgame_detector: str | None) -> object:
    os.environ.setdefault(PG_DSN_ENV, DEFAULT_DSN)
    from babylon.engine.headless_runner.models import SimulationRunConfig
    from babylon.engine.headless_runner.runner import run as runner_run
    from babylon.engine.headless_runner.scopes import resolve_scope

    sc = resolve_scope("detroit-tri-county")
    return runner_run(
        SimulationRunConfig(
            ticks=ticks,
            start_year=2010,
            random_seed=2010,
            scope_name="detroit-tri-county",
            scope_fips=sc.scope_fips,
            external_node_ids=sc.external_node_ids,
            sqlite_reference_path=SQLITE_REF,
            output_dir=Path(tempfile.mkdtemp(prefix="sim_endgame_")),
            endgame_detector=endgame_detector,
        )
    )


def test_imperial_collapse_at_tick_3() -> None:
    """T061: detector firing at tick 3 → early termination at tick 4 (range)."""
    # FireAtTick3 has a zero-arg constructor (required by
    # WorldStateBridge.set_endgame_detector's dotted-path instantiation,
    # which passes no constructor args) and fires at tick 3, keeping this
    # Postgres-backed round trip cheap instead of running out to tick 250.
    detector_path = "tests.integration.fixtures.endgame.FireAtTick3"
    result = _run(ticks=10, endgame_detector=detector_path)

    from babylon.engine.headless_runner.models import ExitReason

    assert result.exit_reason == ExitReason.EARLY_TERMINATED, (  # type: ignore[attr-defined]
        f"expected EARLY_TERMINATED, got {result.exit_reason}"  # type: ignore[attr-defined]
    )
    # The detector fires at tick=3; ticks_completed = 4.
    assert result.ticks_completed == 4  # type: ignore[attr-defined]

    summary = json.loads(
        (result.artifact_dir / "summary.json").read_text()  # type: ignore[attr-defined]
    )
    assert summary["run_metadata"]["exit_reason"] == "early_terminated"
    end_game = summary.get("end_game_event")
    assert end_game is not None
    assert end_game["tick"] == 3
    assert end_game["condition"] == "IMPERIAL_COLLAPSE"


def test_no_detector_runs_full_ticks() -> None:
    """T062: without --endgame-detector, runs to full tick count."""
    result = _run(ticks=5, endgame_detector=None)

    from babylon.engine.headless_runner.models import ExitReason

    assert result.exit_reason == ExitReason.COMPLETED  # type: ignore[attr-defined]
    assert result.ticks_completed == 5  # type: ignore[attr-defined]

    summary = json.loads(
        (result.artifact_dir / "summary.json").read_text()  # type: ignore[attr-defined]
    )
    assert summary["run_metadata"]["exit_reason"] == "completed"
    assert "end_game_event" not in summary or summary.get("end_game_event") is None
