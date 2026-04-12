"""TDD RED phase: Tests for Volume III Dialectics using the economics engine.

These tests validate the behavior of dialectics handling the distribution
of surplus value (V3 Ch1-10), the tendency of the rate of profit to fall
(V3 Ch13-15), credit and fictitious capital (V3 Ch21-33), ground rent
(V3 Ch37-47), and imperial rent (V3 Ch14 §V + Babylon MLM-TW contribution).

They verify that each dialectic correctly wraps the pure domain functions
from ``babylon.economics.distribution``, ``babylon.economics.credit``,
``babylon.economics.counter_tendencies``, ``babylon.economics.rent``,
and ``babylon.economics.financial_crisis``.
"""

from __future__ import annotations

import pytest

from babylon.economics.counter_tendencies.types import CounterTendencyStrength
from babylon.economics.credit.types import FictitiousCapitalStock
from babylon.economics.rent.types import RentExtraction
from babylon.engine.dialectics.base import EmptyPole, TickInputs, WorldView
from babylon.engine.dialectics.volume_3 import (
    CoreEconomy,
    CreditDialectic,
    CreditPole,
    DebtSpiralCrisisDialectic,
    FinancialCrisisDialectic,
    ImperialDialectic,
    PeripheryEconomy,
    ProfitRateState,
    RentDialectic,
    RentPole,
    TransformationDialectic,
    TransformationPole,
    TRPFDialectic,
)

# ===========================================================================
# TransformationDialectic (V3 Ch9-10): Value ↔ PriceOfProduction
# ===========================================================================


class TestTransformationDialectic:
    """Tests for the surplus value distribution dialectic."""

    def test_construction_and_poles(self) -> None:
        pole_a = TransformationPole(
            total_surplus=1000.0,
            interest_payments=200.0,
            ground_rent=100.0,
            taxes=50.0,
        )
        td = TransformationDialectic(
            pole_a=pole_a,
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert td.type_tag == "TransformationDialectic"
        assert td.pole_a.total_surplus == 1000.0

    def test_observe_emits_distribution_components(self) -> None:
        pole_a = TransformationPole(
            total_surplus=1000.0,
            interest_payments=200.0,
            ground_rent=100.0,
            taxes=50.0,
        )
        td = TransformationDialectic(
            pole_a=pole_a,
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = td.observe()
        assert obs["total_surplus"] == 1000.0
        assert obs["interest_payments"] == 200.0
        assert obs["ground_rent"] == 100.0
        assert obs["taxes"] == 50.0
        assert obs["profit_of_enterprise"] == 650.0  # 1000 - 200 - 100 - 50

    def test_step_shifts_weight_on_profit_squeeze(self) -> None:
        """When claims crowd out enterprise profit, weight shifts negative."""
        pole_a = TransformationPole(
            total_surplus=100.0,
            interest_payments=40.0,
            ground_rent=30.0,
            taxes=20.0,
        )
        td = TransformationDialectic(
            pole_a=pole_a,
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        # Provide upstream input with increasing interest pressure
        inputs = TickInputs(upstream={td.id: {"interest_rate_increase": 0.5}})
        result = td.step(inputs, WorldView(tick=1, dialectics={}))
        # When interest increases, weight should shift (toward B / claims dominant)
        assert result.tick_updated == 1
        assert isinstance(result, TransformationDialectic)

    def test_invariant_accounting_identity(self) -> None:
        """s = p + i + r + t must hold."""
        pole_a = TransformationPole(
            total_surplus=1000.0,
            interest_payments=200.0,
            ground_rent=100.0,
            taxes=50.0,
        )
        td = TransformationDialectic(
            pole_a=pole_a,
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        # Should have no violations
        assert td.invariants() == []

    def test_sublation_to_debt_spiral(self) -> None:
        """Claims exceeding surplus triggers debt spiral crisis."""
        pole_a = TransformationPole(
            total_surplus=100.0,
            interest_payments=50.0,
            ground_rent=40.0,
            taxes=20.0,
        )
        # Claims = 50 + 40 + 20 = 110 > 100 surplus → claims exceed surplus
        td = TransformationDialectic(
            pole_a=pole_a,
            pole_b=EmptyPole(),
            weight=-0.9,
            tick_created=0,
            tick_updated=5,
        )
        sublated = td.sublate()
        assert sublated is not None
        assert isinstance(sublated, DebtSpiralCrisisDialectic)
        assert sublated.parent_id == td.id


# ===========================================================================
# TRPFDialectic (V3 Ch13-15): Tendency ↔ CounterTendencies
# ===========================================================================


class TestTRPFDialectic:
    """Tests for the TRPF dialectic."""

    def test_construction_and_poles(self) -> None:
        pole_a = ProfitRateState(
            profit_rate=0.15,
            profit_rate_trend=-0.02,
            organic_composition=3.5,
        )
        ct = CounterTendencyStrength(
            year=2022,
            exploitation_rate_change=0.01,
            wage_suppression=0.02,
            constant_capital_cheapening=-0.01,
            reserve_army_size=0.08,
            imperial_rent_flow=500.0,
            fictitious_profit_share=0.25,
        )
        trpf = TRPFDialectic(
            pole_a=pole_a,
            pole_b=ct,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert trpf.type_tag == "TRPFDialectic"
        assert trpf.pole_a.profit_rate == 0.15

    def test_observe_emits_net_counter_tendency(self) -> None:
        pole_a = ProfitRateState(
            profit_rate=0.15,
            profit_rate_trend=-0.02,
            organic_composition=3.5,
        )
        ct = CounterTendencyStrength(
            year=2022,
            exploitation_rate_change=0.05,
            wage_suppression=0.03,
            constant_capital_cheapening=-0.02,
            reserve_army_size=0.10,
            imperial_rent_flow=1000.0,
            fictitious_profit_share=0.30,
        )
        trpf = TRPFDialectic(
            pole_a=pole_a,
            pole_b=ct,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = trpf.observe()
        assert "net_counter_tendency" in obs
        assert "profit_rate" in obs
        assert "organic_composition" in obs
        assert obs["profit_rate"] == 0.15

    def test_step_updates_weight_from_net_ct(self) -> None:
        pole_a = ProfitRateState(
            profit_rate=0.15,
            profit_rate_trend=-0.02,
            organic_composition=3.5,
        )
        ct = CounterTendencyStrength(
            year=2022,
            exploitation_rate_change=0.01,
        )
        trpf = TRPFDialectic(
            pole_a=pole_a,
            pole_b=ct,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs(upstream={trpf.id: {"occ": 4.0, "exploitation_rate": 1.5}})
        result = trpf.step(inputs, WorldView(tick=1, dialectics={}))
        assert result.tick_updated == 1
        assert isinstance(result, TRPFDialectic)

    def test_no_sublation(self) -> None:
        """TRPF is a structural tendency, not an event — no sublation."""
        pole_a = ProfitRateState(profit_rate=0.01)
        ct = CounterTendencyStrength(year=2022)
        trpf = TRPFDialectic(pole_a=pole_a, pole_b=ct, weight=-0.9, tick_created=0, tick_updated=0)
        assert trpf.sublate() is None


# ===========================================================================
# CreditDialectic (V3 Ch21-33): RealCapital ↔ FictitiousCapital
# ===========================================================================


class TestCreditDialectic:
    """Tests for the credit/fictitious capital dialectic."""

    def test_construction_and_poles(self) -> None:
        real = CreditPole(
            total_real_capital=1_000_000.0,
            profit_rate=0.12,
            gdp=5_000_000.0,
        )
        fict = FictitiousCapitalStock(
            year=2022,
            government_debt=500_000.0,
            corporate_equity=800_000.0,
            corporate_debt=300_000.0,
            household_debt=400_000.0,
        )
        cd = CreditDialectic(
            pole_a=real,
            pole_b=fict,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert cd.type_tag == "CreditDialectic"
        assert cd.pole_a.total_real_capital == 1_000_000.0

    def test_observe_emits_financialization_index(self) -> None:
        real = CreditPole(
            total_real_capital=1_000_000.0,
            profit_rate=0.12,
            gdp=1_000_000.0,
        )
        fict = FictitiousCapitalStock(
            year=2022,
            government_debt=500_000.0,
            corporate_equity=800_000.0,
            corporate_debt=300_000.0,
            household_debt=400_000.0,
        )
        cd = CreditDialectic(
            pole_a=real,
            pole_b=fict,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = cd.observe()
        assert "financialization_index" in obs
        # total_claims = 500k + 800k + 300k + 400k = 2M, gdp = 1M → ratio = 2.0
        assert obs["financialization_index"] == pytest.approx(2.0)

    def test_step_advances_credit_state(self) -> None:
        real = CreditPole(
            total_real_capital=1_000_000.0,
            profit_rate=0.12,
            gdp=5_000_000.0,
        )
        fict = FictitiousCapitalStock(
            year=2022,
            government_debt=500_000.0,
            corporate_equity=800_000.0,
            corporate_debt=300_000.0,
            household_debt=400_000.0,
        )
        cd = CreditDialectic(pole_a=real, pole_b=fict, weight=0.0, tick_created=0, tick_updated=0)
        inputs = TickInputs(upstream={cd.id: {"credit_growth": 0.05, "default_rate": 0.01}})
        result = cd.step(inputs, WorldView(tick=1, dialectics={}))
        assert result.tick_updated == 1
        assert isinstance(result, CreditDialectic)

    def test_sublation_to_financial_crisis(self) -> None:
        """Financialization above FINANCIALIZATION_BUBBLE triggers crisis."""
        real = CreditPole(
            total_real_capital=1_000_000.0,
            profit_rate=0.05,
            gdp=500_000.0,  # Very low GDP relative to claims
        )
        fict = FictitiousCapitalStock(
            year=2022,
            government_debt=500_000.0,
            corporate_equity=800_000.0,
            corporate_debt=300_000.0,
            household_debt=400_000.0,
        )
        # total_claims = 2M, GDP = 500k → financialization = 4.0 > 3.5 threshold
        cd = CreditDialectic(pole_a=real, pole_b=fict, weight=0.8, tick_created=0, tick_updated=5)
        sublated = cd.sublate()
        assert sublated is not None
        assert isinstance(sublated, FinancialCrisisDialectic)
        assert sublated.parent_id == cd.id

    def test_no_sublation_below_threshold(self) -> None:
        real = CreditPole(
            total_real_capital=1_000_000.0,
            profit_rate=0.12,
            gdp=5_000_000.0,  # Large GDP → low ratio
        )
        fict = FictitiousCapitalStock(
            year=2022,
            government_debt=500_000.0,
            corporate_equity=800_000.0,
            corporate_debt=300_000.0,
            household_debt=400_000.0,
        )
        cd = CreditDialectic(pole_a=real, pole_b=fict, weight=0.0, tick_created=0, tick_updated=0)
        assert cd.sublate() is None


# ===========================================================================
# RentDialectic (V3 Ch37-47): AbsoluteRent ↔ DifferentialRent
# ===========================================================================


class TestRentDialectic:
    """Tests for the ground rent dialectic."""

    def test_construction_and_poles(self) -> None:
        rent = RentExtraction(
            fips_code="26163",
            year=2022,
            agricultural_rent=100.0,
            resource_rent=200.0,
            urban_rent=500.0,
        )
        rd = RentDialectic(
            pole_a=RentPole(
                agricultural_rent=rent.agricultural_rent,
                resource_rent=rent.resource_rent,
                urban_rent=rent.urban_rent,
            ),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert rd.type_tag == "RentDialectic"

    def test_observe_emits_rent_components(self) -> None:
        rd = RentDialectic(
            pole_a=RentPole(
                agricultural_rent=100.0,
                resource_rent=200.0,
                urban_rent=500.0,
            ),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = rd.observe()
        assert obs["total_rent"] == 800.0
        assert obs["agricultural_rent"] == 100.0
        assert obs["resource_rent"] == 200.0
        assert obs["urban_rent"] == 500.0

    def test_step_updates_weight(self) -> None:
        rd = RentDialectic(
            pole_a=RentPole(
                agricultural_rent=100.0,
                resource_rent=200.0,
                urban_rent=500.0,
            ),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs(upstream={rd.id: {"total_surplus": 10000.0}})
        result = rd.step(inputs, WorldView(tick=1, dialectics={}))
        assert result.tick_updated == 1
        assert isinstance(result, RentDialectic)

    def test_invariant_rent_non_negative(self) -> None:
        rd = RentDialectic(
            pole_a=RentPole(
                agricultural_rent=100.0,
                resource_rent=200.0,
                urban_rent=500.0,
            ),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert rd.invariants() == []


# ===========================================================================
# ImperialDialectic (V3 Ch14 §V + Babylon MLM-TW)
# ===========================================================================


class TestImperialDialectic:
    """Tests for the imperial rent dialectic."""

    def test_construction_and_poles(self) -> None:
        core = CoreEconomy(
            core_wages=100.0,
            value_produced=80.0,
            profit_rate=0.15,
        )
        periphery = PeripheryEconomy(
            periphery_wages=20.0,
            extraction_rate=0.6,
            consciousness=0.1,
        )
        imp = ImperialDialectic(
            pole_a=core,
            pole_b=periphery,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert imp.type_tag == "ImperialDialectic"

    def test_observe_emits_imperial_rent(self) -> None:
        core = CoreEconomy(
            core_wages=100.0,
            value_produced=80.0,
            profit_rate=0.15,
        )
        periphery = PeripheryEconomy(
            periphery_wages=20.0,
            extraction_rate=0.6,
            consciousness=0.1,
        )
        imp = ImperialDialectic(
            pole_a=core,
            pole_b=periphery,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = imp.observe()
        assert "imperial_rent_phi" in obs
        assert "labor_aristocracy_ratio" in obs
        assert obs["imperial_rent_phi"] >= 0.0

    def test_step_adjusts_weight_from_lar(self) -> None:
        core = CoreEconomy(
            core_wages=100.0,
            value_produced=80.0,
            profit_rate=0.15,
        )
        periphery = PeripheryEconomy(
            periphery_wages=20.0,
            extraction_rate=0.6,
            consciousness=0.1,
        )
        imp = ImperialDialectic(
            pole_a=core,
            pole_b=periphery,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs(upstream={imp.id: {"extraction_boost": 0.3}})
        result = imp.step(inputs, WorldView(tick=1, dialectics={}))
        assert result.tick_updated == 1
        assert isinstance(result, ImperialDialectic)

    def test_invariant_imperial_rent_non_negative(self) -> None:
        core = CoreEconomy(
            core_wages=100.0,
            value_produced=80.0,
            profit_rate=0.15,
        )
        periphery = PeripheryEconomy(
            periphery_wages=20.0,
            extraction_rate=0.6,
            consciousness=0.1,
        )
        imp = ImperialDialectic(
            pole_a=core,
            pole_b=periphery,
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert imp.invariants() == []


# ===========================================================================
# Crisis Dialectic Tests
# ===========================================================================


class TestDebtSpiralCrisisDialectic:
    def test_construction(self) -> None:
        crisis = DebtSpiralCrisisDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=5,
            tick_updated=5,
        )
        assert crisis.type_tag == "DebtSpiralCrisisDialectic"

    def test_step_passthrough(self) -> None:
        crisis = DebtSpiralCrisisDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=5,
            tick_updated=5,
        )
        result = crisis.step(TickInputs(), WorldView(tick=6, dialectics={}))
        assert result.tick_updated == 6


class TestFinancialCrisisDialectic:
    def test_construction(self) -> None:
        crisis = FinancialCrisisDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=5,
            tick_updated=5,
        )
        assert crisis.type_tag == "FinancialCrisisDialectic"

    def test_step_passthrough(self) -> None:
        crisis = FinancialCrisisDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=5,
            tick_updated=5,
        )
        result = crisis.step(TickInputs(), WorldView(tick=6, dialectics={}))
        assert result.tick_updated == 6
