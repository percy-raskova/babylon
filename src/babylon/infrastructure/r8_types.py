"""R8 geographic substrate data models (Feature 036-R8).

Frozen Pydantic models for per-cell geographic state at H3 resolution 8
and linear infrastructure features passing through R8 cells.

R8 is a read-only computational substrate. Immutable during gameplay.
Data aggregates upward to produce refined R7 attributes.

See Also:
    :mod:`babylon.infrastructure.types`: R7-level TerrainClassification.
    :mod:`babylon.infrastructure.r8_mesh`: R8 mesh generation.
    :mod:`babylon.infrastructure.r8_aggregation`: R8 → R7 aggregation.
"""

from __future__ import annotations

import re
from enum import StrEnum

import h3
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class R8FeatureType(StrEnum):
    """Linear infrastructure feature types at R8 resolution.

    Maps to NE road ``type`` classifications:
    - ``Major Highway`` → HIGHWAY
    - ``Beltway`` → HIGHWAY
    - ``Secondary Highway`` → ARTERIAL
    - NE railroads → RAIL

    Values:
        HIGHWAY: Major highway or interstate
        ARTERIAL: Secondary highway
        LOCAL_ROAD: Local or county road
        RAIL: Railroad line
        PIPELINE: Energy pipeline
        TRANSMISSION: Power transmission line
    """

    HIGHWAY = "HIGHWAY"
    ARTERIAL = "ARTERIAL"
    LOCAL_ROAD = "LOCAL_ROAD"
    RAIL = "RAIL"
    PIPELINE = "PIPELINE"
    TRANSMISSION = "TRANSMISSION"


# ---------------------------------------------------------------------------
# R8 Cell State
# ---------------------------------------------------------------------------

_FIPS_PATTERN = re.compile(r"^\d{5}$")

_VALID_TERRAIN_TYPES = frozenset({"LAND", "WATER", "RESOURCE"})


class HexR8State(BaseModel):
    """Per-cell geographic state at H3 resolution 8.

    Read-only reference data. Immutable during gameplay.
    Aggregates upward to R7 HexEconomicState and TerrainClassification.

    Args:
        h3_index: H3 R8 cell index (must be resolution 8).
        parent_h3: R7 parent cell index (must equal ``cell_to_parent(h3_index, 7)``).
        county_fips: 5-digit FIPS code for the county containing this cell.
        terrain_type: ``LAND``, ``WATER``, or ``RESOURCE``.
        water_fraction: Fraction of cell covered by water [0.0, 1.0].
        elevation_m: Elevation in meters. Stub: ``None`` until DEM data.
        has_water_service: Potable water service present.
        has_sewer: Sanitary sewer service present.
        has_electric: Electrical distribution present.
        has_gas: Natural gas service present.
        has_broadband: Broadband internet available.
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="H3 R8 cell index")
    parent_h3: str = Field(description="R7 parent cell index")
    county_fips: str = Field(description="5-digit county FIPS code")
    terrain_type: str = Field(description="LAND, WATER, or RESOURCE")
    water_fraction: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of cell covered by water [0.0, 1.0]",
    )
    elevation_m: float | None = Field(
        default=None,
        description="Elevation in meters; None = stub (not 0.0)",
    )
    has_water_service: bool = Field(default=True, description="Potable water service")
    has_sewer: bool = Field(default=True, description="Sanitary sewer service")
    has_electric: bool = Field(default=True, description="Electrical distribution")
    has_gas: bool = Field(default=True, description="Natural gas service")
    has_broadband: bool = Field(default=True, description="Broadband internet")

    @field_validator("h3_index")
    @classmethod
    def validate_h3_resolution_8(cls, v: str) -> str:
        """Validate h3_index is a valid H3 cell at resolution 8."""
        if not h3.is_valid_cell(v):
            msg = f"h3_index must be a valid H3 cell, got {v!r}"
            raise ValueError(msg)
        res = h3.get_resolution(v)
        if res != 8:
            msg = f"h3_index must be resolution 8, got resolution {res}"
            raise ValueError(msg)
        return v

    @field_validator("parent_h3")
    @classmethod
    def validate_parent_resolution_7(cls, v: str) -> str:
        """Validate parent_h3 is a valid H3 cell at resolution 7."""
        if not h3.is_valid_cell(v):
            msg = f"parent_h3 must be a valid H3 cell, got {v!r}"
            raise ValueError(msg)
        res = h3.get_resolution(v)
        if res != 7:
            msg = f"parent_h3 must be resolution 7, got resolution {res}"
            raise ValueError(msg)
        return v

    @field_validator("county_fips")
    @classmethod
    def validate_county_fips(cls, v: str) -> str:
        """Validate county_fips is exactly 5 digits."""
        if not _FIPS_PATTERN.match(v):
            msg = f"county_fips must be exactly 5 digits, got {v!r}"
            raise ValueError(msg)
        return v

    @field_validator("terrain_type")
    @classmethod
    def validate_terrain_type(cls, v: str) -> str:
        """Validate terrain_type is LAND, WATER, or RESOURCE."""
        if v not in _VALID_TERRAIN_TYPES:
            msg = f"terrain_type must be one of {sorted(_VALID_TERRAIN_TYPES)}, got {v!r}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_parent_consistency(self) -> HexR8State:
        """Validate parent_h3 matches h3.cell_to_parent(h3_index, 7)."""
        expected_parent = h3.cell_to_parent(self.h3_index, 7)
        if self.parent_h3 != expected_parent:
            msg = (
                f"parent_h3 must equal cell_to_parent(h3_index, 7): "
                f"expected {expected_parent!r}, got {self.parent_h3!r}"
            )
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# R8 Linear Feature
# ---------------------------------------------------------------------------


class R8LinearFeature(BaseModel):
    """A linear infrastructure feature passing through an R8 cell.

    Args:
        h3_index: R8 cell this feature passes through.
        feature_type: Classification (HIGHWAY, ARTERIAL, etc.).
        feature_name: Feature name from source data (e.g., "I-75").
        source_dataset: Provenance (e.g., ``NE_10M_ROADS``).
        source_feature_id: Original feature ID from source data.
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(description="R8 cell this feature passes through")
    feature_type: R8FeatureType = Field(description="Feature classification")
    feature_name: str | None = Field(
        default=None,
        description="Feature name from source data",
    )
    source_dataset: str = Field(description="Source dataset provenance")
    source_feature_id: str | None = Field(
        default=None,
        description="Original feature ID from source",
    )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "HexR8State",
    "R8FeatureType",
    "R8LinearFeature",
]
