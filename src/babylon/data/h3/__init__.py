"""H3 hexagonal grid data loading infrastructure.

This module provides loaders for generating and persisting H3 hexagonal
cells from county geometries for efficient spatial joins.

H3 is a hierarchical hexagonal geospatial indexing system that enables:
- Fast point-in-polygon lookups without runtime spatial operations
- Consistent cell sizes for spatial aggregation
- Efficient storage of spatial relationships

Usage:
    from babylon.data.h3 import H3GridLoader
    from babylon.data.reference.database import get_normalized_session_factory

    loader = H3GridLoader(resolution=5)
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from babylon.data.h3.loader import (
    H3GridLoader,
    cell_to_latlon,
    generate_h3_cells,
    wkt_to_polygon,
)

__all__ = [
    "H3GridLoader",
    "cell_to_latlon",
    "generate_h3_cells",
    "wkt_to_polygon",
]
