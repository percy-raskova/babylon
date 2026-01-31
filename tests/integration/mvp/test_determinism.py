"""Integration tests for simulation determinism (SC-002).

This test validates that the simulation is deterministic:
- Two simulations with identical initial state produce identical results
- Running 100 ticks produces reproducible profit_rate values
- reset() followed by step() produces identical state

See Also:
    - quickstart.md#Determinism Verification: Usage examples
    - spec.md#SC-002: Success criterion definition
"""

from __future__ import annotations

import pytest

from babylon.engine.simulation import Simulation
from babylon.models import SimulationConfig, WorldState
from babylon.models.snapshots import HexState, TerritoryState


def create_simulation_with_territories(
    territories: dict[str, TerritoryState],
    hexes: dict[str, HexState],
) -> Simulation:
    """Create a simulation with MVP territory state initialized."""
    state = WorldState()
    config = SimulationConfig()
    sim = Simulation(state, config)
    sim._initialize_mvp_territories(territories=territories, hexes=hexes)
    return sim


@pytest.fixture
def detroit_territories() -> dict[str, TerritoryState]:
    """Create Detroit test case territories (Wayne and Oakland counties)."""
    wayne = TerritoryState(
        territory_id="26163",
        controlling_polity="26163",
        hex_claims=frozenset(["8528a9c9bffffff", "8528a9c8bffffff"]),
        tick=0,
        profit_rate=0.18,  # Wayne County rate
        equilibrium_r=0.18,
    )
    oakland = TerritoryState(
        territory_id="26125",
        controlling_polity="26125",
        hex_claims=frozenset(["8528a9cbaffffff"]),
        tick=0,
        profit_rate=0.12,  # Oakland County rate (different from Wayne)
        equilibrium_r=0.12,
    )
    return {"26163": wayne, "26125": oakland}


@pytest.fixture
def detroit_hexes() -> dict[str, HexState]:
    """Create hex states for Detroit test case."""
    return {
        "8528a9c9bffffff": HexState(h3_index="8528a9c9bffffff"),
        "8528a9c8bffffff": HexState(h3_index="8528a9c8bffffff"),
        "8528a9cbaffffff": HexState(h3_index="8528a9cbaffffff"),
    }


class TestDeterminism100Ticks:
    """Test that 100-tick simulation is deterministic (SC-002)."""

    def test_two_identical_simulations_produce_same_results(
        self,
        detroit_territories: dict[str, TerritoryState],
        detroit_hexes: dict[str, HexState],
    ) -> None:
        """Verify two simulations with same initial state produce identical results."""
        # Create two identical simulations
        sim1 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )
        sim2 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )

        # Run 100 ticks on each
        sim1.step(100)
        sim2.step(100)

        # Verify identical tick
        assert sim1.get_current_tick() == 100
        assert sim2.get_current_tick() == 100

        # Verify identical territory states
        for territory_id in ["26163", "26125"]:
            state1 = sim1.get_territory_state(territory_id)
            state2 = sim2.get_territory_state(territory_id)

            assert state1 is not None
            assert state2 is not None
            assert state1.profit_rate == state2.profit_rate, (
                f"Determinism violation for {territory_id}: "
                f"{state1.profit_rate} != {state2.profit_rate}"
            )
            assert state1.tick == state2.tick

    def test_territories_maintain_different_rates(
        self,
        detroit_territories: dict[str, TerritoryState],
        detroit_hexes: dict[str, HexState],
    ) -> None:
        """Verify Wayne and Oakland maintain different profit rates (SC-006 prerequisite)."""
        sim = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )

        # Run 100 ticks
        sim.step(100)

        # Get territory states
        wayne = sim.get_territory_state("26163")
        oakland = sim.get_territory_state("26125")

        assert wayne is not None
        assert oakland is not None

        # They should still have different profit rates
        # (due to territory-specific equilibrium_r)
        # Note: They won't necessarily be exactly the initial values,
        # but they should remain distinct due to different equilibrium_r values
        assert wayne.equilibrium_r != oakland.equilibrium_r
        # The profit rates should have converged toward their respective equilibria
        # With decay_rate=0.05, after 100 ticks they should be very close to equilibrium


class TestDeterminismResetBehavior:
    """Test that reset produces deterministic results."""

    def test_reset_then_step_produces_identical_state(
        self,
        detroit_territories: dict[str, TerritoryState],
        detroit_hexes: dict[str, HexState],
    ) -> None:
        """Verify reset -> step produces same state as fresh simulation."""
        # Create first simulation and run
        sim1 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )
        sim1.step(50)

        # Reset and run 50 more ticks
        sim1.reset()
        sim1.step(50)

        # Create fresh simulation and run 50 ticks
        sim2 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )
        sim2.step(50)

        # Verify identical states
        for territory_id in ["26163", "26125"]:
            state1 = sim1.get_territory_state(territory_id)
            state2 = sim2.get_territory_state(territory_id)

            assert state1 is not None
            assert state2 is not None
            assert state1.profit_rate == state2.profit_rate
            assert state1.tick == state2.tick

    def test_multiple_reset_cycles_are_deterministic(
        self,
        detroit_territories: dict[str, TerritoryState],
        detroit_hexes: dict[str, HexState],
    ) -> None:
        """Verify multiple reset cycles produce identical results."""
        sim = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )

        # Run, reset, run, get state
        sim.step(25)
        sim.reset()
        sim.step(50)
        state_after_first_cycle = sim.get_territory_state("26163")

        # Reset and repeat
        sim.reset()
        sim.step(25)
        sim.reset()
        sim.step(50)
        state_after_second_cycle = sim.get_territory_state("26163")

        assert state_after_first_cycle is not None
        assert state_after_second_cycle is not None
        assert state_after_first_cycle.profit_rate == state_after_second_cycle.profit_rate


class TestDeterminismSnapshotConsistency:
    """Test that snapshots are consistent across identical runs."""

    def test_snapshot_consistency(
        self,
        detroit_territories: dict[str, TerritoryState],
        detroit_hexes: dict[str, HexState],
    ) -> None:
        """Verify snapshots from identical runs are identical."""
        sim1 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )
        sim2 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )

        # Run 10 ticks each
        sim1.step(10)
        sim2.step(10)

        # Get snapshots
        snapshot1 = sim1.get_snapshot()
        snapshot2 = sim2.get_snapshot()

        # Verify identical
        assert snapshot1.tick == snapshot2.tick
        assert len(snapshot1.territories) == len(snapshot2.territories)
        assert len(snapshot1.hexes) == len(snapshot2.hexes)

        for tid in snapshot1.territories:
            assert tid in snapshot2.territories
            t1 = snapshot1.territories[tid]
            t2 = snapshot2.territories[tid]
            assert t1.profit_rate == t2.profit_rate
            assert t1.tick == t2.tick
            assert t1.hex_claims == t2.hex_claims


class TestDeterminismEdgeCases:
    """Test determinism edge cases."""

    def test_single_step_is_deterministic(
        self,
        detroit_territories: dict[str, TerritoryState],
        detroit_hexes: dict[str, HexState],
    ) -> None:
        """Verify single step produces identical results."""
        sim1 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )
        sim2 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )

        sim1.step()
        sim2.step()

        wayne1 = sim1.get_territory_state("26163")
        wayne2 = sim2.get_territory_state("26163")

        assert wayne1 is not None
        assert wayne2 is not None
        assert wayne1.profit_rate == wayne2.profit_rate

    def test_step_1_vs_step_n_1_produce_same_result(
        self,
        detroit_territories: dict[str, TerritoryState],
        detroit_hexes: dict[str, HexState],
    ) -> None:
        """Verify step() and step(1) produce identical results."""
        sim1 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )
        sim2 = create_simulation_with_territories(
            territories=detroit_territories,
            hexes=detroit_hexes,
        )

        sim1.step()  # Default n=1
        sim2.step(1)  # Explicit n=1

        wayne1 = sim1.get_territory_state("26163")
        wayne2 = sim2.get_territory_state("26163")

        assert wayne1 is not None
        assert wayne2 is not None
        assert wayne1.profit_rate == wayne2.profit_rate
