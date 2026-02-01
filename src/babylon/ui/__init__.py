"""Babylon UI components.

This module provides the user interface components for the Babylon
simulation engine.

PyQt6 Dashboard (God Mode):
    dashboard: H3 hexagonal map visualization with pydeck.

Example (PyQt6 Dashboard)::

    python -m babylon.ui.dashboard --demo
"""

from babylon.ui import dashboard
from babylon.ui.design_system import BunkerPalette

__all__ = ["BunkerPalette", "dashboard"]
