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
    def profit_rate(self) -> float:
        """Average rate of profit across all departments.

        Computed as total_s / (total_c + total_v), representing the
        economy-wide return on capital investment.

        Returns:
            Profit rate (s / (c + v)), or float('inf') if (c + v) = 0.
        """
        total_s = self.dept_I.s + self.dept_IIa.s + self.dept_IIb.s + self.dept_III.s
        total_c = self.dept_I.c + self.dept_IIa.c + self.dept_IIb.c + self.dept_III.c
        total_v = self.dept_I.v + self.dept_IIa.v + self.dept_IIb.v + self.dept_III.v
        denominator = total_c + total_v
        if denominator == 0.0:
            return float("inf")
        return total_s / denominator


__all__ = [
    "DepartmentRow",
    "ValueTensor4x3",
]
