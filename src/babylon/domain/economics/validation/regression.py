"""Regression validation for falsifiability testing (Feature 005 - US3).

This module provides regression analysis to validate theoretical predictions
against empirical data, ensuring the Marxian economic models are falsifiable.

**Primary Validation:**

The domestic_hours ~ 1/income regression tests the theoretical prediction that
lower-income households spend more time on unpaid reproductive labor. This
inverse relationship (β > 0 when regressing on 1/income) is a key falsifiable
claim of the shadow labor model.

**Implementation:**

Uses scipy.stats.linregress for simplicity (per research.md decision).
The regression uses ATUS seed data occupation multipliers as proxy data.

See Also:
    :mod:`babylon.data.atus`: ATUS data loading.
    specs/005-atus-department-iii/research.md Section 5.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict
from scipy.stats import linregress  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class RegressionResult(BaseModel):
    """Result of linear regression analysis.

    Contains all statistics returned by scipy.stats.linregress.

    Attributes:
        slope: Slope of the regression line.
        intercept: Y-intercept of the regression line.
        r_value: Pearson correlation coefficient.
        p_value: Two-sided p-value for slope != 0.
        std_err: Standard error of the estimated slope.

    Example:
        >>> result = RegressionResult(
        ...     slope=2.5,
        ...     intercept=10.0,
        ...     r_value=0.85,
        ...     p_value=0.001,
        ...     std_err=0.3,
        ... )
        >>> result.slope > 0
        True
    """

    model_config = ConfigDict(frozen=True)

    slope: float
    intercept: float
    r_value: float
    p_value: float
    std_err: float


def run_linear_regression(
    x_values: Sequence[float],
    y_values: Sequence[float],
) -> RegressionResult:
    """Run linear regression on provided data.

    Args:
        x_values: Independent variable values.
        y_values: Dependent variable values.

    Returns:
        RegressionResult with slope, intercept, and statistics.

    Raises:
        ValueError: If fewer than 2 data points provided.

    Example:
        >>> result = run_linear_regression([1, 2, 3], [2, 4, 6])
        >>> result.slope
        2.0
    """
    if len(x_values) < 2 or len(y_values) < 2:
        msg = "Regression requires at least 2 data points"
        raise ValueError(msg)

    if len(x_values) != len(y_values):
        msg = f"x and y must have same length, got {len(x_values)} and {len(y_values)}"
        raise ValueError(msg)

    result = linregress(x_values, y_values)

    return RegressionResult(
        slope=result.slope,
        intercept=result.intercept,
        r_value=result.rvalue,
        p_value=result.pvalue,
        std_err=result.stderr,
    )


def validate_domestic_hours_regression(
    seed_data_path: str | Path | None = None,
) -> RegressionResult:
    """Validate domestic hours ~ 1/income inverse relationship.

    Loads occupation multipliers from ATUS seed data and runs regression
    of total domestic hours against inverse "income" (using occupation
    class character as proxy).

    The theoretical expectation (SC-005) is that the slope should be positive:
    as 1/income increases (i.e., income decreases), domestic hours increase.

    Args:
        seed_data_path: Optional path to seed data YAML. Uses default if None.

    Returns:
        RegressionResult with slope (expect > 0), intercept, and statistics.

    Example:
        >>> result = validate_domestic_hours_regression()
        >>> result.slope > 0  # Confirms inverse relationship
        True
    """
    # Default path
    # one extra .parent: economics moved under domain/ (Program 14 Phase 3d)
    default_path = Path(__file__).parent.parent.parent.parent / "data" / "atus" / "seed_data.yaml"
    path = Path(seed_data_path) if seed_data_path else default_path

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    occupation_multipliers = data["occupation_multipliers"]

    # Build proxy data from occupation groups
    # Income proxy: bourgeois/petit_bourgeois = high, proletariat = low
    # domestic_hours proxy: sum of housework + cooking multipliers
    income_proxy_map = {
        "bourgeois/petit_bourgeois": 3.0,  # High income
        "labor_aristocracy": 2.0,  # Upper-middle
        "proletariat/petit_bourgeois": 1.5,  # Lower-middle
        "proletariat": 1.0,  # Low income
    }

    x_inverse_income: list[float] = []
    y_domestic_hours: list[float] = []

    for occ_name, occ_data in occupation_multipliers.items():
        class_char = occ_data["class_character"]
        multipliers = occ_data["multipliers"]

        # Income proxy (use inverse)
        income = income_proxy_map.get(class_char, 1.0)
        inverse_income = 1.0 / income

        # Domestic hours proxy: housework + cooking (main unpaid labor categories)
        domestic = multipliers.get("housework", 1.0) + multipliers.get("cooking", 1.0)

        x_inverse_income.append(inverse_income)
        y_domestic_hours.append(domestic)

        logger.debug(
            f"{occ_name}: income_proxy={income}, 1/income={inverse_income:.3f}, "
            f"domestic_hours={domestic:.2f}"
        )

    return run_linear_regression(x_inverse_income, y_domestic_hours)


__all__ = [
    "RegressionResult",
    "run_linear_regression",
    "validate_domestic_hours_regression",
]
