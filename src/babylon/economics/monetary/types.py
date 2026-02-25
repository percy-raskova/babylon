"""Type definitions for the value basis conversion module.

Feature: 024-capital-volume-iii (US7)
"""

from __future__ import annotations

from enum import StrEnum


class ValueBasis(StrEnum):
    """Value expression basis for economic quantities.

    Feature: 024-capital-volume-iii (FR-013)

    All tensor values should be expressible in these three bases to
    distinguish genuine changes in material conditions from nominal
    monetary effects.

    Values:
        NOMINAL: Current dollars (unadjusted for inflation).
        REAL: Constant dollars (inflation-adjusted to base year).
        LABOR_TIME: Hours of socially necessary labor time (SNLT).
    """

    NOMINAL = "nominal"
    REAL = "real"
    LABOR_TIME = "labor_time"
