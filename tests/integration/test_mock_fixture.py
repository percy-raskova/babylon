import json
from pathlib import Path

import pytest

FIXTURE_PATH = Path("web/game/fixtures/mock_map_data.json")


@pytest.fixture
def mock_fixture():
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def test_fixture_is_valid_geojson(mock_fixture):
    """Top-level keys: type, metadata, features."""
    assert "type" in mock_fixture
    assert mock_fixture["type"] == "FeatureCollection"
    assert "metadata" in mock_fixture
    assert "features" in mock_fixture
    assert isinstance(mock_fixture["features"], list)


def test_fixture_has_required_metadata(mock_fixture):
    """metadata contains tick, scenario, h3_resolution, available_metrics, bounds."""
    metadata = mock_fixture["metadata"]
    assert "tick" in metadata
    assert "scenario" in metadata
    assert "h3_resolution" in metadata
    assert "available_metrics" in metadata
    assert "bounds" in metadata


def test_all_features_have_required_properties(mock_fixture):
    """Every feature has all property keys from the schema."""
    required_keys = {
        "h3_index",
        "county_fips",
        "county_name",
        "profit_rate",
        "exploitation_rate",
        "occ",
        "imperial_rent",
        "heat",
        "org_presence",
        "dominant_class",
        "population",
    }
    for feature in mock_fixture["features"]:
        props = feature["properties"]
        assert required_keys.issubset(set(props.keys()))


def test_county_distribution(mock_fixture):
    """At least 10 hexes per county FIPS code."""
    from collections import Counter

    counts = Counter(f["properties"]["county_fips"] for f in mock_fixture["features"])
    assert counts.get("26163", 0) >= 10
    assert counts.get("26125", 0) >= 10
    assert counts.get("26099", 0) >= 10


def test_directional_realism(mock_fixture):
    """Mean profit_rate for Wayne < Macomb < Oakland."""
    from collections import defaultdict

    profits = defaultdict(list)
    for feature in mock_fixture["features"]:
        fips = feature["properties"]["county_fips"]
        profits[fips].append(feature["properties"]["profit_rate"])

    wayne_mean = sum(profits["26163"]) / len(profits["26163"])
    macomb_mean = sum(profits["26099"]) / len(profits["26099"])
    oakland_mean = sum(profits["26125"]) / len(profits["26125"])

    assert wayne_mean < macomb_mean
    assert macomb_mean < oakland_mean
