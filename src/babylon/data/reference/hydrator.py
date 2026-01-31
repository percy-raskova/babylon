"""MVP Simulation Engine hydrator for SQLite reference data.

This module provides hydration functions to initialize simulation state from
the reference database (marxist-data-3NF.sqlite). It bridges the gap between
raw federal statistical data and simulation-ready TerritoryState objects.

Key Functions:
    - query_counties: Fetch county metadata from dim_county
    - query_hex_claims: Fetch H3 cells from bridge_county_h3
    - compute_initial_profit_rate: Calculate profit_rate from QCEW/BEA data
    - hydrate_territories: Create TerritoryState objects from database

See Also:
    - research.md#3. SQLite Reference Database Schema
    - research.md#4. Economics Hydrator
    - plan.md#Hydration Flow
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from babylon.data.reference.database import get_reference_session
from babylon.data.reference.schema import BridgeCountyH3, DimCounty
from babylon.models.snapshots import HexState, TerritoryState

logger = logging.getLogger(__name__)


@dataclass
class CountyInfo:
    """County metadata from dim_county."""

    county_id: int
    fips: str
    county_name: str


def query_counties(
    fips_codes: list[str],
    session: Session | None = None,
) -> dict[str, CountyInfo]:
    """Fetch county metadata from dim_county.

    Args:
        fips_codes: List of 5-digit FIPS codes to fetch.
        session: Optional existing session. If None, creates a new one.

    Returns:
        Dict mapping FIPS code to CountyInfo.

    Raises:
        ValueError: If any requested FIPS code is not found.
    """
    if not fips_codes:
        msg = "fips_codes list cannot be empty"
        raise ValueError(msg)

    # Deduplicate while preserving order
    unique_fips = list(dict.fromkeys(fips_codes))

    def _query(sess: Session) -> dict[str, CountyInfo]:
        stmt = select(DimCounty).where(DimCounty.fips.in_(unique_fips))
        results = sess.execute(stmt).scalars().all()

        county_map: dict[str, CountyInfo] = {}
        for county in results:
            county_map[county.fips] = CountyInfo(
                county_id=county.county_id,
                fips=county.fips,
                county_name=county.county_name,
            )

        # Check for missing counties
        missing = set(unique_fips) - set(county_map.keys())
        if missing:
            msg = f"Counties not found in database: {sorted(missing)}"
            raise ValueError(msg)

        return county_map

    if session is not None:
        return _query(session)

    with get_reference_session() as sess:
        return _query(sess)


def query_hex_claims(
    county_ids: list[int],
    session: Session | None = None,
) -> dict[int, set[str]]:
    """Fetch H3 cells from bridge_county_h3 for given counties.

    Args:
        county_ids: List of county_id values from dim_county.
        session: Optional existing session.

    Returns:
        Dict mapping county_id to set of H3 index strings.
        Counties with no H3 cells will have empty sets.
    """
    if not county_ids:
        return {}

    def _query(sess: Session) -> dict[int, set[str]]:
        stmt = select(BridgeCountyH3).where(BridgeCountyH3.county_id.in_(county_ids))
        results = sess.execute(stmt).scalars().all()

        hex_map: dict[int, set[str]] = {cid: set() for cid in county_ids}
        for h3_row in results:
            hex_map[h3_row.county_id].add(h3_row.h3_index)

        # Warn for counties with no hex cells
        for county_id, hexes in hex_map.items():
            if not hexes:
                logger.warning(
                    "County %d has no H3 cells in bridge_county_h3",
                    county_id,
                )

        return hex_map

    if session is not None:
        return _query(session)

    with get_reference_session() as sess:
        return _query(sess)


class StubBEASource:
    """Stub BEA source that returns None, letting DepartmentMapper provide defaults.

    The MarxianHydrator falls back to sector-level ratios from DepartmentMapper
    when the BEA source returns None.
    """

    def get_sv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Return None to fall back to DepartmentMapper defaults."""
        return None

    def get_cv_ratio(self, naics_code: str, year: int) -> float | None:  # noqa: ARG002
        """Return None to fall back to DepartmentMapper defaults."""
        return None


def compute_initial_profit_rate(
    fips: str,
    year: int,
) -> float:
    """Compute initial profit_rate from QCEW/BEA data.

    Uses MarxianHydrator to compute c, v, s, then derives profit_rate.

    profit_rate = s / (c + v)

    Where:
        s = surplus value (total across departments)
        c = constant capital (total across departments)
        v = variable capital (total across departments)

    Args:
        fips: 5-digit FIPS code.
        year: Data year.

    Returns:
        Profit rate in range [0.0, 1.0] (clamped if necessary).

    Raises:
        ValueError: If QCEW data is missing for the county.
    """
    # Lazy import to avoid circular dependencies
    from pathlib import Path

    from babylon.economics.adapters import SQLiteQCEWSource
    from babylon.economics.department_mapper import DepartmentMapper
    from babylon.economics.hydrator import MarxianHydrator

    # Locate NAICS-to-department mapping YAML
    economics_path = (
        Path(__file__).parent.parent.parent / "economics" / "data" / "naics_to_dept.yaml"
    )

    # Create data sources
    with get_reference_session() as session:
        qcew_source = SQLiteQCEWSource(session)
        bea_source = StubBEASource()  # Falls back to DepartmentMapper defaults
        dept_mapper = DepartmentMapper.from_yaml(economics_path)

        hydrator = MarxianHydrator(qcew_source, bea_source, dept_mapper)

        try:
            tensor = hydrator.hydrate(fips, year)
        except Exception as e:
            msg = f"Failed to hydrate county {fips} for year {year}: {e}"
            raise ValueError(msg) from e

        # Use the tensor's built-in profit_rate property
        profit_rate = tensor.profit_rate

        # Handle edge cases (inf, nan)
        if profit_rate != profit_rate or profit_rate == float("inf"):  # NaN or inf check
            logger.warning(
                "County %s has invalid profit_rate=%s, using default",
                fips,
                profit_rate,
            )
            return 0.04  # STUB: Default fallback

        # Clamp to valid range
        return max(0.0, min(1.0, profit_rate))


def hydrate_territories(
    fips_codes: list[str],
    year: int = 2022,
) -> tuple[dict[str, TerritoryState], dict[str, HexState]]:
    """Hydrate territories from SQLite reference database.

    This is the main entry point for initializing simulation state from
    the reference database.

    Args:
        fips_codes: List of 5-digit FIPS codes for counties to hydrate.
        year: Data year for QCEW/BEA data (default 2022).

    Returns:
        Tuple of (territories, hexes):
        - territories: Dict mapping territory_id (FIPS) to TerritoryState
        - hexes: Dict mapping h3_index to HexState

    Raises:
        ValueError: If fips_codes is empty or any county is not found.
    """
    if not fips_codes:
        msg = "fips_codes list cannot be empty"
        raise ValueError(msg)

    # Deduplicate while preserving order
    unique_fips = list(dict.fromkeys(fips_codes))

    with get_reference_session() as session:
        # Step 1: Fetch county metadata
        counties = query_counties(unique_fips, session)

        # Step 2: Fetch H3 cells
        county_ids = [counties[fips].county_id for fips in unique_fips]
        hex_claims_by_county = query_hex_claims(county_ids, session)

    # Step 3: Compute profit rates and build territories
    territories: dict[str, TerritoryState] = {}
    all_hexes: dict[str, HexState] = {}

    for fips in unique_fips:
        county = counties[fips]
        hex_indices = hex_claims_by_county.get(county.county_id, set())

        # Compute initial profit_rate from QCEW/BEA
        try:
            initial_r = compute_initial_profit_rate(fips, year)
        except ValueError as e:
            logger.error("Failed to compute profit_rate for %s: %s", fips, e)
            raise

        # Create TerritoryState
        territory = TerritoryState(
            territory_id=fips,
            controlling_polity=fips,  # MVP: controlling_polity = territory_id
            hex_claims=frozenset(hex_indices),
            tick=0,
            profit_rate=initial_r,
            equilibrium_r=initial_r,  # Territory-specific equilibrium
        )
        territories[fips] = territory

        # Create HexState for each hex
        for h3_idx in hex_indices:
            if h3_idx not in all_hexes:
                all_hexes[h3_idx] = HexState(h3_index=h3_idx)

    logger.info(
        "Hydrated %d territories with %d total hex cells",
        len(territories),
        len(all_hexes),
    )

    return territories, all_hexes


__all__ = [
    "CountyInfo",
    "compute_initial_profit_rate",
    "hydrate_territories",
    "query_counties",
    "query_hex_claims",
]
