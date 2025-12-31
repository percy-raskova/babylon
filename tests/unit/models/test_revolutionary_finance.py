"""Tests for RevolutionaryFinance model.

TDD Red Phase: These tests define the contract for RevolutionaryFinance.
RevolutionaryFinance tracks the financial state of revolutionary organizations
including war chest, operational costs, various income streams, and strategic concerns.

Epoch 1 (The Ledger) - Political Economy of Liquidity specification.

The RevolutionaryFinance model represents the fiscal capacity of revolutionary actors:
- war_chest: available liquid funds for revolutionary activity
- operational_burn: minimum cost to maintain organization per tick
- Income streams: dues (members), expropriation (direct action), donors (liberal funding)
- Strategic concerns: heat (state attention), reformist_drift (ideological corruption)

Key insight: Revolutionary organizations face a fundamental tension:
- Donor income is easiest but causes reformist_drift (ideological corruption)
- Expropriation income is most revolutionary but generates heat (state attention)
- Dues income is sustainable but requires organizational capacity
"""

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

# This import will fail until model exists - that's the RED phase!
from babylon.models.entities.revolutionary_finance import RevolutionaryFinance

TC = TestConstants

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestRevolutionaryFinanceCreation:
    """RevolutionaryFinance should be createable with valid data."""

    def test_minimal_creation(self) -> None:
        """Can create RevolutionaryFinance with all defaults."""
        finance = RevolutionaryFinance()
        assert finance.war_chest == TC.RevolutionaryFinance.DEFAULT_WAR_CHEST

    def test_with_custom_war_chest(self) -> None:
        """Can create RevolutionaryFinance with custom war chest."""
        finance = RevolutionaryFinance(war_chest=TC.RevolutionaryFinance.SIGNIFICANT_WAR_CHEST)
        assert finance.war_chest == TC.RevolutionaryFinance.SIGNIFICANT_WAR_CHEST

    def test_with_custom_operational_burn(self) -> None:
        """Can create RevolutionaryFinance with custom operational burn."""
        finance = RevolutionaryFinance(operational_burn=TC.RevolutionaryFinance.OPERATIONAL_BURN)
        assert finance.operational_burn == TC.RevolutionaryFinance.OPERATIONAL_BURN

    def test_with_custom_dues_income(self) -> None:
        """Can create RevolutionaryFinance with custom dues income."""
        finance = RevolutionaryFinance(dues_income=TC.RevolutionaryFinance.DUES_INCOME)
        assert finance.dues_income == TC.RevolutionaryFinance.DUES_INCOME

    def test_with_custom_expropriation_income(self) -> None:
        """Can create RevolutionaryFinance with custom expropriation income."""
        finance = RevolutionaryFinance(
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_STANDARD
        )
        assert finance.expropriation_income == TC.RevolutionaryFinance.EXPROPRIATION_STANDARD

    def test_with_custom_donor_income(self) -> None:
        """Can create RevolutionaryFinance with custom donor income."""
        finance = RevolutionaryFinance(donor_income=TC.RevolutionaryFinance.DONOR_STANDARD)
        assert finance.donor_income == TC.RevolutionaryFinance.DONOR_STANDARD

    def test_with_custom_heat(self) -> None:
        """Can create RevolutionaryFinance with custom heat."""
        finance = RevolutionaryFinance(heat=TC.Probability.MIDPOINT)
        assert finance.heat == TC.Probability.MIDPOINT

    def test_with_custom_reformist_drift(self) -> None:
        """Can create RevolutionaryFinance with custom reformist drift."""
        finance = RevolutionaryFinance(reformist_drift=TC.RevolutionaryFinance.DRIFT_MODERATE)
        assert finance.reformist_drift == TC.RevolutionaryFinance.DRIFT_MODERATE

    def test_full_custom_creation(self) -> None:
        """Can create RevolutionaryFinance with all custom field values."""
        finance = RevolutionaryFinance(
            war_chest=TC.RevolutionaryFinance.MODERATE_WAR_CHEST,
            operational_burn=TC.RevolutionaryFinance.OPERATIONAL_BURN,
            dues_income=TC.RevolutionaryFinance.DUES_INCOME,
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_STANDARD,
            donor_income=TC.RevolutionaryFinance.DONOR_STANDARD,
            heat=TC.Probability.HIGH,
            reformist_drift=TC.Ideology.LEANING_REVOLUTIONARY,
        )
        assert finance.war_chest == TC.RevolutionaryFinance.MODERATE_WAR_CHEST
        assert finance.operational_burn == TC.RevolutionaryFinance.OPERATIONAL_BURN
        assert finance.dues_income == TC.RevolutionaryFinance.DUES_INCOME
        assert finance.expropriation_income == TC.RevolutionaryFinance.EXPROPRIATION_STANDARD
        assert finance.donor_income == TC.RevolutionaryFinance.DONOR_STANDARD
        assert finance.heat == TC.Probability.HIGH
        assert finance.reformist_drift == TC.Ideology.LEANING_REVOLUTIONARY


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestRevolutionaryFinanceValidation:
    """RevolutionaryFinance should validate fields according to type constraints."""

    # --- War Chest (Currency [0, inf)) ---

    def test_war_chest_cannot_be_negative(self) -> None:
        """war_chest is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(war_chest=-10.0)

    def test_war_chest_can_be_zero(self) -> None:
        """war_chest can be zero (depleted organization)."""
        finance = RevolutionaryFinance(war_chest=0.0)
        assert finance.war_chest == 0.0

    def test_war_chest_can_be_large(self) -> None:
        """war_chest can be arbitrarily large."""
        finance = RevolutionaryFinance(war_chest=TC.RevolutionaryFinance.LARGE_WAR_CHEST)
        assert finance.war_chest == TC.RevolutionaryFinance.LARGE_WAR_CHEST

    # --- Operational Burn (Currency [0, inf)) ---

    def test_operational_burn_cannot_be_negative(self) -> None:
        """operational_burn is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(operational_burn=-2.0)

    def test_operational_burn_can_be_zero(self) -> None:
        """operational_burn can be zero (volunteer-only org)."""
        finance = RevolutionaryFinance(operational_burn=0.0)
        assert finance.operational_burn == 0.0

    # --- Dues Income (Currency [0, inf)) ---

    def test_dues_income_cannot_be_negative(self) -> None:
        """dues_income is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(dues_income=-1.0)

    def test_dues_income_can_be_zero(self) -> None:
        """dues_income can be zero (no paying members)."""
        finance = RevolutionaryFinance(dues_income=0.0)
        assert finance.dues_income == 0.0

    # --- Expropriation Income (Currency [0, inf)) ---

    def test_expropriation_income_cannot_be_negative(self) -> None:
        """expropriation_income is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(expropriation_income=-5.0)

    def test_expropriation_income_can_be_zero(self) -> None:
        """expropriation_income can be zero (no direct action)."""
        finance = RevolutionaryFinance(expropriation_income=0.0)
        assert finance.expropriation_income == 0.0

    # --- Donor Income (Currency [0, inf)) ---

    def test_donor_income_cannot_be_negative(self) -> None:
        """donor_income is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(donor_income=-3.0)

    def test_donor_income_can_be_zero(self) -> None:
        """donor_income can be zero (no liberal funding)."""
        finance = RevolutionaryFinance(donor_income=0.0)
        assert finance.donor_income == 0.0

    # --- Heat (Intensity [0, 1]) ---

    def test_heat_cannot_be_negative(self) -> None:
        """heat is Intensity type [0, 1]."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(heat=-0.1)

    def test_heat_cannot_exceed_one(self) -> None:
        """heat is Intensity type [0, 1]."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(heat=1.5)

    def test_heat_boundary_zero(self) -> None:
        """Heat can be 0.0 (no state attention)."""
        finance = RevolutionaryFinance(heat=0.0)
        assert finance.heat == 0.0

    def test_heat_boundary_one(self) -> None:
        """Heat can be 1.0 (maximum state attention - imminent crackdown)."""
        finance = RevolutionaryFinance(heat=1.0)
        assert finance.heat == 1.0

    def test_heat_boundary_midpoint(self) -> None:
        """Heat can be 0.5 (moderate surveillance)."""
        finance = RevolutionaryFinance(heat=TC.Probability.MIDPOINT)
        assert finance.heat == TC.Probability.MIDPOINT

    # --- Reformist Drift (Ideology [-1, 1]) ---

    def test_reformist_drift_cannot_be_less_than_minus_one(self) -> None:
        """reformist_drift is Ideology type [-1, 1]."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(reformist_drift=-1.5)

    def test_reformist_drift_cannot_exceed_one(self) -> None:
        """reformist_drift is Ideology type [-1, 1]."""
        with pytest.raises(ValidationError):
            RevolutionaryFinance(reformist_drift=1.5)

    def test_reformist_drift_boundary_negative_one(self) -> None:
        """Reformist drift can be -1.0 (fully revolutionary)."""
        finance = RevolutionaryFinance(reformist_drift=-1.0)
        assert finance.reformist_drift == -1.0

    def test_reformist_drift_boundary_positive_one(self) -> None:
        """Reformist drift can be 1.0 (fully co-opted/reformist)."""
        finance = RevolutionaryFinance(reformist_drift=1.0)
        assert finance.reformist_drift == 1.0

    def test_reformist_drift_boundary_zero(self) -> None:
        """Reformist drift can be 0.0 (ideologically neutral)."""
        finance = RevolutionaryFinance(reformist_drift=0.0)
        assert finance.reformist_drift == 0.0


# =============================================================================
# DEFAULT VALUES TESTS
# =============================================================================


@pytest.mark.ledger
class TestRevolutionaryFinanceDefaults:
    """RevolutionaryFinance should have defaults matching specification."""

    def test_war_chest_defaults_to_5(self) -> None:
        """War chest defaults to 5.0 (minimal starting funds)."""
        finance = RevolutionaryFinance()
        assert finance.war_chest == TC.RevolutionaryFinance.DEFAULT_WAR_CHEST

    def test_operational_burn_defaults_to_2(self) -> None:
        """Operational burn defaults to 2.0 (minimum spend per tick)."""
        finance = RevolutionaryFinance()
        assert finance.operational_burn == TC.RevolutionaryFinance.DEFAULT_OPERATIONAL_BURN

    def test_dues_income_defaults_to_1(self) -> None:
        """Dues income defaults to 1.0 (member contributions)."""
        finance = RevolutionaryFinance()
        assert finance.dues_income == TC.RevolutionaryFinance.DEFAULT_DUES_INCOME

    def test_expropriation_income_defaults_to_0(self) -> None:
        """Expropriation income defaults to 0.0 (no direct action)."""
        finance = RevolutionaryFinance()
        assert finance.expropriation_income == TC.RevolutionaryFinance.DEFAULT_EXPROPRIATION

    def test_donor_income_defaults_to_0(self) -> None:
        """Donor income defaults to 0.0 (no liberal funding)."""
        finance = RevolutionaryFinance()
        assert finance.donor_income == TC.RevolutionaryFinance.DEFAULT_DONOR_INCOME

    def test_heat_defaults_to_0(self) -> None:
        """Heat defaults to 0.0 (no state attention)."""
        finance = RevolutionaryFinance()
        assert finance.heat == TC.RevolutionaryFinance.DEFAULT_HEAT

    def test_reformist_drift_defaults_to_0(self) -> None:
        """Reformist drift defaults to 0.0 (ideologically neutral start)."""
        finance = RevolutionaryFinance()
        assert finance.reformist_drift == TC.RevolutionaryFinance.DEFAULT_REFORMIST_DRIFT


# =============================================================================
# COMPUTED FIELD TESTS (if any)
# =============================================================================


@pytest.mark.math
class TestRevolutionaryFinanceComputed:
    """Test computed fields and derived calculations for RevolutionaryFinance.

    Note: RevolutionaryFinance spec doesn't define explicit computed fields,
    but these tests verify important derived calculations that systems will use.
    """

    def test_total_income_calculation(self) -> None:
        """Total income = dues + expropriation + donor income.

        This isn't a model field but a common calculation.
        """
        finance = RevolutionaryFinance(
            dues_income=TC.RevolutionaryFinance.DUES_INCOME,
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_STANDARD,
            donor_income=TC.RevolutionaryFinance.DONOR_STANDARD,
        )
        total_income = finance.dues_income + finance.expropriation_income + finance.donor_income
        assert total_income == pytest.approx(TC.RevolutionaryFinance.TOTAL_INCOME_FULL)

    def test_net_flow_calculation(self) -> None:
        """Net flow = total income - operational burn.

        Positive = growing war chest, Negative = depleting.
        """
        finance = RevolutionaryFinance(
            operational_burn=TC.RevolutionaryFinance.OPERATIONAL_BURN,
            dues_income=TC.RevolutionaryFinance.DUES_INCOME,
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_MODERATE,
            donor_income=TC.RevolutionaryFinance.DEFAULT_DONOR_INCOME,
        )
        total_income = finance.dues_income + finance.expropriation_income + finance.donor_income
        net_flow = total_income - finance.operational_burn
        assert net_flow == pytest.approx(
            TC.RevolutionaryFinance.NET_FLOW_POSITIVE
        )  # Positive: sustainable

    def test_ticks_until_bankruptcy(self) -> None:
        """Calculate how many ticks until war chest depleted.

        If net flow is negative, war_chest / abs(net_flow) = ticks.
        """
        finance = RevolutionaryFinance(
            war_chest=TC.RevolutionaryFinance.BANKRUPTCY,
            operational_burn=TC.RevolutionaryFinance.OPERATIONAL_BURN,
            dues_income=TC.RevolutionaryFinance.DEFAULT_DUES_INCOME,
            expropriation_income=TC.RevolutionaryFinance.DEFAULT_EXPROPRIATION,
            donor_income=TC.RevolutionaryFinance.DEFAULT_DONOR_INCOME,
        )
        total_income = finance.dues_income + finance.expropriation_income + finance.donor_income
        net_flow = total_income - finance.operational_burn
        assert net_flow < 0  # Negative: unsustainable
        ticks_until_bankrupt = finance.war_chest / abs(net_flow)
        assert ticks_until_bankrupt == pytest.approx(2.5)  # 10 / 4 = 2.5 ticks (computed result)

    def test_heat_danger_threshold(self) -> None:
        """Heat >= 0.8 represents imminent crackdown danger.

        This is a game logic threshold, not a validation rule.
        """
        finance_safe = RevolutionaryFinance(heat=TC.Probability.MIDPOINT)
        finance_danger = RevolutionaryFinance(heat=TC.Probability.VERY_HIGH)
        finance_extreme = RevolutionaryFinance(heat=TC.Probability.FULL)

        assert finance_safe.heat < TC.Probability.VERY_HIGH  # Safe zone
        assert finance_danger.heat >= TC.Probability.VERY_HIGH  # Danger zone
        assert finance_extreme.heat >= TC.Probability.VERY_HIGH  # Extreme danger


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.ledger
class TestRevolutionaryFinanceImmutability:
    """RevolutionaryFinance should be frozen (immutable after creation)."""

    def test_cannot_mutate_war_chest(self) -> None:
        """war_chest cannot be mutated after creation."""
        finance = RevolutionaryFinance()
        with pytest.raises(ValidationError):
            finance.war_chest = TC.RevolutionaryFinance.SIGNIFICANT_WAR_CHEST  # type: ignore[misc]

    def test_cannot_mutate_operational_burn(self) -> None:
        """operational_burn cannot be mutated after creation."""
        finance = RevolutionaryFinance()
        with pytest.raises(ValidationError):
            finance.operational_burn = TC.RevolutionaryFinance.DONOR_HEAVY  # type: ignore[misc]

    def test_cannot_mutate_dues_income(self) -> None:
        """dues_income cannot be mutated after creation."""
        finance = RevolutionaryFinance()
        with pytest.raises(ValidationError):
            finance.dues_income = TC.RevolutionaryFinance.DUES_MASS_ORG  # type: ignore[misc]

    def test_cannot_mutate_expropriation_income(self) -> None:
        """expropriation_income cannot be mutated after creation."""
        finance = RevolutionaryFinance()
        with pytest.raises(ValidationError):
            finance.expropriation_income = TC.RevolutionaryFinance.EXPROPRIATION_MILITANT  # type: ignore[misc]

    def test_cannot_mutate_donor_income(self) -> None:
        """donor_income cannot be mutated after creation."""
        finance = RevolutionaryFinance()
        with pytest.raises(ValidationError):
            finance.donor_income = TC.RevolutionaryFinance.DONOR_HEAVY  # type: ignore[misc]

    def test_cannot_mutate_heat(self) -> None:
        """heat cannot be mutated after creation."""
        finance = RevolutionaryFinance()
        with pytest.raises(ValidationError):
            finance.heat = TC.Probability.EXTREME  # type: ignore[misc]

    def test_cannot_mutate_reformist_drift(self) -> None:
        """reformist_drift cannot be mutated after creation."""
        finance = RevolutionaryFinance()
        with pytest.raises(ValidationError):
            finance.reformist_drift = TC.Ideology.LEANING_REACTIONARY  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestRevolutionaryFinanceSerialization:
    """RevolutionaryFinance should serialize correctly for Ledger storage."""

    def test_model_dump(self) -> None:
        """Can dump RevolutionaryFinance to dict."""
        finance = RevolutionaryFinance(
            war_chest=TC.RevolutionaryFinance.MODERATE_WAR_CHEST,
            operational_burn=TC.RevolutionaryFinance.OPERATIONAL_BURN,
            dues_income=TC.RevolutionaryFinance.DUES_INCOME,
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_STANDARD,
            donor_income=TC.RevolutionaryFinance.DONOR_STANDARD,
            heat=TC.Probability.HIGH,
            reformist_drift=TC.Ideology.LEANING_REVOLUTIONARY,
        )
        data = finance.model_dump()
        assert data["war_chest"] == TC.RevolutionaryFinance.MODERATE_WAR_CHEST
        assert data["operational_burn"] == TC.RevolutionaryFinance.OPERATIONAL_BURN
        assert data["dues_income"] == TC.RevolutionaryFinance.DUES_INCOME
        assert data["expropriation_income"] == TC.RevolutionaryFinance.EXPROPRIATION_STANDARD
        assert data["donor_income"] == TC.RevolutionaryFinance.DONOR_STANDARD
        assert data["heat"] == pytest.approx(TC.Probability.HIGH)
        assert data["reformist_drift"] == pytest.approx(TC.Ideology.LEANING_REVOLUTIONARY)

    def test_model_validate(self) -> None:
        """Can reconstruct RevolutionaryFinance from dict."""
        data = {
            "war_chest": TC.RevolutionaryFinance.MODERATE_WAR_CHEST,
            "operational_burn": TC.RevolutionaryFinance.OPERATIONAL_BURN,
            "dues_income": TC.RevolutionaryFinance.DUES_INCOME,
            "expropriation_income": TC.RevolutionaryFinance.EXPROPRIATION_STANDARD,
            "donor_income": TC.RevolutionaryFinance.DONOR_STANDARD,
            "heat": TC.Probability.HIGH,
            "reformist_drift": TC.Ideology.LEANING_REVOLUTIONARY,
        }
        finance = RevolutionaryFinance.model_validate(data)
        assert finance.war_chest == TC.RevolutionaryFinance.MODERATE_WAR_CHEST
        assert finance.operational_burn == TC.RevolutionaryFinance.OPERATIONAL_BURN
        assert finance.dues_income == TC.RevolutionaryFinance.DUES_INCOME
        assert finance.expropriation_income == TC.RevolutionaryFinance.EXPROPRIATION_STANDARD
        assert finance.donor_income == TC.RevolutionaryFinance.DONOR_STANDARD
        assert finance.heat == pytest.approx(TC.Probability.HIGH)
        assert finance.reformist_drift == pytest.approx(TC.Ideology.LEANING_REVOLUTIONARY)

    def test_json_round_trip(self) -> None:
        """RevolutionaryFinance survives JSON serialization round trip."""
        original = RevolutionaryFinance(
            war_chest=TC.RevolutionaryFinance.ELEVATED_WAR_CHEST,
            operational_burn=TC.RevolutionaryFinance.BURN_ELEVATED,
            dues_income=TC.RevolutionaryFinance.DUES_HIGH,
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_ELEVATED,
            donor_income=TC.RevolutionaryFinance.DONOR_MODERATE,
            heat=TC.Probability.BELOW_MIDPOINT,
            reformist_drift=TC.RevolutionaryFinance.DRIFT_MILD,
        )
        json_str = original.model_dump_json()
        restored = RevolutionaryFinance.model_validate_json(json_str)

        assert restored.war_chest == pytest.approx(original.war_chest)
        assert restored.operational_burn == pytest.approx(original.operational_burn)
        assert restored.dues_income == pytest.approx(original.dues_income)
        assert restored.expropriation_income == pytest.approx(original.expropriation_income)
        assert restored.donor_income == pytest.approx(original.donor_income)
        assert restored.heat == pytest.approx(original.heat)
        assert restored.reformist_drift == pytest.approx(original.reformist_drift)

    def test_dict_round_trip(self) -> None:
        """RevolutionaryFinance survives dict round-trip."""
        original = RevolutionaryFinance(
            war_chest=TC.RevolutionaryFinance.MODEST_WAR_CHEST,
            heat=TC.Probability.MODERATE,
        )
        data = original.model_dump()
        restored = RevolutionaryFinance.model_validate(data)

        assert restored.war_chest == original.war_chest
        assert restored.heat == original.heat


# =============================================================================
# STRATEGIC TENSION TESTS
# =============================================================================


@pytest.mark.math
class TestRevolutionaryFinanceStrategicTensions:
    """Tests for the strategic tensions inherent in revolutionary finance.

    These tests document the game design intent:
    - Donor income causes reformist drift (ideological corruption)
    - Expropriation income generates heat (state attention)
    - Dues income is sustainable but limited by organization size
    """

    def test_donor_dependent_org_has_high_reformist_drift(self) -> None:
        """Organizations relying on donors tend toward reformism.

        This isn't enforced by the model but is a game design expectation.
        Systems will increase reformist_drift when donor_income is high.
        """
        # Donor-heavy org
        ngo_style = RevolutionaryFinance(
            dues_income=TC.RevolutionaryFinance.DUES_LOW,
            donor_income=TC.RevolutionaryFinance.DONOR_HEAVY,
            expropriation_income=TC.RevolutionaryFinance.DEFAULT_EXPROPRIATION,
            reformist_drift=TC.RevolutionaryFinance.DRIFT_HIGH,  # Already drifting right
        )
        assert ngo_style.donor_income > ngo_style.dues_income
        assert (
            ngo_style.reformist_drift > TC.RevolutionaryFinance.DEFAULT_REFORMIST_DRIFT
        )  # Positive = reformist

    def test_expropriation_heavy_org_has_high_heat(self) -> None:
        """Organizations engaging in expropriation attract state attention.

        This isn't enforced by the model but is a game design expectation.
        Systems will increase heat when expropriation_income is high.
        """
        # Action-heavy org
        militant = RevolutionaryFinance(
            dues_income=TC.RevolutionaryFinance.DEFAULT_DUES_INCOME,
            donor_income=TC.RevolutionaryFinance.DEFAULT_DONOR_INCOME,
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_MILITANT,
            heat=TC.Probability.VERY_HIGH,  # High state attention
        )
        assert militant.expropriation_income > militant.dues_income
        assert militant.heat >= TC.Probability.VERY_HIGH  # Danger zone

    def test_dues_based_org_is_sustainable(self) -> None:
        """Organizations funded by dues maintain ideological integrity.

        Dues-based funding neither attracts heat nor causes drift,
        but is limited by organizational capacity.
        """
        # Mass org with dues
        mass_org = RevolutionaryFinance(
            dues_income=TC.RevolutionaryFinance.DUES_MASS_ORG,
            donor_income=TC.RevolutionaryFinance.DEFAULT_DONOR_INCOME,
            expropriation_income=TC.RevolutionaryFinance.DEFAULT_EXPROPRIATION,
            heat=TC.RevolutionaryFinance.DEFAULT_HEAT,
            reformist_drift=TC.RevolutionaryFinance.DEFAULT_REFORMIST_DRIFT,
        )
        assert mass_org.heat == TC.RevolutionaryFinance.DEFAULT_HEAT  # No state attention
        assert (
            mass_org.reformist_drift == TC.RevolutionaryFinance.DEFAULT_REFORMIST_DRIFT
        )  # Ideologically pure

    def test_mixed_funding_balances_risks(self) -> None:
        """Organizations can balance funding sources to manage risks.

        A mix of income sources trades off heat vs drift vs capacity.
        """
        balanced = RevolutionaryFinance(
            dues_income=TC.RevolutionaryFinance.DUES_MODERATE,
            donor_income=TC.RevolutionaryFinance.DONOR_LOW,
            expropriation_income=TC.RevolutionaryFinance.EXPROPRIATION_LOW,
            heat=TC.Probability.MODERATE,  # Moderate attention
            reformist_drift=TC.RevolutionaryFinance.DRIFT_SLIGHT,  # Slight drift
        )
        total_income = balanced.dues_income + balanced.donor_income + balanced.expropriation_income
        assert total_income == pytest.approx(TC.RevolutionaryFinance.BALANCED_TOTAL)
        # Balanced: not too hot, not too reformist
        assert TC.Probability.ZERO < balanced.heat < TC.Probability.VERY_HIGH
        assert (
            TC.Ideology.LEANING_REVOLUTIONARY
            < balanced.reformist_drift
            < TC.Ideology.LEANING_REACTIONARY
        )
