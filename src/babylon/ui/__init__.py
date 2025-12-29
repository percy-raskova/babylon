"""Babylon UI components (Dear PyGui-based).

This module provides the user interface components for the Babylon
simulation engine, built on Dear PyGui with a "Bunker Constructivism" aesthetic.

Components:
    dpg_runner: Main dashboard entry point with render loop.
    design_system: Color palette and styling constants.

Example:
    Run the dashboard::

        from babylon.ui.dpg_runner import main
        main()

    Or from command line::

        poetry run python -m babylon.ui.dpg_runner
"""

from babylon.ui import dpg_runner
from babylon.ui.design_system import BunkerPalette, DPGColors

__all__ = ["BunkerPalette", "DPGColors", "dpg_runner"]
