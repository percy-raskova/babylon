"""ETL pipeline from research.sqlite to marxist-data-3NF.sqlite.

Extracts, transforms, and loads data from the denormalized research database
into the properly normalized 3NF schema with Marxian classifications.

Usage:
    from babylon.data.normalize.etl import run_etl
    stats = run_etl(reset=True)
    print(stats)
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from babylon.data.normalize.classifications import (
    classify_class_composition,
    classify_labor_type,
    classify_marxian_class,
    classify_ownership,
    classify_rent_burden,
    classify_world_system_tier,
    get_sector_code,
)
from babylon.data.normalize.database import (
    NormalizedBase,
    get_normalized_engine,
    get_source_engine,
)
from babylon.data.normalize.schema import (
    # Dimensions
    DimAssetCategory,
    DimCommodity,
    DimCommodityMetric,
    DimCommuteMode,
    DimCountry,
    DimCounty,
    DimDataSource,
    DimEducationLevel,
    DimEmploymentStatus,
    DimEnergySeries,
    DimEnergyTable,
    DimFredSeries,
    DimGender,
    DimHousingTenure,
    DimImportSource,
    DimIncomeBracket,
    DimIndustry,
    DimMetroArea,
    DimOccupation,
    DimOwnership,
    DimPovertyCategory,
    DimRentBurden,
    DimSector,
    DimState,
    DimTime,
    DimWealthClass,
    DimWorkerClass,
    # Facts
    FactCensusCommute,
    FactCensusEducation,
    FactCensusEmployment,
    FactCensusGini,
    FactCensusHours,
    FactCensusHousing,
    FactCensusIncome,
    FactCensusIncomeSources,
    FactCensusMedianIncome,
    FactCensusOccupation,
    FactCensusPoverty,
    FactCensusRent,
    FactCensusRentBurden,
    FactCensusWorkerClass,
    FactCommodityObservation,
    FactEnergyAnnual,
    FactFredIndustryUnemployment,
    FactFredNational,
    FactFredStateUnemployment,
    FactFredWealthLevels,
    FactFredWealthShares,
    FactMineralEmployment,
    FactMineralProduction,
    FactProductivityAnnual,
    FactQcewAnnual,
    FactStateMinerals,
    FactTradeMonthly,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)


@dataclass
class ETLStats:
    """Statistics from ETL run."""

    dimensions_loaded: dict[str, int] = field(default_factory=dict)
    facts_loaded: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def total_dimensions(self) -> int:
        return sum(self.dimensions_loaded.values())

    @property
    def total_facts(self) -> int:
        return sum(self.facts_loaded.values())

    def __str__(self) -> str:
        lines = ["ETL Statistics:"]
        lines.append(
            f"  Dimensions: {self.total_dimensions} rows in {len(self.dimensions_loaded)} tables"
        )
        for table, count in sorted(self.dimensions_loaded.items()):
            lines.append(f"    {table}: {count}")
        lines.append(f"  Facts: {self.total_facts} rows in {len(self.facts_loaded)} tables")
        for table, count in sorted(self.facts_loaded.items()):
            lines.append(f"    {table}: {count}")
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
            for error in self.errors[:5]:
                lines.append(f"    - {error}")
        return "\n".join(lines)


# =============================================================================
# DIMENSION LOADERS
# =============================================================================


def load_dim_state(source: Engine, session: Session) -> int:
    """Load unified state dimension from multiple sources."""
    states: dict[str, dict[str, Any]] = {}

    # From census_counties
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT
                SUBSTR(fips, 1, 2) as state_fips,
                state_name
            FROM census_counties
            WHERE state_name IS NOT NULL
        """)
        )
        for row in result:
            state_fips = row[0]
            if state_fips and state_fips not in states:
                states[state_fips] = {
                    "state_fips": state_fips,
                    "state_name": row[1],
                    "state_abbrev": "",  # Will populate from fred_states if available
                }

    # From fred_states (has abbreviations)
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT fips_code, name, abbreviation
            FROM fred_states
        """)
        )
        for row in result:
            state_fips = row[0]
            if state_fips:
                if state_fips in states:
                    states[state_fips]["state_abbrev"] = row[2] or ""
                else:
                    states[state_fips] = {
                        "state_fips": state_fips,
                        "state_name": row[1],
                        "state_abbrev": row[2] or "",
                    }

    # Insert
    for i, (_fips, data) in enumerate(sorted(states.items()), 1):
        session.add(
            DimState(
                state_id=i,
                state_fips=data["state_fips"],
                state_name=data["state_name"],
                state_abbrev=data["state_abbrev"],
            )
        )

    session.commit()
    return len(states)


def load_dim_county(source: Engine, session: Session) -> int:
    """Load county dimension."""
    # Build state lookup
    state_lookup = {s.state_fips: s.state_id for s in session.query(DimState).all()}

    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, fips, state_fips, county_fips, name
            FROM census_counties
        """)
        )

        count = 0
        for row in result:
            state_id = state_lookup.get(row[2])
            if state_id:
                session.add(
                    DimCounty(
                        county_id=row[0],
                        fips=row[1],
                        state_id=state_id,
                        county_fips=row[3],
                        county_name=row[4],
                    )
                )
                count += 1

    session.commit()
    return count


def load_dim_metro_area(source: Engine, session: Session) -> int:
    """Load metro area dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, geo_id, cbsa_code, name
            FROM census_metro_areas
        """)
        )

        count = 0
        for row in result:
            # Infer area_type from geo_id or name
            area_type = "msa"
            if row[1] and row[1].startswith("330"):
                area_type = "csa"

            session.add(
                DimMetroArea(
                    metro_area_id=row[0],
                    geo_id=row[1],
                    cbsa_code=row[2],
                    metro_name=row[3],
                    area_type=area_type,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_country(source: Engine, session: Session) -> int:
    """Load country dimension with world system tier classification."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, cty_code, name, is_region
            FROM trade_countries
        """)
        )

        count = 0
        for row in result:
            tier = classify_world_system_tier(row[2]) if not row[3] else None
            session.add(
                DimCountry(
                    country_id=row[0],
                    cty_code=row[1],
                    country_name=row[2],
                    is_region=bool(row[3]),
                    world_system_tier=tier,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_import_source(source: Engine, session: Session) -> int:
    """Load import source dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, country, commodity_count, map_class
            FROM import_sources
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimImportSource(
                    import_source_id=row[0],
                    country=row[1],
                    commodity_count=row[2],
                    map_class=row[3],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_industry(source: Engine, session: Session) -> int:
    """Load unified industry dimension from QCEW + Productivity + FRED."""
    industries: dict[str, dict[str, Any]] = {}

    # From qcew_industries
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT industry_code, industry_title, naics_level, parent_code
            FROM qcew_industries
        """)
        )
        for row in result:
            code = row[0]
            if code not in industries:
                industries[code] = {
                    "naics_code": code,
                    "industry_title": row[1],
                    "naics_level": row[2] or 0,
                    "parent_naics_code": row[3],
                    "has_qcew_data": True,
                    "has_productivity_data": False,
                    "has_fred_data": False,
                }

    # From productivity_industries
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT naics_code, industry_title, digit_level
            FROM productivity_industries
        """)
        )
        for row in result:
            code = row[0]
            # Extract digit level as integer
            level_str = row[2] or ""
            level = 0
            if "3-Digit" in level_str:
                level = 3
            elif "4-Digit" in level_str:
                level = 4
            elif "5-Digit" in level_str:
                level = 5
            elif "6-Digit" in level_str:
                level = 6

            if code in industries:
                industries[code]["has_productivity_data"] = True
            else:
                industries[code] = {
                    "naics_code": code,
                    "industry_title": row[1],
                    "naics_level": level,
                    "parent_naics_code": None,
                    "has_qcew_data": False,
                    "has_productivity_data": True,
                    "has_fred_data": False,
                }

    # From fred_industries
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT lnu_code, name, naics_sector
            FROM fred_industries
        """)
        )
        for row in result:
            code = row[0]
            if code in industries:
                industries[code]["has_fred_data"] = True
            else:
                industries[code] = {
                    "naics_code": code,
                    "industry_title": row[1],
                    "naics_level": 2,  # FRED uses sector level
                    "parent_naics_code": None,
                    "has_qcew_data": False,
                    "has_productivity_data": False,
                    "has_fred_data": True,
                }

    # Insert with classifications
    for i, (_code, data) in enumerate(sorted(industries.items()), 1):
        session.add(
            DimIndustry(
                industry_id=i,
                naics_code=data["naics_code"],
                industry_title=data["industry_title"],
                naics_level=data["naics_level"],
                parent_naics_code=data["parent_naics_code"],
                sector_code=get_sector_code(data["naics_code"]),
                class_composition=classify_class_composition(
                    data["naics_code"], data["industry_title"]
                ),
                has_productivity_data=data["has_productivity_data"],
                has_fred_data=data["has_fred_data"],
                has_qcew_data=data["has_qcew_data"],
            )
        )

    session.commit()
    return len(industries)


def load_dim_sector(_source: Engine, session: Session) -> int:
    """Load sector dimension from industries."""
    # Derive from loaded industries
    sectors: dict[str, str] = {}
    for ind in session.query(DimIndustry).filter(DimIndustry.sector_code.isnot(None)).all():
        if ind.sector_code and ind.sector_code not in sectors:
            sectors[ind.sector_code] = ind.industry_title

    for i, (code, name) in enumerate(sorted(sectors.items()), 1):
        session.add(
            DimSector(
                sector_id=i,
                sector_code=code,
                sector_name=name[:100],
                class_composition=classify_class_composition(code) or "service_producing",
            )
        )

    session.commit()
    return len(sectors)


def load_dim_ownership(source: Engine, session: Session) -> int:
    """Load ownership dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, own_code, own_title
            FROM qcew_ownership
        """)
        )

        count = 0
        for row in result:
            is_gov, is_priv = classify_ownership(row[1])
            session.add(
                DimOwnership(
                    ownership_id=row[0],
                    own_code=row[1],
                    own_title=row[2],
                    is_government=is_gov,
                    is_private=is_priv,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_income_bracket(source: Engine, session: Session) -> int:
    """Load income bracket dimension from census_income_distribution."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT bracket_code, bracket_label
            FROM census_income_distribution
            ORDER BY bracket_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            # Parse bracket bounds from label
            label = row[1] or ""
            min_usd = None
            max_usd = None

            # Example: "Less than $10,000" -> max=10000
            # Example: "$10,000 to $14,999" -> min=10000, max=14999
            # Example: "$200,000 or more" -> min=200000
            if "Less than" in label:
                with contextlib.suppress(ValueError):
                    max_usd = int(
                        label.replace("Less than", "").replace("$", "").replace(",", "").strip()
                    )
            elif " to " in label:
                with contextlib.suppress(ValueError, IndexError):
                    parts = label.replace("$", "").replace(",", "").split(" to ")
                    min_usd = int(parts[0].strip())
                    max_usd = int(parts[1].strip())
            elif "or more" in label:
                with contextlib.suppress(ValueError):
                    min_usd = int(
                        label.replace("or more", "").replace("$", "").replace(",", "").strip()
                    )

            session.add(
                DimIncomeBracket(
                    bracket_id=i,
                    bracket_code=row[0],
                    bracket_label=label,
                    bracket_min_usd=min_usd,
                    bracket_max_usd=max_usd,
                    bracket_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_employment_status(source: Engine, session: Session) -> int:
    """Load employment status dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT category_code, category_label
            FROM census_employment_status
            ORDER BY category_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            label = row[1] or ""
            is_labor_force = None
            is_employed = None

            if "In labor force" in label:
                is_labor_force = True
            elif "Not in labor force" in label:
                is_labor_force = False

            if "Employed" in label:
                is_employed = True
            elif "Unemployed" in label:
                is_employed = False

            session.add(
                DimEmploymentStatus(
                    status_id=i,
                    status_code=row[0],
                    status_label=label,
                    is_labor_force=is_labor_force,
                    is_employed=is_employed,
                    status_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_worker_class(source: Engine, session: Session) -> int:
    """Load worker class dimension with Marxian classification."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT class_code, class_label
            FROM census_worker_class
            ORDER BY class_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            session.add(
                DimWorkerClass(
                    class_id=i,
                    class_code=row[0],
                    class_label=row[1] or "",
                    marxian_class=classify_marxian_class(row[0], row[1] or ""),
                    class_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_occupation(source: Engine, session: Session) -> int:
    """Load occupation dimension with labor type classification."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT occupation_code, occupation_label, occupation_category
            FROM census_occupation
            ORDER BY occupation_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            session.add(
                DimOccupation(
                    occupation_id=i,
                    occupation_code=row[0],
                    occupation_label=row[1] or "",
                    occupation_category=row[2],
                    labor_type=classify_labor_type(row[2]),
                    occupation_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_education_level(source: Engine, session: Session) -> int:
    """Load education level dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT level_code, level_label
            FROM census_education
            ORDER BY level_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            session.add(
                DimEducationLevel(
                    level_id=i,
                    level_code=row[0],
                    level_label=row[1] or "",
                    years_of_schooling=None,  # Would need manual mapping
                    level_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_housing_tenure(session: Session) -> int:
    """Load housing tenure dimension (generated)."""
    tenures = [
        (1, "owner", "Owner-occupied", True),
        (2, "renter", "Renter-occupied", False),
    ]

    for tenure_id, tenure_type, tenure_label, is_owner in tenures:
        session.add(
            DimHousingTenure(
                tenure_id=tenure_id,
                tenure_type=tenure_type,
                tenure_label=tenure_label,
                is_owner=is_owner,
            )
        )

    session.commit()
    return len(tenures)


def load_dim_rent_burden(source: Engine, session: Session) -> int:
    """Load rent burden dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT bracket_code, burden_bracket
            FROM census_rent_burden
            ORDER BY bracket_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            is_cost_burdened, is_severely_burdened = classify_rent_burden(row[1] or "")
            session.add(
                DimRentBurden(
                    burden_id=i,
                    bracket_code=row[0],
                    burden_bracket=row[1] or "",
                    burden_min_pct=None,  # Would need parsing
                    burden_max_pct=None,
                    is_cost_burdened=is_cost_burdened,
                    is_severely_burdened=is_severely_burdened,
                    bracket_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_commute_mode(source: Engine, session: Session) -> int:
    """Load commute mode dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT mode_code, mode_label
            FROM census_commute
            ORDER BY mode_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            label = (row[1] or "").lower()
            is_public = any(x in label for x in ["bus", "subway", "rail", "ferry", "transit"])
            is_active = any(x in label for x in ["walk", "bicycle", "bike"])

            session.add(
                DimCommuteMode(
                    mode_id=i,
                    mode_code=row[0],
                    mode_label=row[1] or "",
                    is_public_transit=is_public if is_public else None,
                    is_active_transport=is_active if is_active else None,
                    mode_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_poverty_category(source: Engine, session: Session) -> int:
    """Load poverty category dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT DISTINCT category_code, category_label
            FROM census_poverty
            ORDER BY category_code
        """)
        )

        count = 0
        for i, row in enumerate(result, 1):
            label = (row[1] or "").lower()
            is_below = "below" in label or "under" in label

            session.add(
                DimPovertyCategory(
                    category_id=i,
                    category_code=row[0],
                    category_label=row[1] or "",
                    is_below_poverty=is_below if "poverty" in label else None,
                    category_order=i,
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_energy_table(source: Engine, session: Session) -> int:
    """Load energy table dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, table_code, title, category, marxian_interpretation
            FROM energy_tables
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimEnergyTable(
                    table_id=row[0],
                    table_code=row[1],
                    title=row[2],
                    category=row[3],
                    marxian_interpretation=row[4],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_energy_series(source: Engine, session: Session) -> int:
    """Load energy series dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, table_id, series_code, series_name, units, column_index
            FROM energy_series
        """)
        )

        count = 0
        for row in result:
            # Generate series_code if source is empty/null
            series_code = row[2]
            if not series_code:
                # Use table_id and series_id to create synthetic code
                series_code = f"EIA_T{row[1]}_S{row[0]}"

            session.add(
                DimEnergySeries(
                    series_id=row[0],
                    table_id=row[1],
                    series_code=series_code,
                    series_name=row[3],
                    units=row[4],
                    column_index=row[5],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_wealth_class(source: Engine, session: Session) -> int:
    """Load FRED wealth class dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, percentile_code, percentile_label, babylon_class
            FROM fred_wealth_classes
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimWealthClass(
                    wealth_class_id=row[0],
                    percentile_code=row[1],
                    percentile_label=row[2],
                    babylon_class=row[3],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_asset_category(source: Engine, session: Session) -> int:
    """Load FRED asset category dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, category_code, category_label, marxian_interpretation
            FROM fred_asset_categories
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimAssetCategory(
                    category_id=row[0],
                    category_code=row[1],
                    category_label=row[2],
                    marxian_interpretation=row[3],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_fred_series(source: Engine, session: Session) -> int:
    """Load FRED series dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, series_id, title, units, frequency, seasonal_adjustment, source
            FROM fred_series
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimFredSeries(
                    series_id=row[0],
                    series_code=row[1] or f"SERIES_{row[0]}",
                    title=row[2],
                    units=row[3],
                    frequency=row[4],
                    seasonal_adjustment=row[5],
                    source=row[6],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_commodity(source: Engine, session: Session) -> int:
    """Load commodity dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, code, name, is_critical, primary_applications, marxian_interpretation
            FROM commodities
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimCommodity(
                    commodity_id=row[0],
                    code=row[1],
                    name=row[2],
                    is_critical=bool(row[3]) if row[3] is not None else None,
                    primary_applications=row[4],
                    marxian_interpretation=row[5],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_commodity_metric(source: Engine, session: Session) -> int:
    """Load commodity metric dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, code, name, units, category, marxian_interpretation
            FROM commodity_metrics
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimCommodityMetric(
                    metric_id=row[0],
                    code=row[1],
                    name=row[2],
                    units=row[3],
                    category=row[4],
                    marxian_interpretation=row[5],
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_gender(session: Session) -> int:
    """Load gender dimension (generated)."""
    genders = [
        (1, "Male", "Male"),
        (2, "Female", "Female"),
        (3, "Total", "Total"),
    ]

    for gender_id, code, label in genders:
        session.add(
            DimGender(
                gender_id=gender_id,
                gender_code=code,
                gender_label=label,
            )
        )

    session.commit()
    return len(genders)


def load_dim_data_source(source: Engine, session: Session) -> int:
    """Load data source dimension."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, variant, year, description
            FROM census_data_sources
        """)
        )

        count = 0
        for row in result:
            session.add(
                DimDataSource(
                    source_id=row[0],
                    source_code=row[1] or f"SOURCE_{row[0]}",
                    source_name=row[3] or row[1] or "",
                    source_year=row[2],
                    source_agency="Census Bureau",
                )
            )
            count += 1

    session.commit()
    return count


def load_dim_time(source: Engine, session: Session) -> int:
    """Load time dimension from all fact tables."""
    times: dict[tuple[int, int | None], dict[str, Any]] = {}

    # Collect unique year/month combinations from various sources
    queries = [
        "SELECT DISTINCT year, NULL as month FROM qcew_annual",
        "SELECT DISTINCT year, NULL as month FROM productivity_annual",
        "SELECT DISTINCT year, month FROM trade_monthly",
        "SELECT DISTINCT year, NULL as month FROM energy_annual",
        "SELECT DISTINCT year, NULL as month FROM fred_national",
        "SELECT DISTINCT year, quarter as month FROM fred_wealth_levels",
        "SELECT DISTINCT year, NULL as month FROM commodity_observations",
        "SELECT DISTINCT year, NULL as month FROM mineral_trends",
    ]

    with source.connect() as conn:
        for query in queries:
            try:
                result = conn.execute(text(query))
                for row in result:
                    year = row[0]
                    month = row[1] if len(row) > 1 else None
                    if year:
                        key = (year, month)
                        if key not in times:
                            quarter = None
                            if month and month <= 12:
                                quarter = (month - 1) // 3 + 1
                            times[key] = {
                                "year": year,
                                "month": month if month and month <= 12 else None,
                                "quarter": quarter,
                                "is_annual": month is None or month > 12,
                            }
            except Exception as e:
                logger.warning(f"Could not query time from: {query}: {e}")

    # Sort with None-safe key (None treated as 0 for sorting)
    def sort_key(item: tuple[tuple[int, int | None], dict[str, Any]]) -> tuple[int, int]:
        key = item[0]
        return (key[0], key[1] if key[1] is not None else 0)

    for i, (_key, data) in enumerate(sorted(times.items(), key=sort_key), 1):
        session.add(
            DimTime(
                time_id=i,
                year=data["year"],
                month=data["month"],
                quarter=data["quarter"],
                is_annual=data["is_annual"],
            )
        )

    session.commit()
    return len(times)


# =============================================================================
# FACT LOADERS
# =============================================================================


def build_lookups(session: Session) -> dict[str, Any]:
    """Build lookup dictionaries for FK resolution."""
    return {
        "county": {c.fips: c.county_id for c in session.query(DimCounty).all()},
        "state": {s.state_fips: s.state_id for s in session.query(DimState).all()},
        "industry": {i.naics_code: i.industry_id for i in session.query(DimIndustry).all()},
        "ownership": {o.own_code: o.ownership_id for o in session.query(DimOwnership).all()},
        "country": {c.cty_code: c.country_id for c in session.query(DimCountry).all()},
        "time": {(t.year, t.month): t.time_id for t in session.query(DimTime).all()},
        "income_bracket": {
            b.bracket_code: b.bracket_id for b in session.query(DimIncomeBracket).all()
        },
        "employment_status": {
            s.status_code: s.status_id for s in session.query(DimEmploymentStatus).all()
        },
        "worker_class": {c.class_code: c.class_id for c in session.query(DimWorkerClass).all()},
        "occupation": {
            o.occupation_code: o.occupation_id for o in session.query(DimOccupation).all()
        },
        "education_level": {
            e.level_code: e.level_id for e in session.query(DimEducationLevel).all()
        },
        "housing_tenure": {"owner": 1, "renter": 2},
        "rent_burden": {b.bracket_code: b.burden_id for b in session.query(DimRentBurden).all()},
        "commute_mode": {m.mode_code: m.mode_id for m in session.query(DimCommuteMode).all()},
        "poverty_category": {
            c.category_code: c.category_id for c in session.query(DimPovertyCategory).all()
        },
        "gender": {"Male": 1, "Female": 2, "Total": 3},
        "energy_series": {s.series_id: s.series_id for s in session.query(DimEnergySeries).all()},
        "fred_series": {s.series_id: s.series_id for s in session.query(DimFredSeries).all()},
        "wealth_class": {
            w.wealth_class_id: w.wealth_class_id for w in session.query(DimWealthClass).all()
        },
        "asset_category": {
            c.category_id: c.category_id for c in session.query(DimAssetCategory).all()
        },
        "commodity": {c.commodity_id: c.commodity_id for c in session.query(DimCommodity).all()},
        "commodity_metric": {
            m.metric_id: m.metric_id for m in session.query(DimCommodityMetric).all()
        },
    }


def load_fact_census_income(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census income distribution facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, bracket_code, estimate
            FROM census_income_distribution
        """)
        )

        count = 0
        batch = []
        for row in result:
            bracket_id = lookups["income_bracket"].get(row[2])
            if bracket_id:
                batch.append(
                    FactCensusIncome(
                        county_id=row[0],
                        source_id=row[1],
                        bracket_id=bracket_id,
                        household_count=row[3],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_median_income(
    source: Engine, session: Session, _lookups: dict[str, Any]
) -> int:
    """Load census median income facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, estimate
            FROM census_median_income
        """)
        )

        count = 0
        for row in result:
            session.add(
                FactCensusMedianIncome(
                    county_id=row[0],
                    source_id=row[1],
                    median_income_usd=Decimal(str(row[2])) if row[2] else Decimal("0"),
                )
            )
            count += 1

    session.commit()
    return count


def load_fact_trade_monthly(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load trade monthly facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT country_id, year, month, imports_usd_millions, exports_usd_millions
            FROM trade_monthly
        """)
        )

        count = 0
        batch = []
        for row in result:
            time_id = lookups["time"].get((row[1], row[2]))
            if time_id:
                batch.append(
                    FactTradeMonthly(
                        country_id=row[0],
                        time_id=time_id,
                        imports_usd_millions=Decimal(str(row[3])) if row[3] else None,
                        exports_usd_millions=Decimal(str(row[4])) if row[4] else None,
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_employment(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census employment status facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, category_code, estimate
            FROM census_employment_status
        """)
        )

        count = 0
        batch = []
        for row in result:
            status_id = lookups["employment_status"].get(row[2])
            if status_id:
                batch.append(
                    FactCensusEmployment(
                        county_id=row[0],
                        source_id=row[1],
                        status_id=status_id,
                        population_count=row[3],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_worker_class(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census worker class facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, gender, class_code, estimate
            FROM census_worker_class
        """)
        )

        count = 0
        batch = []
        for row in result:
            class_id = lookups["worker_class"].get(row[3])
            gender_id = lookups["gender"].get(row[2])
            if class_id and gender_id:
                batch.append(
                    FactCensusWorkerClass(
                        county_id=row[0],
                        source_id=row[1],
                        gender_id=gender_id,
                        class_id=class_id,
                        worker_count=row[4],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_occupation(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census occupation facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, gender, occupation_code, estimate
            FROM census_occupation
        """)
        )

        count = 0
        batch = []
        for row in result:
            occupation_id = lookups["occupation"].get(row[3])
            gender_id = lookups["gender"].get(row[2])
            if occupation_id and gender_id:
                batch.append(
                    FactCensusOccupation(
                        county_id=row[0],
                        source_id=row[1],
                        gender_id=gender_id,
                        occupation_id=occupation_id,
                        worker_count=row[4],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_hours(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census hours worked facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, gender, aggregate_hours, mean_hours
            FROM census_hours_worked
        """)
        )

        count = 0
        for row in result:
            gender_id = lookups["gender"].get(row[2])
            if gender_id:
                session.add(
                    FactCensusHours(
                        county_id=row[0],
                        source_id=row[1],
                        gender_id=gender_id,
                        aggregate_hours=Decimal(str(row[3])) if row[3] else None,
                        mean_hours=Decimal(str(row[4])) if row[4] else None,
                    )
                )
                count += 1

    session.commit()
    return count


def load_fact_census_housing(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census housing tenure facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, tenure_type, estimate
            FROM census_housing_tenure
        """)
        )

        count = 0
        for row in result:
            tenure_id = lookups["housing_tenure"].get(row[2])
            if tenure_id:
                session.add(
                    FactCensusHousing(
                        county_id=row[0],
                        source_id=row[1],
                        tenure_id=tenure_id,
                        household_count=row[3],
                    )
                )
                count += 1

    session.commit()
    return count


def load_fact_census_rent(source: Engine, session: Session, _lookups: dict[str, Any]) -> int:
    """Load census median rent facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, estimate
            FROM census_median_rent
        """)
        )

        count = 0
        for row in result:
            session.add(
                FactCensusRent(
                    county_id=row[0],
                    source_id=row[1],
                    median_rent_usd=Decimal(str(row[2])) if row[2] else Decimal("0"),
                )
            )
            count += 1

    session.commit()
    return count


def load_fact_census_rent_burden(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census rent burden facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, bracket_code, estimate
            FROM census_rent_burden
        """)
        )

        count = 0
        batch = []
        for row in result:
            burden_id = lookups["rent_burden"].get(row[2])
            if burden_id:
                batch.append(
                    FactCensusRentBurden(
                        county_id=row[0],
                        source_id=row[1],
                        burden_id=burden_id,
                        household_count=row[3],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_education(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census education facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, level_code, estimate
            FROM census_education
        """)
        )

        count = 0
        batch = []
        for row in result:
            level_id = lookups["education_level"].get(row[2])
            if level_id:
                batch.append(
                    FactCensusEducation(
                        county_id=row[0],
                        source_id=row[1],
                        level_id=level_id,
                        population_count=row[3],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_gini(source: Engine, session: Session, _lookups: dict[str, Any]) -> int:
    """Load census gini facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, gini_index
            FROM census_gini
        """)
        )

        count = 0
        for row in result:
            session.add(
                FactCensusGini(
                    county_id=row[0],
                    source_id=row[1],
                    gini_index=Decimal(str(row[2])) if row[2] else None,
                )
            )
            count += 1

    session.commit()
    return count


def load_fact_census_commute(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census commute facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, mode_code, estimate
            FROM census_commute
        """)
        )

        count = 0
        batch = []
        for row in result:
            mode_id = lookups["commute_mode"].get(row[2])
            if mode_id:
                batch.append(
                    FactCensusCommute(
                        county_id=row[0],
                        source_id=row[1],
                        mode_id=mode_id,
                        worker_count=row[3],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_poverty(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load census poverty facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT county_id, source_id, category_code, estimate
            FROM census_poverty
        """)
        )

        count = 0
        batch = []
        for row in result:
            category_id = lookups["poverty_category"].get(row[2])
            if category_id:
                batch.append(
                    FactCensusPoverty(
                        county_id=row[0],
                        source_id=row[1],
                        category_id=category_id,
                        population_count=row[3],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_census_income_sources(
    source: Engine, session: Session, _lookups: dict[str, Any]
) -> int:
    """Load combined census income sources facts (wage, self-employment, investment)."""
    # Join the three income source tables
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT
                w.county_id,
                w.source_id,
                w.with_wages,
                COALESCE(s.with_self_employment, 0) as with_self_employment,
                COALESCE(i.with_investment_income, 0) as with_investment
            FROM census_wage_income w
            LEFT JOIN census_self_employment s
                ON w.county_id = s.county_id AND w.source_id = s.source_id
            LEFT JOIN census_investment_income i
                ON w.county_id = i.county_id AND w.source_id = i.source_id
        """)
        )

        count = 0
        for row in result:
            session.add(
                FactCensusIncomeSources(
                    county_id=row[0],
                    source_id=row[1],
                    with_wages=row[2],
                    with_self_employment=row[3],
                    with_investment=row[4],
                )
            )
            count += 1

    session.commit()
    return count


def load_fact_qcew_annual(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load QCEW annual facts."""
    # Need to map area_id to county_id via area_fips
    area_to_county: dict[int, int] = {}
    with source.connect() as conn:
        # First get area_fips mapping
        result = conn.execute(
            text("""
            SELECT a.id, a.area_fips
            FROM qcew_areas a
            WHERE a.area_type = 'county'
        """)
        )
        area_fips_map = {row[0]: row[1] for row in result}

    # Map to our county lookup
    for area_id, fips in area_fips_map.items():
        county_id = lookups["county"].get(fips)
        if county_id:
            area_to_county[area_id] = county_id

    # Map industry codes to our industry IDs
    industry_code_map: dict[int, str] = {}
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, industry_code FROM qcew_industries
        """)
        )
        industry_code_map = {row[0]: row[1] for row in result}

    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT
                area_id, industry_id, ownership_id, year,
                establishments, employment, total_wages,
                avg_weekly_wage, avg_annual_pay,
                lq_employment, lq_avg_annual_pay,
                oty_employment_chg, oty_employment_pct,
                disclosure_code
            FROM qcew_annual
        """)
        )

        count = 0
        batch = []
        for row in result:
            county_id = area_to_county.get(row[0])
            ind_code = industry_code_map.get(row[1])
            industry_id = lookups["industry"].get(ind_code) if ind_code else None
            time_id = lookups["time"].get((row[3], None))

            if county_id and industry_id and time_id:
                batch.append(
                    FactQcewAnnual(
                        county_id=county_id,
                        industry_id=industry_id,
                        ownership_id=row[2],
                        time_id=time_id,
                        establishments=row[4],
                        employment=row[5],
                        total_wages_usd=Decimal(str(row[6])) if row[6] else None,
                        avg_weekly_wage_usd=row[7],
                        avg_annual_pay_usd=row[8],
                        lq_employment=Decimal(str(row[9])) if row[9] else None,
                        lq_annual_pay=Decimal(str(row[10])) if row[10] else None,
                        disclosure_code=row[13],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_productivity_annual(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load productivity annual facts."""
    # Map productivity industry IDs to our unified industry dimension
    prod_industry_map: dict[int, str] = {}
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, naics_code FROM productivity_industries
        """)
        )
        prod_industry_map = {row[0]: row[1] for row in result}

    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT
                industry_id, year,
                labor_productivity_index, labor_productivity_pct_chg,
                hours_worked_index, hours_worked_millions,
                employment_thousands, hourly_compensation_index,
                unit_labor_costs_index, real_output_index,
                sectoral_output_index, labor_compensation_millions,
                sectoral_output_millions
            FROM productivity_annual
        """)
        )

        count = 0
        for row in result:
            naics_code = prod_industry_map.get(row[0])
            industry_id = lookups["industry"].get(naics_code) if naics_code else None
            time_id = lookups["time"].get((row[1], None))

            if industry_id and time_id:
                session.add(
                    FactProductivityAnnual(
                        industry_id=industry_id,
                        time_id=time_id,
                        labor_productivity_index=Decimal(str(row[2])) if row[2] else None,
                        labor_productivity_pct_chg=Decimal(str(row[3])) if row[3] else None,
                        hours_worked_index=Decimal(str(row[4])) if row[4] else None,
                        hours_worked_millions=Decimal(str(row[5])) if row[5] else None,
                        employment_thousands=Decimal(str(row[6])) if row[6] else None,
                        hourly_compensation_index=Decimal(str(row[7])) if row[7] else None,
                        unit_labor_costs_index=Decimal(str(row[8])) if row[8] else None,
                        real_output_index=Decimal(str(row[9])) if row[9] else None,
                        sectoral_output_index=Decimal(str(row[10])) if row[10] else None,
                        labor_compensation_millions_usd=Decimal(str(row[11])) if row[11] else None,
                        sectoral_output_millions_usd=Decimal(str(row[12])) if row[12] else None,
                    )
                )
                count += 1

    session.commit()
    return count


def load_fact_energy_annual(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load energy annual facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT series_id, year, value
            FROM energy_annual
        """)
        )

        count = 0
        batch = []
        for row in result:
            time_id = lookups["time"].get((row[1], None))
            if time_id:
                batch.append(
                    FactEnergyAnnual(
                        series_id=row[0],
                        time_id=time_id,
                        value=Decimal(str(row[2])) if row[2] else None,
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_fred_national(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load FRED national facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT series_id, year, month, value
            FROM fred_national
        """)
        )

        count = 0
        batch = []
        for row in result:
            time_id = lookups["time"].get((row[1], row[2]))
            if time_id:
                batch.append(
                    FactFredNational(
                        series_id=row[0],
                        time_id=time_id,
                        value=Decimal(str(row[3])) if row[3] else None,
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_fred_wealth_levels(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load FRED wealth levels facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT wealth_class_id, asset_category_id, year, quarter, value_millions
            FROM fred_wealth_levels
        """)
        )

        count = 0
        batch = []
        for row in result:
            # Use quarter as month placeholder for time lookup
            time_id = lookups["time"].get((row[2], row[3]))
            if time_id:
                batch.append(
                    FactFredWealthLevels(
                        wealth_class_id=row[0],
                        category_id=row[1],
                        time_id=time_id,
                        value_millions=Decimal(str(row[4])) if row[4] else None,
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_fred_wealth_shares(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load FRED wealth shares facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT wealth_class_id, asset_category_id, year, quarter, share_percent
            FROM fred_wealth_shares
        """)
        )

        count = 0
        batch = []
        for row in result:
            time_id = lookups["time"].get((row[2], row[3]))
            if time_id:
                batch.append(
                    FactFredWealthShares(
                        wealth_class_id=row[0],
                        category_id=row[1],
                        time_id=time_id,
                        share_percent=Decimal(str(row[4])) if row[4] else None,
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_fred_industry_unemployment(
    source: Engine, session: Session, lookups: dict[str, Any]
) -> int:
    """Load FRED industry unemployment facts."""
    # Map FRED industry IDs to our unified industry dimension
    fred_industry_map: dict[int, str] = {}
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, lnu_code FROM fred_industries
        """)
        )
        fred_industry_map = {row[0]: row[1] for row in result}

    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT industry_id, year, month, unemployment_rate
            FROM fred_industry_unemployment
        """)
        )

        count = 0
        batch = []
        for row in result:
            lnu_code = fred_industry_map.get(row[0])
            industry_id = lookups["industry"].get(lnu_code) if lnu_code else None
            time_id = lookups["time"].get((row[1], row[2]))

            if industry_id and time_id:
                batch.append(
                    FactFredIndustryUnemployment(
                        industry_id=industry_id,
                        time_id=time_id,
                        unemployment_rate=Decimal(str(row[3])) if row[3] else None,
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_fred_state_unemployment(
    source: Engine, session: Session, lookups: dict[str, Any]
) -> int:
    """Load FRED state unemployment facts."""
    # Map FRED state IDs to our unified state dimension
    fred_state_map: dict[int, str] = {}
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, fips_code FROM fred_states
        """)
        )
        fred_state_map = {row[0]: row[1] for row in result}

    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT state_id, year, month, unemployment_rate
            FROM fred_state_unemployment
        """)
        )

        count = 0
        batch = []
        for row in result:
            fips = fred_state_map.get(row[0])
            state_id = lookups["state"].get(fips) if fips else None
            time_id = lookups["time"].get((row[1], row[2]))

            if state_id and time_id:
                batch.append(
                    FactFredStateUnemployment(
                        state_id=state_id,
                        time_id=time_id,
                        unemployment_rate=Decimal(str(row[3])) if row[3] else None,
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_commodity_observation(
    source: Engine, session: Session, lookups: dict[str, Any]
) -> int:
    """Load commodity observation facts."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT commodity_id, metric_id, year, value, value_text
            FROM commodity_observations
        """)
        )

        count = 0
        batch = []
        for row in result:
            time_id = lookups["time"].get((row[2], None))
            if time_id:
                batch.append(
                    FactCommodityObservation(
                        commodity_id=row[0],
                        metric_id=row[1],
                        time_id=time_id,
                        value=Decimal(str(row[3])) if row[3] else None,
                        value_text=row[4],
                    )
                )
                count += 1

            if len(batch) >= 10000:
                session.bulk_save_objects(batch)
                session.commit()
                batch = []

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    return count


def load_fact_state_minerals(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load state minerals facts."""
    # Map materials_states to our unified state dimension
    mat_state_map: dict[int, str] = {}
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT id, fips FROM materials_states
        """)
        )
        mat_state_map = {row[0]: row[1] for row in result}

    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT state_id, year, value_millions, rank, percent_total, principal_commodities
            FROM state_minerals
        """)
        )

        count = 0
        for row in result:
            fips = mat_state_map.get(row[0])
            state_id = lookups["state"].get(fips) if fips else None
            time_id = lookups["time"].get((row[1], None))

            if state_id and time_id:
                session.add(
                    FactStateMinerals(
                        state_id=state_id,
                        time_id=time_id,
                        value_millions_usd=Decimal(str(row[2])) if row[2] else None,
                        rank=row[3],
                        percent_total=Decimal(str(row[4])) if row[4] else None,
                        principal_commodities=row[5],
                    )
                )
                count += 1

    session.commit()
    return count


def load_fact_mineral_production(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load mineral production facts (from denormalized mineral_trends)."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT
                year,
                mine_production_metals_millions,
                mine_production_industrial_millions,
                mine_production_coal_millions
            FROM mineral_trends
        """)
        )

        count = 0
        for row in result:
            time_id = lookups["time"].get((row[0], None))
            if time_id:
                session.add(
                    FactMineralProduction(
                        time_id=time_id,
                        metals_millions_usd=Decimal(str(row[1])) if row[1] else None,
                        industrial_millions_usd=Decimal(str(row[2])) if row[2] else None,
                        coal_millions_usd=Decimal(str(row[3])) if row[3] else None,
                    )
                )
                count += 1

    session.commit()
    return count


def load_fact_mineral_employment(source: Engine, session: Session, lookups: dict[str, Any]) -> int:
    """Load mineral employment facts (from denormalized mineral_trends)."""
    with source.connect() as conn:
        result = conn.execute(
            text("""
            SELECT
                year,
                employment_coal_thousands,
                employment_nonfuel_thousands,
                employment_chemicals_thousands,
                employment_stone_clay_glass_thousands,
                employment_primary_metal_thousands,
                avg_weekly_earnings_coal,
                avg_weekly_earnings_all,
                avg_weekly_earnings_stone_clay_glass,
                avg_weekly_earnings_primary_metal
            FROM mineral_trends
        """)
        )

        count = 0
        for row in result:
            time_id = lookups["time"].get((row[0], None))
            if time_id:
                session.add(
                    FactMineralEmployment(
                        time_id=time_id,
                        coal_employment_thousands=Decimal(str(row[1])) if row[1] else None,
                        nonfuel_employment_thousands=Decimal(str(row[2])) if row[2] else None,
                        chemicals_employment_thousands=Decimal(str(row[3])) if row[3] else None,
                        stone_clay_glass_employment_thousands=Decimal(str(row[4]))
                        if row[4]
                        else None,
                        primary_metal_employment_thousands=Decimal(str(row[5])) if row[5] else None,
                        coal_avg_weekly_earnings=Decimal(str(row[6])) if row[6] else None,
                        all_avg_weekly_earnings=Decimal(str(row[7])) if row[7] else None,
                        stone_clay_glass_avg_weekly_earnings=Decimal(str(row[8]))
                        if row[8]
                        else None,
                        primary_metal_avg_weekly_earnings=Decimal(str(row[9])) if row[9] else None,
                    )
                )
                count += 1

    session.commit()
    return count


# =============================================================================
# MAIN ETL ORCHESTRATION
# =============================================================================


def run_etl(reset: bool = False) -> ETLStats:
    """Run the complete ETL pipeline.

    Args:
        reset: If True, drop and recreate all tables

    Returns:
        ETLStats with counts and errors
    """
    stats = ETLStats()
    target_engine = get_normalized_engine()
    source_engine = get_source_engine()

    if reset:
        logger.info("Dropping existing tables...")
        NormalizedBase.metadata.drop_all(bind=target_engine)

    logger.info("Creating tables...")
    NormalizedBase.metadata.create_all(bind=target_engine)

    # Create session
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=target_engine)
    session = SessionLocal()

    try:
        # Phase 1: Load dimensions (order matters for FK dependencies)
        logger.info("Loading dimensions...")

        dimension_loaders = [
            ("dim_state", lambda: load_dim_state(source_engine, session)),
            ("dim_county", lambda: load_dim_county(source_engine, session)),
            ("dim_metro_area", lambda: load_dim_metro_area(source_engine, session)),
            ("dim_country", lambda: load_dim_country(source_engine, session)),
            ("dim_import_source", lambda: load_dim_import_source(source_engine, session)),
            ("dim_industry", lambda: load_dim_industry(source_engine, session)),
            ("dim_sector", lambda: load_dim_sector(source_engine, session)),
            ("dim_ownership", lambda: load_dim_ownership(source_engine, session)),
            ("dim_income_bracket", lambda: load_dim_income_bracket(source_engine, session)),
            ("dim_employment_status", lambda: load_dim_employment_status(source_engine, session)),
            ("dim_worker_class", lambda: load_dim_worker_class(source_engine, session)),
            ("dim_occupation", lambda: load_dim_occupation(source_engine, session)),
            ("dim_education_level", lambda: load_dim_education_level(source_engine, session)),
            ("dim_housing_tenure", lambda: load_dim_housing_tenure(session)),
            ("dim_rent_burden", lambda: load_dim_rent_burden(source_engine, session)),
            ("dim_commute_mode", lambda: load_dim_commute_mode(source_engine, session)),
            ("dim_poverty_category", lambda: load_dim_poverty_category(source_engine, session)),
            ("dim_energy_table", lambda: load_dim_energy_table(source_engine, session)),
            ("dim_energy_series", lambda: load_dim_energy_series(source_engine, session)),
            ("dim_wealth_class", lambda: load_dim_wealth_class(source_engine, session)),
            ("dim_asset_category", lambda: load_dim_asset_category(source_engine, session)),
            ("dim_fred_series", lambda: load_dim_fred_series(source_engine, session)),
            ("dim_commodity", lambda: load_dim_commodity(source_engine, session)),
            ("dim_commodity_metric", lambda: load_dim_commodity_metric(source_engine, session)),
            ("dim_gender", lambda: load_dim_gender(session)),
            ("dim_data_source", lambda: load_dim_data_source(source_engine, session)),
            ("dim_time", lambda: load_dim_time(source_engine, session)),
        ]

        for name, loader in dimension_loaders:
            try:
                count = loader()  # type: ignore[no-untyped-call]
                stats.dimensions_loaded[name] = count
                logger.info(f"  {name}: {count} rows")
            except Exception as e:
                stats.errors.append(f"{name}: {e}")
                logger.error(f"  {name}: ERROR - {e}")

        # Phase 2: Build lookups
        logger.info("Building FK lookups...")
        lookups = build_lookups(session)

        # Phase 3: Load facts
        logger.info("Loading facts...")

        fact_loaders = [
            # Census facts
            (
                "fact_census_income",
                lambda: load_fact_census_income(source_engine, session, lookups),
            ),
            (
                "fact_census_median_income",
                lambda: load_fact_census_median_income(source_engine, session, lookups),
            ),
            (
                "fact_census_employment",
                lambda: load_fact_census_employment(source_engine, session, lookups),
            ),
            (
                "fact_census_worker_class",
                lambda: load_fact_census_worker_class(source_engine, session, lookups),
            ),
            (
                "fact_census_occupation",
                lambda: load_fact_census_occupation(source_engine, session, lookups),
            ),
            ("fact_census_hours", lambda: load_fact_census_hours(source_engine, session, lookups)),
            (
                "fact_census_housing",
                lambda: load_fact_census_housing(source_engine, session, lookups),
            ),
            ("fact_census_rent", lambda: load_fact_census_rent(source_engine, session, lookups)),
            (
                "fact_census_rent_burden",
                lambda: load_fact_census_rent_burden(source_engine, session, lookups),
            ),
            (
                "fact_census_education",
                lambda: load_fact_census_education(source_engine, session, lookups),
            ),
            ("fact_census_gini", lambda: load_fact_census_gini(source_engine, session, lookups)),
            (
                "fact_census_commute",
                lambda: load_fact_census_commute(source_engine, session, lookups),
            ),
            (
                "fact_census_poverty",
                lambda: load_fact_census_poverty(source_engine, session, lookups),
            ),
            (
                "fact_census_income_sources",
                lambda: load_fact_census_income_sources(source_engine, session, lookups),
            ),
            # Trade facts
            (
                "fact_trade_monthly",
                lambda: load_fact_trade_monthly(source_engine, session, lookups),
            ),
            # QCEW/Productivity facts
            ("fact_qcew_annual", lambda: load_fact_qcew_annual(source_engine, session, lookups)),
            (
                "fact_productivity_annual",
                lambda: load_fact_productivity_annual(source_engine, session, lookups),
            ),
            # Energy facts
            (
                "fact_energy_annual",
                lambda: load_fact_energy_annual(source_engine, session, lookups),
            ),
            # FRED facts
            (
                "fact_fred_national",
                lambda: load_fact_fred_national(source_engine, session, lookups),
            ),
            (
                "fact_fred_wealth_levels",
                lambda: load_fact_fred_wealth_levels(source_engine, session, lookups),
            ),
            (
                "fact_fred_wealth_shares",
                lambda: load_fact_fred_wealth_shares(source_engine, session, lookups),
            ),
            (
                "fact_fred_industry_unemployment",
                lambda: load_fact_fred_industry_unemployment(source_engine, session, lookups),
            ),
            (
                "fact_fred_state_unemployment",
                lambda: load_fact_fred_state_unemployment(source_engine, session, lookups),
            ),
            # Commodity facts
            (
                "fact_commodity_observation",
                lambda: load_fact_commodity_observation(source_engine, session, lookups),
            ),
            # Mineral facts
            (
                "fact_state_minerals",
                lambda: load_fact_state_minerals(source_engine, session, lookups),
            ),
            (
                "fact_mineral_production",
                lambda: load_fact_mineral_production(source_engine, session, lookups),
            ),
            (
                "fact_mineral_employment",
                lambda: load_fact_mineral_employment(source_engine, session, lookups),
            ),
        ]

        for name, loader in fact_loaders:
            try:
                count = loader()  # type: ignore[no-untyped-call]
                stats.facts_loaded[name] = count
                logger.info(f"  {name}: {count} rows")
            except Exception as e:
                stats.errors.append(f"{name}: {e}")
                logger.error(f"  {name}: ERROR - {e}")

    finally:
        session.close()

    return stats


__all__ = [
    "ETLStats",
    "run_etl",
]
