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

# Piketty's empirical profit rate bounds for color normalization
# Real profit rates cluster in 3-8% range (see "Capital in the 21st Century")
PROFIT_RATE_MIN = 0.03  # 3% - recessionary floor (red)
PROFIT_RATE_MAX = 0.08  # 8% - prosperity ceiling (green)


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


def profit_rate_to_rgb(
    rate: float,
    *,
    use_realistic_range: bool = True,
) -> tuple[int, int, int]:
    """Map profit_rate to RGB tuple.

    Linear interpolation between phosphor_burn_red and data_green.

    By default, uses Piketty's empirical profit rate bounds (3-12%):
    - 0.03 (3%) -> phosphor_burn_red (212, 0, 0) - crisis
    - 0.12 (12%) -> data_green (57, 255, 20) - prosperity

    With use_realistic_range=False, uses raw [0,1] range for demo mode.

    Args:
        rate: Profit rate value (as decimal, e.g., 0.05 for 5%).
        use_realistic_range: If True (default), normalize to [3%, 12%] range.
                             If False, use raw [0, 1] range (for demo mode).

    Returns:
        RGB tuple (r, g, b) with values in [0, 255].

    Example:
        >>> profit_rate_to_rgb(0.03)  # 3% -> red (crisis)
        (212, 0, 0)
        >>> profit_rate_to_rgb(0.12)  # 12% -> green (prosperity)
        (57, 255, 20)
        >>> profit_rate_to_rgb(0.075)  # 7.5% -> middle
        (134, 127, 10)
        >>> profit_rate_to_rgb(0.5, use_realistic_range=False)  # Demo mode
        (134, 127, 10)
    """
    if use_realistic_range:
        # Normalize from realistic Piketty range [3%, 12%] to [0, 1]
        normalized = (rate - PROFIT_RATE_MIN) / (PROFIT_RATE_MAX - PROFIT_RATE_MIN)
    else:
        # Use raw input for demo mode
        normalized = rate

    # Clamp normalized value to [0, 1]
    normalized = max(0.0, min(1.0, normalized))

    low_r, low_g, low_b = PHOSPHOR_BURN_RED_RGB
    high_r, high_g, high_b = DATA_GREEN_RGB

    r = int(low_r + (high_r - low_r) * normalized)
    g = int(low_g + (high_g - low_g) * normalized)
    b = int(low_b + (high_b - low_b) * normalized)

    return (r, g, b)


def profit_rate_to_hex(
    rate: float,
    *,
    use_realistic_range: bool = True,
) -> str:
    """Map profit_rate to hex color string.

    Args:
        rate: Profit rate value (as decimal, e.g., 0.05 for 5%).
        use_realistic_range: If True (default), normalize to [3%, 12%] range.
                             If False, use raw [0, 1] range (for demo mode).

    Returns:
        Hex color string (e.g., "#D40000").

    Example:
        >>> profit_rate_to_hex(0.03)  # 3% -> red
        '#d40000'
        >>> profit_rate_to_hex(0.12)  # 12% -> green
        '#39ff14'
    """
    r, g, b = profit_rate_to_rgb(rate, use_realistic_range=use_realistic_range)
    return f"#{r:02x}{g:02x}{b:02x}"


__all__ = [
    "BUNKER_CONSTRUCTIVISM",
    "DATA_GREEN_RGB",
    "PHOSPHOR_BURN_RED_RGB",
    "PROFIT_RATE_MIN",
    "PROFIT_RATE_MAX",
    "QSS_THEME",
    "profit_rate_to_rgb",
    "profit_rate_to_hex",
]
