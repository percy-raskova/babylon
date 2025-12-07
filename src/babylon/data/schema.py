"""SQLite schema for external reality data.

These tables store ground-truth data from Census, FRED, BLS, etc.
This is the material base that constrains the simulation.

Tables:
    Geographic Reference:
        - states: US state FIPS codes and names
        - metro_areas: Metropolitan Statistical Areas (CBSA codes)

    Census Data:
        - census_population: State-level population and class proxies
        - census_metro: Metro-level demographics

    Economic Data:
        - fred_indicators: Federal Reserve economic indicators

    Labor Data:
        - union_membership: Union membership by state

    Resource Data:
        - strategic_resources: Strategic resource stockpiles and production
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from babylon.data.database import Base

# =============================================================================
# GEOGRAPHIC REFERENCE TABLES
# =============================================================================


class State(Base):
    """US States - reference table."""

    __tablename__ = "states"

    fips: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    abbreviation: Mapped[str] = mapped_column(String(2))


class MetroArea(Base):
    """Metropolitan Statistical Areas."""

    __tablename__ = "metro_areas"

    cbsa_code: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


# =============================================================================
# CENSUS DATA TABLES
# =============================================================================


class CensusPopulation(Base):
    """State-level population and class proxies from Census ACS."""

    __tablename__ = "census_population"

    id: Mapped[int] = mapped_column(primary_key=True)
    state_fips: Mapped[str | None] = mapped_column(String(2), ForeignKey("states.fips"))
    year: Mapped[int]
    total_pop: Mapped[int | None] = mapped_column(default=None)
    employed: Mapped[int | None] = mapped_column(default=None)
    unemployed: Mapped[int | None] = mapped_column(default=None)
    self_employed: Mapped[int | None] = mapped_column(default=None)
    median_income: Mapped[float | None] = mapped_column(default=None)
    poverty_pop: Mapped[int | None] = mapped_column(default=None)


class CensusMetro(Base):
    """Metro-level demographics from Census ACS."""

    __tablename__ = "census_metro"

    id: Mapped[int] = mapped_column(primary_key=True)
    cbsa_code: Mapped[str | None] = mapped_column(String(5), ForeignKey("metro_areas.cbsa_code"))
    year: Mapped[int]
    total_pop: Mapped[int | None] = mapped_column(default=None)
    median_income: Mapped[float | None] = mapped_column(default=None)
    gini_index: Mapped[float | None] = mapped_column(default=None)
    median_rent: Mapped[float | None] = mapped_column(default=None)
    median_home_value: Mapped[float | None] = mapped_column(default=None)


# =============================================================================
# ECONOMIC DATA TABLES
# =============================================================================


class FredIndicator(Base):
    """Federal Reserve economic indicators."""

    __tablename__ = "fred_indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int]
    quarter: Mapped[int | None] = mapped_column(default=None)  # NULL for annual data
    gdp_billions: Mapped[float | None] = mapped_column(default=None)
    unemployment_pct: Mapped[float | None] = mapped_column(default=None)
    cpi: Mapped[float | None] = mapped_column(default=None)
    fed_funds_rate: Mapped[float | None] = mapped_column(default=None)
    federal_debt_millions: Mapped[float | None] = mapped_column(default=None)
    m2_money_supply: Mapped[float | None] = mapped_column(default=None)
    median_income: Mapped[float | None] = mapped_column(default=None)


# =============================================================================
# LABOR DATA TABLES
# =============================================================================


class UnionMembership(Base):
    """Union membership by state from BLS."""

    __tablename__ = "union_membership"

    id: Mapped[int] = mapped_column(primary_key=True)
    state_fips: Mapped[str | None] = mapped_column(String(2), ForeignKey("states.fips"))
    year: Mapped[int]
    total_employed: Mapped[int | None] = mapped_column(default=None)
    union_members: Mapped[int | None] = mapped_column(default=None)
    union_pct: Mapped[float | None] = mapped_column(default=None)


# =============================================================================
# RESOURCE DATA TABLES
# =============================================================================


class StrategicResource(Base):
    """Strategic resource stockpiles and production."""

    __tablename__ = "strategic_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(10))  # Maps to game resources.json
    resource_name: Mapped[str] = mapped_column(String(100))
    year: Mapped[int]
    annual_production: Mapped[float | None] = mapped_column(default=None)
    production_unit: Mapped[str | None] = mapped_column(String(50), default=None)
    strategic_reserve: Mapped[float | None] = mapped_column(default=None)
    reserve_unit: Mapped[str | None] = mapped_column(String(50), default=None)


# Export all models
__all__ = [
    "State",
    "MetroArea",
    "CensusPopulation",
    "CensusMetro",
    "FredIndicator",
    "UnionMembership",
    "StrategicResource",
]
