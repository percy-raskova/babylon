"""Spatial substrate generation for the tri-county area.

Feature: 026-tri-county-economic-substrate
Date: 2026-02-26

Generates H3 resolution 7 hex meshes from county boundary polygons,
assigns each hex to exactly one county, and builds the resolution
hierarchy (r7 -> r6 -> r5).

Uses ``generate_h3_cells()`` from the existing H3 loader directly
rather than modifying ``DEFAULT_H3_RESOLUTIONS`` (which would generate
~12M+ cells nationwide).

See Also:
    :mod:`babylon.data.h3.loader`: H3 cell generation functions.
    :mod:`babylon.economics.substrate.types`: HexGrid type definition.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import h3

from babylon.economics.substrate.h3_utils import generate_h3_cells, wkt_to_geometry
from babylon.economics.substrate.types import (
    HexEconomicState,
    HexGrid,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from babylon.economics.substrate.types import SubstrateConfig

logger = logging.getLogger(__name__)


class DefaultSpatialSubstrateSource:
    """Generate H3 hex meshes from county boundary polygons.

    Reads county geometries from DimCountyGeometry and uses
    ``h3.geo_to_cells`` (via ``generate_h3_cells``) to produce
    resolution 7 hex cells.
    """

    def __init__(self, session_factory: object) -> None:
        """Initialize with a session factory.

        Args:
            session_factory: Callable returning SQLAlchemy sessions.
        """
        self._session_factory = session_factory

    def generate_hex_mesh(self, county_fips_list: Sequence[str], resolution: int = 7) -> HexGrid:
        """Generate H3 hex mesh for given counties.

        Args:
            county_fips_list: FIPS codes for counties to cover.
            resolution: H3 resolution level (default 7).

        Returns:
            HexGrid with hex-to-county assignments and resolution hierarchy.

        Raises:
            ValueError: If county boundary data unavailable.
        """

        hexes: dict[str, HexEconomicState] = {}
        county_hex_ids: dict[str, frozenset[str]] = {}

        with self._session_factory() as session:  # type: ignore[operator]
            for fips in county_fips_list:
                county_cells = self._generate_county_hexes(session, fips, resolution)
                hex_id_set: set[str] = set()

                for h3_id in county_cells:
                    if h3_id in hexes:
                        # Skip duplicates from boundary overlap
                        continue

                    hexes[h3_id] = HexEconomicState(
                        h3_index=h3_id,
                        county_fips=fips,
                        constant_capital=0.0,
                        variable_capital=0.0,
                        surplus_value=0.0,
                        employment=0.0,
                        dept_shares=(0.25, 0.25, 0.25, 0.25),
                    )
                    hex_id_set.add(h3_id)

                county_hex_ids[fips] = frozenset(hex_id_set)
                logger.info(
                    "County %s: generated %d hexes at resolution %d",
                    fips,
                    len(hex_id_set),
                    resolution,
                )

        # Build resolution hierarchy
        res6_parents, res5_parents = _build_parent_maps(set(hexes.keys()))
        res6_children = _invert_parent_map(res6_parents)
        res5_children = _invert_parent_map(res5_parents)

        return HexGrid(
            hexes=hexes,
            county_hex_ids=county_hex_ids,
            res6_parents=res6_parents,
            res5_parents=res5_parents,
            res6_children=res6_children,
            res5_children=res5_children,
        )

    def get_county_boundary(self, county_fips: str) -> object:
        """Return Shapely polygon for county boundary.

        Args:
            county_fips: 5-digit county FIPS code.

        Returns:
            Shapely Polygon or MultiPolygon geometry, or None.
        """

        with self._session_factory() as session:  # type: ignore[operator]
            return _load_county_geometry(session, county_fips)

    def _generate_county_hexes(
        self, session: Session, county_fips: str, resolution: int
    ) -> set[str]:
        """Generate H3 cells for a single county.

        Args:
            session: SQLAlchemy session.
            county_fips: 5-digit FIPS code.
            resolution: H3 resolution.

        Returns:
            Set of H3 cell ID strings.

        Raises:
            ValueError: If county geometry is not available.
        """
        geometry = _load_county_geometry(session, county_fips)
        if geometry is None:
            msg = f"No geometry available for county {county_fips}"
            raise ValueError(msg)

        return generate_h3_cells(geometry, resolution)


def _load_county_geometry(session: Session, county_fips: str) -> object:
    """Load county boundary geometry from database.

    Args:
        session: SQLAlchemy session.
        county_fips: 5-digit county FIPS code.

    Returns:
        Shapely geometry or None.
    """
    from babylon.reference.schema import DimCounty, DimCountyGeometry

    geom_row = (
        session.query(DimCountyGeometry)
        .join(DimCounty, DimCounty.county_id == DimCountyGeometry.county_id)
        .filter(DimCounty.fips == county_fips)
        .first()
    )

    if geom_row is None or not geom_row.geometry_wkt:
        return None

    return wkt_to_geometry(geom_row.geometry_wkt)


def _build_parent_maps(
    hex_ids: set[str],
) -> tuple[dict[str, str], dict[str, str]]:
    """Build resolution hierarchy parent maps.

    Args:
        hex_ids: Set of resolution 7 H3 cell IDs.

    Returns:
        Tuple of (res6_parents, res5_parents) dicts.
    """
    res6_parents: dict[str, str] = {}
    res5_parents: dict[str, str] = {}

    for h3_id in hex_ids:
        res6_parents[h3_id] = h3.cell_to_parent(h3_id, 6)
        res5_parents[h3_id] = h3.cell_to_parent(h3_id, 5)

    return res6_parents, res5_parents


def _invert_parent_map(
    parent_map: dict[str, str],
) -> dict[str, frozenset[str]]:
    """Invert a parent map to get children map.

    Args:
        parent_map: Mapping of child h3_id to parent h3_id.

    Returns:
        Mapping of parent h3_id to frozenset of child h3_ids.
    """
    children: dict[str, set[str]] = defaultdict(set)
    for child_id, parent_id in parent_map.items():
        children[parent_id].add(child_id)

    return {k: frozenset(v) for k, v in children.items()}


def generate_tri_county_mesh(config: SubstrateConfig) -> HexGrid:
    """Convenience function to generate the standard tri-county mesh.

    Requires a database session factory (uses ``get_normalized_session_factory``).

    Args:
        config: Substrate configuration with county FIPS list and resolution.

    Returns:
        HexGrid for the tri-county area.
    """
    from babylon.reference.database import get_normalized_session_factory

    session_factory = get_normalized_session_factory()
    source = DefaultSpatialSubstrateSource(session_factory)
    return source.generate_hex_mesh(
        county_fips_list=config.county_fips_list,
        resolution=config.h3_resolution,
    )


__all__ = [
    "DefaultSpatialSubstrateSource",
    "generate_tri_county_mesh",
]
