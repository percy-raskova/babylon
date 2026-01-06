"""Geographic hierarchy loader for state-to-county allocation weights.

Populates DimGeographicHierarchy with weights derived from Census population
and QCEW employment data, enabling disaggregation of state-level external data
(e.g., Census CFS commodity flows) to county-level internal schema representation.

Usage:
    from babylon.data.geography import GeographicHierarchyLoader

    loader = GeographicHierarchyLoader()
    stats = loader.load(session)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from tqdm import tqdm

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.normalize.schema import (
    DimCounty,
    DimGeographicHierarchy,
    FactCensusEmployment,
    FactQcewAnnual,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class GeographicHierarchyLoader(DataLoader):
    """Loader for state-to-county geographic hierarchy with allocation weights.

    Derives allocation weights from existing data in the normalized database:
    - population_weight: From Census employment totals (proxy for population)
    - employment_weight: From QCEW annual employment data

    Weights are normalized per-state so they sum to 1.0 for each state,
    enabling proportional disaggregation of state-level data to counties.
    """

    def __init__(self, config: LoaderConfig | None = None) -> None:
        """Initialize geographic hierarchy loader."""
        super().__init__(config)

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables this loader populates."""
        return [DimGeographicHierarchy]

    def get_fact_tables(self) -> list[type]:
        """No fact tables - this populates a dimension."""
        return []

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load geographic hierarchy with allocation weights.

        Derives weights from Census and QCEW data already in the database.
        Uses Census year from config for population proxy, QCEW for employment.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing hierarchy data first.
            verbose: If True, print progress information.

        Returns:
            LoadStats with count of hierarchy records loaded.
        """
        stats = LoadStats(source="geography")
        # Use most recent year from census_years for hierarchy data
        source_year = self.config.census_years[-1] if self.config.census_years else 2022

        if verbose:
            print(f"Loading geographic hierarchy for year {source_year}")

        try:
            if reset:
                if verbose:
                    print("Clearing existing hierarchy data...")
                session.query(DimGeographicHierarchy).filter(
                    DimGeographicHierarchy.source_year == source_year
                ).delete(synchronize_session=False)
                session.flush()

            # Build state -> county mapping from existing data
            state_counties = self._get_state_county_mapping(session)

            if not state_counties:
                stats.errors.append("No state-county data found in database")
                return stats

            # Get population-proxy weights from Census employment
            pop_weights = self._get_population_weights(session, source_year)

            # Get employment weights from QCEW
            emp_weights = self._get_employment_weights(session, source_year)

            # Load hierarchy records
            count = self._load_hierarchy(
                session,
                state_counties,
                pop_weights,
                emp_weights,
                source_year,
                verbose,
            )
            stats.dimensions_loaded["dim_geographic_hierarchy"] = count
            stats.record_ingest("geography:dim_geographic_hierarchy", count)

            session.commit()

            if verbose:
                print(f"\n{stats}")

        except Exception as e:
            stats.record_api_error(e, context="geography:load")
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _get_state_county_mapping(self, session: Session) -> dict[int, list[tuple[int, str]]]:
        """Get mapping of state_id -> [(county_id, fips), ...].

        Returns:
            Dict mapping state_id to list of (county_id, fips) tuples.
        """
        query = select(DimCounty.state_id, DimCounty.county_id, DimCounty.fips).order_by(
            DimCounty.state_id
        )

        result: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for row in session.execute(query):
            result[row.state_id].append((row.county_id, row.fips))

        return dict(result)

    def _get_population_weights(self, session: Session, _year: int) -> dict[str, Decimal]:
        """Get population-proxy weights from Census employment totals.

        Uses total employment from FactCensusEmployment as a proxy for
        population since direct population isn't available in the schema.

        Args:
            session: Database session.
            _year: Source year (unused - uses all available data).

        Returns:
            Dict mapping county FIPS to raw weight value (not yet normalized).
        """
        # Sum employment across all categories per county
        query = (
            select(
                DimCounty.fips,
                func.sum(FactCensusEmployment.person_count).label("total_emp"),
            )
            .join(DimCounty, FactCensusEmployment.county_id == DimCounty.county_id)
            .group_by(DimCounty.fips)
        )

        weights: dict[str, Decimal] = {}
        for row in session.execute(query):
            if row.total_emp and row.total_emp > 0:
                weights[row.fips] = Decimal(str(row.total_emp))

        return weights

    def _get_employment_weights(self, session: Session, _year: int) -> dict[str, Decimal]:
        """Get employment weights from QCEW annual data.

        Uses total annual employment from FactQcewAnnual.

        Args:
            session: Database session.
            _year: Source year (unused - uses all available data).

        Returns:
            Dict mapping county FIPS to raw employment count.
        """
        # Get employment from QCEW - employment field contains count
        query = (
            select(
                DimCounty.fips,
                func.sum(FactQcewAnnual.employment).label("total_emp"),
            )
            .join(DimCounty, FactQcewAnnual.county_id == DimCounty.county_id)
            .group_by(DimCounty.fips)
        )

        weights: dict[str, Decimal] = {}
        for row in session.execute(query):
            if row.total_emp and row.total_emp > 0:
                weights[row.fips] = Decimal(str(row.total_emp))

        return weights

    def _normalize_weights(
        self,
        raw_weights: dict[str, Decimal],
        county_fips_list: list[str],
    ) -> dict[str, Decimal]:
        """Normalize weights to sum to 1.0 for a state.

        Args:
            raw_weights: Dict of county FIPS -> raw weight value.
            county_fips_list: List of county FIPS in this state.

        Returns:
            Dict of county FIPS -> normalized weight (0.0 to 1.0).
        """
        # Get weights for counties in this state
        state_total = Decimal("0")
        county_weights: dict[str, Decimal] = {}

        for fips in county_fips_list:
            weight = raw_weights.get(fips, Decimal("0"))
            county_weights[fips] = weight
            state_total += weight

        # Normalize to sum to 1.0
        if state_total > 0:
            normalized = {fips: weight / state_total for fips, weight in county_weights.items()}
        else:
            # Equal distribution if no data
            equal_weight = Decimal("1") / Decimal(len(county_fips_list))
            normalized = dict.fromkeys(county_fips_list, equal_weight)

        return normalized

    def _load_hierarchy(
        self,
        session: Session,
        state_counties: dict[int, list[tuple[int, str]]],
        pop_weights: dict[str, Decimal],
        emp_weights: dict[str, Decimal],
        source_year: int,
        verbose: bool,
    ) -> int:
        """Load hierarchy records with normalized weights.

        Args:
            session: Database session.
            state_counties: Mapping of state_id -> [(county_id, fips), ...].
            pop_weights: Raw population-proxy weights by county FIPS.
            emp_weights: Raw employment weights by county FIPS.
            source_year: Year for the weight calculations.
            verbose: Whether to show progress.

        Returns:
            Number of hierarchy records loaded.
        """
        count = 0
        state_iter = tqdm(
            state_counties.items(),
            desc="States",
            disable=not verbose,
        )

        for state_id, counties in state_iter:
            county_fips_list = [fips for _, fips in counties]

            # Normalize weights for this state
            norm_pop = self._normalize_weights(pop_weights, county_fips_list)
            norm_emp = self._normalize_weights(emp_weights, county_fips_list)

            for county_id, fips in counties:
                hierarchy = DimGeographicHierarchy(
                    state_id=state_id,
                    county_id=county_id,
                    population_weight=norm_pop.get(fips, Decimal("0")),
                    employment_weight=norm_emp.get(fips, Decimal("0")),
                    gdp_weight=None,  # Could derive from wages + employment
                    source_year=source_year,
                )
                session.add(hierarchy)
                count += 1

        session.flush()
        return count


__all__ = ["GeographicHierarchyLoader"]
