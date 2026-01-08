"""H3-based spatial join helpers for county resolution.

Source config: src/babylon/data/data_sources/county_boundaries.json
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import h3  # type: ignore[import-not-found]

from babylon.data.data_sources import (
    get_arcgis_out_fields,
    get_arcgis_return_geometry,
    get_arcgis_service_url,
)
from babylon.data.external.arcgis import ArcGISClient
from babylon.data.utils.fips_resolver import normalize_fips

logger = logging.getLogger(__name__)

COUNTY_BOUNDARIES_SERVICE_URL = get_arcgis_service_url("county_boundaries")
COUNTY_BOUNDARIES_OUT_FIELDS = get_arcgis_out_fields("county_boundaries")
COUNTY_BOUNDARIES_RETURN_GEOMETRY = get_arcgis_return_geometry("county_boundaries")

DEFAULT_H3_RESOLUTION = 4

_WEB_MERCATOR_RADIUS = 20037508.34


def web_mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator meters to WGS84 lat/lon."""
    lon = (x / _WEB_MERCATOR_RADIUS) * 180.0
    lat = (y / _WEB_MERCATOR_RADIUS) * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return lat, lon


def geometry_to_latlon(
    geometry: dict[str, Any] | None,
    spatial_reference: dict[str, Any] | None = None,
) -> tuple[float, float]:
    """Extract representative lat/lon from ArcGIS geometry."""
    if not geometry:
        return 0.0, 0.0

    wkid = (spatial_reference or {}).get("wkid") or (spatial_reference or {}).get("latestWkid")

    def to_latlon(x: float, y: float) -> tuple[float, float]:
        if wkid in {3857, 102100}:
            return web_mercator_to_wgs84(x, y)
        return y, x

    if "x" in geometry and "y" in geometry:
        return to_latlon(float(geometry["x"]), float(geometry["y"]))

    if "points" in geometry and geometry["points"]:
        x, y = geometry["points"][0]
        return to_latlon(float(x), float(y))

    if "paths" in geometry and geometry["paths"]:
        coords = geometry["paths"][0]
        if coords:
            x, y = coords[len(coords) // 2]
            return to_latlon(float(x), float(y))

    if "rings" in geometry and geometry["rings"]:
        ring = geometry["rings"][0]
        if ring:
            lat, lon = _ring_centroid_latlon(ring, to_latlon)
            return lat, lon

    return 0.0, 0.0


def _ring_centroid_latlon(
    ring: Iterable[Iterable[float]],
    to_latlon: Callable[[float, float], tuple[float, float]],
) -> tuple[float, float]:
    coords = [(float(x), float(y)) for x, y in ring]
    if len(coords) < 3:
        x, y = coords[0]
        return to_latlon(x, y)

    area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        step = x0 * y1 - x1 * y0
        area += step
        cx += (x0 + x1) * step
        cy += (y0 + y1) * step

    if abs(area) < 1e-9:
        avg_x = sum(x for x, _ in coords) / len(coords)
        avg_y = sum(y for _, y in coords) / len(coords)
        return to_latlon(avg_x, avg_y)

    area *= 0.5
    cx /= 6.0 * area
    cy /= 6.0 * area
    return to_latlon(cx, cy)


def _rings_to_cells(
    rings: Iterable[list[list[float]]],
    resolution: int,
) -> set[str]:
    cells: set[str] = set()
    for ring in rings:
        polygon = {"type": "Polygon", "coordinates": [ring]}
        try:
            cells.update(h3.geo_to_cells(polygon, resolution))
        except Exception as exc:
            logger.debug("Failed to polyfill ring: %s", exc)
    return cells


@dataclass
class CountyH3Index:
    """H3 cell -> county FIPS lookup for spatial joins."""

    resolution: int = DEFAULT_H3_RESOLUTION
    cell_to_fips: dict[str, str] = field(default_factory=dict)

    def resolve_latlon(self, lat: float, lon: float) -> str | None:
        if not self.cell_to_fips:
            return None
        cell = h3.latlng_to_cell(lat, lon, self.resolution)
        return self.cell_to_fips.get(cell)

    def resolve_geometry(
        self,
        geometry: dict[str, Any] | None,
        spatial_reference: dict[str, Any] | None = None,
    ) -> str | None:
        if not geometry:
            return None
        lat, lon = geometry_to_latlon(geometry, spatial_reference)
        return self.resolve_latlon(lat, lon)

    @classmethod
    def from_arcgis(
        cls,
        resolution: int = DEFAULT_H3_RESOLUTION,
        service_url: str = COUNTY_BOUNDARIES_SERVICE_URL,
    ) -> CountyH3Index:
        index = cls(resolution=resolution)
        index._build_from_arcgis(service_url)
        return index

    def _build_from_arcgis(self, service_url: str) -> None:
        client = ArcGISClient(service_url)
        try:
            info = client.get_service_info()
            spatial_reference = info.get("spatialReference", {"wkid": 4326})
            features = client.query_all(
                out_fields=COUNTY_BOUNDARIES_OUT_FIELDS,
                return_geometry=COUNTY_BOUNDARIES_RETURN_GEOMETRY,
            )
            for feature in features:
                fips_raw = feature.attributes.get("FIPS")
                fips = normalize_fips(fips_raw, 5, min_length=4)
                if not fips:
                    continue
                geometry = feature.geometry
                if not geometry:
                    continue
                rings = geometry.get("rings") if isinstance(geometry, dict) else None
                if not rings:
                    continue
                cells = _rings_to_cells(rings, self.resolution)
                if not cells:
                    lat, lon = geometry_to_latlon(geometry, spatial_reference)
                    cell = h3.latlng_to_cell(lat, lon, self.resolution)
                    self.cell_to_fips.setdefault(cell, fips)
                    continue
                for cell in cells:
                    self.cell_to_fips.setdefault(cell, fips)
        finally:
            client.close()


@lru_cache(maxsize=4)
def get_county_h3_index(
    resolution: int = DEFAULT_H3_RESOLUTION,
) -> CountyH3Index:
    """Return cached county H3 index built from ArcGIS boundaries."""
    return CountyH3Index.from_arcgis(resolution=resolution)


__all__ = [
    "COUNTY_BOUNDARIES_SERVICE_URL",
    "COUNTY_BOUNDARIES_OUT_FIELDS",
    "COUNTY_BOUNDARIES_RETURN_GEOMETRY",
    "CountyH3Index",
    "DEFAULT_H3_RESOLUTION",
    "geometry_to_latlon",
    "get_county_h3_index",
    "web_mercator_to_wgs84",
]
