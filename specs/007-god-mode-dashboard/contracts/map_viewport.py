"""MapViewport interface contract.

This module defines the expected interface for the H3 hexagonal map component.
Implementation goes in src/babylon/ui/dashboard/map_viewport.py.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import QWidget

    from babylon.models.snapshots import SimulationSnapshot


class MapViewportProtocol(Protocol):
    """H3 hexagonal map visualization interface.

    The MapViewport renders the Detroit region as a grid of H3 hexagons
    colored by profit_rate. It:
    1. Generates pydeck HTML for initial render
    2. Updates hex colors incrementally via JavaScript
    3. Handles hex click events via QWebChannel
    4. Highlights selected territory hexes

    Implementation uses:
    - QWebEngineView for Chromium-based rendering
    - pydeck.Deck with H3HexagonLayer
    - QWebChannel for JavaScript-Python bridge

    Example:
        >>> viewport = MapViewport(parent=window)
        >>> viewport.initialize(snapshot)
        >>> viewport.hex_clicked.connect(on_hex_clicked)
    """

    # Signal emitted when user clicks a hex
    # Payload is the H3 index string (15-char hex)
    hex_clicked: pyqtSignal  # pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create map viewport widget.

        Args:
            parent: Parent widget.

        The constructor creates the QWebEngineView but does not load content.
        Call initialize() with a snapshot to render the map.
        """
        ...

    def initialize(self, snapshot: SimulationSnapshot) -> None:
        """Initialize map with simulation snapshot.

        This generates the full pydeck HTML and loads it into QWebEngineView.
        Call this once at startup, then use update_colors() for updates.

        Args:
            snapshot: Initial simulation state.

        The generated HTML includes:
        - pydeck runtime JavaScript
        - H3HexagonLayer with all hexes
        - QWebChannel bridge script
        - Click event handler
        """
        ...

    def update_colors(self, snapshot: SimulationSnapshot) -> None:
        """Update hex colors from simulation snapshot.

        This uses incremental JSON update (FR-011) instead of regenerating HTML.
        Called by DashboardObserver on each tick.

        Args:
            snapshot: Current simulation state.

        Implementation:
        1. Extract territory colors from snapshot
        2. Build JSON data array
        3. Call deck.setProps() via evaluateJavaScript()
        """
        ...

    def highlight_territory(self, territory_id: str) -> None:
        """Highlight all hexes belonging to a territory.

        Adds visual indicator (border or color shift) per FR-014.
        Previous highlight is automatically cleared.

        Args:
            territory_id: FIPS code of territory to highlight.
        """
        ...

    def clear_highlight(self) -> None:
        """Remove all highlights.

        Called when selection is cleared (background click).
        """
        ...


# Type alias for implementations
MapViewport = MapViewportProtocol

__all__ = ["MapViewportProtocol", "MapViewport"]
