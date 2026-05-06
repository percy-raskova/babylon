"""Snapshot types for the MVP simulation engine.

These are immutable representations of simulation state at a point in time.
They are designed for the GUI interface and differ from internal simulation
entities which may be mutable.

Available types:
- HexState: Immutable geographic cell (H3 index only for MVP)
- EdgeState: Relationship snapshot (source, target, type, weight)
- TerritoryState: Territory state at a specific tick
- SimulationSnapshot: Complete simulation state container

All types are Pydantic models with validation.

See Also:
    - data-model.md: Entity definitions and validation rules
    - contracts/simulation_state.py: Protocol that returns these types
"""

from __future__ import annotations

import logging
import re
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# H3 index pattern: 15-character hexadecimal string
H3_INDEX_PATTERN = re.compile(r"^[0-9a-f]{15}$")

# FIPS code pattern: 5-digit string (for county territories)
FIPS_PATTERN = re.compile(r"^[0-9]{5}$")


class SnapshotEdgeType(StrEnum):
    """Edge types for simulation snapshots.

    Maps to constitution I.6 edge modes.
    """

    ADJACENCY = "ADJACENCY"
    EXTRACTION = "EXTRACTION"
    SOLIDARITY = "SOLIDARITY"
    ANTAGONISTIC = "ANTAGONISTIC"


class HexState(BaseModel):
    """Immutable geographic cell snapshot.

    Hexes are the invariant substrate - they don't change during simulation.
    For MVP, HexState contains only the H3 index. Future versions may add
    physical properties (terrain, resources).

    Attributes:
        h3_index: H3 cell index (15-char hex string, resolution 5).
    """

    model_config = ConfigDict(frozen=True)

    h3_index: str = Field(
        ...,
        description="H3 cell index (15-char hex string, resolution 5)",
    )

    @field_validator("h3_index")
    @classmethod
    def validate_h3_index(cls, v: str) -> str:
        """Validate H3 index is 15-char lowercase hex."""
        v_lower = v.lower()
        if not H3_INDEX_PATTERN.match(v_lower):
            msg = f"h3_index must be 15-char hex string, got '{v}'"
            raise ValueError(msg)
        return v_lower


class EdgeState(BaseModel):
    """Relationship snapshot between entities at a specific tick.

    Attributes:
        source_id: ID of the source entity.
        target_id: ID of the target entity.
        edge_type: Relationship type.
        weight: Edge weight (default 1.0).
    """

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(..., description="ID of the source entity")
    target_id: str = Field(..., description="ID of the target entity")
    edge_type: SnapshotEdgeType = Field(
        ...,
        description="Relationship type (ADJACENCY, EXTRACTION, SOLIDARITY, ANTAGONISTIC)",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Edge weight (non-negative)",
    )


# Type alias for clamped profit rate
ProfitRate = Annotated[float, Field(ge=0.0, le=1.0)]


class TerritoryState(BaseModel):
    """Territory state snapshot at a specific tick.

    This is the GUI-facing representation of a territory.

    Attributes:
        territory_id: Unique identifier (FIPS code for counties).
        controlling_polity: Current controller (equals territory_id for MVP).
        hex_claims: Set of H3 indices this territory claims.
        tick: Tick number when this snapshot was taken.
        profit_rate: Current profit rate, range [0.0, 1.0].
        equilibrium_r: Territory-specific equilibrium (= initial_r at hydration).
    """

    model_config = ConfigDict(frozen=True)

    territory_id: str = Field(
        ...,
        description="Unique identifier (FIPS code for counties)",
    )
    controlling_polity: str = Field(
        ...,
        description="Current controller (equals territory_id for MVP)",
    )
    hex_claims: frozenset[str] = Field(
        default_factory=frozenset,
        description="Set of H3 indices this territory claims",
    )
    tick: int = Field(
        ...,
        ge=0,
        description="Tick number when this snapshot was taken",
    )
    profit_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current profit rate, range [0.0, 1.0]",
    )
    equilibrium_r: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Territory-specific equilibrium (= initial_r at hydration)",
    )
    tensor_year: int | None = Field(
        default=None,
        ge=1900,
        description="Year for tensor lookup (may differ from tick). None if no tensor data.",
    )

    @field_validator("territory_id")
    @classmethod
    def validate_territory_id(cls, v: str) -> str:
        """Validate territory_id is a 5-digit FIPS code."""
        if not FIPS_PATTERN.match(v):
            msg = f"territory_id must be 5-digit FIPS code, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("hex_claims", mode="before")
    @classmethod
    def convert_hex_claims(cls, v: set[str] | frozenset[str] | list[str]) -> frozenset[str]:
        """Convert hex_claims to frozenset for immutability."""
        if isinstance(v, frozenset):
            return v
        return frozenset(v)

    @model_validator(mode="after")
    def validate_hex_claims_patterns(self) -> TerritoryState:
        """Validate all H3 indices in hex_claims match pattern."""
        for h3_idx in self.hex_claims:
            if not H3_INDEX_PATTERN.match(h3_idx.lower()):
                msg = f"Invalid H3 index in hex_claims: '{h3_idx}'"
                raise ValueError(msg)
        return self

    @classmethod
    def with_clamped_profit_rate(
        cls,
        territory_id: str,
        controlling_polity: str,
        hex_claims: set[str] | frozenset[str],
        tick: int,
        profit_rate: float,
        equilibrium_r: float,
        tensor_year: int | None = None,
    ) -> TerritoryState:
        """Create TerritoryState with profit_rate clamped to [0.0, 1.0].

        If profit_rate is outside valid range, it is clamped and a warning is logged.

        Args:
            territory_id: FIPS code.
            controlling_polity: Controller ID.
            hex_claims: Set of H3 indices.
            tick: Current tick.
            profit_rate: Computed profit rate (may be out of range).
            equilibrium_r: Territory-specific equilibrium.
            tensor_year: Year for tensor lookup (may differ from tick). None if no tensor data.

        Returns:
            TerritoryState with clamped profit_rate.
        """
        original = profit_rate
        clamped = max(0.0, min(1.0, profit_rate))
        if original != clamped:
            logger.warning(
                "profit_rate %.6f clamped to %.6f for territory %s",
                original,
                clamped,
                territory_id,
            )
        return cls(
            territory_id=territory_id,
            controlling_polity=controlling_polity,
            hex_claims=frozenset(hex_claims),
            tick=tick,
            profit_rate=clamped,
            equilibrium_r=equilibrium_r,
            tensor_year=tensor_year,
        )


class SimulationSnapshot(BaseModel):
    """Complete simulation state at a specific tick.

    This is the top-level container returned by `get_snapshot()`.

    Attributes:
        tick: Current tick number.
        territories: Map of territory_id to TerritoryState.
        hexes: Map of h3_index to HexState (invariant substrate).
        edges: List of EdgeState relationships (empty for MVP).
        tensor_registry: Optional reference to TensorRegistry for cached
            tensor data access without database queries.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tick: int = Field(
        ...,
        ge=0,
        description="Current tick number",
    )
    territories: dict[str, TerritoryState] = Field(
        default_factory=dict,
        description="Map of territory_id to TerritoryState",
    )
    hexes: dict[str, HexState] = Field(
        default_factory=dict,
        description="Map of h3_index to HexState (invariant substrate)",
    )
    edges: list[EdgeState] = Field(
        default_factory=list,
        description="List of EdgeState relationships (empty for MVP)",
    )
    # Note: Using Any here to avoid circular import issues. At runtime,
    # this will hold a TensorRegistry instance from babylon.economics.tensor_registry.
    # TYPE_CHECKING provides the proper type hint for static analysis.
    tensor_registry: Any = Field(
        default=None,
        description="Optional TensorRegistry for cached tensor data access",
        exclude=True,  # Exclude from serialization
    )

    @model_validator(mode="after")
    def validate_hex_references(self) -> SimulationSnapshot:
        """Validate all hex_claims reference existing hexes."""
        hex_ids = set(self.hexes.keys())
        for territory_id, territory in self.territories.items():
            missing = territory.hex_claims - hex_ids
            if missing:
                # Log warning but don't fail - hex mapping may be incomplete
                logger.warning(
                    "Territory %s has hex_claims not in hexes dict: %s",
                    territory_id,
                    missing,
                )
        return self


__all__ = [
    "HexState",
    "EdgeState",
    "TerritoryState",
    "SimulationSnapshot",
    "SnapshotEdgeType",
]
