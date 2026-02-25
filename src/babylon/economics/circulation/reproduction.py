"""Reproduction schema analysis for Capital Volume II.

Feature: 023-capital-volume-ii
Tasks: T048-T054 (FR-012, FR-013, FR-014)

Implements Marx's reproduction schema from Capital Volume II Part III
(Chapters 18-21). The schema models inter-departmental balance conditions
required for smooth capitalist reproduction.

Simple reproduction: I(v+s) = IIc (Department I's revenue equals
Department II's constant capital demand).

Extended reproduction: Department III must produce enough means of
subsistence to reproduce labor power across all departments.

Disproportionality: Imbalance between Dept I (means of production) and
Dept II (means of consumption) output creates crisis tendencies.

See Also:
    :mod:`babylon.economics.circulation.types`: Frozen Pydantic models.
    :class:`ReproductionBalance`: Simple reproduction condition result.
    :class:`ReproductionAnalysis`: Extended reproduction capacity analysis.
    :class:`DisproportionalityCrisis`: Department output imbalance.
"""

from __future__ import annotations

import datetime

from babylon.economics.circulation.types import (
    DisproportionalityCrisis,
    ReproductionAnalysis,
    ReproductionBalance,
)
from babylon.economics.tensor import DepartmentRow
from babylon.models.types import Currency, LaborHours


def combine_departments_ii(
    dept_iia: DepartmentRow,
    dept_iib: DepartmentRow,
) -> DepartmentRow:
    """Sum IIa (necessary consumption) + IIb (luxury consumption) into single Department II.

    Marx subdivides Department II into necessary consumption goods (IIa)
    and luxury consumption goods (IIb). For reproduction schema analysis,
    they are often combined into a single Department II.

    Args:
        dept_iia: Department IIa (necessary consumption goods).
        dept_iib: Department IIb (luxury consumption goods).

    Returns:
        Combined DepartmentRow with summed c, v, s components.

    Example:
        >>> from babylon.economics.tensor import DepartmentRow
        >>> iia = DepartmentRow(c=150.0, v=75.0, s=75.0)
        >>> iib = DepartmentRow(c=50.0, v=25.0, s=25.0)
        >>> combined = combine_departments_ii(iia, iib)
        >>> combined.c
        200.0
    """
    return DepartmentRow(
        c=LaborHours(dept_iia.c + dept_iib.c),
        v=LaborHours(dept_iia.v + dept_iib.v),
        s=LaborHours(dept_iia.s + dept_iib.s),
    )


def check_simple_reproduction(
    dept_i: DepartmentRow,
    dept_ii: DepartmentRow,
    tolerance: float = 0.01,
) -> ReproductionBalance:
    """Check I(v+s) = IIc simple reproduction balance condition.

    In simple reproduction (no accumulation), the revenue of Department I
    (v+s) must equal the constant capital demand of Department II (c).
    This ensures that Department I produces exactly the means of production
    that Department II needs to replace its consumed constant capital.

    Args:
        dept_i: Department I (means of production).
        dept_ii: Department II (means of consumption).
        tolerance: Maximum absolute gap to consider balanced (default 0.01).

    Returns:
        ReproductionBalance with condition_met, gap, and interpretation.
        - gap = I(v+s) - IIc
        - interpretation: "BALANCED", "OVERPRODUCTION_DEPT_I", or
          "UNDERPRODUCTION_DEPT_I"

    Example:
        >>> from babylon.economics.tensor import DepartmentRow
        >>> dept_i = DepartmentRow(c=100.0, v=30.0, s=20.0)
        >>> dept_ii = DepartmentRow(c=50.0, v=25.0, s=25.0)
        >>> result = check_simple_reproduction(dept_i, dept_ii)
        >>> result.condition_met
        True
    """
    gap = float((dept_i.v + dept_i.s) - dept_ii.c)
    condition_met = abs(gap) < tolerance

    if condition_met:
        interpretation = "BALANCED"
    elif gap > 0.0:
        interpretation = "OVERPRODUCTION_DEPT_I"
    else:
        interpretation = "UNDERPRODUCTION_DEPT_I"

    return ReproductionBalance(
        condition_met=condition_met,
        gap=gap,
        interpretation=interpretation,
    )


def check_extended_reproduction(
    dept_i: DepartmentRow,
    dept_ii: DepartmentRow,
    dept_iii: DepartmentRow,
) -> ReproductionAnalysis:
    """Check if Dept III can reproduce all departments' labor power.

    In extended reproduction, Department III (social reproduction) must
    produce sufficient means of subsistence to reproduce the labor power
    employed across all three departments.

    Args:
        dept_i: Department I (means of production).
        dept_ii: Department II (means of consumption).
        dept_iii: Department III (social reproduction).

    Returns:
        ReproductionAnalysis with labor_power_demand, reproduction_capacity,
        gap (demand - capacity), and sustainability (gap <= 0).

    Example:
        >>> from babylon.economics.tensor import DepartmentRow
        >>> d1 = DepartmentRow(c=200.0, v=100.0, s=100.0)
        >>> d2 = DepartmentRow(c=150.0, v=75.0, s=75.0)
        >>> d3 = DepartmentRow(c=100.0, v=50.0, s=100.0)
        >>> result = check_extended_reproduction(d1, d2, d3)
        >>> result.sustainability
        True
    """
    labor_power_demand = float(dept_i.v + dept_ii.v + dept_iii.v)
    reproduction_capacity = float(dept_iii.c + dept_iii.v + dept_iii.s)
    gap = labor_power_demand - reproduction_capacity
    sustainability = gap <= 0.0

    return ReproductionAnalysis(
        labor_power_demand=labor_power_demand,
        reproduction_capacity=reproduction_capacity,
        gap=gap,
        sustainability=sustainability,
    )


def compute_disproportionality(
    dept_i_output: Currency,
    dept_ii_output: Currency,
    dept_i_share_required: float,
) -> DisproportionalityCrisis:
    """Compute department output imbalance metrics.

    Assesses the proportional balance between means-of-production output
    (Dept I) and means-of-consumption output (Dept II). Imbalance between
    departments creates crisis tendencies per Marx's reproduction schemas.

    Args:
        dept_i_output: Total output of Department I (means of production).
        dept_ii_output: Total output of Department II (means of consumption).
        dept_i_share_required: Theoretically required Dept I share of total
            output for balanced reproduction, in [0, 1].

    Returns:
        DisproportionalityCrisis with actual_i_share, imbalance, and
        imbalance_direction computed automatically.

    Example:
        >>> result = compute_disproportionality(
        ...     dept_i_output=Currency(600.0),
        ...     dept_ii_output=Currency(400.0),
        ...     dept_i_share_required=0.55,
        ... )
        >>> result.imbalance_direction
        'OVERPRODUCTION_MEANS_PRODUCTION'
    """
    current_year = datetime.datetime.now(tz=datetime.UTC).year

    return DisproportionalityCrisis(
        year=current_year,
        dept_i_output=dept_i_output,
        dept_ii_output=dept_ii_output,
        dept_i_share_required=dept_i_share_required,
    )


__all__ = [
    "check_extended_reproduction",
    "check_simple_reproduction",
    "combine_departments_ii",
    "compute_disproportionality",
]
