"""H3 hexagonal grid data loading infrastructure.

This module provides loaders for generating and persisting H3 hexagonal
cells from county geometries for efficient spatial joins.

H3 is a hierarchical hexagonal geospatial indexing system that enables:
- Fast point-in-polygon lookups without runtime spatial operations
- Consistent cell sizes for spatial aggregation
- Efficient storage of spatial relationships

Supports multi-resolution generation for different visualization scales:
- Resolution 3: ~12,393 km² per cell (~300 cells for CONUS - 50-state overview)
- Resolution 4: ~1,770 km² per cell (~3,000 cells - state-level view)
- Resolution 5: ~252 km² per cell (~38,000 cells - county-level view)

Usage:
    from babylon.data.h3 import H3GridLoader, DEFAULT_H3_RESOLUTIONS
    from babylon.data.reference.database import get_normalized_session_factory

    # Single resolution (backwards compatible)
    loader = H3GridLoader(resolution=5)
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)

    # Multiple resolutions (recommended for visualization)
    loader = H3GridLoader(resolutions=DEFAULT_H3_RESOLUTIONS)  # [3, 4, 5]
    with session_factory() as session:
        stats = loader.load(session)
"""

from babylon.data.h3.loader import (
    DEFAULT_H3_RESOLUTION,
    DEFAULT_H3_RESOLUTIONS,
    H3GridLoader,
    cell_to_latlon,
    generate_h3_cells,
    wkt_to_polygon,
)

__all__ = [
    "DEFAULT_H3_RESOLUTION",
    "DEFAULT_H3_RESOLUTIONS",
    "H3GridLoader",
    "cell_to_latlon",
    "generate_h3_cells",
    "wkt_to_polygon",
]
