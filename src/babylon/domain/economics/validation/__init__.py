"""Validation module for economics falsifiability testing.

This module provides regression analysis and statistical validation
to test theoretical predictions against empirical data, ensuring
the Marxian economic models are falsifiable.

Feature 005: ATUS Department III - Visibility Decomposition

Current Validation Tests:
    - Domestic hours regression: domestic_hours ~ 1/income (expect β > 0)
      Lower income households spend more time on unpaid reproductive labor.

Example:
    >>> from babylon.domain.economics.validation import (
    ...     RegressionResult,
    ...     validate_domestic_hours_regression,
    ... )
    >>> result = validate_domestic_hours_regression()
    >>> assert result.slope > 0, "Inverse income relationship not confirmed"

See Also:
    :mod:`babylon.domain.economics.shadow_labor`: Shadow labor calculations.
    :mod:`babylon.data.atus`: ATUS data loading and models.
"""

from babylon.domain.economics.validation.regression import (
    RegressionResult,
    run_linear_regression,
    validate_domestic_hours_regression,
)

__all__ = [
    "RegressionResult",
    "run_linear_regression",
    "validate_domestic_hours_regression",
]
