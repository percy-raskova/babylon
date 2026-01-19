"""HIFLD Local Law Enforcement Locations loader with streaming checkpoint support.

Loads police station data from HIFLD ArcGIS Feature Service and aggregates
to county-level facility counts with page-level checkpoints for resume.

The loader categorizes facilities by type (local police, sheriff, campus
police, etc.) and aggregates counts to the county level.

Source: https://hifld-geoplatform.opendata.arcgis.com/datasets/local-law-enforcement-locations
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import func

from babylon.config.defines import GameDefines
from babylon.data.arcgis_loader_base import ArcGISStreamingLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.normalize.schema import (
    DimCoerciveType,
    FactCoerciveInfrastructure,
    StagingArcGISFeature,
)
from babylon.data.utils.fips_resolver import extract_county_fips_from_attrs

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_police_service_url(defines: GameDefines | None = None) -> str:
    """Get Law Enforcement Locations FeatureServer URL from configuration.

    Args:
        defines: Optional GameDefines instance. Uses default if not provided.

    Returns:
        Complete FeatureServer URL for Law Enforcement Locations.
    """
    if defines is None:
        defines = GameDefines.load_default()
    return defines.external_data.law_enforcement_url()


# Police type mapping: facility_type -> (code, name, category, command_chain)
POLICE_TYPE_MAP: dict[str, tuple[str, str, str, str]] = {
    "POLICE DEPARTMENT": ("police_local", "Local Police Department", "enforcement", "local"),
    "SHERIFF": ("police_sheriff", "Sheriff's Office", "enforcement", "local"),
    "CAMPUS POLICE": ("police_campus", "Campus Police", "enforcement", "local"),
    "TRANSIT POLICE": ("police_transit", "Transit Police", "enforcement", "local"),
    "CONSTABLE": ("police_constable", "Constable", "enforcement", "local"),
    "MARSHAL": ("police_marshal", "Marshal's Office", "enforcement", "local"),
    "TRIBAL POLICE": ("police_tribal", "Tribal Police", "enforcement", "federal"),
}

DEFAULT_POLICE_TYPE = ("police_other", "Other Law Enforcement", "enforcement", "local")


class HIFLDPoliceLoader(ArcGISStreamingLoader):
    """Loader for HIFLD Local Law Enforcement Locations with checkpoint support.

    Fetches police station data from HIFLD ArcGIS Feature Service with
    page-level checkpoints, then aggregates to county-level facility counts.

    Two-phase loading:
        1. Fetch: Stream features to staging table with checkpoints
        2. Aggregate: GROUP BY county/type and insert facts
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize police loader."""
        super().__init__(config)

    # -------------------------------------------------------------------------
    # Abstract Method Implementations
    # -------------------------------------------------------------------------

    def _get_source_code(self) -> str:
        """Return source code for checkpoints."""
        return "hifld_police"

    def _get_service_url(self) -> str:
        """Return ArcGIS FeatureServer URL."""
        return _get_police_service_url()

    def _get_out_fields(self) -> str:
        """Return comma-separated field names to fetch."""
        return "OBJECTID,COUNTYFIPS,COUNTY,STATE,TYPE,NAME"

    def _map_feature_to_staging(
        self, feature: Any, fips_lookup: dict[str, int]
    ) -> dict[str, Any] | None:
        """Convert ArcGIS feature to staging record.

        Args:
            feature: ArcGIS feature with object_id and attributes.
            fips_lookup: Map of county FIPS code -> county_id.

        Returns:
            Dict with staging record fields, or None to skip.
        """
        attrs = feature.attributes

        county_fips = extract_county_fips_from_attrs(attrs)
        if not county_fips or county_fips not in fips_lookup:
            return None

        type_code = self._map_facility_type(attrs)

        return {
            "object_id": feature.object_id,
            "county_fips": county_fips,
            "type_code": type_code,
            "capacity": None,  # Police stations don't have capacity
        }

    def _aggregate_and_insert_facts(self, session: Session, source_id: int) -> int:
        """Aggregate staging data and insert facts.

        Uses SQL GROUP BY on staging table to produce county-level aggregates.
        """
        source_code = self._get_source_code()

        # Query aggregates from staging
        results = (
            session.query(
                StagingArcGISFeature.county_fips,
                StagingArcGISFeature.type_code,
                func.count(StagingArcGISFeature.feature_id).label("count"),
            )
            .filter(StagingArcGISFeature.source_code == source_code)
            .filter(StagingArcGISFeature.county_fips.isnot(None))
            .group_by(
                StagingArcGISFeature.county_fips,
                StagingArcGISFeature.type_code,
            )
            .all()
        )

        # Insert facts
        count = 0
        for county_fips, type_code, facility_count in results:
            county_id = self._fips_to_county.get(county_fips)
            type_id = self._type_to_id.get(type_code)

            if county_id and type_id:
                fact = FactCoerciveInfrastructure(
                    county_id=county_id,
                    coercive_type_id=type_id,
                    source_id=source_id,
                    facility_count=facility_count,
                    total_capacity=None,
                )
                session.add(fact)
                count += 1

        session.flush()
        return count

    # -------------------------------------------------------------------------
    # Optional Override Implementations
    # -------------------------------------------------------------------------

    def _setup_dimensions(self, session: Session, verbose: bool) -> None:
        """Set up dimension tables before loading."""
        if verbose:
            print(f"Loaded {len(self._fips_to_county):,} county mappings")

        self._load_coercive_types(session)
        self._load_data_source(session)

    def _clear_fact_data(self, session: Session, verbose: bool) -> None:
        """Clear existing police fact data on reset."""
        if verbose:
            print("Clearing existing police data...")
        self._clear_police_data(session)

    # -------------------------------------------------------------------------
    # Police-Specific Methods
    # -------------------------------------------------------------------------

    def _clear_police_data(self, session: Session) -> None:
        """Clear only police-related coercive infrastructure data."""
        police_type_codes = list({code for code, _, _, _ in POLICE_TYPE_MAP.values()})
        police_type_codes.append(DEFAULT_POLICE_TYPE[0])

        types = (
            session.query(DimCoerciveType).filter(DimCoerciveType.code.in_(police_type_codes)).all()
        )
        type_ids = [t.coercive_type_id for t in types]

        if type_ids:
            session.query(FactCoerciveInfrastructure).filter(
                FactCoerciveInfrastructure.coercive_type_id.in_(type_ids)
            ).delete(synchronize_session=False)

    def _load_coercive_types(self, session: Session) -> int:
        """Load/ensure coercive type dimension for police."""
        count = 0
        seen_codes: set[str] = set()
        all_types = list(POLICE_TYPE_MAP.values()) + [DEFAULT_POLICE_TYPE]

        for code, name, category, command_chain in all_types:
            if code in seen_codes:
                continue
            seen_codes.add(code)

            existing = session.query(DimCoerciveType).filter(DimCoerciveType.code == code).first()

            if existing:
                self._type_to_id[code] = existing.coercive_type_id
            else:
                coercive_type = DimCoerciveType(
                    code=code,
                    name=name,
                    category=category,
                    command_chain=command_chain,
                )
                session.add(coercive_type)
                session.flush()
                self._type_to_id[code] = coercive_type.coercive_type_id
                count += 1

        return count

    def _load_data_source(self, session: Session) -> None:
        """Load data source dimension."""
        self._source_id = self._get_or_create_data_source(
            session,
            source_code="HIFLD_POLICE_2024",
            source_name="HIFLD Local Law Enforcement Locations",
            source_url="https://hifld-geoplatform.opendata.arcgis.com/datasets/local-law-enforcement-locations",
            source_agency="DHS HIFLD",
            source_year=2024,
        )

    def _map_facility_type(self, attrs: dict[str, Any]) -> str:
        """Map facility type to coercive type code."""
        facility_type = (attrs.get("TYPE") or "").upper().strip()

        # Direct match
        if facility_type in POLICE_TYPE_MAP:
            return POLICE_TYPE_MAP[facility_type][0]

        # Partial matches
        for key, (code, _, _, _) in POLICE_TYPE_MAP.items():
            if key in facility_type:
                return code

        # Check name field for hints
        name = (attrs.get("NAME") or "").upper()
        if "SHERIFF" in name:
            return "police_sheriff"
        if "CAMPUS" in name or "UNIVERSITY" in name or "COLLEGE" in name:
            return "police_campus"

        return DEFAULT_POLICE_TYPE[0]


__all__ = ["HIFLDPoliceLoader"]
