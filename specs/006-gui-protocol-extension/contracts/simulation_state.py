"""SimulationState protocol contract for GUI Protocol Extension.

This file defines the EXTENDED protocol interface for simulation state queries.
The Simulation class must implement all methods defined here.

Feature: 006-gui-protocol-extension
Date: 2026-01-31

Changes from baseline:
- Added get_node_by_spatial_index() for H3 hex -> Territory lookup
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
        >>> def on_hex_click(sim: SimulationState, h3_index: str) -> None:
        ...     territory = sim.get_node_by_spatial_index(h3_index)
        ...     if territory:
        ...         print(f"Clicked on {territory.territory_id}")
        ...     else:
        ...         print("Unclaimed hex")
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
        affect the simulation.

        Returns:
            SimulationSnapshot containing all state at the current tick.
        """
        ...

    def get_territory_state(self, territory_id: str) -> TerritoryState | None:
        """Return the state of a specific territory.

        Args:
            territory_id: Unique identifier for the territory (FIPS code).

        Returns:
            TerritoryState if the territory exists, None otherwise.
        """
        ...

    def get_hexes_for_territory(self, territory_id: str) -> set[str]:
        """Return the H3 indices claimed by a territory.

        Args:
            territory_id: Unique identifier for the territory.

        Returns:
            Set of H3 index strings. Empty set if territory not found.
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
