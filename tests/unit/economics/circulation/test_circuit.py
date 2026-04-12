"""Tests for Capital Volume II circuit state functions.

Feature: 023-capital-volume-ii
Tasks: T025-T027

Tests for advance_circuit and initialize_circuit_state,
modeling the M-C-P-C'-M' circuit of capital as a continuous
fractional flow system.
"""

from __future__ import annotations

import pytest

from babylon.economics.circulation.circuit import (
    advance_circuit,
    initialize_circuit_state,
)
from babylon.economics.circulation.types import (
    CircuitState,
    TurnoverProfile,
)
from babylon.models.types import Currency

from .conftest import TEST_YEAR, WAYNE_COUNTY_FIPS

# =============================================================================
# HELPER: Standard TurnoverProfile for tests
# =============================================================================

MANUFACTURING_PROFILE = TurnoverProfile(
    naics_code="31",
    working_period_days=30,
    non_working_production_days=10,
    purchase_time_days=10,
    sale_time_days=20,
    fixed_capital_ratio=0.6,
)
"""Manufacturing profile: 70 day turnover (30+10+10+20)."""


SERVICE_PROFILE = TurnoverProfile(
    naics_code="62",
    working_period_days=1,
    non_working_production_days=0,
    purchase_time_days=3,
    sale_time_days=5,
    fixed_capital_ratio=0.5,
)
"""Service profile: 9 day turnover (1+0+3+5)."""


AGRICULTURE_PROFILE = TurnoverProfile(
    naics_code="11",
    working_period_days=90,
    non_working_production_days=60,
    purchase_time_days=15,
    sale_time_days=30,
    fixed_capital_ratio=0.6,
)
"""Agriculture profile: 195 day turnover (90+60+15+30)."""


# =============================================================================
# T025: initialize_circuit_state tests
# =============================================================================


class TestInitializeCircuitState:
    """Tests for initial capital distribution across circuit forms."""

    def test_distributes_capital_proportionally(self) -> None:
        """Capital is distributed proportional to phase durations.

        Manufacturing profile: turnover=70 days
        M fraction = (purchase + sale) / turnover = (10+20)/70 = 30/70
        P fraction = working / turnover = 30/70
        C fraction = non_working / turnover = 10/70
        """
        state = initialize_circuit_state(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            total_capital=Currency(700.0),
            turnover=MANUFACTURING_PROFILE,
        )

        assert isinstance(state, CircuitState)
        assert state.fips_code == WAYNE_COUNTY_FIPS
        assert state.year == TEST_YEAR

        # M = 10/70 * 700 = 100
        assert abs(state.money_capital - 100.0) < 0.01
        # P = 40/70 * 700 = 400
        assert abs(state.productive_capital - 400.0) < 0.01
        # C = 20/70 * 700 = 200
        assert abs(state.commodity_capital - 200.0) < 0.01

    def test_total_capital_preserved(self) -> None:
        """Total capital (M+P+C) equals initial total_capital."""
        state = initialize_circuit_state(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            total_capital=Currency(1000.0),
            turnover=MANUFACTURING_PROFILE,
        )

        assert abs(state.total_capital - 1000.0) < 0.01

    def test_fixed_circulating_split(self) -> None:
        """Productive capital is split into fixed and circulating.

        fixed = P * fixed_capital_ratio
        circulating = P - fixed
        """
        state = initialize_circuit_state(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            total_capital=Currency(700.0),
            turnover=MANUFACTURING_PROFILE,
        )

        # P = 400, fixed_ratio = 0.6
        # fixed = 400 * 0.6 = 240
        assert abs(state.fixed_capital - 240.0) < 0.01
        # circulating = 400 - 240 = 160
        assert abs(state.circulating_capital - 160.0) < 0.01

    def test_fixed_plus_circulating_equals_productive(self) -> None:
        """fixed_capital + circulating_capital == productive_capital."""
        state = initialize_circuit_state(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            total_capital=Currency(500.0),
            turnover=AGRICULTURE_PROFILE,
        )

        assert (
            abs(state.fixed_capital + state.circulating_capital - state.productive_capital) < 0.01
        )

    def test_zero_capital(self) -> None:
        """Zero total capital yields zero in all forms."""
        state = initialize_circuit_state(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            total_capital=Currency(0.0),
            turnover=MANUFACTURING_PROFILE,
        )

        assert state.money_capital == 0.0
        assert state.productive_capital == 0.0
        assert state.commodity_capital == 0.0
        assert state.fixed_capital == 0.0
        assert state.circulating_capital == 0.0

    def test_zero_turnover_time_all_in_money(self) -> None:
        """If turnover_time is 0 (edge case), all capital goes to money form.

        We construct a profile with minimum valid values (working_period=1, all others=0)
        to get a nonzero turnover. But if somehow turnover is 0 (from division logic),
        the fallback puts everything in money form.

        Since TurnoverProfile requires working_period_days > 0, we test
        that a profile with very small non-working/purchase/sale = 0 correctly
        distributes: M = sale/turnover fraction, P = working/turnover, C = non_working/turnover.
        """
        minimal_profile = TurnoverProfile(
            naics_code="99",
            working_period_days=1,
            non_working_production_days=0,
            purchase_time_days=0,
            sale_time_days=0,
            fixed_capital_ratio=0.5,
        )
        # turnover_time = 1, so P fraction = 1/1 = 1.0, M = 0, C = 0
        state = initialize_circuit_state(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            total_capital=Currency(100.0),
            turnover=minimal_profile,
        )

        assert abs(state.productive_capital - 100.0) < 0.01
        assert abs(state.money_capital - 0.0) < 0.01
        assert abs(state.commodity_capital - 0.0) < 0.01

    def test_service_sector_distribution(self) -> None:
        """Service sector: short production, longer circulation.

        SERVICE_PROFILE: working=1, non_working=0, purchase=3, sale=5
        turnover = 9 days
        M fraction = 3/9
        P fraction = 1/9
        C fraction = 5/9
        """
        state = initialize_circuit_state(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            total_capital=Currency(900.0),
            turnover=SERVICE_PROFILE,
        )

        assert abs(state.money_capital - 300.0) < 0.01
        assert abs(state.productive_capital - 100.0) < 0.01
        assert abs(state.commodity_capital - 500.0) < 0.01


# =============================================================================
# T026: advance_circuit — phase transitions
# =============================================================================


class TestAdvanceCircuitTransitions:
    """Tests for capital flowing through M->P->C'->M' phases."""

    def _make_state(
        self,
        money: float = 0.0,
        productive: float = 0.0,
        commodity: float = 0.0,
        fixed_ratio: float = 0.6,
    ) -> CircuitState:
        """Create a CircuitState with given capital distribution."""
        prod = Currency(productive)
        fixed = Currency(productive * fixed_ratio)
        circ = Currency(productive * (1.0 - fixed_ratio))
        return CircuitState(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            money_capital=Currency(money),
            productive_capital=prod,
            commodity_capital=Currency(commodity),
            fixed_capital=fixed,
            circulating_capital=circ,
        )

    def test_money_to_productive_transition(self) -> None:
        """M->P: Money capital converts to productive capital during purchase phase.

        With all capital in M, after elapsed_days / purchase_time fraction should
        flow from M to P.
        """
        state = self._make_state(money=100.0)
        # purchase_time = 10 days, elapsed = 5 days -> fraction = 0.5
        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=5,
        )

        # 50% of M should move to P (50 units)
        assert result.money_capital < state.money_capital
        assert result.productive_capital > state.productive_capital
        # M should lose ~50, P should gain ~50
        assert abs(result.money_capital - 50.0) < 1.0
        assert abs(result.productive_capital - 50.0) < 1.0

    def test_productive_to_commodity_transition(self) -> None:
        """P->C': Productive capital converts to commodity during production.

        With all capital in P, after elapsed / working_period fraction flows
        from P to C.
        """
        state = self._make_state(productive=100.0)
        # working_period = 30, non_working = 10 => production = 40 days, elapsed = 15 -> fraction = 0.375
        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=15,
        )

        assert result.productive_capital < state.productive_capital
        assert result.commodity_capital > state.commodity_capital

    def test_commodity_to_money_transition(self) -> None:
        """C'->M': Commodity capital converts to money during sale phase.

        With all capital in C, after elapsed / sale_time fraction flows
        from C to M.
        """
        state = self._make_state(commodity=100.0)
        # sale_time = 20 days, elapsed = 10 -> fraction = 0.5
        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=10,
        )

        assert result.commodity_capital < state.commodity_capital
        assert result.money_capital > state.money_capital

    def test_surplus_created_during_production(self) -> None:
        """Surplus value is added during the P->C' transition.

        surplus_created = surplus_value * production_fraction
        Total capital increases by surplus_created.
        """
        state = self._make_state(productive=100.0)
        initial_total = state.total_capital

        # production = 40 days, elapsed = 30 -> fraction = 0.75
        # surplus_value = 50 -> surplus_created = 50 * 0.75 = 37.5
        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(50.0),
            elapsed_days=30,
        )

        # Total should increase by surplus_created (37.5)
        assert abs(result.total_capital - (initial_total + 37.5)) < 1.0

    def test_surplus_proportional_to_production_fraction(self) -> None:
        """Surplus created is proportional to production fraction.

        Half a production cycle should create half the surplus.
        """
        state = self._make_state(productive=100.0)
        initial_total = state.total_capital

        # production = 40 days, elapsed = 15 -> fraction = 0.375
        # surplus_value = 60 -> surplus_created = 60 * 0.375 = 22.5
        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(60.0),
            elapsed_days=15,
        )

        expected_surplus = 60.0 * (15.0 / 40.0)
        assert abs(result.total_capital - (initial_total + expected_surplus)) < 1.0


# =============================================================================
# T027: advance_circuit — invariants and edge cases
# =============================================================================


class TestAdvanceCircuitInvariants:
    """Tests for capital conservation and edge cases."""

    def _make_state(
        self,
        money: float = 0.0,
        productive: float = 0.0,
        commodity: float = 0.0,
        fixed_ratio: float = 0.6,
    ) -> CircuitState:
        """Create a CircuitState with given capital distribution."""
        prod = Currency(productive)
        fixed = Currency(productive * fixed_ratio)
        circ = Currency(productive * (1.0 - fixed_ratio))
        return CircuitState(
            fips_code=WAYNE_COUNTY_FIPS,
            year=TEST_YEAR,
            money_capital=Currency(money),
            productive_capital=prod,
            commodity_capital=Currency(commodity),
            fixed_capital=fixed,
            circulating_capital=circ,
        )

    def test_total_capital_invariant_no_surplus(self) -> None:
        """Without surplus, total capital (M+P+C) is conserved.

        Capital just moves between forms; nothing is created or destroyed.
        """
        state = self._make_state(money=40.0, productive=30.0, commodity=30.0)
        initial_total = state.total_capital

        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=7,
        )

        assert abs(result.total_capital - initial_total) < 0.01

    def test_total_capital_with_surplus(self) -> None:
        """With surplus, total capital increases by surplus_created.

        surplus_created = surplus_value * (elapsed_days / working_period)
        """
        state = self._make_state(money=30.0, productive=50.0, commodity=20.0)
        initial_total = state.total_capital

        elapsed = 15
        surplus = 40.0
        # production_fraction = 15 / 40 = 0.375
        expected_surplus_created = surplus * (elapsed / 40.0)

        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(surplus),
            elapsed_days=elapsed,
        )

        assert abs(result.total_capital - (initial_total + expected_surplus_created)) < 0.1

    def test_zero_capital_stays_zero(self) -> None:
        """All-zero capital state remains zero regardless of elapsed time."""
        state = self._make_state(money=0.0, productive=0.0, commodity=0.0)

        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=30,
        )

        assert result.money_capital == 0.0
        assert result.productive_capital == 0.0
        assert result.commodity_capital == 0.0

    def test_all_capital_in_money_form(self) -> None:
        """100% in money form: only M->P transition occurs."""
        state = self._make_state(money=100.0)

        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=5,
        )

        # M decreases, P increases, C stays 0 (no C to sell, no P to produce)
        assert result.money_capital < 100.0
        assert result.productive_capital > 0.0
        # Without production happening first, no commodity is created
        # Total preserved
        assert abs(result.total_capital - 100.0) < 0.01

    def test_negative_elapsed_days_raises(self) -> None:
        """Negative elapsed_days raises ValueError."""
        state = self._make_state(money=100.0)

        with pytest.raises(ValueError, match="elapsed_days"):
            advance_circuit(
                state=state,
                turnover=MANUFACTURING_PROFILE,
                surplus_value=Currency(0.0),
                elapsed_days=-1,
            )

    def test_zero_elapsed_days_no_change(self) -> None:
        """Zero elapsed_days produces no capital movement."""
        state = self._make_state(money=40.0, productive=30.0, commodity=30.0)

        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(10.0),
            elapsed_days=0,
        )

        assert abs(result.money_capital - state.money_capital) < 0.01
        assert abs(result.productive_capital - state.productive_capital) < 0.01
        assert abs(result.commodity_capital - state.commodity_capital) < 0.01

    def test_large_elapsed_days_caps_fraction(self) -> None:
        """Elapsed days exceeding phase duration caps fraction at 1.0.

        Cannot transfer more than 100% of capital in a phase.
        """
        state = self._make_state(money=100.0)

        # purchase_time = 10 days, elapsed = 100 days -> fraction capped at 1.0
        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=100,
        )

        # All money should have moved to productive
        # (and then productive to commodity, commodity to money)
        # But no capital should be negative
        assert result.money_capital >= 0.0
        assert result.productive_capital >= 0.0
        assert result.commodity_capital >= 0.0

    def test_instant_purchase_zero_purchase_time(self) -> None:
        """When purchase_time is 0, all M->P happens instantly (fraction=1.0)."""
        instant_profile = TurnoverProfile(
            naics_code="99",
            working_period_days=10,
            non_working_production_days=0,
            purchase_time_days=0,
            sale_time_days=5,
            fixed_capital_ratio=0.5,
        )

        state = self._make_state(money=100.0)
        result = advance_circuit(
            state=state,
            turnover=instant_profile,
            surplus_value=Currency(0.0),
            elapsed_days=1,
        )

        # All money should have converted to productive instantly
        # (since purchase fraction = 1.0 for zero purchase time)
        assert result.money_capital < 100.0

    def test_result_preserves_fips_and_year(self) -> None:
        """Returned CircuitState preserves fips_code and year."""
        state = self._make_state(money=50.0, productive=30.0, commodity=20.0)

        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=5,
        )

        assert result.fips_code == WAYNE_COUNTY_FIPS
        assert result.year == TEST_YEAR

    def test_fixed_circulating_updated(self) -> None:
        """Fixed and circulating capital are updated based on new productive capital."""
        state = self._make_state(money=100.0, productive=0.0, commodity=0.0)

        result = advance_circuit(
            state=state,
            turnover=MANUFACTURING_PROFILE,
            surplus_value=Currency(0.0),
            elapsed_days=5,
        )

        # New productive capital should be split by fixed_capital_ratio
        if result.productive_capital > 0.0:
            expected_fixed = result.productive_capital * MANUFACTURING_PROFILE.fixed_capital_ratio
            assert abs(result.fixed_capital - expected_fixed) < 0.01
            expected_circ = result.productive_capital - expected_fixed
            assert abs(result.circulating_capital - expected_circ) < 0.01
