"""Tests for babylon.models.config.

TDD Red Phase: These tests define the contract for SimulationConfig.
SimulationConfig holds all formula coefficients and global parameters
for the simulation engine.

Sprint 3: SimulationConfig model for Phase 2 game loop.
"""

import pytest
from pydantic import ValidationError

from babylon.models.config import SimulationConfig

# =============================================================================
# DEFAULT VALUES TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigDefaults:
    """SimulationConfig should have sensible defaults for all parameters.

    These defaults match the formula-to-entity wiring specification
    in ai-docs/game-loop-architecture.yaml.
    """

    def test_extraction_efficiency_default(self) -> None:
        """Alpha (α) defaults to 0.8 for imperial rent calculation."""
        config = SimulationConfig()
        assert config.extraction_efficiency == 0.8

    def test_consciousness_sensitivity_default(self) -> None:
        """k defaults to 0.5 for consciousness drift calculation."""
        config = SimulationConfig()
        assert config.consciousness_sensitivity == 0.5

    def test_subsistence_threshold_default(self) -> None:
        """Poverty line defaults to 0.3 for acquiescence sigmoid."""
        config = SimulationConfig()
        assert config.subsistence_threshold == 0.3

    def test_survival_steepness_default(self) -> None:
        """Sigmoid sharpness defaults to 10.0."""
        config = SimulationConfig()
        assert config.survival_steepness == 10.0

    def test_repression_level_default(self) -> None:
        """State violence capacity defaults to 0.5."""
        config = SimulationConfig()
        assert config.repression_level == 0.5

    def test_initial_worker_wealth_default(self) -> None:
        """Starting wealth for periphery worker defaults to 0.5."""
        config = SimulationConfig()
        assert config.initial_worker_wealth == 0.5

    def test_initial_owner_wealth_default(self) -> None:
        """Starting wealth for core owner defaults to 0.5."""
        config = SimulationConfig()
        assert config.initial_owner_wealth == 0.5

    def test_loss_aversion_lambda_default(self) -> None:
        """Kahneman-Tversky lambda defaults to 2.25."""
        config = SimulationConfig()
        assert config.loss_aversion_lambda == 2.25

    def test_all_defaults_can_create_config(self) -> None:
        """Config can be created with all defaults."""
        config = SimulationConfig()
        assert config is not None


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigValidation:
    """SimulationConfig should validate all parameters against their constraints."""

    # Extraction efficiency (Coefficient: [0, 1])
    def test_extraction_efficiency_accepts_zero(self) -> None:
        """Zero extraction is valid (no imperial rent)."""
        config = SimulationConfig(extraction_efficiency=0.0)
        assert config.extraction_efficiency == 0.0

    def test_extraction_efficiency_accepts_one(self) -> None:
        """Full extraction is valid."""
        config = SimulationConfig(extraction_efficiency=1.0)
        assert config.extraction_efficiency == 1.0

    def test_extraction_efficiency_rejects_negative(self) -> None:
        """Negative extraction is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(extraction_efficiency=-0.1)

    def test_extraction_efficiency_rejects_greater_than_one(self) -> None:
        """Extraction > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(extraction_efficiency=1.5)

    # Consciousness sensitivity (Coefficient: [0, 1])
    def test_consciousness_sensitivity_accepts_zero(self) -> None:
        """Zero sensitivity means consciousness never changes."""
        config = SimulationConfig(consciousness_sensitivity=0.0)
        assert config.consciousness_sensitivity == 0.0

    def test_consciousness_sensitivity_rejects_negative(self) -> None:
        """Negative sensitivity is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(consciousness_sensitivity=-0.1)

    def test_consciousness_sensitivity_rejects_greater_than_one(self) -> None:
        """Sensitivity > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(consciousness_sensitivity=1.1)

    # Subsistence threshold (Currency: [0, inf))
    def test_subsistence_threshold_accepts_zero(self) -> None:
        """Zero subsistence is valid (no survival requirement)."""
        config = SimulationConfig(subsistence_threshold=0.0)
        assert config.subsistence_threshold == 0.0

    def test_subsistence_threshold_accepts_large(self) -> None:
        """Large subsistence threshold is valid."""
        config = SimulationConfig(subsistence_threshold=100.0)
        assert config.subsistence_threshold == 100.0

    def test_subsistence_threshold_rejects_negative(self) -> None:
        """Negative subsistence is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(subsistence_threshold=-0.1)

    # Survival steepness (positive float)
    def test_survival_steepness_accepts_small(self) -> None:
        """Small steepness (gradual sigmoid) is valid."""
        config = SimulationConfig(survival_steepness=1.0)
        assert config.survival_steepness == 1.0

    def test_survival_steepness_accepts_large(self) -> None:
        """Large steepness (sharp sigmoid) is valid."""
        config = SimulationConfig(survival_steepness=100.0)
        assert config.survival_steepness == 100.0

    def test_survival_steepness_rejects_zero(self) -> None:
        """Zero steepness is invalid (undefined sigmoid)."""
        with pytest.raises(ValidationError):
            SimulationConfig(survival_steepness=0.0)

    def test_survival_steepness_rejects_negative(self) -> None:
        """Negative steepness is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(survival_steepness=-1.0)

    # Repression level (Probability: [0, 1])
    def test_repression_level_accepts_zero(self) -> None:
        """Zero repression (no state violence) is valid."""
        config = SimulationConfig(repression_level=0.0)
        assert config.repression_level == 0.0

    def test_repression_level_accepts_one(self) -> None:
        """Full repression is valid."""
        config = SimulationConfig(repression_level=1.0)
        assert config.repression_level == 1.0

    def test_repression_level_rejects_negative(self) -> None:
        """Negative repression is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(repression_level=-0.1)

    def test_repression_level_rejects_greater_than_one(self) -> None:
        """Repression > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(repression_level=1.1)

    # Initial wealth values (Currency: [0, inf))
    def test_initial_worker_wealth_accepts_zero(self) -> None:
        """Destitute worker is valid."""
        config = SimulationConfig(initial_worker_wealth=0.0)
        assert config.initial_worker_wealth == 0.0

    def test_initial_worker_wealth_rejects_negative(self) -> None:
        """Negative wealth is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(initial_worker_wealth=-1.0)

    def test_initial_owner_wealth_accepts_zero(self) -> None:
        """Destitute owner is valid."""
        config = SimulationConfig(initial_owner_wealth=0.0)
        assert config.initial_owner_wealth == 0.0

    def test_initial_owner_wealth_rejects_negative(self) -> None:
        """Negative wealth is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(initial_owner_wealth=-1.0)

    # Loss aversion lambda (positive float, typically 2.25)
    def test_loss_aversion_accepts_typical(self) -> None:
        """Kahneman-Tversky value 2.25 is valid."""
        config = SimulationConfig(loss_aversion_lambda=2.25)
        assert config.loss_aversion_lambda == 2.25

    def test_loss_aversion_accepts_one(self) -> None:
        """Lambda = 1.0 (no loss aversion) is valid."""
        config = SimulationConfig(loss_aversion_lambda=1.0)
        assert config.loss_aversion_lambda == 1.0

    def test_loss_aversion_rejects_zero(self) -> None:
        """Lambda = 0 is invalid (undefined behavior)."""
        with pytest.raises(ValidationError):
            SimulationConfig(loss_aversion_lambda=0.0)

    def test_loss_aversion_rejects_negative(self) -> None:
        """Negative lambda is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(loss_aversion_lambda=-1.0)


# =============================================================================
# CUSTOMIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigCustomization:
    """SimulationConfig should allow custom parameter values."""

    def test_custom_extraction_efficiency(self) -> None:
        """Can set custom extraction efficiency."""
        config = SimulationConfig(extraction_efficiency=0.3)
        assert config.extraction_efficiency == 0.3

    def test_custom_repression_level(self) -> None:
        """Can set custom repression level."""
        config = SimulationConfig(repression_level=0.9)
        assert config.repression_level == 0.9

    def test_multiple_custom_values(self) -> None:
        """Can set multiple custom values at once."""
        config = SimulationConfig(
            extraction_efficiency=0.6,
            consciousness_sensitivity=0.3,
            subsistence_threshold=0.5,
            repression_level=0.7,
        )
        assert config.extraction_efficiency == 0.6
        assert config.consciousness_sensitivity == 0.3
        assert config.subsistence_threshold == 0.5
        assert config.repression_level == 0.7


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigSerialization:
    """SimulationConfig should serialize correctly for save/load."""

    def test_json_round_trip(self) -> None:
        """Config survives JSON round-trip."""
        original = SimulationConfig(
            extraction_efficiency=0.75,
            consciousness_sensitivity=0.4,
            repression_level=0.6,
        )
        json_str = original.model_dump_json()
        restored = SimulationConfig.model_validate_json(json_str)

        assert restored.extraction_efficiency == pytest.approx(0.75)
        assert restored.consciousness_sensitivity == pytest.approx(0.4)
        assert restored.repression_level == pytest.approx(0.6)

    def test_dict_round_trip(self) -> None:
        """Config survives dict round-trip."""
        original = SimulationConfig(extraction_efficiency=0.9)
        data = original.model_dump()
        restored = SimulationConfig.model_validate(data)

        assert restored.extraction_efficiency == original.extraction_efficiency

    def test_model_copy_with_update(self) -> None:
        """Config can be copied with updated values."""
        original = SimulationConfig()
        modified = original.model_copy(update={"repression_level": 0.9})

        assert original.repression_level == 0.5  # Unchanged
        assert modified.repression_level == 0.9  # Updated


# =============================================================================
# IMMUTABILITY TESTS (Optional - for frozen config)
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigImmutability:
    """SimulationConfig should be immutable during simulation."""

    def test_config_is_frozen(self) -> None:
        """Config fields cannot be modified after creation."""
        config = SimulationConfig()
        with pytest.raises(ValidationError):
            config.extraction_efficiency = 0.5  # type: ignore[misc]
