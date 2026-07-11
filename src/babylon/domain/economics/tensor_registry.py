"""Tensor registry for cached tensor primitive access.

This module provides the TensorRegistry class, which serves as the single source
of truth for all economic tensor data in the simulation. The registry:

1. Caches ValueTensor4x3 instances keyed by (fips, year)
2. Provides lazy aggregation with LRU caching for state/nation totals
3. Ensures thread-safe access to cached data
4. Implements the TensorPrimitive protocol for read-only access

The registry enforces the architectural constraint that consumers (simulation,
hexagons) access tensor data without database queries after initialization.

Example:
    >>> from babylon.domain.economics.tensor_registry import TensorRegistry, GeoLevel
    >>> from babylon.domain.economics.snlt import SNLTConfig
    >>>
    >>> # Create registry with default SNLT (wage-proportional proxy)
    >>> registry = TensorRegistry()
    >>>
    >>> # After hydration (via TensorHydrator), access data
    >>> if tensor := registry.get("26163", 2022):
    ...     print(f"Profit rate: {tensor.profit_rate}")
    ... else:
    ...     print(f"No data: {tensor.reason}")
    >>>
    >>> # Access state aggregate (computed lazily, cached)
    >>> if michigan := registry.get_aggregate(GeoLevel.STATE, "26", 2022):
    ...     print(f"Michigan total: {michigan.total_value}")

See Also:
    :mod:`babylon.domain.economics.tensor`: ValueTensor4x3 and NoDataSentinel definitions.
    :mod:`babylon.domain.economics.snlt`: SNLT configuration for labor-hour conversion.
    :mod:`babylon.domain.economics.hydrator`: TensorHydrator for database loading.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, Final, Protocol, runtime_checkable

from babylon.domain.economics.snlt import DEFAULT_SNLT_CONFIG, SNLTConfig
from babylon.domain.economics.tensor import DepartmentRow, NoDataSentinel, ValueTensor4x3
from babylon.models.types import LaborHours, Probability

if TYPE_CHECKING:
    pass


@runtime_checkable
class CountyHydrator(Protocol):
    """Protocol for single-county tensor hydration.

    Classes implementing this protocol can hydrate individual county-year
    combinations into ValueTensor4x3 instances. The MarxianHydrator class
    implements this protocol.
    """

    def hydrate(self, fips_code: str, year: int) -> ValueTensor4x3:
        """Hydrate a single county-year into a tensor.

        Args:
            fips_code: 5-digit FIPS county code.
            year: Calendar year.

        Returns:
            ValueTensor4x3 with c, v, s for each department in LaborHours.
        """
        ...


logger = logging.getLogger(__name__)


class GeoLevel(Enum):
    """Geographic aggregation levels.

    Used to specify the level of geographic aggregation when requesting
    aggregated tensor data via TensorRegistry.get_aggregate().

    Attributes:
        COUNTY: Individual county level (5-digit FIPS code).
        STATE: State level (2-digit state FIPS prefix).
        NATION: National aggregate (single value for entire US).
    """

    COUNTY = "county"
    STATE = "state"
    NATION = "nation"


# Type aliases for cache structures
TensorCache = dict[tuple[str, int], ValueTensor4x3 | NoDataSentinel]
"""Type alias for county tensor cache: (fips, year) -> tensor | sentinel."""

AggregateKey = tuple[GeoLevel, str, int]
"""Type alias for aggregate cache key: (level, code, year)."""


class TensorRegistry:
    """Cached container for tensor primitives.

    The TensorRegistry serves as the single source of truth for all economic
    tensor data in the simulation. It provides:

    - Cached access to county-level ValueTensor4x3 instances
    - Lazy computation and LRU caching of geographic aggregates
    - Thread-safe operations via locks
    - Clear separation between hydration (database) and access (cache)

    Args:
        snlt_config: Configuration for SNLT conversion factors.
            Defaults to DEFAULT_SNLT_CONFIG (factor 1.0).
        maxsize: Maximum size of the aggregate cache (LRU eviction).
            Defaults to 10,000 entries.

    Example:
        >>> registry = TensorRegistry()
        >>> # After hydration...
        >>> if tensor := registry.get("26163", 2022):
        ...     print(tensor.profit_rate)

    Note:
        The registry does not perform database queries. Data must be loaded
        via the TensorHydrator.hydrate_counties() method, which populates
        the registry's cache.
    """

    # Default LRU cache size (aggregate cache)
    DEFAULT_MAXSIZE: Final[int] = 10_000

    # Valid year range for data
    MIN_YEAR: Final[int] = 2010
    MAX_YEAR: Final[int] = 2025

    def __init__(
        self,
        snlt_config: SNLTConfig | None = None,
        maxsize: int = DEFAULT_MAXSIZE,
    ) -> None:
        """Initialize the tensor registry.

        Args:
            snlt_config: SNLT configuration for labor-hour conversion.
                Defaults to DEFAULT_SNLT_CONFIG (factor 1.0).
            maxsize: Maximum aggregate cache entries before LRU eviction.
        """
        self._snlt_config: Final[SNLTConfig] = snlt_config or DEFAULT_SNLT_CONFIG
        self._maxsize: Final[int] = maxsize

        # Primary cache: (fips, year) -> ValueTensor4x3 | NoDataSentinel
        self._county_cache: TensorCache = {}

        # Thread safety locks
        self._county_lock = threading.RLock()
        self._aggregate_lock = threading.RLock()

        # Create LRU-cached aggregate computation
        # We wrap this to allow cache info access and clearing
        self._aggregate_cache_fn = lru_cache(maxsize=maxsize // 10)(
            self._compute_aggregate_uncached
        )

        logger.debug("TensorRegistry initialized with maxsize=%d", maxsize)

    @property
    def snlt_config(self) -> SNLTConfig:
        """Get the SNLT configuration.

        Returns:
            The SNLTConfig used for labor-hour conversion.
        """
        return self._snlt_config

    def get(self, fips: str, year: int) -> ValueTensor4x3 | NoDataSentinel:
        """Get tensor for a specific county and year.

        This method returns cached tensor data without performing any database
        queries. If the requested (fips, year) combination was not loaded
        during hydration, a NoDataSentinel is returned.

        Args:
            fips: 5-digit FIPS code (e.g., "26163" for Wayne County, MI).
            year: Calendar year (e.g., 2022).

        Returns:
            ValueTensor4x3 if data exists in cache, NoDataSentinel otherwise.

        Example:
            >>> if tensor := registry.get("26163", 2022):
            ...     print(tensor.profit_rate)
            ... else:
            ...     print(f"No data: {tensor.reason}")
        """
        # Check year boundaries first
        if year < self.MIN_YEAR or year > self.MAX_YEAR:
            logger.debug("get(%s, %d): Year outside valid range", fips, year)
            return NoDataSentinel(
                fips,
                year,
                f"get({fips}, {year}): Year outside available data range ({self.MIN_YEAR}-{self.MAX_YEAR})",
            )

        with self._county_lock:
            cache_key = (fips, year)
            if cache_key in self._county_cache:
                result = self._county_cache[cache_key]
                logger.debug("get(%s, %d): Cache hit", fips, year)
                return result

        # Not in cache - return sentinel
        logger.debug("get(%s, %d): Cache miss", fips, year)
        return NoDataSentinel(
            fips,
            year,
            f"get({fips}, {year}): FIPS/year not loaded",
        )

    def get_aggregate(
        self, level: GeoLevel, code: str, year: int
    ) -> ValueTensor4x3 | NoDataSentinel:
        """Get aggregated tensor for a geographic level.

        Aggregates are computed lazily on first request and cached via LRU.
        The aggregate is the sum of all constituent county tensors.

        Args:
            level: Aggregation level (STATE or NATION).
            code: Geographic code:
                - STATE: 2-digit state FIPS (e.g., "26" for Michigan)
                - NATION: "US" for national aggregate
            year: Calendar year.

        Returns:
            Aggregated ValueTensor4x3 (sum of constituent counties),
            or NoDataSentinel if no data available.

        Example:
            >>> if michigan := registry.get_aggregate(GeoLevel.STATE, "26", 2022):
            ...     print(f"Michigan total value: {michigan.total_value}")
        """
        # Year boundary check
        if year < self.MIN_YEAR or year > self.MAX_YEAR:
            return NoDataSentinel(
                code,
                year,
                f"get_aggregate({level.value}, {code}, {year}): Year outside available data range",
            )

        # Use cached computation
        with self._aggregate_lock:
            return self._aggregate_cache_fn(level, code, year)

    def _compute_aggregate_uncached(
        self, level: GeoLevel, code: str, year: int
    ) -> ValueTensor4x3 | NoDataSentinel:
        """Compute aggregate tensor (uncached implementation).

        This method is wrapped by lru_cache for caching.

        Args:
            level: Aggregation level.
            code: Geographic code.
            year: Calendar year.

        Returns:
            Aggregated tensor or sentinel.
        """
        if level == GeoLevel.COUNTY:
            # COUNTY level just delegates to get()
            return self.get(code, year)

        # Get constituent county FIPS codes
        county_fips = self._get_counties_for_aggregate(level, code)

        if not county_fips:
            return NoDataSentinel(
                code,
                year,
                f"get_aggregate({level.value}, {code}, {year}): No counties found for code",
            )

        # Collect valid tensors
        tensors: list[ValueTensor4x3] = []
        with self._county_lock:
            for fips in county_fips:
                cache_key = (fips, year)
                if cache_key in self._county_cache:
                    result = self._county_cache[cache_key]
                    if isinstance(result, ValueTensor4x3):
                        tensors.append(result)

        if not tensors:
            return NoDataSentinel(
                code,
                year,
                f"get_aggregate({level.value}, {code}, {year}): No county data loaded for this aggregate",
            )

        # Sum all tensors
        return self._sum_tensors(tensors, code, year)

    def _get_counties_for_aggregate(self, level: GeoLevel, code: str) -> list[str]:
        """Get list of county FIPS codes for a geographic aggregate.

        Args:
            level: Aggregation level (STATE or NATION).
            code: Geographic code.

        Returns:
            List of 5-digit county FIPS codes.
        """
        with self._county_lock:
            all_fips = [key[0] for key in self._county_cache]

        if level == GeoLevel.STATE:
            # Filter counties by state prefix (first 2 digits)
            return [fips for fips in all_fips if fips.startswith(code)]
        elif level == GeoLevel.NATION:
            # Return all counties
            return list(set(all_fips))
        else:
            return []

    def _sum_tensors(
        self, tensors: list[ValueTensor4x3], fips_code: str, year: int
    ) -> ValueTensor4x3:
        """Sum multiple tensors into a single aggregate tensor.

        Args:
            tensors: List of tensors to sum.
            fips_code: FIPS code for the aggregate (state or "US").
            year: Year for the aggregate.

        Returns:
            Aggregated ValueTensor4x3.
        """
        # Initialize department accumulators
        dept_I_c, dept_I_v, dept_I_s = 0.0, 0.0, 0.0
        dept_IIa_c, dept_IIa_v, dept_IIa_s = 0.0, 0.0, 0.0
        dept_IIb_c, dept_IIb_v, dept_IIb_s = 0.0, 0.0, 0.0
        dept_III_c, dept_III_v, dept_III_s = 0.0, 0.0, 0.0
        total_excluded_wages = 0.0
        total_naics_weight = 0.0
        total_visibility_weight = 0.0

        for t in tensors:
            dept_I_c += t.dept_I.c
            dept_I_v += t.dept_I.v
            dept_I_s += t.dept_I.s

            dept_IIa_c += t.dept_IIa.c
            dept_IIa_v += t.dept_IIa.v
            dept_IIa_s += t.dept_IIa.s

            dept_IIb_c += t.dept_IIb.c
            dept_IIb_v += t.dept_IIb.v
            dept_IIb_s += t.dept_IIb.s

            dept_III_c += t.dept_III.c
            dept_III_v += t.dept_III.v
            dept_III_s += t.dept_III.s

            total_excluded_wages += t.excluded_wages

            # Weight by total value for naics_granularity and visibility
            weight = t.total_value
            total_naics_weight += t.naics_granularity * weight
            total_visibility_weight += t.visibility_g33 * weight

        # Compute weighted average for naics_granularity and visibility_g33
        total_value = sum(t.total_value for t in tensors)
        avg_naics = total_naics_weight / total_value if total_value > 0 else 0.5
        avg_visibility = total_visibility_weight / total_value if total_value > 0 else 1.0

        # Use appropriate FIPS code for aggregate
        # STATE: pad to 5 digits (e.g., "26" -> "26000")
        # NATION: use "00000" as national aggregate code
        if fips_code == "US":
            aggregate_fips = "00000"
        elif len(fips_code) == 2:
            aggregate_fips = f"{fips_code}000"  # State aggregate
        else:
            aggregate_fips = fips_code.zfill(5)

        return ValueTensor4x3(
            fips_code=aggregate_fips,
            year=year,
            dept_I=DepartmentRow(c=dept_I_c, v=dept_I_v, s=dept_I_s),
            dept_IIa=DepartmentRow(c=dept_IIa_c, v=dept_IIa_v, s=dept_IIa_s),
            dept_IIb=DepartmentRow(c=dept_IIb_c, v=dept_IIb_v, s=dept_IIb_s),
            dept_III=DepartmentRow(c=dept_III_c, v=dept_III_v, s=dept_III_s),
            naics_granularity=Probability(max(0.0, min(1.0, avg_naics))),
            excluded_wages=LaborHours(total_excluded_wages),
            visibility_g33=max(0.0, min(1.0, avg_visibility)),
        )

    def all_fips(self) -> frozenset[str]:
        """Get all FIPS codes with cached tensor data.

        Returns:
            Frozen set of 5-digit FIPS codes.
        """
        with self._county_lock:
            return frozenset(fips for fips, _year in self._county_cache)

    def available_years(self, fips: str) -> frozenset[int]:
        """Get available years for a county.

        Args:
            fips: 5-digit FIPS code.

        Returns:
            Frozen set of years with data for this county.
        """
        with self._county_lock:
            years = {year for (cached_fips, year) in self._county_cache if cached_fips == fips}
        return frozenset(years)

    def put(self, fips: str, year: int, tensor: ValueTensor4x3) -> None:
        """Store a tensor in the cache.

        This method is used by TensorHydrator to populate the registry.

        Args:
            fips: 5-digit FIPS code.
            year: Calendar year.
            tensor: The tensor to cache.
        """
        with self._county_lock:
            self._county_cache[(fips, year)] = tensor

        # Invalidate aggregate cache when source data changes
        self._invalidate_aggregates()

    def put_sentinel(self, fips: str, year: int, reason: str) -> None:
        """Store a NoDataSentinel in the cache.

        This method is used to explicitly mark a (fips, year) as having
        no available data.

        Args:
            fips: 5-digit FIPS code.
            year: Calendar year.
            reason: Reason for missing data.
        """
        sentinel = NoDataSentinel(fips, year, reason)
        with self._county_lock:
            self._county_cache[(fips, year)] = sentinel

    def _invalidate_aggregates(self) -> None:
        """Clear the aggregate cache.

        Called when source tensors are updated to ensure aggregates
        are recomputed from fresh data.
        """
        with self._aggregate_lock:
            self._aggregate_cache_fn.cache_clear()
            logger.info("Aggregate cache invalidated")

    def clear(self) -> None:
        """Clear all caches.

        Removes all cached tensors and aggregates.
        """
        with self._county_lock:
            self._county_cache.clear()
        self._invalidate_aggregates()
        logger.info("TensorRegistry cleared")

    def cache_info(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics:
            - county_count: Number of cached county tensors
            - aggregate_hits: LRU cache hits
            - aggregate_misses: LRU cache misses
            - aggregate_size: Current LRU cache size
        """
        with self._county_lock:
            county_count = len(self._county_cache)

        aggregate_info = self._aggregate_cache_fn.cache_info()

        return {
            "county_count": county_count,
            "aggregate_hits": aggregate_info.hits,
            "aggregate_misses": aggregate_info.misses,
            "aggregate_size": aggregate_info.currsize,
        }

    def hydrate_state(
        self,
        hydrator: CountyHydrator,
        state_fips: str,
        years: Sequence[int],
    ) -> None:
        """Load tensors for all counties in a state.

        This is a convenience method that queries the database for all counties
        in a state and hydrates them in batch. Useful for state-level analysis.

        Args:
            hydrator: County-level hydrator (e.g., MarxianHydrator).
            state_fips: 2-digit state FIPS code (e.g., "26" for Michigan).
            years: List of years to load.

        Note:
            This method requires database access to discover counties.
            Use hydrate_counties() if you already have a list of FIPS codes.

        Example:
            >>> from babylon.domain.economics.hydrator import MarxianHydrator
            >>> registry = TensorRegistry()
            >>> # ... set up hydrator with database session ...
            >>> registry.hydrate_state(hydrator, "26", [2020, 2021, 2022])
            >>> # Now all Michigan counties are loaded for those years
        """
        # Lazy import to avoid circular dependencies
        from babylon.reference.database import get_reference_session

        # Query all counties in this state
        query = """
            SELECT fips
            FROM dim_county
            WHERE fips LIKE :state_prefix
            ORDER BY fips
        """

        with get_reference_session() as session:
            result = session.execute(
                __import__("sqlalchemy").text(query),
                {"state_prefix": f"{state_fips}%"},
            )
            fips_codes = [row[0] for row in result]

        if not fips_codes:
            logger.warning("hydrate_state: No counties found for state %s", state_fips)
            return

        logger.info(
            "hydrate_state: Found %d counties in state %s",
            len(fips_codes),
            state_fips,
        )

        # Delegate to hydrate_counties
        self.hydrate_counties(hydrator, fips_codes, years)

    def hydrate_counties(
        self,
        hydrator: CountyHydrator,
        fips_codes: Sequence[str],
        years: Sequence[int],
    ) -> None:
        """Load tensors for multiple counties and years.

        This method performs database queries via the hydrator. Call once at
        initialization, then use get() for all subsequent access.

        Args:
            hydrator: County-level hydrator (e.g., MarxianHydrator).
            fips_codes: List of 5-digit FIPS codes.
            years: List of years to load.

        Note:
            - Years outside the valid range (2010-2025) are skipped.
            - Hydration failures for individual county-years are logged as
              warnings and result in NoDataSentinel entries.
            - Aggregate cache is invalidated after hydration.

        Example:
            >>> from babylon.domain.economics.hydrator import MarxianHydrator
            >>> registry = TensorRegistry()
            >>> hydrator = MarxianHydrator(qcew_source, bea_source, dept_mapper)
            >>> registry.hydrate_counties(hydrator, ["26163", "26125"], [2020, 2021])
            >>> tensor = registry.get("26163", 2020)
        """
        loaded_count = 0
        failed_count = 0

        for fips in fips_codes:
            for year in years:
                # Skip years outside valid range
                if year < self.MIN_YEAR or year > self.MAX_YEAR:
                    logger.debug("hydrate_counties: Skipping year %d outside valid range", year)
                    continue

                try:
                    tensor = hydrator.hydrate(fips, year)
                    self.put(fips, year, tensor)
                    loaded_count += 1
                    logger.debug("hydrate_counties: Loaded %s/%d", fips, year)
                except Exception as e:
                    # Log warning and store sentinel for failed hydration
                    logger.warning("hydrate_counties: Failed to hydrate %s/%d: %s", fips, year, e)
                    self.put_sentinel(fips, year, f"hydrate_counties({fips}, {year}): {e!s}")
                    failed_count += 1

        logger.info(
            "hydrate_counties: Loaded %d tensors, %d failures",
            loaded_count,
            failed_count,
        )


__all__ = [
    "AggregateKey",
    "CountyHydrator",
    "GeoLevel",
    "TensorCache",
    "TensorRegistry",
]
