"""Natural Earth data reading infrastructure (Feature 036).

Provides read-only access to the Natural Earth SQLite database for
loading geographic features (lakes, roads, railroads, airports, ports,
geographic regions) within bounding boxes.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: FR-001 through FR-003
"""

from babylon.data.natural_earth.reader import (
    NE_DB_PATH,
    RESOURCE_FEATURECLA,
    AirportFeature,
    LakeFeature,
    NaturalEarthReader,
    PortFeature,
    RailroadFeature,
    RegionFeature,
    RoadFeature,
)

__all__ = [
    "AirportFeature",
    "LakeFeature",
    "NE_DB_PATH",
    "NaturalEarthReader",
    "PortFeature",
    "RESOURCE_FEATURECLA",
    "RailroadFeature",
    "RegionFeature",
    "RoadFeature",
]
