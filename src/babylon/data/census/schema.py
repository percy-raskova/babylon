"""SQLite schema for Census ACS research data.

Normalized star schema with counties as the central dimension table,
aligned with QCEW data via 5-digit FIPS codes for labor analysis.

Tables:
    Dimension Tables:
        - census_counties: Geographic reference (~3,200 US counties)
        - census_data_sources: Data variant tracking (API year)

    Fact Tables (Original 8):
        - census_median_income: B19013 - Median household income
        - census_income_distribution: B19001 - Income bracket distribution
        - census_employment_status: B23025 - Labor force status
        - census_worker_class: B24080 - Class of worker by gender
        - census_housing_tenure: B25003 - Owner vs renter
        - census_median_rent: B25064 - Median gross rent
        - census_rent_burden: B25070 - Rent as % of income
        - census_occupation: C24010 - Occupation by gender

    Fact Tables (Marxian Analysis - 8 new):
        - census_hours_worked: B23020 - Aggregate/mean hours worked (labor time proxy)
        - census_poverty: B17001 - Poverty status (reserve army metric)
        - census_education: B15003 - Educational attainment (skills reproduction)
        - census_gini: B19083 - GINI coefficient (inequality measure)
        - census_commute: B08301 - Commute mode (unproductive labor time)
        - census_wage_income: B19052 - Wage income indicator (labor income flag)
        - census_self_employment: B19053 - Self-employment income (petty bourgeois)
        - census_investment_income: B19054 - Interest/dividend income (capital income)

    Metadata:
        - census_column_metadata: Column label definitions
"""

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from babylon.data.census.database import CensusBase

# =============================================================================
# DIMENSION TABLES
# =============================================================================


class CensusCounty(CensusBase):
    """US Counties - geographic dimension aligned with QCEW.

    Uses 5-digit FIPS codes (state_fips + county_fips) matching
    QCEW's area_fips for cross-dataset joins.
    """

    __tablename__ = "census_counties"

    id: Mapped[int] = mapped_column(primary_key=True)
    fips: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    state_fips: Mapped[str] = mapped_column(String(2), nullable=False)
    county_fips: Mapped[str] = mapped_column(String(3), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    state_name: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        Index("idx_county_state", "state_fips"),
        Index("idx_county_name", "name"),
    )


# Backwards compatibility alias
CensusMetroArea = CensusCounty


class CensusDataSource(CensusBase):
    """Data source tracking - API year and dataset."""

    __tablename__ = "census_data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int | None] = mapped_column()
    description: Mapped[str | None] = mapped_column(String(200))


# =============================================================================
# ORIGINAL FACT TABLES (8)
# =============================================================================


class CensusMedianIncome(CensusBase):
    """B19013 - Median Household Income."""

    __tablename__ = "census_median_income"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    estimate: Mapped[float] = mapped_column(nullable=False)


class CensusIncomeDistribution(CensusBase):
    """B19001 - Household Income Distribution by bracket."""

    __tablename__ = "census_income_distribution"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    bracket_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    bracket_label: Mapped[str | None] = mapped_column(String(100))
    estimate: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("idx_income_county", "county_id"),)


class CensusEmploymentStatus(CensusBase):
    """B23025 - Employment Status for population 16+."""

    __tablename__ = "census_employment_status"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    category_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    category_label: Mapped[str | None] = mapped_column(String(100))
    estimate: Mapped[int] = mapped_column(nullable=False)


class CensusWorkerClass(CensusBase):
    """B24080 - Class of Worker by gender."""

    __tablename__ = "census_worker_class"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    gender: Mapped[str] = mapped_column(String(10), primary_key=True)
    class_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    class_label: Mapped[str | None] = mapped_column(String(200))
    estimate: Mapped[int] = mapped_column(nullable=False)


class CensusHousingTenure(CensusBase):
    """B25003 - Housing Units by Occupancy Type."""

    __tablename__ = "census_housing_tenure"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    tenure_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    estimate: Mapped[int] = mapped_column(nullable=False)


class CensusMedianRent(CensusBase):
    """B25064 - Median Gross Rent."""

    __tablename__ = "census_median_rent"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    estimate: Mapped[float] = mapped_column(nullable=False)


class CensusRentBurden(CensusBase):
    """B25070 - Gross Rent as Percentage of Household Income."""

    __tablename__ = "census_rent_burden"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    bracket_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    burden_bracket: Mapped[str | None] = mapped_column(String(50))
    estimate: Mapped[int] = mapped_column(nullable=False)


class CensusOccupation(CensusBase):
    """C24010 - Occupation by Gender (flattened hierarchy)."""

    __tablename__ = "census_occupation"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    gender: Mapped[str] = mapped_column(String(10), primary_key=True)
    occupation_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    occupation_label: Mapped[str | None] = mapped_column(String(300))
    occupation_category: Mapped[str | None] = mapped_column(String(100))
    estimate: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("idx_occupation_category", "occupation_category"),)


# =============================================================================
# MARXIAN ANALYSIS FACT TABLES (8 new)
# =============================================================================


class CensusHoursWorked(CensusBase):
    """B23020 - Aggregate and Mean Hours Worked.

    Key metric for Marxian value analysis: labor time is the
    fundamental measure of value production.
    """

    __tablename__ = "census_hours_worked"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    gender: Mapped[str] = mapped_column(String(10), primary_key=True)
    # Aggregate usual hours worked per week (in 10s of hours)
    aggregate_hours: Mapped[float | None] = mapped_column()
    # Mean usual hours worked per week
    mean_hours: Mapped[float | None] = mapped_column()

    __table_args__ = (Index("idx_hours_county", "county_id"),)


class CensusPoverty(CensusBase):
    """B17001 - Poverty Status in Past 12 Months.

    Reserve army of labor metric: population below poverty line
    represents surplus labor available to capital.
    """

    __tablename__ = "census_poverty"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    category_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    category_label: Mapped[str | None] = mapped_column(String(200))
    # Age/gender breakdown available
    estimate: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("idx_poverty_county", "county_id"),)


class CensusEducation(CensusBase):
    """B15003 - Educational Attainment for Population 25+.

    Skills reproduction: education levels indicate investment
    in human capital and class mobility potential.
    """

    __tablename__ = "census_education"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    level_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    level_label: Mapped[str | None] = mapped_column(String(200))
    estimate: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("idx_education_county", "county_id"),)


class CensusGini(CensusBase):
    """B19083 - GINI Index of Income Inequality.

    Single-value inequality measure per county.
    Range: 0 (perfect equality) to 1 (perfect inequality).
    """

    __tablename__ = "census_gini"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    gini_index: Mapped[float] = mapped_column(nullable=False)


class CensusCommute(CensusBase):
    """B08301 - Means of Transportation to Work.

    Unproductive labor time: commute represents time workers
    spend that produces no value but is necessary for employment.
    """

    __tablename__ = "census_commute"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    mode_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    mode_label: Mapped[str | None] = mapped_column(String(200))
    estimate: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("idx_commute_county", "county_id"),)


class CensusWageIncome(CensusBase):
    """B19052 - Wage or Salary Income in Past 12 Months.

    Labor income flag: households receiving wage income
    represent the proletariat (sellers of labor-power).
    """

    __tablename__ = "census_wage_income"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    # B19052_001E = Total, B19052_002E = With wages, B19052_003E = Without
    total_households: Mapped[int | None] = mapped_column()
    with_wages: Mapped[int | None] = mapped_column()
    without_wages: Mapped[int | None] = mapped_column()


class CensusSelfEmployment(CensusBase):
    """B19053 - Self-Employment Income in Past 12 Months.

    Petty bourgeois flag: households with self-employment income
    occupy an intermediate class position.
    """

    __tablename__ = "census_self_employment"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    # B19053_001E = Total, B19053_002E = With self-emp, B19053_003E = Without
    total_households: Mapped[int | None] = mapped_column()
    with_self_employment: Mapped[int | None] = mapped_column()
    without_self_employment: Mapped[int | None] = mapped_column()


class CensusInvestmentIncome(CensusBase):
    """B19054 - Interest, Dividends, or Net Rental Income.

    Capital income flag: households receiving investment income
    represent the bourgeoisie (owners of capital).
    """

    __tablename__ = "census_investment_income"

    county_id: Mapped[int] = mapped_column(ForeignKey("census_counties.id"), primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("census_data_sources.id"), primary_key=True)
    # B19054_001E = Total, B19054_002E = With investment, B19054_003E = Without
    total_households: Mapped[int | None] = mapped_column()
    with_investment_income: Mapped[int | None] = mapped_column()
    without_investment_income: Mapped[int | None] = mapped_column()


# =============================================================================
# METADATA TABLE
# =============================================================================


class CensusColumnMetadata(CensusBase):
    """Column definitions from Census API variable metadata."""

    __tablename__ = "census_column_metadata"

    table_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    column_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    column_label: Mapped[str | None] = mapped_column(Text)


# Export all models
__all__ = [
    # Dimension tables
    "CensusCounty",
    "CensusMetroArea",  # Backwards compatibility alias
    "CensusDataSource",
    # Original fact tables (8)
    "CensusMedianIncome",
    "CensusIncomeDistribution",
    "CensusEmploymentStatus",
    "CensusWorkerClass",
    "CensusHousingTenure",
    "CensusMedianRent",
    "CensusRentBurden",
    "CensusOccupation",
    # Marxian analysis fact tables (8 new)
    "CensusHoursWorked",
    "CensusPoverty",
    "CensusEducation",
    "CensusGini",
    "CensusCommute",
    "CensusWageIncome",
    "CensusSelfEmployment",
    "CensusInvestmentIncome",
    # Metadata
    "CensusColumnMetadata",
]
