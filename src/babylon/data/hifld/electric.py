"""HIFLD Electric Grid Infrastructure loader.

Loads electric substation and transmission line data from HIFLD ArcGIS Feature
Services and aggregates to county-level infrastructure metrics.

Sources:
    Substations: https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-substations
    Transmission: https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-power-transmission-lines
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from tqdm import tqdm  # type: ignore[import-untyped]

from babylon.data.external.arcgis import ArcGISClient
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimCounty,
    DimDataSource,
    FactElectricGrid,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# HIFLD Electric Grid Feature Services
SUBSTATIONS_SERVICE_URL = (
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
    "Electric_Substations/FeatureServer/0"
)

TRANSMISSION_SERVICE_URL = (
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
    "Electric_Power_Transmission_Lines/FeatureServer/0"
)


class HIFLDElectricLoader(DataLoader):
    """Loader for HIFLD Electric Grid Infrastructure data.

    Fetches electric substation and transmission line data from HIFLD ArcGIS
    Feature Services and aggregates to county-level metrics.
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize electric grid loader."""
        super().__init__(config)
        self._substation_client: ArcGISClient | None = None
        self._transmission_client: ArcGISClient | None = None
        self._fips_to_county: dict[str, int] = {}
        self._source_id: int | None = None

    def get_dimension_tables(self) -> list[type[Any]]:
        """Return dimension tables (none specific to this loader)."""
        return []

    def get_fact_tables(self) -> list[type[Any]]:
        """Return fact tables."""
        return [FactElectricGrid]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load electric grid data into 3NF schema."""
        stats = LoadStats(source="hifld_electric")

        if verbose:
            print("Loading HIFLD Electric Grid from ArcGIS Feature Services")

        try:
            self._substation_client = ArcGISClient(SUBSTATIONS_SERVICE_URL)
            self._transmission_client = ArcGISClient(TRANSMISSION_SERVICE_URL)

            substation_count = self._substation_client.get_record_count()
            transmission_count = self._transmission_client.get_record_count()
            if verbose:
                print(f"Total substations: {substation_count:,}")
                print(f"Total transmission lines: {transmission_count:,}")

            if reset:
                if verbose:
                    print("Clearing existing electric grid data...")
                self._clear_electric_data(session)
                session.flush()

            self._load_county_lookup(session)
            if verbose:
                print(f"Loaded {len(self._fips_to_county):,} county mappings")

            self._load_data_source(session)
            stats.dimensions_loaded["dim_data_source"] = 1

            session.flush()

            # Load substations first
            substation_agg = self._aggregate_substations(substation_count, verbose)
            stats.api_calls += (substation_count // 2000) + 1

            # Load transmission lines
            transmission_agg = self._aggregate_transmission(transmission_count, verbose)
            stats.api_calls += (transmission_count // 2000) + 1

            # Merge aggregates and insert facts
            fact_count = self._insert_merged_facts(session, substation_agg, transmission_agg)
            stats.facts_loaded["fact_electric_grid"] = fact_count

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        finally:
            if self._substation_client:
                self._substation_client.close()
                self._substation_client = None
            if self._transmission_client:
                self._transmission_client.close()
                self._transmission_client = None

        return stats

    def _clear_electric_data(self, session: Session) -> None:
        """Clear existing electric grid data."""
        # Delete all facts for our source
        source = (
            session.query(DimDataSource)
            .filter(DimDataSource.source_code == "HIFLD_ELECTRIC_2024")
            .first()
        )
        if source:
            session.query(FactElectricGrid).filter(
                FactElectricGrid.source_id == source.source_id
            ).delete(synchronize_session=False)

    def _load_county_lookup(self, session: Session) -> None:
        """Build FIPS -> county_id lookup."""
        counties = session.query(DimCounty).all()
        self._fips_to_county = {c.fips: c.county_id for c in counties}

    def _load_data_source(self, session: Session) -> None:
        """Load data source dimension."""
        existing = (
            session.query(DimDataSource)
            .filter(DimDataSource.source_code == "HIFLD_ELECTRIC_2024")
            .first()
        )
        if existing:
            self._source_id = existing.source_id
            return

        source = DimDataSource(
            source_code="HIFLD_ELECTRIC_2024",
            source_name="HIFLD Electric Grid Infrastructure",
            source_url="https://hifld-geoplatform.opendata.arcgis.com/",
            source_agency="DHS HIFLD",
            source_year=2024,
        )
        session.add(source)
        session.flush()
        self._source_id = source.source_id

    def _aggregate_substations(
        self,
        total_count: int,
        verbose: bool,
    ) -> dict[str, dict[str, float]]:
        """Aggregate substations by county.

        Returns:
            Dict mapping county_fips -> {count: int, capacity_mw: float}
        """
        if self._substation_client is None:
            msg = "Substation client not initialized"
            raise RuntimeError(msg)

        aggregates: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0.0, "capacity_mw": 0.0}
        )

        features = self._substation_client.query_all(
            out_fields="COUNTYFIPS,COUNTY,STATE,MAX_VOLT,MIN_VOLT,STATUS",
        )
        feature_iter = tqdm(features, total=total_count, desc="Substations", disable=not verbose)

        for feature in feature_iter:
            attrs = feature.attributes

            county_fips = self._extract_county_fips(attrs)
            if not county_fips or county_fips not in self._fips_to_county:
                continue

            # Skip non-operational
            status = (attrs.get("STATUS") or "").upper()
            if status and ("RETIRED" in status or "DECOMM" in status):
                continue

            aggregates[county_fips]["count"] += 1

            # Estimate capacity from voltage (rough approximation)
            max_volt = self._parse_numeric(attrs.get("MAX_VOLT"))
            if max_volt and max_volt > 0:
                # Very rough capacity estimate based on voltage class
                # This is approximate - real capacity data isn't public
                if max_volt >= 345000:  # EHV
                    aggregates[county_fips]["capacity_mw"] += 500
                elif max_volt >= 230000:
                    aggregates[county_fips]["capacity_mw"] += 200
                elif max_volt >= 115000:
                    aggregates[county_fips]["capacity_mw"] += 100
                else:
                    aggregates[county_fips]["capacity_mw"] += 50

        return aggregates

    def _aggregate_transmission(
        self,
        total_count: int,
        verbose: bool,
    ) -> dict[str, float]:
        """Aggregate transmission line miles by county.

        Note: This is approximate as lines span multiple counties.
        We attribute the full line length to each county it passes through.

        Returns:
            Dict mapping county_fips -> total_miles
        """
        if self._transmission_client is None:
            msg = "Transmission client not initialized"
            raise RuntimeError(msg)

        # For transmission lines, we need geometry to calculate miles per county
        # Since we don't have per-county breakdown, we'll skip this for now
        # and just count the lines that touch each county
        aggregates: dict[str, float] = defaultdict(float)

        features = self._transmission_client.query_all(
            out_fields="ID,VOLTAGE,STATUS,SHAPE_Length",
            return_geometry=False,  # Geometry too complex for county attribution
        )
        feature_iter = tqdm(features, total=total_count, desc="Transmission", disable=not verbose)

        # Without county FIPS on transmission lines, we can't aggregate by county
        # This is a known limitation - HIFLD transmission data doesn't have county FIPS
        # We'll return empty aggregates for now
        # Future enhancement: Use spatial join with county boundaries

        lines_skipped = 0
        for _ in feature_iter:
            lines_skipped += 1

        if verbose:
            print(
                f"\nNote: Transmission lines ({lines_skipped:,}) lack county FIPS - skipping aggregation"
            )

        return aggregates

    def _insert_merged_facts(
        self,
        session: Session,
        substation_agg: dict[str, dict[str, float]],
        transmission_agg: dict[str, float],
    ) -> int:
        """Merge substation and transmission aggregates and insert facts."""
        if self._source_id is None:
            msg = "Data source not loaded"
            raise RuntimeError(msg)

        count = 0
        # Get all county FIPS from both sources
        all_fips = set(substation_agg.keys()) | set(transmission_agg.keys())

        for county_fips in all_fips:
            county_id = self._fips_to_county.get(county_fips)
            if not county_id:
                continue

            sub_data = substation_agg.get(county_fips, {"count": 0, "capacity_mw": 0})
            trans_miles = transmission_agg.get(county_fips, 0)

            # Only insert if we have some data
            if sub_data["count"] > 0 or trans_miles > 0:
                fact = FactElectricGrid(
                    county_id=county_id,
                    source_id=self._source_id,
                    substation_count=int(sub_data["count"]),
                    total_capacity_mw=Decimal(str(sub_data["capacity_mw"]))
                    if sub_data["capacity_mw"] > 0
                    else None,
                    transmission_line_miles=Decimal(str(trans_miles)) if trans_miles > 0 else None,
                )
                session.add(fact)
                count += 1

        session.flush()
        return count

    def _extract_county_fips(self, attrs: dict[str, Any]) -> str | None:
        """Extract 5-digit county FIPS from feature attributes."""
        county_fips = attrs.get("COUNTYFIPS") or attrs.get("CNTY_FIPS") or attrs.get("COUNTY_FIP")
        if county_fips:
            fips_str = str(county_fips).strip()
            if len(fips_str) >= 5:
                return fips_str[:5].zfill(5)
            if len(fips_str) == 4:
                return fips_str.zfill(5)
        return None

    def _parse_numeric(self, value: Any) -> float | None:
        """Parse numeric value from various formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", "").strip())
            except ValueError:
                pass
        return None


__all__ = ["HIFLDElectricLoader"]
