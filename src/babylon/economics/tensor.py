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
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from babylon.models.types import Currency, Probability


class DepartmentRow(BaseModel):
    """Value composition for a single Marxian department.

    Represents the three-fold decomposition of commodity value:
    - c (constant capital): Value transferred from machinery/materials
    - v (variable capital): Value paid to workers as wages
    - s (surplus value): Unpaid labor appropriated by capital

    Args:
        c: Constant capital (non-negative Currency).
        v: Variable capital (non-negative Currency).
        s: Surplus value (non-negative Currency).

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

    c: Currency = Field(description="Constant capital (dead labor: machinery, raw materials)")
    v: Currency = Field(description="Variable capital (living labor: wages)")
    s: Currency = Field(description="Surplus value (unpaid labor)")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_value(self) -> Currency:
        """Total commodity value (c + v + s).

        Returns:
            Sum of constant capital, variable capital, and surplus value.
        """
        return self.c + self.v + self.s

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
    excluded_wages: Currency = Field(
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
    def total_value(self) -> Currency:
        """Total value across all departments.

        Returns:
            Sum of all department total_values.
        """
        return (
            self.dept_I.total_value
            + self.dept_IIa.total_value
            + self.dept_IIb.total_value
            + self.dept_III.total_value
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_v(self) -> Currency:
        """Total variable capital (wages) across all departments.

        This represents the aggregate wage bill for the county - the total
        living labor employed across all four departments of production.

        Returns:
            Sum of v (variable capital) across all departments.
        """
        return self.dept_I.v + self.dept_IIa.v + self.dept_IIb.v + self.dept_III.v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_s(self) -> Currency:
        """Total surplus value across all departments.

        Returns:
            Sum of s (surplus value) across all departments.
        """
        return Currency(self.dept_I.s + self.dept_IIa.s + self.dept_IIb.s + self.dept_III.s)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def profit_rate(self) -> float:
        """Average rate of profit across all departments.

        Computed as total_s / (total_c + total_v), representing the
        economy-wide return on capital investment.

        Returns:
            Profit rate (s / (c + v)), or float('inf') if (c + v) = 0.
        """
        total_c = self.dept_I.c + self.dept_IIa.c + self.dept_IIb.c + self.dept_III.c
        denominator = total_c + self.total_v
        if denominator == 0.0:
            return float("inf")
        return self.total_s / denominator

    @computed_field  # type: ignore[prop-decorator]
    @property
    def monetized_value(self) -> Currency:
        """Total value visible to the price system.

        Includes full value of Depts I, IIa, IIb, but only the visible
        fraction of Dept III based on g₃₃.

        Formula: Σ(Dept_i.total) + Dept_III.total × g₃₃
                 for i ∈ {I, IIa, IIb}

        Returns:
            Total monetized value across all departments.
        """
        visible_dept_iii = self.dept_III.total_value * self.visibility_g33
        return Currency(
            self.dept_I.total_value
            + self.dept_IIa.total_value
            + self.dept_IIb.total_value
            + visible_dept_iii
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def monetized_v(self) -> Currency:
        """Total variable capital actually paid as wages.

        Includes full v from Depts I, IIa, IIb, but only the visible
        fraction of Dept III v based on g₃₃.

        Formula: v_I + v_IIa + v_IIb + (v_III × g₃₃)

        Returns:
            Total wages actually paid (monetized variable capital).
        """
        visible_dept_iii_v = self.dept_III.v * self.visibility_g33
        return Currency(self.dept_I.v + self.dept_IIa.v + self.dept_IIb.v + visible_dept_iii_v)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def shadow_subsidy(self) -> Currency:
        """Unpaid reproductive labor appropriated as surplus.

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
        return Currency(self.dept_III.v * (1 - self.visibility_g33))

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
    "ValueTensor4x3",
]
