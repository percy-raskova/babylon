"""Tests for StateFinance model.

TDD Red Phase: These tests define the contract for StateFinance.
StateFinance tracks the financial state of sovereign entities (states)
including treasury, budgets, taxation, tribute, and debt.

Epoch 1 (The Ledger) - Political Economy of Liquidity specification.

The StateFinance model represents the fiscal capacity of a state actor:
- Treasury: available liquid funds for deployment
- Budgets: allocated spending on repression (police) and social reproduction (welfare)
- Taxation: extraction rate from bourgeoisie class
- Tribute: imperial rent flowing from CLIENT_STATE relationships
- Debt: accumulated liabilities with ceiling constraint

Key computed field:
- burn_rate: police_budget + social_reproduction_budget (spending per tick)
"""

import pytest
from pydantic import ValidationError
from tests.constants import TestConstants

# This import will fail until model exists - that's the RED phase!
from babylon.models.entities.state_finance import StateFinance

# Aliases for readability
TC = TestConstants

# =============================================================================
# CREATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestStateFinanceCreation:
    """StateFinance should be createable with valid data."""

    def test_minimal_creation(self) -> None:
        """Can create StateFinance with all defaults."""
        finance = StateFinance()
        assert finance.treasury == TC.StateFinance.DEFAULT_TREASURY

    def test_with_custom_treasury(self) -> None:
        """Can create StateFinance with custom treasury."""
        finance = StateFinance(treasury=TC.StateFinance.HEALTHY_TREASURY)
        assert finance.treasury == TC.StateFinance.HEALTHY_TREASURY

    def test_with_custom_police_budget(self) -> None:
        """Can create StateFinance with custom police budget."""
        finance = StateFinance(police_budget=TC.StateFinance.ELEVATED_WELFARE_BUDGET)
        assert finance.police_budget == TC.StateFinance.ELEVATED_WELFARE_BUDGET

    def test_with_custom_social_reproduction_budget(self) -> None:
        """Can create StateFinance with custom social reproduction budget."""
        finance = StateFinance(social_reproduction_budget=TC.StateFinance.HIGH_WELFARE_BUDGET)
        assert finance.social_reproduction_budget == TC.StateFinance.HIGH_WELFARE_BUDGET

    def test_with_custom_tax_rate(self) -> None:
        """Can create StateFinance with custom tax rate."""
        finance = StateFinance(tax_rate=TC.StateFinance.CONFISCATORY_TAX_RATE)
        assert finance.tax_rate == TC.StateFinance.CONFISCATORY_TAX_RATE

    def test_with_custom_tribute_income(self) -> None:
        """Can create StateFinance with custom tribute income."""
        finance = StateFinance(tribute_income=TC.Wealth.MODEST)
        assert finance.tribute_income == TC.Wealth.MODEST

    def test_with_custom_debt_level(self) -> None:
        """Can create StateFinance with custom debt level."""
        finance = StateFinance(debt_level=TC.Wealth.SIGNIFICANT)
        assert finance.debt_level == TC.Wealth.SIGNIFICANT

    def test_with_custom_debt_ceiling(self) -> None:
        """Can create StateFinance with custom debt ceiling."""
        finance = StateFinance(debt_ceiling=TC.StateFinance.HIGH_DEBT_CEILING)
        assert finance.debt_ceiling == TC.StateFinance.HIGH_DEBT_CEILING

    def test_full_custom_creation(self) -> None:
        """Can create StateFinance with all custom field values."""
        finance = StateFinance(
            treasury=TC.StateFinance.MODERATE_TREASURY,
            police_budget=TC.StateFinance.ELEVATED_POLICE_BUDGET,
            social_reproduction_budget=TC.StateFinance.HIGH_WELFARE_BUDGET,
            tax_rate=TC.StateFinance.CONFISCATORY_TAX_RATE,
            tribute_income=TC.Wealth.MODEST,
            debt_level=TC.Wealth.SIGNIFICANT,
            debt_ceiling=TC.StateFinance.HIGH_DEBT_CEILING,
        )
        assert finance.treasury == TC.StateFinance.MODERATE_TREASURY
        assert finance.police_budget == TC.StateFinance.ELEVATED_POLICE_BUDGET
        assert finance.social_reproduction_budget == TC.StateFinance.HIGH_WELFARE_BUDGET
        assert finance.tax_rate == TC.StateFinance.CONFISCATORY_TAX_RATE
        assert finance.tribute_income == TC.Wealth.MODEST
        assert finance.debt_level == TC.Wealth.SIGNIFICANT
        assert finance.debt_ceiling == TC.StateFinance.HIGH_DEBT_CEILING


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestStateFinanceValidation:
    """StateFinance should validate its fields according to type constraints."""

    # --- Treasury (Currency [0, inf)) ---

    def test_treasury_cannot_be_negative(self) -> None:
        """treasury is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            StateFinance(treasury=-10.0)

    def test_treasury_can_be_zero(self) -> None:
        """treasury can be zero (bankrupt state)."""
        finance = StateFinance(treasury=0.0)
        assert finance.treasury == 0.0

    def test_treasury_can_be_large(self) -> None:
        """treasury can be arbitrarily large."""
        finance = StateFinance(treasury=1_000_000.0)
        assert finance.treasury == 1_000_000.0

    # --- Police Budget (Currency [0, inf)) ---

    def test_police_budget_cannot_be_negative(self) -> None:
        """police_budget is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            StateFinance(police_budget=-5.0)

    def test_police_budget_can_be_zero(self) -> None:
        """police_budget can be zero (no repression spending)."""
        finance = StateFinance(police_budget=0.0)
        assert finance.police_budget == 0.0

    # --- Social Reproduction Budget (Currency [0, inf)) ---

    def test_social_reproduction_budget_cannot_be_negative(self) -> None:
        """social_reproduction_budget is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            StateFinance(social_reproduction_budget=-5.0)

    def test_social_reproduction_budget_can_be_zero(self) -> None:
        """social_reproduction_budget can be zero (no welfare spending)."""
        finance = StateFinance(social_reproduction_budget=0.0)
        assert finance.social_reproduction_budget == 0.0

    # --- Tax Rate (Coefficient [0, 1]) ---

    def test_tax_rate_cannot_be_negative(self) -> None:
        """tax_rate is Coefficient type [0, 1]."""
        with pytest.raises(ValidationError):
            StateFinance(tax_rate=-0.1)

    def test_tax_rate_cannot_exceed_one(self) -> None:
        """tax_rate is Coefficient type [0, 1]."""
        with pytest.raises(ValidationError):
            StateFinance(tax_rate=1.5)

    def test_tax_rate_boundary_zero(self) -> None:
        """Tax rate can be 0.0 (no taxation)."""
        finance = StateFinance(tax_rate=0.0)
        assert finance.tax_rate == 0.0

    def test_tax_rate_boundary_one(self) -> None:
        """Tax rate can be 1.0 (full confiscation)."""
        finance = StateFinance(tax_rate=1.0)
        assert finance.tax_rate == 1.0

    # --- Tribute Income (Currency [0, inf)) ---

    def test_tribute_income_cannot_be_negative(self) -> None:
        """tribute_income is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            StateFinance(tribute_income=-10.0)

    def test_tribute_income_can_be_zero(self) -> None:
        """tribute_income can be zero (no imperial rent)."""
        finance = StateFinance(tribute_income=0.0)
        assert finance.tribute_income == 0.0

    # --- Debt Level (Currency [0, inf)) ---

    def test_debt_level_cannot_be_negative(self) -> None:
        """debt_level is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            StateFinance(debt_level=-50.0)

    def test_debt_level_can_be_zero(self) -> None:
        """debt_level can be zero (no debt)."""
        finance = StateFinance(debt_level=0.0)
        assert finance.debt_level == 0.0

    # --- Debt Ceiling (Currency [0, inf)) ---

    def test_debt_ceiling_cannot_be_negative(self) -> None:
        """debt_ceiling is Currency type [0, inf)."""
        with pytest.raises(ValidationError):
            StateFinance(debt_ceiling=-100.0)

    def test_debt_ceiling_can_be_zero(self) -> None:
        """debt_ceiling can be zero (no borrowing allowed)."""
        finance = StateFinance(debt_ceiling=0.0)
        assert finance.debt_ceiling == 0.0


# =============================================================================
# DEFAULT VALUES TESTS
# =============================================================================


@pytest.mark.ledger
class TestStateFinanceDefaults:
    """StateFinance should have defaults matching specification."""

    def test_treasury_defaults_to_100(self) -> None:
        """Treasury defaults to 100.0 (starting liquidity)."""
        finance = StateFinance()
        assert finance.treasury == TC.StateFinance.DEFAULT_TREASURY

    def test_police_budget_defaults_to_10(self) -> None:
        """Police budget defaults to 10.0 (repression cost per tick)."""
        finance = StateFinance()
        assert finance.police_budget == TC.StateFinance.DEFAULT_POLICE_BUDGET

    def test_social_reproduction_budget_defaults_to_15(self) -> None:
        """Social reproduction budget defaults to 15.0 (welfare cost per tick)."""
        finance = StateFinance()
        assert finance.social_reproduction_budget == TC.StateFinance.DEFAULT_WELFARE_BUDGET

    def test_tax_rate_defaults_to_0_3(self) -> None:
        """Tax rate defaults to 0.3 (30% extraction from bourgeoisie)."""
        finance = StateFinance()
        assert finance.tax_rate == pytest.approx(TC.StateFinance.DEFAULT_TAX_RATE)

    def test_tribute_income_defaults_to_0(self) -> None:
        """Tribute income defaults to 0.0 (no CLIENT_STATE relationships)."""
        finance = StateFinance()
        assert finance.tribute_income == TC.EconomicFlow.NO_FLOW

    def test_debt_level_defaults_to_0(self) -> None:
        """Debt level defaults to 0.0 (no accumulated debt)."""
        finance = StateFinance()
        assert finance.debt_level == TC.EconomicFlow.NO_FLOW

    def test_debt_ceiling_defaults_to_500(self) -> None:
        """Debt ceiling defaults to 500.0 (max sustainable debt)."""
        finance = StateFinance()
        assert finance.debt_ceiling == TC.StateFinance.DEFAULT_DEBT_CEILING


# =============================================================================
# COMPUTED FIELD TESTS
# =============================================================================


@pytest.mark.math
class TestStateFinanceComputed:
    """Test computed fields for StateFinance."""

    def test_burn_rate_with_defaults(self) -> None:
        """burn_rate = police_budget + social_reproduction_budget.

        With defaults: 10.0 + 15.0 = 25.0
        """
        finance = StateFinance()
        expected_burn_rate = (
            TC.StateFinance.DEFAULT_POLICE_BUDGET + TC.StateFinance.DEFAULT_WELFARE_BUDGET
        )
        assert finance.burn_rate == pytest.approx(expected_burn_rate)

    def test_burn_rate_with_custom_budgets(self) -> None:
        """burn_rate computed from custom budgets."""
        finance = StateFinance(
            police_budget=TC.StateFinance.ELEVATED_POLICE_BUDGET,
            social_reproduction_budget=TC.StateFinance.HIGH_WELFARE_BUDGET,
        )
        expected = TC.StateFinance.ELEVATED_POLICE_BUDGET + TC.StateFinance.HIGH_WELFARE_BUDGET
        assert finance.burn_rate == pytest.approx(expected)

    def test_burn_rate_with_zero_police(self) -> None:
        """burn_rate when police budget is zero."""
        finance = StateFinance(
            police_budget=TC.Probability.ZERO,
            social_reproduction_budget=TC.StateFinance.DEFAULT_WELFARE_BUDGET,
        )
        assert finance.burn_rate == pytest.approx(TC.StateFinance.DEFAULT_WELFARE_BUDGET)

    def test_burn_rate_with_zero_welfare(self) -> None:
        """burn_rate when social reproduction budget is zero."""
        finance = StateFinance(
            police_budget=TC.StateFinance.DEFAULT_POLICE_BUDGET,
            social_reproduction_budget=TC.Probability.ZERO,
        )
        assert finance.burn_rate == pytest.approx(TC.StateFinance.DEFAULT_POLICE_BUDGET)

    def test_burn_rate_with_both_zero(self) -> None:
        """burn_rate when both budgets are zero (austerity)."""
        finance = StateFinance(
            police_budget=TC.Probability.ZERO,
            social_reproduction_budget=TC.Probability.ZERO,
        )
        assert finance.burn_rate == pytest.approx(TC.Probability.ZERO)

    def test_burn_rate_with_large_budgets(self) -> None:
        """burn_rate with large budget values."""
        finance = StateFinance(
            police_budget=TC.Wealth.HIGH,
            social_reproduction_budget=750.0,  # Large welfare budget
        )
        expected = TC.Wealth.HIGH + 750.0
        assert finance.burn_rate == pytest.approx(expected)


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.ledger
class TestStateFinanceImmutability:
    """StateFinance should be frozen (immutable after creation)."""

    def test_cannot_mutate_treasury(self) -> None:
        """treasury cannot be mutated after creation."""
        finance = StateFinance()
        with pytest.raises(ValidationError):
            finance.treasury = 50.0  # type: ignore[misc]

    def test_cannot_mutate_police_budget(self) -> None:
        """police_budget cannot be mutated after creation."""
        finance = StateFinance()
        with pytest.raises(ValidationError):
            finance.police_budget = 5.0  # type: ignore[misc]

    def test_cannot_mutate_social_reproduction_budget(self) -> None:
        """social_reproduction_budget cannot be mutated after creation."""
        finance = StateFinance()
        with pytest.raises(ValidationError):
            finance.social_reproduction_budget = 5.0  # type: ignore[misc]

    def test_cannot_mutate_tax_rate(self) -> None:
        """tax_rate cannot be mutated after creation."""
        finance = StateFinance()
        with pytest.raises(ValidationError):
            finance.tax_rate = 0.5  # type: ignore[misc]

    def test_cannot_mutate_tribute_income(self) -> None:
        """tribute_income cannot be mutated after creation."""
        finance = StateFinance()
        with pytest.raises(ValidationError):
            finance.tribute_income = 100.0  # type: ignore[misc]

    def test_cannot_mutate_debt_level(self) -> None:
        """debt_level cannot be mutated after creation."""
        finance = StateFinance()
        with pytest.raises(ValidationError):
            finance.debt_level = 200.0  # type: ignore[misc]

    def test_cannot_mutate_debt_ceiling(self) -> None:
        """debt_ceiling cannot be mutated after creation."""
        finance = StateFinance()
        with pytest.raises(ValidationError):
            finance.debt_ceiling = 1000.0  # type: ignore[misc]


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.ledger
class TestStateFinanceSerialization:
    """StateFinance should serialize correctly for Ledger storage."""

    def test_model_dump(self) -> None:
        """Can dump StateFinance to dict."""
        finance = StateFinance(
            treasury=150.0,
            police_budget=20.0,
            social_reproduction_budget=25.0,
            tax_rate=0.4,
            tribute_income=30.0,
            debt_level=50.0,
            debt_ceiling=600.0,
        )
        data = finance.model_dump()
        assert data["treasury"] == 150.0
        assert data["police_budget"] == 20.0
        assert data["social_reproduction_budget"] == 25.0
        assert data["tax_rate"] == pytest.approx(0.4)
        assert data["tribute_income"] == 30.0
        assert data["debt_level"] == 50.0
        assert data["debt_ceiling"] == 600.0

    def test_model_dump_includes_computed(self) -> None:
        """model_dump includes computed burn_rate field."""
        finance = StateFinance(
            police_budget=20.0,
            social_reproduction_budget=30.0,
        )
        data = finance.model_dump()
        assert "burn_rate" in data
        assert data["burn_rate"] == pytest.approx(50.0)

    def test_model_validate(self) -> None:
        """Can reconstruct StateFinance from dict."""
        data = {
            "treasury": 150.0,
            "police_budget": 20.0,
            "social_reproduction_budget": 25.0,
            "tax_rate": 0.4,
            "tribute_income": 30.0,
            "debt_level": 50.0,
            "debt_ceiling": 600.0,
        }
        finance = StateFinance.model_validate(data)
        assert finance.treasury == 150.0
        assert finance.police_budget == 20.0
        assert finance.social_reproduction_budget == 25.0
        assert finance.tax_rate == pytest.approx(0.4)
        assert finance.tribute_income == 30.0
        assert finance.debt_level == 50.0
        assert finance.debt_ceiling == 600.0

    def test_json_round_trip(self) -> None:
        """StateFinance survives JSON serialization round trip."""
        original = StateFinance(
            treasury=175.0,
            police_budget=15.0,
            social_reproduction_budget=20.0,
            tax_rate=0.35,
            tribute_income=40.0,
            debt_level=75.0,
            debt_ceiling=550.0,
        )
        json_str = original.model_dump_json()
        restored = StateFinance.model_validate_json(json_str)

        assert restored.treasury == pytest.approx(original.treasury)
        assert restored.police_budget == pytest.approx(original.police_budget)
        assert restored.social_reproduction_budget == pytest.approx(
            original.social_reproduction_budget
        )
        assert restored.tax_rate == pytest.approx(original.tax_rate)
        assert restored.tribute_income == pytest.approx(original.tribute_income)
        assert restored.debt_level == pytest.approx(original.debt_level)
        assert restored.debt_ceiling == pytest.approx(original.debt_ceiling)
        assert restored.burn_rate == pytest.approx(original.burn_rate)

    def test_dict_round_trip(self) -> None:
        """StateFinance survives dict round-trip."""
        original = StateFinance(
            treasury=200.0,
            tax_rate=0.5,
        )
        data = original.model_dump()
        restored = StateFinance.model_validate(data)

        assert restored.treasury == original.treasury
        assert restored.tax_rate == original.tax_rate
        assert restored.burn_rate == original.burn_rate


# =============================================================================
# FISCAL HEALTH HELPER TESTS
# =============================================================================


@pytest.mark.math
class TestStateFinanceFiscalHealth:
    """Tests for fiscal health calculations and thresholds."""

    def test_treasury_can_cover_burn_rate(self) -> None:
        """Treasury should typically cover at least one tick of spending."""
        finance = StateFinance(treasury=TC.StateFinance.DEFAULT_TREASURY)
        # Default burn_rate is 25.0 (10 + 15)
        ticks_sustainable = finance.treasury / finance.burn_rate
        assert ticks_sustainable >= 1.0

    def test_debt_level_below_ceiling(self) -> None:
        """Debt level should be below ceiling in healthy state."""
        finance = StateFinance(
            debt_level=TC.Wealth.SIGNIFICANT,
            debt_ceiling=TC.StateFinance.DEFAULT_DEBT_CEILING,
        )
        debt_ratio = finance.debt_level / finance.debt_ceiling
        assert debt_ratio < 1.0

    def test_debt_at_ceiling(self) -> None:
        """Debt at ceiling represents fiscal crisis."""
        finance = StateFinance(
            debt_level=TC.StateFinance.DEFAULT_DEBT_CEILING,
            debt_ceiling=TC.StateFinance.DEFAULT_DEBT_CEILING,
        )
        debt_ratio = finance.debt_level / finance.debt_ceiling
        assert debt_ratio == pytest.approx(1.0)

    def test_debt_above_ceiling_is_valid(self) -> None:
        """Debt can exceed ceiling (unsustainable but valid state).

        The debt_ceiling is a soft constraint - exceeding it should
        trigger crisis events but is not a validation error.
        """
        finance = StateFinance(
            debt_level=600.0,  # Exceeds ceiling
            debt_ceiling=TC.StateFinance.DEFAULT_DEBT_CEILING,
        )
        assert finance.debt_level > finance.debt_ceiling
