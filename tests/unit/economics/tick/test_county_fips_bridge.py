"""Territory ``county_fips`` contract — owner item 25 (the tick-52 crash).

WorldStateBridge mints per-county territory node ids as ``T{i:03d}`` while
``TickDynamicsSystem`` builds ``ClassDistribution(fips=<node id>)`` — whose ``fips``
is ``min_length=5`` — so a 4-char ``'T001'`` crashed every bridged run at the first
productive tick (the year-boundary tick 52). Owner-ruled fix: ``Territory`` carries a
real ``county_fips`` field; the tick readers and the graph writeback resolve the county
identity from it, while the node id stays a graph-local label.

These tests pin the contract: the model accepts ``county_fips``, it survives the
graph round-trip, the writeback lands county state on the ``T``-prefixed node keyed by
the real FIPS, the readers return the real FIPS, and — critically — abstract territory
nodes with no ``county_fips`` are an EMPTY DOMAIN (Constitution III.11), not a
fabricated pseudo-county.

That last clause is the 2026-07-18 correction. The original fix left a
``county_fips or node.id`` fallback, which fabricated a county identity out of a
graph-local label. It stayed unreachable while ``TickDynamicsSystem`` returned
early on a missing ``melt_calculator``; once task U1.3b opened that gate it
crashed all five ``qa:regression`` scenarios (abstract 2/4-node dialectics whose
territories are ``'T001'``/``'T002'`` and carry no ``county_fips``).
"""

from __future__ import annotations

import pytest

from babylon.domain.economics.tick.graph_bridge import (
    read_tick_state_from_graph,
    write_tick_state_to_graph,
)
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.domain.economics.tick.types import SimulationTickState
from babylon.engine.context import TickContext
from babylon.models.entities.territory import Territory
from babylon.models.enums import SectorType
from babylon.models.world_state import WorldState
from babylon.topology.graph import BabylonGraph
from tests.unit.economics.tick.conftest import WAYNE_FIPS

# A graph-local territory label distinct from the real county FIPS — the shape the
# bridge actually produces (``T{i:03d}``), which is what used to crash at tick 52.
T_LABEL = "T001"


class TestTerritoryCountyFipsField:
    """The Territory model carries an optional real-county identity."""

    def test_accepts_county_fips(self) -> None:
        """A per-county territory with a labelled id can carry its real FIPS."""
        terr = Territory(
            id=T_LABEL,
            name=f"County {WAYNE_FIPS}",
            sector_type=SectorType.INDUSTRIAL,
            county_fips=WAYNE_FIPS,
        )
        assert terr.id == T_LABEL
        assert terr.county_fips == WAYNE_FIPS

    def test_county_fips_defaults_to_none(self) -> None:
        """Abstract territories omit county_fips (backward compatible)."""
        terr = Territory(id=T_LABEL, name="Sector", sector_type=SectorType.INDUSTRIAL)
        assert terr.county_fips is None


class TestCountyFipsRoundTrip:
    """county_fips survives the WorldState <-> graph round-trip."""

    def test_round_trips_through_graph(self) -> None:
        """to_graph -> from_graph preserves county_fips on a T-labelled territory."""
        terr = Territory(
            id=T_LABEL,
            name=f"County {WAYNE_FIPS}",
            sector_type=SectorType.INDUSTRIAL,
            county_fips=WAYNE_FIPS,
        )
        state = WorldState(tick=0, entities={}, territories={T_LABEL: terr}, relationships=[])

        recovered = WorldState.from_graph(state.to_graph(), tick=0)

        assert recovered.territories[T_LABEL].county_fips == WAYNE_FIPS

    def test_from_graph_drops_transient_tick_attrs(self) -> None:
        """A territory node stamped with per-tick outputs still reconstructs.

        Once a run passes the first productive tick, write_tick_state_to_graph
        stamps ``tick_``-prefixed attrs on territory nodes; ``extra='forbid'``
        would reject them on reconstruction without the filter — the second
        blocker on the completing-run path (owner item 25 round-trip).
        """
        terr = Territory(
            id=T_LABEL,
            name=f"County {WAYNE_FIPS}",
            sector_type=SectorType.INDUSTRIAL,
            county_fips=WAYNE_FIPS,
        )
        state = WorldState(tick=0, entities={}, territories={T_LABEL: terr}, relationships=[])
        graph = state.to_graph()
        # Simulate a productive-tick writeback stamping transient outputs.
        graph.update_node(T_LABEL, tick_capital_stock=1.0e9, tick_turnover_crisis=False)

        recovered = WorldState.from_graph(graph, tick=1)

        assert recovered.territories[T_LABEL].county_fips == WAYNE_FIPS

    def test_from_graph_drops_transient_flow_attrs(self) -> None:
        """Spec-109 A7: ``flow_``-prefixed accrual outputs hit the identical
        extra='forbid' landmine as ``tick_`` attrs and must be dropped too.
        """
        terr = Territory(
            id=T_LABEL,
            name=f"County {WAYNE_FIPS}",
            sector_type=SectorType.INDUSTRIAL,
            county_fips=WAYNE_FIPS,
        )
        state = WorldState(tick=0, entities={}, territories={T_LABEL: terr}, relationships=[])
        graph = state.to_graph()
        graph.update_node(T_LABEL, flow_phi_accrued=1234.5, flow_wage_accrued=6789.0)

        recovered = WorldState.from_graph(graph, tick=1)

        assert recovered.territories[T_LABEL].county_fips == WAYNE_FIPS


class TestWritebackResolvesNodeId:
    """The graph writeback maps real FIPS -> graph node id (T-label)."""

    def test_writeback_lands_on_labelled_node(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """county_states keyed by real FIPS write onto the T-labelled node."""
        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory", county_fips=WAYNE_FIPS)

        # sample_tick_state.county_states is keyed by the real FIPS (WAYNE_FIPS)
        write_tick_state_to_graph(graph, sample_tick_state)

        # The tick_ payload must land on the T-labelled node, not be dropped.
        assert "tick_capital_stock" in graph.nodes[T_LABEL]
        assert graph.nodes[T_LABEL]["tick_capital_stock"] == 1_000_000_000.0

    def test_readback_keys_by_real_fips(
        self,
        sample_tick_state: SimulationTickState,
    ) -> None:
        """read_tick_state_from_graph returns county_states keyed by the real FIPS."""
        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory", county_fips=WAYNE_FIPS)
        write_tick_state_to_graph(graph, sample_tick_state)

        result = read_tick_state_from_graph(graph)

        assert result is not None
        assert WAYNE_FIPS in result.county_states
        assert result.county_states[WAYNE_FIPS].fips == WAYNE_FIPS


class TestGetTerritoryFips:
    """TickDynamicsSystem reads the county identity, not the node label."""

    def test_returns_real_fips_for_labelled_node(self) -> None:
        """A T-labelled territory carrying county_fips resolves to the real FIPS."""
        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory", county_fips=WAYNE_FIPS)

        fips = TickDynamicsSystem()._get_territory_fips(graph)

        assert fips == [WAYNE_FIPS]

    def test_node_id_alone_is_not_a_county_identity(self) -> None:
        """Even a FIPS-SHAPED node id is not a county identity by itself.

        Supersedes the old ``test_falls_back_to_node_id_without_county_fips``,
        which pinned the ``county_fips or node.id`` fabrication. The identity
        lives in ``county_fips`` and nowhere else; a node id that merely looks
        like a FIPS is a coincidence of the fixture, and production can never
        produce one (``Territory.id`` is ``^(T[0-9]{3,}|[0-9a-f]{15})$``).
        """
        graph = BabylonGraph()
        graph.add_node(WAYNE_FIPS, _node_type="territory")  # id looks like a FIPS

        assert TickDynamicsSystem()._get_territory_fips(graph) == []

    def test_labelled_node_would_crash_class_distribution_without_fix(self) -> None:
        """Documents the bug: a 4-char node id can't be a ClassDistribution fips.

        Before the fix, TickDynamics used the node id (``'T001'``, 4 chars) as the
        ``fips``, violating ClassDistribution's ``min_length=5``. With the fix the
        readers return the real 5-char FIPS instead, so the crash cannot recur.
        """
        from babylon.domain.economics.dynamics.types import ClassDistribution

        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory", county_fips=WAYNE_FIPS)
        [resolved_fips] = TickDynamicsSystem()._get_territory_fips(graph)

        # The resolved identity must be a valid ClassDistribution fips (>= 5 chars).
        dist = ClassDistribution(
            fips=resolved_fips,
            year=2011,
            bourgeoisie_share=0.01,
            petit_bourgeoisie_share=0.09,
            labor_aristocracy_share=0.40,
            proletariat_share=0.35,
            lumpenproletariat_share=0.15,
        )
        assert dist.fips == WAYNE_FIPS

        # And the raw node label would indeed have been rejected.
        with pytest.raises(ValueError):
            ClassDistribution(
                fips=T_LABEL,
                year=2011,
                bourgeoisie_share=0.01,
                petit_bourgeoisie_share=0.09,
                labor_aristocracy_share=0.40,
                proletariat_share=0.35,
                lumpenproletariat_share=0.15,
            )


class TestAbstractTerritoryIsEmptyDomain:
    """A territory with no ``county_fips`` has NO county economic identity.

    The pre-existing ``county_fips or node.id`` fallback FABRICATED one: it
    asserted that a graph-local label (``'T001'``) or a 15-char H3 cell id was
    a county FIPS code. It never could be — ``Territory.id`` is constrained to
    ``^(T[0-9]{3,}|[0-9a-f]{15})$``, so no production territory id is ever a
    valid 5-char FIPS. The fallback therefore had exactly two possible
    outcomes, both wrong: a pydantic ``ValidationError`` (``'T001'``, 4 chars),
    or a pseudo-county that misses every real-FIPS-keyed data source.

    The honest behaviour is Constitution III.11: absent county identity is an
    EMPTY DOMAIN. The county layer skips the node; it does not invent an
    identifier, and it does not crash.
    """

    def test_abstract_territory_yields_no_county_identity(self) -> None:
        """A T-labelled node with no county_fips contributes no FIPS at all."""
        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory")

        assert TickDynamicsSystem()._get_territory_fips(graph) == []

    def test_h3_territory_yields_no_county_identity(self) -> None:
        """A 15-char H3 territory id is not a county FIPS either."""
        graph = BabylonGraph()
        graph.add_node("85d9a4bfffffff", _node_type="territory")

        assert TickDynamicsSystem()._get_territory_fips(graph) == []

    def test_mixed_graph_keeps_only_real_county_identities(self) -> None:
        """Abstract nodes drop out; a stamped node still resolves to its FIPS."""
        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory")
        graph.add_node("T002", _node_type="territory", county_fips=WAYNE_FIPS)

        assert TickDynamicsSystem()._get_territory_fips(graph) == [WAYNE_FIPS]

    def test_bootstrap_skips_abstract_territory(self) -> None:
        """_bootstrap_county_states must not mint a state under a fake FIPS."""
        graph = BabylonGraph()
        graph.add_node(
            T_LABEL,
            _node_type="territory",
            tick_capital_stock=1.0e9,
        )

        states = TickDynamicsSystem()._bootstrap_county_states(graph, 2011)

        assert states == {}

    def test_year_boundary_step_does_not_crash_on_abstract_territories(self) -> None:
        """The regression-scenario shape: abstract territories, melt gate OPEN.

        This is the qa:regression crash reproduced at unit scale. With a
        melt_calculator present the annual pipeline executes, and the old
        fallback died in _compute_county_states with a ValidationError on
        ``fips='T001'``.
        """
        from tests.unit.economics.tick.test_system import _make_services

        graph = BabylonGraph()
        graph.add_node(T_LABEL, _node_type="territory")
        graph.add_node("T002", _node_type="territory")

        services = _make_services()
        context = TickContext(tick=0)

        # Must not raise. Absence is an empty domain, not a Loud Failure.
        TickDynamicsSystem().step(graph, services, context)
