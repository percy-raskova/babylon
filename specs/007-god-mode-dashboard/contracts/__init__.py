"""Interface contracts for God Mode Dashboard.

These protocols define the expected interfaces for dashboard components.
Implementations go in src/babylon/ui/dashboard/.

Feature: 007-god-mode-dashboard
"""

from .dashboard_window import DashboardWindow, DashboardWindowProtocol
from .hex_bridge import HexBridge, HexBridgeProtocol
from .inspector_panel import InspectorPanel, InspectorPanelProtocol
from .map_viewport import MapViewport, MapViewportProtocol

__all__ = [
    "DashboardWindow",
    "DashboardWindowProtocol",
    "HexBridge",
    "HexBridgeProtocol",
    "InspectorPanel",
    "InspectorPanelProtocol",
    "MapViewport",
    "MapViewportProtocol",
]
