"""HIFLD Local Law Enforcement Locations loader.

Loads police station data from HIFLD ArcGIS Feature Service and aggregates
to county-level facility counts.

The loader categorizes facilities by type (local police, sheriff, campus
police, etc.) and aggregates counts to the county level.

Source: https://hifld-geoplatform.opendata.arcgis.com/datasets/local-law-enforcement-locations
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.external.arcgis import ArcGISClient
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimCoerciveType,
    FactCoerciveInfrastructure,
)
from babylon.data.utils.fips_resolver import extract_county_fips_from_attrs

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# HIFLD Local Law Enforcement Feature Service
POLICE_SERVICE_URL = (
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
    "Local_Law_Enforcement_Locations/FeatureServer/0"
)

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


class HIFLDPoliceLoader(DataLoader):
    """Loader for HIFLD Local Law Enforcement Locations data.

    Fetches police station data from HIFLD ArcGIS Feature Service and
    aggregates to county-level facility counts.
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize police loader."""
        super().__init__(config)
        self._client: ArcGISClient | None = None
        self._fips_to_county: dict[str, int] = {}
        self._type_to_id: dict[str, int] = {}
        self._source_id: int | None = None

    def get_dimension_tables(self) -> list[type[Any]]:
        """Return dimension tables."""
        return [DimCoerciveType]

    def get_fact_tables(self) -> list[type[Any]]:
        """Return fact tables."""
        return [FactCoerciveInfrastructure]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load police data into 3NF schema."""
        stats = LoadStats(source="hifld_police")

        if verbose:
            print("Loading HIFLD Local Law Enforcement from ArcGIS Feature Service")

        try:
            self._client = ArcGISClient(POLICE_SERVICE_URL)

            total_count = self._client.get_record_count()
            if verbose:
                print(f"Total facilities: {total_count:,}")

            if reset:
                if verbose:
                    print("Clearing existing police data...")
                self._clear_police_data(session)
                session.flush()

            self._fips_to_county = self._build_county_lookup(session)
            if verbose:
                print(f"Loaded {len(self._fips_to_county):,} county mappings")

            type_count = self._load_coercive_types(session)
            stats.dimensions_loaded["dim_coercive_type"] = type_count

            self._load_data_source(session)
            stats.dimensions_loaded["dim_data_source"] = 1

            session.flush()

            fact_count = self._load_aggregated_facts(session, total_count, verbose)
            stats.facts_loaded["fact_coercive_infrastructure"] = fact_count
            stats.api_calls = (total_count // 2000) + 1

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        finally:
            if self._client:
                self._client.close()
                self._client = None

        return stats

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

    def _load_aggregated_facts(
        self,
        session: Session,
        total_count: int,
        verbose: bool,
    ) -> int:
        """Load county-aggregated police facts."""
        if self._client is None:
            msg = "ArcGIS client not initialized"
            raise RuntimeError(msg)
        if self._source_id is None:
            msg = "Data source not loaded"
            raise RuntimeError(msg)

        # Aggregate: county_fips -> type_code -> count
        aggregates: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        features = self._client.query_all(
            out_fields="COUNTYFIPS,COUNTY,STATE,TYPE,NAME",
        )
        feature_iter = tqdm(features, total=total_count, desc="Police", disable=not verbose)

        skipped_no_fips = 0
        skipped_not_in_db = 0

        for feature in feature_iter:
            attrs = feature.attributes

            county_fips = extract_county_fips_from_attrs(attrs)
            if not county_fips:
                skipped_no_fips += 1
                continue

            if county_fips not in self._fips_to_county:
                skipped_not_in_db += 1
                continue

            type_code = self._map_facility_type(attrs)
            aggregates[county_fips][type_code] += 1

        if verbose:
            print(f"\nSkipped: {skipped_no_fips} no FIPS, {skipped_not_in_db} not in DB")

        # Insert aggregated facts
        count = 0
        for county_fips, type_data in aggregates.items():
            county_id = self._fips_to_county.get(county_fips)
            if not county_id:
                continue

            for type_code, facility_count in type_data.items():
                type_id = self._type_to_id.get(type_code)
                if not type_id:
                    continue

                fact = FactCoerciveInfrastructure(
                    county_id=county_id,
                    coercive_type_id=type_id,
                    source_id=self._source_id,
                    facility_count=facility_count,
                    total_capacity=None,  # No capacity for police stations
                )
                session.add(fact)
                count += 1

        session.flush()
        return count

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
