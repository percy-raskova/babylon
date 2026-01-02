"""SQLite schema for BLS Industry Productivity data.

Provides tables for labor productivity, hours worked, and compensation metrics
by NAICS industry code, joinable with QCEW wage data for Marxian analysis.

Tables:
    Dimension Tables:
        - productivity_industries: NAICS industry reference (aligned with QCEW)

    Fact Tables:
        - productivity_annual: Annual productivity metrics by industry
"""

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from babylon.data.census.database import CensusBase

# =============================================================================
# DIMENSION TABLES
# =============================================================================


class ProductivityIndustry(CensusBase):
    """BLS productivity industry dimension, aligned with QCEW NAICS codes.

    The naics_code field can be joined with qcew_industries.industry_code
    to link productivity data with geographic wage/employment data.
    """

    __tablename__ = "productivity_industries"

    id: Mapped[int] = mapped_column(primary_key=True)
    naics_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    industry_title: Mapped[str] = mapped_column(String(300), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100))
    digit_level: Mapped[str] = mapped_column(String(10), nullable=False)

    __table_args__ = (
        Index("idx_productivity_naics", "naics_code"),
        Index("idx_productivity_sector", "sector"),
    )


# =============================================================================
# FACT TABLES
# =============================================================================


class ProductivityAnnual(CensusBase):
    """Annual productivity metrics by industry.

    Contains key metrics for Marxian value analysis:
    - Labor productivity: output per hour (value creation rate)
    - Hours worked: total labor time (socially necessary labor)
    - Hourly compensation: variable capital (wages per hour)
    - Unit labor costs: labor share proxy
    - Output: total value produced (V + S)
    - Labor compensation: total wages (V, variable capital)

    Rate of surplus value = (Output - Labor Comp) / Labor Comp
    """

    __tablename__ = "productivity_annual"

    industry_id: Mapped[int] = mapped_column(
        ForeignKey("productivity_industries.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(primary_key=True)

    # Core productivity metrics (Index 2017=100)
    labor_productivity_index: Mapped[float | None] = mapped_column()
    labor_productivity_pct_chg: Mapped[float | None] = mapped_column()

    # Hours and employment
    hours_worked_index: Mapped[float | None] = mapped_column()
    hours_worked_millions: Mapped[float | None] = mapped_column()
    employment_thousands: Mapped[float | None] = mapped_column()

    # Compensation metrics (Index 2017=100)
    hourly_compensation_index: Mapped[float | None] = mapped_column()
    unit_labor_costs_index: Mapped[float | None] = mapped_column()

    # Output metrics
    real_output_index: Mapped[float | None] = mapped_column()
    sectoral_output_index: Mapped[float | None] = mapped_column()

    # Absolute values for Marxian calculations (millions of current dollars)
    labor_compensation_millions: Mapped[float | None] = mapped_column()
    sectoral_output_millions: Mapped[float | None] = mapped_column()

    __table_args__ = (
        Index("idx_productivity_year", "year"),
        Index("idx_productivity_industry_year", "industry_id", "year"),
    )


# Export all models
__all__ = [
    "ProductivityIndustry",
    "ProductivityAnnual",
]
