"""Testing utilities for God Mode Dashboard.

This module provides MockSimulation and helper functions for testing
dashboard components without a real simulation engine.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from babylon.models.snapshots import (
    HexState,
    SimulationSnapshot,
    TerritoryState,
)
from babylon.protocols import ObserverCallback

if TYPE_CHECKING:
    pass

# H3 index pattern: 15-character hexadecimal string
H3_INDEX_PATTERN = re.compile(r"^[0-9a-f]{15}$")


class MockSimulation:
    """Mock implementation of SimulationState and SimulationControl protocols.

    This mock provides a controllable simulation for testing dashboard
    components. It supports:
    - Configurable initial territories with profit rates
    - Observer registration/notification
    - Step and reset operations
    - Spatial lookup via H3 index

    Example:
        >>> mock = MockSimulation.with_detroit_territories()
        >>> snapshot = mock.get_snapshot()
        >>> len(snapshot.territories)
        3
        >>> mock.step()
        >>> mock.get_current_tick()
        1
    """

    def __init__(
        self,
        territories: dict[str, TerritoryState] | None = None,
        hexes: dict[str, HexState] | None = None,
    ) -> None:
        """Initialize MockSimulation with optional pre-configured state.

        Args:
            territories: Initial territory states. Defaults to empty.
            hexes: Initial hex states. Defaults to empty.
        """
        self._tick = 0
        self._territories = territories or {}
        self._hexes = hexes or {}
        # Use list[object] to support both ObserverCallback and SimulationObserver protocol
        self._observers: list[object] = []
        self._initial_territories = dict(self._territories)
        self._initial_hexes = dict(self._hexes)

        # Build spatial index: h3_index -> territory_id
        self._spatial_index: dict[str, str] = {}
        for territory_id, territory in self._territories.items():
            for h3_idx in territory.hex_claims:
                self._spatial_index[h3_idx.lower()] = territory_id

    # =========================================================================
    # SimulationState Protocol Methods
    # =========================================================================

    def get_current_tick(self) -> int:
        """Return the current tick number."""
        return self._tick

    def get_snapshot(self) -> SimulationSnapshot:
        """Return a complete snapshot of the current simulation state."""
        return SimulationSnapshot(
            tick=self._tick,
            territories=dict(self._territories),
            hexes=dict(self._hexes),
            edges=[],
        )

    def get_territory_state(self, territory_id: str) -> TerritoryState | None:
        """Return the state of a specific territory."""
        return self._territories.get(territory_id)

    def get_territory(self, territory_id: str) -> TerritoryState | None:
        """Alias for get_territory_state for convenience.

        Args:
            territory_id: FIPS code of the territory.

        Returns:
            TerritoryState if found, None otherwise.
        """
        return self._territories.get(territory_id)

    def get_hexes_for_territory(self, territory_id: str) -> set[str]:
        """Return the H3 indices claimed by a territory."""
        territory = self._territories.get(territory_id)
        if territory is None:
            return set()
        return set(territory.hex_claims)

    def get_node_by_spatial_index(self, h3_index: str) -> TerritoryState | None:
        """Return the territory that claims a specific H3 hex.

        Args:
            h3_index: H3 cell index (15-character lowercase hex string).

        Returns:
            TerritoryState if a territory claims this hex, None otherwise.

        Raises:
            ValueError: If h3_index is not a valid H3 cell index.
        """
        h3_lower = h3_index.lower()
        if not H3_INDEX_PATTERN.match(h3_lower):
            msg = f"Invalid H3 index: '{h3_index}'"
            raise ValueError(msg)

        territory_id = self._spatial_index.get(h3_lower)
        if territory_id is None:
            return None
        return self._territories.get(territory_id)

    # =========================================================================
    # SimulationControl Protocol Methods
    # =========================================================================

    def step(self, n: int = 1) -> None:
        """Advance the simulation by n ticks.

        Args:
            n: Number of ticks to advance. Must be positive.

        Raises:
            ValueError: If n <= 0.
        """
        if n <= 0:
            msg = f"n must be positive, got {n}"
            raise ValueError(msg)

        for _ in range(n):
            self._tick += 1
            # Notify all observers with frozen snapshot
            snapshot = self.get_snapshot()
            for observer in self._observers:
                # Support both ObserverCallback (callable) and SimulationObserver (has on_tick)
                if hasattr(observer, "on_tick"):
                    # SimulationObserver protocol - call on_tick(previous, new)
                    observer.on_tick(None, snapshot)
                elif callable(observer):
                    # ObserverCallback - call directly
                    observer(self._tick, snapshot)

    def reset(self) -> None:
        """Reset simulation to initial state (tick 0)."""
        self._tick = 0
        self._territories = dict(self._initial_territories)
        self._hexes = dict(self._initial_hexes)
        # Rebuild spatial index
        self._spatial_index.clear()
        for territory_id, territory in self._territories.items():
            for h3_idx in territory.hex_claims:
                self._spatial_index[h3_idx.lower()] = territory_id

    def register_observer(self, observer: ObserverCallback | object) -> None:
        """Register a callback or observer for tick notifications.

        Supports both ObserverCallback (simple function) and SimulationObserver
        (protocol with on_tick method).

        Args:
            observer: Function or observer object to notify after each tick.
        """
        if observer not in self._observers:
            self._observers.append(observer)

    def unregister_observer(self, observer: ObserverCallback | object) -> None:
        """Remove a previously registered callback or observer.

        Args:
            observer: The callback function or observer to remove.
        """
        if observer in self._observers:
            self._observers.remove(observer)

    # =========================================================================
    # Test Helper Methods
    # =========================================================================

    def set_territory_profit_rate(self, territory_id: str, profit_rate: float) -> None:
        """Update a territory's profit rate for testing.

        This creates a new TerritoryState with the updated profit_rate
        while preserving other fields.

        Args:
            territory_id: Territory to update.
            profit_rate: New profit rate [0.0, 1.0].

        Raises:
            KeyError: If territory_id does not exist.
            ValueError: If profit_rate is out of range.
        """
        if territory_id not in self._territories:
            msg = f"Territory not found: {territory_id}"
            raise KeyError(msg)

        old = self._territories[territory_id]
        self._territories[territory_id] = TerritoryState(
            territory_id=old.territory_id,
            controlling_polity=old.controlling_polity,
            hex_claims=old.hex_claims,
            tick=self._tick,
            profit_rate=profit_rate,
            equilibrium_r=old.equilibrium_r,
        )

    def add_territory(self, territory: TerritoryState) -> None:
        """Add a territory to the simulation.

        Args:
            territory: TerritoryState to add.
        """
        self._territories[territory.territory_id] = territory
        for h3_idx in territory.hex_claims:
            self._spatial_index[h3_idx.lower()] = territory.territory_id

    @property
    def observers(self) -> list[object]:
        """Return list of registered observers (for testing)."""
        return list(self._observers)

    @classmethod
    def with_detroit_territories(cls) -> MockSimulation:
        """Create a MockSimulation pre-populated with Detroit-area territories.

        Creates three counties with representative H3 hexes and realistic
        profit rates within Piketty's empirical range (3-8%):
        - 26163 (Wayne County): High profit rate (0.075 = 7.5%)
        - 26125 (Oakland County): Medium profit rate (0.055 = 5.5%)
        - 26099 (Macomb County): Low profit rate (0.035 = 3.5%)

        Returns:
            MockSimulation with Detroit territories configured.
        """
        # Real H3 indices at resolution 5 for Detroit metropolitan area
        # Generated from actual Detroit coordinates using h3.latlng_to_cell()
        # Wayne County: Downtown Detroit (42.3314, -83.0458) + neighbors
        wayne_hexes = frozenset(
            [
                "852ab2c7fffffff",  # Detroit center
                "852ab2c3fffffff",  # Neighbor
                "852ab2cffffffff",  # Neighbor
                "852ab21bfffffff",  # Neighbor
            ]
        )
        # Oakland County: Pontiac area (42.6389, -83.2911) + neighbor
        oakland_hexes = frozenset(
            [
                "852ab2dbfffffff",  # Pontiac center
                "85274daffffffff",  # Neighbor
            ]
        )
        # Macomb County: Warren area (42.6256, -82.9319)
        macomb_hexes = frozenset(
            [
                "852ab66ffffffff",  # Warren center
            ]
        )

        # Realistic profit rates within Piketty's empirical range (3-8%)
        # Wayne (urban core): higher economic activity -> higher profit rate
        # Macomb (outer suburban): lower economic density -> lower profit rate
        territories = {
            "26163": TerritoryState(
                territory_id="26163",
                controlling_polity="26163",
                hex_claims=wayne_hexes,
                tick=0,
                profit_rate=0.075,  # 7.5% - high (green)
                equilibrium_r=0.065,
            ),
            "26125": TerritoryState(
                territory_id="26125",
                controlling_polity="26125",
                hex_claims=oakland_hexes,
                tick=0,
                profit_rate=0.055,  # 5.5% - medium (amber)
                equilibrium_r=0.055,
            ),
            "26099": TerritoryState(
                territory_id="26099",
                controlling_polity="26099",
                hex_claims=macomb_hexes,
                tick=0,
                profit_rate=0.035,  # 3.5% - low (red)
                equilibrium_r=0.04,
            ),
        }

        hexes = {}
        for territory in territories.values():
            for h3_idx in territory.hex_claims:
                hexes[h3_idx] = HexState(h3_index=h3_idx)

        return cls(territories=territories, hexes=hexes)


__all__ = [
    "MockSimulation",
]
