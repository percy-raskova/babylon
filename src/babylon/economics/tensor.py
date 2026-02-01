"""Marxian value tensor models for the Babylon simulation.

This module provides Pydantic models representing the 4x3 Marxian reproduction
schema: 4 departments (I, IIa, IIb, III) x 3 value categories (c, v, s).

Departments:
    I   = Means of Production (consumed productively by capital)
    IIa = Necessary Consumption (wage goods for proletariat reproduction)
    IIb = Luxury Consumption (surplus value sink, bourgeois consumption)
    III = Social Reproduction (produces labor power itself)

Value Categories:
    c = Constant capital (dead labor: machinery, raw materials)
    v = Variable capital (living labor: wages)
    s = Surplus value (unpaid labor extracted from workers)

Example:
    >>> from babylon.economics.tensor import DepartmentRow, ValueTensor4x3
    >>> dept_I = DepartmentRow(c=300.0, v=100.0, s=200.0)
    >>> dept_I.organic_composition  # c/v
    3.0
    >>> dept_I.exploitation_rate  # s/v
    2.0

See Also:
    :mod:`babylon.economics.hydrator`: Transforms QCEW data into tensors.
    :mod:`babylon.economics.department_mapper`: Maps NAICS codes to departments.
    :class:`NoDataSentinel`: Marker for missing tensor data.
"""

from __future__ import annotations

import re
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from babylon.models.types import LaborHours, Probability, SignedLaborHours

# =============================================================================
# NO DATA SENTINEL
# =============================================================================


class NoDataSentinel:
    """Marker for missing tensor data.

    This sentinel object is returned when tensor data is unavailable for a
    given FIPS/year combination. It is falsy (bool(sentinel) == False) to
    enable clean consumer patterns using the walrus operator.

    The sentinel pattern allows distinguishing between:
    - Valid zero values (a county legitimately has zero activity)
    - Missing data (no QCEW data exists for this county-year)

    Args:
        fips: The FIPS code that was queried.
        year: The year that was queried.
        reason: Human-readable explanation of why data is missing.

    Example:
        >>> sentinel = NoDataSentinel("99999", 2022, "FIPS code not in database")
        >>> bool(sentinel)
        False
        >>> if tensor := registry.get("26163", 2022):
        ...     print(tensor.profit_rate)
        ... else:
        ...     print(f"No data: {tensor.reason}")

    Note:
        Reason format follows the pattern "{context}: {specific_reason}".
        Example: "get(26163, 2022): No QCEW data available for this county-year"
    """

    __slots__: Final = ("fips", "year", "reason")

    def __init__(self, fips: str, year: int, reason: str) -> None:
        """Initialize a NoDataSentinel.

        Args:
            fips: The 5-digit FIPS code that was queried.
            year: The calendar year that was queried.
            reason: Human-readable explanation for missing data.
        """
        self.fips: Final[str] = fips
        self.year: Final[int] = year
        self.reason: Final[str] = reason

    def __bool__(self) -> bool:
        """Return False to enable walrus operator pattern.

        This allows clean code like:
            if tensor := registry.get(fips, year):
                use(tensor)
            else:
                handle_missing(tensor.reason)

        Returns:
            Always False - sentinels represent missing data.
        """
        return False

    def __repr__(self) -> str:
        """Return a detailed string representation.

        Returns:
            String showing fips, year, and reason.
        """
        return f"NoDataSentinel(fips={self.fips!r}, year={self.year}, reason={self.reason!r})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another sentinel.

        Args:
            other: Another object to compare.

        Returns:
            True if other is a NoDataSentinel with same fips, year, reason.
        """
        if not isinstance(other, NoDataSentinel):
            return NotImplemented
        return self.fips == other.fips and self.year == other.year and self.reason == other.reason

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts.

        Returns:
            Hash based on fips, year, and reason.
        """
        return hash((self.fips, self.year, self.reason))


class DepartmentRow(BaseModel):
    """Value composition for a single Marxian department.

    Represents the three-fold decomposition of commodity value in labor-hours:
    - c (constant capital): Dead labor transferred from machinery/materials
    - v (variable capital): Living labor time paid as wages
    - s (surplus value): Unpaid labor time appropriated by capital

    All values are measured in labor-hours (LaborHours type), not monetary units.
    This follows Marx's labor theory of value where all economic quantities are
    ultimately reducible to socially necessary labor time (SNLT).

    Args:
        c: Constant capital in labor-hours (non-negative).
        v: Variable capital in labor-hours (non-negative).
        s: Surplus value in labor-hours (non-negative).

    Example:
        >>> row = DepartmentRow(c=100.0, v=50.0, s=75.0)
        >>> row.total_value
        225.0
        >>> row.organic_composition  # c/v = 100/50
        2.0
        >>> row.exploitation_rate  # s/v = 75/50
        1.5
    """

    model_config = ConfigDict(frozen=True)

    c: LaborHours = Field(description="Constant capital (dead labor: machinery, raw materials)")
    v: LaborHours = Field(description="Variable capital (living labor: wages)")
    s: LaborHours = Field(description="Surplus value (unpaid labor)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_value(self) -> LaborHours:
        """Total commodity value (c + v + s) in labor-hours.

        Returns:
            Sum of constant capital, variable capital, and surplus value.
        """
        return LaborHours(self.c + self.v + self.s)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def organic_composition(self) -> float:
        """Organic composition of capital (c/v).

        Marx's measure of capital intensity: ratio of dead labor (machinery)
        to living labor (workers). Higher OCC indicates more mechanization.

        Returns:
            c/v ratio, or float('inf') if v=0.
        """
        if self.v == 0.0:
            return float("inf")
        return self.c / self.v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exploitation_rate(self) -> float:
        """Rate of exploitation (s/v).

        The ratio of unpaid labor to paid labor. A rate of 1.0 means workers
        spend equal time producing value they keep vs. value extracted.

        Returns:
            s/v ratio, or float('inf') if v=0.
        """
        if self.v == 0.0:
            return float("inf")
        return self.s / self.v


# FIPS code pattern: exactly 5 digits
_FIPS_PATTERN = re.compile(r"^\d{5}$")


class ValueTensor4x3(BaseModel):
    """4x3 Marxian value tensor for a county-year.

    Represents the complete reproduction schema with four departments,
    each decomposed into constant capital (c), variable capital (v),
    and surplus value (s).

    Args:
        fips_code: 5-digit FIPS county code (e.g., "26163" for Wayne County).
        year: Data year (must be >= 1900).
        dept_I: Department I (Means of Production).
        dept_IIa: Department IIa (Necessary Consumption).
        dept_IIb: Department IIb (Luxury Consumption).
        dept_III: Department III (Social Reproduction).
        naics_granularity: Data quality metric [0, 1] indicating NAICS coverage.
        excluded_wages: Wages excluded from allocation (e.g., NAICS 92 government).

    Example:
        >>> tensor = ValueTensor4x3(
        ...     fips_code="26163",
        ...     year=2022,
        ...     dept_I=DepartmentRow(c=300.0, v=100.0, s=200.0),
        ...     dept_IIa=DepartmentRow(c=150.0, v=100.0, s=100.0),
        ...     dept_IIb=DepartmentRow(c=250.0, v=100.0, s=300.0),
        ...     dept_III=DepartmentRow(c=50.0, v=100.0, s=70.0),
        ...     naics_granularity=0.85,
        ...     excluded_wages=50000.0,
        ... )
        >>> tensor.profit_rate  # total_s / (total_c + total_v)
        0.5826086956521739
    """

    model_config = ConfigDict(frozen=True)

    fips_code: Annotated[
        str,
        Field(
            min_length=5,
            max_length=5,
            description="5-digit FIPS county code",
        ),
    ]
    year: Annotated[
        int,
        Field(
            ge=1900,
            description="Data year (QCEW data starts 1975)",
        ),
    ]

    dept_I: DepartmentRow = Field(description="Department I: Means of Production (capital goods)")
    dept_IIa: DepartmentRow = Field(
        description="Department IIa: Necessary Consumption (wage goods)"
    )
    dept_IIb: DepartmentRow = Field(
        description="Department IIb: Luxury Consumption (bourgeois goods)"
    )
    dept_III: DepartmentRow = Field(description="Department III: Social Reproduction (care work)")

    naics_granularity: Probability = Field(
        description="Data quality: fraction of wages with 6-digit NAICS mapping"
    )
    excluded_wages: LaborHours = Field(
        description="Wages excluded from allocation (e.g., government NAICS 92)"
    )

    visibility_g33: Annotated[float, Field(default=1.0, ge=0.0, le=1.0)] = 1.0
    """Visibility scalar for Department III reproductive labor.

    Controls what fraction of care work is visible to the price system:
    - 1.0 = fully monetized (backward compatible default)
    - 0.0 = fully unwaged (all shadow labor)
    - 0.5 = half visible, half shadow (typical estimate)

    Based on Fortunati's "The Arcane of Reproduction" (1981).
    """

    @field_validator("fips_code")
    @classmethod
    def validate_fips_numeric(cls, v: str) -> str:
        """Validate FIPS code is numeric (digits only)."""
        if not _FIPS_PATTERN.match(v):
            msg = f"FIPS code must be exactly 5 digits, got: {v!r}"
            raise ValueError(msg)
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_value(self) -> LaborHours:
        """Total value across all departments in labor-hours.

        Returns:
            Sum of all department total_values.
        """
        return LaborHours(
            self.dept_I.total_value
            + self.dept_IIa.total_value
            + self.dept_IIb.total_value
            + self.dept_III.total_value
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_c(self) -> LaborHours:
        """Total constant capital (dead labor) across all departments.

        This represents the aggregate machinery, raw materials, and other
        means of production consumed across all four departments.

        Returns:
            Sum of c (constant capital) across all departments.
        """
        return LaborHours(self.dept_I.c + self.dept_IIa.c + self.dept_IIb.c + self.dept_III.c)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_v(self) -> LaborHours:
        """Total variable capital (wages) across all departments in labor-hours.

        This represents the aggregate wage bill for the county - the total
        living labor employed across all four departments of production.

        Returns:
            Sum of v (variable capital) across all departments.
        """
        return LaborHours(self.dept_I.v + self.dept_IIa.v + self.dept_IIb.v + self.dept_III.v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_s(self) -> LaborHours:
        """Total surplus value across all departments in labor-hours.

        Returns:
            Sum of s (surplus value) across all departments.
        """
        return LaborHours(self.dept_I.s + self.dept_IIa.s + self.dept_IIb.s + self.dept_III.s)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def profit_rate(self) -> float:
        """Average rate of profit across all departments.

        Computed as total_s / (total_c + total_v), representing the
        economy-wide return on capital investment.

        Returns:
            Profit rate (s / (c + v)), or float('inf') if (c + v) = 0.
        """
        denominator = self.total_c + self.total_v
        if denominator == 0.0:
            return float("inf")
        return self.total_s / denominator

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exploitation_rate(self) -> float:
        """Aggregate rate of exploitation across all departments.

        The ratio of unpaid labor (surplus value) to paid labor (variable capital)
        across the entire county economy. A rate of 1.0 means workers spend equal
        time producing value they keep vs. value extracted by capital.

        Formula: e = total_s / total_v

        Returns:
            Exploitation rate (s/v), or float('inf') if total_v = 0.
        """
        if self.total_v == 0.0:
            return float("inf")
        return self.total_s / self.total_v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def organic_composition(self) -> float:
        """Aggregate organic composition of capital across all departments.

        Marx's measure of capital intensity: ratio of dead labor (machinery,
        materials) to living labor (workers). Higher OCC indicates more
        mechanization and capital-intensive production.

        Formula: OCC = total_c / total_v

        Returns:
            Organic composition (c/v), or float('inf') if total_v = 0.
        """
        if self.total_v == 0.0:
            return float("inf")
        return self.total_c / self.total_v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def imperial_rent(self) -> SignedLaborHours:
        """Imperial rent extracted from or donated to the global system.

        Per MLM-TW theory, imperial rent (Φ) represents the value transfer
        between core and periphery in the world-system:

        Formula: Φ = total_v - total_value

        Interpretation:
        - Φ > 0 (positive): Core position - receiving rent from periphery.
          Workers are paid MORE than the value they produce, subsidized by
          unequal exchange with the periphery.
        - Φ < 0 (negative): Peripheral position - donating rent to core.
          Workers produce MORE value than they receive in wages, with the
          surplus extracted via unequal exchange.
        - Φ ≈ 0: Semi-peripheral or autarkic position.

        Returns:
            Imperial rent in signed labor-hours (can be negative).

        See Also:
            :func:`babylon.formulas.calculate_imperial_rent`: Formula documentation.
        """
        return SignedLaborHours(self.total_v - self.total_value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def monetized_value(self) -> LaborHours:
        """Total value visible to the price system in labor-hours.

        Includes full value of Depts I, IIa, IIb, but only the visible
        fraction of Dept III based on g₃₃.

        Formula: Σ(Dept_i.total) + Dept_III.total × g₃₃
                 for i ∈ {I, IIa, IIb}

        Returns:
            Total monetized value across all departments.
        """
        visible_dept_iii = self.dept_III.total_value * self.visibility_g33
        return LaborHours(
            self.dept_I.total_value
            + self.dept_IIa.total_value
            + self.dept_IIb.total_value
            + visible_dept_iii
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def monetized_v(self) -> LaborHours:
        """Total variable capital actually paid as wages in labor-hours.

        Includes full v from Depts I, IIa, IIb, but only the visible
        fraction of Dept III v based on g₃₃.

        Formula: v_I + v_IIa + v_IIb + (v_III × g₃₃)

        Returns:
            Total wages actually paid (monetized variable capital).
        """
        visible_dept_iii_v = self.dept_III.v * self.visibility_g33
        return LaborHours(self.dept_I.v + self.dept_IIa.v + self.dept_IIb.v + visible_dept_iii_v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def shadow_subsidy(self) -> LaborHours:
        """Unpaid reproductive labor appropriated as surplus in labor-hours.

        In Fortunati's framework, shadow labor is NOT merely "unpaid costs" -
        it is **appropriated surplus value**. The capitalist class benefits
        twice: they pay less V, AND they capture the surplus labor time of
        the reproduction sphere.

        Formula: Dept_III.v × (1 - g₃₃)

        When g₃₃=1.0, shadow_subsidy=0 (all care work is paid).
        When g₃₃=0.0, shadow_subsidy=Dept_III.v (all care work unpaid).

        Returns:
            Shadow subsidy (unpaid reproductive labor value).
        """
        return LaborHours(self.dept_III.v * (1 - self.visibility_g33))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exploitation_rate_fortunati(self) -> float:
        """Expanded exploitation rate including shadow labor as appropriated surplus.

        The Fortunati rate recognizes that unpaid domestic labor is NOT
        merely a cost reduction but is **appropriated surplus value**.
        Capital extracts labor time from the reproductive sphere without
        any compensation whatsoever.

        Formula: e' = (S_total + shadow_subsidy) / monetized_v

        Example (Dept III only, v=100, s=100, g₃₃=0.5):
            - monetized_v = 50 (half paid)
            - shadow_subsidy = 50 (half unpaid → appropriated surplus)
            - total_surplus = 100 + 50 = 150
            - Fortunati rate = 150 / 50 = 300%
            - (Standard rate would be 100/100 = 100%)

        When g₃₃=1.0, equals standard exploitation_rate (total_s/total_v).
        When g₃₃<1.0, rate increases dramatically as shadow labor is recognized.

        Returns:
            Fortunati exploitation rate, or float('inf') if monetized_v = 0.

        See Also:
            Fortunati, Leopoldina. "The Arcane of Reproduction" (1981).
        """
        if self.monetized_v == 0.0:
            return float("inf")
        numerator = self.total_s + self.shadow_subsidy
        return float(numerator / self.monetized_v)


__all__ = [
    "DepartmentRow",
    "NoDataSentinel",
    "ValueTensor4x3",
]
