"""Type definitions for the Tensor Hierarchy module.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Defines Level 1 and Level 2 tensor types for multi-level economic analysis.

Level 1 (from federal data):
    - InterIndustryFlow: BEA I-O coefficient matrix
    - VisibilityMetric: Gamma diagonal visibility
    - GeographicFlow: BTS FAF O-D flow matrix
    - ReproductionRequirements: CEX + ATUS requirements by class
    - ClassTransitionMatrix: PSID-based class mobility

Level 2 (derived):
    - LeontiefInverse: (I - A)^{-1}
    - ImperialRentField: Net value extraction per CFS area
    - ShadowSubsidyTensor: Dept III × (1 - g_33)
    - StationaryDistribution: Long-run class distribution

See Also:
    :mod:`babylon.economics.tensor`: Level 0 ValueTensor4x3 primitive.
    :mod:`babylon.economics.tensor_hierarchy.protocols`: Source protocols.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# =============================================================================
# ENUMS
# =============================================================================


class IOTableType(StrEnum):
    """BEA input-output table type classification.

    Controls which BEA I-O table a coefficient matrix was derived from.

    Values:
        USE: Use table (commodity-by-industry intermediate use).
        MAKE: Make table (industry-by-commodity output).
        SUPPLY: Supply table (total supply of commodities).
        TOTAL_REQ: Total requirements (Leontief inverse from BEA).

    Example:
        >>> IOTableType.USE
        <IOTableType.USE: 'USE'>
        >>> IOTableType.USE.value
        'USE'
    """

    USE = "USE"
    MAKE = "MAKE"
    SUPPLY = "SUPPLY"
    TOTAL_REQ = "TOTAL_REQ"


class Department(StrEnum):
    """Marxian department classification for industry aggregation.

    Four departments of social reproduction:
        I: Means of Production (capital goods, investment)
        IIA: Necessary Consumption (wage goods, food, shelter)
        IIB: Luxury Consumption (bourgeois consumption)
        III: Social Reproduction (care, education, health)

    Example:
        >>> Department.I
        <Department.I: 'I'>
    """

    I = "I"  # noqa: E741
    IIA = "IIA"
    IIB = "IIB"
    III = "III"


# =============================================================================
# NUMPY ARRAY VALIDATOR HELPER
# =============================================================================


def _to_ndarray(v: object) -> np.ndarray:
    """Convert list or array to numpy float64 ndarray.

    Args:
        v: Input value (list or ndarray).

    Returns:
        numpy float64 ndarray.

    Raises:
        ValueError: If conversion fails.
    """
    if isinstance(v, np.ndarray):
        return v.astype(np.float64)
    try:
        return np.array(v, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        msg = f"Cannot convert {type(v).__name__} to ndarray: {exc}"
        raise ValueError(msg) from exc


# =============================================================================
# LEVEL 1: INTER-INDUSTRY FLOW
# =============================================================================


class InterIndustryFlow(BaseModel):
    """BEA input-output direct requirements coefficient matrix.

    Represents the A matrix where A[i,j] is the dollar value of industry i's
    output required per dollar of industry j's output (direct requirements).

    For a productive economy all column sums < 1.0 (Hawkins-Simon condition).

    Args:
        year: BEA data year (>= 1997 when I-O tables begin).
        table_type: Which BEA table this was derived from.
        industries: Ordered list of BEA industry codes (Summary level).
        coefficients: Square coefficient matrix, shape (n, n).

    Example:
        >>> import numpy as np
        >>> flow = InterIndustryFlow(
        ...     year=2021,
        ...     table_type=IOTableType.USE,
        ...     industries=["1100A1", "327C00"],
        ...     coefficients=np.array([[0.1, 0.2], [0.15, 0.05]]),
        ... )
        >>> flow.n_industries
        2
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=1997, description="BEA data year")]
    table_type: IOTableType = Field(description="Source BEA table type")
    industries: list[str] = Field(description="Ordered BEA industry codes at Summary level")
    coefficients: np.ndarray = Field(description="Direct requirements matrix, shape (n, n)")

    @field_validator("coefficients", mode="before")
    @classmethod
    def coerce_coefficients(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_shape(self) -> InterIndustryFlow:
        """Validate matrix is square and matches industry list length."""
        n = len(self.industries)
        if self.coefficients.shape != (n, n):
            msg = (
                f"coefficients shape {self.coefficients.shape} "
                f"must be ({n}, {n}) to match {n} industries"
            )
            raise ValueError(msg)
        return self

    @property
    def n_industries(self) -> int:
        """Number of industries in the matrix."""
        return len(self.industries)


# =============================================================================
# LEVEL 1: VISIBILITY METRIC
# =============================================================================


class VisibilityMetric(BaseModel):
    """Diagonal visibility tensor for the four Marxian departments.

    Represents the fraction of each department's labor that is visible
    to the price system (commodified). Based on Fortunati (1981).

    Args:
        year: Data year (>= 2003, ATUS availability).
        g_diagonal: Shape (4,) array [g_11, g_22a, g_22b, g_33].
        g_11: Department I visibility (capital goods, expected ≈ 1.0).
        g_22a: Department IIa visibility (wage goods, expected ≈ 1.0).
        g_22b: Department IIb visibility (luxury goods, expected ≈ 1.0).
        g_33: Department III visibility (care work, expected < 0.5).
        is_estimated: True if using MVP/estimated gamma values.

    Example:
        >>> import numpy as np
        >>> vm = VisibilityMetric(
        ...     year=2022,
        ...     g_diagonal=np.array([1.0, 1.0, 1.0, 0.333]),
        ...     g_11=1.0, g_22a=1.0, g_22b=1.0, g_33=0.333,
        ...     is_estimated=True,
        ... )
        >>> vm.g_33 < vm.g_11
        True
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=2003, description="Data year (ATUS from 2003)")]
    g_diagonal: np.ndarray = Field(description="Visibility diagonal [g_11, g_22a, g_22b, g_33]")
    g_11: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Dept I visibility (capital goods)"
    )
    g_22a: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Dept IIa visibility (wage goods)"
    )
    g_22b: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Dept IIb visibility (luxury goods)"
    )
    g_33: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="Dept III visibility (reproductive care)"
    )
    is_estimated: bool = Field(default=False, description="True if using estimated/MVP values")

    @field_validator("g_diagonal", mode="before")
    @classmethod
    def coerce_g_diagonal(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray of shape (4,)."""
        arr = _to_ndarray(v)
        if arr.shape != (4,):
            msg = f"g_diagonal must have shape (4,), got {arr.shape}"
            raise ValueError(msg)
        return arr


# =============================================================================
# LEVEL 1: GEOGRAPHIC FLOW
# =============================================================================


class GeographicFlow(BaseModel):
    """BTS FAF origin-destination commodity flow matrix.

    Represents flows between CFS Areas (~130 geographic zones used by
    the Bureau of Transportation Statistics for freight analysis).

    The flow_matrix is a dense ndarray for compatibility with Pydantic
    frozen models (scipy sparse matrices are not directly serializable).
    For computation the matrix should be converted to scipy.sparse.

    Args:
        year: FAF data year (>= 2012 for FAF5 data).
        areas: Ordered list of CFS Area codes.
        flow_matrix: O-D matrix, shape (n, n), values in millions USD.
        commodity_code: SCTG code or None for all-commodity aggregate.

    Example:
        >>> import numpy as np
        >>> gf = GeographicFlow(
        ...     year=2017,
        ...     areas=["11", "12"],
        ...     flow_matrix=np.array([[100.0, 50.0], [30.0, 200.0]]),
        ... )
        >>> gf.n_areas
        2
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=2012, description="FAF data year (FAF5 from 2012)")]
    areas: list[str] = Field(description="Ordered CFS Area codes (~130 areas)")
    flow_matrix: np.ndarray = Field(
        description="O-D flow matrix, shape (n, n), values in millions USD"
    )
    commodity_code: str | None = Field(
        default=None,
        description="SCTG code for commodity-specific flows, None for aggregate",
    )

    @field_validator("flow_matrix", mode="before")
    @classmethod
    def coerce_flow_matrix(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_shape(self) -> GeographicFlow:
        """Validate matrix is square and matches areas list length."""
        n = len(self.areas)
        if self.flow_matrix.shape != (n, n):
            msg = (
                f"flow_matrix shape {self.flow_matrix.shape} must be ({n}, {n}) to match {n} areas"
            )
            raise ValueError(msg)
        return self

    @property
    def n_areas(self) -> int:
        """Number of CFS areas in the matrix."""
        return len(self.areas)


# =============================================================================
# LEVEL 1: REPRODUCTION REQUIREMENTS
# =============================================================================


class ReproductionRequirements(BaseModel):
    """Consumption and reproductive labor requirements by social class.

    Represents the use-value bundles needed to reproduce each class
    across the four Marxian departments (CEX + ATUS data).

    Args:
        year: Data year.
        consumption: class -> department -> use_value_category -> labor_hours.
        reproductive_labor: reproduced_class -> laborer_class -> type -> hours.

    Note:
        Production loaders are deferred (US4). Tests use synthetic data.
    """

    model_config = ConfigDict(frozen=True)

    year: Annotated[int, Field(ge=2000, description="Data year")]
    consumption: dict[str, dict[str, dict[str, float]]] = Field(
        description="Consumption by class, department, use-value category"
    )
    reproductive_labor: dict[str, dict[str, dict[str, float]]] = Field(
        description="Reproductive labor hours by class and type"
    )


# =============================================================================
# LEVEL 1: CLASS TRANSITION MATRIX
# =============================================================================


class ClassTransitionMatrix(BaseModel):
    """Stochastic matrix of class mobility probabilities.

    P[i,j] is the probability that someone in class i at period start
    is in class j at period end (rows sum to 1.0).

    Args:
        period: (start_year, end_year) tuple defining the transition window.
        classes: Ordered list of SocialRole values.
        transition_matrix: Stochastic matrix, shape (n, n), rows sum to 1.0.

    Note:
        Production loader deferred (US5). Tests use synthetic data.

    Example:
        >>> import numpy as np
        >>> ctm = ClassTransitionMatrix(
        ...     period=(2015, 2020),
        ...     classes=["proletariat", "petit_bourgeois"],
        ...     transition_matrix=np.array([[0.9, 0.1], [0.3, 0.7]]),
        ... )
        >>> ctm.n_classes
        2
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    period: tuple[int, int] = Field(description="(start_year, end_year) of the transition period")
    classes: list[str] = Field(description="Ordered list of SocialRole class names")
    transition_matrix: np.ndarray = Field(
        description="Stochastic matrix, shape (n, n), each row sums to 1.0"
    )

    @field_validator("transition_matrix", mode="before")
    @classmethod
    def coerce_transition_matrix(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_stochastic(self) -> ClassTransitionMatrix:
        """Validate shape and row-stochastic property (rows sum to 1.0)."""
        n = len(self.classes)
        if self.transition_matrix.shape != (n, n):
            msg = (
                f"transition_matrix shape {self.transition_matrix.shape} "
                f"must be ({n}, {n}) to match {n} classes"
            )
            raise ValueError(msg)
        row_sums = self.transition_matrix.sum(axis=1)
        if not np.allclose(row_sums, 1.0, atol=1e-6):
            msg = f"transition_matrix rows must sum to 1.0 (got {row_sums})"
            raise ValueError(msg)
        return self

    @property
    def n_classes(self) -> int:
        """Number of classes in the transition matrix."""
        return len(self.classes)


# =============================================================================
# LEVEL 2: LEONTIEF INVERSE
# =============================================================================


class LeontiefInverse(BaseModel):
    """Total requirements matrix L = (I - A)^{-1}.

    The Leontief inverse captures both direct and indirect supply chain
    requirements. L[i,j] is the total output of industry i required
    (directly and indirectly) per unit of final demand for industry j.

    All elements >= 0. Diagonal elements >= 1.0.

    Args:
        year: Same as source InterIndustryFlow year.
        industries: Same as source InterIndustryFlow industries.
        inverse_matrix: Total requirements matrix, shape (n, n).

    Example:
        >>> import numpy as np
        >>> li = LeontiefInverse(
        ...     year=2021,
        ...     industries=["1100A1", "327C00"],
        ...     inverse_matrix=np.array([[1.15, 0.25], [0.18, 1.08]]),
        ... )
        >>> li.n_industries
        2
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=1997, description="Data year")]
    industries: list[str] = Field(description="Ordered BEA industry codes")
    inverse_matrix: np.ndarray = Field(
        description="Leontief inverse matrix (I-A)^{-1}, shape (n, n)"
    )

    @field_validator("inverse_matrix", mode="before")
    @classmethod
    def coerce_inverse_matrix(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_shape(self) -> LeontiefInverse:
        """Validate matrix shape matches industry list."""
        n = len(self.industries)
        if self.inverse_matrix.shape != (n, n):
            msg = (
                f"inverse_matrix shape {self.inverse_matrix.shape} "
                f"must be ({n}, {n}) to match {n} industries"
            )
            raise ValueError(msg)
        return self

    @property
    def n_industries(self) -> int:
        """Number of industries in the matrix."""
        return len(self.industries)


# =============================================================================
# LEVEL 2: IMPERIAL RENT FIELD
# =============================================================================


class ImperialRentField(BaseModel):
    """Net value extraction (inflow - outflow) per CFS area.

    phi[a] = sum of all inflows to area a - sum of all outflows from area a.
    For a closed system sum(phi) ≈ 0.

    Positive phi: Area extracts value (core/accumulation zone).
    Negative phi: Area loses value (periphery/extraction zone).

    Args:
        year: Same as source GeographicFlow year.
        areas: Same as source GeographicFlow areas.
        phi: Net value extraction vector, shape (n_areas,), signed.

    Example:
        >>> import numpy as np
        >>> irf = ImperialRentField(
        ...     year=2017,
        ...     areas=["11", "12"],
        ...     phi=np.array([50.0, -50.0]),
        ... )
        >>> abs(irf.phi.sum()) < 1e-6
        True
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=2012, description="Data year")]
    areas: list[str] = Field(description="Ordered CFS Area codes")
    phi: np.ndarray = Field(
        description="Net value extraction per area (inflow - outflow), millions USD"
    )

    @field_validator("phi", mode="before")
    @classmethod
    def coerce_phi(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_shape(self) -> ImperialRentField:
        """Validate phi shape matches areas list."""
        n = len(self.areas)
        if self.phi.shape != (n,):
            msg = f"phi shape {self.phi.shape} must be ({n},) to match {n} areas"
            raise ValueError(msg)
        return self

    @property
    def n_areas(self) -> int:
        """Number of CFS areas."""
        return len(self.areas)


# =============================================================================
# LEVEL 2: SHADOW SUBSIDY TENSOR
# =============================================================================


class ShadowSubsidyTensor(BaseModel):
    """Shadow subsidy from unvisibilized reproductive labor.

    Wraps the gamma module's shadow subsidy computation for use in
    the tensor hierarchy. Distinct from the gamma module's ShadowSubsidy
    type to avoid circular imports.

    Args:
        year: Reference year.
        phi_iii_labor_hours: Dept III value × (1 - g_33) in labor-hours.
        phi_iii_dollars: Dollars value if MELT available, else None.
        melt_available: True if MELT was used for conversion.

    Example:
        >>> ss = ShadowSubsidyTensor(
        ...     year=2022,
        ...     phi_iii_labor_hours=22.0,
        ...     phi_iii_dollars=None,
        ...     melt_available=False,
        ... )
        >>> ss.phi_iii_labor_hours
        22.0
    """

    model_config = ConfigDict(frozen=True)

    year: Annotated[int, Field(ge=2000, description="Reference year")]
    phi_iii_labor_hours: Annotated[float, Field(ge=0.0)] = Field(
        description="Shadow subsidy in labor-hours: Dept_III_value × (1 - g_33)"
    )
    phi_iii_dollars: float | None = Field(
        default=None,
        description="Shadow subsidy in dollars (if MELT available)",
    )
    melt_available: bool = Field(default=False, description="Whether MELT was available")


# =============================================================================
# LEVEL 2: STATIONARY DISTRIBUTION
# =============================================================================


class StationaryDistribution(BaseModel):
    """Long-run class distribution from ClassTransitionMatrix eigenvector.

    The stationary distribution pi satisfies pi @ P = pi, normalized to sum=1.
    Computed as the dominant eigenvector of P^T (eigenvalue = 1.0).

    Args:
        period: Same as source ClassTransitionMatrix period.
        classes: Same as source ClassTransitionMatrix classes.
        distribution: Stationary distribution, shape (n_classes,), sums to 1.0.

    Example:
        >>> import numpy as np
        >>> sd = StationaryDistribution(
        ...     period=(2015, 2020),
        ...     classes=["proletariat", "petit_bourgeois"],
        ...     distribution=np.array([0.75, 0.25]),
        ... )
        >>> abs(sd.distribution.sum() - 1.0) < 1e-10
        True
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    period: tuple[int, int] = Field(description="(start_year, end_year)")
    classes: list[str] = Field(description="Ordered class names")
    distribution: np.ndarray = Field(description="Stationary distribution, sums to 1.0")

    @field_validator("distribution", mode="before")
    @classmethod
    def coerce_distribution(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_distribution(self) -> StationaryDistribution:
        """Validate shape and that distribution sums to 1.0."""
        n = len(self.classes)
        if self.distribution.shape != (n,):
            msg = f"distribution shape {self.distribution.shape} must be ({n},)"
            raise ValueError(msg)
        if not np.isclose(self.distribution.sum(), 1.0, atol=1e-6):
            msg = f"distribution must sum to 1.0 (got {self.distribution.sum():.8f})"
            raise ValueError(msg)
        return self

    @property
    def n_classes(self) -> int:
        """Number of classes."""
        return len(self.classes)


# =============================================================================
# LEVEL 2: LEONTIEF PRODUCTION CHAIN RENT
# =============================================================================


class ImportShareVector(BaseModel):
    """Fraction of inputs sourced from imports per industry (m_j).

    Derived from BEA IMPORT_USE and total USE tables.

    Args:
        year: Data year.
        industries: Ordered BEA industry codes.
        shares: Vector of import fractions, shape (n,), values in [0.0, 1.0].
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=1997, description="BEA data year")]
    industries: list[str] = Field(description="Ordered BEA industry codes")
    shares: np.ndarray = Field(description="Import share fractions, shape (n,)")

    @field_validator("shares", mode="before")
    @classmethod
    def coerce_shares(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_shares(self) -> ImportShareVector:
        """Validate shape and range of shares."""
        n = len(self.industries)
        if self.shares.shape != (n,):
            msg = f"shares shape {self.shares.shape} must be ({n},)"
            raise ValueError(msg)
        if not np.all((self.shares >= 0.0) & (self.shares <= 1.0)):
            msg = "All import shares must be in range [0.0, 1.0]"
            raise ValueError(msg)
        return self


class DecomposedFlow(BaseModel):
    """Decomposed BEA coefficient matrix into domestic and import segments.

    Args:
        year: Data year.
        industries: Ordered BEA industry codes.
        A_d: Domestic coefficient matrix, shape (n, n).
        A_m: Import coefficient matrix, shape (n, n).
        L_d: Domestic Leontief inverse (I - A_d)^{-1}, shape (n, n).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=1997, description="BEA data year")]
    industries: list[str] = Field(description="Ordered BEA industry codes")
    A_d: np.ndarray = Field(description="Domestic coefficient matrix")
    A_m: np.ndarray = Field(description="Import coefficient matrix")
    L_d: np.ndarray = Field(description="Domestic Leontief inverse")

    @field_validator("A_d", "A_m", "L_d", mode="before")
    @classmethod
    def coerce_matrices(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_shapes(self) -> DecomposedFlow:
        """Validate shapes of all matrices."""
        n = len(self.industries)
        for name, matrix in (("A_d", self.A_d), ("A_m", self.A_m), ("L_d", self.L_d)):
            if matrix.shape != (n, n):
                msg = f"{name} shape {matrix.shape} must be ({n}, {n})"
                raise ValueError(msg)
        return self


class PeripheryLaborCoefficients(BaseModel):
    """Wage differentials per industry between Core and Periphery.

    Represents (w_core / w_periphery) for each industry group.

    Args:
        year: Data year.
        industries: Ordered BEA industry codes.
        wage_ratios: Vector of wage ratios, shape (n,), expected >= 1.0.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=1997, description="BEA data year")]
    industries: list[str] = Field(description="Ordered BEA industry codes")
    wage_ratios: np.ndarray = Field(description="Core-to-periphery wage ratios, shape (n,)")

    @field_validator("wage_ratios", mode="before")
    @classmethod
    def coerce_wage_ratios(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_ratios(self) -> PeripheryLaborCoefficients:
        """Validate shapes and optionally basic sanity bounds."""
        n = len(self.industries)
        if self.wage_ratios.shape != (n,):
            msg = f"wage_ratios shape {self.wage_ratios.shape} must be ({n},)"
            raise ValueError(msg)
        return self


class ProductionChainRentResult(BaseModel):
    """Imperial rent extracted via Leontief production chain.

    Args:
        year: Data year.
        industries: Ordered BEA industry codes.
        phi_vector: Vector of imperial rent extracted per industry phi_j, shape (n,).
        total_phi: Aggregate imperial rent across all industries.
        dept_phi: Rent aggregated by Marxian Department (I, IIA, IIB, III).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    year: Annotated[int, Field(ge=1997, description="Data year")]
    industries: list[str] = Field(description="Ordered BEA industry codes")
    phi_vector: np.ndarray = Field(description="Rent vector, shape (n,)")
    total_phi: float = Field(description="Total imperial rent extracted")
    dept_phi: dict[Department, float] = Field(description="Rent aggregated by Department")

    @field_validator("phi_vector", mode="before")
    @classmethod
    def coerce_phi_vector(cls, v: object) -> np.ndarray:
        """Coerce list or array to float64 ndarray."""
        return _to_ndarray(v)

    @model_validator(mode="after")
    def validate_vector(self) -> ProductionChainRentResult:
        """Validate shape matches industries."""
        n = len(self.industries)
        if self.phi_vector.shape != (n,):
            msg = f"phi_vector shape {self.phi_vector.shape} must be ({n},)"
            raise ValueError(msg)
        return self


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    "ClassTransitionMatrix",
    "DecomposedFlow",
    "Department",
    "GeographicFlow",
    "ImperialRentField",
    "ImportShareVector",
    "InterIndustryFlow",
    "IOTableType",
    "LeontiefInverse",
    "PeripheryLaborCoefficients",
    "ProductionChainRentResult",
    "ReproductionRequirements",
    "ShadowSubsidyTensor",
    "StationaryDistribution",
    "VisibilityMetric",
]
