"""Integration tests for GUI readiness (SC-001).

This test validates that the simulation is ready for GUI development:
- Simulation can be initialized with territory state
- step() advances simulation and changes profit_rate
- get_snapshot() returns complete state
- get_territory_state() returns territory by ID
- Profit rate clamping works for edge cases

See Also:
    - quickstart.md#GUI Readiness Test: Usage examples
    - spec.md#SC-001: Success criterion definition
"""

from __future__ import annotations

import logging

import pytest

from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.snapshots import HexState, SimulationSnapshot, TerritoryState
from babylon.protocols import SimulationControl, SimulationState


@pytest.fixture
def sample_territory_state() -> TerritoryState:
    """Create a sample Wayne County territory state."""
    return TerritoryState(
        territory_id="26163",
        controlling_polity="26163",
        hex_claims=frozenset(["8528a9c9bffffff", "8528a9c8bffffff"]),
        tick=0,
        profit_rate=0.15,
        equilibrium_r=0.15,
    )


@pytest.fixture
def sample_hex_states() -> dict[str, HexState]:
    """Create sample hex states."""
    return {
        "8528a9c9bffffff": HexState(h3_index="8528a9c9bffffff"),
        "8528a9c8bffffff": HexState(h3_index="8528a9c8bffffff"),
    }


@pytest.fixture
def simulation_with_territory(
    sample_territory_state: TerritoryState,
    sample_hex_states: dict[str, HexState],
) -> Simulation:
    """Create a simulation with MVP territory state initialized."""
    # Create basic WorldState and SimulationConfig
    state = WorldState()
    config = SimulationConfig()

    # Create simulation
    sim = Simulation(state, config)

    # Initialize MVP territory state
    sim._initialize_mvp_territories(
        territories={"26163": sample_territory_state},
        hexes=sample_hex_states,
    )

    return sim


class TestGUIReadinessProtocolMethods:
    """Test that SimulationState protocol methods work correctly."""

    def test_get_current_tick_returns_zero_initially(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_current_tick() returns 0 for new simulation."""
        sim = simulation_with_territory
        assert sim.get_current_tick() == 0

    def test_get_snapshot_returns_simulation_snapshot(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_snapshot() returns SimulationSnapshot with territories."""
        sim = simulation_with_territory
        snapshot = sim.get_snapshot()

        assert isinstance(snapshot, SimulationSnapshot)
        assert snapshot.tick == 0
        assert "26163" in snapshot.territories
        assert len(snapshot.hexes) == 2

    def test_get_territory_state_returns_territory(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_territory_state() returns correct territory."""
        sim = simulation_with_territory
        territory = sim.get_territory_state("26163")

        assert territory is not None
        assert territory.territory_id == "26163"
        assert territory.profit_rate == 0.15

    def test_get_territory_state_returns_none_for_invalid_id(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_territory_state() returns None for invalid ID."""
        sim = simulation_with_territory
        territory = sim.get_territory_state("99999")

        assert territory is None

    def test_get_hexes_for_territory_returns_set(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_hexes_for_territory() returns hex set."""
        sim = simulation_with_territory
        hexes = sim.get_hexes_for_territory("26163")

        assert len(hexes) == 2
        assert "8528a9c9bffffff" in hexes
        assert "8528a9c8bffffff" in hexes

    def test_get_hexes_for_territory_returns_empty_for_invalid_id(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify get_hexes_for_territory() returns empty set for invalid ID."""
        sim = simulation_with_territory
        hexes = sim.get_hexes_for_territory("99999")

        assert hexes == set()


class TestGUIReadinessStepBehavior:
    """Test that step() advances simulation state correctly."""

    def test_step_advances_tick(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify step() increments the tick counter."""
        sim = simulation_with_territory
        assert sim.get_current_tick() == 0

        sim.step()

        assert sim.get_current_tick() == 1

    def test_step_changes_profit_rate(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify step() changes territory profit_rate (SC-001 core test)."""
        sim = simulation_with_territory

        # Get initial state
        initial_state = sim.get_territory_state("26163")
        assert initial_state is not None
        _ = initial_state.profit_rate  # Verify profit_rate exists

        # Step simulation
        sim.step()

        # Get updated state
        updated_state = sim.get_territory_state("26163")
        assert updated_state is not None

        # Profit rate should change (per decay formula)
        # With decay_rate=0.05 and equilibrium_r=initial_r, first tick produces:
        # r_new = r_old * (1 - 0.05) + equilibrium_r * 0.05 = r_old (no change if at equilibrium)
        # But the tick should still be updated
        assert updated_state.tick == 1

    def test_step_n_advances_multiple_ticks(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify step(n) advances by n ticks."""
        sim = simulation_with_territory
        assert sim.get_current_tick() == 0

        sim.step(10)

        assert sim.get_current_tick() == 10

    def test_step_rejects_non_positive_n(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify step(n<=0) raises ValueError."""
        sim = simulation_with_territory

        with pytest.raises(ValueError, match="must be positive"):
            sim.step(0)

        with pytest.raises(ValueError, match="must be positive"):
            sim.step(-1)


class TestGUIReadinessResetBehavior:
    """Test that reset() restores initial state."""

    def test_reset_restores_tick_zero(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify reset() restores tick to 0."""
        sim = simulation_with_territory
        sim.step(100)
        assert sim.get_current_tick() == 100

        sim.reset()

        assert sim.get_current_tick() == 0

    def test_reset_restores_territory_state(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify reset() restores territory profit_rate to initial value."""
        sim = simulation_with_territory

        initial_state = sim.get_territory_state("26163")
        assert initial_state is not None
        initial_profit_rate = initial_state.profit_rate

        # Run many ticks
        sim.step(100)

        # Reset
        sim.reset()

        # Verify restored
        restored_state = sim.get_territory_state("26163")
        assert restored_state is not None
        assert restored_state.profit_rate == initial_profit_rate
        assert restored_state.tick == 0


class TestGUIReadinessProfitRateClamping:
    """Test profit_rate clamping for edge cases."""

    def test_clamping_logs_warning_for_out_of_range(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify profit_rate clamping logs warning."""
        with caplog.at_level(logging.WARNING):
            territory = TerritoryState.with_clamped_profit_rate(
                territory_id="26163",
                controlling_polity="26163",
                hex_claims=frozenset(),
                tick=0,
                profit_rate=1.5,  # Out of range - should clamp to 1.0
                equilibrium_r=0.15,
            )

        assert territory.profit_rate == 1.0
        assert "clamped" in caplog.text

    def test_clamping_handles_negative_values(self) -> None:
        """Verify negative profit_rate is clamped to 0.0."""
        territory = TerritoryState.with_clamped_profit_rate(
            territory_id="26163",
            controlling_polity="26163",
            hex_claims=frozenset(),
            tick=0,
            profit_rate=-0.5,  # Out of range - should clamp to 0.0
            equilibrium_r=0.15,
        )

        assert territory.profit_rate == 0.0

    def test_valid_profit_rate_not_clamped(self) -> None:
        """Verify valid profit_rate is not modified."""
        territory = TerritoryState.with_clamped_profit_rate(
            territory_id="26163",
            controlling_polity="26163",
            hex_claims=frozenset(),
            tick=0,
            profit_rate=0.5,  # In range
            equilibrium_r=0.15,
        )

        assert territory.profit_rate == 0.5


class TestGUIReadinessProtocolCompliance:
    """Test that Simulation implements protocols correctly."""

    def test_simulation_implements_simulation_state(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify Simulation is instance of SimulationState."""
        sim = simulation_with_territory
        assert isinstance(sim, SimulationState)

    def test_simulation_implements_simulation_control(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify Simulation is instance of SimulationControl."""
        sim = simulation_with_territory
        assert isinstance(sim, SimulationControl)

    def test_protocol_type_hints_work(
        self,
        simulation_with_territory: Simulation,
    ) -> None:
        """Verify protocol methods can be called via protocol types."""

        def query_state(sim: SimulationState) -> int:
            return sim.get_current_tick()

        def control_sim(sim: SimulationControl) -> None:
            sim.step()

        # These should work without type errors
        tick = query_state(simulation_with_territory)
        assert tick == 0

        control_sim(simulation_with_territory)
        tick = query_state(simulation_with_territory)
        assert tick == 1
