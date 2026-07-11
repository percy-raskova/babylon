"""Data source and computation protocols for the Tensor Hierarchy module.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Defines Protocol interfaces for dependency injection across all tensor
sources and computation engines.

See Also:
    :mod:`babylon.domain.economics.tensor_hierarchy.types`: Tensor type definitions.
    :mod:`babylon.domain.economics.gamma.data_sources`: Feature 015 source protocols.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    from babylon.domain.economics.tensor import NoDataSentinel
    from babylon.domain.economics.tensor_hierarchy.types import (
        ClassTransitionMatrix,
        GeographicFlow,
        ImperialRentField,
        InterIndustryFlow,
        LeontiefInverse,
        ReproductionRequirements,
        ShadowSubsidyTensor,
        StationaryDistribution,
        VisibilityMetric,
    )

# =============================================================================
# TENSOR SOURCE PROTOCOLS
# =============================================================================


@runtime_checkable
class InterIndustryFlowSource(Protocol):
    """Protocol for loading BEA I-O coefficient data from SQLite.

    Data Source:
        Bureau of Economic Analysis (BEA) Input-Output Accounts.
        https://www.bea.gov/industry/input-output-accounts-data

    Example:
        >>> source = DefaultInterIndustryFlowSource(session_factory)
        >>> flow = source.get_direct_requirements(2021)
        >>> print(f"Industries: {flow.n_industries}")
        Industries: 71
    """

    def get_direct_requirements(self, year: int) -> InterIndustryFlow | NoDataSentinel:
        """Load the direct requirements coefficient matrix A for a given year.

        Args:
            year: Calendar year for the I-O table.

        Returns:
            InterIndustryFlow with the A matrix, or NoDataSentinel if unavailable.
        """
        ...

    def get_industry_codes(self) -> list[str]:
        """Return ordered list of BEA industry codes at Summary level.

        Returns:
            List of BEA Summary-level industry codes in canonical order.
        """
        ...

    def available_years(self) -> frozenset[int]:
        """Return set of years with I-O data available in SQLite.

        Returns:
            Frozenset of years with loaded coefficient data.
        """
        ...


@runtime_checkable
class GeographicFlowSource(Protocol):
    """Protocol for loading BTS FAF commodity flow data from SQLite.

    Data Source:
        Bureau of Transportation Statistics Freight Analysis Framework (FAF5).
        https://www.bts.gov/faf

    Example:
        >>> source = DefaultGeographicFlowSource(session_factory)
        >>> flow = source.get_flows(2017)
        >>> print(f"CFS areas: {flow.n_areas}")
    """

    def get_flows(
        self, year: int, commodity_code: str | None = None
    ) -> GeographicFlow | NoDataSentinel:
        """Load O-D flow matrix for a given year and optional commodity.

        Args:
            year: FAF data year.
            commodity_code: SCTG commodity code, or None for all-commodity aggregate.

        Returns:
            GeographicFlow with O-D matrix, or NoDataSentinel if unavailable.
        """
        ...

    def get_cfs_areas(self) -> list[str]:
        """Return ordered list of CFS Area codes.

        Returns:
            List of CFS Area codes in canonical order.
        """
        ...

    def get_cfs_to_county_mapping(self) -> dict[str, list[str]]:
        """Return mapping from CFS Area code to list of county FIPS codes.

        Returns:
            Dict mapping CFS Area code -> list of 5-digit FIPS codes.
        """
        ...


@runtime_checkable
class VisibilitySource(Protocol):
    """Protocol for computing visibility metrics by wrapping the gamma module.

    Wraps Feature 015 DefaultGammaIIICalculator without modifying gamma/.

    Example:
        >>> source = DefaultVisibilitySource(gamma_calculator, shadow_calculator)
        >>> metric = source.get_visibility(2022)
        >>> print(f"g_33: {metric.g_33:.3f}")
    """

    def get_visibility(self, year: int) -> VisibilityMetric | NoDataSentinel:
        """Compute diagonal visibility metric for a given year.

        Args:
            year: Calendar year (ATUS available from 2003).

        Returns:
            VisibilityMetric with g_diagonal, or NoDataSentinel if unavailable.
        """
        ...

    def get_shadow_subsidy(
        self, year: int, dept_iii_value: float, melt: float | None = None
    ) -> ShadowSubsidyTensor | NoDataSentinel:
        """Compute shadow subsidy from visibility and Dept III value.

        Args:
            year: Calendar year.
            dept_iii_value: Department III total value in labor-hours.
            melt: Monetary Expression of Labor Time (optional for dollar conversion).

        Returns:
            ShadowSubsidyTensor, or NoDataSentinel if visibility unavailable.
        """
        ...


@runtime_checkable
class ReproductionSource(Protocol):
    """Protocol for loading reproduction requirements from CEX + ATUS.

    Note:
        Production loader deferred (US4). Stub implementations return
        NoDataSentinel. Tests use synthetic ReproductionRequirements.

    Example:
        >>> source = StubReproductionSource()
        >>> req = source.get_requirements(2022)
        >>> bool(req)  # NoDataSentinel is falsy
        False
    """

    def get_requirements(self, year: int) -> ReproductionRequirements | NoDataSentinel:
        """Load consumption and labor requirements by social class.

        Args:
            year: Calendar year.

        Returns:
            ReproductionRequirements, or NoDataSentinel if unavailable.
        """
        ...

    def total_reproduction_cost(
        self, social_class: str, year: int, snlt: float
    ) -> float | NoDataSentinel:
        """Compute total reproduction cost in labor-time units.

        Args:
            social_class: SocialRole class name.
            year: Calendar year.
            snlt: Social Necessary Labor Time (hours per dollar).

        Returns:
            Total reproduction cost in labor-hours, or NoDataSentinel.
        """
        ...


@runtime_checkable
class ClassTransitionSource(Protocol):
    """Protocol for loading class transition matrices.

    Note:
        Production loader deferred (US5). Stub implementations return
        NoDataSentinel. Tests use synthetic ClassTransitionMatrix.

    Example:
        >>> source = StubClassTransitionSource()
        >>> matrix = source.get_transition_matrix((2015, 2020))
        >>> bool(matrix)  # NoDataSentinel is falsy
        False
    """

    def get_transition_matrix(
        self, period: tuple[int, int]
    ) -> ClassTransitionMatrix | NoDataSentinel:
        """Load transition matrix for a given time period.

        Args:
            period: (start_year, end_year) tuple.

        Returns:
            ClassTransitionMatrix, or NoDataSentinel if unavailable.
        """
        ...

    def get_stationary_distribution(
        self, period: tuple[int, int]
    ) -> StationaryDistribution | NoDataSentinel:
        """Compute long-run class distribution.

        Args:
            period: (start_year, end_year) tuple.

        Returns:
            StationaryDistribution, or NoDataSentinel if unavailable.
        """
        ...


# =============================================================================
# COMPUTATION PROTOCOLS
# =============================================================================


@runtime_checkable
class LeontiefComputer(Protocol):
    """Protocol for computing Leontief inverse and total labor coefficients.

    Example:
        >>> computer = DefaultLeontiefComputer()
        >>> inverse = computer.compute_inverse(flow)
        >>> all elements >= 0 and diagonal >= 1.0
    """

    def compute_inverse(self, flow: InterIndustryFlow) -> LeontiefInverse:
        """Compute L = (I - A)^{-1}.

        Args:
            flow: InterIndustryFlow with direct requirements matrix A.

        Returns:
            LeontiefInverse with the total requirements matrix.

        Raises:
            numpy.linalg.LinAlgError: If (I - A) is singular.
        """
        ...

    def total_labor_coefficients(
        self, leontief: LeontiefInverse, direct_labor: np.ndarray
    ) -> np.ndarray:
        """Compute total labor (direct + indirect) per unit of final demand.

        Args:
            leontief: LeontiefInverse matrix.
            direct_labor: Direct labor coefficients per industry, shape (n,).

        Returns:
            Total labor coefficients, shape (n,): l_total = l_direct @ L.
        """
        ...


@runtime_checkable
class ImperialRentComputer(Protocol):
    """Protocol for computing the imperial rent field from geographic flows.

    Example:
        >>> computer = DefaultImperialRentComputer()
        >>> rent_field = computer.compute_rent_field(flow)
        >>> abs(rent_field.phi.sum()) < total_flow * 0.001
    """

    def compute_rent_field(self, flow: GeographicFlow) -> ImperialRentField:
        """Compute net value extraction (inflow - outflow) per area.

        Args:
            flow: GeographicFlow with O-D matrix.

        Returns:
            ImperialRentField with phi vector (positive = extracting core,
            negative = donating periphery).
        """
        ...

    def decompose_symmetric_antisymmetric(
        self, flow: GeographicFlow
    ) -> tuple[np.ndarray, np.ndarray]:
        """Decompose F into symmetric (exchange) and antisymmetric (extraction).

        S = (F + F^T) / 2  (symmetric: mutual exchange)
        A = (F - F^T) / 2  (antisymmetric: net extraction)

        Args:
            flow: GeographicFlow with O-D matrix F.

        Returns:
            Tuple of (S, A) as dense numpy arrays.
        """
        ...


@runtime_checkable
class DepartmentAggregator(Protocol):
    """Protocol for aggregating BEA industries to 4 Marxian departments.

    Applies a TOML-defined mapping to reduce ~70 industries to 4 departments
    using weighted aggregation (weights = industry output shares).

    Example:
        >>> aggregator = DefaultDepartmentAggregator()
        >>> dept_flow = aggregator.aggregate(flow, aggregator.get_default_mapping())
        >>> dept_flow.n_industries == 4
        True
    """

    def aggregate(self, flow: InterIndustryFlow, mapping: dict[str, str]) -> InterIndustryFlow:
        """Produce a 4x4 department-level I-O matrix.

        Args:
            flow: InterIndustryFlow with industry-level coefficients.
            mapping: Dict mapping BEA industry code -> Department enum value.

        Returns:
            InterIndustryFlow with 4 departments as industries.
        """
        ...

    def get_default_mapping(self) -> dict[str, str]:
        """Load the BEA-to-department mapping from TOML data file.

        Returns:
            Dict mapping BEA Summary industry code -> Department value string.
        """
        ...


__all__ = [
    "ClassTransitionSource",
    "DepartmentAggregator",
    "GeographicFlowSource",
    "ImperialRentComputer",
    "InterIndustryFlowSource",
    "LeontiefComputer",
    "ReproductionSource",
    "VisibilitySource",
]
