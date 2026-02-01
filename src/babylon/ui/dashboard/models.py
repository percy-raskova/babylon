"""Dashboard data models for God Mode visualization.

This module defines the internal data structures used by the dashboard
components for rendering and display. These models are derived from
SimulationSnapshot data on each update.

Feature: 007-god-mode-dashboard
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HexDisplayData(BaseModel):
    """Data for a single hex in the map display.

    This is the internal format used by MapViewport for pydeck rendering.
    Derived from TerritoryState on each update.

    Attributes:
        h3: H3 index (15-char hex string at resolution 5).
        color: RGB color tuple derived from profit_rate.
        profit_rate: Actual profit rate [0.0, 1.0] for tooltip display.
        territory_id: Territory that claims this hex, or None if unclaimed.
        selected: True if part of currently selected territory.
    """

    model_config = ConfigDict(frozen=True)

    h3: str = Field(description="H3 index (15-char hex string)")
    color: tuple[int, int, int] = Field(description="RGB color from profit_rate")
    profit_rate: float = Field(ge=0.0, le=1.0, description="Actual profit rate [0.0, 1.0]")
    territory_id: str | None = Field(default=None, description="Territory claiming this hex")
    selected: bool = Field(default=False, description="Part of selected territory")


class InspectorDisplayData(BaseModel):
    """Formatted data for the inspector panel.

    Converts TerritoryState to display-ready strings for the Value Tensor.

    Attributes:
        territory_id: FIPS code identifier.
        controlling_polity: Controller identifier.
        tick: Current simulation tick.
        profit_rate_display: Formatted profit rate (e.g., "42.0%").
        equilibrium_r_display: Formatted equilibrium R (e.g., "0.50").
        hex_count: Number of hexes claimed by this territory.
    """

    model_config = ConfigDict(frozen=True)

    territory_id: str = Field(description="5-digit FIPS code")
    controlling_polity: str = Field(description="Controller identifier")
    tick: int = Field(ge=0, description="Simulation tick")
    profit_rate_display: str = Field(description="Formatted profit rate")
    equilibrium_r_display: str = Field(description="Formatted equilibrium R")
    hex_count: int = Field(ge=0, description="Number of claimed hexes")


class ConnectionStatus(BaseModel):
    """Dashboard connection state.

    Tracks the connection to the simulation for status bar display
    and reconnection logic.

    Attributes:
        connected: Whether connected to simulation.
        last_tick: Last received tick number, or None if never received.
        error_message: Most recent error message, or None if no error.
    """

    model_config = ConfigDict(frozen=True)

    connected: bool = Field(description="Connected to simulation")
    last_tick: int | None = Field(default=None, description="Last received tick or None")
    error_message: str | None = Field(default=None, description="Most recent error or None")


__all__ = [
    "HexDisplayData",
    "InspectorDisplayData",
    "ConnectionStatus",
]
