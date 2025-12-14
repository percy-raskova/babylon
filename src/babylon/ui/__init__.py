"""Babylon UI components (NiceGUI-based).

This module provides the user interface components for the Babylon
simulation engine, built on NiceGUI with a "Cybernetic Terminal" aesthetic.

Components:
    ControlDeck: Simulation control panel with STEP, PLAY, PAUSE, RESET buttons.
    NarrativeTerminal: Typewriter-style narrative display with auto-scroll.
    SystemLog: Raw event log with instant display (NO typewriter animation).
    TrendPlotter: Real-time EChart line graph for simulation metrics.
"""

from babylon.ui.components import SystemLog, TrendPlotter
from babylon.ui.controls import ControlDeck
from babylon.ui.terminal import NarrativeTerminal

__all__ = ["ControlDeck", "NarrativeTerminal", "SystemLog", "TrendPlotter"]
