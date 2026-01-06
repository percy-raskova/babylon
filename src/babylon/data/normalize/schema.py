"""3NF Normalized SQLite schema for Marxian economic analysis.

Provides properly normalized dimension and fact tables populated via ETL
from research.sqlite. Optimized for imperial rent, surplus value, labor
aristocracy, and unequal exchange analysis.

Dimensions (33 tables):
    Geographic: dim_state, dim_county, dim_metro_area, dim_geographic_hierarchy,
                dim_cfs_area, dim_country, dim_import_source
    Bridge: bridge_county_metro, bridge_cfs_county
    Industry: dim_industry, dim_sector, dim_ownership
    Census Codes: dim_income_bracket, dim_employment_status, dim_worker_class,
                  dim_occupation, dim_education_level, dim_housing_tenure,
                  dim_rent_burden, dim_commute_mode, dim_poverty_category
    Energy: dim_energy_table, dim_energy_series
    FRED: dim_wealth_class, dim_asset_category, dim_fred_series
    Commodities: dim_commodity, dim_commodity_metric, dim_sctg_commodity
    Metadata: dim_time, dim_gender, dim_data_source, dim_race
    Coercive: dim_coercive_type

Facts (28 tables):
    Census (14), QCEW/Productivity (2), Trade (1), Energy (1),
    FRED (5), Commodities (1), Materials (3), Circulatory (4)

Note:
    Census fact tables include time_id and race_id FKs for multi-year and
    race-disaggregated analysis (15 years x 10 race groups).
"""

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from babylon.data.normalize.database import NormalizedBase

# =============================================================================
# GEOGRAPHIC DIMENSION TABLES
# =============================================================================


class DimState(NormalizedBase):
    """US state dimension - unified from Census, FRED, and Materials."""

    __tablename__ = "dim_state"

    state_id: Mapped[int] = mapped_column(primary_key=True)
    state_fips: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    state_name: Mapped[str] = mapped_column(String(100), nullable=False)
    state_abbrev: Mapped[str] = mapped_column(String(2), nullable=False)

    __table_args__ = (Index("idx_state_abbrev", "state_abbrev"),)


class DimCounty(NormalizedBase):
    """US county dimension - primary domestic geographic grain."""

    __tablename__ = "dim_county"

    county_id: Mapped[int] = mapped_column(primary_key=True)
    fips: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    state_id: Mapped[int] = mapped_column(ForeignKey("dim_state.state_id"), nullable=False)
    county_fips: Mapped[str] = mapped_column(String(3), nullable=False)
    county_name: Mapped[str] = mapped_column(String(200), nullable=False)

    __table_args__ = (
        Index("idx_county_state", "state_id"),
        Index("idx_county_name", "county_name"),
    )


class DimMetroArea(NormalizedBase):
    """Metropolitan and Micropolitan Statistical Areas.

    Area Types:
        msa: Metropolitan Statistical Area (50K+ urban core)
        micropolitan: Micropolitan Statistical Area (10K-50K urban core)
        csa: Combined Statistical Area (aggregation of adjacent CBSAs)
    """

    __tablename__ = "dim_metro_area"

    metro_area_id: Mapped[int] = mapped_column(primary_key=True)
    geo_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cbsa_code: Mapped[str | None] = mapped_column(String(10))
    metro_name: Mapped[str] = mapped_column(String(200), nullable=False)
    area_type: Mapped[str] = mapped_column(String(20), nullable=False)  # msa, micropolitan, csa

    __table_args__ = (
        Index("idx_metro_cbsa", "cbsa_code"),
        CheckConstraint("area_type IN ('msa', 'micropolitan', 'csa')", name="ck_metro_area_type"),
    )


class BridgeCountyMetro(NormalizedBase):
    """Many-to-many county-metro mapping."""

    __tablename__ = "bridge_county_metro"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    metro_area_id: Mapped[int] = mapped_column(
        ForeignKey("dim_metro_area.metro_area_id"), primary_key=True
    )
    is_principal_city: Mapped[bool] = mapped_column(default=False)


class DimGeographicHierarchy(NormalizedBase):
    """State-to-county geographic hierarchy with allocation weights.

    Enables disaggregation of state-level external data (e.g., Census CFS)
    to county-level internal schema representation. Each county row contains
    weights for distributing state-level flows proportionally.

    Allocation weight types:
        - population_weight: Share of state population in county
        - employment_weight: Share of state employment in county
        - gdp_weight: Share of state GDP in county (proxy via employment + wages)

    Example usage::

        # Get all counties for California with weights
        SELECT c.county_name, h.population_weight, h.employment_weight
        FROM dim_geographic_hierarchy h
        JOIN dim_county c ON h.county_id = c.county_id
        JOIN dim_state s ON h.state_id = s.state_id
        WHERE s.state_fips = '06'
        ORDER BY h.population_weight DESC
    """

    __tablename__ = "dim_geographic_hierarchy"

    hierarchy_id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("dim_state.state_id"), nullable=False)
    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), nullable=False)
    population_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 8), nullable=False
    )  # 0.0 to 1.0, sum to 1.0 per state
    employment_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 8), nullable=False
    )  # 0.0 to 1.0, sum to 1.0 per state
    gdp_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 8)
    )  # Optional, derived from employment+wages
    source_year: Mapped[int] = mapped_column(nullable=False)  # Year of weight calculation

    __table_args__ = (
        Index("idx_geo_hierarchy_state", "state_id"),
        Index("idx_geo_hierarchy_county", "county_id"),
        # Ensure unique state-county pairing per year
        Index("idx_geo_hierarchy_unique", "state_id", "county_id", "source_year", unique=True),
        CheckConstraint(
            "population_weight >= 0 AND population_weight <= 1",
            name="ck_population_weight_range",
        ),
        CheckConstraint(
            "employment_weight >= 0 AND employment_weight <= 1",
            name="ck_employment_weight_range",
        ),
    )


class DimCFSArea(NormalizedBase):
    """Census Commodity Flow Survey geographic areas (132 FAF zones).

    CFS areas are aggregations of counties used by the Census Bureau for
    commodity flow analysis. Each CFS area maps to one or more counties.
    """

    __tablename__ = "dim_cfs_area"

    cfs_area_id: Mapped[int] = mapped_column(primary_key=True)
    cfs_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    cfs_name: Mapped[str] = mapped_column(String(200), nullable=False)
    state_id: Mapped[int | None] = mapped_column(ForeignKey("dim_state.state_id"))

    __table_args__ = (Index("idx_cfs_area_state", "state_id"),)


class BridgeCFSCounty(NormalizedBase):
    """Many-to-many CFS area to county mapping with allocation weights."""

    __tablename__ = "bridge_cfs_county"

    cfs_area_id: Mapped[int] = mapped_column(
        ForeignKey("dim_cfs_area.cfs_area_id"), primary_key=True
    )
    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    allocation_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 8), nullable=False
    )  # Share of CFS area in this county


class DimSCTGCommodity(NormalizedBase):
    """Standard Classification of Transported Goods (SCTG) commodity codes.

    42 two-digit SCTG codes used by Census CFS for commodity classification.
    """

    __tablename__ = "dim_sctg_commodity"

    sctg_id: Mapped[int] = mapped_column(primary_key=True)
    sctg_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    sctg_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))  # agriculture, mining, manufacturing
    strategic_value: Mapped[str | None] = mapped_column(String(20))  # critical, high, medium, low

    __table_args__ = (
        Index("idx_sctg_category", "category"),
        CheckConstraint(
            "strategic_value IN ('critical', 'high', 'medium', 'low') OR strategic_value IS NULL",
            name="ck_sctg_strategic_value",
        ),
    )


class DimCountry(NormalizedBase):
    """International trade partners with world-system classification."""

    __tablename__ = "dim_country"

    country_id: Mapped[int] = mapped_column(primary_key=True)
    cty_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    country_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_region: Mapped[bool] = mapped_column(default=False)
    world_system_tier: Mapped[str | None] = mapped_column(
        String(20)
    )  # core/semi_periphery/periphery

    __table_args__ = (
        Index("idx_country_tier", "world_system_tier"),
        Index("idx_country_name", "country_name"),
        CheckConstraint(
            "world_system_tier IN ('core', 'semi_periphery', 'periphery') OR world_system_tier IS NULL",
            name="ck_world_system_tier",
        ),
    )


class DimImportSource(NormalizedBase):
    """Import source countries with geopolitical classification."""

    __tablename__ = "dim_import_source"

    import_source_id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    commodity_count: Mapped[int | None] = mapped_column()
    map_class: Mapped[str | None] = mapped_column(String(50))  # Geopolitical classification


# =============================================================================
# INDUSTRY & OWNERSHIP DIMENSION TABLES
# =============================================================================


class DimIndustry(NormalizedBase):
    """Unified NAICS industry dimension bridging QCEW, Productivity, and FRED."""

    __tablename__ = "dim_industry"

    industry_id: Mapped[int] = mapped_column(primary_key=True)
    naics_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    industry_title: Mapped[str] = mapped_column(String(300), nullable=False)
    naics_level: Mapped[int] = mapped_column(nullable=False)  # 0-6
    parent_naics_code: Mapped[str | None] = mapped_column(String(20))
    sector_code: Mapped[str | None] = mapped_column(String(2))  # 2-digit for rollup

    # Marxian classification
    class_composition: Mapped[str | None] = mapped_column(String(20))

    # Data source flags
    has_productivity_data: Mapped[bool] = mapped_column(default=False)
    has_fred_data: Mapped[bool] = mapped_column(default=False)
    has_qcew_data: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        Index("idx_industry_level", "naics_level"),
        Index("idx_industry_sector", "sector_code"),
        Index("idx_industry_class", "class_composition"),
        Index("idx_industry_parent", "parent_naics_code"),
        CheckConstraint(
            "class_composition IN ('goods_producing', 'service_producing', 'circulation', "
            "'government', 'extraction') OR class_composition IS NULL",
            name="ck_class_composition",
        ),
    )


class DimSector(NormalizedBase):
    """High-level 2-digit NAICS sector aggregation."""

    __tablename__ = "dim_sector"

    sector_id: Mapped[int] = mapped_column(primary_key=True)
    sector_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    sector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_composition: Mapped[str] = mapped_column(String(20), nullable=False)


class DimOwnership(NormalizedBase):
    """QCEW ownership types with government/private flags."""

    __tablename__ = "dim_ownership"

    ownership_id: Mapped[int] = mapped_column(primary_key=True)
    own_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    own_title: Mapped[str] = mapped_column(String(50), nullable=False)
    is_government: Mapped[bool] = mapped_column(nullable=False)
    is_private: Mapped[bool] = mapped_column(nullable=False)


# =============================================================================
# CENSUS CODE DIMENSION TABLES (Extracted Labels)
# =============================================================================


class DimIncomeBracket(NormalizedBase):
    """Income distribution brackets from census_income_distribution."""

    __tablename__ = "dim_income_bracket"

    bracket_id: Mapped[int] = mapped_column(primary_key=True)
    bracket_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    bracket_label: Mapped[str] = mapped_column(String(100), nullable=False)
    bracket_min_usd: Mapped[int | None] = mapped_column()
    bracket_max_usd: Mapped[int | None] = mapped_column()  # NULL = open-ended
    bracket_order: Mapped[int] = mapped_column(nullable=False)


class DimEmploymentStatus(NormalizedBase):
    """Employment status categories from census_employment_status."""

    __tablename__ = "dim_employment_status"

    status_id: Mapped[int] = mapped_column(primary_key=True)
    status_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status_label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_labor_force: Mapped[bool | None] = mapped_column()
    is_employed: Mapped[bool | None] = mapped_column()
    status_order: Mapped[int] = mapped_column(nullable=False)


class DimWorkerClass(NormalizedBase):
    """Class of worker from census_worker_class with Marxian mapping."""

    __tablename__ = "dim_worker_class"

    class_id: Mapped[int] = mapped_column(primary_key=True)
    class_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    class_label: Mapped[str] = mapped_column(String(200), nullable=False)
    marxian_class: Mapped[str | None] = mapped_column(String(20))
    class_order: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint(
            "marxian_class IN ('proletariat', 'petty_bourgeois', 'state_worker', 'unpaid_labor') "
            "OR marxian_class IS NULL",
            name="ck_marxian_class",
        ),
    )


class DimOccupation(NormalizedBase):
    """Occupation codes from census_occupation with labor type classification."""

    __tablename__ = "dim_occupation"

    occupation_id: Mapped[int] = mapped_column(primary_key=True)
    occupation_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    occupation_label: Mapped[str] = mapped_column(String(300), nullable=False)
    occupation_category: Mapped[str | None] = mapped_column(String(100))
    labor_type: Mapped[str | None] = mapped_column(String(20))
    occupation_order: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_occupation_category", "occupation_category"),
        Index("idx_occupation_labor_type", "labor_type"),
        CheckConstraint(
            "labor_type IN ('productive', 'unproductive', 'reproductive', 'managerial') "
            "OR labor_type IS NULL",
            name="ck_labor_type",
        ),
    )


class DimEducationLevel(NormalizedBase):
    """Education levels from census_education."""

    __tablename__ = "dim_education_level"

    level_id: Mapped[int] = mapped_column(primary_key=True)
    level_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    level_label: Mapped[str] = mapped_column(String(200), nullable=False)
    years_of_schooling: Mapped[int | None] = mapped_column()
    level_order: Mapped[int] = mapped_column(nullable=False)


class DimHousingTenure(NormalizedBase):
    """Housing tenure types (Owner/Renter)."""

    __tablename__ = "dim_housing_tenure"

    tenure_id: Mapped[int] = mapped_column(primary_key=True)
    tenure_type: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    tenure_label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_owner: Mapped[bool] = mapped_column(nullable=False)


class DimRentBurden(NormalizedBase):
    """Rent burden brackets from census_rent_burden."""

    __tablename__ = "dim_rent_burden"

    burden_id: Mapped[int] = mapped_column(primary_key=True)
    bracket_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    burden_bracket: Mapped[str] = mapped_column(String(50), nullable=False)
    burden_min_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    burden_max_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    is_cost_burdened: Mapped[bool | None] = mapped_column()  # >= 30%
    is_severely_burdened: Mapped[bool | None] = mapped_column()  # >= 50%
    bracket_order: Mapped[int] = mapped_column(nullable=False)


class DimCommuteMode(NormalizedBase):
    """Commute mode from census_commute."""

    __tablename__ = "dim_commute_mode"

    mode_id: Mapped[int] = mapped_column(primary_key=True)
    mode_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    mode_label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_public_transit: Mapped[bool | None] = mapped_column()
    is_active_transport: Mapped[bool | None] = mapped_column()  # Walk, bike
    mode_order: Mapped[int] = mapped_column(nullable=False)


class DimPovertyCategory(NormalizedBase):
    """Poverty categories from census_poverty."""

    __tablename__ = "dim_poverty_category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    category_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    category_label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_below_poverty: Mapped[bool | None] = mapped_column()
    category_order: Mapped[int] = mapped_column(nullable=False)


# =============================================================================
# ENERGY DIMENSION TABLES
# =============================================================================


class DimEnergyTable(NormalizedBase):
    """Energy table metadata with Marxian interpretation."""

    __tablename__ = "dim_energy_table"

    table_id: Mapped[int] = mapped_column(primary_key=True)
    table_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    marxian_interpretation: Mapped[str | None] = mapped_column(Text)


class DimEnergySeries(NormalizedBase):
    """Energy series dimension."""

    __tablename__ = "dim_energy_series"

    series_id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("dim_energy_table.table_id"), nullable=False)
    series_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    series_name: Mapped[str] = mapped_column(String(200), nullable=False)
    units: Mapped[str | None] = mapped_column(String(50))
    column_index: Mapped[int | None] = mapped_column()


# =============================================================================
# FRED DIMENSION TABLES
# =============================================================================


class DimWealthClass(NormalizedBase):
    """FRED wealth percentile classes with Babylon mapping."""

    __tablename__ = "dim_wealth_class"

    wealth_class_id: Mapped[int] = mapped_column(primary_key=True)
    percentile_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    percentile_label: Mapped[str] = mapped_column(String(100), nullable=False)
    babylon_class: Mapped[str | None] = mapped_column(String(50))  # Maps to Babylon social class


class DimAssetCategory(NormalizedBase):
    """FRED asset categories with Marxian interpretation."""

    __tablename__ = "dim_asset_category"

    category_id: Mapped[int] = mapped_column(primary_key=True)
    category_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    category_label: Mapped[str] = mapped_column(String(100), nullable=False)
    marxian_interpretation: Mapped[str | None] = mapped_column(Text)


class DimFredSeries(NormalizedBase):
    """FRED series metadata."""

    __tablename__ = "dim_fred_series"

    series_id: Mapped[int] = mapped_column(primary_key=True)
    series_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    units: Mapped[str | None] = mapped_column(String(50))
    frequency: Mapped[str | None] = mapped_column(String(20))
    seasonal_adjustment: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str | None] = mapped_column(String(100))


# =============================================================================
# COMMODITIES DIMENSION TABLES
# =============================================================================


class DimCommodity(NormalizedBase):
    """Critical commodities with Marxian interpretation."""

    __tablename__ = "dim_commodity"

    commodity_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_critical: Mapped[bool | None] = mapped_column()
    primary_applications: Mapped[str | None] = mapped_column(Text)
    marxian_interpretation: Mapped[str | None] = mapped_column(Text)


class DimCommodityMetric(NormalizedBase):
    """Commodity metrics with categories."""

    __tablename__ = "dim_commodity_metric"

    metric_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    units: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str | None] = mapped_column(String(50))  # Production, Reserves, Price
    marxian_interpretation: Mapped[str | None] = mapped_column(Text)


# =============================================================================
# METADATA DIMENSION TABLES
# =============================================================================


class DimTime(NormalizedBase):
    """Calendar dimension for temporal analysis."""

    __tablename__ = "dim_time"

    time_id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False)
    month: Mapped[int | None] = mapped_column()  # NULL for annual data
    quarter: Mapped[int | None] = mapped_column()  # 1-4
    is_annual: Mapped[bool] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_time_year", "year"),
        Index("idx_time_annual", "is_annual"),
    )


class DimGender(NormalizedBase):
    """Gender dimension for disaggregated census data."""

    __tablename__ = "dim_gender"

    gender_id: Mapped[int] = mapped_column(primary_key=True)
    gender_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    gender_label: Mapped[str] = mapped_column(String(20), nullable=False)


class DimDataSource(NormalizedBase):
    """Data source tracking for provenance."""

    __tablename__ = "dim_data_source"

    source_id: Mapped[int] = mapped_column(primary_key=True)
    source_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    source_year: Mapped[int | None] = mapped_column()
    source_agency: Mapped[str | None] = mapped_column(String(100))
    coverage_start_year: Mapped[int | None] = mapped_column()
    coverage_end_year: Mapped[int | None] = mapped_column()


class DimRace(NormalizedBase):
    """Race/ethnicity dimension following Census A-I suffix scheme.

    Enables analysis of national oppression and class composition by race,
    critical for understanding material conditions in MLM-TW framework.

    Census Race Codes:
        A = White alone
        B = Black or African American alone
        C = American Indian and Alaska Native alone
        D = Asian alone
        E = Native Hawaiian and Other Pacific Islander alone
        F = Some other race alone
        G = Two or more races
        H = White alone, not Hispanic or Latino
        I = Hispanic or Latino
        T = Total (all races, base table)
    """

    __tablename__ = "dim_race"

    race_id: Mapped[int] = mapped_column(primary_key=True)
    race_code: Mapped[str] = mapped_column(String(1), unique=True, nullable=False)
    race_name: Mapped[str] = mapped_column(String(100), nullable=False)
    race_short_name: Mapped[str] = mapped_column(String(20), nullable=False)
    is_hispanic_ethnicity: Mapped[bool] = mapped_column(default=False)
    is_indigenous: Mapped[bool] = mapped_column(default=False)
    display_order: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        Index("idx_race_code", "race_code"),
        CheckConstraint(
            "race_code IN ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'T')",
            name="ck_race_code_valid",
        ),
    )


# =============================================================================
# COERCIVE INFRASTRUCTURE DIMENSION TABLES
# =============================================================================


class DimCoerciveType(NormalizedBase):
    """Coercive infrastructure type classification.

    Categorizes state power apparatus by function and command chain:
    - Carceral: prisons, jails, detention centers
    - Enforcement: police stations, sheriff offices
    - Military: bases, armories, installations
    """

    __tablename__ = "dim_coercive_type"

    coercive_type_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # carceral, enforcement, military
    command_chain: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # federal, state, local, mixed

    __table_args__ = (
        Index("idx_coercive_category", "category"),
        Index("idx_coercive_command", "command_chain"),
        CheckConstraint(
            "category IN ('carceral', 'enforcement', 'military')",
            name="ck_coercive_category",
        ),
        CheckConstraint(
            "command_chain IN ('federal', 'state', 'local', 'mixed')",
            name="ck_coercive_command_chain",
        ),
    )


# =============================================================================
# CENSUS FACT TABLES
# =============================================================================


class FactCensusIncome(NormalizedBase):
    """Income distribution by county, time, and race."""

    __tablename__ = "fact_census_income"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    bracket_id: Mapped[int] = mapped_column(
        ForeignKey("dim_income_bracket.bracket_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    household_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_income_county", "county_id"),
        Index("idx_income_time", "time_id"),
        Index("idx_income_race", "race_id"),
    )


class FactCensusMedianIncome(NormalizedBase):
    """Median income by county, time, and race."""

    __tablename__ = "fact_census_median_income"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    median_income_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (
        Index("idx_median_income_time", "time_id"),
        Index("idx_median_income_race", "race_id"),
    )


class FactCensusEmployment(NormalizedBase):
    """Employment status by county, time, and race."""

    __tablename__ = "fact_census_employment"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey("dim_employment_status.status_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    person_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_employment_time", "time_id"),
        Index("idx_employment_race", "race_id"),
    )


class FactCensusWorkerClass(NormalizedBase):
    """Class of worker by county, gender, time, and race."""

    __tablename__ = "fact_census_worker_class"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    gender_id: Mapped[int] = mapped_column(ForeignKey("dim_gender.gender_id"), primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("dim_worker_class.class_id"), primary_key=True)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    worker_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_worker_class_time", "time_id"),
        Index("idx_worker_class_race", "race_id"),
    )


class FactCensusOccupation(NormalizedBase):
    """Occupation by county, gender, time, and race."""

    __tablename__ = "fact_census_occupation"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    gender_id: Mapped[int] = mapped_column(ForeignKey("dim_gender.gender_id"), primary_key=True)
    occupation_id: Mapped[int] = mapped_column(
        ForeignKey("dim_occupation.occupation_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    worker_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_occupation_county", "county_id"),
        Index("idx_occupation_time", "time_id"),
        Index("idx_occupation_race", "race_id"),
    )


class FactCensusHours(NormalizedBase):
    """Hours worked by county, gender, time, and race."""

    __tablename__ = "fact_census_hours"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    gender_id: Mapped[int] = mapped_column(ForeignKey("dim_gender.gender_id"), primary_key=True)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    aggregate_hours: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    mean_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    __table_args__ = (
        Index("idx_hours_time", "time_id"),
        Index("idx_hours_race", "race_id"),
    )


class FactCensusHousing(NormalizedBase):
    """Housing tenure by county, time, and race."""

    __tablename__ = "fact_census_housing"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    tenure_id: Mapped[int] = mapped_column(
        ForeignKey("dim_housing_tenure.tenure_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    household_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_housing_time", "time_id"),
        Index("idx_housing_race", "race_id"),
    )


class FactCensusRent(NormalizedBase):
    """Median rent by county, time, and race."""

    __tablename__ = "fact_census_rent"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    median_rent_usd: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    __table_args__ = (
        Index("idx_rent_time", "time_id"),
        Index("idx_rent_race", "race_id"),
    )


class FactCensusRentBurden(NormalizedBase):
    """Rent burden distribution by county, time, and race."""

    __tablename__ = "fact_census_rent_burden"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    burden_id: Mapped[int] = mapped_column(
        ForeignKey("dim_rent_burden.burden_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    household_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_rent_burden_time", "time_id"),
        Index("idx_rent_burden_race", "race_id"),
    )


class FactCensusEducation(NormalizedBase):
    """Education attainment by county, time, and race."""

    __tablename__ = "fact_census_education"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    level_id: Mapped[int] = mapped_column(
        ForeignKey("dim_education_level.level_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    person_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_education_time", "time_id"),
        Index("idx_education_race", "race_id"),
    )


class FactCensusGini(NormalizedBase):
    """Gini inequality coefficient by county, time, and race."""

    __tablename__ = "fact_census_gini"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    gini_coefficient: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "gini_coefficient >= 0 AND gini_coefficient <= 1",
            name="ck_gini_range",
        ),
        Index("idx_gini_time", "time_id"),
        Index("idx_gini_race", "race_id"),
    )


class FactCensusCommute(NormalizedBase):
    """Commute mode by county, time, and race."""

    __tablename__ = "fact_census_commute"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    mode_id: Mapped[int] = mapped_column(ForeignKey("dim_commute_mode.mode_id"), primary_key=True)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    worker_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_commute_time", "time_id"),
        Index("idx_commute_race", "race_id"),
    )


class FactCensusPoverty(NormalizedBase):
    """Poverty status by county, time, and race."""

    __tablename__ = "fact_census_poverty"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("dim_poverty_category.category_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    person_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("idx_poverty_time", "time_id"),
        Index("idx_poverty_race", "race_id"),
    )


class FactCensusIncomeSources(NormalizedBase):
    """Income sources (wage/self-employment/investment) by county, time, and race."""

    __tablename__ = "fact_census_income_sources"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("dim_race.race_id"), primary_key=True)
    total_households: Mapped[int | None] = mapped_column()
    with_wage_income: Mapped[int | None] = mapped_column()
    with_self_employment_income: Mapped[int | None] = mapped_column()
    with_investment_income: Mapped[int | None] = mapped_column()

    __table_args__ = (
        Index("idx_income_sources_time", "time_id"),
        Index("idx_income_sources_race", "race_id"),
    )


# =============================================================================
# QCEW / PRODUCTIVITY FACT TABLES
# =============================================================================


class FactQcewAnnual(NormalizedBase):
    """QCEW annual employment/wage data."""

    __tablename__ = "fact_qcew_annual"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    industry_id: Mapped[int] = mapped_column(
        ForeignKey("dim_industry.industry_id"), primary_key=True
    )
    ownership_id: Mapped[int] = mapped_column(
        ForeignKey("dim_ownership.ownership_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)

    establishments: Mapped[int | None] = mapped_column()
    employment: Mapped[int | None] = mapped_column()
    total_wages_usd: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    avg_weekly_wage_usd: Mapped[int | None] = mapped_column()
    avg_annual_pay_usd: Mapped[int | None] = mapped_column()
    lq_employment: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    lq_annual_pay: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    disclosure_code: Mapped[str | None] = mapped_column(String(5))

    __table_args__ = (
        Index("idx_qcew_county_time", "county_id", "time_id"),
        Index("idx_qcew_industry_time", "industry_id", "time_id"),
        Index("idx_qcew_ownership", "ownership_id"),
    )


class FactProductivityAnnual(NormalizedBase):
    """BLS productivity data for surplus value analysis."""

    __tablename__ = "fact_productivity_annual"

    industry_id: Mapped[int] = mapped_column(
        ForeignKey("dim_industry.industry_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)

    # Indices
    labor_productivity_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    hours_worked_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    hourly_compensation_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    unit_labor_costs_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    real_output_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    sectoral_output_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))

    # Absolute measures (key for Marxian analysis)
    hours_worked_millions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    employment_thousands: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    labor_compensation_millions_usd: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    sectoral_output_millions_usd: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    __table_args__ = (Index("idx_productivity_time", "time_id"),)


# =============================================================================
# TRADE FACT TABLES
# =============================================================================


class FactTradeMonthly(NormalizedBase):
    """Monthly trade flows with countries."""

    __tablename__ = "fact_trade_monthly"

    country_id: Mapped[int] = mapped_column(ForeignKey("dim_country.country_id"), primary_key=True)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    imports_usd_millions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    exports_usd_millions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    __table_args__ = (
        Index("idx_trade_country_time", "country_id", "time_id"),
        Index("idx_trade_time", "time_id"),
    )


# =============================================================================
# ENERGY FACT TABLES
# =============================================================================


class FactEnergyAnnual(NormalizedBase):
    """Annual energy consumption/production by series."""

    __tablename__ = "fact_energy_annual"

    series_id: Mapped[int] = mapped_column(
        ForeignKey("dim_energy_series.series_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))


# =============================================================================
# FRED FACT TABLES
# =============================================================================


class FactFredNational(NormalizedBase):
    """FRED national economic data."""

    __tablename__ = "fact_fred_national"

    series_id: Mapped[int] = mapped_column(
        ForeignKey("dim_fred_series.series_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))


class FactFredWealthLevels(NormalizedBase):
    """FRED wealth levels by percentile class and asset category."""

    __tablename__ = "fact_fred_wealth_levels"

    series_id: Mapped[int] = mapped_column(
        ForeignKey("dim_fred_series.series_id"), primary_key=True
    )
    wealth_class_id: Mapped[int] = mapped_column(
        ForeignKey("dim_wealth_class.wealth_class_id"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("dim_asset_category.category_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    value_millions: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))


class FactFredWealthShares(NormalizedBase):
    """FRED wealth shares by percentile class and asset category."""

    __tablename__ = "fact_fred_wealth_shares"

    series_id: Mapped[int] = mapped_column(
        ForeignKey("dim_fred_series.series_id"), primary_key=True
    )
    wealth_class_id: Mapped[int] = mapped_column(
        ForeignKey("dim_wealth_class.wealth_class_id"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("dim_asset_category.category_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    share_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))


class FactFredIndustryUnemployment(NormalizedBase):
    """FRED unemployment by industry."""

    __tablename__ = "fact_fred_industry_unemployment"

    industry_id: Mapped[int] = mapped_column(
        ForeignKey("dim_industry.industry_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    unemployment_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class FactFredStateUnemployment(NormalizedBase):
    """FRED unemployment by state."""

    __tablename__ = "fact_fred_state_unemployment"

    state_id: Mapped[int] = mapped_column(ForeignKey("dim_state.state_id"), primary_key=True)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    unemployment_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


# =============================================================================
# COMMODITIES FACT TABLES
# =============================================================================


class FactCommodityObservation(NormalizedBase):
    """Commodity observation (production, reserves, price, etc.)."""

    __tablename__ = "fact_commodity_observation"

    commodity_id: Mapped[int] = mapped_column(
        ForeignKey("dim_commodity.commodity_id"), primary_key=True
    )
    metric_id: Mapped[int] = mapped_column(
        ForeignKey("dim_commodity_metric.metric_id"), primary_key=True
    )
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    value_text: Mapped[str | None] = mapped_column(String(100))  # For non-numeric values


# =============================================================================
# MATERIALS/MINERALS FACT TABLES
# =============================================================================


class FactStateMinerals(NormalizedBase):
    """State mineral production value."""

    __tablename__ = "fact_state_minerals"

    state_id: Mapped[int] = mapped_column(ForeignKey("dim_state.state_id"), primary_key=True)
    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    value_millions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    rank: Mapped[int | None] = mapped_column()
    percent_total: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    principal_commodities: Mapped[str | None] = mapped_column(Text)


class FactMineralProduction(NormalizedBase):
    """National mineral production by type (normalized from mineral_trends)."""

    __tablename__ = "fact_mineral_production"

    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    production_type: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )  # metals, industrial, coal
    value_millions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))


class FactMineralEmployment(NormalizedBase):
    """Mineral industry employment (normalized from mineral_trends)."""

    __tablename__ = "fact_mineral_employment"

    time_id: Mapped[int] = mapped_column(ForeignKey("dim_time.time_id"), primary_key=True)
    sector: Mapped[str] = mapped_column(
        String(50), primary_key=True
    )  # coal, nonfuel, chemicals, etc.
    employment_thousands: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    avg_weekly_earnings_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))


# =============================================================================
# CIRCULATORY SYSTEM FACT TABLES
# =============================================================================


class FactCoerciveInfrastructure(NormalizedBase):
    """County-level coercive infrastructure capacity.

    Aggregates facility-level data from HIFLD (prisons, police) and MIRTA
    (military) to county-level counts and capacity metrics.
    """

    __tablename__ = "fact_coercive_infrastructure"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    coercive_type_id: Mapped[int] = mapped_column(
        ForeignKey("dim_coercive_type.coercive_type_id"), primary_key=True
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    facility_count: Mapped[int] = mapped_column(default=0)
    total_capacity: Mapped[int | None] = mapped_column()  # beds, personnel, etc.

    __table_args__ = (
        Index("idx_coercive_county", "county_id"),
        Index("idx_coercive_type_fact", "coercive_type_id"),
    )


class FactBroadbandCoverage(NormalizedBase):
    """County-level broadband coverage metrics from FCC BDC.

    Tracks broadband access at multiple speed tiers for digital divide analysis.
    """

    __tablename__ = "fact_broadband_coverage"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    pct_25_3: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # % with 25/3 Mbps
    pct_100_20: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # % with 100/20 Mbps
    pct_1000_100: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # % with gigabit
    provider_count: Mapped[int | None] = mapped_column()

    __table_args__ = (Index("idx_broadband_county", "county_id"),)


class FactElectricGrid(NormalizedBase):
    """County-level electric grid infrastructure from HIFLD.

    Tracks power infrastructure capacity for critical infrastructure modeling.
    """

    __tablename__ = "fact_electric_grid"

    county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("dim_data_source.source_id"), primary_key=True
    )
    substation_count: Mapped[int] = mapped_column(default=0)
    total_capacity_mw: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    transmission_line_miles: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    __table_args__ = (Index("idx_electric_county", "county_id"),)


class FactCommodityFlow(NormalizedBase):
    """State-level commodity flows from Census CFS, allocated to counties.

    Stores origin-destination commodity flow data from the Commodity Flow Survey.
    State-level CFS data is disaggregated to county level using allocation weights
    from DimGeographicHierarchy.

    Flow values are in millions USD (value_millions) and thousands of tons (tons_thousands).
    """

    __tablename__ = "fact_commodity_flow"

    flow_id: Mapped[int] = mapped_column(primary_key=True)
    origin_county_id: Mapped[int] = mapped_column(
        ForeignKey("dim_county.county_id"), nullable=False
    )
    dest_county_id: Mapped[int] = mapped_column(ForeignKey("dim_county.county_id"), nullable=False)
    sctg_id: Mapped[int] = mapped_column(ForeignKey("dim_sctg_commodity.sctg_id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("dim_data_source.source_id"), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    value_millions: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))  # USD millions
    tons_thousands: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))  # Thousands of tons
    ton_miles_millions: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))  # Millions ton-miles
    mode_code: Mapped[str | None] = mapped_column(String(10))  # Transport mode

    __table_args__ = (
        Index("idx_commodity_flow_origin", "origin_county_id"),
        Index("idx_commodity_flow_dest", "dest_county_id"),
        Index("idx_commodity_flow_sctg", "sctg_id"),
        Index("idx_commodity_flow_year", "year"),
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Dimensions - Geographic
    "DimState",
    "DimCounty",
    "DimMetroArea",
    "BridgeCountyMetro",
    "DimGeographicHierarchy",
    "DimCFSArea",
    "BridgeCFSCounty",
    "DimSCTGCommodity",
    "DimCountry",
    "DimImportSource",
    # Dimensions - Industry
    "DimIndustry",
    "DimSector",
    "DimOwnership",
    # Dimensions - Census Codes
    "DimIncomeBracket",
    "DimEmploymentStatus",
    "DimWorkerClass",
    "DimOccupation",
    "DimEducationLevel",
    "DimHousingTenure",
    "DimRentBurden",
    "DimCommuteMode",
    "DimPovertyCategory",
    # Dimensions - Energy
    "DimEnergyTable",
    "DimEnergySeries",
    # Dimensions - FRED
    "DimWealthClass",
    "DimAssetCategory",
    "DimFredSeries",
    # Dimensions - Commodities
    "DimCommodity",
    "DimCommodityMetric",
    # Dimensions - Metadata
    "DimTime",
    "DimGender",
    "DimDataSource",
    "DimRace",
    # Dimensions - Coercive Infrastructure
    "DimCoerciveType",
    # Facts - Census
    "FactCensusIncome",
    "FactCensusMedianIncome",
    "FactCensusEmployment",
    "FactCensusWorkerClass",
    "FactCensusOccupation",
    "FactCensusHours",
    "FactCensusHousing",
    "FactCensusRent",
    "FactCensusRentBurden",
    "FactCensusEducation",
    "FactCensusGini",
    "FactCensusCommute",
    "FactCensusPoverty",
    "FactCensusIncomeSources",
    # Facts - QCEW/Productivity
    "FactQcewAnnual",
    "FactProductivityAnnual",
    # Facts - Trade
    "FactTradeMonthly",
    # Facts - Energy
    "FactEnergyAnnual",
    # Facts - FRED
    "FactFredNational",
    "FactFredWealthLevels",
    "FactFredWealthShares",
    "FactFredIndustryUnemployment",
    "FactFredStateUnemployment",
    # Facts - Commodities
    "FactCommodityObservation",
    # Facts - Materials
    "FactStateMinerals",
    "FactMineralProduction",
    "FactMineralEmployment",
    # Facts - Circulatory System
    "FactCoerciveInfrastructure",
    "FactBroadbandCoverage",
    "FactElectricGrid",
    "FactCommodityFlow",
]
