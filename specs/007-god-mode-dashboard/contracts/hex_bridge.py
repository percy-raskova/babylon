"""HexBridge interface contract.

This module defines the expected interface for the QWebChannel bridge.
Implementation goes in src/babylon/ui/dashboard/hex_bridge.py.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PyQt6.QtCore import pyqtSignal

    from babylon.protocols import SimulationState


class HexBridgeProtocol(Protocol):
    """QWebChannel bridge for hex click handling.

    The HexBridge is a QObject registered with QWebChannel that receives
    hex click events from the pydeck JavaScript layer and resolves them
    to territories using SimulationState.get_node_by_spatial_index().

    Data flow:
    1. User clicks hex in pydeck map
    2. JavaScript calls bridge.on_hex_click(h3_index)
    3. HexBridge resolves H3 → Territory via SimulationState
    4. Emits territory_selected or unclaimed_hex signal

    Example:
        >>> bridge = HexBridge(simulation_state)
        >>> channel = QWebChannel(web_view.page())
        >>> channel.registerObject("bridge", bridge)
        >>> bridge.territory_selected.connect(inspector.display_territory)
        >>> bridge.unclaimed_hex.connect(inspector.display_unclaimed)
    """

    # Signal emitted when user clicks a hex claimed by a territory
    # Payload is TerritoryState
    territory_selected: pyqtSignal  # pyqtSignal(TerritoryState)

    # Signal emitted when user clicks a hex not claimed by any territory
    # Payload is the H3 index string
    unclaimed_hex: pyqtSignal  # pyqtSignal(str)

    # Signal emitted when user clicks map background (not on any hex)
    selection_cleared: pyqtSignal  # pyqtSignal()

    def __init__(self, simulation_state: SimulationState) -> None:
        """Create hex bridge.

        Args:
            simulation_state: SimulationState protocol for territory lookup.
        """
        ...

    def on_hex_click(self, h3_index: str) -> None:
        """Handle hex click from JavaScript.

        This is a Qt slot decorated with @pyqtSlot(str).
        Called by JavaScript via QWebChannel when user clicks a hex.

        Args:
            h3_index: H3 cell index (15-char hex string).

        Behavior:
        1. Validate H3 index format
        2. Call simulation_state.get_node_by_spatial_index(h3_index)
        3. If territory found: emit territory_selected(territory)
        4. If no territory: emit unclaimed_hex(h3_index)
        5. If invalid H3: log warning, no signal

        Per FR-009: Uses SimulationState.get_node_by_spatial_index()
        Per FR-015: Exceptions logged, not propagated
        """
        ...

    def on_background_click(self) -> None:
        """Handle background click from JavaScript.

        This is a Qt slot decorated with @pyqtSlot().
        Called by JavaScript via QWebChannel when user clicks map background.

        Emits selection_cleared signal.
        """
        ...


# Type alias for implementations
HexBridge = HexBridgeProtocol

__all__ = ["HexBridgeProtocol", "HexBridge"]
