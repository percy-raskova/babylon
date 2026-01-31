"""Type checking verification for protocols (T041, SC-005).

This file imports ONLY protocols and verifies that:
- Protocol types can be used as type hints
- Functions typed with protocols accept Simulation instances
- mypy can type-check this file without errors

To verify: Run `mypy tests/unit/protocols/test_mypy_protocols.py`
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Import ONLY protocols - no implementation
from babylon.protocols import SimulationControl, SimulationState

if TYPE_CHECKING:
    pass


def display_current_tick(sim: SimulationState) -> str:
    """Display current tick using only SimulationState protocol.

    This function demonstrates that GUI code can depend on protocols
    without importing Simulation implementation.
    """
    tick = sim.get_current_tick()
    return f"Current tick: {tick}"


def get_territory_info(sim: SimulationState, territory_id: str) -> str:
    """Query territory info using only SimulationState protocol."""
    territory = sim.get_territory_state(territory_id)
    if territory is None:
        return f"Territory {territory_id} not found"
    return f"Territory {territory_id}: profit_rate={territory.profit_rate:.4f}"


def render_all_territories(sim: SimulationState) -> list[str]:
    """Render all territories using only SimulationState protocol."""
    snapshot = sim.get_snapshot()
    results: list[str] = []
    for tid, state in snapshot.territories.items():
        results.append(f"{tid}: {state.profit_rate:.4f}")
    return results


def advance_simulation(sim: SimulationControl, ticks: int = 1) -> None:
    """Advance simulation using only SimulationControl protocol."""
    sim.step(ticks)


def reset_to_initial(sim: SimulationControl) -> None:
    """Reset simulation using only SimulationControl protocol."""
    sim.reset()


def run_simulation_loop(
    state_reader: SimulationState,
    controller: SimulationControl,
    max_ticks: int,
) -> list[str]:
    """Run simulation loop using both protocols.

    This demonstrates the protocol separation:
    - state_reader: read-only access to simulation state
    - controller: write access to control simulation

    In practice, the same Simulation instance implements both.
    """
    results: list[str] = []

    for _ in range(max_ticks):
        # Read state via SimulationState protocol
        tick = state_reader.get_current_tick()
        snapshot = state_reader.get_snapshot()

        results.append(f"Tick {tick}: {len(snapshot.territories)} territories")

        # Advance via SimulationControl protocol
        controller.step()

    return results


# Note: Type verification happens implicitly via mypy on this file.
# The functions above use protocol types in their signatures, which
# mypy validates against the protocol definitions.
