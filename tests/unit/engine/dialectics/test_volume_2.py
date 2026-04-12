"""TDD RED phase: Tests for Volume II Dialectics using the economics engine.

These tests validate the behavior of dialectics handling Circulation,
Turnover, and Reproduction by verifying they correctly wrap the pure
functions from `babylon.economics.circulation`.
"""

from __future__ import annotations

from babylon.economics.circulation.types import (
    AnnualSurplusValue,
    CircuitState,
    TurnoverProfile,
)
from babylon.economics.tensor import DepartmentRow
from babylon.engine.dialectics.base import TickInputs, WorldView
from babylon.engine.dialectics.volume_2 import (
    CirculationDialectic,
    DisproportionalityCrisisDialectic,
    EmptyPole,
    RealizationCrisisDialectic,
    ReproductionDialectic,
    TurnoverDialectic,
)
from babylon.models.types import Currency, LaborHours

# ===========================================================================
# CirculationDialectic (Circuit of Capital) Tests
# ===========================================================================


class TestCirculationDialectic:
    def test_construction_and_poles(self) -> None:
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(0.0),
            commodity_capital=Currency(0.0),
            fixed_capital=Currency(0.0),
            circulating_capital=Currency(0.0),
        )
        cd = CirculationDialectic(
            pole_a=state,
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert cd.type_tag == "CirculationDialectic"
        assert cd.pole_a.money_capital == 100.0

    def test_step_advances_circuit(self) -> None:
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(100.0),
            productive_capital=Currency(0.0),
            commodity_capital=Currency(0.0),
            fixed_capital=Currency(0.0),
            circulating_capital=Currency(0.0),
        )
        cd = CirculationDialectic(
            pole_a=state, pole_b=EmptyPole(), weight=0.0, tick_created=0, tick_updated=0
        )
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=10,
            non_working_production_days=0,
            purchase_time_days=10,
            sale_time_days=10,
            fixed_capital_ratio=0.0,
        )
        # Advance by 5 days (half of purchase time)
        inputs = TickInputs(
            upstream={
                cd.id: {"event": "advance", "elapsed_days": 5, "profile_dict": profile.model_dump()}
            }
        )
        world = WorldView(tick=1, dialectics={})

        result = cd.step(inputs, world)

        # Money capital should decrease, productive should increase
        assert result.pole_a.money_capital < 100.0
        assert result.pole_a.productive_capital > 0.0

    def test_sublation_to_realization_crisis(self) -> None:
        # High commodity overhang should trigger RealizationCrisis
        state = CircuitState(
            fips_code="26163",
            year=2022,
            money_capital=Currency(10.0),
            productive_capital=Currency(0.0),
            commodity_capital=Currency(90.0),
            fixed_capital=Currency(0.0),
            circulating_capital=Currency(0.0),
        )
        cd = CirculationDialectic(
            pole_a=state, pole_b=EmptyPole(), weight=-0.9, tick_created=0, tick_updated=0
        )
        # Weight computed internally, but we can test sublate directly
        sublated = cd.sublate()
        assert sublated is not None
        assert isinstance(sublated, RealizationCrisisDialectic)
        assert sublated.parent_id == cd.id


# ===========================================================================
# TurnoverDialectic Tests
# ===========================================================================


class TestTurnoverDialectic:
    def test_construction(self) -> None:
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=20,
            non_working_production_days=5,
            purchase_time_days=3,
            sale_time_days=7,
            fixed_capital_ratio=0.6,
        )
        td = TurnoverDialectic(
            pole_a=profile,
            pole_b=AnnualSurplusValue(
                fips_code="00000",
                year=2022,
                variable_capital_advanced=Currency(1),
                surplus_value_per_cycle=Currency(0),
                turnover_time_days=35,
            ),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert td.type_tag == "TurnoverDialectic"
        assert td.pole_a.turnover_time == 35

    def test_observe_yields_annual_surplus_value(self) -> None:
        profile = TurnoverProfile(
            naics_code="31",
            working_period_days=30,
            non_working_production_days=0,
            purchase_time_days=30,
            sale_time_days=13,
            fixed_capital_ratio=0.6,
        )
        # Turnover time = 73 days (5 turnovers/year)
        td = TurnoverDialectic(
            pole_a=profile,
            pole_b=AnnualSurplusValue(
                fips_code="00000",
                year=2022,
                variable_capital_advanced=Currency(1),
                surplus_value_per_cycle=Currency(0),
                turnover_time_days=73,
            ),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        # Assuming we passed v=1000, s=1000 via inputs
        inputs = TickInputs(upstream={td.id: {"v": 1000.0, "s": 1000.0}})
        td = td.step(inputs, WorldView(tick=1, dialectics={}))

        obs = td.observe()
        assert obs["annual_rate_of_surplus_value"] == 5.0
        assert obs["annual_surplus_value"] == 5000.0


# ===========================================================================
# ReproductionDialectic Tests
# ===========================================================================


class TestReproductionDialectic:
    def test_construction_and_poles(self) -> None:
        dept_i = DepartmentRow(c=LaborHours(4000.0), v=LaborHours(1000.0), s=LaborHours(1000.0))
        dept_ii = DepartmentRow(c=LaborHours(2000.0), v=LaborHours(500.0), s=LaborHours(500.0))

        rd = ReproductionDialectic(
            pole_a=dept_i, pole_b=dept_ii, weight=0.0, tick_created=0, tick_updated=0
        )
        assert rd.type_tag == "ReproductionDialectic"
        assert rd.pole_a.c == 4000.0

    def test_step_enforces_reproduction_balance(self) -> None:
        # Simple Reproduction: I(v+s) == 2000, IIc == 2000 -> Perfect balance, weight 0.0
        dept_i = DepartmentRow(c=LaborHours(4000.0), v=LaborHours(1000.0), s=LaborHours(1000.0))
        dept_ii = DepartmentRow(c=LaborHours(2000.0), v=LaborHours(500.0), s=LaborHours(500.0))

        rd = ReproductionDialectic(
            pole_a=dept_i, pole_b=dept_ii, weight=0.0, tick_created=0, tick_updated=0
        )
        result = rd.step(TickInputs(), WorldView(tick=1, dialectics={}))
        assert result.weight == 0.0

        # Imbalance: I forces overproduction of Dept I (v+s=2500 > IIc=2000) -> weight shifts
        dept_i_bad = DepartmentRow(c=LaborHours(4000.0), v=LaborHours(1500.0), s=LaborHours(1000.0))
        rd2 = ReproductionDialectic(
            pole_a=dept_i_bad, pole_b=dept_ii, weight=0.0, tick_created=0, tick_updated=0
        )
        result2 = rd2.step(TickInputs(), WorldView(tick=1, dialectics={}))
        assert (
            result2.weight != 0.0
        )  # Should shift negative based on our formulation (pole A overproduced)

    def test_sublation_to_crisis(self) -> None:
        # Imbalance -> DisproportionalityCrisisDialectic
        dept_i = DepartmentRow(c=LaborHours(0.0), v=LaborHours(0.0), s=LaborHours(0.0))
        dept_ii = DepartmentRow(c=LaborHours(0.0), v=LaborHours(0.0), s=LaborHours(0.0))
        rd = ReproductionDialectic(
            pole_a=dept_i, pole_b=dept_ii, weight=0.9, tick_created=0, tick_updated=0
        )
        sublated = rd.sublate()
        assert sublated is not None
        assert isinstance(sublated, DisproportionalityCrisisDialectic)
        assert sublated.parent_id == rd.id
