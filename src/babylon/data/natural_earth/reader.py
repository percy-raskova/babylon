"""Natural Earth SQLite database reader (Feature 036).

Provides read-only access to the Natural Earth vector SQLite database
for loading geographic features within bounding boxes. Uses raw sqlite3
(not SQLAlchemy) because this is an external read-only data source.

Geometry is stored as WKB blobs in EPSG:4326. Shapely loads them via
``shapely.wkb.loads()``.

See Also:
    ``specs/036-infrastructure-topology/spec.md``: FR-001 through FR-003.
    :mod:`babylon.infrastructure.terrain`: DefaultTerrainClassifier.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from shapely import wkb  # type: ignore[import-untyped]
from shapely.geometry import box as shapely_box  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Default NE database path
NE_DB_PATH = Path(
    "/media/user/data/babylon-data/natural-earth/packages/natural_earth_vector.sqlite"
)

# featurecla values from ne_10m_geography_regions_polys that map to RESOURCE
RESOURCE_FEATURECLA = frozenset(
    {
        "Range/mtn",
        "Plateau",
        "Basin",
        "Delta",
        "Wetlands",
    }
)

# Maximum features per query (safety bound per CLAUDE.md rule 2)
_MAX_FEATURES = 10_000


# ---------------------------------------------------------------------------
# Feature dataclasses (ephemeral spatial objects — NOT Pydantic)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LakeFeature:
    """A lake polygon from NE 10m lakes tables."""

    ogc_fid: int
    name: str
    scalerank: int
    geometry: BaseGeometry = field(repr=False)


@dataclass(frozen=True)
class RoadFeature:
    """A road segment from NE 10m roads tables."""

    ogc_fid: int
    name: str
    prefix: str
    number: str
    road_class: str
    road_type: str
    expressway: int
    scalerank: int
    geometry: BaseGeometry = field(repr=False)
    source_table: str = ""


@dataclass(frozen=True)
class RailroadFeature:
    """A railroad segment from NE 10m railroads tables."""

    ogc_fid: int
    name: str
    scalerank: int
    mult_track: int
    geometry: BaseGeometry = field(repr=False)
    source_table: str = ""


@dataclass(frozen=True)
class AirportFeature:
    """An airport point from NE 10m airports table."""

    ogc_fid: int
    name: str
    iata_code: str
    scalerank: int
    natlscale: float
    type_: str
    geometry: BaseGeometry = field(repr=False)


@dataclass(frozen=True)
class PortFeature:
    """A port point from NE 10m ports table."""

    ogc_fid: int
    name: str
    scalerank: int
    natlscale: float
    geometry: BaseGeometry = field(repr=False)


@dataclass(frozen=True)
class RegionFeature:
    """A geographic region polygon from NE 10m geography_regions_polys."""

    ogc_fid: int
    name: str
    featurecla: str
    scalerank: int
    geometry: BaseGeometry = field(repr=False)


# ---------------------------------------------------------------------------
# Reader class
# ---------------------------------------------------------------------------


BBox = tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)


class NaturalEarthReader:
    """Read-only reader for the Natural Earth SQLite database.

    Loads geographic features within bounding boxes, combining global
    and North America supplement tables where appropriate.

    Args:
        db_path: Path to the NE SQLite database file.
    """

    def __init__(self, db_path: str | Path = NE_DB_PATH) -> None:
        self._db_path = Path(db_path)
        if not self._db_path.exists():
            msg = f"Natural Earth database not found: {self._db_path}"
            raise FileNotFoundError(msg)

    def _connect(self) -> sqlite3.Connection:
        """Open a read-only connection to the NE database."""
        uri = f"file:{self._db_path}?mode=ro"
        return sqlite3.connect(uri, uri=True)

    def load_lakes(self, bbox: BBox) -> list[LakeFeature]:
        """Load lake features from both global and NA supplement tables.

        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) bounding box.

        Returns:
            List of LakeFeature objects intersecting the bbox.
        """
        bbox_poly = shapely_box(*bbox)
        features: list[LakeFeature] = []

        conn = self._connect()
        try:
            for table in ("ne_10m_lakes", "ne_10m_lakes_north_america"):
                cursor = conn.execute(
                    f"SELECT ogc_fid, name, scalerank, GEOMETRY "  # noqa: S608
                    f"FROM {table} LIMIT {_MAX_FEATURES}"
                )
                for row in cursor:
                    ogc_fid, name, scalerank, geom_blob = row
                    if geom_blob is None:
                        continue
                    geom = wkb.loads(geom_blob)
                    if geom.intersects(bbox_poly):
                        features.append(
                            LakeFeature(
                                ogc_fid=ogc_fid,
                                name=name or "",
                                scalerank=scalerank or 0,
                                geometry=geom,
                            )
                        )
        finally:
            conn.close()

        logger.debug("Loaded %d lake features for bbox %s", len(features), bbox)
        return features

    def load_roads(self, bbox: BBox) -> list[RoadFeature]:
        """Load road features from both global and NA supplement tables.

        Global roads have ``type`` and ``expressway`` columns.
        NA supplement roads have ``class`` and ``type`` columns with
        different semantics (class=Interstate/State, type=road type).

        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) bounding box.

        Returns:
            List of RoadFeature objects intersecting the bbox.
        """
        bbox_poly = shapely_box(*bbox)
        features: list[RoadFeature] = []

        conn = self._connect()
        try:
            # Global roads table
            cursor = conn.execute(
                "SELECT ogc_fid, name, prefix, type, expressway, "
                f"scalerank, GEOMETRY FROM ne_10m_roads LIMIT {_MAX_FEATURES}"
            )
            for row in cursor:
                ogc_fid, name, prefix, road_type, expressway, scalerank, geom_blob = row
                if geom_blob is None:
                    continue
                geom = wkb.loads(geom_blob)
                if geom.intersects(bbox_poly):
                    features.append(
                        RoadFeature(
                            ogc_fid=ogc_fid,
                            name=name or "",
                            prefix=prefix or "",
                            number="",
                            road_class="",
                            road_type=road_type or "",
                            expressway=expressway or 0,
                            scalerank=scalerank or 0,
                            geometry=geom,
                            source_table="ne_10m_roads",
                        )
                    )

            # NA supplement roads table
            cursor = conn.execute(
                "SELECT ogc_fid, prefix, number, class, type, "
                f"scalerank, GEOMETRY FROM ne_10m_roads_north_america LIMIT {_MAX_FEATURES}"
            )
            for row in cursor:
                ogc_fid, prefix, number, road_class, road_type, scalerank, geom_blob = row
                if geom_blob is None:
                    continue
                geom = wkb.loads(geom_blob)
                if geom.intersects(bbox_poly):
                    features.append(
                        RoadFeature(
                            ogc_fid=ogc_fid,
                            name="",
                            prefix=prefix or "",
                            number=number or "",
                            road_class=road_class or "",
                            road_type=road_type or "",
                            expressway=0,
                            scalerank=scalerank or 0,
                            geometry=geom,
                            source_table="ne_10m_roads_north_america",
                        )
                    )
        finally:
            conn.close()

        logger.debug("Loaded %d road features for bbox %s", len(features), bbox)
        return features

    def load_railroads(self, bbox: BBox) -> list[RailroadFeature]:
        """Load railroad features from both global and NA supplement tables.

        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) bounding box.

        Returns:
            List of RailroadFeature objects intersecting the bbox.
        """
        bbox_poly = shapely_box(*bbox)
        features: list[RailroadFeature] = []

        conn = self._connect()
        try:
            # Global railroads — has mult_track
            cursor = conn.execute(
                "SELECT ogc_fid, featurecla, scalerank, mult_track, "
                f"GEOMETRY FROM ne_10m_railroads LIMIT {_MAX_FEATURES}"
            )
            for row in cursor:
                ogc_fid, name, scalerank, mult_track, geom_blob = row
                if geom_blob is None:
                    continue
                geom = wkb.loads(geom_blob)
                if geom.intersects(bbox_poly):
                    features.append(
                        RailroadFeature(
                            ogc_fid=ogc_fid,
                            name=name or "",
                            scalerank=scalerank or 0,
                            mult_track=mult_track or 0,
                            geometry=geom,
                            source_table="ne_10m_railroads",
                        )
                    )

            # NA supplement — no mult_track
            cursor = conn.execute(
                "SELECT ogc_fid, featurecla, scalerank, "
                f"GEOMETRY FROM ne_10m_railroads_north_america LIMIT {_MAX_FEATURES}"
            )
            for row in cursor:
                ogc_fid, name, scalerank, geom_blob = row
                if geom_blob is None:
                    continue
                geom = wkb.loads(geom_blob)
                if geom.intersects(bbox_poly):
                    features.append(
                        RailroadFeature(
                            ogc_fid=ogc_fid,
                            name=name or "",
                            scalerank=scalerank or 0,
                            mult_track=0,
                            geometry=geom,
                            source_table="ne_10m_railroads_north_america",
                        )
                    )
        finally:
            conn.close()

        logger.debug("Loaded %d railroad features for bbox %s", len(features), bbox)
        return features

    def load_airports(self, bbox: BBox) -> list[AirportFeature]:
        """Load airport features from the NE 10m airports table.

        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) bounding box.

        Returns:
            List of AirportFeature objects within the bbox.
        """
        bbox_poly = shapely_box(*bbox)
        features: list[AirportFeature] = []

        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT ogc_fid, name, iata_code, scalerank, natlscale, "
                f"type, GEOMETRY FROM ne_10m_airports LIMIT {_MAX_FEATURES}"
            )
            for row in cursor:
                ogc_fid, name, iata_code, scalerank, natlscale, type_, geom_blob = row
                if geom_blob is None:
                    continue
                geom = wkb.loads(geom_blob)
                if geom.intersects(bbox_poly):
                    features.append(
                        AirportFeature(
                            ogc_fid=ogc_fid,
                            name=name or "",
                            iata_code=iata_code or "",
                            scalerank=scalerank or 0,
                            natlscale=natlscale or 0.0,
                            type_=type_ or "",
                            geometry=geom,
                        )
                    )
        finally:
            conn.close()

        logger.debug("Loaded %d airport features for bbox %s", len(features), bbox)
        return features

    def load_ports(self, bbox: BBox) -> list[PortFeature]:
        """Load port features from the NE 10m ports table.

        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) bounding box.

        Returns:
            List of PortFeature objects within the bbox.
        """
        bbox_poly = shapely_box(*bbox)
        features: list[PortFeature] = []

        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT ogc_fid, name, scalerank, natlscale, "
                f"GEOMETRY FROM ne_10m_ports LIMIT {_MAX_FEATURES}"
            )
            for row in cursor:
                ogc_fid, name, scalerank, natlscale, geom_blob = row
                if geom_blob is None:
                    continue
                geom = wkb.loads(geom_blob)
                if geom.intersects(bbox_poly):
                    features.append(
                        PortFeature(
                            ogc_fid=ogc_fid,
                            name=name or "",
                            scalerank=scalerank or 0,
                            natlscale=natlscale or 0.0,
                            geometry=geom,
                        )
                    )
        finally:
            conn.close()

        logger.debug("Loaded %d port features for bbox %s", len(features), bbox)
        return features

    def load_geography_regions(self, bbox: BBox) -> list[RegionFeature]:
        """Load geographic region polygons from NE 10m.

        Loads from ``ne_10m_geography_regions_polys``. Features with
        ``featurecla`` in RESOURCE_FEATURECLA indicate resource-bearing
        terrain.

        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) bounding box.

        Returns:
            List of RegionFeature objects intersecting the bbox.
        """
        bbox_poly = shapely_box(*bbox)
        features: list[RegionFeature] = []

        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT ogc_fid, name, featurecla, scalerank, "
                "GEOMETRY FROM ne_10m_geography_regions_polys "
                f"LIMIT {_MAX_FEATURES}"
            )
            for row in cursor:
                ogc_fid, name, featurecla, scalerank, geom_blob = row
                if geom_blob is None:
                    continue
                geom = wkb.loads(geom_blob)
                if geom.intersects(bbox_poly):
                    features.append(
                        RegionFeature(
                            ogc_fid=ogc_fid,
                            name=name or "",
                            featurecla=featurecla or "",
                            scalerank=scalerank or 0,
                            geometry=geom,
                        )
                    )
        finally:
            conn.close()

        logger.debug("Loaded %d region features for bbox %s", len(features), bbox)
        return features
