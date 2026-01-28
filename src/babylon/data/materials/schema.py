"""USGS Mineral Commodity Summaries SQLAlchemy schema.

Defines ORM models for USGS mineral and material production, trade, and
strategic dependency data for imperial economics analysis.

All tables are stored in the unified research.sqlite database alongside
Census, QCEW, FRED, Energy, Trade, and Productivity data.

Tables:
    commodities: Dimension table for minerals/materials (~85 commodities)
    commodity_metrics: Dimension table for measurement types (~15 metrics)
    commodity_observations: Fact table for annual observations (EAV, 2020-2024)
    materials_states: Dimension table for US states (for geographic joins)
    state_minerals: Fact table for state-level production values
    mineral_trends: Fact table for industry aggregate trends
    import_sources: Dimension table for major import countries

Join keys:
    year: For temporal joins with Census, QCEW, FRED, Energy data
    fips_code: For geographic joins with Census counties

Key Marxian metric:
    NIR_pct (Net Import Reliance) = imperial vulnerability index.
    NIR >50% means dependent on periphery extraction for strategic materials.
"""

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from babylon.data.census.database import CensusBase


class Commodity(CensusBase):
    """Dimension table for USGS mineral commodities.

    Represents individual minerals and materials tracked by USGS,
    from strategic metals (lithium, cobalt) to industrial minerals
    (cement, sand).

    Attributes:
        id: Auto-incrementing primary key.
        code: Short code from filename (e.g., "lithium", "cobalt", "alumi").
        name: Full commodity name (e.g., "Lithium", "Cobalt", "Aluminum").
        is_critical: True if on DOE/USGS critical minerals list.
        primary_applications: Key end uses (e.g., "Batteries, electronics").
        marxian_interpretation: Strategic significance for imperial economics.
    """

    __tablename__ = "commodities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_applications: Mapped[str | None] = mapped_column(String(500), nullable=True)
    marxian_interpretation: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship to observations
    observations: Mapped[list["CommodityObservation"]] = relationship(
        back_populates="commodity", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_commodity_critical", "is_critical"),)


class CommodityMetric(CensusBase):
    """Dimension table for commodity measurement types.

    Different commodities have different available metrics (production
    forms, trade types, etc.). This normalized dimension allows flexible
    tracking without NULL-heavy wide tables.

    Categories:
        production: USprod_*, Mine_Production_*
        trade: Imports_*, Exports_*
        consumption: Consump_Apprnt_*
        price: Price_*, Avg_*
        strategic: NIR_pct, Employment_*, Stocks_*

    Attributes:
        id: Auto-incrementing primary key.
        code: Metric identifier (e.g., "USprod_t", "NIR_pct").
        name: Human-readable name (e.g., "US Production (metric tons)").
        units: Measurement units (e.g., "metric tons", "percent").
        category: Analytical category for grouping.
        marxian_interpretation: What this metric reveals about class relations.
    """

    __tablename__ = "commodity_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    units: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    marxian_interpretation: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Relationship to observations
    observations: Mapped[list["CommodityObservation"]] = relationship(
        back_populates="metric", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_metric_category", "category"),)


class CommodityObservation(CensusBase):
    """Fact table for annual commodity observations (EAV pattern).

    Uses Entity-Attribute-Value structure because different commodities
    have different available metrics. Lithium has USprod_t, Cobalt has
    USprod_Mine_t + USprod_Secondary_t. EAV allows flexible schema.

    Special value handling:
        - "W" (Withheld): value=None, value_text="W"
        - "NA" (Not Available): value=None, value_text="NA"
        - ">50": value=50.0, value_text=">50"
        - Numeric: value=float, value_text=None

    Attributes:
        id: Auto-incrementing primary key.
        commodity_id: Foreign key to commodities.
        metric_id: Foreign key to commodity_metrics.
        year: Calendar year (2020-2024).
        value: Numeric value (nullable for W/NA).
        value_text: Original text if special (e.g., ">50", "W").
    """

    __tablename__ = "commodity_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commodity_id: Mapped[int] = mapped_column(Integer, ForeignKey("commodities.id"), nullable=False)
    metric_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("commodity_metrics.id"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationships
    commodity: Mapped["Commodity"] = relationship(back_populates="observations")
    metric: Mapped["CommodityMetric"] = relationship(back_populates="observations")

    __table_args__ = (
        UniqueConstraint("commodity_id", "metric_id", "year", name="uq_commodity_metric_year"),
        Index("idx_commodity_obs_year", "year"),
        Index("idx_commodity_obs_commodity", "commodity_id"),
        Index("idx_commodity_obs_metric_year", "metric_id", "year"),
    )


class MaterialsState(CensusBase):
    """Dimension table for US states in materials context.

    Provides state names and FIPS codes for joining mineral production
    data with Census and FRED geographic data.

    Attributes:
        id: Auto-incrementing primary key.
        name: Full state name (e.g., "Nevada", "California").
        fips_code: 2-digit state FIPS code for joins.
    """

    __tablename__ = "materials_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    fips_code: Mapped[str | None] = mapped_column(String(2), nullable=True)

    # Relationship to state minerals
    minerals: Mapped[list["StateMineral"]] = relationship(
        back_populates="state", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_materials_state_fips", "fips_code"),)


class StateMineral(CensusBase):
    """Fact table for state-level mineral production.

    From MCS2025_T3_State_Value_Rank.csv. Key for understanding
    geographic distribution of extraction within imperial core.

    Attributes:
        state_id: Foreign key to materials_states (part of PK).
        year: Calendar year (part of PK).
        value_millions: Mineral production value in millions USD.
        rank: National rank by production value.
        percent_total: Percentage of national total.
        principal_commodities: Comma-separated list of top commodities.
    """

    __tablename__ = "state_minerals"

    state_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materials_states.id"), primary_key=True
    )
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    value_millions: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    percent_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    principal_commodities: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship
    state: Mapped["MaterialsState"] = relationship(back_populates="minerals")

    __table_args__ = (
        Index("idx_state_mineral_year", "year"),
        Index("idx_state_mineral_rank", "rank"),
    )


class MineralTrend(CensusBase):
    """Fact table for aggregate mineral industry trends.

    From MCS2025_T1_Mineral_Industry_Trends.csv. Tracks overall
    mineral sector health and employment.

    Attributes:
        year: Calendar year (primary key).
        mine_production_metals_millions: Metal mining value ($ millions).
        mine_production_industrial_millions: Industrial minerals value.
        mine_production_coal_millions: Coal mining value.
        employment_coal_thousands: Coal mining employment (thousands).
        employment_nonfuel_thousands: Nonfuel minerals employment.
        employment_chemicals_thousands: Chemicals sector employment.
        employment_stone_clay_glass_thousands: Construction materials.
        employment_primary_metal_thousands: Primary metals processing.
        avg_weekly_earnings_coal: Coal miners average weekly earnings.
        avg_weekly_earnings_all: All mining average weekly earnings.
        avg_weekly_earnings_stone_clay_glass: Construction materials earnings.
        avg_weekly_earnings_primary_metal: Primary metals earnings.
    """

    __tablename__ = "mineral_trends"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    mine_production_metals_millions: Mapped[float | None] = mapped_column(Float, nullable=True)
    mine_production_industrial_millions: Mapped[float | None] = mapped_column(Float, nullable=True)
    mine_production_coal_millions: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_coal_thousands: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_nonfuel_thousands: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_chemicals_thousands: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_stone_clay_glass_thousands: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    employment_primary_metal_thousands: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_weekly_earnings_coal: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_weekly_earnings_all: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_weekly_earnings_stone_clay_glass: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_weekly_earnings_primary_metal: Mapped[float | None] = mapped_column(Float, nullable=True)


class ImportSource(CensusBase):
    """Dimension table for major import source countries.

    Tracks countries that supply multiple mineral commodities to the US.
    Key for understanding imperial extraction geography.

    Attributes:
        id: Auto-incrementing primary key.
        country: Country name.
        commodity_count: Number of commodities sourced from this country.
        map_class: Classification for mapping (e.g., "19 to 24", "7 to 12").
    """

    __tablename__ = "import_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    commodity_count: Mapped[int] = mapped_column(Integer, nullable=False)
    map_class: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint("country", name="uq_import_source_country"),
        Index("idx_import_source_count", "commodity_count"),
    )


# Critical minerals list (DOE/USGS designated)
CRITICAL_MINERALS: set[str] = {
    "alumi",  # Aluminum (bauxite)
    "antim",  # Antimony
    "arsen",  # Arsenic
    "barit",  # Barite
    "beryl",  # Beryllium
    "bismu",  # Bismuth
    "cesiu",  # Cesium
    "chrom",  # Chromium
    "cobal",  # Cobalt
    "fluor",  # Fluorite
    "galli",  # Gallium
    "germa",  # Germanium
    "graph",  # Graphite
    "hafni",  # Hafnium
    "indiu",  # Indium
    "lithi",  # Lithium
    "magne",  # Magnesium
    "manga",  # Manganese
    "nicke",  # Nickel
    "niobi",  # Niobium
    "plati",  # Platinum group metals
    "potas",  # Potash
    "reare",  # Rare earth elements
    "rheni",  # Rhenium
    "rubid",  # Rubidium
    "scand",  # Scandium
    "tanta",  # Tantalum
    "tellu",  # Tellurium
    "tin",  # Tin
    "titan",  # Titanium
    "tungs",  # Tungsten
    "vanad",  # Vanadium
    "zinc",  # Zinc
    "zirco",  # Zirconium
}

# Metric category mappings
METRIC_CATEGORIES: dict[str, str] = {
    "USprod": "production",
    "Mine_Production": "production",
    "Imports": "trade",
    "Exports": "trade",
    "Consump": "consumption",
    "Price": "price",
    "NIR": "strategic",
    "Employment": "employment",
    "Stocks": "strategic",
    "Supply": "consumption",
}

# Marxian interpretations for key metrics
METRIC_INTERPRETATIONS: dict[str, str] = {
    "NIR_pct": "Imperial vulnerability index. NIR >50% = dependent on periphery extraction.",
    "USprod": "Domestic extraction capacity - strategic autonomy metric.",
    "Imports": "Materials flowing from periphery to core via unequal exchange.",
    "Exports": "Processed materials flowing to periphery (value-added extraction).",
    "Employment": "Living labor in extraction sector - variable capital.",
}
