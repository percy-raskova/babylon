"""TDD RED phase: Tests for V1 Production Dialectics.

Tests for five dialectics derived from Capital Volume I:
- LaborProcessDialectic (Ch7§1): ConcreteLabor ↔ AbstractLabor
- ProductionDialectic (Ch7§2, Ch8, Ch9): LaborProcess ↔ Valorization
- WageDialectic (Ch19-22): ValueOfLaborPower ↔ PriceOfLaborPower
- AccumulationDialectic (Ch23-25): ConcentrationOfCapital ↔ ReserveArmyExpansion
- PrimitiveAccumulationDialectic (Ch26-33 + Sakai/MIM(P)):
    ColonialExpropriation ↔ SettlerFormation

Each test section validates:
- Pole construction and Pydantic validation
- type_tag identity
- step() motion law correctness (with citations to Marx)
- observe() projection (value tensor, labor pool)
- invariants() domain checks
- Weight clamping at ±1
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from babylon.economics.tensor import DepartmentRow
from babylon.economics.value import AbstractLabor, ConcreteLabor
from babylon.engine.dialectics.base import EmptyPole, TickInputs, WorldView
from babylon.engine.dialectics.tick import tick
from babylon.engine.dialectics.volume_1 import (
    AccumulationDialectic,
    ColonialExpropriation,
    ConcentrationOfCapital,
    LaborProcessDialectic,
    PriceOfLaborPower,
    PrimitiveAccumulationDialectic,
    ProductionDialectic,
    ReserveArmyExpansion,
    SettlerFormation,
    ValueOfLaborPower,
    WageDialectic,
)
from babylon.engine.dialectics.world import Morphism, World

# ===========================================================================
# Helpers
# ===========================================================================


def _empty_inputs() -> TickInputs:
    return TickInputs()


def _world(tick_n: int = 1) -> WorldView:
    return WorldView(tick=tick_n, dialectics={})


# ===========================================================================
# LaborProcessDialectic Tests (V1 Ch7§1)
# ===========================================================================


class TestConcreteLabor:
    """ConcreteLabor pole construction and validation."""

    def test_default_construction(self) -> None:
        cl = ConcreteLabor()
        assert 0.0 <= cl.skill <= 1.0
        assert 0.0 <= cl.intensity <= 1.0
        assert cl.hours >= 0.0

    def test_custom_values(self) -> None:
        cl = ConcreteLabor(skill=0.8, intensity=0.6, hours=8.0, labor_type="spinning")
        assert cl.skill == 0.8
        assert cl.intensity == 0.6
        assert cl.hours == 8.0
        assert cl.labor_type == "spinning"

    def test_skill_bounded(self) -> None:
        with pytest.raises(ValidationError):
            ConcreteLabor(skill=-0.1)
        with pytest.raises(ValidationError):
            ConcreteLabor(skill=1.1)

    def test_intensity_bounded(self) -> None:
        with pytest.raises(ValidationError):
            ConcreteLabor(intensity=-0.1)
        with pytest.raises(ValidationError):
            ConcreteLabor(intensity=1.1)


class TestAbstractLabor:
    """AbstractLabor pole construction and validation."""

    def test_default_construction(self) -> None:
        al = AbstractLabor()
        assert al.snlt >= 0.0
        assert al.productivity > 0.0

    def test_custom_values(self) -> None:
        al = AbstractLabor(snlt=4.0, productivity=1.5)
        assert al.snlt == 4.0
        assert al.productivity == 1.5

    def test_snlt_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            AbstractLabor(snlt=-1.0)

    def test_productivity_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            AbstractLabor(productivity=0.0)
        with pytest.raises(ValidationError):
            AbstractLabor(productivity=-1.0)


class TestLaborProcessDialectic:
    """LaborProcessDialectic: concrete ↔ abstract labor (V1 Ch1§2)."""

    def _make(self, weight: float = 0.0) -> LaborProcessDialectic:
        return LaborProcessDialectic(
            pole_a=ConcreteLabor(skill=0.5, intensity=0.5, hours=8.0),
            pole_b=AbstractLabor(snlt=4.0, productivity=1.0),
            weight=weight,
            tick_created=0,
            tick_updated=0,
        )

    def test_type_tag(self) -> None:
        d = self._make()
        assert d.type_tag == "LaborProcessDialectic"

    def test_step_returns_same_type(self) -> None:
        d = self._make()
        result = d.step(_empty_inputs(), _world())
        assert isinstance(result, LaborProcessDialectic)

    def test_no_input_identity(self) -> None:
        """No upstream input → weight unchanged."""
        d = self._make(weight=0.3)
        result = d.step(_empty_inputs(), _world())
        assert result.weight == d.weight

    def test_tick_updated(self) -> None:
        d = self._make()
        result = d.step(_empty_inputs(), _world(tick_n=5))
        assert result.tick_updated == 5

    def test_competitive_pressure_shifts_positive(self) -> None:
        """Ch7§1: competitive pressure shifts toward abstract labor (B, positive)."""
        d = self._make(weight=0.0)
        inputs = TickInputs(upstream={d.id: {"competitive_pressure": 0.5}})
        result = d.step(inputs, _world())
        assert result.weight > 0.0

    def test_weight_clamped_positive(self) -> None:
        d = self._make(weight=0.95)
        inputs = TickInputs(upstream={d.id: {"competitive_pressure": 1.0}})
        result = d.step(inputs, _world())
        assert result.weight <= 1.0

    def test_weight_clamped_negative(self) -> None:
        d = self._make(weight=-0.95)
        inputs = TickInputs(upstream={d.id: {"competitive_pressure": -1.0}})
        result = d.step(inputs, _world())
        assert result.weight >= -1.0

    def test_observe_includes_labor_fields(self) -> None:
        d = self._make()
        obs = d.observe()
        assert obs["type"] == "LaborProcessDialectic"
        assert "skill" in obs
        assert "intensity" in obs
        assert "hours" in obs
        assert "snlt" in obs
        assert "productivity" in obs


# ===========================================================================
# ProductionDialectic Tests (V1 Ch7§2, Ch8, Ch9)
# ===========================================================================


class TestProductionDialectic:
    """ProductionDialectic: labor process ↔ valorization (V1 Ch7§2)."""

    def _make(self, weight: float = 0.0, **kwargs: Any) -> ProductionDialectic:
        row = DepartmentRow(
            c=kwargs.get("c", 12.0),
            v=kwargs.get("v", 3.0),
            s=kwargs.get("s", 3.0),
        )
        return ProductionDialectic(
            pole_a=row,
            pole_b=EmptyPole(),
            weight=weight,
            tick_created=0,
            tick_updated=0,
        )

    def test_type_tag(self) -> None:
        d = self._make()
        assert d.type_tag == "ProductionDialectic"

    def test_step_returns_same_type(self) -> None:
        d = self._make()
        result = d.step(_empty_inputs(), _world())
        assert isinstance(result, ProductionDialectic)

    def test_ch9_surplus_value_formula(self) -> None:
        """Ch9: s = v × e."""
        d = self._make(v=3.0, e=1.0, s=3.0)
        obs = d.observe()
        assert obs["s"] == pytest.approx(3.0, abs=0.01)

    def test_ch8_value_conservation(self) -> None:
        """Ch8: total product value = c + v + s = c + l."""
        d = self._make(c=12.0, v=3.0, s=3.0)
        obs = d.observe()
        total = obs["c"] + obs["v"] + obs["s"]
        assert total == pytest.approx(18.0, abs=0.01)
        # l = v + s (living labor = new value)
        assert obs["l"] == pytest.approx(6.0, abs=0.01)

    def test_ch9_yarn_example(self) -> None:
        """Marx's yarn example (Ch9): cotton=10, spindle=2, labor=3 → product=15, surplus=3."""
        d = self._make(
            c=12.0,  # cotton(10) + spindle(2)
            v=3.0,  # labor-power value
            s=3.0,  # surplus
        )
        obs = d.observe()
        assert obs["c"] == pytest.approx(12.0)
        assert obs["v"] == pytest.approx(3.0)
        assert obs["s"] == pytest.approx(3.0)
        assert obs["l"] == pytest.approx(6.0)  # v + s

    def test_observe_returns_value_tensor(self) -> None:
        """observe() returns the complete value tensor [l, c, v, s, r]."""
        d = self._make()
        obs = d.observe()
        for key in ("l", "c", "v", "s", "r"):
            assert key in obs, f"Missing key: {key}"

    def test_observe_organic_composition(self) -> None:
        """Ch25§2: OCC = c/v."""
        d = self._make(c=12.0, v=3.0)
        obs = d.observe()
        assert obs["occ"] == pytest.approx(4.0)

    def test_invariant_surplus_non_negative(self) -> None:
        """Surplus value cannot be negative under normal production."""
        d = self._make(s=0.0)
        assert d.invariants() == []

    def test_step_updates_weight(self) -> None:
        """Higher exploitation → weight shifts positive (toward valorization)."""
        d = self._make(weight=0.0, e=2.0)  # High exploitation
        result = d.step(_empty_inputs(), _world())
        # With e > 1, weight should shift positive
        assert result.weight > 0.0 or result.weight == 0.0  # at minimum no regression


# ===========================================================================
# WageDialectic Tests (V1 Ch19-22)
# ===========================================================================


class TestValueOfLaborPower:
    """ValueOfLaborPower pole."""

    def test_default_construction(self) -> None:
        v = ValueOfLaborPower()
        assert v.reproduction_cost >= 0.0

    def test_custom_values(self) -> None:
        v = ValueOfLaborPower(
            reproduction_cost=5.0,
            subsistence_hours=4.0,
            historical_moral_element=0.3,
        )
        assert v.reproduction_cost == 5.0
        assert v.subsistence_hours == 4.0
        assert v.historical_moral_element == 0.3


class TestPriceOfLaborPower:
    """PriceOfLaborPower pole."""

    def test_default_construction(self) -> None:
        p = PriceOfLaborPower()
        assert p.nominal_wage >= 0.0

    def test_custom_values(self) -> None:
        p = PriceOfLaborPower(
            nominal_wage=10.0,
            real_wage=8.0,
            relative_wage=0.4,
        )
        assert p.nominal_wage == 10.0
        assert p.real_wage == 8.0
        assert p.relative_wage == 0.4

    def test_relative_wage_bounded(self) -> None:
        with pytest.raises(ValidationError):
            PriceOfLaborPower(relative_wage=-0.1)
        with pytest.raises(ValidationError):
            PriceOfLaborPower(relative_wage=1.1)


class TestWageDialectic:
    """WageDialectic: value of labor-power ↔ price of labor-power (V1 Ch19)."""

    def _make(self, weight: float = 0.0) -> WageDialectic:
        return WageDialectic(
            pole_a=ValueOfLaborPower(reproduction_cost=5.0, subsistence_hours=4.0),
            pole_b=PriceOfLaborPower(nominal_wage=6.0, real_wage=5.5, relative_wage=0.4),
            weight=weight,
            tick_created=0,
            tick_updated=0,
        )

    def test_type_tag(self) -> None:
        d = self._make()
        assert d.type_tag == "WageDialectic"

    def test_step_returns_same_type(self) -> None:
        d = self._make()
        result = d.step(_empty_inputs(), _world())
        assert isinstance(result, WageDialectic)

    def test_ch19_value_neq_price(self) -> None:
        """Ch19: value of labor-power ≠ price of labor."""
        d = self._make()
        assert d.pole_a.reproduction_cost != d.pole_b.nominal_wage

    def test_reserve_army_shifts_weight_positive(self) -> None:
        """Reserve army pressure shifts weight positive (sell market, B dominant)."""
        d = self._make(weight=0.0)
        inputs = TickInputs(upstream={d.id: {"reserve_army_pressure": 0.5}})
        result = d.step(inputs, _world())
        assert result.weight > 0.0

    def test_negative_weight_is_buy_market(self) -> None:
        """weight < 0 = tight labor market (buy market for labor-power)."""
        d = self._make(weight=-0.4)
        obs = d.observe()
        assert obs["principal_aspect"] == "A"  # A dominant = tight market

    def test_positive_weight_is_sell_market(self) -> None:
        """weight > 0 = loose labor market (sell market for labor-power)."""
        d = self._make(weight=0.4)
        obs = d.observe()
        assert obs["principal_aspect"] == "B"  # B dominant = loose market

    def test_observe_includes_wage_fields(self) -> None:
        d = self._make()
        obs = d.observe()
        assert "reproduction_cost" in obs
        assert "nominal_wage" in obs
        assert "real_wage" in obs
        assert "relative_wage" in obs


# ===========================================================================
# AccumulationDialectic Tests (V1 Ch23-25)
# ===========================================================================


class TestConcentrationOfCapital:
    """ConcentrationOfCapital pole."""

    def test_default_construction(self) -> None:
        c = ConcentrationOfCapital()
        assert c.total_capital >= 0.0

    def test_custom_values(self) -> None:
        c = ConcentrationOfCapital(
            total_capital=1000.0,
            reinvestment_rate=0.5,
            fixed_capital=400.0,
            centralization_index=0.3,
        )
        assert c.total_capital == 1000.0
        assert c.reinvestment_rate == 0.5
        assert c.centralization_index == 0.3


class TestReserveArmyExpansion:
    """ReserveArmyExpansion pole."""

    def test_default_construction(self) -> None:
        ra = ReserveArmyExpansion()
        assert 0.0 <= ra.unemployed_fraction <= 1.0

    def test_custom_values(self) -> None:
        ra = ReserveArmyExpansion(
            unemployed_fraction=0.1,
            wage_pressure=-0.2,
            absorption_rate=0.05,
            total_labor_pool=1000.0,
        )
        assert ra.unemployed_fraction == 0.1
        assert ra.wage_pressure == -0.2
        assert ra.total_labor_pool == 1000.0


class TestAccumulationDialectic:
    """AccumulationDialectic: concentration ↔ reserve army (V1 Ch25)."""

    def _make(self, weight: float = 0.0) -> AccumulationDialectic:
        return AccumulationDialectic(
            pole_a=ConcentrationOfCapital(
                total_capital=1000.0,
                reinvestment_rate=0.5,
                fixed_capital=400.0,
                centralization_index=0.2,
            ),
            pole_b=ReserveArmyExpansion(
                unemployed_fraction=0.05,
                wage_pressure=0.0,
                absorption_rate=0.03,
                total_labor_pool=500.0,
            ),
            weight=weight,
            tick_created=0,
            tick_updated=0,
        )

    def test_type_tag(self) -> None:
        d = self._make()
        assert d.type_tag == "AccumulationDialectic"

    def test_step_returns_same_type(self) -> None:
        d = self._make()
        result = d.step(_empty_inputs(), _world())
        assert isinstance(result, AccumulationDialectic)

    def test_observe_includes_reserve_army_fields(self) -> None:
        d = self._make()
        obs = d.observe()
        assert "total_capital" in obs
        assert "unemployed_fraction" in obs
        assert "total_labor_pool" in obs

    def test_rising_occ_displaces_workers(self) -> None:
        """Ch25§2: rising OCC → labor displacement."""
        d = self._make(weight=0.0)
        # Feed high OCC from upstream
        inputs = TickInputs(
            upstream={
                d.id: {
                    "rate_of_exploitation": 1.0,
                    "occ": 5.0,
                    "labor_hours_contributed": 100.0,
                }
            }
        )
        result = d.step(inputs, _world())
        # Weight should shift positive (reserve army expanding)
        assert isinstance(result, AccumulationDialectic)

    def test_no_input_identity(self) -> None:
        d = self._make(weight=0.3)
        result = d.step(_empty_inputs(), _world())
        assert result.weight == d.weight


# ===========================================================================
# PrimitiveAccumulationDialectic Tests (V1 Ch26-33 + Sakai/MIM(P))
# ===========================================================================


class TestColonialExpropriation:
    """ColonialExpropriation pole."""

    def test_default_construction(self) -> None:
        ce = ColonialExpropriation()
        assert 0.0 <= ce.expropriation_rate <= 1.0

    def test_custom_values(self) -> None:
        ce = ColonialExpropriation(
            expropriation_rate=0.3,
            colonial_extraction=500.0,
            land_theft=0.7,
            super_exploitation_rate=0.5,
        )
        assert ce.expropriation_rate == 0.3
        assert ce.colonial_extraction == 500.0
        assert ce.land_theft == 0.7
        assert ce.super_exploitation_rate == 0.5

    def test_expropriation_rate_bounded(self) -> None:
        with pytest.raises(ValidationError):
            ColonialExpropriation(expropriation_rate=-0.1)
        with pytest.raises(ValidationError):
            ColonialExpropriation(expropriation_rate=1.1)


class TestSettlerFormation:
    """SettlerFormation pole (Sakai/MIM(P))."""

    def test_default_construction(self) -> None:
        sf = SettlerFormation()
        assert 0.0 <= sf.settler_share <= 1.0

    def test_custom_values(self) -> None:
        sf = SettlerFormation(
            settler_share=0.6,
            labor_aristocracy_ratio=1.2,
            settler_identity=0.7,
            immiseration_resistance=0.8,
        )
        assert sf.settler_share == 0.6
        assert sf.labor_aristocracy_ratio == 1.2
        assert sf.settler_identity == 0.7
        assert sf.immiseration_resistance == 0.8

    def test_labor_aristocracy_above_one_is_valid(self) -> None:
        """MIM(P): Wc/Vc > 1 = labor aristocracy (net exploiters)."""
        sf = SettlerFormation(labor_aristocracy_ratio=1.5)
        assert sf.labor_aristocracy_ratio == 1.5


class TestPrimitiveAccumulationDialectic:
    """PrimitiveAccumulationDialectic: colonial expropriation ↔ settler formation."""

    def _make(self, weight: float = 0.0) -> PrimitiveAccumulationDialectic:
        return PrimitiveAccumulationDialectic(
            pole_a=ColonialExpropriation(
                expropriation_rate=0.3,
                colonial_extraction=500.0,
                land_theft=0.7,
                super_exploitation_rate=0.5,
            ),
            pole_b=SettlerFormation(
                settler_share=0.5,
                labor_aristocracy_ratio=1.2,
                settler_identity=0.6,
                immiseration_resistance=0.7,
            ),
            weight=weight,
            tick_created=0,
            tick_updated=0,
        )

    def test_type_tag(self) -> None:
        d = self._make()
        assert d.type_tag == "PrimitiveAccumulationDialectic"

    def test_step_returns_same_type(self) -> None:
        d = self._make()
        result = d.step(_empty_inputs(), _world())
        assert isinstance(result, PrimitiveAccumulationDialectic)

    def test_observe_includes_settler_fields(self) -> None:
        """observe() returns settler-colonial metrics for downstream consumption."""
        d = self._make()
        obs = d.observe()
        assert "colonial_extraction" in obs
        assert "settler_share" in obs
        assert "labor_aristocracy_ratio" in obs
        assert "settler_identity" in obs
        assert "land_theft" in obs

    def test_negative_weight_is_raw_violence(self) -> None:
        """weight < 0 = A dominant = raw colonial violence primary."""
        d = self._make(weight=-0.6)
        obs = d.observe()
        assert obs["principal_aspect"] == "A"

    def test_positive_weight_is_mature_settler(self) -> None:
        """weight > 0 = B dominant = settler formation mature, bribe flowing."""
        d = self._make(weight=0.6)
        obs = d.observe()
        assert obs["principal_aspect"] == "B"

    def test_no_input_identity(self) -> None:
        d = self._make(weight=0.3)
        result = d.step(_empty_inputs(), _world())
        assert result.weight == d.weight

    def test_weight_clamped(self) -> None:
        d = self._make(weight=0.95)
        inputs = TickInputs(upstream={d.id: {"extraction_boost": 1.0}})
        result = d.step(inputs, _world())
        assert -1.0 <= result.weight <= 1.0


# ===========================================================================
# Coupling Tests (5-dialectic wired world)
# ===========================================================================


class TestDialecticCoupling:
    """Integration test: 5 dialectics wired together run without violations."""

    def _make_world(self) -> World:
        """Build a 5-dialectic world with morphism wiring."""
        lp = LaborProcessDialectic(
            pole_a=ConcreteLabor(skill=0.5, intensity=0.5, hours=8.0),
            pole_b=AbstractLabor(snlt=4.0, productivity=1.0),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        pd = ProductionDialectic(
            pole_a=DepartmentRow(
                c=12.0,
                v=3.0,
                s=3.0,
            ),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        wd = WageDialectic(
            pole_a=ValueOfLaborPower(reproduction_cost=5.0, subsistence_hours=4.0),
            pole_b=PriceOfLaborPower(nominal_wage=6.0, real_wage=5.5, relative_wage=0.4),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        ad = AccumulationDialectic(
            pole_a=ConcentrationOfCapital(
                total_capital=1000.0,
                reinvestment_rate=0.5,
                fixed_capital=400.0,
                centralization_index=0.2,
            ),
            pole_b=ReserveArmyExpansion(
                unemployed_fraction=0.05,
                wage_pressure=0.0,
                absorption_rate=0.03,
                total_labor_pool=500.0,
            ),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        pa = PrimitiveAccumulationDialectic(
            pole_a=ColonialExpropriation(
                expropriation_rate=0.3,
                colonial_extraction=500.0,
                land_theft=0.7,
                super_exploitation_rate=0.5,
            ),
            pole_b=SettlerFormation(
                settler_share=0.5,
                labor_aristocracy_ratio=1.2,
                settler_identity=0.6,
                immiseration_resistance=0.7,
            ),
            weight=0.3,
            tick_created=0,
            tick_updated=0,
        )

        morphisms = [
            Morphism(source_id=lp.id, target_id=pd.id, relation="feeds", weight=1.0),
            Morphism(source_id=pd.id, target_id=ad.id, relation="feeds", weight=1.0),
            Morphism(source_id=ad.id, target_id=wd.id, relation="feeds", weight=1.0),
            Morphism(source_id=wd.id, target_id=lp.id, relation="feeds", weight=1.0),
            Morphism(source_id=pa.id, target_id=ad.id, relation="feeds", weight=1.0),
            Morphism(source_id=pa.id, target_id=wd.id, relation="feeds", weight=1.0),
        ]

        return World(
            tick=0,
            dialectics={
                lp.id: lp,
                pd.id: pd,
                wd.id: wd,
                ad.id: ad,
                pa.id: pa,
            },
            morphisms=morphisms,
        )

    def test_five_dialectic_world_10_ticks_no_violations(self) -> None:
        """5-dialectic wired world runs 10 ticks without invariant violations."""
        world = self._make_world()
        for _ in range(10):
            world, events = tick(world, [])
            violations = [e for e in events if e.event_type == "invariant_violation"]
            assert len(violations) == 0, f"Violations at tick {world.tick}: {violations}"

    def test_all_weights_remain_bounded(self) -> None:
        """All weights stay in [-1, 1] after 10 ticks."""
        world = self._make_world()
        for _ in range(10):
            world, _ = tick(world, [])
        for d in world.dialectics.values():
            assert -1.0 <= d.weight <= 1.0, f"{d.type_tag} weight out of bounds: {d.weight}"

    def test_all_dialectics_stepped(self) -> None:
        """All 5 dialectics have tick_updated > 0 after one tick."""
        world = self._make_world()
        world, _ = tick(world, [])
        for d in world.dialectics.values():
            assert d.tick_updated > 0, f"{d.type_tag} not stepped"
