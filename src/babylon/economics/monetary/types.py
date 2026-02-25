"""Type definitions for the value basis conversion module.

Feature: 024-capital-volume-iii (US7)
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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


class MonetaryAdjustment(BaseModel):
    """Conversion factors between value bases for a given year.

    Provides CPI, GDP deflator, and SNLT-per-dollar conversion factors
    needed to translate between nominal, real, and labor-time value bases.

    Feature: 024-capital-volume-iii (FR-013)
    """

    model_config = ConfigDict(frozen=True)

    year: int = Field(..., ge=2007, le=2040)
    cpi_index: float = Field(..., gt=0.0, description="CPI (base year = 100)")
    gdp_deflator: float = Field(..., gt=0.0, description="GDP deflator (base year = 100)")
    snlt_per_dollar: float = Field(..., gt=0.0, description="Labor-hours per dollar of GDP")
    base_year: int = Field(..., ge=2007, le=2040, description="Reference year for real conversion")
