"""Behavioral laws for SubstrateSystem (P27 Phase-0 coverage backfill, Task 11).

Read end-to-end before writing: ``src/babylon/engine/systems/substrate.py``
(``SubstrateSystem.step``, lines 193-260, plus ``_read_ceiling`` at 262-292 and
the module docstring's "Scope: raw_material_stock ONLY" / "Lattice binding"
sections), the shared formula it calls,
``src/babylon/formulas/metabolic_rift.py::calculate_biocapacity_delta``
(lines 9-52), and the extensive-sum aggregator it publishes into,
``src/babylon/domain/dialectics/instances/scale.py::ScaleAdjunction.aggregate``
(lines 141-156).

Laws pinned (each traces to a specific source range -- see per-test
docstrings for file:line grounding):

  L1 -- clamp: post-step ``raw_material_stock`` on every eligible territory
        always lands in ``[0.0, raw_material_capacity]``, for ANY defines
        coefficients and ANY pre-tick stock/capacity/extraction values
        (``substrate.py:237-244``'s ``_write_clamped(lo=0.0, hi=ceiling)``).
  L2 -- monotone depletion under the SHIPPED DEFAULT coefficients
        (``regeneration_rate=0.0`` -- ``data/defines.yaml:1018``, "minerals
        are non-renewable, so the default is 0.0 (monotone depletion)"):
        with a non-negative extraction_intensity, ``raw_material_stock``
        never rises in one tick (``metabolic_rift.py:40-52``: regeneration
        is forced to ``0.0`` whenever the rate is ``0.0``, so
        ``delta = -ecological_cost <= 0``).
  L3 -- extensive-sum conservation: ``substrate.nation`` (published at
        ``substrate.py:256``) always equals the sum of every eligible
        territory's post-depletion stock -- ``ScaleAdjunction.aggregate``
        (``scale.py:141-156``) is a plain per-parent sum with no share
        weighting, and the module docstring (``substrate.py:58-60``) states
        the four rungs are "EXTENSIVE (summed, never
        ``aggregate_intensive``)".
  L4 -- inactivity: a territory with no ``county_fips``, or with
        ``raw_material_stock`` absent/``None``, is never touched and the
        tick publishes NOTHING into ``context.persistent_data``
        (``substrate.py:209-219``'s eligibility filter + early ``return``).

Caveat (NOT a law): the per-territory clamp (L1) does NOT imply a
system-wide conservation law the way a wealth-TRANSFER system would -- this
system is a depletion/regeneration stock dynamic (mass can leave via
``ecological_cost`` or appear via ``regeneration``), so "total stock before
== total stock after" does not hold in general (only the DEFAULT
``regeneration_rate=0.0`` case gives the weaker monotone-non-increase
law, L2, not an equality).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines import GameDefines, SubstrateDefines
from babylon.domain.dialectics.instances.scale import ScaleAdjunction
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.substrate import SUBSTRATE_NATION_KEY, SubstrateSystem
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_EMPTY = ScaleAdjunction.uniform({})


def _services(substrate: SubstrateDefines | None = None) -> ServiceContainer:
    defines = GameDefines().model_copy(update={"substrate": substrate or SubstrateDefines()})
    return ServiceContainer.create(defines=defines)


def _system() -> SubstrateSystem:
    # Both lattice sources stubbed to empty mappings -- no eligible county in
    # any of these fixtures maps to a real CZ/MSA, and none of these laws
    # inspect the cz/msa rungs, only "state"/"nation" (which are TOTAL over
    # every requested county regardless of the cz/msa sources, per
    # levels.py:524-536). Avoids the real msa_adjunction()'s reference-DB
    # session (module docstring, "Lattice binding").
    return SubstrateSystem(cz_adjunction_fn=lambda: _EMPTY, msa_adjunction_fn=lambda: _EMPTY)


def _territory(
    graph: BabylonGraph,
    territory_id: str,
    county_fips: str,
    *,
    stock: float,
    capacity: float,
    extraction_intensity: float = 0.0,
) -> None:
    graph.add_node(
        territory_id,
        _node_type="territory",
        county_fips=county_fips,
        raw_material_stock=stock,
        raw_material_capacity=capacity,
        extraction_intensity=extraction_intensity,
    )


class TestClampLaw:
    """L1: for ANY defines coefficients and ANY pre-tick values, the
    post-step stock is clamped to ``[0.0, raw_material_capacity]`` --
    ``substrate.py:237-244`` always routes the write through
    ``_write_clamped(lo=0.0, hi=ceiling)`` regardless of the computed delta's
    sign or magnitude."""

    @given(
        stock=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False),
        capacity=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False),
        extraction_intensity=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
        depletion_scale=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
        regeneration_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        entropy_factor=st.floats(min_value=1.000001, max_value=3.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_stock_always_lands_in_bounds(
        self,
        stock: float,
        capacity: float,
        extraction_intensity: float,
        depletion_scale: float,
        regeneration_rate: float,
        entropy_factor: float,
    ) -> None:
        graph = BabylonGraph()
        _territory(
            graph,
            "T001",
            "11001",
            stock=stock,
            capacity=capacity,
            extraction_intensity=extraction_intensity,
        )
        services = _services(
            SubstrateDefines(
                depletion_scale=depletion_scale,
                regeneration_rate=regeneration_rate,
                entropy_factor=entropy_factor,
            )
        )
        context = TickContext(tick=1)

        _system().step(graph, services, context)

        new_stock = graph.nodes["T001"]["raw_material_stock"]
        assert -1e-9 <= new_stock <= capacity + 1e-9


class TestMonotoneDepletionUnderDefaultLaw:
    """L2: under the SHIPPED DEFAULT ``regeneration_rate=0.0`` (non-renewable
    minerals, ``defines.yaml:1018``), a non-negative extraction_intensity can
    only hold or lower the stock in one tick -- never raise it. Proven from
    ``metabolic_rift.py:40-52``: ``regeneration = rate * ceiling = 0.0``
    unconditionally when ``rate == 0.0``, so ``delta = -ecological_cost``
    with ``ecological_cost = extraction * current_stock * entropy_factor``
    always ``>= 0``, hence ``delta <= 0``; the subsequent clamp
    (``lo=0.0, hi=ceiling``) can only move the pre-clamp value TOWARD
    ``current_stock``, never past it (never above it), since
    ``pre_clamp <= current_stock`` and ``current_stock >= lo``."""

    @given(
        stock=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False),
        capacity=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False),
        extraction_intensity=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
        depletion_scale=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_stock_never_rises(
        self,
        stock: float,
        capacity: float,
        extraction_intensity: float,
        depletion_scale: float,
    ) -> None:
        graph = BabylonGraph()
        _territory(
            graph,
            "T001",
            "11001",
            stock=stock,
            capacity=capacity,
            extraction_intensity=extraction_intensity,
        )
        services = _services(
            SubstrateDefines(depletion_scale=depletion_scale, regeneration_rate=0.0)
        )
        context = TickContext(tick=1)

        _system().step(graph, services, context)

        new_stock = graph.nodes["T001"]["raw_material_stock"]
        assert new_stock <= stock + 1e-9


class TestNationExtensiveConservationLaw:
    """L3: ``substrate.nation`` is a plain sum (``ScaleAdjunction.aggregate``,
    ``scale.py:141-156``, no share weighting) over EVERY eligible county's
    post-depletion stock -- ``state``/``nation`` are TOTAL over every
    requested county by construction (``levels.py:524-536``), so summing the
    published ``substrate.nation`` dict must equal the sum of the same
    territories' post-step ``raw_material_stock`` read straight off the
    graph."""

    @given(
        stocks=st.tuples(*[st.floats(min_value=0.0, max_value=1_000.0, allow_nan=False)] * 3),
        capacities=st.tuples(*[st.floats(min_value=0.0, max_value=1_000.0, allow_nan=False)] * 3),
        extraction_intensities=st.tuples(
            *[st.floats(min_value=0.0, max_value=2.0, allow_nan=False)] * 3
        ),
    )
    @settings(max_examples=25, deadline=None)
    def test_nation_aggregate_equals_sum_of_post_step_stocks(
        self,
        stocks: tuple[float, float, float],
        capacities: tuple[float, float, float],
        extraction_intensities: tuple[float, float, float],
    ) -> None:
        county_fips = ["11001", "24001", "51001"]
        graph = BabylonGraph()
        for tid, fips, stock, capacity, extraction in zip(
            ("T001", "T002", "T003"),
            county_fips,
            stocks,
            capacities,
            extraction_intensities,
            strict=True,
        ):
            _territory(
                graph, tid, fips, stock=stock, capacity=capacity, extraction_intensity=extraction
            )
        services = _services()
        context = TickContext(tick=1)

        _system().step(graph, services, context)

        expected_total = sum(
            graph.nodes[tid]["raw_material_stock"] for tid in ("T001", "T002", "T003")
        )
        nation_aggregate = context.persistent_data[SUBSTRATE_NATION_KEY]
        assert sum(nation_aggregate.values()) == pytest.approx(expected_total)


class TestInactivityLaw:
    """L4: an ineligible territory (no ``county_fips``, or
    ``raw_material_stock`` absent/``None``) is a full no-op --
    ``substrate.py:209-219`` filters it out of ``eligible`` and the
    subsequent ``if not eligible: return`` (``:218-219``) fires before any
    write or publish."""

    def test_no_county_fips_writes_nothing(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "T001", _node_type="territory", raw_material_stock=100.0, extraction_intensity=0.5
        )
        context = TickContext(tick=1)

        _system().step(graph, _services(), context)

        assert graph.nodes["T001"]["raw_material_stock"] == 100.0
        assert context.persistent_data == {}

    def test_stock_none_writes_nothing(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "T001",
            _node_type="territory",
            county_fips="11001",
            raw_material_stock=None,
            extraction_intensity=0.5,
        )
        context = TickContext(tick=1)

        _system().step(graph, _services(), context)

        assert graph.nodes["T001"]["raw_material_stock"] is None
        assert context.persistent_data == {}

    def test_stock_attr_absent_writes_nothing(self) -> None:
        graph = BabylonGraph()
        graph.add_node(
            "T001", _node_type="territory", county_fips="11001", extraction_intensity=0.5
        )
        context = TickContext(tick=1)

        _system().step(graph, _services(), context)

        assert "raw_material_stock" not in graph.nodes["T001"]
        assert context.persistent_data == {}
