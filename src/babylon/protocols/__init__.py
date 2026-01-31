"""Protocol definitions for the Babylon simulation engine.

This package defines the protocol interfaces that the GUI layer depends on.
By depending only on protocols (not implementations), the GUI code can:
- Type-check against stable interfaces
- Accept multiple implementations (real, mock, replay)
- Remain decoupled from simulation internals

Available protocols:
- SimulationState: Read-only interface for querying simulation state
- SimulationControl: Write interface for controlling simulation execution

Usage:
    from babylon.protocols import SimulationState, SimulationControl

    def render_map(sim: SimulationState) -> None:
        snapshot = sim.get_snapshot()
        for territory_id, state in snapshot.territories.items():
            render_territory(territory_id, state)

    def step_simulation(sim: SimulationControl) -> None:
        sim.step()
"""

from babylon.protocols.simulation_control import SimulationControl
from babylon.protocols.simulation_state import SimulationState

__all__ = [
    "SimulationState",
    "SimulationControl",
]
