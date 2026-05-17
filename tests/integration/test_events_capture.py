"""Spec-065 T068/T069: events capture integration tests.

T068: summary.events is a list with the right schema for each entry.
T069: An engine-emitted event lands in summary.events with the right tick.

Without engine integration the events array stays empty (current
spec-065 first cut). T069 simulates engine emission via the bridge's
event_capture.on_event() interface to validate the round-trip.
"""

from __future__ import annotations

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


def _run(*, ticks: int = 5) -> object:
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
            output_dir=Path(tempfile.mkdtemp(prefix="sim_events_")),
        )
    )


def test_events_array_schema() -> None:
    """T068: summary.events is a list (possibly empty) with valid entries.

    Each entry has: tick (int >= 0), event_type (str), entity_ids (list),
    severity ∈ {info, warning, error, critical}, details (dict).
    Inter-tick ordering: tick is non-decreasing.
    """
    result = _run(ticks=5)
    assert result.exit_reason.value == "completed"  # type: ignore[attr-defined]

    summary = json.loads(
        (result.artifact_dir / "summary.json").read_text()  # type: ignore[attr-defined]
    )
    events = summary.get("events", [])
    assert isinstance(events, list)

    last_tick = -1
    for ev in events:
        assert isinstance(ev["tick"], int) and ev["tick"] >= 0
        assert isinstance(ev["event_type"], str)
        assert isinstance(ev["entity_ids"], list)
        assert ev["severity"] in {"info", "warning", "error", "critical"}
        assert isinstance(ev["details"], dict)
        # Inter-tick monotonicity: tick is non-decreasing across the array.
        assert ev["tick"] >= last_tick, (
            f"events array not monotonic: tick {ev['tick']} after {last_tick}"
        )
        last_tick = ev["tick"]


def test_engine_emitted_event_visible_in_summary(monkeypatch) -> None:
    """T069: a synthetic event injected via event_capture lands in summary.events."""
    # Patch _advance_tick to inject an event before persist on tick 2.
    from babylon.engine.headless_runner import runner as runner_module

    real_advance = runner_module._advance_tick

    class _SyntheticEvent:
        event_type = "SUPERWAGE_CRISIS"
        affected_entity_ids = ("26163",)
        severity = "warning"

    def patched_advance(*, bridge: Any, world: Any, tick: int, determinism_hash: str) -> None:
        if tick == 2 and bridge.event_capture is not None:
            bridge.event_capture.on_event(_SyntheticEvent())
        return real_advance(
            bridge=bridge,
            world=world,
            tick=tick,
            determinism_hash=determinism_hash,
        )

    monkeypatch.setattr(runner_module, "_advance_tick", patched_advance)

    result = _run(ticks=5)
    assert result.exit_reason.value == "completed"  # type: ignore[attr-defined]

    summary = json.loads(
        (result.artifact_dir / "summary.json").read_text()  # type: ignore[attr-defined]
    )
    events = summary.get("events", [])
    matching = [
        e for e in events if e.get("event_type") == "SUPERWAGE_CRISIS" and e.get("tick") == 2
    ]
    assert matching, f"Expected SUPERWAGE_CRISIS at tick 2; got events={events}"
    assert "26163" in matching[0]["entity_ids"]
