"""SimulationState protocol definition.

This protocol defines the read interface for simulation state.
GUI code should depend ONLY on this protocol, not on implementation details.

The protocol enables:
- GUI code to type-check against a stable interface
- Simulation internals to evolve without breaking GUI
- Multiple implementations (mock, real, replay)

Implementation:
    The Simulation class in src/babylon/engine/simulation.py implements this protocol.

See Also:
    - data-model.md: TerritoryState, SimulationSnapshot definitions
    - plan.md#Hydration Flow: Initialization sequence
    - research.md#5: Profit rate dynamics
    - quickstart.md: Usage examples

Feature 006-gui-protocol-extension:
    Added get_node_by_spatial_index() method for H3 hex -> Territory lookup.
    Enables GUI map click handling via pydeck H3HexagonLayer events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from babylon.models.snapshots import SimulationSnapshot, TerritoryState


@runtime_checkable
class SimulationState(Protocol):
    """Read interface to simulation state with spatial query support.

    This protocol defines how GUI code queries simulation state,
    including spatial lookups by H3 hex index.

    All methods are read-only - they do not modify simulation state.

    Example:
        >>> def render_map(sim: SimulationState) -> None:
        ...     snapshot = sim.get_snapshot()
        ...     for territory_id, state in snapshot.territories.items():
        ...         color = profit_rate_to_color(state.profit_rate)
        ...         render_hexes(state.hex_claims, color)
        ...
        >>> def on_hex_click(sim: SimulationState, h3_index: str) -> None:
        ...     territory = sim.get_node_by_spatial_index(h3_index)
        ...     if territory:
        ...         print(f"Clicked on {territory.territory_id}")
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

        The snapshot is immutable - modifying the returned object does not
        affect the simulation. The snapshot contains:
        - tick: Current tick number
        - territories: Dict of territory_id -> TerritoryState
        - hexes: Dict of h3_index -> HexState (invariant substrate)
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

    def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None:
        """Return the territory that claims a specific H3 hex.

        This method bridges the spatial representation (H3 hexes used by
        map visualization like pydeck) to the simulation's territory model.

        Args:
            h3_index: H3 cell index (15-character lowercase hex string).

        Returns:
            TerritoryState if a territory claims this hex, None otherwise.

        Raises:
            ValueError: If h3_index is not a valid H3 cell index.

        Example:
            >>> # User clicks on map, pydeck returns H3 index
            >>> h3_index = "852a1072fffffff"
            >>> territory = sim.get_node_by_spatial_index(h3_index)
            >>> if territory:
            ...     show_territory_details(territory)
            ... else:
            ...     show_unclaimed_message()

        Note:
            If multiple territories claim the same hex (data error),
            the first match is returned. This should not occur in
            well-formed simulation data.
        """
        ...
