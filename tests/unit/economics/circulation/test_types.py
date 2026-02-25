"""Tests for Capital Volume II circulation type definitions.

Feature: 023-capital-volume-ii
Tasks: T004-T016

RED phase tests for all 19 entities in the circulation data model.
These tests will FAIL until the types module is implemented.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.circulation.types import (
    AnnualSurplusValue,
    CapitalForm,
    CircuitState,
    CirculationCrisisAssessment,
    CirculationCrisisState,
    CrisisSeverity,
    DepreciationFundState,
    DisproportionalityCrisis,
    FixedCapitalItem,
    InventoryDiagnosis,
    InventoryState,
    MoralDepreciation,
    PureCirculationCosts,
    RealizationCrisis,
    ReplacementCyclePosition,
    ReproductionAnalysis,
    ReproductionBalance,
    TransportationValue,
    TurnoverProfile,
)
from babylon.models.types import Currency

# =============================================================================
# T004: CapitalForm StrEnum
# =============================================================================


class TestCapitalForm:
    """Tests for CapitalForm StrEnum (M-C-M' circuit phases)."""

    def test_money_value(self) -> None:
        """CapitalForm.MONEY has string value 'money'."""
        assert CapitalForm.MONEY == "money"
        assert CapitalForm.MONEY.value == "money"

    def test_productive_value(self) -> None:
        """CapitalForm.PRODUCTIVE has string value 'productive'."""
        assert CapitalForm.PRODUCTIVE == "productive"
        assert CapitalForm.PRODUCTIVE.value == "productive"

    def test_commodity_value(self) -> None:
        """CapitalForm.COMMODITY has string value 'commodity'."""
        assert CapitalForm.COMMODITY == "commodity"
        assert CapitalForm.COMMODITY.value == "commodity"

    def test_membership_count(self) -> None:
        """CapitalForm has exactly 3 members."""
        assert len(CapitalForm) == 3

    def test_is_str_enum(self) -> None:
        """All CapitalForm values are strings for JSON serialization."""
        for form in CapitalForm:
            assert isinstance(form, str)
            assert isinstance(form.value, str)

    def test_membership_iteration_order(self) -> None:
        """CapitalForm members iterate in definition order: M -> P -> C."""
        forms = list(CapitalForm)
        assert forms == [
            CapitalForm.MONEY,
            CapitalForm.PRODUCTIVE,
            CapitalForm.COMMODITY,
        ]


# =============================================================================
# T004: ReplacementCyclePosition StrEnum
# =============================================================================


class TestReplacementCyclePosition:
    """Tests for ReplacementCyclePosition StrEnum."""

    def test_investment_boom_exists(self) -> None:
        """INVESTMENT_BOOM is a valid position."""
        assert ReplacementCyclePosition.INVESTMENT_BOOM is not None

    def test_expansion_exists(self) -> None:
        """EXPANSION is a valid position."""
        assert ReplacementCyclePosition.EXPANSION is not None

    def test_maintenance_exists(self) -> None:
        """MAINTENANCE is a valid position."""
        assert ReplacementCyclePosition.MAINTENANCE is not None

    def test_disinvestment_exists(self) -> None:
        """DISINVESTMENT is a valid position."""
        assert ReplacementCyclePosition.DISINVESTMENT is not None

    def test_membership_count(self) -> None:
        """ReplacementCyclePosition has exactly 4 members."""
        assert len(ReplacementCyclePosition) == 4

    def test_is_str_enum(self) -> None:
        """All ReplacementCyclePosition values are strings."""
        for pos in ReplacementCyclePosition:
            assert isinstance(pos, str)


# =============================================================================
# T004: InventoryDiagnosis StrEnum
# =============================================================================


class TestInventoryDiagnosis:
    """Tests for InventoryDiagnosis StrEnum."""

    def test_normal_exists(self) -> None:
        """NORMAL is a valid diagnosis."""
        assert InventoryDiagnosis.NORMAL is not None

    def test_overproduction_exists(self) -> None:
        """OVERPRODUCTION is a valid diagnosis."""
        assert InventoryDiagnosis.OVERPRODUCTION is not None

    def test_supply_crisis_exists(self) -> None:
        """SUPPLY_CRISIS is a valid diagnosis."""
        assert InventoryDiagnosis.SUPPLY_CRISIS is not None

    def test_membership_count(self) -> None:
        """InventoryDiagnosis has exactly 3 members."""
        assert len(InventoryDiagnosis) == 3

    def test_is_str_enum(self) -> None:
        """All InventoryDiagnosis values are strings."""
        for diag in InventoryDiagnosis:
            assert isinstance(diag, str)


# =============================================================================
# T004: CrisisSeverity StrEnum
# =============================================================================


class TestCrisisSeverity:
    """Tests for CrisisSeverity StrEnum."""

    def test_normal_exists(self) -> None:
        """NORMAL is a valid severity."""
        assert CrisisSeverity.NORMAL is not None

    def test_mild_slowdown_exists(self) -> None:
        """MILD_SLOWDOWN is a valid severity."""
        assert CrisisSeverity.MILD_SLOWDOWN is not None

    def test_recession_exists(self) -> None:
        """RECESSION is a valid severity."""
        assert CrisisSeverity.RECESSION is not None

    def test_crisis_exists(self) -> None:
        """CRISIS is a valid severity."""
        assert CrisisSeverity.CRISIS is not None

    def test_membership_count(self) -> None:
        """CrisisSeverity has exactly 4 members."""
        assert len(CrisisSeverity) == 4

    def test_is_str_enum(self) -> None:
        """All CrisisSeverity values are strings."""
        for sev in CrisisSeverity:
            assert isinstance(sev, str)

    def test_definition_order(self) -> None:
        """CrisisSeverity members are in escalating order."""
        severities = list(CrisisSeverity)
        assert severities == [
            CrisisSeverity.NORMAL,
            CrisisSeverity.MILD_SLOWDOWN,
            CrisisSeverity.RECESSION,
            CrisisSeverity.CRISIS,
        ]


# =============================================================================
# T005: CircuitState
# =============================================================================


class TestCircuitState:
    """Tests for CircuitState frozen Pydantic model (M-C-P circuit snapshot)."""

    def test_valid_construction(self) -> None:
        """CircuitState constructs with standard values."""
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(200.0),
            commodity_capital=Currency(50.0),
            fixed_capital=Currency(150.0),
            circulating_capital=Currency(100.0),
        )
        assert state.fips_code == "26163"
        assert state.year == 2022
        assert state.money_capital == pytest.approx(100.0)
        assert state.productive_capital == pytest.approx(200.0)
        assert state.commodity_capital == pytest.approx(50.0)

    def test_total_capital_computed(self) -> None:
        """total_capital = money + productive + commodity."""
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(200.0),
            commodity_capital=Currency(50.0),
            fixed_capital=Currency(150.0),
            circulating_capital=Currency(100.0),
        )
        assert state.total_capital == pytest.approx(350.0)

    def test_liquidity_ratio_computed(self) -> None:
        """liquidity_ratio = money / total_capital."""
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(200.0),
            commodity_capital=Currency(50.0),
            fixed_capital=Currency(150.0),
            circulating_capital=Currency(100.0),
        )
        # 100 / 350 = 0.2857...
        assert state.liquidity_ratio == pytest.approx(100.0 / 350.0)

    def test_commodity_overhang_computed(self) -> None:
        """commodity_overhang = commodity / total_capital."""
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(200.0),
            commodity_capital=Currency(50.0),
            fixed_capital=Currency(150.0),
            circulating_capital=Currency(100.0),
        )
        # 50 / 350 = 0.1428...
        assert state.commodity_overhang == pytest.approx(50.0 / 350.0)

    def test_zero_capital_edge_case(self) -> None:
        """When all capital forms are zero, both ratios return 0.0."""
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(0.0),
            productive_capital=Currency(0.0),
            commodity_capital=Currency(0.0),
            fixed_capital=Currency(0.0),
            circulating_capital=Currency(0.0),
        )
        assert state.total_capital == pytest.approx(0.0)
        assert state.liquidity_ratio == pytest.approx(0.0)
        assert state.commodity_overhang == pytest.approx(0.0)

    def test_frozen_immutability(self) -> None:
        """CircuitState is frozen (immutable)."""
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(200.0),
            commodity_capital=Currency(50.0),
            fixed_capital=Currency(150.0),
            circulating_capital=Currency(100.0),
        )
        with pytest.raises(ValidationError):
            state.money_capital = Currency(999.0)  # type: ignore[misc]

    def test_fips_code_five_digits(self) -> None:
        """FIPS code must be exactly 5 characters."""
        with pytest.raises(ValidationError):
            CircuitState(
                fips_code="261",
                year=2022,
                money_capital=Currency(100.0),
                productive_capital=Currency(200.0),
                commodity_capital=Currency(50.0),
                fixed_capital=Currency(150.0),
                circulating_capital=Currency(100.0),
            )

    def test_year_minimum(self) -> None:
        """Year must be >= 2010."""
        with pytest.raises(ValidationError):
            CircuitState(
                fips_code="26163",
                year=2009,
                money_capital=Currency(100.0),
                productive_capital=Currency(200.0),
                commodity_capital=Currency(50.0),
                fixed_capital=Currency(150.0),
                circulating_capital=Currency(100.0),
            )

    def test_negative_capital_rejected(self) -> None:
        """Negative capital values are rejected (Currency is >= 0)."""
        with pytest.raises(ValidationError):
            CircuitState(
                fips_code="26163",
                year=2022,
                money_capital=Currency(-1.0),  # type: ignore[arg-type]
                productive_capital=Currency(200.0),
                commodity_capital=Currency(50.0),
                fixed_capital=Currency(150.0),
                circulating_capital=Currency(100.0),
            )


# =============================================================================
# T006: TurnoverProfile
# =============================================================================


class TestTurnoverProfile:
    """Tests for TurnoverProfile frozen Pydantic model."""

    def test_valid_construction(self) -> None:
        """TurnoverProfile constructs with standard manufacturing values."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=5,
            purchase_time_days=10,
            sale_time_days=15,
            fixed_capital_ratio=0.6,
        )
        assert profile.naics_code == "31"
        assert profile.working_period_days == 30
        assert profile.fixed_capital_ratio == pytest.approx(0.6)

    def test_production_time_computed(self) -> None:
        """production_time = working_period + non_working_production."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=5,
            purchase_time_days=10,
            sale_time_days=15,
            fixed_capital_ratio=0.6,
        )
        assert profile.production_time == 35

    def test_circulation_time_computed(self) -> None:
        """circulation_time = purchase_time + sale_time."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=5,
            purchase_time_days=10,
            sale_time_days=15,
            fixed_capital_ratio=0.6,
        )
        assert profile.circulation_time == 25

    def test_turnover_time_computed(self) -> None:
        """turnover_time = production_time + circulation_time."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=5,
            purchase_time_days=10,
            sale_time_days=15,
            fixed_capital_ratio=0.6,
        )
        assert profile.turnover_time == 60

    def test_turnovers_per_year_computed(self) -> None:
        """turnovers_per_year = 365 / turnover_time."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=5,
            purchase_time_days=10,
            sale_time_days=15,
            fixed_capital_ratio=0.6,
        )
        # 365 / 60 = 6.0833...
        assert profile.turnovers_per_year == pytest.approx(365.0 / 60.0)

    def test_production_ratio_computed(self) -> None:
        """production_ratio = production_time / turnover_time."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=5,
            purchase_time_days=10,
            sale_time_days=15,
            fixed_capital_ratio=0.6,
        )
        # 35 / 60 = 0.5833...
        assert profile.production_ratio == pytest.approx(35.0 / 60.0)

    def test_zero_turnover_time_edge_case(self) -> None:
        """When turnover_time is zero, turnovers_per_year returns 0.0."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=1,
            non_working_production_days=0,
            purchase_time_days=0,
            sale_time_days=0,
            fixed_capital_ratio=0.5,
        )
        # turnover_time = 1, so turnovers_per_year = 365.0
        # Actually test the zero case properly: need working_period=0 but >0 required
        # Instead test minimal turnover: working_period=1, all others 0
        assert profile.turnovers_per_year == pytest.approx(365.0)

    def test_working_period_must_be_positive(self) -> None:
        """working_period_days must be > 0."""
        with pytest.raises(ValidationError):
            TurnoverProfile(
                naics_code="31",
                working_period_days=0,
                non_working_production_days=0,
                purchase_time_days=0,
                sale_time_days=0,
                fixed_capital_ratio=0.5,
            )

    def test_fixed_capital_ratio_bounds(self) -> None:
        """fixed_capital_ratio must be in [0, 1]."""
        with pytest.raises(ValidationError):
            TurnoverProfile(
                naics_code="31",
                working_period_days=30,
                non_working_production_days=0,
                purchase_time_days=0,
                sale_time_days=0,
                fixed_capital_ratio=1.5,
            )
        with pytest.raises(ValidationError):
            TurnoverProfile(
                naics_code="31",
                working_period_days=30,
                non_working_production_days=0,
                purchase_time_days=0,
                sale_time_days=0,
                fixed_capital_ratio=-0.1,
            )

    def test_frozen_immutability(self) -> None:
        """TurnoverProfile is frozen (immutable)."""
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=5,
            purchase_time_days=10,
            sale_time_days=15,
            fixed_capital_ratio=0.6,
        )
        with pytest.raises(ValidationError):
            profile.working_period_days = 60  # type: ignore[misc]


# =============================================================================
# T007: AnnualSurplusValue
# =============================================================================


class TestAnnualSurplusValue:
    """Tests for AnnualSurplusValue frozen Pydantic model.

    Marx's key insight in Capital Vol. II: the annual rate of surplus value
    is the rate of surplus value multiplied by the number of turnovers.
    """

    def test_valid_construction(self) -> None:
        """AnnualSurplusValue constructs with standard values."""
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=60,
        )
        assert asv.fips_code == "26163"
        assert asv.variable_capital_advanced == pytest.approx(100.0)

    def test_rate_of_surplus_value_computed(self) -> None:
        """rate_of_surplus_value = surplus_value / variable_capital."""
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=60,
        )
        # 100 / 100 = 1.0 (100% rate of surplus value)
        assert asv.rate_of_surplus_value == pytest.approx(1.0)

    def test_turnovers_per_year_computed(self) -> None:
        """turnovers_per_year = 365 / turnover_time_days."""
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=60,
        )
        # 365 / 60 = 6.0833...
        assert asv.turnovers_per_year == pytest.approx(365.0 / 60.0)

    def test_annual_surplus_value_computed(self) -> None:
        """annual_surplus_value = surplus_value_per_cycle * turnovers_per_year."""
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=60,
        )
        # 100 * 6.0833... = 608.33...
        expected = 100.0 * (365.0 / 60.0)
        assert asv.annual_surplus_value == pytest.approx(expected)

    def test_annual_rate_of_surplus_value_computed(self) -> None:
        """annual_rate = (s/v) * turnovers_per_year."""
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=60,
        )
        # (100/100) * (365/60) = 1.0 * 6.0833... = 6.0833... (608.3%)
        expected = 1.0 * (365.0 / 60.0)
        assert asv.annual_rate_of_surplus_value == pytest.approx(expected)

    def test_marx_example_60_day_turnover(self) -> None:
        """Marx's example: s/v=100%, 60-day turnover -> ~608% annual rate.

        Capital Vol. II, Ch. 16: A faster-turning capital generates more
        surplus value annually even with the same per-cycle rate.
        """
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=60,
        )
        # 365 / 60 = 6.0833... turnovers
        assert asv.turnovers_per_year == pytest.approx(6.0833, rel=1e-3)
        # Annual rate = 100% * 6.0833 = 608.3%
        assert asv.annual_rate_of_surplus_value == pytest.approx(6.0833, rel=1e-3)

    def test_marx_example_182_day_turnover(self) -> None:
        """Marx's example: s/v=100%, 182-day turnover -> ~200% annual rate.

        A slower turnover (semi-annual) yields dramatically less annual
        surplus value despite the same per-cycle extraction.
        """
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=182,
        )
        # 365 / 182 = 2.0054... turnovers
        assert asv.turnovers_per_year == pytest.approx(2.005, rel=1e-3)
        # Annual rate = 100% * 2.005 = 200.5%
        assert asv.annual_rate_of_surplus_value == pytest.approx(2.005, rel=1e-3)

    def test_variable_capital_must_be_positive(self) -> None:
        """variable_capital_advanced must be > 0 (division guard)."""
        with pytest.raises(ValidationError):
            AnnualSurplusValue(
                fips_code="26163",
                year=2022,
                variable_capital_advanced=Currency(0.0),
                surplus_value_per_cycle=Currency(100.0),
                turnover_time_days=60,
            )

    def test_turnover_time_must_be_positive(self) -> None:
        """turnover_time_days must be > 0 (division guard)."""
        with pytest.raises(ValidationError):
            AnnualSurplusValue(
                fips_code="26163",
                year=2022,
                variable_capital_advanced=Currency(100.0),
                surplus_value_per_cycle=Currency(100.0),
                turnover_time_days=0,
            )

    def test_frozen_immutability(self) -> None:
        """AnnualSurplusValue is frozen (immutable)."""
        asv = AnnualSurplusValue(
            fips_code="26163",
            year=2022,
            variable_capital_advanced=Currency(100.0),
            surplus_value_per_cycle=Currency(100.0),
            turnover_time_days=60,
        )
        with pytest.raises(ValidationError):
            asv.turnover_time_days = 90  # type: ignore[misc]


# =============================================================================
# T008: FixedCapitalItem
# =============================================================================


class TestFixedCapitalItem:
    """Tests for FixedCapitalItem frozen Pydantic model.

    Models individual fixed capital assets with straight-line depreciation.
    """

    def test_valid_construction(self) -> None:
        """FixedCapitalItem constructs with standard factory values."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=0.0,
        )
        assert item.item_id == "factory_001"
        assert item.category == "machinery"
        assert item.initial_value == pytest.approx(1_000_000.0)

    def test_annual_depreciation_computed(self) -> None:
        """annual_depreciation = initial_value / service_life_years."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=0.0,
        )
        # 1,000,000 / 10 = 100,000
        assert item.annual_depreciation == pytest.approx(100_000.0)

    def test_remaining_value_new_asset(self) -> None:
        """New asset (age=0) has full remaining value."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=0.0,
        )
        assert item.remaining_value == pytest.approx(1_000_000.0)

    def test_remaining_value_mid_life(self) -> None:
        """Asset at age 5 of 10-year life has $500K remaining."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=5.0,
        )
        # 1,000,000 - (100,000 * 5) = 500,000
        assert item.remaining_value == pytest.approx(500_000.0)

    def test_remaining_value_fully_depreciated(self) -> None:
        """Asset at end of service life has $0 remaining."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=10.0,
        )
        assert item.remaining_value == pytest.approx(0.0)

    def test_remaining_value_over_life_clamped_to_zero(self) -> None:
        """Asset past service life has remaining value clamped to 0 (not negative)."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=15.0,
        )
        assert item.remaining_value == pytest.approx(0.0)

    def test_depreciation_fund_required(self) -> None:
        """depreciation_fund_required = initial_value - remaining_value."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=5.0,
        )
        # 1,000,000 - 500,000 = 500,000
        assert item.depreciation_fund_required == pytest.approx(500_000.0)

    def test_initial_value_must_be_positive(self) -> None:
        """initial_value must be > 0."""
        with pytest.raises(ValidationError):
            FixedCapitalItem(
                item_id="factory_001",
                category="machinery",
                initial_value=Currency(0.0),
                service_life_years=10.0,
                current_age_years=0.0,
            )

    def test_service_life_must_be_positive(self) -> None:
        """service_life_years must be > 0 (division guard)."""
        with pytest.raises(ValidationError):
            FixedCapitalItem(
                item_id="factory_001",
                category="machinery",
                initial_value=Currency(1_000_000.0),
                service_life_years=0.0,
                current_age_years=0.0,
            )

    def test_current_age_non_negative(self) -> None:
        """current_age_years must be >= 0."""
        with pytest.raises(ValidationError):
            FixedCapitalItem(
                item_id="factory_001",
                category="machinery",
                initial_value=Currency(1_000_000.0),
                service_life_years=10.0,
                current_age_years=-1.0,
            )

    def test_frozen_immutability(self) -> None:
        """FixedCapitalItem is frozen (immutable)."""
        item = FixedCapitalItem(
            item_id="factory_001",
            category="machinery",
            initial_value=Currency(1_000_000.0),
            service_life_years=10.0,
            current_age_years=0.0,
        )
        with pytest.raises(ValidationError):
            item.current_age_years = 5.0  # type: ignore[misc]


# =============================================================================
# T009: DepreciationFundState
# =============================================================================


class TestDepreciationFundState:
    """Tests for DepreciationFundState frozen Pydantic model.

    Models the replacement cycle position based on replacement/depreciation ratio.
    """

    def test_valid_construction(self) -> None:
        """DepreciationFundState constructs with standard values."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(1_500_000.0),
        )
        assert state.fips_code == "26163"
        assert state.total_fixed_capital == pytest.approx(10_000_000.0)

    def test_fund_adequacy_computed(self) -> None:
        """fund_adequacy = accumulated_depreciation / annual_depreciation_flow."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(1_500_000.0),
        )
        assert state.fund_adequacy == pytest.approx(3.0)

    def test_replacement_cycle_investment_boom(self) -> None:
        """Replacement/depreciation ratio > 1.5 -> INVESTMENT_BOOM."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(2_000_000.0),  # 2.0 > 1.5
        )
        assert state.replacement_cycle_position == ReplacementCyclePosition.INVESTMENT_BOOM

    def test_replacement_cycle_expansion(self) -> None:
        """Replacement/depreciation ratio > 1.0 (but <= 1.5) -> EXPANSION."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(1_200_000.0),  # 1.2 > 1.0
        )
        assert state.replacement_cycle_position == ReplacementCyclePosition.EXPANSION

    def test_replacement_cycle_maintenance(self) -> None:
        """Replacement/depreciation ratio > 0.7 (but <= 1.0) -> MAINTENANCE."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(800_000.0),  # 0.8 > 0.7
        )
        assert state.replacement_cycle_position == ReplacementCyclePosition.MAINTENANCE

    def test_replacement_cycle_disinvestment(self) -> None:
        """Replacement/depreciation ratio <= 0.7 -> DISINVESTMENT."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(500_000.0),  # 0.5 <= 0.7
        )
        assert state.replacement_cycle_position == ReplacementCyclePosition.DISINVESTMENT

    def test_replacement_cycle_at_boundary_0_7(self) -> None:
        """Replacement/depreciation ratio exactly 0.7 -> DISINVESTMENT."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(700_000.0),  # exactly 0.7
        )
        assert state.replacement_cycle_position == ReplacementCyclePosition.DISINVESTMENT

    def test_annual_depreciation_flow_must_be_positive(self) -> None:
        """annual_depreciation_flow must be > 0 (division guard)."""
        with pytest.raises(ValidationError):
            DepreciationFundState(
                fips_code="26163",
                year=2022,
                total_fixed_capital=Currency(10_000_000.0),
                accumulated_depreciation=Currency(0.0),
                annual_depreciation_flow=Currency(0.0),
                replacement_expenditure=Currency(0.0),
            )

    def test_frozen_immutability(self) -> None:
        """DepreciationFundState is frozen (immutable)."""
        state = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(1_500_000.0),
        )
        with pytest.raises(ValidationError):
            state.replacement_expenditure = Currency(0.0)  # type: ignore[misc]


# =============================================================================
# T010: MoralDepreciation
# =============================================================================


class TestMoralDepreciation:
    """Tests for MoralDepreciation frozen Pydantic model.

    Marx distinguished physical depreciation (wear and tear) from moral
    depreciation (obsolescence due to technical change).
    """

    def test_valid_construction(self) -> None:
        """MoralDepreciation constructs with standard values."""
        md = MoralDepreciation(
            naics_code="334",
            physical_remaining_life=10.0,
            economic_remaining_life=5.0,
        )
        assert md.naics_code == "334"
        assert md.physical_remaining_life == pytest.approx(10.0)
        assert md.economic_remaining_life == pytest.approx(5.0)

    def test_obsolescence_factor_computed(self) -> None:
        """obsolescence_factor = economic_remaining / physical_remaining."""
        md = MoralDepreciation(
            naics_code="334",
            physical_remaining_life=10.0,
            economic_remaining_life=5.0,
        )
        # 5 / 10 = 0.5 (50% of physical life is economically useful)
        assert md.obsolescence_factor == pytest.approx(0.5)

    def test_obsolescence_factor_equal_lives(self) -> None:
        """When economic == physical, obsolescence_factor = 1.0 (no obsolescence)."""
        md = MoralDepreciation(
            naics_code="31",
            physical_remaining_life=10.0,
            economic_remaining_life=10.0,
        )
        assert md.obsolescence_factor == pytest.approx(1.0)

    def test_obsolescence_factor_zero_physical_life(self) -> None:
        """When physical_remaining_life=0, obsolescence_factor defaults to 1.0."""
        md = MoralDepreciation(
            naics_code="31",
            physical_remaining_life=0.0,
            economic_remaining_life=0.0,
        )
        assert md.obsolescence_factor == pytest.approx(1.0)

    def test_physical_life_non_negative(self) -> None:
        """physical_remaining_life must be >= 0."""
        with pytest.raises(ValidationError):
            MoralDepreciation(
                naics_code="334",
                physical_remaining_life=-1.0,
                economic_remaining_life=5.0,
            )

    def test_economic_life_non_negative(self) -> None:
        """economic_remaining_life must be >= 0."""
        with pytest.raises(ValidationError):
            MoralDepreciation(
                naics_code="334",
                physical_remaining_life=10.0,
                economic_remaining_life=-1.0,
            )

    def test_frozen_immutability(self) -> None:
        """MoralDepreciation is frozen (immutable)."""
        md = MoralDepreciation(
            naics_code="334",
            physical_remaining_life=10.0,
            economic_remaining_life=5.0,
        )
        with pytest.raises(ValidationError):
            md.economic_remaining_life = 3.0  # type: ignore[misc]


# =============================================================================
# T011: InventoryState
# =============================================================================


class TestInventoryState:
    """Tests for InventoryState frozen Pydantic model.

    Models inventory levels and diagnoses overproduction vs supply crisis.
    """

    def test_valid_construction(self) -> None:
        """InventoryState constructs with standard values."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=45.0,
        )
        assert state.fips_code == "26163"
        assert state.raw_materials == pytest.approx(500_000.0)

    def test_total_inventory_computed(self) -> None:
        """total_inventory = raw_materials + work_in_progress + finished_goods."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=45.0,
        )
        assert state.total_inventory == pytest.approx(1_000_000.0)

    def test_inventory_problem_normal(self) -> None:
        """NORMAL when days_inventory_finished <= 60 and days_inventory_raw >= 7."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=45.0,
        )
        assert state.inventory_problem == InventoryDiagnosis.NORMAL

    def test_inventory_problem_overproduction(self) -> None:
        """OVERPRODUCTION when days_inventory_finished > 60."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=61.0,
        )
        assert state.inventory_problem == InventoryDiagnosis.OVERPRODUCTION

    def test_inventory_problem_supply_crisis(self) -> None:
        """SUPPLY_CRISIS when days_inventory_raw < 7."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(50_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=5.0,
            days_inventory_finished=45.0,
        )
        assert state.inventory_problem == InventoryDiagnosis.SUPPLY_CRISIS

    def test_inventory_problem_at_threshold_60_days(self) -> None:
        """Exactly 60 days finished inventory is NORMAL (not overproduction)."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=60.0,
        )
        assert state.inventory_problem == InventoryDiagnosis.NORMAL

    def test_inventory_problem_at_threshold_7_days(self) -> None:
        """Exactly 7 days raw inventory is NORMAL (not supply crisis)."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(100_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=7.0,
            days_inventory_finished=45.0,
        )
        assert state.inventory_problem == InventoryDiagnosis.NORMAL

    def test_frozen_immutability(self) -> None:
        """InventoryState is frozen (immutable)."""
        state = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=45.0,
        )
        with pytest.raises(ValidationError):
            state.raw_materials = Currency(0.0)  # type: ignore[misc]


# =============================================================================
# T012: ReproductionBalance
# =============================================================================


class TestReproductionBalance:
    """Tests for ReproductionBalance frozen Pydantic model."""

    def test_valid_construction(self) -> None:
        """ReproductionBalance constructs with standard values."""
        balance = ReproductionBalance(
            condition_met=True,
            gap=0.0,
            interpretation="Simple reproduction conditions satisfied.",
        )
        assert balance.condition_met is True
        assert balance.gap == pytest.approx(0.0)
        assert "Simple" in balance.interpretation

    def test_imbalanced_state(self) -> None:
        """ReproductionBalance with gap > 0 indicates imbalance."""
        balance = ReproductionBalance(
            condition_met=False,
            gap=150.0,
            interpretation="Department I overproduces relative to Department II demand.",
        )
        assert balance.condition_met is False
        assert balance.gap == pytest.approx(150.0)

    def test_frozen_immutability(self) -> None:
        """ReproductionBalance is frozen (immutable)."""
        balance = ReproductionBalance(
            condition_met=True,
            gap=0.0,
            interpretation="Balanced.",
        )
        with pytest.raises(ValidationError):
            balance.condition_met = False  # type: ignore[misc]


# =============================================================================
# T012: ReproductionAnalysis
# =============================================================================


class TestReproductionAnalysis:
    """Tests for ReproductionAnalysis frozen Pydantic model."""

    def test_valid_construction(self) -> None:
        """ReproductionAnalysis constructs with standard values."""
        analysis = ReproductionAnalysis(
            labor_power_demand=1000.0,
            reproduction_capacity=950.0,
            gap=50.0,
            sustainability=False,
        )
        assert analysis.labor_power_demand == pytest.approx(1000.0)
        assert analysis.reproduction_capacity == pytest.approx(950.0)
        assert analysis.gap == pytest.approx(50.0)
        assert analysis.sustainability is False

    def test_sustainable_state(self) -> None:
        """ReproductionAnalysis with sustainability=True."""
        analysis = ReproductionAnalysis(
            labor_power_demand=1000.0,
            reproduction_capacity=1100.0,
            gap=-100.0,
            sustainability=True,
        )
        assert analysis.sustainability is True
        assert analysis.gap == pytest.approx(-100.0)

    def test_frozen_immutability(self) -> None:
        """ReproductionAnalysis is frozen (immutable)."""
        analysis = ReproductionAnalysis(
            labor_power_demand=1000.0,
            reproduction_capacity=950.0,
            gap=50.0,
            sustainability=False,
        )
        with pytest.raises(ValidationError):
            analysis.sustainability = True  # type: ignore[misc]


# =============================================================================
# T013: RealizationCrisis
# =============================================================================


class TestRealizationCrisis:
    """Tests for RealizationCrisis frozen Pydantic model.

    The realization problem: surplus value exists in commodity form but
    cannot be converted to money form (unsold goods).
    """

    def test_valid_construction(self) -> None:
        """RealizationCrisis constructs with standard values."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(950_000.0),
        )
        assert crisis.fips_code == "26163"
        assert crisis.commodity_value_produced == pytest.approx(1_000_000.0)

    def test_realization_gap_computed(self) -> None:
        """realization_gap = produced - realized."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(950_000.0),
        )
        assert crisis.realization_gap == pytest.approx(50_000.0)

    def test_realization_rate_computed(self) -> None:
        """realization_rate = realized / produced."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(950_000.0),
        )
        assert crisis.realization_rate == pytest.approx(0.95)

    def test_severity_normal(self) -> None:
        """Realization rate > 0.95 -> NORMAL."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(980_000.0),  # 98%
        )
        assert crisis.crisis_severity == CrisisSeverity.NORMAL

    def test_severity_mild_slowdown(self) -> None:
        """Realization rate > 0.85 but <= 0.95 -> MILD_SLOWDOWN."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(900_000.0),  # 90%
        )
        assert crisis.crisis_severity == CrisisSeverity.MILD_SLOWDOWN

    def test_severity_recession(self) -> None:
        """Realization rate > 0.70 but <= 0.85 -> RECESSION."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(750_000.0),  # 75%
        )
        assert crisis.crisis_severity == CrisisSeverity.RECESSION

    def test_severity_crisis(self) -> None:
        """Realization rate <= 0.70 -> CRISIS."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(600_000.0),  # 60%
        )
        assert crisis.crisis_severity == CrisisSeverity.CRISIS

    def test_severity_at_boundary_0_95(self) -> None:
        """Realization rate exactly 0.95 -> MILD_SLOWDOWN (not NORMAL)."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(950_000.0),  # exactly 95%
        )
        assert crisis.crisis_severity == CrisisSeverity.MILD_SLOWDOWN

    def test_severity_at_boundary_0_85(self) -> None:
        """Realization rate exactly 0.85 -> RECESSION (not MILD_SLOWDOWN)."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(850_000.0),  # exactly 85%
        )
        assert crisis.crisis_severity == CrisisSeverity.RECESSION

    def test_severity_at_boundary_0_70(self) -> None:
        """Realization rate exactly 0.70 -> CRISIS (not RECESSION)."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(700_000.0),  # exactly 70%
        )
        assert crisis.crisis_severity == CrisisSeverity.CRISIS

    def test_commodity_value_produced_must_be_positive(self) -> None:
        """commodity_value_produced must be > 0 (division guard)."""
        with pytest.raises(ValidationError):
            RealizationCrisis(
                fips_code="26163",
                year=2022,
                commodity_value_produced=Currency(0.0),
                commodity_value_realized=Currency(0.0),
            )

    def test_frozen_immutability(self) -> None:
        """RealizationCrisis is frozen (immutable)."""
        crisis = RealizationCrisis(
            fips_code="26163",
            year=2022,
            commodity_value_produced=Currency(1_000_000.0),
            commodity_value_realized=Currency(950_000.0),
        )
        with pytest.raises(ValidationError):
            crisis.commodity_value_realized = Currency(0.0)  # type: ignore[misc]


# =============================================================================
# T014: DisproportionalityCrisis
# =============================================================================


class TestDisproportionalityCrisis:
    """Tests for DisproportionalityCrisis frozen Pydantic model.

    Models the imbalance between Department I (means of production) and
    Department II (means of consumption) output.
    """

    def test_valid_construction(self) -> None:
        """DisproportionalityCrisis constructs with standard values."""
        crisis = DisproportionalityCrisis(
            year=2022,
            dept_i_output=Currency(600_000.0),
            dept_ii_output=Currency(400_000.0),
            dept_i_share_required=0.55,
        )
        assert crisis.year == 2022
        assert crisis.dept_i_output == pytest.approx(600_000.0)

    def test_actual_i_share_computed(self) -> None:
        """actual_i_share = dept_i_output / (dept_i_output + dept_ii_output)."""
        crisis = DisproportionalityCrisis(
            year=2022,
            dept_i_output=Currency(600_000.0),
            dept_ii_output=Currency(400_000.0),
            dept_i_share_required=0.55,
        )
        # 600,000 / 1,000,000 = 0.6
        assert crisis.actual_i_share == pytest.approx(0.6)

    def test_imbalance_computed(self) -> None:
        """imbalance = |actual_i_share - dept_i_share_required|."""
        crisis = DisproportionalityCrisis(
            year=2022,
            dept_i_output=Currency(600_000.0),
            dept_ii_output=Currency(400_000.0),
            dept_i_share_required=0.55,
        )
        # |0.6 - 0.55| = 0.05
        assert crisis.imbalance == pytest.approx(0.05)

    def test_imbalance_direction_overproduction_means(self) -> None:
        """actual > required -> OVERPRODUCTION_MEANS_PRODUCTION."""
        crisis = DisproportionalityCrisis(
            year=2022,
            dept_i_output=Currency(700_000.0),
            dept_ii_output=Currency(300_000.0),
            dept_i_share_required=0.55,
        )
        # actual = 0.7 > 0.55 required
        assert crisis.imbalance_direction == "OVERPRODUCTION_MEANS_PRODUCTION"

    def test_imbalance_direction_overproduction_consumption(self) -> None:
        """actual < required -> OVERPRODUCTION_CONSUMPTION_GOODS."""
        crisis = DisproportionalityCrisis(
            year=2022,
            dept_i_output=Currency(400_000.0),
            dept_ii_output=Currency(600_000.0),
            dept_i_share_required=0.55,
        )
        # actual = 0.4 < 0.55 required
        assert crisis.imbalance_direction == "OVERPRODUCTION_CONSUMPTION_GOODS"

    def test_balanced_state(self) -> None:
        """When actual == required, imbalance is 0."""
        crisis = DisproportionalityCrisis(
            year=2022,
            dept_i_output=Currency(550_000.0),
            dept_ii_output=Currency(450_000.0),
            dept_i_share_required=0.55,
        )
        # actual = 550/1000 = 0.55 == required
        assert crisis.imbalance == pytest.approx(0.0)

    def test_frozen_immutability(self) -> None:
        """DisproportionalityCrisis is frozen (immutable)."""
        crisis = DisproportionalityCrisis(
            year=2022,
            dept_i_output=Currency(600_000.0),
            dept_ii_output=Currency(400_000.0),
            dept_i_share_required=0.55,
        )
        with pytest.raises(ValidationError):
            crisis.dept_i_output = Currency(0.0)  # type: ignore[misc]


# =============================================================================
# T015: PureCirculationCosts
# =============================================================================


class TestPureCirculationCosts:
    """Tests for PureCirculationCosts frozen Pydantic model.

    Marx distinguishes pure circulation costs (which add no value) from
    transport costs (which do add value). Pure costs are faux frais.
    """

    def test_valid_construction(self) -> None:
        """PureCirculationCosts constructs with standard values."""
        costs = PureCirculationCosts(
            fips_code="26163",
            year=2022,
            sales_labor=Currency(5_000_000.0),
            accounting_labor=Currency(3_000_000.0),
            marketing_labor=Currency(4_000_000.0),
            sales_facilities=Currency(6_000_000.0),
            advertising_materials=Currency(2_000_000.0),
            transaction_costs=Currency(5_000_000.0),
        )
        assert costs.fips_code == "26163"
        assert costs.sales_labor == pytest.approx(5_000_000.0)

    def test_total_pure_circulation_computed(self) -> None:
        """total_pure_circulation = sum of all 6 cost categories."""
        costs = PureCirculationCosts(
            fips_code="26163",
            year=2022,
            sales_labor=Currency(5_000_000.0),
            accounting_labor=Currency(3_000_000.0),
            marketing_labor=Currency(4_000_000.0),
            sales_facilities=Currency(6_000_000.0),
            advertising_materials=Currency(2_000_000.0),
            transaction_costs=Currency(5_000_000.0),
        )
        # 5 + 3 + 4 + 6 + 2 + 5 = 25 million
        assert costs.total_pure_circulation == pytest.approx(25_000_000.0)

    def test_circulation_burden_method(self) -> None:
        """circulation_burden(revenue) returns total_pure_circulation / revenue."""
        costs = PureCirculationCosts(
            fips_code="26163",
            year=2022,
            sales_labor=Currency(5_000_000.0),
            accounting_labor=Currency(3_000_000.0),
            marketing_labor=Currency(4_000_000.0),
            sales_facilities=Currency(6_000_000.0),
            advertising_materials=Currency(2_000_000.0),
            transaction_costs=Currency(5_000_000.0),
        )
        # 25,000,000 / 250,000,000 = 0.1 (10% burden)
        burden = costs.circulation_burden(Currency(250_000_000.0))
        assert burden == pytest.approx(0.1)

    def test_all_zero_costs(self) -> None:
        """All zero costs produce zero total."""
        costs = PureCirculationCosts(
            fips_code="26163",
            year=2022,
            sales_labor=Currency(0.0),
            accounting_labor=Currency(0.0),
            marketing_labor=Currency(0.0),
            sales_facilities=Currency(0.0),
            advertising_materials=Currency(0.0),
            transaction_costs=Currency(0.0),
        )
        assert costs.total_pure_circulation == pytest.approx(0.0)

    def test_frozen_immutability(self) -> None:
        """PureCirculationCosts is frozen (immutable)."""
        costs = PureCirculationCosts(
            fips_code="26163",
            year=2022,
            sales_labor=Currency(5_000_000.0),
            accounting_labor=Currency(3_000_000.0),
            marketing_labor=Currency(4_000_000.0),
            sales_facilities=Currency(6_000_000.0),
            advertising_materials=Currency(2_000_000.0),
            transaction_costs=Currency(5_000_000.0),
        )
        with pytest.raises(ValidationError):
            costs.sales_labor = Currency(0.0)  # type: ignore[misc]


# =============================================================================
# T015: TransportationValue
# =============================================================================


class TestTransportationValue:
    """Tests for TransportationValue frozen Pydantic model.

    Unlike pure circulation costs, transport adds real value to commodities.
    Marx: 'The use-value of things is only realized in their consumption,
    and their consumption may make a change of location necessary.'
    """

    def test_valid_construction(self) -> None:
        """TransportationValue constructs with standard values."""
        tv = TransportationValue(
            origin_value=Currency(1000.0),
            transport_c=Currency(50.0),
            transport_v=Currency(30.0),
            transport_s=Currency(20.0),
        )
        assert tv.origin_value == pytest.approx(1000.0)

    def test_value_added_computed(self) -> None:
        """value_added = transport_c + transport_v + transport_s."""
        tv = TransportationValue(
            origin_value=Currency(1000.0),
            transport_c=Currency(50.0),
            transport_v=Currency(30.0),
            transport_s=Currency(20.0),
        )
        assert tv.value_added == pytest.approx(100.0)

    def test_destination_value_computed(self) -> None:
        """destination_value = origin_value + value_added."""
        tv = TransportationValue(
            origin_value=Currency(1000.0),
            transport_c=Currency(50.0),
            transport_v=Currency(30.0),
            transport_s=Currency(20.0),
        )
        assert tv.destination_value == pytest.approx(1100.0)

    def test_transport_value_ratio_computed(self) -> None:
        """transport_value_ratio = value_added / destination_value."""
        tv = TransportationValue(
            origin_value=Currency(1000.0),
            transport_c=Currency(50.0),
            transport_v=Currency(30.0),
            transport_s=Currency(20.0),
        )
        # 100 / 1100 = 0.0909...
        assert tv.transport_value_ratio == pytest.approx(100.0 / 1100.0)

    def test_zero_transport_costs(self) -> None:
        """Zero transport costs yield zero value_added and ratio."""
        tv = TransportationValue(
            origin_value=Currency(1000.0),
            transport_c=Currency(0.0),
            transport_v=Currency(0.0),
            transport_s=Currency(0.0),
        )
        assert tv.value_added == pytest.approx(0.0)
        assert tv.destination_value == pytest.approx(1000.0)
        assert tv.transport_value_ratio == pytest.approx(0.0)

    def test_frozen_immutability(self) -> None:
        """TransportationValue is frozen (immutable)."""
        tv = TransportationValue(
            origin_value=Currency(1000.0),
            transport_c=Currency(50.0),
            transport_v=Currency(30.0),
            transport_s=Currency(20.0),
        )
        with pytest.raises(ValidationError):
            tv.origin_value = Currency(0.0)  # type: ignore[misc]


# =============================================================================
# T016: CirculationCrisisAssessment
# =============================================================================


class TestCirculationCrisisAssessment:
    """Tests for CirculationCrisisAssessment frozen Pydantic model."""

    def test_valid_construction(self) -> None:
        """CirculationCrisisAssessment constructs with standard values."""
        assessment = CirculationCrisisAssessment(
            fips_code="26163",
            year=2022,
            realization_crisis=True,
            turnover_crisis=False,
            reproduction_crisis=False,
            vulnerabilities=["Commodity overhang exceeds 40%"],
        )
        assert assessment.fips_code == "26163"
        assert assessment.realization_crisis is True
        assert assessment.turnover_crisis is False

    def test_no_vulnerabilities(self) -> None:
        """Assessment with no vulnerabilities."""
        assessment = CirculationCrisisAssessment(
            fips_code="26163",
            year=2022,
            realization_crisis=False,
            turnover_crisis=False,
            reproduction_crisis=False,
            vulnerabilities=[],
        )
        assert len(assessment.vulnerabilities) == 0

    def test_multiple_vulnerabilities(self) -> None:
        """Assessment with multiple vulnerability flags."""
        vulns = [
            "Realization rate below 85%",
            "Turnover decelerating",
            "Dept I/II imbalance > 10%",
        ]
        assessment = CirculationCrisisAssessment(
            fips_code="26163",
            year=2022,
            realization_crisis=True,
            turnover_crisis=True,
            reproduction_crisis=True,
            vulnerabilities=vulns,
        )
        assert len(assessment.vulnerabilities) == 3
        assert "Realization rate below 85%" in assessment.vulnerabilities

    def test_frozen_immutability(self) -> None:
        """CirculationCrisisAssessment is frozen (immutable)."""
        assessment = CirculationCrisisAssessment(
            fips_code="26163",
            year=2022,
            realization_crisis=False,
            turnover_crisis=False,
            reproduction_crisis=False,
            vulnerabilities=[],
        )
        with pytest.raises(ValidationError):
            assessment.realization_crisis = True  # type: ignore[misc]


# =============================================================================
# T016: CirculationCrisisState
# =============================================================================


class TestCirculationCrisisState:
    """Tests for CirculationCrisisState frozen Pydantic model.

    Composite state object that aggregates circuit, inventory, and depreciation
    states with an optional crisis assessment.
    """

    def test_valid_construction(self) -> None:
        """CirculationCrisisState constructs with nested models."""
        circuit = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(200.0),
            commodity_capital=Currency(50.0),
            fixed_capital=Currency(150.0),
            circulating_capital=Currency(100.0),
        )
        inventory = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=45.0,
        )
        depreciation = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(1_000_000.0),
        )
        state = CirculationCrisisState(
            circuit_state=circuit,
            inventory_state=inventory,
            depreciation_fund=depreciation,
            latest_assessment=None,
        )
        assert state.circuit_state.fips_code == "26163"
        assert state.latest_assessment is None

    def test_with_assessment(self) -> None:
        """CirculationCrisisState accepts a non-None assessment."""
        circuit = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(200.0),
            commodity_capital=Currency(50.0),
            fixed_capital=Currency(150.0),
            circulating_capital=Currency(100.0),
        )
        inventory = InventoryState(
            fips_code="26163",
            year=2022,
            raw_materials=Currency(500_000.0),
            work_in_progress=Currency(300_000.0),
            finished_goods=Currency(200_000.0),
            days_inventory_raw=30.0,
            days_inventory_finished=45.0,
        )
        depreciation = DepreciationFundState(
            fips_code="26163",
            year=2022,
            total_fixed_capital=Currency(10_000_000.0),
            accumulated_depreciation=Currency(3_000_000.0),
            annual_depreciation_flow=Currency(1_000_000.0),
            replacement_expenditure=Currency(1_000_000.0),
        )
        assessment = CirculationCrisisAssessment(
            fips_code="26163",
            year=2022,
            realization_crisis=True,
            turnover_crisis=False,
            reproduction_crisis=False,
            vulnerabilities=["Commodity overhang exceeds 40%"],
        )
        state = CirculationCrisisState(
            circuit_state=circuit,
            inventory_state=inventory,
            depreciation_fund=depreciation,
            latest_assessment=assessment,
        )
        assert state.latest_assessment is not None
        assert state.latest_assessment.realization_crisis is True

    def test_initial_factory(self) -> None:
        """CirculationCrisisState.initial() creates zeroed/neutral defaults."""
        state = CirculationCrisisState.initial(fips="26163", year=2022)
        assert state.circuit_state.fips_code == "26163"
        assert state.circuit_state.year == 2022
        assert state.circuit_state.money_capital == pytest.approx(0.0)
        assert state.circuit_state.productive_capital == pytest.approx(0.0)
        assert state.circuit_state.commodity_capital == pytest.approx(0.0)
        assert state.inventory_state.fips_code == "26163"
        assert state.inventory_state.year == 2022
        assert state.depreciation_fund.fips_code == "26163"
        assert state.depreciation_fund.year == 2022
        assert state.latest_assessment is None

    def test_frozen_immutability(self) -> None:
        """CirculationCrisisState is frozen (immutable)."""
        state = CirculationCrisisState.initial(fips="26163", year=2022)
        with pytest.raises(ValidationError):
            state.latest_assessment = None  # type: ignore[misc]
