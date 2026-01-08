"""Unit tests for ArcGIS source configuration loading."""

from __future__ import annotations

from babylon.data.data_sources import (
    get_arcgis_out_fields,
    get_arcgis_return_geometry,
    get_arcgis_service_url,
    get_data_source_meta,
    get_default_type,
    get_source_config,
    get_type_map,
)


def test_hifld_police_service_url_is_rapt_layer() -> None:
    """HIFLD police config should point at the RAPT layer."""
    url = get_arcgis_service_url("hifld_police")
    assert "Local_Law_Enforcement_Locations_RAPT" in url
    assert url.endswith("/FeatureServer/0")


def test_hifld_prisons_service_url_is_rapt_layer() -> None:
    """HIFLD prisons config should point at the RAPT layer."""
    url = get_arcgis_service_url("hifld_prisons")
    assert "Prison_Boundaries_RAPT" in url
    assert url.endswith("/FeatureServer/1")


def test_hifld_electric_out_fields_match_config() -> None:
    """HIFLD electric out_fields should be configured explicitly."""
    substations = get_arcgis_out_fields("hifld_electric", "substations")
    transmission = get_arcgis_out_fields("hifld_electric", "transmission")
    assert substations == "COUNTYFIPS,COUNTY,STATE,MAX_VOLT,MIN_VOLT,STATUS"
    assert transmission == "ID,VOLTAGE,STATUS,Shape__Length"


def test_mirta_service_fields_and_endpoint_present() -> None:
    """MIRTA config should include service fields and endpoint."""
    config = get_source_config("mirta")
    url = get_arcgis_service_url("mirta")
    assert "/mirta/FeatureServer/0" in url
    assert config.get("service_fields") == ["SERVICE", "BRANCH", "COMPONENT", "OPER_STAT"]


def test_hifld_police_type_map_defaults() -> None:
    """Type map and default types should load from config."""
    type_map = get_type_map("hifld_police")
    default_type = get_default_type("hifld_police")
    assert type_map["POLICE DEPARTMENT"][0] == "police_local"
    assert default_type[0] == "police_other"


def test_mirta_data_source_metadata_is_present() -> None:
    """Data source metadata should be present for MIRTA."""
    meta = get_data_source_meta("mirta")
    assert meta["code"] == "MIRTA_2024"
    assert meta["agency"] == "DoD OASD(S)"


def test_county_boundaries_arcgis_source_present() -> None:
    """County boundary ArcGIS source should be configured for H3 joins."""
    url = get_arcgis_service_url("county_boundaries")
    out_fields = get_arcgis_out_fields("county_boundaries")
    return_geometry = get_arcgis_return_geometry("county_boundaries")

    assert "USA_Counties_Generalized_Boundaries" in url
    assert url.endswith("/FeatureServer/0")
    assert out_fields == "FIPS"
    assert return_geometry is True
