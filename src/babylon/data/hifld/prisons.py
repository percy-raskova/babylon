"""HIFLD Prison Boundaries loader.

Loads prison/correctional facility data from HIFLD ArcGIS Feature Service
and aggregates to county-level capacity metrics.

The loader categorizes facilities by type (federal, state, local, private)
and aggregates counts and capacity to the county level for integration
with the coercive infrastructure fact table.

Source: https://hifld-geoplatform.opendata.arcgis.com/datasets/prison-boundaries
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
    FactCoerciveInfrastructure,
)
from babylon.data.utils.fips_resolver import extract_county_fips_from_attrs

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# HIFLD Prison Boundaries Feature Service
PRISONS_SERVICE_URL = (
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
    "Prison_Boundaries/FeatureServer/0"
)

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


class HIFLDPrisonsLoader(DataLoader):
    """Loader for HIFLD Prison Boundaries data.

    Fetches prison facility data from HIFLD ArcGIS Feature Service and
    aggregates to county-level coercive infrastructure metrics.

    Attributes:
        config: Loader configuration for temporal and geographic scope.
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize prison loader.

        Args:
            config: Optional loader configuration.
        """
        super().__init__(config)
        self._client: ArcGISClient | None = None
        self._fips_to_county: dict[str, int] = {}
        self._type_to_id: dict[str, int] = {}
        self._source_id: int | None = None

    def get_dimension_tables(self) -> list[type[Any]]:
        """Return dimension tables (coercive type dimension)."""
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
        """Load prison data into 3NF schema.

        Args:
            session: SQLAlchemy session for database operations.
            reset: Whether to clear existing prison data before loading.
            verbose: Whether to print progress information.
            **_kwargs: Additional keyword arguments (unused).

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        stats = LoadStats(source="hifld_prisons")

        if verbose:
            print("Loading HIFLD Prison Boundaries from ArcGIS Feature Service")

        try:
            self._client = ArcGISClient(PRISONS_SERVICE_URL)

            # Get record count for progress bar
            total_count = self._client.get_record_count()
            if verbose:
                print(f"Total facilities: {total_count:,}")

            if reset:
                if verbose:
                    print("Clearing existing prison data...")
                self._clear_prison_data(session)
                session.flush()

            # Load county lookup
            self._load_county_lookup(session)
            if verbose:
                print(f"Loaded {len(self._fips_to_county):,} county mappings")

            # Load/ensure coercive types
            type_count = self._load_coercive_types(session)
            stats.dimensions_loaded["dim_coercive_type"] = type_count

            # Load data source
            self._load_data_source(session)
            stats.dimensions_loaded["dim_data_source"] = 1

            session.flush()

            # Aggregate facilities by county
            fact_count = self._load_aggregated_facts(session, total_count, verbose)
            stats.facts_loaded["fact_coercive_infrastructure"] = fact_count
            stats.api_calls = (total_count // 2000) + 1  # Paginated queries

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

    def _clear_prison_data(self, session: Session) -> None:
        """Clear only prison-related coercive infrastructure data."""
        # Get all prison type codes
        prison_type_codes = list({code for code, _, _, _ in PRISON_TYPE_MAP.values()})
        prison_type_codes.append(DEFAULT_PRISON_TYPE[0])

        # Find existing types
        types = (
            session.query(DimCoerciveType).filter(DimCoerciveType.code.in_(prison_type_codes)).all()
        )
        type_ids = [t.coercive_type_id for t in types]

        if type_ids:
            # Delete facts for these types
            session.query(FactCoerciveInfrastructure).filter(
                FactCoerciveInfrastructure.coercive_type_id.in_(type_ids)
            ).delete(synchronize_session=False)

    def _load_county_lookup(self, session: Session) -> None:
        """Build FIPS -> county_id lookup."""
        counties = session.query(DimCounty).all()
        self._fips_to_county = {c.fips: c.county_id for c in counties}

    def _load_coercive_types(self, session: Session) -> int:
        """Load/ensure coercive type dimension for prisons.

        Returns:
            Number of new types created.
        """
        count = 0
        # Collect unique types from the mapping
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

    def _load_aggregated_facts(
        self,
        session: Session,
        total_count: int,
        verbose: bool,
    ) -> int:
        """Load county-aggregated prison facts.

        Args:
            session: Database session.
            total_count: Total feature count for progress bar.
            verbose: Whether to show progress.

        Returns:
            Number of fact rows inserted.
        """
        if self._client is None:
            msg = "ArcGIS client not initialized"
            raise RuntimeError(msg)
        if self._source_id is None:
            msg = "Data source not loaded"
            raise RuntimeError(msg)

        # Aggregate: county_fips -> type_code -> {count, capacity}
        aggregates: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"count": 0, "capacity": 0})
        )

        # Query features with relevant fields
        features = self._client.query_all(
            out_fields="COUNTYFIPS,COUNTY,STATE,TYPE,CAPACITY,STATUS,SECURELVL",
        )
        feature_iter = tqdm(features, total=total_count, desc="Prisons", disable=not verbose)

        skipped_no_fips = 0
        skipped_not_in_db = 0
        skipped_closed = 0

        for feature in feature_iter:
            attrs = feature.attributes

            # Get county FIPS
            county_fips = extract_county_fips_from_attrs(attrs)
            if not county_fips:
                skipped_no_fips += 1
                continue

            # Skip if not in our county list
            if county_fips not in self._fips_to_county:
                skipped_not_in_db += 1
                continue

            # Only count active facilities
            status = (attrs.get("STATUS") or "").upper()
            if status and "CLOSED" in status:
                skipped_closed += 1
                continue

            # Map facility type to coercive type
            type_code = self._map_facility_type(attrs)

            # Parse capacity
            capacity = self._parse_capacity(attrs.get("CAPACITY"))

            # Aggregate
            aggregates[county_fips][type_code]["count"] += 1
            aggregates[county_fips][type_code]["capacity"] += capacity

        if verbose:
            print(
                f"\nSkipped: {skipped_no_fips} no FIPS, {skipped_not_in_db} not in DB, {skipped_closed} closed"
            )

        # Insert aggregated facts
        count = 0
        for county_fips, type_data in aggregates.items():
            county_id = self._fips_to_county.get(county_fips)
            if not county_id:
                continue

            for type_code, metrics in type_data.items():
                type_id = self._type_to_id.get(type_code)
                if not type_id:
                    continue

                fact = FactCoerciveInfrastructure(
                    county_id=county_id,
                    coercive_type_id=type_id,
                    source_id=self._source_id,
                    facility_count=metrics["count"],
                    total_capacity=metrics["capacity"] if metrics["capacity"] > 0 else None,
                )
                session.add(fact)
                count += 1

        session.flush()
        return count

    def _map_facility_type(self, attrs: dict[str, Any]) -> str:
        """Map facility type to coercive type code.

        Args:
            attrs: Feature attribute dictionary.

        Returns:
            Coercive type code.
        """
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
        """Parse capacity value from various formats.

        Args:
            value: Raw capacity value (may be int, str, or None).

        Returns:
            Integer capacity or 0 if invalid.
        """
        if value is None:
            return 0
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float):
            return max(0, int(value))
        if isinstance(value, str):
            # Remove commas and try to parse
            try:
                cleaned = value.replace(",", "").strip()
                if cleaned:
                    return max(0, int(float(cleaned)))
            except ValueError:
                pass
        return 0


__all__ = ["HIFLDPrisonsLoader"]
