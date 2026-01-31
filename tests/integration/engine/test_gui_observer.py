"""Integration tests for GUI observer thread safety.

Feature: 006-gui-protocol-extension
Tests: T029-T031 (User Story 3 - Thread-Safe State Snapshot)

These tests verify that GUI callbacks receive thread-safe immutable snapshots
when the simulation engine runs concurrently.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest

from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.snapshots import HexState, SimulationSnapshot, TerritoryState

if TYPE_CHECKING:
    pass

# Valid H3 indices for testing (Detroit metro area, resolution 5)
VALID_H3_1 = "852ab2c7fffffff"
VALID_H3_2 = "852ab2c3fffffff"


@pytest.fixture
def simulation_with_territory() -> Simulation:
    """Create a simulation with territory state for testing."""
    state = WorldState()
    config = SimulationConfig()
    sim = Simulation(state, config)

    territory = TerritoryState(
        territory_id="26163",
        controlling_polity="26163",
        hex_claims=frozenset([VALID_H3_1, VALID_H3_2]),
        tick=0,
        profit_rate=0.15,
        equilibrium_r=0.15,
    )
    hexes = {
        VALID_H3_1: HexState(h3_index=VALID_H3_1),
        VALID_H3_2: HexState(h3_index=VALID_H3_2),
    }
    sim._initialize_mvp_territories(territories={"26163": territory}, hexes=hexes)

    return sim


class TestSnapshotImmutability:
    """T029: snapshot is immutable (frozen Pydantic)."""

    def test_snapshot_is_frozen_pydantic(self, simulation_with_territory: Simulation) -> None:
        """Verify SimulationSnapshot is frozen and immutable."""
        sim = simulation_with_territory

        received_snapshots: list[SimulationSnapshot] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            received_snapshots.append(snapshot)

        sim.register_observer(callback)
        sim.step()

        assert len(received_snapshots) == 1
        snapshot = received_snapshots[0]

        # Verify it's a SimulationSnapshot
        assert isinstance(snapshot, SimulationSnapshot)

        # SimulationSnapshot should be frozen (Pydantic model with frozen=True)
        # Attempting to modify should raise ValidationError
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            snapshot.tick = 999  # type: ignore[misc]

    def test_territory_state_in_snapshot_is_immutable(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Verify TerritoryState within snapshot is immutable."""
        sim = simulation_with_territory

        received_snapshots: list[SimulationSnapshot] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            received_snapshots.append(snapshot)

        sim.register_observer(callback)
        sim.step()

        snapshot = received_snapshots[0]
        territory = snapshot.territories["26163"]

        # Verify it's a TerritoryState
        assert isinstance(territory, TerritoryState)

        # TerritoryState should be frozen
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            territory.profit_rate = 0.99  # type: ignore[misc]


class TestConcurrentRegisterStep:
    """T030: concurrent register + step doesn't corrupt callback list."""

    def test_concurrent_registration_during_step(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Verify callback list isn't corrupted by concurrent registration."""
        sim = simulation_with_territory

        call_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
        errors: list[Exception] = []

        def callback_a(tick: int, snapshot: SimulationSnapshot) -> None:
            call_counts["A"] += 1

        def callback_b(tick: int, snapshot: SimulationSnapshot) -> None:
            call_counts["B"] += 1

        def callback_c(tick: int, snapshot: SimulationSnapshot) -> None:
            call_counts["C"] += 1

        # Register initial callback
        sim.register_observer(callback_a)

        def step_loop() -> None:
            """Run multiple steps in a thread."""
            try:
                for _ in range(10):
                    sim.step()
            except Exception as e:
                errors.append(e)

        def register_loop() -> None:
            """Register callbacks concurrently."""
            try:
                for _ in range(5):
                    sim.register_observer(callback_b)
                    sim.register_observer(callback_c)
            except Exception as e:
                errors.append(e)

        # Run step and registration concurrently
        step_thread = threading.Thread(target=step_loop)
        register_thread = threading.Thread(target=register_loop)

        step_thread.start()
        register_thread.start()

        step_thread.join()
        register_thread.join()

        # No exceptions during concurrent operation
        assert len(errors) == 0

        # Callback A should have been invoked at least once
        assert call_counts["A"] > 0


class TestSnapshotConsistency:
    """T031: callback receives consistent snapshot (no partial updates)."""

    def test_snapshot_tick_matches_state(self, simulation_with_territory: Simulation) -> None:
        """Verify snapshot tick is consistent with simulation state."""
        sim = simulation_with_territory

        inconsistencies: list[str] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            # The tick parameter and snapshot.tick should match
            if tick != snapshot.tick:
                inconsistencies.append(f"tick={tick} but snapshot.tick={snapshot.tick}")

        sim.register_observer(callback)

        # Run multiple steps
        for _ in range(10):
            sim.step()

        # No inconsistencies should be found
        assert len(inconsistencies) == 0

    def test_all_callbacks_same_snapshot(self, simulation_with_territory: Simulation) -> None:
        """Verify all callbacks receive the same snapshot instance for one tick."""
        sim = simulation_with_territory

        snapshots_by_tick: dict[int, list[SimulationSnapshot]] = {}

        def callback_a(tick: int, snapshot: SimulationSnapshot) -> None:
            if tick not in snapshots_by_tick:
                snapshots_by_tick[tick] = []
            snapshots_by_tick[tick].append(snapshot)

        def callback_b(tick: int, snapshot: SimulationSnapshot) -> None:
            if tick not in snapshots_by_tick:
                snapshots_by_tick[tick] = []
            snapshots_by_tick[tick].append(snapshot)

        sim.register_observer(callback_a)
        sim.register_observer(callback_b)

        # Run a few steps
        for _ in range(3):
            sim.step()

        # For each tick, both callbacks should have received the same snapshot
        for tick, snapshots in snapshots_by_tick.items():
            assert len(snapshots) == 2, f"Tick {tick}: expected 2 callbacks"
            # Same object reference (snapshot created once, passed to all)
            assert snapshots[0] is snapshots[1], f"Tick {tick}: different snapshot objects"

    def test_snapshot_not_modified_by_later_steps(
        self, simulation_with_territory: Simulation
    ) -> None:
        """Verify snapshot from tick N is not affected by step N+1."""
        sim = simulation_with_territory

        received_snapshots: list[tuple[int, SimulationSnapshot]] = []

        def callback(tick: int, snapshot: SimulationSnapshot) -> None:
            received_snapshots.append((tick, snapshot))

        sim.register_observer(callback)

        # Run multiple steps
        sim.step(5)

        # Each snapshot should have its own tick value
        for expected_tick, (received_tick, snapshot) in enumerate(received_snapshots, 1):
            assert received_tick == expected_tick
            assert snapshot.tick == expected_tick
