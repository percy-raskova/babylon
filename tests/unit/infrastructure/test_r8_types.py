"""Tests for R8 geographic substrate Pydantic models (Feature 036-R8).

TDD RED phase: These tests define the contract for HexR8State and
R8LinearFeature models before implementation exists.
"""

from __future__ import annotations

import h3
import pytest
from pydantic import ValidationError


class TestHexR8State:
    """Validate HexR8State model constraints."""

    def _make_r8(self, **overrides: object) -> object:
        """Create a HexR8State with sensible defaults."""
        from babylon.domain.geography.r8_types import HexR8State

        r7_hex = "872a100d2ffffff"
        r8_children = list(h3.cell_to_children(r7_hex, 8))
        r8_hex = r8_children[0]

        defaults: dict[str, object] = {
            "h3_index": r8_hex,
            "parent_h3": r7_hex,
            "county_fips": "26163",
            "terrain_type": "LAND",
            "water_fraction": 0.0,
            "elevation_m": None,
            "has_water_service": True,
            "has_sewer": True,
            "has_electric": True,
            "has_gas": True,
            "has_broadband": True,
        }
        defaults.update(overrides)
        return HexR8State(**defaults)

    def test_valid_construction(self) -> None:
        """A valid HexR8State can be constructed with correct fields."""
        state = self._make_r8()
        assert state.terrain_type == "LAND"
        assert state.water_fraction == 0.0
        assert state.elevation_m is None
        assert state.has_water_service is True

    def test_h3_index_must_be_resolution_8(self) -> None:
        """h3_index must be a valid H3 cell at resolution 8."""
        r7_hex = "872a100d2ffffff"  # This is resolution 7
        with pytest.raises(ValueError, match="resolution 8"):
            self._make_r8(h3_index=r7_hex)

    def test_parent_h3_must_be_resolution_7(self) -> None:
        """parent_h3 must be a valid H3 cell at resolution 7."""
        r7_hex = "872a100d2ffffff"
        r8_children = list(h3.cell_to_children(r7_hex, 8))
        with pytest.raises(ValueError, match="resolution 7"):
            self._make_r8(h3_index=r8_children[0], parent_h3=r8_children[1])

    def test_parent_must_match_cell_to_parent(self) -> None:
        """parent_h3 must equal h3.cell_to_parent(h3_index, 7)."""
        r7_a = "872a100d2ffffff"
        r7_b = "872a100d6ffffff"
        r8_child_of_a = list(h3.cell_to_children(r7_a, 8))[0]
        with pytest.raises(ValueError, match="parent"):
            self._make_r8(h3_index=r8_child_of_a, parent_h3=r7_b)

    def test_county_fips_must_be_5_digits(self) -> None:
        """county_fips must be exactly 5 digits."""
        with pytest.raises(ValueError, match="fips"):
            self._make_r8(county_fips="2616")  # Too short
        with pytest.raises(ValueError, match="fips"):
            self._make_r8(county_fips="261630")  # Too long
        with pytest.raises(ValueError, match="fips"):
            self._make_r8(county_fips="abcde")  # Non-numeric

    def test_terrain_type_must_be_valid(self) -> None:
        """terrain_type must be LAND, WATER, or RESOURCE."""
        with pytest.raises(ValueError):
            self._make_r8(terrain_type="DESERT")

    def test_water_fraction_bounds(self) -> None:
        """water_fraction must be in [0.0, 1.0]."""
        self._make_r8(water_fraction=0.0)  # Lower bound OK
        self._make_r8(water_fraction=1.0)  # Upper bound OK
        with pytest.raises(ValueError):
            self._make_r8(water_fraction=-0.1)
        with pytest.raises(ValueError):
            self._make_r8(water_fraction=1.1)

    def test_elevation_m_none_is_default(self) -> None:
        """elevation_m defaults to None (stub)."""
        state = self._make_r8()
        assert state.elevation_m is None

    def test_elevation_m_zero_is_valid(self) -> None:
        """0.0 is valid for elevation_m (sea level)."""
        state = self._make_r8(elevation_m=0.0)
        assert state.elevation_m == 0.0

    def test_model_is_frozen(self) -> None:
        """HexR8State should be immutable."""
        state = self._make_r8()
        with pytest.raises(ValidationError):
            state.terrain_type = "WATER"  # type: ignore[misc]


class TestR8LinearFeature:
    """Validate R8LinearFeature model constraints."""

    def _make_feature(self, **overrides: object) -> object:
        """Create an R8LinearFeature with sensible defaults."""
        from babylon.domain.geography.r8_types import R8LinearFeature

        r7_hex = "872a100d2ffffff"
        r8_hex = list(h3.cell_to_children(r7_hex, 8))[0]

        defaults: dict[str, object] = {
            "h3_index": r8_hex,
            "feature_type": "HIGHWAY",
            "feature_name": "I-75",
            "source_dataset": "NE_10M_ROADS",
            "source_feature_id": "12345",
        }
        defaults.update(overrides)
        return R8LinearFeature(**defaults)

    def test_valid_construction(self) -> None:
        """A valid R8LinearFeature can be constructed."""
        feature = self._make_feature()
        assert feature.feature_type == "HIGHWAY"
        assert feature.feature_name == "I-75"

    def test_feature_type_must_be_valid(self) -> None:
        """feature_type must be a valid R8FeatureType."""
        with pytest.raises(ValueError):
            self._make_feature(feature_type="TELEPORTER")

    def test_feature_name_can_be_none(self) -> None:
        """feature_name is optional."""
        feature = self._make_feature(feature_name=None)
        assert feature.feature_name is None

    def test_source_feature_id_can_be_none(self) -> None:
        """source_feature_id is optional."""
        feature = self._make_feature(source_feature_id=None)
        assert feature.source_feature_id is None

    def test_model_is_frozen(self) -> None:
        """R8LinearFeature should be immutable."""
        feature = self._make_feature()
        with pytest.raises(ValidationError):
            feature.feature_type = "RAIL"  # type: ignore[misc]

    def test_all_feature_types_valid(self) -> None:
        """All six R8FeatureType values should be constructible."""
        for ft in ("HIGHWAY", "ARTERIAL", "LOCAL_ROAD", "RAIL", "PIPELINE", "TRANSMISSION"):
            feature = self._make_feature(feature_type=ft)
            assert feature.feature_type == ft
