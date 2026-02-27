"""Type definitions for the spatial economic substrate module.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Defines frozen Pydantic models for the tri-county H3 hex mesh economic
substrate covering Wayne (26163), Oakland (26125), and Macomb (26099)
counties in southeastern Michigan.

Models:
    - TractWeight: Census tract demographic weight for allocation.
    - HexEconomicState: Per-hex economic state at a single tick.
    - HexGrid: Collection of all hexes with resolution hierarchy.
    - SubstrateConfig: Configuration for the spatial substrate.
    - BoundaryFlowRegister: Tracks value flows crossing tri-county boundary.

See Also:
    :mod:`babylon.economics.tensor_hierarchy.types`: Level 1/2 tensor types.
    :mod:`babylon.economics.tensor`: Level 0 ValueTensor4x3 primitive.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =============================================================================
# CONSTANTS
# =============================================================================

TRI_COUNTY_FIPS: frozenset[str] = frozenset({"26163", "26125", "26099"})
"""Valid FIPS codes for the tri-county study area.

- 26163: Wayne County (Detroit)
- 26125: Oakland County
- 26099: Macomb County
"""

CONSERVATION_TOLERANCE: float = 1e-10
"""Absolute tolerance for conservation invariant checks."""

# =============================================================================
# TRACT WEIGHT
# =============================================================================


class TractWeight(BaseModel):
    """Census tract demographic weight for economic allocation.

    Used to disaggregate county-level QCEW economic data to individual
    H3 hexes via tract population and employment shares.

    Args:
        tract_geoid: 11-character Census tract GEOID (state+county+tract).
        population: Total population from ACS B01003.
        employed: Employed count from ACS B23025.
        weight: Normalized share of county total, in [0.0, 1.0].

    Example:
        >>> tw = TractWeight(
        ...     tract_geoid="26163500100",
        ...     population=4500,
        ...     employed=2100,
        ...     weight=0.015,
        ... )
        >>> len(tw.tract_geoid)
        11
    """

    model_config = ConfigDict(frozen=True)

    tract_geoid: Annotated[str, Field(min_length=11, max_length=11)] = Field(
        description="11-char Census tract GEOID (state+county+tract)"
    )
    population: Annotated[int, Field(ge=0)] = Field(description="Total population (ACS B01003)")
    employed: Annotated[int, Field(ge=0)] = Field(description="Employed count (ACS B23025)")
    weight: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Normalized share of county total"
    )


# =============================================================================
# HEX ECONOMIC STATE
# =============================================================================


class HexEconomicState(BaseModel):
    """Per-hex economic state at a single simulation tick.

    Represents the Marxian decomposition of value at H3 resolution 7.
    Each hex belongs to exactly one county in the tri-county study area.
    Department shares partition employment across the four Marxian
    departments of social reproduction.

    Args:
        h3_index: H3 resolution 7 cell ID.
        county_fips: 5-digit county FIPS code (must be in tri-county set).
        constant_capital: c -- means of production value.
        variable_capital: v -- wages (pre-circulation).
        surplus_value: s -- extracted surplus.
        employment: Allocated employment count.
        dept_shares: Department I, IIa, IIb, III employment fractions.
        profit_rate: s / (c + v), defaults to 0.0.
        exploitation_rate: s / v, defaults to 0.0.

    Example:
        >>> hex_state = HexEconomicState(
        ...     h3_index="872a10000ffffff",
        ...     county_fips="26163",
        ...     constant_capital=500.0,
        ...     variable_capital=200.0,
        ...     surplus_value=100.0,
        ...     employment=50.0,
        ...     dept_shares=(0.3, 0.3, 0.2, 0.2),
        ... )
        >>> hex_state.county_fips in TRI_COUNTY_FIPS
        True
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 resolution 7 cell ID")
    county_fips: str = Field(description="5-digit county FIPS code")
    constant_capital: Annotated[float, Field(ge=0.0)] = Field(
        description="c -- means of production value"
    )
    variable_capital: Annotated[float, Field(ge=0.0)] = Field(
        description="v -- wages (pre-circulation)"
    )
    surplus_value: Annotated[float, Field(ge=0.0)] = Field(description="s -- extracted surplus")
    employment: Annotated[float, Field(ge=0.0)] = Field(description="Allocated employment count")
    dept_shares: tuple[float, float, float, float] = Field(
        description="Department I, IIa, IIb, III employment fractions"
    )
    profit_rate: float = Field(default=0.0, description="s / (c + v)")
    exploitation_rate: float = Field(default=0.0, description="s / v")

    @field_validator("county_fips")
    @classmethod
    def validate_county_fips(cls, v: str) -> str:
        """Validate county FIPS is in the tri-county set."""
        if v not in TRI_COUNTY_FIPS:
            msg = f"county_fips must be one of {sorted(TRI_COUNTY_FIPS)}, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("dept_shares")
    @classmethod
    def validate_dept_shares(
        cls, v: tuple[float, float, float, float]
    ) -> tuple[float, float, float, float]:
        """Validate department shares are non-negative and sum to 1.0."""
        for i, share in enumerate(v):
            if share < 0.0:
                msg = f"dept_shares[{i}] must be >= 0.0, got {share}"
                raise ValueError(msg)
        total = sum(v)
        if abs(total - 1.0) > CONSERVATION_TOLERANCE:
            msg = f"dept_shares must sum to 1.0 (within {CONSERVATION_TOLERANCE}), got {total:.15f}"
            raise ValueError(msg)
        return v


# =============================================================================
# HEX GRID
# =============================================================================


class HexGrid(BaseModel):
    """Collection of all hexes in the tri-county area with resolution hierarchy.

    Provides the spatial mesh for economic simulation, including mappings
    from resolution 7 hexes to their resolution 6 and resolution 5 parents
    for multi-scale aggregation.

    Args:
        hexes: Mapping of h3_index to HexEconomicState.
        county_hex_ids: Mapping of county_fips to set of h3_indices.
        res6_parents: Mapping of h3_index (r7) to h3_index (r6).
        res5_parents: Mapping of h3_index (r7) to h3_index (r5).
        res6_children: Mapping of h3_index (r6) to set of h3_indices (r7).
        res5_children: Mapping of h3_index (r5) to set of h3_indices (r7).

    Example:
        >>> grid = HexGrid(
        ...     hexes={},
        ...     county_hex_ids={},
        ...     res6_parents={},
        ...     res5_parents={},
        ...     res6_children={},
        ...     res5_children={},
        ... )
        >>> len(grid.hexes)
        0
    """

    model_config = ConfigDict(frozen=True)

    hexes: dict[str, HexEconomicState] = Field(description="h3_index -> HexEconomicState mapping")
    county_hex_ids: dict[str, frozenset[str]] = Field(
        description="county_fips -> set of h3_indices"
    )
    res6_parents: dict[str, str] = Field(description="h3_index (r7) -> h3_index (r6)")
    res5_parents: dict[str, str] = Field(description="h3_index (r7) -> h3_index (r5)")
    res6_children: dict[str, frozenset[str]] = Field(
        description="h3_index (r6) -> set of h3_indices (r7)"
    )
    res5_children: dict[str, frozenset[str]] = Field(
        description="h3_index (r5) -> set of h3_indices (r7)"
    )


# =============================================================================
# SUBSTRATE CONFIG
# =============================================================================


class SubstrateConfig(BaseModel):
    """Configuration for the spatial economic substrate.

    All tunable parameters for the tri-county simulation substrate,
    including spatial resolution, conservation tolerances, and
    equalization dynamics.

    Args:
        county_fips_list: FIPS codes for the tri-county area.
        h3_resolution: Base hex resolution (default 7).
        conservation_tolerance: Absolute threshold for conservation checks.
        equalization_alpha: Capital migration speed coefficient.
        tick_count: Total simulation ticks (260 = 5 years at weekly ticks).
        log_conservation_warnings: Enable runtime conservation logging.

    Example:
        >>> config = SubstrateConfig()
        >>> config.h3_resolution
        7
        >>> len(config.county_fips_list)
        3
    """

    model_config = ConfigDict(frozen=True)

    county_fips_list: tuple[str, ...] = Field(
        default=("26163", "26125", "26099"),
        description="FIPS codes for tri-county area",
    )
    h3_resolution: int = Field(default=7, description="Base hex resolution")
    conservation_tolerance: float = Field(
        default=1e-10, description="abs(diff) threshold for conservation checks"
    )
    equalization_alpha: float = Field(
        default=0.01, description="Capital migration speed coefficient"
    )
    tick_count: int = Field(
        default=260, description="Total simulation ticks (5 years at weekly ticks)"
    )
    log_conservation_warnings: bool = Field(
        default=True, description="Enable runtime conservation logging"
    )


# =============================================================================
# BOUNDARY FLOW REGISTER
# =============================================================================


class BoundaryFlowRegister(BaseModel):
    """Tracks value flows crossing the tri-county boundary.

    Records variable capital (wages) entering and leaving the study area
    via commuter flows. The net_flow field is validated to equal
    inflow minus outflow exactly.

    Args:
        external_outflow_v: Total variable capital leaving tri-county via commute.
        external_inflow_v: Total variable capital entering tri-county via commute.
        net_flow: inflow - outflow (positive = net inbound).

    Example:
        >>> bfr = BoundaryFlowRegister(
        ...     external_outflow_v=150.0,
        ...     external_inflow_v=200.0,
        ...     net_flow=50.0,
        ... )
        >>> bfr.net_flow == bfr.external_inflow_v - bfr.external_outflow_v
        True
    """

    model_config = ConfigDict(frozen=True)

    external_outflow_v: float = Field(
        default=0.0, description="Total variable capital leaving tri-county via commute"
    )
    external_inflow_v: float = Field(
        default=0.0, description="Total variable capital entering tri-county via commute"
    )
    net_flow: float = Field(default=0.0, description="inflow - outflow (positive = net inbound)")

    @model_validator(mode="after")
    def validate_net_flow(self) -> BoundaryFlowRegister:
        """Validate net_flow equals inflow minus outflow."""
        expected = self.external_inflow_v - self.external_outflow_v
        if abs(self.net_flow - expected) > CONSERVATION_TOLERANCE:
            msg = (
                f"net_flow must equal external_inflow_v - external_outflow_v: "
                f"expected {expected}, got {self.net_flow}"
            )
            raise ValueError(msg)
        return self


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "BoundaryFlowRegister",
    "CONSERVATION_TOLERANCE",
    "HexEconomicState",
    "HexGrid",
    "SubstrateConfig",
    "TRI_COUNTY_FIPS",
    "TractWeight",
]
