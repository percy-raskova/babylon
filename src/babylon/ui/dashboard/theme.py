"""Bunker Constructivism theme for God Mode Dashboard.

This module defines the visual theme constants and color utilities
following the ai-docs/design-system.yaml specification.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

# =============================================================================
# BUNKER CONSTRUCTIVISM COLOR PALETTE
# =============================================================================
# From ai-docs/design-system.yaml

BUNKER_CONSTRUCTIVISM = {
    "void": "#050505",  # Deep black base
    "wet_concrete": "#1a1a1a",  # Primary background
    "soot": "#2d2d2d",  # Secondary background
    "data_green": "#39FF14",  # High profit rate / success
    "phosphor_burn_red": "#D40000",  # Low profit rate / danger
    "amber_warning": "#ff8c00",  # Warnings
    "steel_gray": "#708090",  # Neutral UI chrome
}

# RGB tuples for color interpolation
DATA_GREEN_RGB = (57, 255, 20)  # #39FF14
PHOSPHOR_BURN_RED_RGB = (212, 0, 0)  # #D40000


# =============================================================================
# QT STYLESHEET (QSS)
# =============================================================================

QSS_THEME = """
QMainWindow {
    background-color: #1a1a1a;
}

QWidget {
    background-color: #1a1a1a;
    color: #39FF14;
    font-family: monospace;
}

QLabel {
    color: #39FF14;
    font-family: monospace;
    font-size: 12px;
}

QLabel#title {
    font-size: 14px;
    font-weight: bold;
}

QFrame#inspector {
    background-color: #2d2d2d;
    border-left: 2px solid #708090;
}

QFrame#inspector_error {
    background-color: #2d2d2d;
    border: 2px solid #D40000;
}

QSplitter::handle {
    background-color: #708090;
    width: 2px;
}

QStatusBar {
    background-color: #050505;
    color: #708090;
    font-family: monospace;
}

QStatusBar::item {
    border: none;
}
"""


# =============================================================================
# COLOR MAPPING FUNCTIONS
# =============================================================================


def profit_rate_to_rgb(rate: float) -> tuple[int, int, int]:
    """Map profit_rate [0,1] to RGB tuple.

    Linear interpolation between:
    - 0.0 -> phosphor_burn_red (212, 0, 0)
    - 1.0 -> data_green (57, 255, 20)

    Args:
        rate: Profit rate value, should be in [0.0, 1.0].
              Values outside this range are clamped.

    Returns:
        RGB tuple (r, g, b) with values in [0, 255].

    Example:
        >>> profit_rate_to_rgb(0.0)
        (212, 0, 0)
        >>> profit_rate_to_rgb(1.0)
        (57, 255, 20)
        >>> profit_rate_to_rgb(0.5)
        (134, 127, 10)
    """
    # Clamp to valid range
    rate = max(0.0, min(1.0, rate))

    low_r, low_g, low_b = PHOSPHOR_BURN_RED_RGB
    high_r, high_g, high_b = DATA_GREEN_RGB

    r = int(low_r + (high_r - low_r) * rate)
    g = int(low_g + (high_g - low_g) * rate)
    b = int(low_b + (high_b - low_b) * rate)

    return (r, g, b)


def profit_rate_to_hex(rate: float) -> str:
    """Map profit_rate [0,1] to hex color string.

    Args:
        rate: Profit rate value, should be in [0.0, 1.0].

    Returns:
        Hex color string (e.g., "#D40000").

    Example:
        >>> profit_rate_to_hex(0.0)
        '#d40000'
        >>> profit_rate_to_hex(1.0)
        '#39ff14'
    """
    r, g, b = profit_rate_to_rgb(rate)
    return f"#{r:02x}{g:02x}{b:02x}"


__all__ = [
    "BUNKER_CONSTRUCTIVISM",
    "DATA_GREEN_RGB",
    "PHOSPHOR_BURN_RED_RGB",
    "QSS_THEME",
    "profit_rate_to_rgb",
    "profit_rate_to_hex",
]
