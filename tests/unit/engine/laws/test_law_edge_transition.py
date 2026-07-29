"""Behavioral laws for EdgeTransitionSystem (P27 Phase-0 coverage backfill, Task 11).

Read end-to-end before writing: ``src/babylon/engine/systems/edge_transition/_legacy.py``
(``EdgeTransitionSystem.step``, lines 580-690; ``_evaluate_condition``/``_evaluate_predicate``,
lines 484-555; ``_co_optive_suppression``, lines 693-741; ``_handle_co_optive_breakdowns``,
lines 744-794), plus the transition table builder ``_build_transitions`` (lines 92-447) and
the module-level globals it produces (``_TRANSITIONS``/``_TRANSITION_MAP``/``_VALID_TRANSITIONS``,
lines 450-462). Thresholds come from ``GameDefines().edge_transition``
(``config/defines/consciousness.py:334-``) and ``GameDefines().contradiction_field``
(``config/defines/consciousness.py:272-``).

Laws pinned (each traces to a specific source range -- see per-test docstrings):

  L1 -- state-machine closure: for ANY starting ``EdgeMode`` and ANY node field
        values, after one ``step()`` the edge is either UNCHANGED or its
        ``(old_mode, new_mode)`` pair is a member of ``_VALID_TRANSITIONS``
        (``_legacy.py:458-462``). This holds structurally because the system
        only ever consults ``_TRANSITION_MAP.get(current_mode, [])``
        (``_legacy.py:644``) -- transitions whose ``from_mode`` differs from
        the edge's current mode are never even candidates, so no transition
        the system fires can produce an invalid pair.
  L2 -- max-priority selection: when multiple transitions out of the same
        mode are simultaneously eligible, the system always takes the one
        with the (strictly) highest ``priority``
        (``_legacy.py:652-655``'s ``max(fired, key=lambda t: t.priority)``).
        Proven concretely against the SHIPPED DEFAULT TRANSACTIONAL-exit
        table: ``market_failure`` (priority 10, -> ANTAGONISTIC),
        ``power_asymmetry_emerges`` (priority 7, -> EXTRACTIVE) and
        ``co_optive_power`` (priority 6, -> CO_OPTIVE) test independent
        fields (source immiseration df/dt, source exploitation value,
        target imperial_rent value respectively -- ``consciousness.py:374-391``),
        so all three can be made true at once without contradiction; the
        system must then always resolve to ANTAGONISTIC.
  L3 -- CO-OPTIVE suppression accumulator is monotone non-decreasing and
        never negative (``_legacy.py:736-741``): ``suppressed = df_dt * rate``
        is only ever ADDED (never subtracted) to ``node_latent[field]``, and
        only when ``df_dt is not None and df_dt > 0`` (line 739) -- a
        non-positive df/dt leaves the accumulator untouched, never lowers it.
  L4 -- latent release amplifies, never shrinks, and clears the accumulator:
        ``_handle_co_optive_breakdowns`` (``_legacy.py:763,766,784-793``)
        multiplies every released field by ``latent_release_multiplier``,
        which is schema-constrained ``ge=1.0`` (``consciousness.py:319-324``),
        so ``released >= accumulated`` always; and ``latent.pop(source_id, {})``
        (line 766) unconditionally removes the node's entry from the mutable
        accumulator before the events are published.

Caveat (NOT a law, a testing constraint): the 17-transition table's
thresholds are read from ``GameDefines().edge_transition`` exactly ONCE, at
module import time, via ``_build_transitions()`` (``_legacy.py:92-96,450``).
Unlike a system that reads ``services.defines`` fresh every tick, these tests
cannot inject custom threshold coefficients per-example the way
``test_law_substrate.py`` does for ``SubstrateDefines`` -- L1/L2 are proven
against the SHIPPED DEFAULT thresholds only. (``co_optive_suppression_rate``
and ``latent_release_multiplier`` in L3/L4 ARE read live from
``services.defines`` every call, so those two laws hold for any coefficient
in their declared schema range, not just the shipped default.)
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.edge_transition import EdgeTransitionSystem
from babylon.engine.systems.edge_transition._legacy import (
    _VALID_TRANSITIONS,
    _co_optive_suppression,
    _handle_co_optive_breakdowns,
)
from babylon.models.enums import ContradictionCharacter, EdgeMode, EdgeType, EventType, NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_FLOAT = st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False)


def _make_edge(
    graph: BabylonGraph,
    mode: EdgeMode,
    *,
    src_exploitation: float = 0.0,
    src_exploitation_dfdt: float = 0.0,
    src_immiseration: float = 0.0,
    src_immiseration_dfdt: float = 0.0,
    tgt_exploitation: float = 0.0,
    tgt_exploitation_dfdt: float = 0.0,
    tgt_imperial_rent: float = 0.0,
    src_wealth: float = 10.0,
    tgt_wealth: float = 10.0,
) -> None:
    """Build a real 2-node/1-edge graph via BabylonGraph's own API.

    Uses ``NodeType.SOCIAL_CLASS`` (never a hand-stamped string) and the real
    ``contradiction_fields``/``field_derivatives`` node-attribute shape that
    ``_evaluate_condition`` reads (``_legacy.py:503-521``).
    """
    graph.add_node(
        "SRC",
        _node_type=NodeType.SOCIAL_CLASS,
        wealth=src_wealth,
        contradiction_fields={
            "exploitation": src_exploitation,
            "immiseration": src_immiseration,
        },
        field_derivatives={
            "exploitation": {"laplacian": 0.0, "df_dt": src_exploitation_dfdt, "d2f_dt2": None},
            "immiseration": {"laplacian": 0.0, "df_dt": src_immiseration_dfdt, "d2f_dt2": None},
        },
    )
    graph.add_node(
        "TGT",
        _node_type=NodeType.SOCIAL_CLASS,
        wealth=tgt_wealth,
        contradiction_fields={
            "exploitation": tgt_exploitation,
            "imperial_rent": tgt_imperial_rent,
        },
        field_derivatives={
            "exploitation": {"laplacian": 0.0, "df_dt": tgt_exploitation_dfdt, "d2f_dt2": None},
        },
    )
    graph.add_edge(
        "SRC",
        "TGT",
        edge_type=EdgeType.EXPLOITATION,
        edge_mode=mode,
        contradiction_character=ContradictionCharacter.NON_ANTAGONISTIC,
    )


def _co_optive_edge(graph: BabylonGraph, *, src_dfdt: float) -> None:
    """A CO_OPTIVE edge suppressing 'exploitation', for direct
    ``_co_optive_suppression`` calls (L3)."""
    graph.add_node(
        "SRC",
        _node_type=NodeType.SOCIAL_CLASS,
        wealth=5.0,
        field_derivatives={"exploitation": {"laplacian": 0.0, "df_dt": src_dfdt, "d2f_dt2": None}},
    )
    graph.add_node("TGT", _node_type=NodeType.SOCIAL_CLASS, wealth=5.0)
    graph.add_edge(
        "SRC",
        "TGT",
        edge_type=EdgeType.EXPLOITATION,
        edge_mode=EdgeMode.CO_OPTIVE,
        co_optive_suppressed_fields=["exploitation"],
    )


class TestValidTransitionClosureLaw:
    """L1: after one ``step()``, the edge is either unchanged or its
    ``(old_mode, new_mode)`` pair is in ``_VALID_TRANSITIONS`` --
    structurally guaranteed because the system only ever looks up
    candidates via ``_TRANSITION_MAP.get(current_mode, [])`` (``_legacy.py:644``)."""

    @given(
        mode=st.sampled_from(list(EdgeMode)),
        src_exploitation=_FLOAT,
        src_exploitation_dfdt=_FLOAT,
        src_immiseration=_FLOAT,
        src_immiseration_dfdt=_FLOAT,
        tgt_exploitation=_FLOAT,
        tgt_imperial_rent=_FLOAT,
        src_wealth=_FLOAT,
        tgt_wealth=_FLOAT,
    )
    @settings(max_examples=25, deadline=None)
    def test_transition_pair_always_valid_or_unchanged(
        self,
        mode: EdgeMode,
        src_exploitation: float,
        src_exploitation_dfdt: float,
        src_immiseration: float,
        src_immiseration_dfdt: float,
        tgt_exploitation: float,
        tgt_imperial_rent: float,
        src_wealth: float,
        tgt_wealth: float,
    ) -> None:
        graph = BabylonGraph()
        _make_edge(
            graph,
            mode,
            src_exploitation=src_exploitation,
            src_exploitation_dfdt=src_exploitation_dfdt,
            src_immiseration=src_immiseration,
            src_immiseration_dfdt=src_immiseration_dfdt,
            tgt_exploitation=tgt_exploitation,
            tgt_imperial_rent=tgt_imperial_rent,
            src_wealth=src_wealth,
            tgt_wealth=tgt_wealth,
        )
        services = ServiceContainer.create()
        context = TickContext(tick=1, persistent_data={})

        EdgeTransitionSystem().step(graph, services, context)

        new_mode = EdgeMode(graph.edges["SRC", "TGT"]["edge_mode"])
        assert new_mode == mode or (mode, new_mode) in _VALID_TRANSITIONS


class TestMaxPrioritySelectionLaw:
    """L2: with multiple simultaneously-eligible TRANSACTIONAL-exit
    transitions, the system always takes the strictly-highest-priority one
    (``_legacy.py:652-655``). Proven against the shipped default thresholds:
    ``market_failure`` (priority 10) beats ``power_asymmetry_emerges``
    (priority 7) and ``co_optive_power`` (priority 6) whenever all three
    fire together -- possible because each reads a distinct field
    (``consciousness.py:374-391``)."""

    @given(
        exploitation_margin=st.floats(min_value=0.01, max_value=50.0, allow_nan=False),
        dfdt_margin=st.floats(min_value=0.01, max_value=50.0, allow_nan=False),
        rent_margin=st.floats(min_value=0.01, max_value=50.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_market_failure_wins_over_lower_priority_rivals(
        self,
        exploitation_margin: float,
        dfdt_margin: float,
        rent_margin: float,
    ) -> None:
        et = GameDefines().edge_transition
        src_exploitation = et.power_asymmetry_threshold + exploitation_margin
        src_immiseration_dfdt = et.market_failure_threshold + dfdt_margin
        tgt_imperial_rent = et.co_optive_power_threshold + rent_margin

        graph = BabylonGraph()
        _make_edge(
            graph,
            EdgeMode.TRANSACTIONAL,
            src_exploitation=src_exploitation,
            src_immiseration_dfdt=src_immiseration_dfdt,
            tgt_imperial_rent=tgt_imperial_rent,
        )
        services = ServiceContainer.create()
        context = TickContext(tick=1, persistent_data={})

        EdgeTransitionSystem().step(graph, services, context)

        assert graph.edges["SRC", "TGT"]["edge_mode"] == EdgeMode.ANTAGONISTIC


class TestCoOptiveSuppressionMonotoneLaw:
    """L3: the latent-contradiction accumulator only ever grows or holds
    steady across successive ``_co_optive_suppression`` calls, and never
    goes negative -- ``suppressed = df_dt * rate`` is added ONLY when
    ``df_dt is not None and df_dt > 0`` (``_legacy.py:739-741``); a
    non-positive df/dt is a complete no-op for that field that tick."""

    @given(dfdt1=_FLOAT, dfdt2=_FLOAT)
    @settings(max_examples=25, deadline=None)
    def test_accumulator_never_decreases_and_never_negative(
        self, dfdt1: float, dfdt2: float
    ) -> None:
        services = ServiceContainer.create()
        rate = services.defines.contradiction_field.co_optive_suppression_rate
        latent: dict[str, dict[str, float]] = {}

        graph1 = BabylonGraph()
        _co_optive_edge(graph1, src_dfdt=dfdt1)
        _co_optive_suppression(graph1, latent, services)
        after_first = latent.get("SRC", {}).get("exploitation", 0.0)

        assert after_first >= 0.0
        if dfdt1 > 0:
            assert after_first == pytest.approx(dfdt1 * rate)
        else:
            assert after_first == 0.0

        graph2 = BabylonGraph()
        _co_optive_edge(graph2, src_dfdt=dfdt2)
        _co_optive_suppression(graph2, latent, services)
        after_second = latent.get("SRC", {}).get("exploitation", 0.0)

        assert after_second >= after_first - 1e-9  # monotone non-decrease
        if dfdt2 > 0:
            assert after_second == pytest.approx(after_first + dfdt2 * rate)
        else:
            assert after_second == pytest.approx(after_first)


class TestLatentReleaseAmplificationLaw:
    """L4: on CO-OPTIVE breakdown, the released amount is always >= the
    accumulated latent value (``latent_release_multiplier`` is schema
    ``ge=1.0``, ``consciousness.py:319-324``), and the source node's entry
    is unconditionally cleared from the accumulator
    (``_legacy.py:766``'s ``latent.pop(source_id, {})``)."""

    @given(latent_value=st.floats(min_value=0.01, max_value=1_000.0, allow_nan=False))
    @settings(max_examples=25, deadline=None)
    def test_release_amplifies_and_clears_accumulator(self, latent_value: float) -> None:
        services = ServiceContainer.create()
        multiplier = services.defines.contradiction_field.latent_release_multiplier
        latent: dict[str, dict[str, float]] = {"SRC": {"exploitation": latent_value}}
        graph = BabylonGraph()  # unused by the function (param reserved for future writes)

        _handle_co_optive_breakdowns(
            graph, [("SRC", "TGT", str(EdgeType.EXPLOITATION))], latent, services, tick=1
        )

        assert "SRC" not in latent

        events = services.event_bus.get_history()
        release_events = [e for e in events if e.type == EventType.LATENT_CONTRADICTION_RELEASE]
        assert len(release_events) == 1
        released = release_events[0].payload["released_fields"]["exploitation"]
        assert released == pytest.approx(latent_value * multiplier)
        assert released >= latent_value - 1e-9
