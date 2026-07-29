"""Behavioral laws for SolidaritySystem (P27 Phase-0 coverage backfill, Task 11).

Read end-to-end before writing: ``src/babylon/engine/systems/solidarity.py``
(``SolidaritySystem.step``, lines 97-202 -- the dead-node skip at 127-130, the
``solidarity_strength <= 0`` Fascist-Bifurcation skip at 133-136, the
activation-threshold skip at 142-144, the negligible-delta skip at 160-161,
and the clamp + write at 163-169), plus the formula it calls,
``src/babylon/formulas/solidarity.py::calculate_solidarity_transmission``
(lines 10-36: ``delta = solidarity_strength * (source - target)`` when
active, else ``0.0``), and the accessor
``src/babylon/kernel/node_access.py::class_consciousness_from_node``
(lines 15-37: reads ``ideology["class_consciousness"]``, defaulting to
``0.0`` when ``ideology`` is missing or not a dict).

Laws pinned (each traces to a specific source range -- see per-test
docstrings for file:line grounding):

  L1 -- clamp: post-step target ``class_consciousness`` always lands in
        ``[0.0, 1.0]``, for ANY source/target consciousness in ``[0, 1]``
        and ANY (even wildly overshooting) ``solidarity_strength``
        (``solidarity.py:164-165``'s
        ``max(0.0, min(1.0, target_consciousness + delta))``).
  L2 -- directional convergence, never overshoot: when transmission
        activates (source above the activation threshold, strength in
        ``(0, 1]``), the post-step target consciousness lies strictly
        between the pre-step target and the source (or equals one of
        them) -- it moves TOWARD the source and never past it. Follows
        algebraically from ``formulas/solidarity.py:36``'s
        ``delta = strength * (source - target)``: the pre-clamp result is
        ``(1 - strength) * target + strength * source``, a convex
        combination of ``target`` and ``source`` for ``strength`` in
        ``[0, 1]``.
  L3 -- inactivity below the activation threshold: if
        ``source_consciousness <= activation_threshold``, the target's
        ``class_consciousness`` is byte-for-byte unchanged and no
        ``CONSCIOUSNESS_TRANSMISSION`` event is published
        (``solidarity.py:142-144``'s ``continue`` fires before any read of
        the target, matching the guard duplicated in
        ``formulas/solidarity.py:33-34``).
  L4 -- inactivity on dead nodes / zero infrastructure: if the source
        node, the target node, or ``solidarity_strength`` is inert
        (``active=False`` on either endpoint, or
        ``solidarity_strength <= 0``), the target's ``class_consciousness``
        is unchanged (``solidarity.py:127-130`` for dead nodes,
        ``:135-136`` for the Fascist-Bifurcation zero-strength case --
        "no infrastructure, no transmission" even with a fully
        revolutionary source).

Caveat (NOT a law): this is a diffusion/transmission process, not a
transfer -- the SOURCE's own ``class_consciousness`` is never read back
and never mutated by this system (only ``edge.target_id`` is written,
``solidarity.py:169``), so there is no system-wide "total consciousness is
conserved" law here the way a wealth-TRANSFER system would have one.
Multiple inbound SOLIDARITY edges to the same target are also folded in
SEQUENTIALLY within one tick (each edge's write is visible to the next
edge processed, per the existing
``TestSolidaritySystemEdgeCases::test_multiple_solidarity_edges`` unit
test) -- order-dependent, not a simultaneous/summed update -- so this
suite does not assert an edge-count-invariant closed form for the
multi-source case, only the single-edge laws above.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from babylon.config.defines import GameDefines, SolidarityDefines
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.solidarity import SolidaritySystem
from babylon.formulas.solidarity import calculate_solidarity_transmission
from babylon.models.enums import EdgeType, EventType, NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit


def _services(solidarity: SolidarityDefines | None = None) -> ServiceContainer:
    defines = GameDefines().model_copy(update={"solidarity": solidarity or SolidarityDefines()})
    return ServiceContainer.create(defines=defines)


def _worker(
    graph: BabylonGraph,
    node_id: str,
    *,
    class_consciousness: float,
    active: bool = True,
) -> None:
    graph.add_node(
        node_id,
        _node_type=NodeType.SOCIAL_CLASS,
        ideology={
            "class_consciousness": class_consciousness,
            "national_identity": 0.5,
            "agitation": 0.0,
        },
        active=active,
    )


def _solidarity_edge(
    graph: BabylonGraph, source: str, target: str, *, solidarity_strength: float
) -> None:
    graph.add_edge(
        source,
        target,
        edge_type=EdgeType.SOLIDARITY,
        solidarity_strength=solidarity_strength,
    )


def _target_consciousness(graph: BabylonGraph, node_id: str) -> float:
    return float(graph.nodes[node_id]["ideology"]["class_consciousness"])


class TestClampLaw:
    """L1: for ANY consciousness levels and ANY (even overshooting)
    ``solidarity_strength``, the post-step target ``class_consciousness``
    always lands in ``[0.0, 1.0]`` -- ``solidarity.py:164-165`` routes every
    write through ``max(0.0, min(1.0, ...))`` regardless of the computed
    delta's sign or magnitude."""

    @given(
        source_consciousness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        target_consciousness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        solidarity_strength=st.floats(min_value=0.0, max_value=10.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_target_consciousness_always_lands_in_bounds(
        self,
        source_consciousness: float,
        target_consciousness: float,
        solidarity_strength: float,
    ) -> None:
        graph = BabylonGraph()
        _worker(graph, "P_w", class_consciousness=source_consciousness)
        _worker(graph, "C_w", class_consciousness=target_consciousness)
        _solidarity_edge(graph, "P_w", "C_w", solidarity_strength=solidarity_strength)

        # Zero activation threshold so the strategy space always activates --
        # this law must hold regardless of whether transmission fires.
        services = _services(SolidarityDefines(activation_threshold=0.0))
        SolidaritySystem().step(graph, services, TickContext(tick=1))

        new_consciousness = _target_consciousness(graph, "C_w")
        assert 0.0 <= new_consciousness <= 1.0


class TestDirectionalConvergenceLaw:
    """L2: when transmission activates with ``solidarity_strength`` in
    ``(0, 1]``, the target moves TOWARD the source and never past it --
    ``formulas/solidarity.py:36``'s
    ``delta = strength * (source - target)`` makes the pre-clamp result
    ``(1 - strength) * target + strength * source``, a convex combination
    of the two, so the post-step value must lie in
    ``[min(source, target), max(source, target)]``."""

    @given(
        source_consciousness=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False),
        target_consciousness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        solidarity_strength=st.floats(
            min_value=1e-6, max_value=1.0, allow_nan=False, exclude_min=False
        ),
    )
    @settings(max_examples=25, deadline=None)
    def test_target_moves_toward_source_never_past_it(
        self,
        source_consciousness: float,
        target_consciousness: float,
        solidarity_strength: float,
    ) -> None:
        # Zero activation threshold guarantees this strategy space activates
        # (source_consciousness > 0.0 always, per min_value=1e-6).
        activation_threshold = 0.0
        delta = calculate_solidarity_transmission(
            source_consciousness=source_consciousness,
            target_consciousness=target_consciousness,
            solidarity_strength=solidarity_strength,
            activation_threshold=activation_threshold,
        )
        # Skip cases the system itself would treat as noise
        # (solidarity.py:160-161 -- matches the SHIPPED default 0.01).
        assume(abs(delta) >= 0.01)

        graph = BabylonGraph()
        _worker(graph, "P_w", class_consciousness=source_consciousness)
        _worker(graph, "C_w", class_consciousness=target_consciousness)
        _solidarity_edge(graph, "P_w", "C_w", solidarity_strength=solidarity_strength)

        services = _services(SolidarityDefines(activation_threshold=activation_threshold))
        SolidaritySystem().step(graph, services, TickContext(tick=1))

        new_consciousness = _target_consciousness(graph, "C_w")
        lo, hi = sorted((source_consciousness, target_consciousness))
        assert lo - 1e-9 <= new_consciousness <= hi + 1e-9


class TestActivationThresholdInactivityLaw:
    """L3: if ``source_consciousness <= activation_threshold``, the
    target's ``class_consciousness`` is byte-for-byte unchanged and no
    ``CONSCIOUSNESS_TRANSMISSION`` event fires -- ``solidarity.py:142-144``'s
    ``continue`` fires before any read/write of the target, mirroring the
    guard duplicated in ``formulas/solidarity.py:33-34``."""

    @given(
        source_consciousness=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
        target_consciousness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        solidarity_strength=st.floats(min_value=1e-6, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_no_change_when_source_at_or_below_threshold(
        self,
        source_consciousness: float,
        target_consciousness: float,
        solidarity_strength: float,
    ) -> None:
        graph = BabylonGraph()
        _worker(graph, "P_w", class_consciousness=source_consciousness)
        _worker(graph, "C_w", class_consciousness=target_consciousness)
        _solidarity_edge(graph, "P_w", "C_w", solidarity_strength=solidarity_strength)

        # Default activation_threshold=0.3 (SolidarityDefines); the strategy
        # space is drawn <= 0.3 so the guard always fires.
        services = _services(SolidarityDefines(activation_threshold=0.3))
        context = TickContext(tick=1)
        SolidaritySystem().step(graph, services, context)

        assert _target_consciousness(graph, "C_w") == pytest.approx(target_consciousness)
        transmission_events = [
            e
            for e in services.event_bus.get_history()
            if e.type == EventType.CONSCIOUSNESS_TRANSMISSION
        ]
        assert transmission_events == []


class TestInertInfrastructureLaw:
    """L4: a dead endpoint or zero ``solidarity_strength`` fully inhibits
    transmission, even with a maximally revolutionary source --
    ``solidarity.py:127-130`` (dead-node skip) and ``:135-136`` (the
    Fascist-Bifurcation "no infrastructure, no transmission" case)."""

    def test_dead_source_node_blocks_transmission(self) -> None:
        graph = BabylonGraph()
        _worker(graph, "P_w", class_consciousness=0.95, active=False)
        _worker(graph, "C_w", class_consciousness=0.1)
        _solidarity_edge(graph, "P_w", "C_w", solidarity_strength=0.9)

        services = _services()
        SolidaritySystem().step(graph, services, TickContext(tick=1))

        assert _target_consciousness(graph, "C_w") == pytest.approx(0.1)

    def test_dead_target_node_blocks_transmission(self) -> None:
        graph = BabylonGraph()
        _worker(graph, "P_w", class_consciousness=0.95)
        _worker(graph, "C_w", class_consciousness=0.1, active=False)
        _solidarity_edge(graph, "P_w", "C_w", solidarity_strength=0.9)

        services = _services()
        SolidaritySystem().step(graph, services, TickContext(tick=1))

        assert _target_consciousness(graph, "C_w") == pytest.approx(0.1)

    @given(target_consciousness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=25, deadline=None)
    def test_zero_solidarity_strength_blocks_transmission(
        self, target_consciousness: float
    ) -> None:
        graph = BabylonGraph()
        _worker(graph, "P_w", class_consciousness=1.0)
        _worker(graph, "C_w", class_consciousness=target_consciousness)
        _solidarity_edge(graph, "P_w", "C_w", solidarity_strength=0.0)

        services = _services()
        SolidaritySystem().step(graph, services, TickContext(tick=1))

        assert _target_consciousness(graph, "C_w") == pytest.approx(target_consciousness)
