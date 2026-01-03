"""FRED (Federal Reserve Economic Data) SQLAlchemy schema.

Defines ORM models for FRED macroeconomic time series data:
- National indicators (CPI, wages, unemployment, money supply, etc.)
- State-level unemployment rates
- Industry-level unemployment rates

All tables are stored in the unified research.sqlite database alongside
Census, QCEW, Trade, and Productivity data.

Tables:
    fred_series: Dimension table for series metadata
    fred_states: Dimension table for US states
    fred_industries: Dimension table for industry sectors
    fred_national: Fact table for national time series
    fred_state_unemployment: Fact table for state unemployment
    fred_industry_unemployment: Fact table for industry unemployment
"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from babylon.data.census.database import CensusBase


class FredSeries(CensusBase):
    """Dimension table for FRED series metadata.

    Stores metadata about each time series including units, frequency,
    and source information.

    Attributes:
        id: Auto-incrementing primary key.
        series_id: FRED series identifier (e.g., "CPIAUCSL").
        title: Human-readable series title.
        units: Measurement units (e.g., "Index 1982-1984=100").
        frequency: Data frequency ("Monthly", "Quarterly", "Annual").
        seasonal_adjustment: Adjustment status ("Seasonally Adjusted", etc.).
        source: Data source organization.
        last_updated: Last update timestamp from FRED.
    """

    __tablename__ = "fred_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    units: Mapped[str | None] = mapped_column(String, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String, nullable=True)
    seasonal_adjustment: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    last_updated: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationship to observations
    observations: Mapped[list["FredNational"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class FredState(CensusBase):
    """Dimension table for US states.

    Provides state FIPS codes for joining with Census and QCEW data.

    Attributes:
        id: Auto-incrementing primary key.
        fips_code: 2-digit state FIPS code (e.g., "12" for Florida).
        name: Full state name.
        abbreviation: 2-letter state abbreviation (e.g., "FL").
    """

    __tablename__ = "fred_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fips_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationship to unemployment observations
    unemployment_rates: Mapped[list["FredStateUnemployment"]] = relationship(
        back_populates="state", cascade="all, delete-orphan"
    )


class FredIndustry(CensusBase):
    """Dimension table for industry sectors.

    Maps FRED LNU unemployment series to industry names and NAICS sectors
    for joining with QCEW employment data.

    Attributes:
        id: Auto-incrementing primary key.
        lnu_code: FRED LNU series code (e.g., "LNU04032232").
        name: Industry name (e.g., "Manufacturing").
        naics_sector: Corresponding NAICS sector code for QCEW joins.
    """

    __tablename__ = "fred_industries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lnu_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    naics_sector: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationship to unemployment observations
    unemployment_rates: Mapped[list["FredIndustryUnemployment"]] = relationship(
        back_populates="industry", cascade="all, delete-orphan"
    )


class FredNational(CensusBase):
    """Fact table for national-level FRED time series.

    Stores observation values for national economic indicators.
    Each row represents one observation (value at a point in time).

    Attributes:
        id: Auto-incrementing primary key.
        series_id: Foreign key to fred_series.
        date: Observation date (YYYY-MM-DD format).
        year: Year extracted from date for filtering.
        month: Month (1-12) for monthly/quarterly data.
        quarter: Quarter (1-4) for quarterly data.
        value: Numeric observation value.
    """

    __tablename__ = "fred_national"
    __table_args__ = (
        UniqueConstraint("series_id", "date", name="uq_fred_national_series_date"),
        Index("ix_fred_national_year", "year"),
        Index("ix_fred_national_series_year", "series_id", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("fred_series.id"), nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship to series
    series: Mapped["FredSeries"] = relationship(back_populates="observations")


class FredStateUnemployment(CensusBase):
    """Fact table for state-level unemployment rates.

    Stores monthly unemployment rates by state from LAUST series.
    Joins with Census county data via state FIPS prefix.

    Attributes:
        id: Auto-incrementing primary key.
        state_id: Foreign key to fred_states.
        date: Observation date (YYYY-MM-DD format).
        year: Year extracted from date.
        month: Month (1-12).
        unemployment_rate: Unemployment rate as percentage.
    """

    __tablename__ = "fred_state_unemployment"
    __table_args__ = (
        UniqueConstraint("state_id", "date", name="uq_fred_state_unemp_state_date"),
        Index("ix_fred_state_unemp_year", "year"),
        Index("ix_fred_state_unemp_state_year", "state_id", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[int] = mapped_column(Integer, ForeignKey("fred_states.id"), nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unemployment_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship to state
    state: Mapped["FredState"] = relationship(back_populates="unemployment_rates")


class FredIndustryUnemployment(CensusBase):
    """Fact table for industry-level unemployment rates.

    Stores monthly unemployment rates by industry sector from LNU04 series.
    Joins with QCEW data via NAICS sector codes.

    Attributes:
        id: Auto-incrementing primary key.
        industry_id: Foreign key to fred_industries.
        date: Observation date (YYYY-MM-DD format).
        year: Year extracted from date.
        month: Month (1-12).
        unemployment_rate: Unemployment rate as percentage.
    """

    __tablename__ = "fred_industry_unemployment"
    __table_args__ = (
        UniqueConstraint("industry_id", "date", name="uq_fred_industry_unemp_industry_date"),
        Index("ix_fred_industry_unemp_year", "year"),
        Index("ix_fred_industry_unemp_industry_year", "industry_id", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    industry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fred_industries.id"), nullable=False
    )
    date: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unemployment_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship to industry
    industry: Mapped["FredIndustry"] = relationship(back_populates="unemployment_rates")


class FredWealthClass(CensusBase):
    """Dimension table for DFA wealth percentile classes.

    Maps Federal Reserve Distributional Financial Accounts (DFA) wealth
    percentiles to Babylon's Marxist-Leninist-Maoist Third Worldist (MLM-TW)
    class categories.

    The DFA divides household wealth into four strata that correspond
    to distinct class positions in the imperial core:

    - Top 1% (LT01): HauteBourgeoisie - Global Capital Accumulation
        The transnational capitalist class controlling finance capital.
        Their wealth is "stakes in empire" - assets that depend on
        continued imperial extraction from the periphery.

    - 90-99% (N09): PetitBourgeoisie/Managerial - Enforcers & Functionaries
        The professional-managerial class: executives, doctors, lawyers.
        Buffer stratum that enforces capitalist relations in exchange
        for above-median wealth accumulation.

    - 50-90% (N40): LaborAristocracy - The Junior Partner
        Core workers receiving super-wages from imperial rent.
        Their real estate holdings are the "material basis of fascism" -
        property values tie them to the settler-colonial project.

    - Bottom 50% (B50): Proletariat/InternalColonies - The Excluded
        Those with "nothing to lose but their chains."
        Net worth often negative (debt exceeds assets).
        Includes internal colonies: Black, Indigenous, imprisoned.

    Attributes:
        id: Auto-incrementing primary key.
        percentile_code: DFA percentile code (e.g., "LT01" for Top 1%).
        percentile_label: Human-readable label (e.g., "Top 1%").
        percentile_min: Lower bound of percentile range (exclusive).
        percentile_max: Upper bound of percentile range (inclusive).
        babylon_class: Corresponding Babylon SocialRole enum value.
        description: Marxian interpretation of this wealth stratum.
    """

    __tablename__ = "fred_wealth_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    percentile_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    percentile_label: Mapped[str] = mapped_column(String, nullable=False)
    percentile_min: Mapped[float] = mapped_column(Float, nullable=False)
    percentile_max: Mapped[float] = mapped_column(Float, nullable=False)
    babylon_class: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    wealth_levels: Mapped[list["FredWealthLevel"]] = relationship(
        back_populates="wealth_class", cascade="all, delete-orphan"
    )
    wealth_shares: Mapped[list["FredWealthShare"]] = relationship(
        back_populates="wealth_class", cascade="all, delete-orphan"
    )


class FredAssetCategory(CensusBase):
    """Dimension table for DFA asset/wealth categories.

    DFA provides breakdowns of wealth by category. For Babylon, we track:

    - Total Assets: "Stake in Empire" - what this class has to lose
        Total assets (not net worth) measure entrenchment.
        The higher the assets, the more invested in preserving the system.

    - Real Estate: "Material Basis of Fascism" (after Sakai)
        Land value ties settlers to the colonial project.
        Real estate wealth is WHY the "middle class" defends the state.

    - Net Worth: Overall class position indicator
        Assets minus liabilities. Often negative for bottom 50%.
        Shows who is truly "wageless" - living on credit.

    Attributes:
        id: Auto-incrementing primary key.
        category_code: Short code (e.g., "TOTAL_ASSETS", "REAL_ESTATE").
        category_label: Human-readable label.
        marxian_interpretation: What this asset type reveals about class.
    """

    __tablename__ = "fred_asset_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    category_label: Mapped[str] = mapped_column(String, nullable=False)
    marxian_interpretation: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    wealth_levels: Mapped[list["FredWealthLevel"]] = relationship(
        back_populates="asset_category", cascade="all, delete-orphan"
    )
    wealth_shares: Mapped[list["FredWealthShare"]] = relationship(
        back_populates="asset_category", cascade="all, delete-orphan"
    )


class FredWealthLevel(CensusBase):
    """Fact table for DFA wealth levels (absolute $ millions).

    Quarterly time series of wealth held by each percentile class.
    Values are in millions of US dollars (not inflation-adjusted).

    Primary analytical uses:
        1. Calculate class wealth ratios (Top 1% / Bottom 50%)
        2. Track real estate concentration over time
        3. Measure "stake in empire" (total assets by class)

    Join with fred_wealth_classes.babylon_class to connect to
    Babylon's SocialRole enum for simulation initialization.

    Attributes:
        id: Auto-incrementing primary key.
        series_id: Foreign key to fred_series (for metadata).
        wealth_class_id: Foreign key to fred_wealth_classes.
        asset_category_id: Foreign key to fred_asset_categories.
        date: Observation date (YYYY-MM-DD, quarterly).
        year: Year for filtering.
        quarter: Quarter (1-4) for quarterly aggregation.
        value_millions: Wealth in millions of USD.
    """

    __tablename__ = "fred_wealth_levels"
    __table_args__ = (
        UniqueConstraint(
            "wealth_class_id",
            "asset_category_id",
            "date",
            name="uq_fred_wealth_level_class_category_date",
        ),
        Index("ix_fred_wealth_level_year", "year"),
        Index("ix_fred_wealth_level_class_year", "wealth_class_id", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("fred_series.id"), nullable=False)
    wealth_class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fred_wealth_classes.id"), nullable=False
    )
    asset_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fred_asset_categories.id"), nullable=False
    )
    date: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_millions: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    series: Mapped["FredSeries"] = relationship()
    wealth_class: Mapped["FredWealthClass"] = relationship(back_populates="wealth_levels")
    asset_category: Mapped["FredAssetCategory"] = relationship(back_populates="wealth_levels")


class FredWealthShare(CensusBase):
    """Fact table for DFA wealth shares (percentages).

    Quarterly time series of wealth share held by each percentile class.
    Values are percentages (0-100) of total national wealth.

    Primary analytical uses:
        1. Track wealth concentration trends (is inequality rising?)
        2. Compare class shares to population shares
        3. Initialize simulation inequality parameters

    Key insight: Bottom 50% is ~50% of population but holds ~2% of wealth.
    Top 1% is 1% of population but holds ~30% of wealth.
    This disproportion IS the class structure.

    Attributes:
        id: Auto-incrementing primary key.
        series_id: Foreign key to fred_series (for metadata).
        wealth_class_id: Foreign key to fred_wealth_classes.
        asset_category_id: Foreign key to fred_asset_categories.
        date: Observation date (YYYY-MM-DD, quarterly).
        year: Year for filtering.
        quarter: Quarter (1-4) for quarterly aggregation.
        share_percent: Share of total as percentage (0-100).
    """

    __tablename__ = "fred_wealth_shares"
    __table_args__ = (
        UniqueConstraint(
            "wealth_class_id",
            "asset_category_id",
            "date",
            name="uq_fred_wealth_share_class_category_date",
        ),
        Index("ix_fred_wealth_share_year", "year"),
        Index("ix_fred_wealth_share_class_year", "wealth_class_id", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("fred_series.id"), nullable=False)
    wealth_class_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fred_wealth_classes.id"), nullable=False
    )
    asset_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("fred_asset_categories.id"), nullable=False
    )
    date: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    share_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    series: Mapped["FredSeries"] = relationship()
    wealth_class: Mapped["FredWealthClass"] = relationship(back_populates="wealth_shares")
    asset_category: Mapped["FredAssetCategory"] = relationship(back_populates="wealth_shares")
