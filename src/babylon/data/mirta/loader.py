"""MIRTA Military Installations loader.

Loads military installation data from MIRTA ArcGIS FeatureServer and aggregates
to county-level facility counts.

The loader categorizes installations by service branch and aggregates counts
to the county level for coercive infrastructure analysis.

Source: https://www.acq.osd.mil/eie/BSI/BEI_MIRTA.html
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
    DimCounty,
    DimDataSource,
    FactCoerciveInfrastructure,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# MIRTA Military Installations FeatureServer
MIRTA_SERVICE_URL = (
    "https://services7.arcgis.com/n1YM8pTrFmm7L4hs/arcgis/rest/services/"
    "MIRTA_Public/FeatureServer/0"
)

# Military branch mapping: service -> (code, name, category, command_chain)
MILITARY_TYPE_MAP: dict[str, tuple[str, str, str, str]] = {
    "ARMY": ("military_army", "Army Installation", "military", "federal"),
    "NAVY": ("military_navy", "Navy Installation", "military", "federal"),
    "AIR FORCE": ("military_air_force", "Air Force Installation", "military", "federal"),
    "MARINE CORPS": ("military_marines", "Marine Corps Installation", "military", "federal"),
    "COAST GUARD": ("military_coast_guard", "Coast Guard Installation", "military", "federal"),
    "SPACE FORCE": ("military_space_force", "Space Force Installation", "military", "federal"),
    "NATIONAL GUARD": ("military_guard", "National Guard Installation", "military", "federal"),
    "JOINT": ("military_joint", "Joint Military Installation", "military", "federal"),
}

DEFAULT_MILITARY_TYPE = ("military_other", "Other Military Installation", "military", "federal")


class MIRTAMilitaryLoader(DataLoader):
    """Loader for MIRTA Military Installations data.

    Fetches military installation data from MIRTA ArcGIS FeatureServer and
    aggregates to county-level facility counts.
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize military loader."""
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
        """Load military installation data into 3NF schema."""
        stats = LoadStats(source="mirta_military")

        if verbose:
            print("Loading MIRTA Military Installations from ArcGIS FeatureServer")

        try:
            self._client = ArcGISClient(MIRTA_SERVICE_URL)

            total_count = self._client.get_record_count()
            if verbose:
                print(f"Total installations: {total_count:,}")

            if reset:
                if verbose:
                    print("Clearing existing military data...")
                self._clear_military_data(session)
                session.flush()

            self._load_county_lookup(session)
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

    def _clear_military_data(self, session: Session) -> None:
        """Clear only military-related coercive infrastructure data."""
        military_type_codes = list({code for code, _, _, _ in MILITARY_TYPE_MAP.values()})
        military_type_codes.append(DEFAULT_MILITARY_TYPE[0])

        types = (
            session.query(DimCoerciveType)
            .filter(DimCoerciveType.code.in_(military_type_codes))
            .all()
        )
        type_ids = [t.coercive_type_id for t in types]

        if type_ids:
            session.query(FactCoerciveInfrastructure).filter(
                FactCoerciveInfrastructure.coercive_type_id.in_(type_ids)
            ).delete(synchronize_session=False)

    def _load_county_lookup(self, session: Session) -> None:
        """Build FIPS -> county_id lookup."""
        counties = session.query(DimCounty).all()
        self._fips_to_county = {c.fips: c.county_id for c in counties}

    def _load_coercive_types(self, session: Session) -> int:
        """Load/ensure coercive type dimension for military."""
        count = 0
        seen_codes: set[str] = set()
        all_types = list(MILITARY_TYPE_MAP.values()) + [DEFAULT_MILITARY_TYPE]

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
        existing = (
            session.query(DimDataSource).filter(DimDataSource.source_code == "MIRTA_2024").first()
        )
        if existing:
            self._source_id = existing.source_id
            return

        source = DimDataSource(
            source_code="MIRTA_2024",
            source_name="MIRTA Military Installations",
            source_url="https://www.acq.osd.mil/eie/BSI/BEI_MIRTA.html",
            source_agency="DoD OASD(S)",
            source_year=2024,
        )
        session.add(source)
        session.flush()
        self._source_id = source.source_id

    def _load_aggregated_facts(
        self,
        session: Session,
        total_count: int,
        verbose: bool,
    ) -> int:
        """Load county-aggregated military facts."""
        if self._client is None:
            msg = "ArcGIS client not initialized"
            raise RuntimeError(msg)
        if self._source_id is None:
            msg = "Data source not loaded"
            raise RuntimeError(msg)

        # Aggregate: county_fips -> type_code -> count
        aggregates: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # MIRTA fields vary - common ones include SERVICE, SITE_NAME, STATE_TERR, etc.
        features = self._client.query_all(
            out_fields="*",  # Get all fields since MIRTA schema varies
        )
        feature_iter = tqdm(features, total=total_count, desc="Military", disable=not verbose)

        skipped_no_fips = 0
        skipped_not_in_db = 0

        for feature in feature_iter:
            attrs = feature.attributes

            county_fips = self._extract_county_fips(attrs)
            if not county_fips:
                skipped_no_fips += 1
                continue

            if county_fips not in self._fips_to_county:
                skipped_not_in_db += 1
                continue

            type_code = self._map_service_branch(attrs)
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
                    total_capacity=None,
                )
                session.add(fact)
                count += 1

        session.flush()
        return count

    def _extract_county_fips(self, attrs: dict[str, Any]) -> str | None:
        """Extract 5-digit county FIPS from feature attributes.

        MIRTA may have FIPS in various fields - try common ones.
        """
        # Try common FIPS field names
        for field_name in ["COUNTYFIPS", "CNTY_FIPS", "FIPS", "COUNTY_FIPS"]:
            county_fips = attrs.get(field_name)
            if county_fips:
                fips_str = str(county_fips).strip()
                if len(fips_str) >= 5:
                    return fips_str[:5].zfill(5)
                if len(fips_str) == 4:
                    return fips_str.zfill(5)

        # Try constructing from state + county FIPS
        state_fips = attrs.get("STATE_FIPS") or attrs.get("STATEFP")
        county_only = attrs.get("CNTY_FIPS_3") or attrs.get("COUNTYFP")
        if state_fips and county_only:
            return f"{str(state_fips).zfill(2)}{str(county_only).zfill(3)}"

        return None

    def _map_service_branch(self, attrs: dict[str, Any]) -> str:
        """Map service branch to coercive type code."""
        # Try common service field names
        service = None
        for field_name in ["SERVICE", "BRANCH", "COMPONENT", "OPER_STAT"]:
            service = attrs.get(field_name)
            if service:
                break

        if not service:
            return DEFAULT_MILITARY_TYPE[0]

        service = str(service).upper().strip()

        # Direct match
        if service in MILITARY_TYPE_MAP:
            return MILITARY_TYPE_MAP[service][0]

        # Partial matches
        for key, (code, _, _, _) in MILITARY_TYPE_MAP.items():
            if key in service:
                return code

        # Check site name for hints
        site_name = (attrs.get("SITE_NAME") or attrs.get("NAME") or "").upper()
        if "AIR FORCE" in site_name or "AFB" in site_name:
            return "military_air_force"
        if "NAVAL" in site_name or "NAS" in site_name:
            return "military_navy"
        if "ARMY" in site_name or "FORT" in site_name:
            return "military_army"
        if "MARINE" in site_name:
            return "military_marines"
        if "GUARD" in site_name or "ARMORY" in site_name:
            return "military_guard"

        return DEFAULT_MILITARY_TYPE[0]


__all__ = ["MIRTAMilitaryLoader"]
