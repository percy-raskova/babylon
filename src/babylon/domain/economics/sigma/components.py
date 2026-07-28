"""Raw σ ingredient formulas (Program 10 §3): OCC, capital intensity, ℓ.

Each function takes explicit, already-hydrated inputs — no sqlite/reference-DB
I/O happens in this package (spec-107's data contract declares the hydration
adapter as a separate, later task; see ``specs/107-sigma-gradient/tasks.md``).

Formulas (verbatim from the ratified program doc):

- ``organic_composition = K / v`` (BEA Fixed Assets net stock over the QCEW
  wage bill).
- ``capital_intensity = K / L`` (net stock per QCEW employee).
- ``labor_content`` (ℓ): the Pasinetti vertically-integrated labor
  coefficient — BEA TOTAL_REQ (one row of the Leontief inverse) dotted
  against QCEW jobs-per-dollar-output by industry.
"""

from __future__ import annotations

from collections.abc import Mapping

from babylon.domain.economics.sigma.types import LaborContent
from babylon.models.types import Ratio

__all__ = [
    "compute_capital_intensity",
    "compute_organic_composition",
    "compute_vertically_integrated_labor_content",
]


def compute_organic_composition(*, capital_stock: float, wage_bill: float) -> Ratio:
    """OCC = K / v — capital stock over the wage bill (Program 10 §3).

    Args:
        capital_stock: K, net fixed-asset stock (BEA FAAt3.1ESI), USD.
        wage_bill: v, the QCEW total wage bill for the same node-year, USD.

    Returns:
        The organic composition of capital, K/v.

    Raises:
        ValueError: If ``wage_bill`` is not strictly positive.

    Examples:
        >>> compute_organic_composition(capital_stock=300.0, wage_bill=100.0)
        3.0
    """
    if wage_bill <= 0:
        raise ValueError(f"wage_bill must be > 0, got {wage_bill!r}")
    return capital_stock / wage_bill


def compute_capital_intensity(*, capital_stock: float, employment: float) -> Ratio:
    """K/L — net capital stock per QCEW employee (Program 10 §3).

    Args:
        capital_stock: K, net fixed-asset stock (BEA FAAt3.1ESI), USD.
        employment: L, QCEW employment count for the same node-year.

    Returns:
        Capital intensity, K/L (USD per worker).

    Raises:
        ValueError: If ``employment`` is not strictly positive.

    Examples:
        >>> compute_capital_intensity(capital_stock=1_000_000.0, employment=10.0)
        100000.0
    """
    if employment <= 0:
        raise ValueError(f"employment must be > 0, got {employment!r}")
    return capital_stock / employment


def compute_vertically_integrated_labor_content(
    *,
    total_requirements: Mapping[str, float],
    labor_coefficients: Mapping[str, float],
) -> LaborContent:
    """ℓ = Σ_i TOTAL_REQ[target, i] · labor_coefficient[i] (Program 10 §3).

    ``total_requirements`` is one row of the BEA TOTAL_REQ Leontief inverse
    (keyed by *source* industry code, for a fixed target industry) —
    exactly the shape of a ``fact_bea_io_coefficient`` query filtered to one
    ``target_industry_id`` and ``table_type_id = TOTAL_REQ``.
    ``labor_coefficients`` is jobs-per-dollar-output keyed by the same
    industry codes (derived from QCEW employment / BEA gross output). Only
    industries present in *both* mappings contribute — this is the Pasinetti
    vertically-integrated labor coefficient: total direct+indirect labor
    embodied per unit of final output.

    Args:
        total_requirements: ``{source_industry_code: total_requirements_coefficient}``.
        labor_coefficients: ``{industry_code: jobs_per_dollar_output}``.

    Returns:
        ℓ, the vertically-integrated labor content (labor-hours per dollar
        of final output — see :data:`babylon.domain.economics.sigma.types.LaborContent`).

    Raises:
        ValueError: If the two mappings share no industry codes (nothing to
            dot-product), or if any contributing coefficient is negative
            (a Leontief inverse row or a labor coefficient cannot be
            negative under the Aleksandrov Test — a negative value signals
            an upstream data or unit-conversion bug, not a valid input).

    Examples:
        >>> compute_vertically_integrated_labor_content(
        ...     total_requirements={"334": 1.2, "221": 0.3},
        ...     labor_coefficients={"334": 0.01, "221": 0.02},
        ... )
        0.018
    """
    shared_industries = total_requirements.keys() & labor_coefficients.keys()
    if not shared_industries:
        raise ValueError(
            "no overlapping industry codes between total_requirements "
            f"({sorted(total_requirements)!r}) and labor_coefficients "
            f"({sorted(labor_coefficients)!r}); cannot compute ℓ."
        )
    total = 0.0
    for industry_code in sorted(shared_industries):
        requirement = total_requirements[industry_code]
        coefficient = labor_coefficients[industry_code]
        if requirement < 0 or coefficient < 0:
            raise ValueError(
                f"negative coefficient for industry {industry_code!r}: "
                f"total_requirement={requirement!r}, labor_coefficient={coefficient!r}"
            )
        total += requirement * coefficient
    return total
