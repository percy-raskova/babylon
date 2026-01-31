"""Babylon UI components.

This module provides the user interface components for the Babylon
simulation engine. Two visualization backends are available:

DearPyGui Backend (Legacy):
    dpg_runner: Main dashboard entry point with render loop.
    design_system: Color palette and styling constants.

PyQt6 Dashboard (God Mode):
    dashboard: H3 hexagonal map visualization with pydeck.

Example (DearPyGui)::

    from babylon.ui.dpg_runner import main
    main()

Example (PyQt6 Dashboard)::

    python -m babylon.ui.dashboard --demo
"""

from babylon.ui import dashboard, dpg_runner
from babylon.ui.design_system import BunkerPalette, DPGColors

__all__ = ["BunkerPalette", "DPGColors", "dashboard", "dpg_runner"]
