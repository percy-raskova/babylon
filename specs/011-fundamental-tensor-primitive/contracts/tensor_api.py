"""Tensor API Contracts.

This module defines the protocols (interfaces) for the Fundamental Tensor Primitive.
These are contracts that implementations must satisfy.

Feature: 011-fundamental-tensor-primitive
Date: 2026-02-01
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Protocol, runtime_checkable

from pydantic import Field

if TYPE_CHECKING:
    from babylon.economics.tensor import ValueTensor4x3

# =============================================================================
# Type Definitions
# =============================================================================

LaborHours = Annotated[float, Field(ge=0.0, description="Labor-time in hours (non-negative)")]
"""Labor-time measurement in hours. Must be non-negative for primitive tensor cells."""

SignedLaborHours = Annotated[float, Field(description="Labor-time allowing negative values")]
"""Labor-time measurement allowing negative values. Used for derived quantities like imperial rent."""


class GeoLevel(Enum):
    """Geographic aggregation levels."""

    COUNTY = "county"  # 5-digit FIPS code
    STATE = "state"  # 2-digit state FIPS prefix
    NATION = "nation"  # Single national aggregate


# =============================================================================
# Sentinel for Missing Data
# =============================================================================


class NoDataSentinel:
    """Marker for missing tensor data.

    This is a sentinel object returned when tensor data is not available.
    It is falsy (bool(sentinel) == False) to enable clean consumer patterns:

        if tensor := registry.get(fips, year):
            # Use tensor
        else:
            # Handle missing data with tensor.reason

    Attributes:
        fips: The FIPS code that was queried.
        year: The year that was queried.
        reason: Human-readable explanation of why data is missing.
    """

    __slots__ = ("fips", "year", "reason")

    def __init__(self, fips: str, year: int, reason: str) -> None:
        self.fips = fips
        self.year = year
        self.reason = reason

    def __bool__(self) -> bool:
        """Return False to enable `if tensor := registry.get(...)` pattern."""
        return False

    def __repr__(self) -> str:
        return f"NoDataSentinel(fips={self.fips!r}, year={self.year}, reason={self.reason!r})"


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class TensorPrimitive(Protocol):
    """Protocol for read-only tensor access.

    This is the primary interface for consumers (simulation, visualization).
    Implementations provide cached access to tensor data without database queries.
    """

    def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
        """Get tensor for a specific county and year.

        Args:
            fips: 5-digit FIPS code (e.g., "26163" for Wayne County, MI).
            year: Calendar year (e.g., 2022).

        Returns:
            ValueTensor4x3 if data exists, NoDataSentinel otherwise.

        Note:
            This method MUST NOT perform database queries. Data must be
            pre-loaded via TensorHydrator.
        """
        ...

    def get_aggregate(
        self, level: GeoLevel, code: str, year: int
    ) -> ValueTensor4x3 | NoDataSentinel:
        """Get aggregated tensor for a geographic level.

        Args:
            level: Aggregation level (STATE or NATION).
            code: Geographic code:
                - STATE: 2-digit state FIPS (e.g., "26" for Michigan)
                - NATION: "US" for national aggregate
            year: Calendar year.

        Returns:
            Aggregated ValueTensor4x3 (sum of constituent counties).

        Note:
            Aggregates are computed lazily on first request and cached.
        """
        ...

    def available_years(self, fips: str) -> frozenset[int]:
        """Get available years for a county.

        Args:
            fips: 5-digit FIPS code.

        Returns:
            Frozen set of years with data for this county.
        """
        ...


@runtime_checkable
class TensorHydrator(Protocol):
    """Protocol for loading tensors from database.

    This is the only component that touches the database for economic data.
    After hydration, all access goes through TensorPrimitive.
    """

    def hydrate_counties(
        self, fips_codes: Sequence[str], years: Sequence[int]
    ) -> None:
        """Load tensors for multiple counties and years.

        Args:
            fips_codes: List of 5-digit FIPS codes.
            years: List of years to load.

        Note:
            This method performs database queries. Call once at initialization,
            then use TensorPrimitive.get() for all subsequent access.
        """
        ...

    def hydrate_state(self, state_fips: str, years: Sequence[int]) -> None:
        """Load tensors for all counties in a state.

        Args:
            state_fips: 2-digit state FIPS code (e.g., "26" for Michigan).
            years: List of years to load.
        """
        ...


@runtime_checkable
class SNLTConverter(Protocol):
    """Protocol for SNLT conversion factors.

    Provides year-specific factors for converting monetary wages to labor-hours.
    """

    def get_factor(self, year: int) -> float:
        """Get SNLT conversion factor for a year.

        Args:
            year: Calendar year.

        Returns:
            Conversion factor (wages * factor = labor-hours).

        Note:
            Factor of 1.0 means no conversion (wage-proportional proxy).
            Factor < 1.0 means higher productivity (fewer hours per dollar).
        """
        ...


# =============================================================================
# Consumer Protocols (for type checking)
# =============================================================================


@runtime_checkable
class TensorConsumer(Protocol):
    """Protocol for components that consume tensor data.

    Consumers receive a TensorPrimitive reference and use it for read-only access.
    They MUST NOT import database modules or perform direct database queries.
    """

    def set_tensor_source(self, source: TensorPrimitive) -> None:
        """Set the tensor data source.

        Args:
            source: TensorPrimitive implementation (typically TensorRegistry).
        """
        ...


# =============================================================================
# Derived Tensor Protocols
# =============================================================================


@runtime_checkable
class DerivedTensor(Protocol):
    """Protocol for tensors derived from the primitive.

    Derived tensors compute values from ValueTensor4x3 data.
    They MUST NOT access the database directly.
    """

    def get(self, fips: str) -> SignedLaborHours | NoDataSentinel:
        """Get derived value for a county.

        Args:
            fips: 5-digit FIPS code.

        Returns:
            Derived value (may be negative) or NoDataSentinel.
        """
        ...

    @property
    def year(self) -> int:
        """The year this derived tensor represents."""
        ...


# =============================================================================
# Type Aliases for Collections
# =============================================================================

TensorCache = dict[tuple[str, int], "ValueTensor4x3 | NoDataSentinel"]
"""Type alias for county tensor cache: (fips, year) -> tensor."""

AggregateCache = dict[tuple[GeoLevel, str, int], "ValueTensor4x3 | NoDataSentinel"]
"""Type alias for aggregate cache: (level, code, year) -> tensor."""
