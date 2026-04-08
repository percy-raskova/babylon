"""HexBridge for JavaScript-Python communication.

This module provides the HexBridge QObject that handles hex click events
from the pydeck map via QWebChannel and emits Qt signals.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from babylon.ui.dashboard.validators import is_valid_h3_index

if TYPE_CHECKING:
    from babylon.protocols import SimulationState

logger = logging.getLogger(__name__)


class HexBridge(QObject):
    """JavaScript-Python bridge for hex click events.

    This QObject is registered with QWebChannel and receives click events
    from the pydeck map. It resolves H3 indices to territories using the
    simulation's get_node_by_spatial_index() method.

    Signals:
        hex_selected: Emitted when any hex is clicked (H3 index).
        territory_selected: Emitted when a claimed hex is clicked (TerritoryState).
        unclaimed_hex_clicked: Emitted when an unclaimed hex is clicked (H3 index).
        selection_cleared: Emitted when background is clicked.

    Example:
        >>> bridge = HexBridge(simulation=sim)
        >>> bridge.territory_selected.connect(inspector.display_territory)
        >>> bridge.selection_cleared.connect(inspector.display_no_selection)
    """

    # Signals
    hex_selected = pyqtSignal(str)  # H3 index
    territory_selected = pyqtSignal(object)  # TerritoryState
    unclaimed_hex_clicked = pyqtSignal(str)  # H3 index
    selection_cleared = pyqtSignal()

    def __init__(
        self,
        simulation: SimulationState,
        parent: QObject | None = None,
    ) -> None:
        """Initialize HexBridge.

        Args:
            simulation: Simulation state for territory lookup.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._simulation = simulation
        self._selected_territory_id: str | None = None

        logger.debug("HexBridge initialized")

    @property
    def selected_territory_id(self) -> str | None:
        """Get the currently selected territory ID.

        Returns:
            Territory ID if a territory is selected, None otherwise.
        """
        return self._selected_territory_id

    @pyqtSlot(str)
    def on_hex_click(self, h3_index: str) -> None:
        """Handle hex click from JavaScript.

        This slot is called from JavaScript via QWebChannel when the user
        clicks a hexagon on the map.

        Args:
            h3_index: H3 index of the clicked hex.
        """
        logger.debug("Hex clicked: %s", h3_index)

        # Validate H3 index
        if not is_valid_h3_index(h3_index):
            logger.warning("Invalid H3 index received: %s", h3_index)
            return

        # Always emit hex_selected
        self.hex_selected.emit(h3_index)

        # Look up territory
        try:
            territory = self._simulation.get_node_by_spatial_index(h3_index)
        except ValueError as e:
            logger.warning("Error looking up territory: %s", e)
            return

        if territory is not None:
            # Claimed hex - emit territory_selected
            self._selected_territory_id = territory.territory_id
            self.territory_selected.emit(territory)
            logger.info(
                "Territory selected: %s (profit_rate=%.2f)",
                territory.territory_id,
                territory.profit_rate,
            )
        else:
            # Unclaimed hex
            self._selected_territory_id = None
            self.unclaimed_hex_clicked.emit(h3_index)
            logger.debug("Unclaimed hex clicked: %s", h3_index)

    @pyqtSlot()
    def on_background_click(self) -> None:
        """Handle background click from JavaScript.

        This slot is called from JavaScript via QWebChannel when the user
        clicks the map background (not on a hex).
        """
        logger.debug("Background clicked, clearing selection")

        self._selected_territory_id = None
        self.selection_cleared.emit()

    def update_simulation(self, simulation: SimulationState) -> None:
        """Update the simulation reference.

        This is useful when the simulation is replaced or reset.

        Args:
            simulation: New simulation state.
        """
        self._simulation = simulation
        logger.debug("HexBridge simulation reference updated")


__all__ = [
    "HexBridge",
]
