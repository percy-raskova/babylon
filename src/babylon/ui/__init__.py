"""Babylon UI components (NiceGUI-based).

This module provides the user interface components for the Babylon
simulation engine, built on NiceGUI with a "Cybernetic Terminal" aesthetic.

Components:
    ControlDeck: Simulation control panel with STEP, PLAY, PAUSE, RESET buttons.
    NarrativeTerminal: Typewriter-style narrative display with auto-scroll.
"""

from babylon.ui.controls import ControlDeck
from babylon.ui.terminal import NarrativeTerminal

__all__ = ["ControlDeck", "NarrativeTerminal"]
