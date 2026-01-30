"""H3 grid persistence loader for 3NF schema.

Generates H3 hexagonal cells from county geometries (DimCountyGeometry)
and persists them to BridgeCountyH3 for efficient spatial joins.

Supports multiple resolutions for multi-scale geographic visualization:
- Resolution 3: ~12,393 km² per cell (~300 cells for CONUS - 50-state overview)
- Resolution 4: ~1,770 km² per cell (~3,000 cells - state-level view)
- Resolution 5: ~252 km² per cell (~38,000 cells - county-level view)

Usage:
    from babylon.data.h3 import H3GridLoader
    from babylon.data.reference.database import get_normalized_session_factory

    # Single resolution (backwards compatible)
    loader = H3GridLoader(resolution=5)
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)

    # Multiple resolutions
    loader = H3GridLoader(resolutions=[3, 4, 5])
    with session_factory() as session:
        stats = loader.load(session)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import h3
from tqdm import tqdm

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.reference.schema import BridgeCountyH3, DimCountyGeometry

if TYPE_CHECKING:
    from shapely.geometry import Polygon as ShapelyPolygon  # type: ignore[import-untyped]
    from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_H3_RESOLUTION = 5
DEFAULT_H3_RESOLUTIONS = [3, 4, 5]  # Multi-scale: 50-state, state, county views


def wkt_to_geometry(wkt: str | None) -> BaseGeometry | None:
    """Parse WKT string to Shapely geometry (Polygon or MultiPolygon).

    Args:
        wkt: Well-Known Text geometry string.

    Returns:
        Shapely geometry or None if invalid/empty.
    """
    if not wkt or not wkt.strip():
        return None

    from shapely import wkt as shapely_wkt  # type: ignore[import-untyped]

    try:
        geom = shapely_wkt.loads(wkt)
        return geom if geom.is_valid else None
    except Exception:
        return None


# Keep old name for backwards compatibility
wkt_to_polygon = wkt_to_geometry


def _generate_h3_cells_single(polygon: ShapelyPolygon, resolution: int) -> set[str]:
    """Generate H3 cells for a single polygon."""
    coords = list(polygon.exterior.coords)
    geojson_coords = [[x, y] for x, y in coords]
    geojson = {"type": "Polygon", "coordinates": [geojson_coords]}

    try:
        cells = h3.geo_to_cells(geojson, resolution)
        return set(cells)
    except Exception as exc:
        logger.debug("Failed to generate H3 cells: %s", exc)
        centroid = polygon.centroid
        cell = h3.latlng_to_cell(centroid.y, centroid.x, resolution)
        return {cell}


def generate_h3_cells(geometry: BaseGeometry, resolution: int) -> set[str]:
    """Generate H3 cells that cover a geometry (Polygon or MultiPolygon).

    Args:
        geometry: Shapely Polygon or MultiPolygon geometry.
        resolution: H3 resolution level (0-15).

    Returns:
        Set of H3 cell index strings.
    """
    # Handle MultiPolygon by iterating through component polygons
    if geometry.geom_type == "MultiPolygon":
        cells: set[str] = set()
        for poly in geometry.geoms:
            cells.update(_generate_h3_cells_single(poly, resolution))
        return cells
    elif geometry.geom_type == "Polygon":
        return _generate_h3_cells_single(geometry, resolution)
    else:
        # Fall back to centroid for other geometry types
        logger.warning("Unsupported geometry type: %s", geometry.geom_type)
        centroid = geometry.centroid
        cell = h3.latlng_to_cell(centroid.y, centroid.x, resolution)
        return {cell}


def cell_to_latlon(cell: str) -> tuple[float, float]:
    """Get the centroid lat/lon of an H3 cell.

    Args:
        cell: H3 cell index string.

    Returns:
        Tuple of (latitude, longitude).
    """
    lat, lon = h3.cell_to_latlng(cell)
    return (lat, lon)


class H3GridLoader(DataLoader):
    """Loader that generates H3 grid from county geometries.

    Reads county polygons from DimCountyGeometry (WKT) and generates
    H3 hexagonal cells at specified resolutions, persisting them
    to BridgeCountyH3 for efficient spatial joins.

    Supports multiple resolutions for multi-scale visualization:
    - Resolution 3: ~12,393 km² per cell (~300 cells for CONUS - 50-state overview)
    - Resolution 4: ~1,770 km² per cell (~3,000 cells - state-level view)
    - Resolution 5: ~252 km² per cell (~38,000 cells - county-level view)

    Attributes:
        config: LoaderConfig controlling operational settings.
        resolutions: List of H3 resolution levels to generate.
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        resolution: int | None = None,
        resolutions: list[int] | None = None,
    ) -> None:
        """Initialize H3 grid loader.

        Args:
            config: LoaderConfig for operational settings.
            resolution: Single H3 resolution level (0-15, backwards compatible).
            resolutions: List of H3 resolution levels to generate (takes precedence).
        """
        super().__init__(config)
        # Support both single resolution (backwards compat) and multiple resolutions
        if resolutions is not None:
            self.resolutions = resolutions
        elif resolution is not None:
            self.resolutions = [resolution]
        else:
            self.resolutions = [DEFAULT_H3_RESOLUTION]

    @property
    def resolution(self) -> int:
        """Return the first resolution (backwards compatibility).

        For single-resolution loaders, returns the configured resolution.
        For multi-resolution loaders, returns the first (coarsest) resolution.
        """
        return self.resolutions[0]

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return []  # No dimensions, only bridge table

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [BridgeCountyH3]

    def _get_geometries(self, session: Session, verbose: bool) -> list[DimCountyGeometry]:
        """Query county geometries, falling back to centroids if no WKT."""
        geometries = (
            session.query(DimCountyGeometry)
            .filter(DimCountyGeometry.geometry_wkt.isnot(None))
            .all()
        )

        if verbose:
            print(f"County geometries available: {len(geometries)}")

        if len(geometries) == 0:
            geometries = session.query(DimCountyGeometry).all()
            if verbose:
                print(f"Using centroids for {len(geometries)} counties (no WKT)")

        return geometries

    def _load_resolution(
        self,
        session: Session,
        geometries: list[DimCountyGeometry],
        resolution: int,
        verbose: bool,
    ) -> int:
        """Load H3 cells for a single resolution, returning count."""
        count = 0
        seen_cells: set[str] = set()

        for geom in tqdm(geometries, desc=f"H3 res {resolution}", disable=not verbose):
            cells = self._generate_cells_for_county(geom, resolution)

            for cell in cells:
                if cell in seen_cells:
                    continue

                bridge = BridgeCountyH3(
                    h3_index=cell,
                    county_id=geom.county_id,
                    resolution=resolution,
                )
                session.add(bridge)
                seen_cells.add(cell)
                count += 1

                if count % 1000 == 0:
                    session.flush()

        session.commit()
        return count

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Generate H3 grid from county geometries at multiple resolutions.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing H3 data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="h3_grid")
        resolutions_str = ", ".join(str(r) for r in self.resolutions)

        if verbose:
            print(f"Generating H3 grid at resolutions: {resolutions_str}...")

        try:
            if reset:
                if verbose:
                    print("Clearing existing H3 data...")
                session.query(BridgeCountyH3).delete()
                session.commit()

            geometries = self._get_geometries(session, verbose)

            if len(geometries) == 0:
                logger.warning("No county geometries found - cannot generate H3 grid")
                stats.errors.append("DimCountyGeometry is empty - run TIGERCountyLoader first")
                return stats

            total_count = 0
            for resolution in self.resolutions:
                if verbose:
                    print(f"\nProcessing resolution {resolution}...")

                count = self._load_resolution(session, geometries, resolution, verbose)

                if verbose:
                    print(f"  Resolution {resolution}: {count} cells")

                total_count += count

            stats.facts_loaded["bridge_county_h3"] = total_count

            if verbose:
                print(f"\nTotal: {total_count} H3 cells across resolutions {resolutions_str}")
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _generate_cells_for_county(self, geom: DimCountyGeometry, resolution: int) -> set[str]:
        """Generate H3 cells for a county geometry at a specific resolution.

        Uses WKT polygon if available, otherwise falls back to centroid.

        Args:
            geom: DimCountyGeometry record.
            resolution: H3 resolution level.

        Returns:
            Set of H3 cell indices.
        """
        # Try WKT polygon first
        if geom.geometry_wkt:
            polygon = wkt_to_polygon(geom.geometry_wkt)
            if polygon:
                return generate_h3_cells(polygon, resolution)

        # Fall back to centroid
        lat = float(geom.centroid_lat)
        lon = float(geom.centroid_lon)
        cell = h3.latlng_to_cell(lat, lon, resolution)
        return {cell}


__all__ = [
    "DEFAULT_H3_RESOLUTION",
    "DEFAULT_H3_RESOLUTIONS",
    "H3GridLoader",
    "cell_to_latlon",
    "generate_h3_cells",
    "wkt_to_polygon",
]
