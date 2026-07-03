"""Unit tests for Bug E — engine integration into bridged runner (spec-066 US2).

Spec: 066-marx-coherence-fixes (T024-T025).

Targets ``_tick_loop`` directly with fake bridge / engine / services / graph,
so the per-tick wiring is verified without Postgres. The behaviors checked:

- ``SimulationEngine.run_tick`` is called exactly once per tick.
- ``ServiceContainer`` is constructed once (verified at the integration tier
  via real ``runner.run()``); here we verify the unit-level invariant that
  the runner passes the same ``services`` instance into each tick.

Without these checks, the engine could be silently bypassed (the spec-065
bug that this spec addresses).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from babylon.config.defines._assembler import GameDefines
from babylon.engine.factories import create_bourgeoisie, create_proletariat
from babylon.engine.headless_runner.models import SimulationRunConfig
from babylon.engine.headless_runner.runner import _tick_loop
from babylon.models import WorldState

pytestmark = [pytest.mark.unit]


_SESSION_ID = UUID("00000000-0000-0000-0000-000000000099")


class _FakeBridge:
    """Stand-in for WorldStateBridge — captures per-tick calls."""

    def __init__(self) -> None:
        self.persist_calls: list[tuple[int, str]] = []
        self.event_capture: Any = None
        # Bridge attributes referenced by runner; default to no-op stubs.
        self.set_tick_calls: list[int] = []
        self._endgame_returns: list[Any] = []

    def persist_tick(
        self,
        world: Any,
        tick: int,
        determinism_hash: str,
        opposition_states: Any = None,  # noqa: ARG002 - C1.4 optional snapshot
    ) -> None:  # noqa: ARG002
        self.persist_calls.append((tick, determinism_hash))

    def poll_endgame(self, world: Any, tick: int) -> Any:  # noqa: ARG002
        return None

    @property
    def auditor(self) -> None:
        return None


class _FakeEngine:
    """Stand-in for SimulationEngine — counts run_tick invocations."""

    def __init__(self) -> None:
        self.run_tick_calls: list[tuple[int, int]] = []  # (tick, services_id)
        self.per_system_ms: dict[str, float] = {"FakeSystem": 1.0}

    def run_tick(self, graph: Any, services: Any, context: Any) -> None:  # noqa: ARG002
        self.run_tick_calls.append((context.tick, id(services)))


def _make_config(ticks: int = 5) -> SimulationRunConfig:
    from pathlib import Path

    return SimulationRunConfig(
        ticks=ticks,
        start_year=2010,
        random_seed=2010,
        scope_name="detroit-tri-county",
        scope_fips=frozenset({"26163"}),
        external_node_ids=frozenset(),
        sqlite_reference_path=Path("data/sqlite/marxist-data-3NF.sqlite"),
        output_dir=Path("/tmp/spec_066_test_runner_invocation"),
    )


def _make_minimal_world_and_graph() -> tuple[WorldState, Any]:
    """A real (tiny) WorldState + its DiGraph round-trip survives from_graph()."""
    prol = create_proletariat(id="C001", county_fips="26163")
    bourg = create_bourgeoisie(id="C002", county_fips="26163")
    world = WorldState(
        tick=0,
        entities={"C001": prol, "C002": bourg},
        config=GameDefines(),
    )
    graph = world.to_graph()
    return world, graph


def test_engine_run_tick_called_per_tick() -> None:
    """T025: SimulationEngine.run_tick is called exactly N-1 times for an N-tick run.

    Tick 0 is persisted directly by the loop (no engine call); ticks 1..N-1
    each call run_tick. So a 5-tick run invokes the engine 4 times.
    """
    bridge = _FakeBridge()
    engine = _FakeEngine()
    fake_services = object()
    world, graph = _make_minimal_world_and_graph()
    durations: list[float] = []

    ticks_completed, endgame = _tick_loop(
        bridge=bridge,  # type: ignore[arg-type]
        world=world,
        runtime=None,
        session_id=_SESSION_ID,
        config=_make_config(ticks=5),
        per_tick_durations=durations,
        graph=graph,
        engine=engine,  # type: ignore[arg-type]
        services=fake_services,  # type: ignore[arg-type]
    )

    assert ticks_completed == 5
    assert endgame is None
    # Tick 0: persist only (no engine). Ticks 1, 2, 3, 4: engine + persist.
    assert [t for t, _ in engine.run_tick_calls] == [1, 2, 3, 4]


def test_service_container_constructed_once_before_tick_loop() -> None:
    """T024: the same ServiceContainer instance is passed into every tick.

    Verified at unit level by asserting all engine.run_tick calls receive
    the same id(services). (Constructing the container exactly once happens
    in runner.run(), exercised by the integration tests.)
    """
    bridge = _FakeBridge()
    engine = _FakeEngine()
    fake_services = object()
    world, graph = _make_minimal_world_and_graph()
    durations: list[float] = []

    _tick_loop(
        bridge=bridge,  # type: ignore[arg-type]
        world=world,
        runtime=None,
        session_id=_SESSION_ID,
        config=_make_config(ticks=5),
        per_tick_durations=durations,
        graph=graph,
        engine=engine,  # type: ignore[arg-type]
        services=fake_services,  # type: ignore[arg-type]
    )

    services_ids = {sid for _, sid in engine.run_tick_calls}
    assert len(services_ids) == 1, (
        f"Engine received {len(services_ids)} distinct services instances; "
        f"expected exactly 1 (i.e., constructed-once-before-loop)."
    )
    assert next(iter(services_ids)) == id(fake_services)
