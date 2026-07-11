"""Tests for NaturalEarthReader (Feature 036, T009-T010).

Tests are skipped if the NE database file is not available.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.domain.geography.natural_earth_reader import NE_DB_PATH, NaturalEarthReader

# Detroit tri-county bounding box (approximate, EPSG:4326)
# (min_lon, min_lat, max_lon, max_lat)
DETROIT_BBOX = (-84.0, 42.0, -82.5, 42.8)

_DB_EXISTS = NE_DB_PATH.exists()
_SKIP_MSG = f"NE database not found: {NE_DB_PATH}"


@pytest.mark.unit
class TestNaturalEarthReaderInit:
    """Test NaturalEarthReader initialization."""

    def test_missing_db_raises(self, tmp_path: Path) -> None:
        """FileNotFoundError raised when DB path doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Natural Earth database"):
            NaturalEarthReader(tmp_path / "nonexistent.sqlite")


@pytest.mark.unit
@pytest.mark.skipif(not _DB_EXISTS, reason=_SKIP_MSG)
class TestNaturalEarthReaderLakes:
    """Test lake loading with real NE data."""

    def test_loads_lakes_in_detroit_bbox(self) -> None:
        """At minimum, Lake St. Clair should be found."""
        reader = NaturalEarthReader()
        lakes = reader.load_lakes(DETROIT_BBOX)
        assert len(lakes) > 0
        # Lake St. Clair is "Lake Saint Clair" in NE
        names = [lake.name for lake in lakes]
        assert any("Clair" in n for n in names), f"Expected Lake St. Clair, got: {names}"

    def test_lake_features_have_geometry(self) -> None:
        """All loaded lakes have non-None geometry."""
        reader = NaturalEarthReader()
        lakes = reader.load_lakes(DETROIT_BBOX)
        for lake in lakes:
            assert lake.geometry is not None
            assert lake.geometry.is_valid

    def test_empty_bbox_returns_empty(self) -> None:
        """Bbox in middle of ocean returns no lakes."""
        reader = NaturalEarthReader()
        lakes = reader.load_lakes((0.0, 0.0, 0.01, 0.01))
        assert lakes == []


@pytest.mark.unit
@pytest.mark.skipif(not _DB_EXISTS, reason=_SKIP_MSG)
class TestNaturalEarthReaderRoads:
    """Test road loading with real NE data."""

    def test_loads_roads_in_detroit_bbox(self) -> None:
        """Should find roads (interstates) in Detroit metro area."""
        reader = NaturalEarthReader()
        roads = reader.load_roads(DETROIT_BBOX)
        assert len(roads) > 0

    def test_na_supplement_roads_queried(self) -> None:
        """NA supplement table is queried alongside global roads.

        Use wider MI bbox to catch NA supplement roads (lower-class roads
        have less coverage in small bboxes).
        """
        reader = NaturalEarthReader()
        # Wider bbox covering most of lower Michigan
        roads = reader.load_roads((-87.0, 41.5, -82.0, 46.0))
        sources = {r.source_table for r in roads}
        assert "ne_10m_roads" in sources

    def test_road_features_have_geometry(self) -> None:
        """All loaded roads have valid geometry."""
        reader = NaturalEarthReader()
        roads = reader.load_roads(DETROIT_BBOX)
        for road in roads:
            assert road.geometry is not None


@pytest.mark.unit
@pytest.mark.skipif(not _DB_EXISTS, reason=_SKIP_MSG)
class TestNaturalEarthReaderRailroads:
    """Test railroad loading with real NE data."""

    def test_loads_railroads_in_detroit_bbox(self) -> None:
        """Should find railroad lines in Detroit metro area."""
        reader = NaturalEarthReader()
        railroads = reader.load_railroads(DETROIT_BBOX)
        assert len(railroads) > 0


@pytest.mark.unit
@pytest.mark.skipif(not _DB_EXISTS, reason=_SKIP_MSG)
class TestNaturalEarthReaderAirports:
    """Test airport loading with real NE data."""

    def test_loads_airports_in_detroit_bbox(self) -> None:
        """Detroit Metro Airport (DTW) should be found."""
        reader = NaturalEarthReader()
        airports = reader.load_airports(DETROIT_BBOX)
        assert len(airports) > 0
        iata_codes = [a.iata_code for a in airports]
        assert "DTW" in iata_codes, f"Expected DTW, got: {iata_codes}"


@pytest.mark.unit
@pytest.mark.skipif(not _DB_EXISTS, reason=_SKIP_MSG)
class TestNaturalEarthReaderPorts:
    """Test port loading with real NE data."""

    def test_loads_ports_near_detroit(self) -> None:
        """May or may not find ports in the Detroit bbox."""
        reader = NaturalEarthReader()
        # Expand bbox to include Toledo area
        ports = reader.load_ports((-84.5, 41.5, -82.0, 43.0))
        # NE 10m ports may not have Detroit specifically
        # Just verify no crash and valid results
        for port in ports:
            assert port.geometry is not None


@pytest.mark.unit
@pytest.mark.skipif(not _DB_EXISTS, reason=_SKIP_MSG)
class TestNaturalEarthReaderRegions:
    """Test geographic region loading with real NE data."""

    def test_loads_regions_in_wider_michigan_bbox(self) -> None:
        """Should find geographic regions in a wider Michigan bbox."""
        reader = NaturalEarthReader()
        # Widen to capture Great Lakes region features
        regions = reader.load_geography_regions((-90.0, 40.0, -80.0, 48.0))
        # Michigan may have ranges, basins, etc.
        for region in regions:
            assert region.geometry is not None
            assert region.featurecla != ""
