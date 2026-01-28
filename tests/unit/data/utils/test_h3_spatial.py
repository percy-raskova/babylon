"""Unit tests for H3-based spatial helpers."""

from __future__ import annotations

import h3

from babylon.data.utils.h3_spatial import (
    CountyH3Index,
    geometry_to_latlon,
    web_mercator_to_wgs84,
)


def test_web_mercator_to_wgs84_origin() -> None:
    lat, lon = web_mercator_to_wgs84(0.0, 0.0)
    assert abs(lat) < 1e-6
    assert abs(lon) < 1e-6


def test_geometry_to_latlon_point_wgs84() -> None:
    geometry = {"x": -122.4, "y": 37.8}
    lat, lon = geometry_to_latlon(geometry, {"wkid": 4326})
    assert abs(lat - 37.8) < 1e-6
    assert abs(lon + 122.4) < 1e-6


def test_geometry_to_latlon_point_mercator() -> None:
    geometry = {"x": 0.0, "y": 0.0}
    lat, lon = geometry_to_latlon(geometry, {"wkid": 3857})
    assert abs(lat) < 1e-6
    assert abs(lon) < 1e-6


def test_geometry_to_latlon_polygon_centroid() -> None:
    geometry = {
        "rings": [
            [
                [-122.5, 37.7],
                [-122.5, 37.9],
                [-122.3, 37.9],
                [-122.3, 37.7],
                [-122.5, 37.7],
            ]
        ]
    }
    lat, lon = geometry_to_latlon(geometry, {"wkid": 4326})
    assert abs(lat - 37.8) < 1e-3
    assert abs(lon + 122.4) < 1e-3


def test_county_h3_index_resolve_latlon() -> None:
    index = CountyH3Index(resolution=6)
    cell = h3.latlng_to_cell(37.8, -122.4, 6)
    index.cell_to_fips[cell] = "06075"
    assert index.resolve_latlon(37.8, -122.4) == "06075"


def test_county_h3_index_resolve_geometry() -> None:
    index = CountyH3Index(resolution=6)
    cell = h3.latlng_to_cell(37.8, -122.4, 6)
    index.cell_to_fips[cell] = "06075"
    geometry = {"x": -122.4, "y": 37.8}
    assert index.resolve_geometry(geometry, {"wkid": 4326}) == "06075"
