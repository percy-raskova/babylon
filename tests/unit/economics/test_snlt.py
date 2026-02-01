"""Unit tests for SNLT configuration.

Tests for SNLTConfig model that provides year-specific labor-hour conversion factors.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.snlt import DEFAULT_SNLT_CONFIG, SNLTConfig


class TestSNLTConfig:
    """Tests for SNLTConfig Pydantic model."""

    def test_default_config_factor_one(self) -> None:
        """Default configuration has factor 1.0 (wage-proportional proxy)."""
        config = SNLTConfig()
        assert config.default_factor == 1.0
        assert config.factors == {}

    def test_get_factor_explicit_year(self) -> None:
        """get_factor returns explicit factor when year is in mapping."""
        config = SNLTConfig(
            factors={2015: 1.0, 2020: 0.95, 2025: 0.90},
            default_factor=1.0,
        )
        assert config.get_factor(2015) == 1.0
        assert config.get_factor(2020) == 0.95
        assert config.get_factor(2025) == 0.90

    def test_get_factor_fallback_to_default(self) -> None:
        """get_factor returns default_factor when year not in mapping."""
        config = SNLTConfig(
            factors={2020: 0.95},
            default_factor=1.0,
        )
        # Years not in mapping
        assert config.get_factor(2018) == 1.0
        assert config.get_factor(2021) == 1.0
        assert config.get_factor(1990) == 1.0

    def test_config_is_frozen(self) -> None:
        """SNLTConfig is immutable after creation."""
        config = SNLTConfig(default_factor=1.0)
        with pytest.raises(ValidationError):
            config.default_factor = 2.0  # type: ignore[misc]

    def test_rejects_zero_default_factor(self) -> None:
        """default_factor must be > 0.0 to prevent division by zero."""
        with pytest.raises(ValidationError) as exc_info:
            SNLTConfig(default_factor=0.0)
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_negative_default_factor(self) -> None:
        """default_factor must be > 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            SNLTConfig(default_factor=-0.5)
        assert "greater than 0" in str(exc_info.value)

    def test_rejects_zero_factor_in_mapping(self) -> None:
        """Factors in mapping must be > 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            SNLTConfig(factors={2020: 0.0})
        assert "must be > 0.0" in str(exc_info.value)

    def test_rejects_negative_factor_in_mapping(self) -> None:
        """Factors in mapping must be > 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            SNLTConfig(factors={2020: -0.5})
        assert "must be > 0.0" in str(exc_info.value)

    def test_productivity_increase_scenario(self) -> None:
        """Productivity increase means fewer hours per dollar (factor < 1.0)."""
        # 10% productivity increase from 2015 to 2020
        config = SNLTConfig(
            factors={2015: 1.0, 2020: 0.90},
            default_factor=1.0,
        )
        # Same $100 wage represents less labor-time in 2020
        wages = 100.0
        labor_2015 = wages * config.get_factor(2015)  # 100.0 hours
        labor_2020 = wages * config.get_factor(2020)  # 90.0 hours
        assert labor_2015 == 100.0
        assert labor_2020 == 90.0
        assert labor_2020 < labor_2015

    def test_serialization_roundtrip(self) -> None:
        """SNLTConfig can serialize to JSON and deserialize back."""
        config = SNLTConfig(
            factors={2015: 1.0, 2020: 0.95, 2025: 0.90},
            default_factor=1.0,
        )
        json_str = config.model_dump_json()
        restored = SNLTConfig.model_validate_json(json_str)
        assert restored.factors == config.factors
        assert restored.default_factor == config.default_factor
        assert restored.get_factor(2020) == 0.95


class TestDefaultSNLTConfig:
    """Tests for the DEFAULT_SNLT_CONFIG constant."""

    def test_default_config_exists(self) -> None:
        """DEFAULT_SNLT_CONFIG is available for import."""
        assert DEFAULT_SNLT_CONFIG is not None
        assert isinstance(DEFAULT_SNLT_CONFIG, SNLTConfig)

    def test_default_config_is_wage_proportional(self) -> None:
        """DEFAULT_SNLT_CONFIG uses factor 1.0 (no conversion)."""
        assert DEFAULT_SNLT_CONFIG.default_factor == 1.0
        assert DEFAULT_SNLT_CONFIG.factors == {}

    def test_default_config_any_year(self) -> None:
        """DEFAULT_SNLT_CONFIG returns 1.0 for any year."""
        for year in [1975, 2000, 2020, 2025, 2050]:
            assert DEFAULT_SNLT_CONFIG.get_factor(year) == 1.0
