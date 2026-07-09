"""Tests for babylon.models.config.

SimulationConfig is a run-scoped settings carrier. Its ~36 shadow coefficient
fields were removed in the src/ simplification sweep (2026-07) because they had
zero logic readers — the engine reads all coefficients from GameDefines
(``services.defines.*``). These tests now cover only the surviving contract:
the deterministic ``rng_seed``, immutability, and serialization round-trips.
"""

import pytest
from pydantic import ValidationError

from babylon.models.config import SimulationConfig

# =============================================================================
# DEFAULT / CUSTOMIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigRngSeed:
    """SimulationConfig exposes a deterministic run seed with a sensible default."""

    def test_default_rng_seed(self) -> None:
        """rng_seed defaults to 0 (Constitution III.7 deterministic default)."""
        config = SimulationConfig()
        assert config.rng_seed == 0

    def test_all_defaults_can_create_config(self) -> None:
        """Config can be created with all defaults."""
        config = SimulationConfig()
        assert config is not None

    def test_custom_rng_seed(self) -> None:
        """rng_seed accepts a custom integer (threaded from the GameSession)."""
        config = SimulationConfig(rng_seed=12345)
        assert config.rng_seed == 12345


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigSerialization:
    """SimulationConfig should serialize correctly for save/load."""

    def test_json_round_trip(self) -> None:
        """Config survives JSON round-trip."""
        original = SimulationConfig(rng_seed=42)
        json_str = original.model_dump_json()
        restored = SimulationConfig.model_validate_json(json_str)

        assert restored.rng_seed == 42

    def test_dict_round_trip(self) -> None:
        """Config survives dict round-trip."""
        original = SimulationConfig(rng_seed=7)
        data = original.model_dump()
        restored = SimulationConfig.model_validate(data)

        assert restored.rng_seed == original.rng_seed

    def test_model_copy_with_update(self) -> None:
        """Config can be copied with updated values."""
        original = SimulationConfig(rng_seed=1)
        modified = original.model_copy(update={"rng_seed": 2})

        assert original.rng_seed == 1  # Unchanged
        assert modified.rng_seed == 2  # Updated


# =============================================================================
# IMMUTABILITY TESTS (frozen config)
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigImmutability:
    """SimulationConfig should be immutable during simulation."""

    def test_config_is_frozen(self) -> None:
        """Config fields cannot be modified after creation."""
        config = SimulationConfig()
        with pytest.raises(ValidationError):
            config.rng_seed = 99  # type: ignore[misc]
