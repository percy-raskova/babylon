"""Tests for babylon.models.config.

TDD Red Phase: These tests define the contract for SimulationConfig.
SimulationConfig holds all formula coefficients and global parameters
for the simulation engine.

Sprint 3: SimulationConfig model for Phase 2 game loop.
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

    def test_extraction_efficiency_default(self) -> None:
        """Alpha (α) defaults to 0.8 for imperial rent calculation."""
        config = SimulationConfig()
        assert config.extraction_efficiency == TC.Probability.VERY_HIGH

    def test_consciousness_sensitivity_default(self) -> None:
        """k defaults to 0.5 for consciousness drift calculation."""
        config = SimulationConfig()
        assert config.consciousness_sensitivity == TC.Probability.MIDPOINT

    def test_subsistence_threshold_default(self) -> None:
        """Poverty line defaults to 0.3 for acquiescence sigmoid."""
        config = SimulationConfig()
        assert config.subsistence_threshold == TC.Probability.MODERATE

    def test_survival_steepness_default(self) -> None:
        """Sigmoid sharpness defaults to 10.0."""
        config = SimulationConfig()
        assert config.survival_steepness == 10.0  # Specific sigmoid parameter

    def test_repression_level_default(self) -> None:
        """State violence capacity defaults to 0.5."""
        config = SimulationConfig()
        assert config.repression_level == TC.Probability.MIDPOINT

    def test_initial_worker_wealth_default(self) -> None:
        """Starting wealth for periphery worker defaults to 0.5."""
        config = SimulationConfig()
        assert config.initial_worker_wealth == TC.Wealth.WORKER_BASELINE

    def test_initial_owner_wealth_default(self) -> None:
        """Starting wealth for core owner defaults to 0.5."""
        config = SimulationConfig()
        assert config.initial_owner_wealth == TC.Wealth.WORKER_BASELINE

    def test_loss_aversion_lambda_default(self) -> None:
        """Kahneman-Tversky lambda defaults to 2.25."""
        config = SimulationConfig()
        assert config.loss_aversion_lambda == TC.Behavioral.LOSS_AVERSION

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

    def test_solidarity_activation_threshold_default(self) -> None:
        """solidarity_activation_threshold defaults to 0.3.

        Source consciousness must be > this threshold for transmission.
        """
        config = SimulationConfig()
        assert config.solidarity_activation_threshold == TC.Solidarity.ACTIVATION_THRESHOLD

    def test_mass_awakening_threshold_default(self) -> None:
        """mass_awakening_threshold defaults to 0.6.

        When target consciousness crosses this threshold, MASS_AWAKENING event fires.
        """
        config = SimulationConfig()
        assert config.mass_awakening_threshold == TC.Solidarity.MASS_AWAKENING_THRESHOLD

    def test_solidarity_activation_threshold_accepts_zero(self) -> None:
        """Zero threshold means any consciousness transmits."""
        config = SimulationConfig(solidarity_activation_threshold=0.0)
        assert config.solidarity_activation_threshold == 0.0

    def test_solidarity_activation_threshold_accepts_one(self) -> None:
        """Threshold of 1.0 means transmission requires full consciousness."""
        config = SimulationConfig(solidarity_activation_threshold=1.0)
        assert config.solidarity_activation_threshold == 1.0

    def test_solidarity_activation_threshold_rejects_negative(self) -> None:
        """Negative threshold is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(solidarity_activation_threshold=-0.1)

    def test_solidarity_activation_threshold_rejects_greater_than_one(self) -> None:
        """Threshold > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(solidarity_activation_threshold=1.1)

    def test_mass_awakening_threshold_accepts_zero(self) -> None:
        """Zero mass awakening threshold is valid."""
        config = SimulationConfig(mass_awakening_threshold=0.0)
        assert config.mass_awakening_threshold == 0.0

    def test_mass_awakening_threshold_accepts_one(self) -> None:
        """Mass awakening at full consciousness is valid."""
        config = SimulationConfig(mass_awakening_threshold=1.0)
        assert config.mass_awakening_threshold == 1.0

    def test_mass_awakening_threshold_rejects_negative(self) -> None:
        """Negative mass awakening threshold is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(mass_awakening_threshold=-0.1)

    def test_mass_awakening_threshold_rejects_greater_than_one(self) -> None:
        """Mass awakening threshold > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(mass_awakening_threshold=1.1)


# =============================================================================
# TERRITORY DYNAMICS PARAMETERS (Sprint 3.5.4)
# =============================================================================


@pytest.mark.ledger
class TestTerritoryDynamicsConfig:
    """SimulationConfig should have territory dynamics parameters.

    Sprint 3.5.4: Layer 0 - The Territorial Substrate.
    These parameters control heat dynamics, eviction, and spillover.
    """

    def test_heat_decay_rate_default(self) -> None:
        """heat_decay_rate defaults to 0.1.

        Rate at which heat decays for LOW_PROFILE territories.
        """
        config = SimulationConfig()
        assert config.heat_decay_rate == TC.Probability.LOW

    def test_high_profile_heat_gain_default(self) -> None:
        """high_profile_heat_gain defaults to 0.15.

        Heat gain per tick for HIGH_PROFILE territories.
        """
        config = SimulationConfig()
        assert config.high_profile_heat_gain == 0.15  # Territory-specific rate

    def test_eviction_heat_threshold_default(self) -> None:
        """eviction_heat_threshold defaults to 0.8.

        Heat level at which eviction pipeline is triggered.
        """
        config = SimulationConfig()
        assert config.eviction_heat_threshold == TC.Territory.EVICTION_THRESHOLD

    def test_rent_spike_multiplier_default(self) -> None:
        """rent_spike_multiplier defaults to 1.5.

        Rent multiplier during eviction.
        """
        config = SimulationConfig()
        assert config.rent_spike_multiplier == 1.5  # Multiplier (not a probability)

    def test_displacement_rate_default(self) -> None:
        """displacement_rate defaults to 0.1.

        Population displacement rate during eviction.
        """
        config = SimulationConfig()
        assert config.displacement_rate == TC.Probability.LOW

    def test_heat_spillover_rate_default(self) -> None:
        """heat_spillover_rate defaults to 0.05.

        Rate of heat spillover via ADJACENCY edges.
        """
        config = SimulationConfig()
        assert config.heat_spillover_rate == 0.05  # Territory-specific rate

    def test_clarity_profile_coefficient_default(self) -> None:
        """clarity_profile_coefficient defaults to 0.3.

        Clarity bonus for HIGH_PROFILE territories.
        """
        config = SimulationConfig()
        assert config.clarity_profile_coefficient == TC.Probability.MODERATE

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

    def test_heat_decay_rate_rejects_negative(self) -> None:
        """Negative heat decay rate is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(heat_decay_rate=-0.1)

    def test_heat_decay_rate_rejects_greater_than_one(self) -> None:
        """Heat decay rate > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(heat_decay_rate=1.1)

    def test_rent_spike_multiplier_rejects_zero(self) -> None:
        """Zero rent spike multiplier is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(rent_spike_multiplier=0.0)

    def test_rent_spike_multiplier_rejects_negative(self) -> None:
        """Negative rent spike multiplier is invalid."""
        with pytest.raises(ValidationError):
            SimulationConfig(rent_spike_multiplier=-1.0)
