"""God Mode Dashboard - Real-time simulation visualization.

This package provides a PyQt6-based dashboard for visualizing the Babylon
simulation state using H3 hexagonal maps rendered via pydeck.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from babylon.ui.dashboard.hex_bridge import HexBridge
from babylon.ui.dashboard.inspector_panel import InspectorPanel
from babylon.ui.dashboard.main_window import DashboardWindow
from babylon.ui.dashboard.map_viewport import MapViewport
from babylon.ui.dashboard.observer import DashboardObserver
from babylon.ui.dashboard.tensor_consumer import (
    TensorConsumer,
    TensorConsumerMixin,
    TensorPrimitive,
)

__all__ = [
    "DashboardObserver",
    "DashboardWindow",
    "HexBridge",
    "InspectorPanel",
    "MapViewport",
    "TensorConsumer",
    "TensorConsumerMixin",
    "TensorPrimitive",
]
