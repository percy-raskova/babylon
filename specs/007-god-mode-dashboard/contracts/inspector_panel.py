"""InspectorPanel interface contract.

This module defines the expected interface for the territory detail panel.
Implementation goes in src/babylon/ui/dashboard/inspector_panel.py.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from babylon.models.snapshots import SimulationSnapshot, TerritoryState


class InspectorPanelProtocol(Protocol):
    """Territory detail display panel interface.

    The InspectorPanel displays the "Value Tensor" (all numeric properties)
    of the currently selected territory. It appears on the right edge of
    the dashboard window (30% width per layout spec).

    Display modes:
    1. Territory selected: Show all TerritoryState properties
    2. No selection: Show "No territory selected" message
    3. Unclaimed hex: Show "No territory claims this hex" + H3 index
    4. Error state: Show error message with indicator

    Example:
        >>> panel = InspectorPanel(parent=window)
        >>> panel.display_territory(territory_state)
        >>> # User clicks unclaimed hex
        >>> panel.display_unclaimed("852a1072fffffff")
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create inspector panel widget.

        Args:
            parent: Parent widget.

        The panel is created with "No territory selected" initial state.
        Applies Bunker Constructivism theme (dark background, monospace text).
        """
        ...

    def display_territory(self, territory: TerritoryState) -> None:
        """Display territory details.

        Shows all properties from the "Value Tensor":
        - territory_id: FIPS code
        - controlling_polity: Controller ID
        - tick: Current tick number
        - profit_rate: As percentage (e.g., "42.0%")
        - equilibrium_r: As decimal (e.g., "0.50")
        - hex_count: Number of claimed hexes

        Args:
            territory: Territory state to display.
        """
        ...

    def display_no_selection(self) -> None:
        """Display 'No territory selected' message.

        Called when:
        - Dashboard opens (initial state)
        - User clicks map background (clears selection)
        """
        ...

    def display_unclaimed(self, h3_index: str) -> None:
        """Display 'No territory claims this hex' message.

        Called when user clicks a hex that no territory claims.
        Shows the H3 index for reference.

        Args:
            h3_index: The clicked H3 cell index.
        """
        ...

    def display_error(self, message: str) -> None:
        """Display error message with visual indicator.

        Per FR-015, errors are displayed gracefully without crashing.
        The panel shows the error message and adds a visual indicator
        (e.g., red border) to signal the error state.

        Args:
            message: Error description to display.
        """
        ...

    def update_from_snapshot(self, snapshot: SimulationSnapshot) -> None:
        """Update displayed territory from new snapshot.

        If a territory is currently selected, refreshes the display
        with updated values from the snapshot. If the territory no
        longer exists in the snapshot, clears the selection.

        Called by DashboardObserver on each tick.

        Args:
            snapshot: New simulation state.
        """
        ...


# Type alias for implementations
InspectorPanel = InspectorPanelProtocol

__all__ = ["InspectorPanelProtocol", "InspectorPanel"]
