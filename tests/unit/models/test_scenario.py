"""Tests for ScenarioConfig model.

RED Phase: These tests will fail initially until ScenarioConfig is implemented.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# Import will fail in RED phase - this is expected
from babylon.models.scenario import ScenarioConfig


class TestScenarioConfigValidation:
    """Test ScenarioConfig Pydantic validation."""

    @pytest.mark.unit
    def test_create_with_defaults(self) -> None:
        """Test that ScenarioConfig can be created with just a name."""
        scenario = ScenarioConfig(name="default_scenario")

        assert scenario.name == "default_scenario"
        assert scenario.superwage_multiplier == 1.0  # Default multiplier
        assert scenario.solidarity_index == 0.5  # Default coefficient
        assert scenario.repression_capacity == 0.5  # Default coefficient

    @pytest.mark.unit
    def test_create_with_all_values(self) -> None:
        """Test that ScenarioConfig accepts all specified values."""
        scenario = ScenarioConfig(
            name="high_tension",
            superwage_multiplier=1.5,
            solidarity_index=0.8,
            repression_capacity=0.2,
        )

        assert scenario.name == "high_tension"
        assert scenario.superwage_multiplier == 1.5
        assert scenario.solidarity_index == 0.8
        assert scenario.repression_capacity == 0.2

    @pytest.mark.unit
    def test_name_required(self) -> None:
        """Test that name field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioConfig()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) and e["type"] == "missing" for e in errors)

    @pytest.mark.unit
    def test_solidarity_index_must_be_coefficient(self) -> None:
        """Test that solidarity_index must be in [0, 1] range."""
        # Valid at boundary
        scenario_low = ScenarioConfig(name="test", solidarity_index=0.0)
        assert scenario_low.solidarity_index == 0.0

        scenario_high = ScenarioConfig(name="test", solidarity_index=1.0)
        assert scenario_high.solidarity_index == 1.0

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            ScenarioConfig(name="test", solidarity_index=1.5)

        errors = exc_info.value.errors()
        assert any("solidarity_index" in str(e["loc"]) for e in errors)

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            ScenarioConfig(name="test", solidarity_index=-0.1)

        errors = exc_info.value.errors()
        assert any("solidarity_index" in str(e["loc"]) for e in errors)

    @pytest.mark.unit
    def test_repression_capacity_must_be_coefficient(self) -> None:
        """Test that repression_capacity must be in [0, 1] range."""
        # Valid at boundary
        scenario_low = ScenarioConfig(name="test", repression_capacity=0.0)
        assert scenario_low.repression_capacity == 0.0

        scenario_high = ScenarioConfig(name="test", repression_capacity=1.0)
        assert scenario_high.repression_capacity == 1.0

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            ScenarioConfig(name="test", repression_capacity=1.5)

        errors = exc_info.value.errors()
        assert any("repression_capacity" in str(e["loc"]) for e in errors)

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            ScenarioConfig(name="test", repression_capacity=-0.1)

        errors = exc_info.value.errors()
        assert any("repression_capacity" in str(e["loc"]) for e in errors)

    @pytest.mark.unit
    def test_superwage_multiplier_must_be_non_negative(self) -> None:
        """Test that superwage_multiplier must be >= 0 (multiplier cannot be negative)."""
        # Valid: zero superwage (no extraction)
        scenario_zero = ScenarioConfig(name="test", superwage_multiplier=0.0)
        assert scenario_zero.superwage_multiplier == 0.0

        # Valid: high superwage (aggressive extraction)
        scenario_high = ScenarioConfig(name="test", superwage_multiplier=2.5)
        assert scenario_high.superwage_multiplier == 2.5

        # Invalid: negative superwage
        with pytest.raises(ValidationError) as exc_info:
            ScenarioConfig(name="test", superwage_multiplier=-0.5)

        errors = exc_info.value.errors()
        assert any("superwage_multiplier" in str(e["loc"]) for e in errors)


class TestScenarioConfigSerialization:
    """Test ScenarioConfig JSON serialization."""

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        """Test that ScenarioConfig can be serialized to dict."""
        scenario = ScenarioConfig(
            name="test_scenario",
            superwage_multiplier=1.2,
            solidarity_index=0.3,
            repression_capacity=0.7,
        )

        data = scenario.model_dump()

        assert data["name"] == "test_scenario"
        assert data["superwage_multiplier"] == 1.2
        assert data["solidarity_index"] == 0.3
        assert data["repression_capacity"] == 0.7

    @pytest.mark.unit
    def test_from_dict(self) -> None:
        """Test that ScenarioConfig can be deserialized from dict."""
        data = {
            "name": "from_dict_scenario",
            "superwage_multiplier": 0.5,
            "solidarity_index": 0.9,
            "repression_capacity": 0.1,
        }

        scenario = ScenarioConfig.model_validate(data)

        assert scenario.name == "from_dict_scenario"
        assert scenario.superwage_multiplier == 0.5
        assert scenario.solidarity_index == 0.9
        assert scenario.repression_capacity == 0.1

    @pytest.mark.unit
    def test_round_trip_serialization(self) -> None:
        """Test that ScenarioConfig survives round-trip serialization."""
        original = ScenarioConfig(
            name="round_trip",
            superwage_multiplier=1.3,
            solidarity_index=0.4,
            repression_capacity=0.6,
        )

        # Convert to dict and back
        data = original.model_dump()
        restored = ScenarioConfig.model_validate(data)

        assert restored.name == original.name
        assert restored.superwage_multiplier == original.superwage_multiplier
        assert restored.solidarity_index == original.solidarity_index
        assert restored.repression_capacity == original.repression_capacity


class TestScenarioConfigImmutability:
    """Test ScenarioConfig immutability (frozen model)."""

    @pytest.mark.unit
    def test_is_frozen(self) -> None:
        """Test that ScenarioConfig is immutable (frozen)."""
        scenario = ScenarioConfig(name="frozen_test")

        with pytest.raises(ValidationError):
            scenario.name = "modified"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            scenario.rent_level = 2.0  # type: ignore[misc]


class TestScenarioConfigExport:
    """Test that ScenarioConfig is exported from babylon.models."""

    @pytest.mark.unit
    def test_import_from_models(self) -> None:
        """Test that ScenarioConfig can be imported from babylon.models."""
        from babylon.models import ScenarioConfig as ImportedScenarioConfig

        scenario = ImportedScenarioConfig(name="import_test")
        assert scenario.name == "import_test"
