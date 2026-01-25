"""TIGER/Line shapefile data loading infrastructure.

This module provides loaders for Census Bureau TIGER/Line shapefiles:
- County boundaries and centroids for spatial operations
- Geographic features for H3 hex-to-county mapping

The data enables spatial aggregation and visualization by providing:
- County boundary polygons (WKT format)
- County centroids (lat/lon)
- County areas (sq km)

Usage:
    from babylon.data.tiger import TIGERCountyLoader
    from babylon.data.normalize.database import get_normalized_session_factory

    loader = TIGERCountyLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from babylon.data.tiger.loader import (
    TIGERCountyLoader,
    calculate_area_sq_km,
    calculate_centroid,
    extract_county_fips,
    geometry_to_wkt,
)

__all__ = [
    "TIGERCountyLoader",
    "calculate_centroid",
    "calculate_area_sq_km",
    "extract_county_fips",
    "geometry_to_wkt",
]
