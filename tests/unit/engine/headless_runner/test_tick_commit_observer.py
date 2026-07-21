"""Unit tests for the tick-commit observer seam (Program 24, the Archive).

Targets ``_advance_tick`` directly with a fake bridge, per this directory's
established no-Postgres wiring-test pattern
(``test_runner_engine_invocation.py``). Pins three behaviors:

- the observer fires strictly *after* ``bridge.persist_tick`` returns,
- a ``None`` observer (the default, and every pre-Program-24 call path)
  changes nothing, and
- the observer is skipped when no graph is in play (the spec-065
  persist-only path has no committed graph to observe).
"""

from __future__ import annotations

from typing import Any

import pytest

from babylon.engine.headless_runner.runner import _advance_tick

pytestmark = [pytest.mark.unit]


class _FakeBridge:
    """Stand-in for WorldStateBridge — records persist calls in sequence."""

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    def persist_tick(
        self,
        world: Any,
        tick: int,
        determinism_hash: str,
        opposition_states: Any = None,
    ) -> None:
        self._journal.append(f"persist:{tick}")


class _RecordingObserver:
    """Structural TickCommitObserver — records what it was handed."""

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.seen: list[tuple[int, Any, Any]] = []

    def on_tick_committed(self, *, tick: int, world: Any, graph: Any) -> None:
        self._journal.append(f"observe:{tick}")
        self.seen.append((tick, world, graph))


class TestTickCommitObserver:
    """The bake-at-tick-commit seam's ordering and default-off contract."""

    def test_observer_fires_after_persist_with_committed_state(self) -> None:
        """Observer runs post-persist and receives the same world + graph."""
        journal: list[str] = []
        observer = _RecordingObserver(journal)
        world, graph = object(), object()

        returned = _advance_tick(
            bridge=_FakeBridge(journal),  # type: ignore[arg-type]
            world=world,
            tick=7,
            determinism_hash="0" * 64,
            graph=graph,
            tick_commit_observer=observer,
        )

        assert journal == ["persist:7", "observe:7"]
        assert observer.seen == [(7, world, graph)]
        assert returned is world

    def test_default_none_observer_changes_nothing(self) -> None:
        """The pre-Program-24 call shape is byte-identical: persist only."""
        journal: list[str] = []

        _advance_tick(
            bridge=_FakeBridge(journal),  # type: ignore[arg-type]
            world=object(),
            tick=3,
            determinism_hash="0" * 64,
            graph=object(),
        )

        assert journal == ["persist:3"]

    def test_observer_skipped_without_graph(self) -> None:
        """The persist-only path (no graph) has nothing committed to observe."""
        journal: list[str] = []
        observer = _RecordingObserver(journal)

        _advance_tick(
            bridge=_FakeBridge(journal),  # type: ignore[arg-type]
            world=object(),
            tick=1,
            determinism_hash="0" * 64,
            tick_commit_observer=observer,
        )

        assert journal == ["persist:1"]
        assert observer.seen == []
