"""SQLite schema for BLS QCEW (Quarterly Census of Employment and Wages) data.

Provides tables for US employment/wage data by geography, industry, and ownership
for labor aristocracy analysis. Uses the shared research.sqlite database via CensusBase.

Tables:
    Dimension Tables:
        - qcew_areas: Geographic reference (counties, states, CSAs)
        - qcew_industries: NAICS industry hierarchy
        - qcew_ownership: Ownership sector types

    Fact Tables:
        - qcew_annual: Annual employment/wage metrics
"""

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from babylon.data.census.database import CensusBase

# =============================================================================
# DIMENSION TABLES
# =============================================================================


class QcewArea(CensusBase):
    """Geographic dimension for QCEW data (counties, states, CSAs)."""

    __tablename__ = "qcew_areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    area_fips: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    area_title: Mapped[str] = mapped_column(String(200), nullable=False)
    area_type: Mapped[str] = mapped_column(String(20), nullable=False)  # county/state/csa/msa
    state_fips: Mapped[str | None] = mapped_column(String(2))  # Extracted from area_fips

    __table_args__ = (
        Index("idx_qcew_area_fips", "area_fips"),
        Index("idx_qcew_area_type", "area_type"),
    )


class QcewIndustry(CensusBase):
    """NAICS industry hierarchy dimension."""

    __tablename__ = "qcew_industries"

    id: Mapped[int] = mapped_column(primary_key=True)
    industry_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    industry_title: Mapped[str] = mapped_column(String(300), nullable=False)
    naics_level: Mapped[int] = mapped_column(nullable=False)  # 0=total, 2-6=NAICS, 99=supersector
    parent_code: Mapped[str | None] = mapped_column(String(20))  # For hierarchy navigation

    __table_args__ = (
        Index("idx_qcew_industry_code", "industry_code"),
        Index("idx_qcew_industry_level", "naics_level"),
    )


class QcewOwnership(CensusBase):
    """Ownership sector dimension (Federal, State, Local, Private, Total)."""

    __tablename__ = "qcew_ownership"

    id: Mapped[int] = mapped_column(primary_key=True)
    own_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    own_title: Mapped[str] = mapped_column(String(50), nullable=False)


# =============================================================================
# FACT TABLES
# =============================================================================


class QcewAnnual(CensusBase):
    """Annual employment and wage metrics by area, industry, and ownership.

    Values:
        - establishments: Average number of establishments
        - employment: Average employment level
        - total_wages: Total annual wages (USD)
        - avg_weekly_wage: Average weekly wage (USD)
        - avg_annual_pay: Average annual pay per employee (USD)
        - lq_*: Location quotients (indexed to national average)
        - oty_*: Year-over-year changes
    """

    __tablename__ = "qcew_annual"

    area_id: Mapped[int] = mapped_column(ForeignKey("qcew_areas.id"), primary_key=True)
    industry_id: Mapped[int] = mapped_column(ForeignKey("qcew_industries.id"), primary_key=True)
    ownership_id: Mapped[int] = mapped_column(ForeignKey("qcew_ownership.id"), primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)

    # Core metrics
    establishments: Mapped[int | None] = mapped_column()  # annual_avg_estabs_count
    employment: Mapped[int | None] = mapped_column()  # annual_avg_emplvl
    total_wages: Mapped[float | None] = mapped_column()  # total_annual_wages
    avg_weekly_wage: Mapped[int | None] = mapped_column()  # annual_avg_wkly_wage
    avg_annual_pay: Mapped[int | None] = mapped_column()  # avg_annual_pay

    # Location quotients
    lq_employment: Mapped[float | None] = mapped_column()  # lq_annual_avg_emplvl
    lq_avg_annual_pay: Mapped[float | None] = mapped_column()  # lq_avg_annual_pay

    # Year-over-year changes
    oty_employment_chg: Mapped[int | None] = mapped_column()  # oty_annual_avg_emplvl_chg
    oty_employment_pct: Mapped[float | None] = mapped_column()  # oty_annual_avg_emplvl_pct_chg

    # Metadata
    disclosure_code: Mapped[str | None] = mapped_column(String(5))  # "" or "N" (suppressed)

    __table_args__ = (
        Index("idx_qcew_annual_area_year", "area_id", "year"),
        Index("idx_qcew_annual_industry_year", "industry_id", "year"),
        Index("idx_qcew_annual_ownership", "ownership_id"),
    )


# Export all models
__all__ = [
    "QcewArea",
    "QcewIndustry",
    "QcewOwnership",
    "QcewAnnual",
]
