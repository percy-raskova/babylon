"""DashboardWindow main application window.

This module provides the main window that assembles all dashboard components:
MapViewport, InspectorPanel, HexBridge, and status bar.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStatusBar,
    QWidget,
)

from babylon.ui.dashboard.hex_bridge import HexBridge
from babylon.ui.dashboard.inspector_panel import InspectorPanel
from babylon.ui.dashboard.map_viewport import MapViewport
from babylon.ui.dashboard.observer import DashboardObserver
from babylon.ui.dashboard.theme import QSS_THEME

if TYPE_CHECKING:
    from PyQt6.QtGui import QCloseEvent

    from babylon.models.snapshots import SimulationSnapshot, TerritoryState
    from babylon.protocols import SimulationState

logger = logging.getLogger(__name__)

# Window dimensions per layout spec
MIN_WINDOW_WIDTH = 1460
MIN_WINDOW_HEIGHT = 820


class DashboardWindow(QMainWindow):
    """Main dashboard window with map and inspector panels.

    This window provides the complete God Mode Dashboard interface:
    - Left panel (70%): MapViewport with H3 hexagonal map
    - Right panel (30%): InspectorPanel with territory details
    - Status bar: Connection status indicator

    The window connects all components via signals:
    - HexBridge.territory_selected -> InspectorPanel.display_territory
    - HexBridge.unclaimed_hex_clicked -> InspectorPanel.display_unclaimed
    - HexBridge.selection_cleared -> InspectorPanel.display_no_selection

    Example:
        >>> window = DashboardWindow(simulation=sim)
        >>> window.show()
    """

    def __init__(
        self,
        simulation: SimulationState,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize DashboardWindow.

        Args:
            simulation: Simulation state and control interface.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._simulation = simulation

        # Set window properties
        self.setWindowTitle("Babylon - God Mode Dashboard")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # Apply Bunker Constructivism theme
        self.setStyleSheet(QSS_THEME)

        # Create central widget with splitter layout
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(splitter)

        # Create MapViewport (left panel - 70%)
        self._map_viewport = MapViewport(parent=splitter)

        # Create InspectorPanel (right panel - 30%)
        self._inspector_panel = InspectorPanel(parent=splitter)

        # Set splitter proportions (70/30)
        splitter.setSizes([int(MIN_WINDOW_WIDTH * 0.7), int(MIN_WINDOW_WIDTH * 0.3)])

        # Create HexBridge for click handling
        self._hex_bridge = HexBridge(simulation=simulation, parent=self)

        # Connect signals
        self._connect_signals()

        # Initialize map with simulation state
        self._map_viewport.initialize(simulation)
        self._map_viewport.register_bridge(self._hex_bridge)

        # Create status bar
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._update_status("Connected", tick=simulation.get_current_tick())

        # Create and register DashboardObserver (T040)
        self._observer = DashboardObserver(simulation=simulation, parent=self)
        self._observer.tick_processed.connect(self.update_from_snapshot)
        self._register_observer()

        logger.info("DashboardWindow initialized")

    def _register_observer(self) -> None:
        """Register the dashboard observer with the simulation."""
        if hasattr(self._simulation, "register_observer"):
            self._simulation.register_observer(self._observer)
            logger.debug("Observer registered with simulation")

    def _unregister_observer(self) -> None:
        """Unregister the dashboard observer from the simulation."""
        if hasattr(self._simulation, "unregister_observer"):
            self._simulation.unregister_observer(self._observer)
            logger.debug("Observer unregistered from simulation")

    def _connect_signals(self) -> None:
        """Connect HexBridge signals to InspectorPanel methods."""
        # Territory selected -> show territory details
        self._hex_bridge.territory_selected.connect(self._on_territory_selected)

        # Unclaimed hex clicked -> show unclaimed message
        self._hex_bridge.unclaimed_hex_clicked.connect(self._inspector_panel.display_unclaimed)

        # Background clicked -> clear selection
        self._hex_bridge.selection_cleared.connect(self._inspector_panel.display_no_selection)

        logger.debug("Dashboard signals connected")

    def _on_territory_selected(self, territory: TerritoryState) -> None:
        """Handle territory selection.

        Args:
            territory: Selected territory state.
        """
        # Update inspector panel
        self._inspector_panel.display_territory(territory)

        # Highlight selected territory on map
        self._map_viewport.highlight_territory(territory.territory_id)

        logger.debug("Territory selected: %s", territory.territory_id)

    def update_from_snapshot(self, tick: int, snapshot: SimulationSnapshot) -> None:
        """Update dashboard from simulation snapshot.

        This method is called by DashboardObserver on each tick.

        Args:
            tick: Current tick number.
            snapshot: Simulation snapshot.
        """
        # Update map colors
        self._map_viewport.update_colors(snapshot)

        # Update status bar
        self._update_status("Connected", tick=tick)

        # If a territory is selected, refresh inspector with new data
        selected_id = self._hex_bridge.selected_territory_id
        if selected_id:
            territory = snapshot.territories.get(selected_id)
            if territory:
                self._inspector_panel.display_territory(territory)

        logger.debug("Dashboard updated for tick %d", tick)

    def _update_status(self, status: str, tick: int | None = None) -> None:
        """Update status bar message.

        Args:
            status: Connection status text.
            tick: Optional tick number to display.
        """
        message = f"{status} | Tick: {tick}" if tick is not None else status
        self._status_bar.showMessage(message)
        logger.debug("Status: %s", message)

    def set_connection_error(self, message: str) -> None:
        """Display connection error state.

        Args:
            message: Error message to display.
        """
        self._inspector_panel.display_error(message)
        self._update_status(f"Error: {message}")
        logger.error("Connection error: %s", message)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Handle window close event.

        Unregisters observer from simulation (FR-012).
        """
        logger.info("DashboardWindow closing")
        self._unregister_observer()
        super().closeEvent(event)

    @property
    def map_viewport(self) -> MapViewport:
        """Get the MapViewport widget."""
        return self._map_viewport

    @property
    def inspector_panel(self) -> InspectorPanel:
        """Get the InspectorPanel widget."""
        return self._inspector_panel

    @property
    def hex_bridge(self) -> HexBridge:
        """Get the HexBridge instance."""
        return self._hex_bridge


__all__ = [
    "DashboardWindow",
    "MIN_WINDOW_WIDTH",
    "MIN_WINDOW_HEIGHT",
]
