"""SQLite schema for UN trade data.

Provides tables for US imports/exports by country for imperial rent analysis.
Uses the shared research.sqlite database via CensusBase.

Tables:
    Dimension Tables:
        - trade_countries: Country/region reference (259 entities)

    Fact Tables:
        - trade_monthly: Monthly import/export values
        - trade_annual: Annual aggregates with trade balance
"""

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from babylon.data.census.database import CensusBase

# =============================================================================
# DIMENSION TABLES
# =============================================================================


class TradeCountry(CensusBase):
    """Country/region dimension for trade data."""

    __tablename__ = "trade_countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    cty_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_region: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (Index("idx_trade_country_name", "name"),)


# =============================================================================
# FACT TABLES
# =============================================================================


class TradeMonthly(CensusBase):
    """Monthly import/export values by country.

    Values are in millions of USD.
    """

    __tablename__ = "trade_monthly"

    country_id: Mapped[int] = mapped_column(ForeignKey("trade_countries.id"), primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[int] = mapped_column(primary_key=True)  # 1-12
    imports_usd_millions: Mapped[float | None] = mapped_column()
    exports_usd_millions: Mapped[float | None] = mapped_column()

    __table_args__ = (
        Index("idx_trade_monthly_year", "year"),
        Index("idx_trade_monthly_country_year", "country_id", "year"),
    )


class TradeAnnual(CensusBase):
    """Annual trade aggregates by country.

    Values are in millions of USD.
    Trade balance = exports - imports (positive = US surplus, negative = US deficit).
    """

    __tablename__ = "trade_annual"

    country_id: Mapped[int] = mapped_column(ForeignKey("trade_countries.id"), primary_key=True)
    year: Mapped[int] = mapped_column(primary_key=True)
    imports_total: Mapped[float | None] = mapped_column()
    exports_total: Mapped[float | None] = mapped_column()
    trade_balance: Mapped[float | None] = mapped_column()  # exports - imports

    __table_args__ = (
        Index("idx_trade_annual_year", "year"),
        Index("idx_trade_annual_balance", "trade_balance"),
    )


# Export all models
__all__ = [
    "TradeCountry",
    "TradeMonthly",
    "TradeAnnual",
]
