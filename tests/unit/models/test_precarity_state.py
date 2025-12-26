"""Tests for PrecarityState model.

TDD Red Phase: These tests define the contract for PrecarityState.
PrecarityState tracks the economic precarity of working-class populations
including wages, purchasing power, and proletarianization risk.

Epoch 1 (The Ledger) - Political Economy of Liquidity specification.

The PrecarityState model captures the material conditions that determine
whether a class can survive through acquiescence or must turn to revolution:
- nominal_wage: Raw wage in currency units
- ppp_factor: Purchasing power parity adjustment
- inflation_index: Price level multiplier
- subsistence_threshold: Minimum for survival
- organization: Collective capacity to resist

Key computed fields:
- real_wage: (nominal_wage * ppp_factor) / inflation_index
- precarity_index: 1 - sigmoid(real_wage - subsistence_threshold)
- proletarianization_risk: precarity_index * (1 - organization)

The sigmoid function maps the wage-subsistence gap to a probability:
- When real_wage >> subsistence_threshold, precarity_index -> 0 (secure)
- When real_wage << subsistence_threshold, precarity_index -> 1 (precarious)
- When real_wage == subsistence_threshold, precarity_index -> 0.5 (marginal)
"""

import math

import pytest
from pydantic import ValidationError

# This import will fail until model exists - that's the RED phase!
from babylon.models.entities.precarity_state import PrecarityState


def sigmoid(x: float) -> float:
    """Standard logistic sigmoid function for test calculations."""
    return 1.0 / (1.0 + math.exp(-x))


# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestPrecarityStateCreation:
    """PrecarityState should be createable with valid data."""

    def test_minimal_creation(self) -> None:
        """Can create PrecarityState with all defaults."""
        precarity = PrecarityState()
        assert precarity.nominal_wage == 10.0

    def test_with_custom_nominal_wage(self) -> None:
        """Can create PrecarityState with custom nominal wage."""
        precarity = PrecarityState(nominal_wage=20.0)
        assert precarity.nominal_wage == 20.0

    def test_with_custom_ppp_factor(self) -> None:
        """Can create PrecarityState with custom PPP factor."""
        precarity = PrecarityState(ppp_factor=0.5)
        assert precarity.ppp_factor == 0.5

    def test_with_custom_inflation_index(self) -> None:
        """Can create PrecarityState with custom inflation index."""
        precarity = PrecarityState(inflation_index=2.0)
        assert precarity.inflation_index == 2.0

    def test_with_custom_subsistence_threshold(self) -> None:
        """Can create PrecarityState with custom subsistence threshold."""
        precarity = PrecarityState(subsistence_threshold=8.0)
        assert precarity.subsistence_threshold == 8.0

    def test_with_custom_organization(self) -> None:
        """Can create PrecarityState with custom organization."""
        precarity = PrecarityState(organization=0.7)
        assert precarity.organization == 0.7

    def test_full_custom_creation(self) -> None:
        """Can create PrecarityState with all custom field values."""
        precarity = PrecarityState(
            nominal_wage=25.0,
            ppp_factor=0.8,
            inflation_index=1.5,
            subsistence_threshold=7.0,
            organization=0.6,
        )
        assert precarity.nominal_wage == 25.0
        assert precarity.ppp_factor == 0.8
        assert precarity.inflation_index == 1.5
        assert precarity.subsistence_threshold == 7.0
        assert precarity.organization == 0.6


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestPrecarityStateValidation:
    """PrecarityState should validate fields according to type constraints."""

    # --- Nominal Wage (Currency [0, inf)) ---

    def test_nominal_wage_cannot_be_negative(self) -> None:
        """nominal_wage is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            PrecarityState(nominal_wage=-5.0)

    def test_nominal_wage_can_be_zero(self) -> None:
        """nominal_wage can be zero (unemployed)."""
        precarity = PrecarityState(nominal_wage=0.0)
        assert precarity.nominal_wage == 0.0

    def test_nominal_wage_can_be_large(self) -> None:
        """nominal_wage can be arbitrarily large."""
        precarity = PrecarityState(nominal_wage=100_000.0)
        assert precarity.nominal_wage == 100_000.0

    # --- PPP Factor (Coefficient [0, 1]) ---

    def test_ppp_factor_cannot_be_negative(self) -> None:
        """ppp_factor is Coefficient type [0, 1]."""
        with pytest.raises(ValidationError):
            PrecarityState(ppp_factor=-0.1)

    def test_ppp_factor_cannot_exceed_one(self) -> None:
        """ppp_factor is Coefficient type [0, 1]."""
        with pytest.raises(ValidationError):
            PrecarityState(ppp_factor=1.5)

    def test_ppp_factor_boundary_zero(self) -> None:
        """PPP factor can be 0.0 (currency worthless locally)."""
        precarity = PrecarityState(ppp_factor=0.0)
        assert precarity.ppp_factor == 0.0

    def test_ppp_factor_boundary_one(self) -> None:
        """PPP factor can be 1.0 (full purchasing power)."""
        precarity = PrecarityState(ppp_factor=1.0)
        assert precarity.ppp_factor == 1.0

    # --- Inflation Index (float >= 1.0) ---

    def test_inflation_index_cannot_be_less_than_one(self) -> None:
        """inflation_index must be >= 1.0 (deflation not modeled as < 1)."""
        with pytest.raises(ValidationError):
            PrecarityState(inflation_index=0.9)

    def test_inflation_index_cannot_be_zero(self) -> None:
        """inflation_index cannot be zero (would cause division by zero)."""
        with pytest.raises(ValidationError):
            PrecarityState(inflation_index=0.0)

    def test_inflation_index_cannot_be_negative(self) -> None:
        """inflation_index cannot be negative."""
        with pytest.raises(ValidationError):
            PrecarityState(inflation_index=-1.0)

    def test_inflation_index_boundary_one(self) -> None:
        """Inflation index of 1.0 means no inflation (baseline)."""
        precarity = PrecarityState(inflation_index=1.0)
        assert precarity.inflation_index == 1.0

    def test_inflation_index_can_be_large(self) -> None:
        """Inflation index can be large (hyperinflation)."""
        precarity = PrecarityState(inflation_index=1000.0)
        assert precarity.inflation_index == 1000.0

    # --- Subsistence Threshold (Currency [0, inf)) ---

    def test_subsistence_threshold_cannot_be_negative(self) -> None:
        """subsistence_threshold is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            PrecarityState(subsistence_threshold=-3.0)

    def test_subsistence_threshold_can_be_zero(self) -> None:
        """subsistence_threshold can be zero (theoretical edge case)."""
        precarity = PrecarityState(subsistence_threshold=0.0)
        assert precarity.subsistence_threshold == 0.0

    # --- Organization (Probability [0, 1]) ---

    def test_organization_cannot_be_negative(self) -> None:
        """organization is Probability type [0, 1]."""
        with pytest.raises(ValidationError):
            PrecarityState(organization=-0.1)

    def test_organization_cannot_exceed_one(self) -> None:
        """organization is Probability type [0, 1]."""
        with pytest.raises(ValidationError):
            PrecarityState(organization=1.5)

    def test_organization_boundary_zero(self) -> None:
        """Organization can be 0.0 (atomized, no collective capacity)."""
        precarity = PrecarityState(organization=0.0)
        assert precarity.organization == 0.0

    def test_organization_boundary_one(self) -> None:
        """Organization can be 1.0 (fully organized class)."""
        precarity = PrecarityState(organization=1.0)
        assert precarity.organization == 1.0


# =============================================================================
# DEFAULT VALUES TESTS
# =============================================================================


@pytest.mark.ledger
class TestPrecarityStateDefaults:
    """PrecarityState should have defaults matching specification."""

    def test_nominal_wage_defaults_to_10(self) -> None:
        """Nominal wage defaults to 10.0."""
        precarity = PrecarityState()
        assert precarity.nominal_wage == 10.0

    def test_ppp_factor_defaults_to_1(self) -> None:
        """PPP factor defaults to 1.0 (full purchasing power)."""
        precarity = PrecarityState()
        assert precarity.ppp_factor == 1.0

    def test_inflation_index_defaults_to_1(self) -> None:
        """Inflation index defaults to 1.0 (no inflation)."""
        precarity = PrecarityState()
        assert precarity.inflation_index == 1.0

    def test_subsistence_threshold_defaults_to_5(self) -> None:
        """Subsistence threshold defaults to 5.0."""
        precarity = PrecarityState()
        assert precarity.subsistence_threshold == 5.0

    def test_organization_defaults_to_0_5(self) -> None:
        """Organization defaults to 0.5 (moderate organization)."""
        precarity = PrecarityState()
        assert precarity.organization == 0.5


# =============================================================================
# COMPUTED FIELD TESTS
# =============================================================================


@pytest.mark.math
class TestPrecarityStateComputedRealWage:
    """Test real_wage computed field.

    real_wage = (nominal_wage * ppp_factor) / inflation_index
    """

    def test_real_wage_with_defaults(self) -> None:
        """real_wage with defaults: (10 * 1.0) / 1.0 = 10.0."""
        precarity = PrecarityState()
        assert precarity.real_wage == pytest.approx(10.0)

    def test_real_wage_with_low_ppp(self) -> None:
        """real_wage with low PPP: (10 * 0.5) / 1.0 = 5.0."""
        precarity = PrecarityState(nominal_wage=10.0, ppp_factor=0.5, inflation_index=1.0)
        assert precarity.real_wage == pytest.approx(5.0)

    def test_real_wage_with_high_inflation(self) -> None:
        """real_wage with inflation: (10 * 1.0) / 2.0 = 5.0."""
        precarity = PrecarityState(nominal_wage=10.0, ppp_factor=1.0, inflation_index=2.0)
        assert precarity.real_wage == pytest.approx(5.0)

    def test_real_wage_combined_effects(self) -> None:
        """real_wage with combined effects: (20 * 0.8) / 2.0 = 8.0."""
        precarity = PrecarityState(nominal_wage=20.0, ppp_factor=0.8, inflation_index=2.0)
        assert precarity.real_wage == pytest.approx(8.0)

    def test_real_wage_with_zero_nominal(self) -> None:
        """real_wage with zero nominal: (0 * 1.0) / 1.0 = 0.0."""
        precarity = PrecarityState(nominal_wage=0.0)
        assert precarity.real_wage == pytest.approx(0.0)

    def test_real_wage_with_zero_ppp(self) -> None:
        """real_wage with zero PPP: (10 * 0.0) / 1.0 = 0.0."""
        precarity = PrecarityState(nominal_wage=10.0, ppp_factor=0.0)
        assert precarity.real_wage == pytest.approx(0.0)

    def test_real_wage_hyperinflation(self) -> None:
        """real_wage under hyperinflation: (100 * 1.0) / 100.0 = 1.0."""
        precarity = PrecarityState(nominal_wage=100.0, ppp_factor=1.0, inflation_index=100.0)
        assert precarity.real_wage == pytest.approx(1.0)


@pytest.mark.math
class TestPrecarityStateComputedPrecarityIndex:
    """Test precarity_index computed field.

    precarity_index = 1 - sigmoid(real_wage - subsistence_threshold)

    Interpretation:
    - real_wage >> subsistence: precarity -> 0 (secure)
    - real_wage << subsistence: precarity -> 1 (precarious)
    - real_wage == subsistence: precarity -> 0.5 (marginal)
    """

    def test_precarity_index_at_subsistence(self) -> None:
        """precarity_index when real_wage == subsistence_threshold.

        At the subsistence threshold: sigmoid(0) = 0.5
        precarity_index = 1 - 0.5 = 0.5
        """
        precarity = PrecarityState(
            nominal_wage=5.0,
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=5.0,
        )
        # real_wage = 5, subsistence = 5, gap = 0
        expected = 1.0 - sigmoid(0.0)
        assert precarity.precarity_index == pytest.approx(expected, abs=0.01)
        assert precarity.precarity_index == pytest.approx(0.5, abs=0.01)

    def test_precarity_index_above_subsistence(self) -> None:
        """precarity_index when real_wage > subsistence_threshold.

        Above subsistence: sigmoid(positive) > 0.5
        precarity_index = 1 - sigmoid(positive) < 0.5
        """
        precarity = PrecarityState(
            nominal_wage=10.0,  # real_wage = 10
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=5.0,
        )
        # gap = 10 - 5 = 5
        expected = 1.0 - sigmoid(5.0)
        assert precarity.precarity_index == pytest.approx(expected, abs=0.01)
        assert precarity.precarity_index < 0.5  # Relatively secure

    def test_precarity_index_well_above_subsistence(self) -> None:
        """precarity_index approaches 0 when real_wage >> subsistence."""
        precarity = PrecarityState(
            nominal_wage=100.0,  # real_wage = 100
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=5.0,
        )
        # gap = 100 - 5 = 95, sigmoid(95) -> 1.0
        assert precarity.precarity_index < 0.01  # Nearly zero (very secure)

    def test_precarity_index_below_subsistence(self) -> None:
        """precarity_index when real_wage < subsistence_threshold.

        Below subsistence: sigmoid(negative) < 0.5
        precarity_index = 1 - sigmoid(negative) > 0.5
        """
        precarity = PrecarityState(
            nominal_wage=3.0,  # real_wage = 3
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=5.0,
        )
        # gap = 3 - 5 = -2
        expected = 1.0 - sigmoid(-2.0)
        assert precarity.precarity_index == pytest.approx(expected, abs=0.01)
        assert precarity.precarity_index > 0.5  # Relatively precarious

    def test_precarity_index_well_below_subsistence(self) -> None:
        """precarity_index approaches 1 when real_wage << subsistence."""
        precarity = PrecarityState(
            nominal_wage=0.0,  # real_wage = 0
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=10.0,
        )
        # gap = 0 - 10 = -10, sigmoid(-10) -> 0.0
        assert precarity.precarity_index > 0.99  # Nearly one (extremely precarious)

    def test_precarity_index_with_defaults(self) -> None:
        """precarity_index with default values.

        Default: real_wage=10, subsistence=5, gap=5
        """
        precarity = PrecarityState()
        expected = 1.0 - sigmoid(10.0 - 5.0)
        assert precarity.precarity_index == pytest.approx(expected, abs=0.01)


@pytest.mark.math
class TestPrecarityStateComputedProletarianizationRisk:
    """Test proletarianization_risk computed field.

    proletarianization_risk = precarity_index * (1 - organization)

    This captures the insight that:
    - High precarity + low organization = high risk of proletarianization
    - High precarity + high organization = lower risk (collective resistance)
    - Low precarity = low risk regardless of organization
    """

    def test_proletarianization_risk_with_no_organization(self) -> None:
        """proletarianization_risk equals precarity_index when organization=0.

        risk = precarity_index * (1 - 0) = precarity_index
        """
        precarity = PrecarityState(
            nominal_wage=3.0,
            subsistence_threshold=5.0,
            organization=0.0,
        )
        assert precarity.proletarianization_risk == pytest.approx(
            precarity.precarity_index, abs=0.01
        )

    def test_proletarianization_risk_with_full_organization(self) -> None:
        """proletarianization_risk is zero when organization=1.0.

        risk = precarity_index * (1 - 1) = 0
        Organization provides complete protection.
        """
        precarity = PrecarityState(
            nominal_wage=3.0,
            subsistence_threshold=5.0,
            organization=1.0,
        )
        assert precarity.proletarianization_risk == pytest.approx(0.0, abs=0.01)

    def test_proletarianization_risk_with_half_organization(self) -> None:
        """proletarianization_risk is halved with organization=0.5.

        risk = precarity_index * (1 - 0.5) = precarity_index * 0.5
        """
        precarity = PrecarityState(
            nominal_wage=3.0,
            subsistence_threshold=5.0,
            organization=0.5,
        )
        expected = precarity.precarity_index * 0.5
        assert precarity.proletarianization_risk == pytest.approx(expected, abs=0.01)

    def test_proletarianization_risk_secure_class(self) -> None:
        """proletarianization_risk is low when class is secure (high wages).

        Even with low organization, secure classes face low risk.
        """
        precarity = PrecarityState(
            nominal_wage=100.0,  # Well above subsistence
            subsistence_threshold=5.0,
            organization=0.0,
        )
        # precarity_index is near 0, so risk is near 0
        assert precarity.proletarianization_risk < 0.01

    def test_proletarianization_risk_precarious_atomized(self) -> None:
        """proletarianization_risk is maximum when precarious and atomized.

        The worst case: below subsistence with no organization.
        """
        precarity = PrecarityState(
            nominal_wage=1.0,  # Well below subsistence
            subsistence_threshold=10.0,
            organization=0.0,  # Atomized
        )
        # precarity_index is near 1, organization term is 1
        assert precarity.proletarianization_risk > 0.95

    def test_proletarianization_risk_with_defaults(self) -> None:
        """proletarianization_risk with default values.

        Default: precarity_index computed, organization=0.5
        risk = precarity_index * 0.5
        """
        precarity = PrecarityState()
        expected = precarity.precarity_index * (1.0 - precarity.organization)
        assert precarity.proletarianization_risk == pytest.approx(expected, abs=0.01)


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.ledger
class TestPrecarityStateImmutability:
    """PrecarityState should be frozen (immutable after creation)."""

    def test_cannot_mutate_nominal_wage(self) -> None:
        """nominal_wage cannot be mutated after creation."""
        precarity = PrecarityState()
        with pytest.raises(ValidationError):
            precarity.nominal_wage = 20.0  # type: ignore[misc]

    def test_cannot_mutate_ppp_factor(self) -> None:
        """ppp_factor cannot be mutated after creation."""
        precarity = PrecarityState()
        with pytest.raises(ValidationError):
            precarity.ppp_factor = 0.5  # type: ignore[misc]

    def test_cannot_mutate_inflation_index(self) -> None:
        """inflation_index cannot be mutated after creation."""
        precarity = PrecarityState()
        with pytest.raises(ValidationError):
            precarity.inflation_index = 2.0  # type: ignore[misc]

    def test_cannot_mutate_subsistence_threshold(self) -> None:
        """subsistence_threshold cannot be mutated after creation."""
        precarity = PrecarityState()
        with pytest.raises(ValidationError):
            precarity.subsistence_threshold = 8.0  # type: ignore[misc]

    def test_cannot_mutate_organization(self) -> None:
        """organization cannot be mutated after creation."""
        precarity = PrecarityState()
        with pytest.raises(ValidationError):
            precarity.organization = 0.8  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestPrecarityStateSerialization:
    """PrecarityState should serialize correctly for Ledger storage."""

    def test_model_dump(self) -> None:
        """Can dump PrecarityState to dict."""
        precarity = PrecarityState(
            nominal_wage=25.0,
            ppp_factor=0.8,
            inflation_index=1.5,
            subsistence_threshold=7.0,
            organization=0.6,
        )
        data = precarity.model_dump()
        assert data["nominal_wage"] == 25.0
        assert data["ppp_factor"] == pytest.approx(0.8)
        assert data["inflation_index"] == pytest.approx(1.5)
        assert data["subsistence_threshold"] == 7.0
        assert data["organization"] == pytest.approx(0.6)

    def test_model_dump_includes_computed(self) -> None:
        """model_dump includes all computed fields."""
        precarity = PrecarityState(
            nominal_wage=20.0,
            ppp_factor=0.5,
            inflation_index=2.0,
            subsistence_threshold=5.0,
            organization=0.3,
        )
        data = precarity.model_dump()
        # real_wage = (20 * 0.5) / 2.0 = 5.0
        assert "real_wage" in data
        assert data["real_wage"] == pytest.approx(5.0)
        assert "precarity_index" in data
        assert "proletarianization_risk" in data

    def test_model_validate(self) -> None:
        """Can reconstruct PrecarityState from dict."""
        data = {
            "nominal_wage": 25.0,
            "ppp_factor": 0.8,
            "inflation_index": 1.5,
            "subsistence_threshold": 7.0,
            "organization": 0.6,
        }
        precarity = PrecarityState.model_validate(data)
        assert precarity.nominal_wage == 25.0
        assert precarity.ppp_factor == pytest.approx(0.8)
        assert precarity.inflation_index == pytest.approx(1.5)
        assert precarity.subsistence_threshold == 7.0
        assert precarity.organization == pytest.approx(0.6)

    def test_json_round_trip(self) -> None:
        """PrecarityState survives JSON serialization round trip."""
        original = PrecarityState(
            nominal_wage=30.0,
            ppp_factor=0.7,
            inflation_index=1.8,
            subsistence_threshold=6.0,
            organization=0.4,
        )
        json_str = original.model_dump_json()
        restored = PrecarityState.model_validate_json(json_str)

        assert restored.nominal_wage == pytest.approx(original.nominal_wage)
        assert restored.ppp_factor == pytest.approx(original.ppp_factor)
        assert restored.inflation_index == pytest.approx(original.inflation_index)
        assert restored.subsistence_threshold == pytest.approx(original.subsistence_threshold)
        assert restored.organization == pytest.approx(original.organization)
        assert restored.real_wage == pytest.approx(original.real_wage)
        assert restored.precarity_index == pytest.approx(original.precarity_index)
        assert restored.proletarianization_risk == pytest.approx(original.proletarianization_risk)

    def test_dict_round_trip(self) -> None:
        """PrecarityState survives dict round-trip."""
        original = PrecarityState(
            nominal_wage=15.0,
            organization=0.7,
        )
        data = original.model_dump()
        restored = PrecarityState.model_validate(data)

        assert restored.nominal_wage == original.nominal_wage
        assert restored.organization == original.organization
        assert restored.real_wage == original.real_wage
        assert restored.precarity_index == pytest.approx(original.precarity_index)


# =============================================================================
# ECONOMIC SCENARIO TESTS
# =============================================================================


@pytest.mark.math
class TestPrecarityStateEconomicScenarios:
    """Tests for realistic economic scenarios modeled by PrecarityState."""

    def test_core_labor_aristocracy(self) -> None:
        """Core labor aristocracy: high wages, full PPP, low inflation.

        Result: low precarity, low proletarianization risk.
        """
        aristocracy = PrecarityState(
            nominal_wage=50.0,
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=5.0,
            organization=0.3,
        )
        # real_wage = 50, well above subsistence
        assert aristocracy.real_wage == 50.0
        assert aristocracy.precarity_index < 0.01  # Very secure
        assert aristocracy.proletarianization_risk < 0.01

    def test_periphery_proletariat(self) -> None:
        """Periphery proletariat: low wages, low PPP.

        Result: high precarity despite nominal wage appearing adequate.
        """
        periphery = PrecarityState(
            nominal_wage=10.0,
            ppp_factor=0.3,  # Low purchasing power in periphery
            inflation_index=1.0,
            subsistence_threshold=5.0,
            organization=0.2,
        )
        # real_wage = (10 * 0.3) / 1.0 = 3.0, below subsistence
        assert periphery.real_wage == pytest.approx(3.0)
        assert periphery.precarity_index > 0.5  # Precarious
        assert periphery.proletarianization_risk > 0.4  # High risk

    def test_hyperinflation_crisis(self) -> None:
        """Hyperinflation: high nominal wage destroyed by inflation.

        Result: real wage collapse, precarity crisis.
        """
        hyperinflation = PrecarityState(
            nominal_wage=1000.0,  # Seems high
            ppp_factor=1.0,
            inflation_index=100.0,  # Hyperinflation
            subsistence_threshold=5.0,
            organization=0.1,
        )
        # real_wage = (1000 * 1.0) / 100 = 10.0
        assert hyperinflation.real_wage == pytest.approx(10.0)
        # Still above subsistence in this case

    def test_stagflation_squeeze(self) -> None:
        """Stagflation: stagnant wages + inflation + declining PPP.

        Result: real wage erosion, increasing precarity.
        """
        stagflation = PrecarityState(
            nominal_wage=10.0,  # Stagnant
            ppp_factor=0.7,  # Declining
            inflation_index=1.4,  # Rising
            subsistence_threshold=5.0,
            organization=0.4,
        )
        # real_wage = (10 * 0.7) / 1.4 = 5.0, at subsistence
        assert stagflation.real_wage == pytest.approx(5.0)
        assert stagflation.precarity_index == pytest.approx(0.5, abs=0.1)

    def test_organized_resistance(self) -> None:
        """Organized class: precarious but protected by organization.

        Result: high precarity, but low proletarianization risk due to solidarity.
        """
        organized = PrecarityState(
            nominal_wage=3.0,  # Below subsistence
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=5.0,
            organization=0.9,  # Highly organized
        )
        # real_wage = 3, below subsistence
        # precarity_index is high
        # but proletarianization_risk = precarity * (1 - 0.9) = precarity * 0.1
        assert organized.precarity_index > 0.5  # Precarious material conditions
        assert organized.proletarianization_risk < organized.precarity_index * 0.2

    def test_atomized_petty_bourgeoisie(self) -> None:
        """Atomized class: currently secure but vulnerable if conditions change.

        Result: low precarity now, but no organizational buffer.
        """
        atomized = PrecarityState(
            nominal_wage=20.0,
            ppp_factor=1.0,
            inflation_index=1.0,
            subsistence_threshold=5.0,
            organization=0.0,  # Completely atomized
        )
        # Currently secure
        assert atomized.precarity_index < 0.01
        # But if conditions change, no protection
        # risk = precarity * 1.0 = precarity (full exposure)
        assert atomized.proletarianization_risk == pytest.approx(
            atomized.precarity_index, abs=0.001
        )
