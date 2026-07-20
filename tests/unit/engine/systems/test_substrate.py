"""Tests for SubstrateSystem -- real dynamics + ScaleAdjunction binding (#39 T6).

Fast tier: every test injects synthetic ``cz_adjunction_fn``/
``msa_adjunction_fn`` callables so the lattice-binding path never touches
the reference DB (the real ``msa_adjunction()`` opens a reference-DB
session -- see the module docstring). The generator's DB re-derivation
test lives in ``tests/unit/engine/scenarios/test_us_county_data.py``
(``requires_reference_db`` tier, mirroring T4's).

Formula cross-check (default SubstrateDefines: depletion_scale=1.0,
regeneration_rate=0.0, entropy_factor=1.2), via
``calculate_biocapacity_delta``:

    regeneration = regeneration_rate * max_biocapacity = 0.0
    raw_extraction = extraction_intensity * current_biocapacity
    ecological_cost = raw_extraction * entropy_factor
    delta = regeneration - ecological_cost
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from babylon.config.defines import GameDefines, SubstrateDefines
from babylon.domain.dialectics.instances.scale import ScaleAdjunction
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.substrate import (
    SUBSTRATE_CZ_EXCLUDED_KEY,
    SUBSTRATE_CZ_KEY,
    SUBSTRATE_MSA_KEY,
    SUBSTRATE_NATION_KEY,
    SUBSTRATE_STATE_KEY,
    SubstrateSystem,
)
from babylon.topology.graph import BabylonGraph


def _stub_adjunction_fn(mapping: dict[str, str]) -> Callable[[], ScaleAdjunction]:
    """A zero-DB-access stand-in for cz_adjunction()/msa_adjunction()."""

    def _fn() -> ScaleAdjunction:
        return ScaleAdjunction.uniform(mapping)

    return _fn


def _system(
    *,
    cz_mapping: dict[str, str] | None = None,
    msa_mapping: dict[str, str] | None = None,
) -> SubstrateSystem:
    return SubstrateSystem(
        cz_adjunction_fn=_stub_adjunction_fn(cz_mapping or {}),
        msa_adjunction_fn=_stub_adjunction_fn(msa_mapping or {}),
    )


@pytest.mark.unit
class TestCanonicalNoOp:
    """No county_fips (the 5 canonical qa:regression scenarios) or no
    raw_material_stock -> step() writes nothing and publishes nothing."""

    def test_territory_without_county_fips_is_untouched(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            raw_material_stock=100.0,
            extraction_intensity=0.5,
        )
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        _system().step(graph, services, context)

        assert graph.nodes["T001"]["raw_material_stock"] == 100.0
        assert context.persistent_data == {}

    def test_unseeded_county_stock_none_is_skipped(self) -> None:
        """county_fips set but raw_material_stock is None -- never touched."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="11001",
            raw_material_stock=None,
            extraction_intensity=0.5,
        )
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        _system().step(graph, services, context)

        assert graph.nodes["T001"]["raw_material_stock"] is None
        assert context.persistent_data == {}

    def test_missing_raw_material_stock_attr_is_skipped(self) -> None:
        """A territory that never carries the attribute at all (e.g. the
        5 canonical scenarios' plain Territory nodes) is equally a no-op."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="11001",
            extraction_intensity=0.5,
        )
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        _system().step(graph, services, context)

        assert "raw_material_stock" not in graph.nodes["T001"]
        assert context.persistent_data == {}

    def test_publishes_nothing_when_zero_eligible_among_mixed_nodes(self) -> None:
        """A graph with non-territory nodes and an ineligible territory
        still publishes nothing (not even empty aggregate dicts)."""
        graph = BabylonGraph()
        graph.add_node("C001", _node_type="social_class", wealth=10.0)
        graph.add_node("T001", _node_type="territory", raw_material_stock=5.0)  # no county_fips
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        _system().step(graph, services, context)

        assert context.persistent_data == {}


@pytest.mark.unit
class TestDepletionMath:
    """Hand-computed, formula-cross-checked depletion."""

    def test_default_coefficients_deplete_as_expected(self) -> None:
        """stock=100, extraction=0.2, defaults (scale=1.0, regen=0.0, entropy=1.2).

        raw_extraction = 0.2 * 100 = 20; ecological_cost = 20 * 1.2 = 24;
        delta = 0 - 24 = -24; new_stock = 100 - 24 = 76.
        """
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=100.0,
            extraction_intensity=0.2,
        )
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        _system(cz_mapping={"01001": "CZ1"}).step(graph, services, context)

        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(76.0, abs=1e-9)

    def test_zero_extraction_leaves_stock_unchanged(self) -> None:
        """No extraction, default regeneration=0.0 -> delta = 0."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=42.0,
            extraction_intensity=0.0,
        )
        services = ServiceContainer.create()

        _system(cz_mapping={"01001": "CZ1"}).step(graph, services, TickContext(tick=1))

        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(42.0)

    def test_regeneration_is_zero_by_default_monotone_nonincreasing(self) -> None:
        """Across several ticks with sustained extraction, stock never rises."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=1000.0,
            extraction_intensity=0.05,
        )
        services = ServiceContainer.create()
        system = _system(cz_mapping={"01001": "CZ1"})

        stocks = []
        for tick in range(1, 6):
            system.step(graph, services, TickContext(tick=tick))
            stocks.append(graph.nodes["T001"]["raw_material_stock"])

        assert all(a >= b for a, b in zip(stocks[:-1], stocks[1:], strict=True)), (
            f"stock must never increase with regeneration_rate=0.0: {stocks}"
        )
        assert stocks[-1] < stocks[0], "sustained extraction must actually deplete the stock"

    def test_nonzero_regeneration_coefficient_is_wired(self) -> None:
        """A modder-set regeneration_rate > 0 measurably regenerates the
        stock back toward its initial seeded value (the ceiling) once it
        has been depleted below that ceiling.

        The formula's own ceiling guard (``current >= max`` -> regeneration
        forced to 0) means the FIRST tick a territory is seen can never
        show regeneration (current == the just-captured ceiling) -- this is
        why the coefficient must be exercised across two ticks: deplete
        first, then observe regrowth toward the ceiling captured at tick 1.
        """
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=100.0,
            extraction_intensity=0.5,
        )
        defines = GameDefines(substrate=SubstrateDefines(regeneration_rate=0.1))
        services = ServiceContainer.create(defines=defines)
        system = _system(cz_mapping={"01001": "CZ1"})

        # Tick 1: ceiling captured at 100.0; pure depletion (current==ceiling
        # forces regeneration to 0 this tick).
        # raw_extraction = 0.5*100=50; cost=50*1.2=60; stock=100-60=40.
        system.step(graph, services, TickContext(tick=1))
        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(40.0)

        # Tick 2: zero extraction -> pure regeneration toward the 100.0 ceiling.
        graph.update_node("T001", extraction_intensity=0.0)
        system.step(graph, services, TickContext(tick=2))
        # regeneration = 0.1 * 100 (the tick-1 ceiling) = 10; stock=40+10=50.
        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(50.0)

    def test_regeneration_never_exceeds_the_initial_ceiling(self) -> None:
        """Even a large regeneration_rate cannot push the stock above the
        value it was initially seeded with -- clamped like MetabolismSystem
        clamps biocapacity to max_biocapacity."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=95.0,
            extraction_intensity=0.0,
        )
        defines = GameDefines(substrate=SubstrateDefines(regeneration_rate=1.0))
        services = ServiceContainer.create(defines=defines)
        system = _system(cz_mapping={"01001": "CZ1"})

        # First tick captures the ceiling at 95.0 (current==ceiling forces
        # regen to 0 here too) -- confirm no change, then deplete a touch so
        # a SECOND tick can show regeneration clamped at the 95.0 ceiling,
        # never climbing back to some larger figure.
        system.step(graph, services, TickContext(tick=1))
        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(95.0)

        graph.update_node("T001", extraction_intensity=0.1)
        system.step(graph, services, TickContext(tick=2))
        stock_after_tick2 = graph.nodes["T001"]["raw_material_stock"]
        assert stock_after_tick2 < 95.0

        graph.update_node("T001", extraction_intensity=0.0)
        system.step(graph, services, TickContext(tick=3))
        # regeneration_rate=1.0 * ceiling(95.0) would overshoot 95 on its
        # own -- must clamp at the 95.0 ceiling, never above it.
        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(95.0)

    def test_depletion_scale_coefficient_is_wired(self) -> None:
        """depletion_scale multiplies extraction_intensity before the formula."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=100.0,
            extraction_intensity=0.1,
        )
        defines = GameDefines(substrate=SubstrateDefines(depletion_scale=2.0))
        services = ServiceContainer.create(defines=defines)

        _system(cz_mapping={"01001": "CZ1"}).step(graph, services, TickContext(tick=1))

        # effective extraction = 0.1 * 2.0 = 0.2; raw_extraction = 0.2*100=20;
        # cost = 20*1.2=24; new_stock = 100-24=76 (same as the depletion_scale=1
        # extraction=0.2 case above -- scale and intensity are interchangeable).
        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(76.0)

    def test_clamps_at_zero_never_negative(self) -> None:
        """Extreme extraction on a small stock clamps at 0, never negative."""
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=5.0,
            extraction_intensity=1.0,
        )
        services = ServiceContainer.create()

        _system(cz_mapping={"01001": "CZ1"}).step(graph, services, TickContext(tick=1))

        # raw_extraction = 1.0*5=5; cost=5*1.2=6; delta=-6; 5-6=-1 -> clamped to 0.
        assert graph.nodes["T001"]["raw_material_stock"] == 0.0


@pytest.mark.unit
class TestOneTickLag:
    """extraction_intensity written by ProductionSystem this tick is only
    consumed by SubstrateSystem NEXT tick (position 2.5 < 3.0)."""

    def test_extraction_written_this_tick_affects_next_tick_only(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="01001",
            raw_material_stock=100.0,
            extraction_intensity=0.0,  # nothing extracted "last tick"
        )
        services = ServiceContainer.create()
        system = _system(cz_mapping={"01001": "CZ1"})

        # Tick 1: extraction_intensity=0.0 -> no depletion.
        system.step(graph, services, TickContext(tick=1))
        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(100.0)

        # ProductionSystem (@3.0) runs AFTER Substrate within tick 1 and
        # writes a fresh extraction_intensity for the graph to carry into
        # tick 2.
        graph.update_node("T001", extraction_intensity=0.3)

        # Tick 2: Substrate reads the tick-1-Production-written value.
        system.step(graph, services, TickContext(tick=2))
        # raw_extraction = 0.3*100=30; cost=30*1.2=36; new=100-36=64.
        assert graph.nodes["T001"]["raw_material_stock"] == pytest.approx(64.0)


@pytest.mark.unit
class TestScaleLatticeAggregates:
    """The first engine consumer of ScaleAdjunction: extensive (summed)
    aggregates at CZ/MSA/state/nation grain, plus the honest CZ exclusion
    companion key."""

    def _build_three_county_graph(self) -> BabylonGraph:
        graph = BabylonGraph()
        # Two counties sharing a CZ and a state.
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="11111",
            raw_material_stock=100.0,
            extraction_intensity=0.0,
        )
        graph.add_node(
            "T002",
            _node_type="territory",
            county_fips="11112",
            raw_material_stock=50.0,
            extraction_intensity=0.0,
        )
        # A third county, different state, deliberately absent from the CZ
        # stub mapping (simulating one of the real 19-county CZ gap
        # counties) and absent from the MSA stub mapping too (partial
        # coverage by design).
        graph.add_node(
            "T003",
            _node_type="territory",
            county_fips="22221",
            raw_material_stock=30.0,
            extraction_intensity=0.0,
        )
        return graph

    def _system_for_three_counties(self) -> SubstrateSystem:
        return _system(
            cz_mapping={"11111": "CZ_A", "11112": "CZ_A"},  # 22221 excluded
            msa_mapping={"11111": "MSA_X"},  # 11112, 22221 absent (partial)
        )

    def test_state_and_nation_are_total(self) -> None:
        graph = self._build_three_county_graph()
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        self._system_for_three_counties().step(graph, services, context)

        assert context.persistent_data[SUBSTRATE_STATE_KEY] == {"11": 150.0, "22": 30.0}
        assert context.persistent_data[SUBSTRATE_NATION_KEY] == {"US": 180.0}

    def test_cz_excludes_the_uncovered_county_and_records_it(self) -> None:
        graph = self._build_three_county_graph()
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        self._system_for_three_counties().step(graph, services, context)

        assert context.persistent_data[SUBSTRATE_CZ_KEY] == {"CZ_A": 150.0}
        assert context.persistent_data[SUBSTRATE_CZ_EXCLUDED_KEY] == ["22221"]

    def test_msa_is_partial_by_design_no_exclusion_list(self) -> None:
        graph = self._build_three_county_graph()
        services = ServiceContainer.create()
        context = TickContext(tick=1)

        self._system_for_three_counties().step(graph, services, context)

        assert context.persistent_data[SUBSTRATE_MSA_KEY] == {"MSA_X": 100.0}

    def test_aggregates_are_deterministic_across_two_runs(self) -> None:
        services = ServiceContainer.create()

        graph_a = self._build_three_county_graph()
        context_a = TickContext(tick=1)
        self._system_for_three_counties().step(graph_a, services, context_a)

        graph_b = self._build_three_county_graph()
        context_b = TickContext(tick=1)
        self._system_for_three_counties().step(graph_b, services, context_b)

        assert (
            context_a.persistent_data[SUBSTRATE_CZ_KEY]
            == context_b.persistent_data[SUBSTRATE_CZ_KEY]
        )
        assert (
            context_a.persistent_data[SUBSTRATE_MSA_KEY]
            == context_b.persistent_data[SUBSTRATE_MSA_KEY]
        )
        assert (
            context_a.persistent_data[SUBSTRATE_STATE_KEY]
            == context_b.persistent_data[SUBSTRATE_STATE_KEY]
        )
        assert (
            context_a.persistent_data[SUBSTRATE_NATION_KEY]
            == context_b.persistent_data[SUBSTRATE_NATION_KEY]
        )
        assert (
            context_a.persistent_data[SUBSTRATE_CZ_EXCLUDED_KEY]
            == context_b.persistent_data[SUBSTRATE_CZ_EXCLUDED_KEY]
        )

    def test_lattice_is_built_once_not_rebuilt_per_tick(self) -> None:
        """The rungs object is cached; a second tick reuses the same
        ScaleAdjunction instances (no rebuild -- see module docstring)."""
        graph = self._build_three_county_graph()
        services = ServiceContainer.create()
        system = self._system_for_three_counties()

        system.step(graph, services, TickContext(tick=1))
        rungs_after_first = system._rungs  # noqa: SLF001 -- white-box cache check
        system.step(graph, services, TickContext(tick=2))
        rungs_after_second = system._rungs  # noqa: SLF001

        assert rungs_after_first is rungs_after_second


@pytest.mark.unit
class TestSubstrateSystemIdentity:
    def test_name_and_position(self) -> None:
        system = SubstrateSystem()
        assert system.name == "substrate"
        assert system.position == 2.5

    def test_implements_system_protocol(self) -> None:
        from babylon.kernel.system_protocol import System

        assert isinstance(SubstrateSystem(), System)

    def test_default_construction_uses_real_adjunction_functions(self) -> None:
        """No-arg construction (the _DEFAULT_SYSTEMS registration site) must
        still work -- the injectable params default to the real functions."""
        system = SubstrateSystem()
        assert system._cz_adjunction_fn.__name__ == "cz_adjunction"  # noqa: SLF001
        assert system._msa_adjunction_fn.__name__ == "msa_adjunction"  # noqa: SLF001
