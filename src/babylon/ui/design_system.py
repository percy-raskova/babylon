"""Design system constants for Bunker Constructivism aesthetic.

This module defines the color palette and styling constants used across
all Babylon UI components. The design system is inspired by Cold War
bunker aesthetics, terminal interfaces, and industrial design.

The palette conveys a sense of surveillance, decay, and urgency appropriate
for a simulation modeling systemic collapse.

Colors:
    Primary colors convey the fundamental states of the simulation:

    - ``void``: The absolute darkness of background (black)
    - ``data_green``: Healthy/positive metrics (terminal green)
    - ``phosphor_burn_red``: Critical/danger states (alarm red)
    - ``silver_dust``: Neutral text and labels (gray)
    - ``exposed_copper``: Warning states (amber/gold)
    - ``dark_metal``: Borders and grid lines (dark gray)

    Accent colors for specific purposes:

    - ``wet_concrete``: Header/panel backgrounds
    - ``grow_light_purple``: Narrative/title highlights
    - ``royal_blue``: Labor Aristocracy class
    - ``triumph_green``: Victory states (same as data_green)
    - ``warning_amber``: Ecological warning states

Example:
    >>> from babylon.ui.design_system import BunkerPalette
    >>> BunkerPalette.VOID
    '#050505'
    >>> BunkerPalette.DATA_GREEN
    '#39FF14'

See Also:
    ``ai-docs/design-system.yaml`` for the full design specification.
"""

from __future__ import annotations


class BunkerPalette:
    """Bunker Constructivism color palette.

    This class provides all color constants used in the Babylon UI.
    Colors are defined as hex strings suitable for CSS and ECharts.

    Class Attributes:
        VOID: Background black (#050505).
        DARK_METAL: Border/grid dark gray (#404040).
        SILVER_DUST: Neutral text gray (#C0C0C0).
        DATA_GREEN: Positive/healthy terminal green (#39FF14).
        PHOSPHOR_BURN_RED: Critical/danger alarm red (#D40000).
        EXPOSED_COPPER: Warning amber/gold (#FFD700).
        WET_CONCRETE: Header/panel dark gray (#1A1A1A).
        GROW_LIGHT_PURPLE: Narrative highlight purple (#9D00FF).
        ROYAL_BLUE: Labor Aristocracy class blue (#4169E1).
        TRIUMPH_GREEN: Victory green (alias for DATA_GREEN).
        WARNING_AMBER: Ecological warning amber (#B8860B).

    Example:
        >>> from babylon.ui.design_system import BunkerPalette
        >>> BunkerPalette.is_design_system_color("#39FF14")
        True
        >>> BunkerPalette.get_severity_color("critical")
        '#D40000'
    """

    # ==========================================================================
    # PRIMARY COLORS
    # ==========================================================================

    VOID: str = "#050505"
    """Background black - the absolute darkness underlying all UI elements."""

    DARK_METAL: str = "#404040"
    """Border and grid line color - industrial dark gray."""

    SILVER_DUST: str = "#C0C0C0"
    """Neutral text and label color - terminal gray."""

    DATA_GREEN: str = "#39FF14"
    """Positive/healthy metric color - phosphor terminal green."""

    PHOSPHOR_BURN_RED: str = "#D40000"
    """Critical/danger state color - alarm red."""

    EXPOSED_COPPER: str = "#FFD700"
    """Warning state color - oxidized copper amber."""

    # ==========================================================================
    # ACCENT COLORS
    # ==========================================================================

    WET_CONCRETE: str = "#1A1A1A"
    """Header and panel background - wet concrete gray."""

    GROW_LIGHT_PURPLE: str = "#9D00FF"
    """Narrative and title highlight - grow light purple."""

    ROYAL_BLUE: str = "#4169E1"
    """Labor Aristocracy class indicator - royal blue."""

    # ==========================================================================
    # SEMANTIC ALIASES
    # ==========================================================================

    TRIUMPH_GREEN: str = "#39FF14"
    """Victory state color - same as DATA_GREEN."""

    WARNING_AMBER: str = "#B8860B"
    """Ecological warning color - dark goldenrod."""

    # ==========================================================================
    # LOG LEVEL COLORS
    # ==========================================================================

    LOG_INFO: str = "#39FF14"
    """INFO log level - data green."""

    LOG_WARN: str = "#FFD700"
    """WARN log level - exposed copper."""

    LOG_ERROR: str = "#D40000"
    """ERROR log level - phosphor burn red."""

    # ==========================================================================
    # CLASS WEALTH TREND COLORS
    # ==========================================================================

    PW_COLOR: str = "#39FF14"
    """Periphery Worker (C001) - data green (the exploited)."""

    PC_COLOR: str = "#FFD700"
    """Comprador (C002) - exposed copper."""

    CB_COLOR: str = "#D40000"
    """Core Bourgeoisie (C003) - phosphor burn red (the exploiter)."""

    CW_COLOR: str = "#4169E1"
    """Labor Aristocracy (C004) - royal blue."""

    @classmethod
    def is_design_system_color(cls, color: str) -> bool:
        """Check if a color is part of the design system.

        Args:
            color: Hex color string to check.

        Returns:
            True if the color matches any design system color.
        """
        design_colors = {
            cls.VOID,
            cls.DARK_METAL,
            cls.SILVER_DUST,
            cls.DATA_GREEN,
            cls.PHOSPHOR_BURN_RED,
            cls.EXPOSED_COPPER,
            cls.WET_CONCRETE,
            cls.GROW_LIGHT_PURPLE,
            cls.ROYAL_BLUE,
            cls.WARNING_AMBER,
        }
        return color.upper() in {c.upper() for c in design_colors}

    @classmethod
    def get_severity_color(cls, severity: str) -> str:
        """Get color for a severity level.

        Args:
            severity: One of "info", "warn", "error", "critical".

        Returns:
            Hex color string for the severity level.
        """
        severity_map = {
            "info": cls.DATA_GREEN,
            "warn": cls.EXPOSED_COPPER,
            "warning": cls.EXPOSED_COPPER,
            "error": cls.PHOSPHOR_BURN_RED,
            "critical": cls.PHOSPHOR_BURN_RED,
        }
        return severity_map.get(severity.lower(), cls.SILVER_DUST)
