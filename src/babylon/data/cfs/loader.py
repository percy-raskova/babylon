"""Census Commodity Flow Survey (CFS) loader with county disaggregation.

Loads CFS commodity flow data at state level and disaggregates to county
level using allocation weights from DimGeographicHierarchy.

The CFS API provides origin-destination commodity flows at state level.
This loader distributes those flows to counties proportionally based on
employment weights (for origin) and population weights (for destination).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from tqdm import tqdm

from babylon.data.cfs.api_client import CFSAPIClient
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimCounty,
    DimGeographicHierarchy,
    DimSCTGCommodity,
    DimState,
    FactCommodityFlow,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CFSLoader(DataLoader):
    """Loader for Census CFS data with state-to-county disaggregation.

    Fetches state-level commodity flows from Census CFS API and distributes
    them to county pairs using DimGeographicHierarchy allocation weights.

    The disaggregation uses:
    - employment_weight for origin counties (production/shipping)
    - population_weight for destination counties (consumption)

    This creates county-to-county flow estimates from state-level data.
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize CFS loader."""
        super().__init__(config)
        self._client: CFSAPIClient | None = None
        self._state_fips_to_id: dict[str, int] = {}
        self._county_fips_to_id: dict[str, int] = {}
        self._sctg_to_id: dict[str, int] = {}
        self._source_id: int | None = None
        # Hierarchy: state_id -> [(county_id, pop_weight, emp_weight), ...]
        self._hierarchy: dict[int, list[tuple[int, Decimal, Decimal]]] = {}

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables this loader populates."""
        return [DimSCTGCommodity]

    def get_fact_tables(self) -> list[type]:
        """Return fact tables this loader populates."""
        return [FactCommodityFlow]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load CFS data with county disaggregation.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing CFS data first.
            verbose: If True, print progress information.

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        stats = LoadStats(source="cfs")
        # CFS uses most recent year from census_years (surveys are periodic: 2012, 2017, 2022)
        year = self.config.census_years[-1] if self.config.census_years else 2022

        if verbose:
            print(f"Loading Census CFS data for year {year}")

        try:
            # Initialize API client
            self._client = CFSAPIClient(year=year)

            if reset:
                if verbose:
                    print("Clearing existing CFS data...")
                self._clear_cfs_data(session, year)
                session.flush()

            # Load lookups
            self._load_state_lookup(session)
            self._load_county_lookup(session)
            self._load_hierarchy(session, year)

            if not self._hierarchy:
                stats.errors.append(
                    "No geographic hierarchy data found. Run GeographicHierarchyLoader first."
                )
                return stats

            # Load SCTG dimension
            sctg_count = self._load_sctg_dimension(session)
            stats.dimensions_loaded["dim_sctg_commodity"] = sctg_count

            # Load data source
            self._load_data_source(session, year)
            stats.dimensions_loaded["dim_data_source"] = 1

            session.flush()

            # Fetch and disaggregate flows
            flow_count = self._load_disaggregated_flows(session, year, verbose)
            stats.facts_loaded["fact_commodity_flow"] = flow_count
            stats.api_calls = 1  # Single API call for all state flows

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

    def _clear_cfs_data(self, session: Session, year: int) -> None:
        """Clear existing CFS data for the specified year."""
        session.query(FactCommodityFlow).filter(FactCommodityFlow.year == year).delete(
            synchronize_session=False
        )

    def _load_state_lookup(self, session: Session) -> None:
        """Load state FIPS to ID mapping."""
        for row in session.execute(select(DimState.state_fips, DimState.state_id)):
            self._state_fips_to_id[row.state_fips] = row.state_id

    def _load_county_lookup(self, session: Session) -> None:
        """Load county FIPS to ID mapping."""
        for row in session.execute(select(DimCounty.fips, DimCounty.county_id)):
            self._county_fips_to_id[row.fips] = row.county_id

    def _load_hierarchy(self, session: Session, year: int) -> None:
        """Load geographic hierarchy with allocation weights."""
        query = select(
            DimGeographicHierarchy.state_id,
            DimGeographicHierarchy.county_id,
            DimGeographicHierarchy.population_weight,
            DimGeographicHierarchy.employment_weight,
        ).where(DimGeographicHierarchy.source_year == year)

        self._hierarchy = defaultdict(list)
        for row in session.execute(query):
            self._hierarchy[row.state_id].append(
                (row.county_id, row.population_weight, row.employment_weight)
            )
        self._hierarchy = dict(self._hierarchy)

    def _load_sctg_dimension(self, session: Session) -> int:
        """Load SCTG commodity dimension."""
        assert self._client is not None

        # Check for existing SCTG codes
        existing = {row.sctg_code for row in session.execute(select(DimSCTGCommodity.sctg_code))}

        count = 0
        for code, name in self._client.get_sctg_codes():
            if code in existing:
                # Get existing ID
                result = session.execute(
                    select(DimSCTGCommodity.sctg_id).where(DimSCTGCommodity.sctg_code == code)
                ).first()
                if result:
                    self._sctg_to_id[code] = result.sctg_id
                continue

            # Determine category based on SCTG code ranges
            category = self._get_sctg_category(code)
            strategic = self._get_strategic_value(code)

            sctg = DimSCTGCommodity(
                sctg_code=code,
                sctg_name=name,
                category=category,
                strategic_value=strategic,
            )
            session.add(sctg)
            session.flush()
            self._sctg_to_id[code] = sctg.sctg_id
            count += 1

        return count

    def _get_sctg_category(self, code: str) -> str:
        """Determine SCTG category from code."""
        code_int = int(code)
        if code_int <= 9:
            return "agriculture"
        elif code_int <= 19:
            return "mining"
        elif code_int <= 30:
            return "chemicals"
        elif code_int <= 40:
            return "manufacturing"
        else:
            return "other"

    def _get_strategic_value(self, code: str) -> str:
        """Determine strategic value from SCTG code."""
        # Critical: energy, base metals, chemicals
        critical_codes = {"15", "16", "17", "18", "19", "20", "32"}
        # High: food, machinery, electronics
        high_codes = {"02", "05", "07", "34", "35", "36"}

        if code in critical_codes:
            return "critical"
        elif code in high_codes:
            return "high"
        else:
            return "medium"

    def _load_data_source(self, session: Session, year: int) -> None:
        """Load data source dimension."""
        self._source_id = self._get_or_create_data_source(
            session,
            source_code=f"CFS_{year}",
            source_name=f"Census Commodity Flow Survey {year}",
            source_url=f"https://api.census.gov/data/{year}/cfsarea",
            source_agency="Census Bureau",
            source_year=year,
        )

    def _load_disaggregated_flows(
        self,
        session: Session,
        year: int,
        verbose: bool,
    ) -> int:
        """Load commodity flows disaggregated to county level.

        Fetches state-level flows and distributes to counties using
        geographic hierarchy weights.
        """
        assert self._client is not None
        assert self._source_id is not None

        if verbose:
            print("Fetching state-level commodity flows...")

        # Get all state flows
        flows = self._client.get_state_flows()

        if verbose:
            print(f"Retrieved {len(flows):,} state-level flow records")
            print("Disaggregating to county level...")

        count = 0
        flow_iter = tqdm(flows, desc="Disaggregating", disable=not verbose)

        for flow in flow_iter:
            # Get state IDs
            origin_state_id = self._state_fips_to_id.get(flow.origin_state_fips)
            dest_state_id = self._state_fips_to_id.get(flow.dest_state_fips)

            if not origin_state_id or not dest_state_id:
                continue

            # Get SCTG ID
            sctg_id = self._sctg_to_id.get(flow.sctg_code)
            if not sctg_id:
                continue

            # Get hierarchy for both states
            origin_counties = self._hierarchy.get(origin_state_id, [])
            dest_counties = self._hierarchy.get(dest_state_id, [])

            if not origin_counties or not dest_counties:
                continue

            # Disaggregate flow to county pairs
            # Use employment weight for origin, population weight for destination
            for o_county_id, _, o_emp_weight in origin_counties:
                for d_county_id, d_pop_weight, _ in dest_counties:
                    # Combined weight = origin_employment * dest_population
                    combined_weight = o_emp_weight * d_pop_weight

                    # Skip negligible flows
                    if combined_weight < Decimal("0.0000001"):
                        continue

                    # Allocate flow values
                    value = None
                    if flow.value_millions is not None:
                        value = Decimal(str(flow.value_millions)) * combined_weight

                    tons = None
                    if flow.tons_thousands is not None:
                        tons = Decimal(str(flow.tons_thousands)) * combined_weight

                    tmiles = None
                    if flow.ton_miles_millions is not None:
                        tmiles = Decimal(str(flow.ton_miles_millions)) * combined_weight

                    fact = FactCommodityFlow(
                        origin_county_id=o_county_id,
                        dest_county_id=d_county_id,
                        sctg_id=sctg_id,
                        source_id=self._source_id,
                        year=year,
                        value_millions=value,
                        tons_thousands=tons,
                        ton_miles_millions=tmiles,
                        mode_code=flow.mode_code,
                    )
                    session.add(fact)
                    count += 1

                    # Batch flush for performance
                    if count % self.config.batch_size == 0:
                        session.flush()

        session.flush()
        return count


__all__ = ["CFSLoader"]
