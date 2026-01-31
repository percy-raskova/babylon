"""SimulationState protocol definition.

This protocol defines the read interface for simulation state.
GUI code should depend ONLY on this protocol, not on implementation details.

The protocol is defined here in the spec for documentation purposes.
The actual implementation will be in src/babylon/protocols/simulation_state.py

Implementation References
-------------------------
- Return types: See data-model.md for TerritoryState, SimulationSnapshot definitions
- Implementation: src/babylon/engine/simulation.py (Simulation class implements this)
- Snapshot creation: See plan.md#Hydration Flow for initialization sequence
- profit_rate computation: See research.md#5. Profit Rate Dynamics
- Usage examples: See quickstart.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    # Forward references to snapshot types (defined in data-model.md)
    # Actual imports will be from src/babylon/models/snapshots.py
    from babylon.models.snapshots import SimulationSnapshot, TerritoryState


@runtime_checkable
class SimulationState(Protocol):
    """Read interface to simulation state.

    This protocol defines how GUI code queries simulation state.
    All methods are read-only—they do not modify simulation state.

    The protocol enables:
    - GUI code to type-check against a stable interface
    - Simulation internals to evolve without breaking GUI
    - Multiple implementations (mock, real, replay)

    Example:
        >>> def render_map(sim: SimulationState) -> None:
        ...     snapshot = sim.get_snapshot()
        ...     for territory_id, state in snapshot.territories.items():
        ...         color = profit_rate_to_color(state.profit_rate)
        ...         render_hexes(state.hex_claims, color)
    """

    def get_current_tick(self) -> int:
        """Return the current tick number.

        Returns:
            Non-negative integer representing the current simulation tick.
            Tick 0 is the initial state before any step() calls.
        """
        ...

    def get_snapshot(self) -> SimulationSnapshot:
        """Return a complete snapshot of the current simulation state.

        The snapshot is immutable—modifying the returned object does not
        affect the simulation. The snapshot contains:
        - tick: Current tick number
        - territories: Dict of territory_id → TerritoryState
        - hexes: Dict of h3_index → HexState (invariant substrate)
        - edges: List of EdgeState (empty for MVP)

        Returns:
            SimulationSnapshot containing all state at the current tick.
        """
        ...

    def get_territory_state(self, territory_id: str) -> TerritoryState | None:
        """Return the state of a specific territory.

        Args:
            territory_id: Unique identifier for the territory (FIPS code for counties).

        Returns:
            TerritoryState if the territory exists, None otherwise.

        Example:
            >>> state = sim.get_territory_state("26163")  # Wayne County
            >>> if state:
            ...     print(f"Profit rate: {state.profit_rate}")
        """
        ...

    def get_hexes_for_territory(self, territory_id: str) -> set[str]:
        """Return the H3 indices claimed by a territory.

        This is a convenience method equivalent to:
            sim.get_territory_state(id).hex_claims

        Args:
            territory_id: Unique identifier for the territory.

        Returns:
            Set of H3 index strings. Empty set if territory not found or
            has no hex claims.
        """
        ...
