"""H3 grid persistence loader for 3NF schema.

Generates H3 hexagonal cells from county geometries (DimCountyGeometry)
and persists them to BridgeCountyH3 for efficient spatial joins.

Usage:
    from babylon.data.h3 import H3GridLoader
    from babylon.data.reference.database import get_normalized_session_factory

    loader = H3GridLoader(resolution=5)
    session_factory = get_normalized_session_factory()
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
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_H3_RESOLUTION = 5


def wkt_to_polygon(wkt: str | None) -> ShapelyPolygon | None:
    """Parse WKT string to Shapely polygon.

    Args:
        wkt: Well-Known Text polygon string.

    Returns:
        Shapely Polygon or None if invalid/empty.
    """
    if not wkt or not wkt.strip():
        return None

    from shapely import wkt as shapely_wkt  # type: ignore[import-untyped]

    try:
        geom = shapely_wkt.loads(wkt)
        return geom if geom.is_valid else None
    except Exception:
        return None


def generate_h3_cells(polygon: ShapelyPolygon, resolution: int) -> set[str]:
    """Generate H3 cells that cover a polygon.

    Args:
        polygon: Shapely polygon geometry.
        resolution: H3 resolution level (0-15).

    Returns:
        Set of H3 cell index strings.
    """
    # Convert shapely polygon to GeoJSON format for h3
    # Shapely coords are (x, y) = (lon, lat)
    # GeoJSON coordinates are also [lon, lat] format
    coords = list(polygon.exterior.coords)
    geojson_coords = [[x, y] for x, y in coords]

    geojson = {"type": "Polygon", "coordinates": [geojson_coords]}

    try:
        cells = h3.geo_to_cells(geojson, resolution)
        return set(cells)
    except Exception as exc:
        logger.debug("Failed to generate H3 cells: %s", exc)
        # Fall back to centroid cell
        centroid = polygon.centroid
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
    H3 hexagonal cells at the specified resolution, persisting them
    to BridgeCountyH3 for efficient spatial joins.

    At resolution 5 (~252 km² per cell), CONUS generates ~21K cells.
    At resolution 4 (~1770 km² per cell), CONUS generates ~3K cells.

    Attributes:
        config: LoaderConfig controlling operational settings.
        resolution: H3 resolution level (default 5).
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        resolution: int = DEFAULT_H3_RESOLUTION,
    ) -> None:
        """Initialize H3 grid loader.

        Args:
            config: LoaderConfig for operational settings.
            resolution: H3 resolution level (0-15, default 5).
        """
        super().__init__(config)
        self.resolution = resolution

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return []  # No dimensions, only bridge table

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [BridgeCountyH3]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Generate H3 grid from county geometries.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing H3 data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded records.
        """
        stats = LoadStats(source="h3_grid")

        if verbose:
            print(f"Generating H3 grid at resolution {self.resolution}...")

        try:
            # Clear existing H3 data if reset
            if reset:
                if verbose:
                    print("Clearing existing H3 data...")
                session.query(BridgeCountyH3).delete()
                session.commit()

            # Query all county geometries with WKT
            geometries = (
                session.query(DimCountyGeometry)
                .filter(DimCountyGeometry.geometry_wkt.isnot(None))
                .all()
            )

            if verbose:
                print(f"County geometries available: {len(geometries)}")

            if len(geometries) == 0:
                # Fall back to using centroids if no WKT
                geometries = session.query(DimCountyGeometry).all()
                if verbose:
                    print(f"Using centroids for {len(geometries)} counties (no WKT)")

            if len(geometries) == 0:
                logger.warning("No county geometries found - cannot generate H3 grid")
                stats.errors.append("DimCountyGeometry is empty - run TIGERCountyLoader first")
                return stats

            # Generate H3 cells for each county
            count = 0
            seen_cells: set[str] = set()

            for geom in tqdm(geometries, desc="H3 cells", disable=not verbose):
                cells = self._generate_cells_for_county(geom)

                for cell in cells:
                    # Skip if cell already assigned to another county
                    if cell in seen_cells:
                        continue

                    bridge = BridgeCountyH3(
                        h3_index=cell,
                        county_id=geom.county_id,
                        resolution=self.resolution,
                    )
                    session.add(bridge)
                    seen_cells.add(cell)
                    count += 1

                    if count % 1000 == 0:
                        session.flush()

            session.commit()
            stats.facts_loaded["bridge_county_h3"] = count

            if verbose:
                print(f"\nGenerated {count} H3 cells at resolution {self.resolution}")
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _generate_cells_for_county(self, geom: DimCountyGeometry) -> set[str]:
        """Generate H3 cells for a county geometry.

        Uses WKT polygon if available, otherwise falls back to centroid.

        Args:
            geom: DimCountyGeometry record.

        Returns:
            Set of H3 cell indices.
        """
        # Try WKT polygon first
        if geom.geometry_wkt:
            polygon = wkt_to_polygon(geom.geometry_wkt)
            if polygon:
                return generate_h3_cells(polygon, self.resolution)

        # Fall back to centroid
        lat = float(geom.centroid_lat)
        lon = float(geom.centroid_lon)
        cell = h3.latlng_to_cell(lat, lon, self.resolution)
        return {cell}


__all__ = [
    "H3GridLoader",
    "cell_to_latlon",
    "generate_h3_cells",
    "wkt_to_polygon",
]
