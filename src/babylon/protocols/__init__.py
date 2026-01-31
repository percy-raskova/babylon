"""Protocol definitions for the Babylon simulation engine.

This package defines the protocol interfaces that the GUI layer depends on.
By depending only on protocols (not implementations), the GUI code can:
- Type-check against stable interfaces
- Accept multiple implementations (real, mock, replay)
- Remain decoupled from simulation internals

Available protocols:
- SimulationState: Read-only interface for querying simulation state
- SimulationControl: Write interface for controlling simulation execution

Type aliases:
- ObserverCallback: Type for GUI observer callbacks

Usage:
    from babylon.protocols import SimulationState, SimulationControl, ObserverCallback

    def render_map(sim: SimulationState) -> None:
        snapshot = sim.get_snapshot()
        for territory_id, state in snapshot.territories.items():
            render_territory(territory_id, state)

    def step_simulation(sim: SimulationControl) -> None:
        sim.step()

    # GUI observer callback
    def on_tick(tick: int, snapshot: SimulationSnapshot) -> None:
        print(f"Tick {tick}: {len(snapshot.territories)} territories")

    sim.register_observer(on_tick)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from babylon.protocols.simulation_control import SimulationControl
from babylon.protocols.simulation_state import SimulationState

if TYPE_CHECKING:
    from babylon.models.snapshots import SimulationSnapshot

# Type alias for GUI observer callbacks (006-gui-protocol-extension)
# Callbacks receive frozen snapshot, not live reference
ObserverCallback = Callable[[int, "SimulationSnapshot"], None]

__all__ = [
    "SimulationState",
    "SimulationControl",
    "ObserverCallback",
]
