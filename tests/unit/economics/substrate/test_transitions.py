"""Unit tests for discrete ownership transitions (Feature 043)."""

import pytest

from babylon.economics.substrate.transitions import (
    apply_abandonment,
    apply_foreclosure,
    apply_purchase,
    evaluate_class_shares,
)
from babylon.economics.substrate.types import HexEconomicState, HexTenureComposition
from babylon.models.enums import SocialRole


@pytest.fixture
def base_state() -> HexEconomicState:
    """Fixture providing a known baseline HexEconomicState."""
    tenure = HexTenureComposition(
        residential_owner_occupied=0.4,
        residential_rental=0.2,
        commercial=0.1,
        industrial=0.1,
        public=0.1,
        trust_land=0.0,
        vacant_abandoned=0.1,
    )
    return HexEconomicState(
        h3_index="872830828ffffff",
        county_fips="26163",
        constant_capital=500.0,
        variable_capital=200.0,
        surplus_value=100.0,
        employment=50.0,
        dept_shares=(0.3, 0.3, 0.2, 0.2),
        tenure_composition=tenure,
    )


@pytest.mark.unit
class TestDiscreteTransitions:
    """Tests for discrete land ownership transitions."""

    def test_apply_foreclosure_to_vacant(self, base_state: HexEconomicState) -> None:
        """Test foreclosure converting owner-occupied to vacant."""
        new_state = apply_foreclosure(base_state, 0.1, to_rental=False)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_owner_occupied - 0.3) < 1e-9
        assert abs(t.vacant_abandoned - 0.2) < 1e-9
        assert abs(t.residential_rental - 0.2) < 1e-9  # unchanged

    def test_apply_foreclosure_to_rental(self, base_state: HexEconomicState) -> None:
        """Test foreclosure converting owner-occupied to rental."""
        new_state = apply_foreclosure(base_state, 0.1, to_rental=True)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_owner_occupied - 0.3) < 1e-9
        assert abs(t.residential_rental - 0.3) < 1e-9
        assert abs(t.vacant_abandoned - 0.1) < 1e-9  # unchanged

    def test_apply_foreclosure_clamp(self, base_state: HexEconomicState) -> None:
        """Test foreclosure clamping when fraction exceeds available."""
        # Try to foreclose 0.5 when only 0.4 exists
        new_state = apply_foreclosure(base_state, 0.5, to_rental=False)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_owner_occupied - 0.0) < 1e-9
        assert abs(t.vacant_abandoned - 0.5) < 1e-9

    def test_apply_purchase(self, base_state: HexEconomicState) -> None:
        """Test purchase converting rental to owner-occupied."""
        new_state = apply_purchase(base_state, 0.1)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_rental - 0.1) < 1e-9
        assert abs(t.residential_owner_occupied - 0.5) < 1e-9

    def test_apply_purchase_clamp(self, base_state: HexEconomicState) -> None:
        """Test purchase clamping when fraction exceeds available rental."""
        # Try to purchase 0.5 when only 0.2 exists
        new_state = apply_purchase(base_state, 0.5)
        t = new_state.tenure_composition
        assert t is not None
        assert abs(t.residential_rental - 0.0) < 1e-9
        assert abs(t.residential_owner_occupied - 0.6) < 1e-9

    def test_apply_abandonment(self, base_state: HexEconomicState) -> None:
        """Test abandonment converting proportional residential to vacant."""
        # Abandon 0.3 from total residential (0.4 owner + 0.2 rental = 0.6)
        # So half of total residential is abandoned.
        new_state = apply_abandonment(base_state, 0.3)
        t = new_state.tenure_composition
        assert t is not None

        # 4/6 of 0.3 = 0.2 owner lost
        assert abs(t.residential_owner_occupied - 0.2) < 1e-9
        # 2/6 of 0.3 = 0.1 rental lost
        assert abs(t.residential_rental - 0.1) < 1e-9
        # 0.1 original + 0.3 new = 0.4
        assert abs(t.vacant_abandoned - 0.4) < 1e-9

    def test_missing_tenure_composition_noop(self, base_state: HexEconomicState) -> None:
        """Test that transitions are NOOP if tenure_composition is missing."""
        empty_state = base_state.model_copy(update={"tenure_composition": None})
        res1 = apply_foreclosure(empty_state, 0.1)
        assert res1 is empty_state
        res2 = apply_purchase(empty_state, 0.1)
        assert res2 is empty_state
        res3 = apply_abandonment(empty_state, 0.1)
        assert res3 is empty_state

    def test_evaluate_class_shares_with_equity(self, base_state: HexEconomicState) -> None:
        """Test that LA class position is properly constituted from property when equity is met."""
        tenure = base_state.tenure_composition
        assert tenure is not None
        shares = evaluate_class_shares(tenure, equity_threshold_met=True)

        # Owner-occupied (0.4) -> LA
        assert abs(shares[SocialRole.LABOR_ARISTOCRACY] - 0.4) < 1e-9
        # Rental (0.2) -> Proletariat
        assert abs(shares[SocialRole.INTERNAL_PROLETARIAT] - 0.2) < 1e-9
        # Vacant (0.1) -> Lumpenproletariat
        assert abs(shares[SocialRole.LUMPENPROLETARIAT] - 0.1) < 1e-9
        # Commercial (0.1) + Industrial (0.1) -> Bourgeoisie (0.2)
        assert abs(shares[SocialRole.CORE_BOURGEOISIE] - 0.2) < 1e-9

    def test_evaluate_class_shares_without_equity(self, base_state: HexEconomicState) -> None:
        """Test that missing equity threshold demotes owner-occupancy to Proletariat classification."""
        tenure = base_state.tenure_composition
        assert tenure is not None
        shares = evaluate_class_shares(tenure, equity_threshold_met=False)

        # Owner-occupied (0.4) fails equity test -> Proletariat
        assert abs(shares[SocialRole.LABOR_ARISTOCRACY] - 0.0) < 1e-9
        # PROLETARIAT = Owner-occupied (0.4) + Rental (0.2) = 0.6
        assert abs(shares[SocialRole.INTERNAL_PROLETARIAT] - 0.6) < 1e-9
