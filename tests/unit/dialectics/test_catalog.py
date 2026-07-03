"""Unit tests for the production opposition catalog (Phase C).

Pins the honest measure each of the five oppositions is bound to, the
empty-input degeneracies, the tenancy rent-free guard, and the
atomization pole mapping — the contract the engine's ContradictionSystem
relies on when it fills :class:`GraphInputs` each tick.
"""

from __future__ import annotations

import pytest

from babylon.dialectics.instances.catalog import GraphInputs, build_default_registry
from babylon.engine.graph import BabylonUGraph

pytestmark = [pytest.mark.unit, pytest.mark.math]


def _reg():  # type: ignore[no-untyped-def]
    return build_default_registry()


def _states(inputs: GraphInputs, tick: int = 0):  # type: ignore[no-untyped-def]
    return {s.key: s for s in _reg().step(inputs, tick=tick)}


class TestRegistryShape:
    def test_five_oppositions_bound(self) -> None:
        assert _reg().keys == ("atomization", "capital_labor", "imperial", "tenancy", "wage")

    def test_capital_labor_is_antagonistic(self) -> None:
        assert _reg().spec_for("capital_labor").antagonistic is True

    def test_rate_weight_passthrough(self) -> None:
        reg = build_default_registry(rate_weight=3.0)
        assert reg._rate_weight == 3.0  # noqa: SLF001 - white-box knob check


class TestCapitalLabor:
    def test_mean_exploitation_gap(self) -> None:
        # Single EXPLOITATION edge, labor=10, capital=30 → gap 0.5, capital dominant.
        states = _states(GraphInputs(exploitation_pairs=((10.0, 30.0),)))
        assert states["capital_labor"].gap == pytest.approx(0.5)
        assert states["capital_labor"].balance == pytest.approx(0.5)  # >0 == capital (B)
        assert states["capital_labor"].leading_pole == "b"

    def test_labor_dominant_flips_leading_pole(self) -> None:
        # Worker overtakes capital (the empirical bridged crossover ~tick 8).
        states = _states(GraphInputs(exploitation_pairs=((30.0, 10.0),)))
        assert states["capital_labor"].balance == pytest.approx(-0.5)
        assert states["capital_labor"].leading_pole == "a"

    def test_mean_over_multiple_edges(self) -> None:
        states = _states(GraphInputs(exploitation_pairs=((0.0, 10.0), (10.0, 10.0))))
        # gaps: 1.0 and 0.0 → mean 0.5
        assert states["capital_labor"].gap == pytest.approx(0.5)


class TestWage:
    def test_wage_is_the_value_wage_counit_defect(self) -> None:
        # (w_paid=18, v_produced=2): the wage vastly exceeds value produced —
        # a large positive Φ (the imperial bribe). Reordered to (value=A, wage=B).
        states = _states(GraphInputs(wage_value_pairs=((18.0, 2.0),)))
        assert states["wage"].gap == pytest.approx(0.8)  # |18-2|/(18+2)
        assert states["wage"].balance == pytest.approx(0.8)  # wage exceeds value = bribe
        assert states["wage"].leading_pole == "b"  # price-of-labor-power dominant

    def test_wage_negative_when_value_exceeds_wage(self) -> None:
        # (w_paid=2, v_produced=18): super-exploited — wage below value produced.
        states = _states(GraphInputs(wage_value_pairs=((2.0, 18.0),)))
        assert states["wage"].balance == pytest.approx(-0.8)
        assert states["wage"].leading_pole == "a"  # value-produced dominant

    def test_wage_empty_pairs_is_zero_no_endpoint_fallback(self) -> None:
        # No (w, v) data → (0, 0); the old WAGES-endpoint proxy is removed.
        states = _states(GraphInputs())
        assert states["wage"].gap == 0.0
        assert states["wage"].balance == 0.0


class TestTenancy:
    def test_rent_free_edge_is_degenerate_zero(self) -> None:
        """A territory with rent_level ~ 0 must NOT saturate to 1.0."""
        states = _states(GraphInputs(tenancy_pairs=((5.0, 0.0),)))
        assert states["tenancy"].gap == 0.0
        assert states["tenancy"].balance == 0.0

    def test_rent_burden_measured_when_present(self) -> None:
        states = _states(GraphInputs(tenancy_pairs=((10.0, 30.0),)))
        assert states["tenancy"].gap == pytest.approx(0.5)
        assert states["tenancy"].balance == pytest.approx(0.5)  # rent (B) dominant


class TestAtomization:
    def test_fully_atomized_solidarity_graph(self) -> None:
        g = BabylonUGraph()
        g.add_nodes_from(["C001", "C002", "C003"])  # no SOLIDARITY edges
        states = _states(GraphInputs(solidarity_subgraph=g))
        assert states["atomization"].gap == pytest.approx(1.0)
        assert states["atomization"].balance == pytest.approx(-1.0)  # atomized pole

    def test_fully_unified_solidarity_graph(self) -> None:
        g = BabylonUGraph()
        g.add_edges_from([("C001", "C002"), ("C002", "C003"), ("C001", "C003")])
        states = _states(GraphInputs(solidarity_subgraph=g))
        assert states["atomization"].gap == pytest.approx(0.0)
        assert states["atomization"].balance == pytest.approx(1.0)  # unified pole

    def test_empty_subgraph_is_zero(self) -> None:
        states = _states(GraphInputs(solidarity_subgraph=BabylonUGraph()))
        assert states["atomization"].gap == 0.0
        assert states["atomization"].balance == 0.0


class TestImperial:
    def test_imperial_reads_the_wage_value_defect(self) -> None:
        # Rebound in D5: imperial reads the same (w_paid, v_produced) defect.
        states = _states(GraphInputs(wage_value_pairs=((18.0, 2.0),)))
        assert states["imperial"].gap == pytest.approx(0.8)
        assert states["imperial"].balance == pytest.approx(0.8)  # imperial-rent inflow

    def test_imperial_and_wage_share_the_same_defect(self) -> None:
        # Same inputs, same arithmetic — different poles/level only.
        inputs = GraphInputs(wage_value_pairs=((18.0, 2.0), (10.0, 8.0)))
        states = _states(inputs)
        assert states["imperial"].gap == pytest.approx(states["wage"].gap)
        assert states["imperial"].balance == pytest.approx(states["wage"].balance)

    def test_imperial_empty_is_zero(self) -> None:
        states = _states(GraphInputs())
        assert states["imperial"].gap == 0.0
        assert states["imperial"].balance == 0.0


class TestEmptyInputs:
    def test_all_gaps_zero_on_empty_inputs(self) -> None:
        states = _states(GraphInputs())
        assert all(s.gap == 0.0 for s in states.values())

    def test_step_is_pure(self) -> None:
        inputs = GraphInputs(exploitation_pairs=((1.0, 4.0),), wage_value_pairs=((3.0, 2.0),))
        reg = _reg()
        assert reg.step(inputs, tick=7) == reg.step(inputs, tick=7)


class TestLevelPlacement:
    """E1: each opposition is placed on a level-lattice rung (level_name)."""

    def test_level_names_match_the_catalog(self) -> None:
        reg = _reg()
        placement = {key: reg.spec_for(key).level_name for key in reg.keys}
        assert placement == {
            "capital_labor": "county",
            "wage": "county",
            "tenancy": "county",
            "atomization": "class",
            "imperial": "bloc",
        }
