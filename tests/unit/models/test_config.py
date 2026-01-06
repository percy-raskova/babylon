"""Tests for babylon.models.config.

TDD Red Phase: These tests define the contract for SimulationConfig.
SimulationConfig holds all formula coefficients and global parameters
for the simulation engine.

Sprint 3: SimulationConfig model for Phase 2 game loop.

Refactored with pytest.parametrize for Phase 4 of Unit Test Health Improvement Plan.
"""

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

from babylon.models.config import SimulationConfig

# Aliases for readability
TC = TestConstants

# =============================================================================
# DEFAULT VALUES TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigDefaults:
    """SimulationConfig should have sensible defaults for all parameters.

    These defaults match the formula-to-entity wiring specification
    in ai-docs/game-loop-architecture.yaml.
    """

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("extraction_efficiency", TC.Probability.VERY_HIGH),
            ("consciousness_sensitivity", TC.Probability.MIDPOINT),
            ("subsistence_threshold", TC.Probability.MODERATE),
            ("survival_steepness", 10.0),
            ("repression_level", TC.Probability.MIDPOINT),
            ("initial_worker_wealth", TC.Wealth.WORKER_BASELINE),
            ("initial_owner_wealth", TC.Wealth.WORKER_BASELINE),
            ("loss_aversion_lambda", TC.Behavioral.LOSS_AVERSION),
        ],
        ids=[
            "extraction_efficiency",
            "consciousness_sensitivity",
            "subsistence_threshold",
            "survival_steepness",
            "repression_level",
            "initial_worker_wealth",
            "initial_owner_wealth",
            "loss_aversion_lambda",
        ],
    )
    def test_defaults(self, attr: str, expected: object) -> None:
        """SimulationConfig has correct default values."""
        config = SimulationConfig()
        assert getattr(config, attr) == expected

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

    @pytest.mark.parametrize(
        "field,valid_value",
        [
            ("extraction_efficiency", 0.0),
            ("extraction_efficiency", 1.0),
            ("consciousness_sensitivity", 0.0),
            ("subsistence_threshold", 0.0),
            ("subsistence_threshold", 100.0),
            ("survival_steepness", 1.0),
            ("survival_steepness", 100.0),
            ("repression_level", 0.0),
            ("repression_level", 1.0),
            ("initial_worker_wealth", 0.0),
            ("initial_owner_wealth", 0.0),
            ("loss_aversion_lambda", 2.25),
            ("loss_aversion_lambda", 1.0),
        ],
        ids=[
            "extraction_zero",
            "extraction_one",
            "consciousness_zero",
            "subsistence_zero",
            "subsistence_large",
            "steepness_small",
            "steepness_large",
            "repression_zero",
            "repression_one",
            "worker_wealth_zero",
            "owner_wealth_zero",
            "loss_aversion_typical",
            "loss_aversion_one",
        ],
    )
    def test_accepts_valid_value(self, field: str, valid_value: float) -> None:
        """SimulationConfig accepts valid {field} value."""
        config = SimulationConfig(**{field: valid_value})
        assert getattr(config, field) == valid_value

    @pytest.mark.parametrize(
        "field,invalid_value",
        [
            ("extraction_efficiency", -0.1),
            ("extraction_efficiency", 1.5),
            ("consciousness_sensitivity", -0.1),
            ("consciousness_sensitivity", 1.1),
            ("subsistence_threshold", -0.1),
            ("survival_steepness", 0.0),
            ("survival_steepness", -1.0),
            ("repression_level", -0.1),
            ("repression_level", 1.1),
            ("initial_worker_wealth", -1.0),
            ("initial_owner_wealth", -1.0),
            ("loss_aversion_lambda", 0.0),
            ("loss_aversion_lambda", -1.0),
        ],
        ids=[
            "extraction_negative",
            "extraction_over_one",
            "consciousness_negative",
            "consciousness_over_one",
            "subsistence_negative",
            "steepness_zero",
            "steepness_negative",
            "repression_negative",
            "repression_over_one",
            "worker_wealth_negative",
            "owner_wealth_negative",
            "loss_aversion_zero",
            "loss_aversion_negative",
        ],
    )
    def test_rejects_invalid_value(self, field: str, invalid_value: float) -> None:
        """SimulationConfig rejects invalid {field} value."""
        with pytest.raises(ValidationError):
            SimulationConfig(**{field: invalid_value})


# =============================================================================
# CUSTOMIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigCustomization:
    """SimulationConfig should allow custom parameter values."""

    def test_custom_extraction_efficiency(self) -> None:
        """Can set custom extraction efficiency."""
        config = SimulationConfig(extraction_efficiency=TC.Probability.MODERATE)
        assert config.extraction_efficiency == TC.Probability.MODERATE

    def test_custom_repression_level(self) -> None:
        """Can set custom repression level."""
        config = SimulationConfig(repression_level=TC.Probability.EXTREME)
        assert config.repression_level == TC.Probability.EXTREME

    def test_multiple_custom_values(self) -> None:
        """Can set multiple custom values at once."""
        config = SimulationConfig(
            extraction_efficiency=TC.Probability.ELEVATED,
            consciousness_sensitivity=TC.Probability.MODERATE,
            subsistence_threshold=TC.Probability.MIDPOINT,
            repression_level=TC.Probability.HIGH,
        )
        assert config.extraction_efficiency == TC.Probability.ELEVATED
        assert config.consciousness_sensitivity == TC.Probability.MODERATE
        assert config.subsistence_threshold == TC.Probability.MIDPOINT
        assert config.repression_level == TC.Probability.HIGH


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestSimulationConfigSerialization:
    """SimulationConfig should serialize correctly for save/load."""

    def test_json_round_trip(self) -> None:
        """Config survives JSON round-trip."""
        original = SimulationConfig(
            extraction_efficiency=0.75,  # Non-standard value for round-trip test
            consciousness_sensitivity=0.4,  # Non-standard value
            repression_level=TC.Probability.ELEVATED,
        )
        json_str = original.model_dump_json()
        restored = SimulationConfig.model_validate_json(json_str)

        assert restored.extraction_efficiency == pytest.approx(0.75)
        assert restored.consciousness_sensitivity == pytest.approx(0.4)
        assert restored.repression_level == pytest.approx(TC.Probability.ELEVATED)

    def test_dict_round_trip(self) -> None:
        """Config survives dict round-trip."""
        original = SimulationConfig(extraction_efficiency=TC.Probability.EXTREME)
        data = original.model_dump()
        restored = SimulationConfig.model_validate(data)

        assert restored.extraction_efficiency == original.extraction_efficiency

    def test_model_copy_with_update(self) -> None:
        """Config can be copied with updated values."""
        original = SimulationConfig()
        modified = original.model_copy(update={"repression_level": TC.Probability.EXTREME})

        assert original.repression_level == TC.Probability.MIDPOINT  # Unchanged
        assert modified.repression_level == TC.Probability.EXTREME  # Updated


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


# =============================================================================
# SOLIDARITY TRANSMISSION PARAMETERS (Sprint 3.4.2)
# =============================================================================


@pytest.mark.ledger
class TestSolidarityTransmissionConfig:
    """SimulationConfig should have solidarity transmission parameters.

    Sprint 3.4.2: Proletarian Internationalism - The Counterforce.
    These parameters control when consciousness transmission occurs.
    """

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("solidarity_activation_threshold", TC.Solidarity.ACTIVATION_THRESHOLD),
            ("mass_awakening_threshold", TC.Solidarity.MASS_AWAKENING_THRESHOLD),
        ],
        ids=["activation_threshold", "mass_awakening_threshold"],
    )
    def test_solidarity_defaults(self, attr: str, expected: float) -> None:
        """Solidarity parameters have correct default values."""
        config = SimulationConfig()
        assert getattr(config, attr) == expected

    @pytest.mark.parametrize(
        "field,valid_value",
        [
            ("solidarity_activation_threshold", 0.0),
            ("solidarity_activation_threshold", 1.0),
            ("mass_awakening_threshold", 0.0),
            ("mass_awakening_threshold", 1.0),
        ],
        ids=[
            "activation_zero",
            "activation_one",
            "mass_awakening_zero",
            "mass_awakening_one",
        ],
    )
    def test_solidarity_accepts_valid(self, field: str, valid_value: float) -> None:
        """Solidarity parameters accept valid values."""
        config = SimulationConfig(**{field: valid_value})
        assert getattr(config, field) == valid_value

    @pytest.mark.parametrize(
        "field,invalid_value",
        [
            ("solidarity_activation_threshold", -0.1),
            ("solidarity_activation_threshold", 1.1),
            ("mass_awakening_threshold", -0.1),
            ("mass_awakening_threshold", 1.1),
        ],
        ids=[
            "activation_negative",
            "activation_over_one",
            "mass_awakening_negative",
            "mass_awakening_over_one",
        ],
    )
    def test_solidarity_rejects_invalid(self, field: str, invalid_value: float) -> None:
        """Solidarity parameters reject invalid values."""
        with pytest.raises(ValidationError):
            SimulationConfig(**{field: invalid_value})


# =============================================================================
# TERRITORY DYNAMICS PARAMETERS (Sprint 3.5.4)
# =============================================================================


@pytest.mark.ledger
class TestTerritoryDynamicsConfig:
    """SimulationConfig should have territory dynamics parameters.

    Sprint 3.5.4: Layer 0 - The Territorial Substrate.
    These parameters control heat dynamics, eviction, and spillover.
    """

    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("heat_decay_rate", TC.Probability.LOW),
            ("high_profile_heat_gain", 0.15),
            ("eviction_heat_threshold", TC.Territory.EVICTION_THRESHOLD),
            ("rent_spike_multiplier", 1.5),
            ("displacement_rate", TC.Probability.LOW),
            ("heat_spillover_rate", 0.05),
            ("clarity_profile_coefficient", TC.Probability.MODERATE),
        ],
        ids=[
            "heat_decay",
            "high_profile_heat",
            "eviction_threshold",
            "rent_spike",
            "displacement",
            "heat_spillover",
            "clarity_coefficient",
        ],
    )
    def test_territory_defaults(self, attr: str, expected: float) -> None:
        """Territory parameters have correct default values."""
        config = SimulationConfig()
        assert getattr(config, attr) == expected

    def test_territory_params_accept_custom_values(self) -> None:
        """Can set custom territory dynamics parameters."""
        config = SimulationConfig(
            heat_decay_rate=0.2,
            high_profile_heat_gain=0.25,
            eviction_heat_threshold=0.7,
            rent_spike_multiplier=2.0,
            displacement_rate=0.15,
            heat_spillover_rate=0.1,
            clarity_profile_coefficient=0.4,
        )
        assert config.heat_decay_rate == 0.2
        assert config.high_profile_heat_gain == 0.25
        assert config.eviction_heat_threshold == 0.7
        assert config.rent_spike_multiplier == 2.0
        assert config.displacement_rate == 0.15
        assert config.heat_spillover_rate == 0.1
        assert config.clarity_profile_coefficient == 0.4

    @pytest.mark.parametrize(
        "field,invalid_value",
        [
            ("heat_decay_rate", -0.1),
            ("heat_decay_rate", 1.1),
            ("rent_spike_multiplier", 0.0),
            ("rent_spike_multiplier", -1.0),
        ],
        ids=[
            "heat_decay_negative",
            "heat_decay_over_one",
            "rent_spike_zero",
            "rent_spike_negative",
        ],
    )
    def test_territory_rejects_invalid(self, field: str, invalid_value: float) -> None:
        """Territory parameters reject invalid values."""
        with pytest.raises(ValidationError):
            SimulationConfig(**{field: invalid_value})
