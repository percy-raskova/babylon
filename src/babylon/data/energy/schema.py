"""EIA Monthly Energy Review SQLAlchemy schema.

Defines ORM models for EIA energy production, consumption, prices, and emissions
data for metabolic rift analysis in Babylon simulation.

All tables are stored in the unified research.sqlite database alongside
Census, QCEW, FRED, Trade, and Productivity data.

Tables:
    energy_tables: Dimension table for EIA table metadata (grouped series)
    energy_series: Dimension table for individual time series
    energy_annual: Fact table for annual observations (1949-2024)

Join keys:
    year: For temporal joins with Census, QCEW, FRED data

Marxian interpretations:
    Production series measure metabolic throughput - extraction from biosphere.
    Import series measure imperial energy dependency on periphery.
    Emissions series measure metabolic rift accumulation (waste externality).
"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from babylon.data.census.database import CensusBase


class EnergyTable(CensusBase):
    """Dimension table for EIA MER table metadata.

    Groups related energy series by their source table in the Monthly
    Energy Review. Each table covers a specific domain (overview,
    sector consumption, prices, emissions, etc.).

    Attributes:
        id: Auto-incrementing primary key.
        table_code: EIA table identifier (e.g., "01.01", "09.01", "11.01").
        title: Human-readable table title.
        category: Analytical category for grouping.
        marxian_interpretation: How this data relates to metabolic rift theory.
    """

    __tablename__ = "energy_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    marxian_interpretation: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationship to series
    series: Mapped[list["EnergySeries"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_energy_table_category", "category"),)


class EnergySeries(CensusBase):
    """Dimension table for EIA time series metadata.

    Each series represents a single column from an EIA MER table,
    such as "Total Fossil Fuels Production" or "Crude Oil Price".

    Attributes:
        id: Auto-incrementing primary key.
        table_id: Foreign key to energy_tables.
        series_name: Full series name from EIA column header.
        series_code: Short identifier for the series (derived from name).
        units: Measurement units (e.g., "Quadrillion Btu", "Dollars per Barrel").
        column_index: Position in source Excel file (1-based after Year column).
    """

    __tablename__ = "energy_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("energy_tables.id"), nullable=False)
    series_name: Mapped[str] = mapped_column(String(300), nullable=False)
    series_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    units: Mapped[str] = mapped_column(String(100), nullable=False)
    column_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationship to table and observations
    table: Mapped["EnergyTable"] = relationship(back_populates="series")
    observations: Mapped[list["EnergyAnnual"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("table_id", "series_name", name="uq_energy_series_table_name"),
        Index("idx_energy_series_table", "table_id"),
    )


class EnergyAnnual(CensusBase):
    """Fact table for annual energy observations.

    Stores annual values for each energy series from EIA MER.
    Time range spans 1949-2024 (76 years) for most series.

    Primary analytical uses:
        1. Track metabolic throughput (production by source)
        2. Measure imperial energy dependency (imports vs domestic)
        3. Quantify metabolic rift accumulation (CO2 emissions)
        4. Model energy transition dynamics (fossil vs renewable)

    Attributes:
        id: Auto-incrementing primary key.
        series_id: Foreign key to energy_series.
        year: Calendar year (1949-2024).
        value: Numeric observation value (nullable for "Not Available").
    """

    __tablename__ = "energy_annual"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("energy_series.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship to series
    series: Mapped["EnergySeries"] = relationship(back_populates="observations")

    __table_args__ = (
        UniqueConstraint("series_id", "year", name="uq_energy_annual_series_year"),
        Index("idx_energy_annual_year", "year"),
        Index("idx_energy_annual_series_year", "series_id", "year"),
    )


# Priority EIA tables configuration
# Maps table codes to metadata for parser
EIA_PRIORITY_TABLES: dict[str, dict[str, str]] = {
    # Overview (Table 01.*)
    "01.01": {
        "title": "Primary Energy Overview",
        "category": "overview",
        "marxian": "Total metabolic throughput - society's energy metabolism",
    },
    "01.02": {
        "title": "Primary Energy Production by Source",
        "category": "overview",
        "marxian": "Extraction rate from biosphere by energy type",
    },
    "01.03": {
        "title": "Primary Energy Consumption by Source",
        "category": "overview",
        "marxian": "Social metabolism - energy consumed by society",
    },
    "01.04a": {
        "title": "Primary Energy Imports by Source",
        "category": "overview",
        "marxian": "Imperial energy dependency on periphery extraction",
    },
    "01.04b": {
        "title": "Primary Energy Exports by Source",
        "category": "overview",
        "marxian": "Energy exported to periphery (often refined products)",
    },
    # Sector consumption (Table 02.*)
    "02.01a": {
        "title": "Residential Sector Energy Consumption",
        "category": "sector",
        "marxian": "Labor reproduction energy - household metabolism",
    },
    "02.01b": {
        "title": "Commercial Sector Energy Consumption",
        "category": "sector",
        "marxian": "Circulation sphere energy - commerce and services",
    },
    "02.02": {
        "title": "Industrial Sector Energy Consumption",
        "category": "sector",
        "marxian": "Production sphere energy - value creation metabolism",
    },
    "02.05": {
        "title": "Transportation Sector Energy Consumption",
        "category": "sector",
        "marxian": "Circulation metabolism - commodity and labor mobility",
    },
    "02.06": {
        "title": "Electric Power Sector Energy Consumption",
        "category": "sector",
        "marxian": "Energy transformation - primary to secondary conversion",
    },
    # Petroleum (Table 03.*)
    "03.01": {
        "title": "Petroleum Overview",
        "category": "petroleum",
        "marxian": "Fossil capital - accumulated dead labor from geological time",
    },
    "03.05": {
        "title": "Crude Oil Production",
        "category": "petroleum",
        "marxian": "Domestic extraction capacity - strategic autonomy metric",
    },
    # Natural gas (Table 04.*)
    "04.01": {
        "title": "Natural Gas Overview",
        "category": "natural_gas",
        "marxian": "Transition fuel - bridge between coal and renewables",
    },
    # Prices (Table 09.*)
    "09.01": {
        "title": "Crude Oil Price Summary",
        "category": "prices",
        "marxian": "Ground rent - oil as monopolizable natural resource",
    },
    "09.04": {
        "title": "Motor Gasoline Retail Prices",
        "category": "prices",
        "marxian": "Labor reproduction cost component - transport to work",
    },
    "09.08": {
        "title": "Natural Gas Prices",
        "category": "prices",
        "marxian": "Industrial input cost - affects organic composition",
    },
    "09.10": {
        "title": "Electricity End-Use Prices",
        "category": "prices",
        "marxian": "Universal energy carrier price - affects all production",
    },
    # Emissions (Table 11.*)
    "11.01": {
        "title": "CO2 Emissions from Energy Consumption",
        "category": "emissions",
        "marxian": "Metabolic rift accumulation - waste externality to biosphere",
    },
    "11.02": {
        "title": "CO2 Emissions by Sector",
        "category": "emissions",
        "marxian": "Sectoral contribution to metabolic rift",
    },
    "11.05": {
        "title": "CO2 Emissions by Fuel Type",
        "category": "emissions",
        "marxian": "Fuel-specific metabolic rift intensity",
    },
}
