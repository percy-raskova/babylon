"""HIFLD Prison Boundaries loader with streaming checkpoint support.

Loads prison/correctional facility data from HIFLD ArcGIS Feature Service
and aggregates to county-level capacity metrics with page-level checkpoints.

The loader categorizes facilities by type (federal, state, local, private)
and aggregates counts and capacity to the county level for integration
with the coercive infrastructure fact table.

Source: https://hifld-geoplatform.opendata.arcgis.com/datasets/prison-boundaries
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import func

from babylon.config.defines import GameDefines
from babylon.data.arcgis_loader_base import ArcGISStreamingLoader
from babylon.data.loader_base import LoaderConfig
from babylon.data.reference.schema import (
    DimCoerciveType,
    FactCoerciveInfrastructure,
    StagingArcGISFeature,
)
from babylon.data.utils.fips_resolver import extract_county_fips_from_attrs

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_prisons_service_url(defines: GameDefines | None = None) -> str:
    """Get Prison Boundaries FeatureServer URL from configuration.

    Args:
        defines: Optional GameDefines instance. Uses default if not provided.

    Returns:
        Complete FeatureServer URL for Prison Boundaries.
    """
    if defines is None:
        defines = GameDefines.load_default()
    return defines.external_data.prison_boundaries_url()


# Prison type mapping: facility_type -> (code, name, category, command_chain)
PRISON_TYPE_MAP: dict[str, tuple[str, str, str, str]] = {
    "FEDERAL": ("prison_federal", "Federal Prison", "carceral", "federal"),
    "STATE": ("prison_state", "State Prison", "carceral", "state"),
    "LOCAL": ("prison_local", "Local Jail/Detention", "carceral", "local"),
    "COUNTY": ("prison_local", "Local Jail/Detention", "carceral", "local"),
    "CITY": ("prison_local", "Local Jail/Detention", "carceral", "local"),
    "PRIVATE": ("prison_private", "Private Prison", "carceral", "mixed"),
    "TRIBAL": ("prison_tribal", "Tribal Correctional", "carceral", "federal"),
}

# Default for unknown types
DEFAULT_PRISON_TYPE = ("prison_other", "Other Correctional", "carceral", "mixed")


class HIFLDPrisonsLoader(ArcGISStreamingLoader):
    """Loader for HIFLD Prison Boundaries with checkpoint support.

    Fetches prison facility data from HIFLD ArcGIS Feature Service with
    page-level checkpoints, then aggregates to county-level metrics.

    Two-phase loading:
        1. Fetch: Stream features to staging table with checkpoints
        2. Aggregate: GROUP BY county/type and insert facts with capacity
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize prison loader."""
        super().__init__(config)

    # -------------------------------------------------------------------------
    # Abstract Method Implementations
    # -------------------------------------------------------------------------

    def _get_source_code(self) -> str:
        """Return source code for checkpoints."""
        return "hifld_prisons"

    def _get_service_url(self) -> str:
        """Return ArcGIS FeatureServer URL."""
        return _get_prisons_service_url()

    def _get_out_fields(self) -> str:
        """Return comma-separated field names to fetch."""
        return "OBJECTID,COUNTYFIPS,COUNTY,STATE,TYPE,CAPACITY,STATUS,SECURELVL"

    def _map_feature_to_staging(
        self, feature: Any, fips_lookup: dict[str, int]
    ) -> dict[str, Any] | None:
        """Convert ArcGIS feature to staging record.

        Skips closed facilities and those without valid FIPS.
        """
        attrs = feature.attributes

        county_fips = extract_county_fips_from_attrs(attrs)
        if not county_fips or county_fips not in fips_lookup:
            return None

        # Skip closed facilities
        status = (attrs.get("STATUS") or "").upper()
        if status and "CLOSED" in status:
            return None

        type_code = self._map_facility_type(attrs)
        capacity = self._parse_capacity(attrs.get("CAPACITY"))

        return {
            "object_id": feature.object_id,
            "county_fips": county_fips,
            "type_code": type_code,
            "capacity": capacity if capacity > 0 else None,
        }

    def _aggregate_and_insert_facts(self, session: Session, source_id: int) -> int:
        """Aggregate staging data and insert facts with capacity sums."""
        source_code = self._get_source_code()

        # Query aggregates from staging (count + sum capacity)
        results = (
            session.query(
                StagingArcGISFeature.county_fips,
                StagingArcGISFeature.type_code,
                func.count(StagingArcGISFeature.feature_id).label("count"),
                func.coalesce(func.sum(StagingArcGISFeature.capacity), 0).label("capacity"),
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
        for county_fips, type_code, facility_count, total_capacity in results:
            county_id = self._fips_to_county.get(county_fips)
            type_id = self._type_to_id.get(type_code)

            if county_id and type_id:
                fact = FactCoerciveInfrastructure(
                    county_id=county_id,
                    coercive_type_id=type_id,
                    source_id=source_id,
                    facility_count=facility_count,
                    total_capacity=total_capacity if total_capacity > 0 else None,
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
        """Clear existing prison fact data on reset."""
        if verbose:
            print("Clearing existing prison data...")
        self._clear_prison_data(session)

    # -------------------------------------------------------------------------
    # Prison-Specific Methods
    # -------------------------------------------------------------------------

    def _clear_prison_data(self, session: Session) -> None:
        """Clear only prison-related coercive infrastructure data."""
        prison_type_codes = list({code for code, _, _, _ in PRISON_TYPE_MAP.values()})
        prison_type_codes.append(DEFAULT_PRISON_TYPE[0])

        types = (
            session.query(DimCoerciveType).filter(DimCoerciveType.code.in_(prison_type_codes)).all()
        )
        type_ids = [t.coercive_type_id for t in types]

        if type_ids:
            session.query(FactCoerciveInfrastructure).filter(
                FactCoerciveInfrastructure.coercive_type_id.in_(type_ids)
            ).delete(synchronize_session=False)

    def _load_coercive_types(self, session: Session) -> int:
        """Load/ensure coercive type dimension for prisons."""
        count = 0
        seen_codes: set[str] = set()
        all_types = list(PRISON_TYPE_MAP.values()) + [DEFAULT_PRISON_TYPE]

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
            source_code="HIFLD_PRISONS_2024",
            source_name="HIFLD Prison Boundaries",
            source_url="https://hifld-geoplatform.opendata.arcgis.com/datasets/prison-boundaries",
            source_agency="DHS HIFLD",
            source_year=2024,
        )

    def _map_facility_type(self, attrs: dict[str, Any]) -> str:
        """Map facility type to coercive type code."""
        facility_type = (attrs.get("TYPE") or "").upper().strip()

        # Direct match
        if facility_type in PRISON_TYPE_MAP:
            return PRISON_TYPE_MAP[facility_type][0]

        # Partial matches
        for key, (code, _, _, _) in PRISON_TYPE_MAP.items():
            if key in facility_type:
                return code

        return DEFAULT_PRISON_TYPE[0]

    def _parse_capacity(self, value: Any) -> int:
        """Parse capacity value from various formats."""
        if value is None:
            return 0
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float):
            return max(0, int(value))
        if isinstance(value, str):
            try:
                cleaned = value.replace(",", "").strip()
                if cleaned:
                    return max(0, int(float(cleaned)))
            except ValueError:
                pass
        return 0


__all__ = ["HIFLDPrisonsLoader"]
