"""TIGER county geometry loader for 3NF schema.

Loads county boundaries and centroids from the Census Bureau's TIGER/Line
shapefiles into the DimCountyGeometry table. This enables spatial operations
like H3 hex-to-county mapping and visualization.

Usage:
    from babylon.data.tiger import TIGERCountyLoader
    from babylon.data.reference.database import get_normalized_session_factory

    loader = TIGERCountyLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.reference.schema import DimCountyGeometry

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Shapefile location (relative to data directory)
TIGER_COUNTY_SHAPEFILE = "tiger/county/tl_2024_us_county.shp"


def calculate_centroid(geometry: BaseGeometry) -> tuple[float, float]:
    """Calculate centroid from a polygon or multipolygon geometry.

    Args:
        geometry: Shapely geometry (Polygon or MultiPolygon).

    Returns:
        Tuple of (latitude, longitude) in WGS84 coordinates.
    """
    centroid = geometry.centroid
    # Note: In shapefiles, x=longitude, y=latitude
    return (centroid.y, centroid.x)


def calculate_area_sq_km(geometry: BaseGeometry) -> float:
    """Calculate area in square kilometers from WGS84 geometry.

    Uses equal-area projection for accurate area calculation.

    Args:
        geometry: Shapely geometry in WGS84 coordinates.

    Returns:
        Area in square kilometers.
    """
    import pyproj  # type: ignore[import-not-found]
    from shapely.ops import transform  # type: ignore[import-untyped]

    # Project to equal-area CRS (US Albers Equal Area)
    # EPSG:5070 is NAD83/Conus Albers - good for CONUS
    # For Alaska/Hawaii, results will be approximate but acceptable
    wgs84 = pyproj.CRS("EPSG:4326")
    equal_area = pyproj.CRS("EPSG:5070")

    project = pyproj.Transformer.from_crs(wgs84, equal_area, always_xy=True).transform
    projected = transform(project, geometry)

    # Area in m², convert to km²
    return float(projected.area / 1_000_000)


def extract_county_fips(geoid: str | int) -> str:
    """Extract 5-digit FIPS code from TIGER GEOID.

    Args:
        geoid: TIGER GEOID value (may need zero-padding).

    Returns:
        5-digit FIPS code (e.g., "06001" for Alameda County, CA).
    """
    geoid_str = str(geoid)
    return geoid_str.zfill(5)


def geometry_to_wkt(geometry: BaseGeometry, store_wkt: bool = True) -> str | None:
    """Convert geometry to Well-Known Text string.

    Args:
        geometry: Shapely geometry object.
        store_wkt: If False, return None to skip WKT storage.

    Returns:
        WKT string or None if storage is disabled.
    """
    if not store_wkt:
        return None
    return str(geometry.wkt)


class TIGERCountyLoader(DataLoader):
    """Loader for TIGER county shapefiles into geometry table.

    Reads TIGER/Line county shapefiles and populates DimCountyGeometry
    with centroids, areas, and optionally full polygon WKT.

    Only loads geometries for counties that already exist in DimCounty
    (populated by CensusLoader or similar). This ensures FK integrity.

    Attributes:
        config: LoaderConfig controlling operational settings.
        data_dir: Path to data directory containing tiger/county/.
        store_wkt: If True, store full WKT geometry (large, ~500MB).
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        data_dir: Path | None = None,
        store_wkt: bool = False,
    ) -> None:
        """Initialize TIGER loader.

        Args:
            config: LoaderConfig for operational settings.
            data_dir: Path to data directory. Defaults to "data" in project root.
            store_wkt: If True, store full polygon WKT (default: False to save space).
        """
        super().__init__(config)
        self.data_dir = data_dir if data_dir is not None else Path("data")
        self.store_wkt = store_wkt

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimCountyGeometry]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return []  # No fact tables, only dimension extension

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load county geometries from TIGER shapefile.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing geometry data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded records.
        """
        import geopandas as gpd  # type: ignore[import-untyped]

        stats = LoadStats(source="tiger_county")

        if verbose:
            print("Loading TIGER county geometries...")

        try:
            # Clear existing geometry data if reset
            if reset:
                if verbose:
                    print("Clearing existing geometry data...")
                session.query(DimCountyGeometry).delete()
                session.commit()

            # Build county lookup from existing DimCounty
            county_lookup = self._build_county_lookup(session)
            if verbose:
                print(f"Counties available: {len(county_lookup)}")

            if len(county_lookup) == 0:
                logger.warning("No counties in DimCounty - cannot load geometries")
                stats.errors.append("DimCounty is empty - run CensusLoader first")
                return stats

            # Load shapefile
            shapefile_path = self.data_dir / TIGER_COUNTY_SHAPEFILE
            if not shapefile_path.exists():
                raise FileNotFoundError(f"TIGER shapefile not found: {shapefile_path}")

            if verbose:
                print(f"Reading shapefile: {shapefile_path}")

            gdf = gpd.read_file(shapefile_path)

            if verbose:
                print(f"Shapefile contains {len(gdf)} features")

            # Process each county geometry
            count = 0
            skipped = 0

            for _, row in tqdm(
                gdf.iterrows(), total=len(gdf), desc="Geometries", disable=not verbose
            ):
                fips = extract_county_fips(row["GEOID"])

                # Only load if county exists in DimCounty
                county_id = county_lookup.get(fips)
                if county_id is None:
                    skipped += 1
                    continue

                # Calculate centroid and area
                geometry = row.geometry
                lat, lon = calculate_centroid(geometry)
                area = calculate_area_sq_km(geometry)
                wkt = geometry_to_wkt(geometry, store_wkt=self.store_wkt)

                # Create geometry record
                geom = DimCountyGeometry(
                    county_id=county_id,
                    centroid_lat=Decimal(str(round(lat, 6))),
                    centroid_lon=Decimal(str(round(lon, 6))),
                    area_sq_km=Decimal(str(round(area, 4))) if area else None,
                    geometry_wkt=wkt,
                )
                session.add(geom)
                count += 1

                if count % 500 == 0:
                    session.flush()

            session.commit()
            stats.dimensions_loaded["dim_county_geometry"] = count
            stats.files_processed = 1

            if verbose:
                print(f"\nLoaded {count} county geometries")
                if skipped > 0:
                    print(f"Skipped {skipped} (not in DimCounty)")
                print(f"\n{stats}")

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats


__all__ = [
    "TIGERCountyLoader",
    "calculate_centroid",
    "calculate_area_sq_km",
    "extract_county_fips",
    "geometry_to_wkt",
]
