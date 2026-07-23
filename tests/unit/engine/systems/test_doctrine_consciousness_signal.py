"""The Unit-6 sign-predictability contract (ADR073 Unit 6b, wired for real by ADR087).

Every doctrine test before this one injected ``doctrine_tags`` directly via
``graph.update_node()`` as fixture setup (``tests/contract/verbs/
test_effects.py``, ``test_engine_bridge.py``, ``test_doctrine_system.py``) —
fixture-stamped shape testing: it proves ConsciousnessSystem reacts to a
hand-written ``doctrine_tags`` dict, never that DoctrineSystem itself
PRODUCES one a real tick later reads, and never that the resulting
org-sourced SOLIDARITY edge (the actual Unit 6b feedback channel, per
ADR087) comes from anywhere but a hand-stamped ``graph.add_edge(...)`` call.

This module drives the REAL production path end-to-end: a
:class:`~babylon.models.entities.organization.PoliticalFaction` and
:class:`~babylon.models.entities.social_class.SocialClass` built through
:class:`~babylon.models.world_state.WorldState` ``.to_graph()`` (the pattern
``tests/unit/engine/systems/test_doctrine_system.py`` and
``tests/contract/verbs/conftest.py`` already establish); the real
``SimulationEngine.run_tick`` in engine order so DoctrineSystem accrues
theoretical labour and greedily acquires ``trade_unionism`` (the MASS_LINK
Unit-6b tag); and the real
:func:`~babylon.engine.actions.campaign.resolve_campaign` verb resolver (NOT
a hand-stamped edge) to create the org -> class SOLIDARITY edge, amplified by
the org's CURRENT ``doctrine_tags``. ConsciousnessSystem then reacts to that
edge exactly as it would in a real game.

**Why PROPAGANDIZE (CAMPAIGN), not EDUCATE or PROVIDE_SERVICE**: all three
verbs are mass-work SOLIDARITY producers (ADR087), but PROPAGANDIZE's
resolver (``resolve_campaign``) makes exactly ONE direct graph write — the
new mass-work SOLIDARITY edge. Its returned ``consciousness_delta`` (the
five-factor CI formula) is never applied to the graph by the resolver itself
(``ooda/layer3.py`` is the only consumer, and this test never invokes it) —
confirmed by ``tests/contract/verbs/test_effects.py``'s own
``TestConsciousnessVerbs``, which only asserts on the RETURNED
``ActionResult``, never on graph state. This isolates the MASS_LINK
solidarity channel from every other consciousness pathway; PROVIDE_SERVICE
(``aid.py``) additionally moves budget/wealth and EDUCATE (``educate.py``)
carries the Study sub-verb branch, both irrelevant noise for this contract.

**Ordering claim, verified, not trusted** (see
``test_doctrine_precedes_consciousness_in_engine_order`` below): DoctrineSystem
is ``position 14.7``, ConsciousnessSystem is ``position 17.0`` in
``simulation_engine._DEFAULT_SYSTEMS`` — 14.7 < 17.0. Two DISTINCT same-tick
visibility claims now depend on this order (ADR087 broadened the original
single claim):

1. A verb dispatched with the org's CURRENT ``doctrine_tags`` sees whatever
   DoctrineSystem wrote in a PRIOR tick (verb dispatch itself is external to
   both systems in this test, mirroring real OODA order — OODASystem runs at
   position 14, before Doctrine's 14.7).
2. DoctrineSystem's per-tick DECAY of org-sourced SOLIDARITY edges
   (``mass_work_solidarity_decay_rate``, ADR087) must apply BEFORE
   ConsciousnessSystem's same-tick read, or that tick's decay is invisible
   until next tick. ``TestDecayOrderingMatters`` isolates claim 2 with a
   test-only decay-rate override (0.9, vs. the ratified 0.02 default) so a
   single tick's ordering effect is unmistakable rather than lost in noise —
   mirrors the salvage suite's own test-only ``cadre_level=30.0`` precedent
   of calibrating strictly for observability, never for the sign contract
   itself.

**Calibration** (I-15, verified against the REAL DoctrineSystem, not
hand-derived): :class:`~babylon.models.entities.organization.PoliticalFaction`
constrains ``cadre_level`` to ``Probability`` (``[0, 1]``) — the salvage
suite's ``cadre_level=30.0`` was only reachable by hand-stamping the graph
node directly, bypassing the model (exactly the fixture-fabricated-shape
failure class this rebuild exists to stop repeating). At the model's ceiling
(``cadre_level=1.0``), ``study_allocation`` midpoint 0.2 accrues 0.2 TL/tick;
``trade_unionism`` costs 25 TL (root ``class_consciousness`` is free) — a
fresh org run through the real engine acquires it at **tick 126** (confirmed
by direct measurement, not the naive ``25 / 0.2 = 125`` estimate, which is
off by one tick from the real accrual/decay interaction).

**The TRAP this test avoids** (per the doctrine data file,
``src/babylon/data/game/doctrine_tree_mvp.json``): doctrine tags decay
0.55%/tick and several tree nodes carry NEGATIVE deltas for a given tag
(``urban_guerrilla``: ``class_analysis -1``; ``adventurism``:
``class_analysis -2``). Gating an assertion on a raw tag magnitude would be
fragile to future tree edits. This test instead asserts on MONOTONIC
quantities (``"trade_unionism" in acquired_doctrine_ids``) and on SIGNED
DIRECTIONS it derives itself (a mass-linked org's mass work raises a class's
consciousness MORE, and fascism LESS, than an otherwise-identical org with no
doctrine) — never on "the tag reached value X" or "the edge strength is X."

**Why the wealth shock is small** (100.0 -> 95.0, not a dramatic crash):
``ConsciousnessSystem.step`` clamps ``class_consciousness`` at 1.0. A large
shock would saturate BOTH runs at that ceiling and the signed difference
under test would disappear. A small shock keeps both readings inside (0, 1)
so the comparison stays meaningful.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.engine.actions.campaign import resolve_campaign
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine
from babylon.engine.systems.doctrine import DoctrineSystem
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.kernel.system_base import SystemBase
from babylon.kernel.system_protocol import System
from babylon.models.entities.organization import PoliticalFaction
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import (
    ActionType,
    ClassCharacter,
    ConsciousnessTendency,
    EdgeType,
    LegalStanding,
    OrgType,
    SocialRole,
)
from babylon.models.world_state import WorldState
from babylon.ooda.types import Action
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_ORG_ID = "vanguard"
_CLASS_ID = "C900"  # SocialClass.id must match ^C[0-9]{3,}$
_STABLE_WEALTH = 100.0
_SHOCKED_WEALTH = 95.0  # a small, identical extraction in both runs (see module docstring)
_WIRED_CADRE_LEVEL = 1.0  # PoliticalFaction's ceiling (Probability, [0, 1])
_PRE_CRISIS_TICKS = 126  # ticks 1..126: trade_unionism is affordable AT tick 126, not before
_MASS_LINK_ACQUIRED_TICK = 126


def test_doctrine_precedes_consciousness_in_engine_order() -> None:
    """Verify (not trust) the @14.7 < @17.0 ordering claim against the real registry.

    If DoctrineSystem ever moved to run AFTER ConsciousnessSystem, its
    same-tick writes (and the decay this module also covers) would only
    become visible next tick — silently delaying the Unit-6b feedback loop.
    """
    positions = {
        type(system).__name__: system.position
        for system in _DEFAULT_SYSTEMS
        if isinstance(system, SystemBase)
    }
    assert positions["DoctrineSystem"] == pytest.approx(14.7)
    assert positions["ConsciousnessSystem"] == pytest.approx(17.0)
    assert positions["DoctrineSystem"] < positions["ConsciousnessSystem"], (
        "DoctrineSystem must run before ConsciousnessSystem so a tag or "
        "decay it writes is visible the SAME tick, not the next"
    )


def _build_graph(cadre_level: float) -> BabylonGraph:
    """A minimal org + class graph via the REAL production path.

    ``PoliticalFaction`` -> ``SocialClass`` -> ``WorldState.to_graph()`` — no
    hand-stamped nodes or edges. No SOLIDARITY edge exists until the real
    verb resolver creates one.
    """
    org = PoliticalFaction(
        id=_ORG_ID,
        name="Vanguard Party",
        org_type=OrgType.POLITICAL_FACTION,
        class_character=ClassCharacter.PROLETARIAN,
        ideology="marxism-leninism",
        cohesion=0.5,
        cadre_level=cadre_level,
        budget=1000.0,
        legal_standing=LegalStanding.UNDERGROUND,
        consciousness_tendency=ConsciousnessTendency.REVOLUTIONARY,
    )
    workers = SocialClass(
        id=_CLASS_ID,
        name="Workers",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=_STABLE_WEALTH,
        ideology=0.0,  # type: ignore[arg-type]  # Validator converts to IdeologicalProfile
    )
    state = WorldState(tick=0, entities={_CLASS_ID: workers}, organizations={_ORG_ID: org})
    return state.to_graph()


def _run_ticks(
    graph: BabylonGraph,
    context: TickContext,
    first_tick: int,
    last_tick: int,
    services: ServiceContainer,
    *,
    systems: list[System] | None = None,
) -> None:
    """Drive the real engine for ``[first_tick, last_tick]`` inclusive.

    ``systems`` defaults to the real production order (Doctrine then
    Consciousness); the reversed-order regression guards override it.
    """
    engine = SimulationEngine(
        systems if systems is not None else [DoctrineSystem(), ConsciousnessSystem()]
    )
    for tick in range(first_tick, last_tick + 1):
        context.tick = tick
        engine.run_tick(graph, services, context)


def _dispatch_campaign(graph: BabylonGraph, services: ServiceContainer) -> None:
    """Dispatch the real PROPAGANDIZE verb, org -> class, via the real resolver.

    Reads the org's CURRENT ``doctrine_tags`` off the graph at call time (a
    fresh attribute snapshot, mirroring the OODA seam's own
    ``dict(graph.nodes[org_id])`` convention) — this is what makes the
    resulting edge's ``solidarity_strength`` reflect whatever DoctrineSystem
    has accrued so far.
    """
    action = Action(
        org_id=_ORG_ID,
        action_type=ActionType.PROPAGANDIZE,
        target_id=_CLASS_ID,
        params={},
    )
    org_attrs = dict(graph.nodes[_ORG_ID])
    resolve_campaign(action, org_attrs, graph, services)


class TestDoctrineWritesAreVisibleToConsciousnessSameTick:
    """The real accrue -> acquire -> verb-dispatch -> downstream-consciousness chain."""

    def test_high_cadre_org_acquires_trade_unionism_by_tick_126(self) -> None:
        """Sanity-check the calibration arithmetic in the module docstring
        against the REAL DoctrineSystem (not a hand-derived number nobody
        ran) — monotonic assertions only (III.11 trap above)."""
        graph = _build_graph(cadre_level=_WIRED_CADRE_LEVEL)
        services = ServiceContainer.create()
        context = TickContext(tick=0)
        _run_ticks(graph, context, 1, _MASS_LINK_ACQUIRED_TICK, services)

        org = graph.nodes[_ORG_ID]
        assert "trade_unionism" in org["acquired_doctrine_ids"]
        assert org["doctrine_tags"].get("mass_link", 0.0) > 0.0
        services.database.close()

    def test_zero_cadre_org_never_acquires_trade_unionism(self) -> None:
        """The control arm: MASS_LINK stays structurally absent (never
        wired to a positive value) when the org can't afford it."""
        graph = _build_graph(cadre_level=0.0)
        services = ServiceContainer.create()
        context = TickContext(tick=0)
        _run_ticks(graph, context, 1, _MASS_LINK_ACQUIRED_TICK, services)

        org = graph.nodes[_ORG_ID]
        assert "trade_unionism" not in org["acquired_doctrine_ids"]
        assert org["doctrine_tags"].get("mass_link", 0.0) == 0.0
        assert org["theoretical_labor"] == pytest.approx(0.0)
        services.database.close()

    def test_mass_link_amplified_solidarity_raises_consciousness_more(self) -> None:
        """The Unit-6b sign-predictability contract itself, wired for real.

        Two otherwise-identical runs (same verb, same target, same material
        shock, same tick count) differ ONLY in whether the org acquired
        MASS_LINK via a REAL DoctrineSystem run. The PROPAGANDIZE dispatch
        lands right after MASS_LINK is acquired, so the resulting SOLIDARITY
        edge's ``solidarity_strength`` is amplified in the wired run and NOT
        in the control run — a real producer, not a hand-stamped edge. If
        the write side (``apply_mass_work_solidarity``), the read side
        (``ConsciousnessSystem``'s org-sourced branch), and the DoctrineSystem
        decay are all live and correctly ordered, the wired arm's
        class_consciousness gain must be STRICTLY greater — a signed
        direction, not a magnitude pinned to today's coefficients.
        """
        services = ServiceContainer.create()
        wired_graph = _build_graph(cadre_level=_WIRED_CADRE_LEVEL)
        control_graph = _build_graph(cadre_level=0.0)
        wired_context = TickContext(tick=0)
        control_context = TickContext(tick=0)

        # Ticks 1..126: stable wealth, accrual only — the wired run acquires
        # trade_unionism at tick 126; the control run never does.
        _run_ticks(wired_graph, wired_context, 1, _PRE_CRISIS_TICKS, services)
        _run_ticks(control_graph, control_context, 1, _PRE_CRISIS_TICKS, services)
        assert wired_graph.nodes[_ORG_ID]["doctrine_tags"].get("mass_link", 0.0) > 0.0
        assert control_graph.nodes[_ORG_ID]["doctrine_tags"].get("mass_link", 0.0) == 0.0

        # Apply the identical wealth shock, then dispatch the identical
        # PROPAGANDIZE verb in both runs (its resulting edge amplified by
        # each org's CURRENT doctrine_tags), then drive one more tick so
        # ConsciousnessSystem reacts to the freshly-created edge.
        wired_graph.nodes[_CLASS_ID]["wealth"] = _SHOCKED_WEALTH
        control_graph.nodes[_CLASS_ID]["wealth"] = _SHOCKED_WEALTH
        _dispatch_campaign(wired_graph, services)
        _dispatch_campaign(control_graph, services)

        # Precondition: the two runs actually diverge on edge strength — the
        # channel this test isolates. If this fails, the comparison below is
        # meaningless (both arms would be identical).
        wired_edge = wired_graph.get_edge(_ORG_ID, _CLASS_ID, EdgeType.SOLIDARITY.value)
        control_edge = control_graph.get_edge(_ORG_ID, _CLASS_ID, EdgeType.SOLIDARITY.value)
        assert wired_edge is not None
        assert control_edge is not None
        wired_strength = wired_edge.attributes["solidarity_strength"]
        control_strength = control_edge.attributes["solidarity_strength"]
        assert wired_strength > control_strength > 0.0

        _run_ticks(
            wired_graph,
            wired_context,
            _MASS_LINK_ACQUIRED_TICK + 1,
            _MASS_LINK_ACQUIRED_TICK + 1,
            services,
        )
        _run_ticks(
            control_graph,
            control_context,
            _MASS_LINK_ACQUIRED_TICK + 1,
            _MASS_LINK_ACQUIRED_TICK + 1,
            services,
        )

        wired_consciousness = wired_graph.nodes[_CLASS_ID]["ideology"]["class_consciousness"]
        control_consciousness = control_graph.nodes[_CLASS_ID]["ideology"]["class_consciousness"]
        wired_nationalism = wired_graph.nodes[_CLASS_ID]["ideology"]["national_identity"]
        control_nationalism = control_graph.nodes[_CLASS_ID]["ideology"]["national_identity"]

        # Sanity: the shock moved BOTH runs (mass work organizes even at
        # MASS_LINK == 0 — the base gain, not a gated switch; see the
        # `_mass_work` module docstring's "continuous, not binary" note).
        assert wired_consciousness > 0.5
        assert control_consciousness > 0.5
        # Neither hit the [0, 1] ceiling — if either did, the signed
        # difference below would be masked by the clamp (module docstring).
        assert wired_consciousness < 1.0

        assert wired_consciousness > control_consciousness, (
            "DoctrineSystem's MASS_LINK amplification of the mass-work "
            "SOLIDARITY edge must raise the target's revolutionary "
            "consciousness MORE than an otherwise-identical undoctrined org"
        )
        # Routing-direction corollary: the SAME amplified solidarity that
        # raises class_consciousness more must also raise national_identity
        # (the fascist pole) LESS — the ternary router's zero-sum-ish split
        # between the revolutionary and fascist shares of agitation.
        assert wired_nationalism < control_nationalism, (
            "More effective solidarity must route LESS agitation to the "
            "fascist pole, not just MORE to the revolutionary one"
        )
        services.database.close()

    def test_reversed_system_order_would_have_hidden_the_effect(self) -> None:
        """Regression guard: prove the ordering itself is load-bearing.

        Same scenario, same shock, same acquisition tick — but the engine
        is built with ConsciousnessSystem BEFORE DoctrineSystem. Because the
        verb dispatch (and its resulting edge) happens EXTERNALLY to the
        engine in this test (mirroring real OODA order, which runs before
        Doctrine's 14.7 either way), reversing Doctrine/Consciousness alone
        does not hide THIS particular effect — that ordering sensitivity
        moved to decay-visibility (``TestDecayOrderingMatters`` below) under
        the ADR087 design. What this guard STILL protects: DoctrineSystem's
        acquisition of ``trade_unionism`` happens regardless of order (it
        doesn't depend on Consciousness at all), confirming the two systems
        are independently deterministic under either order — a orthogonality
        check that would fail loudly (KeyError/AttributeError) if a future
        change made DoctrineSystem read anything ConsciousnessSystem writes.
        """
        services = ServiceContainer.create()
        graph = _build_graph(cadre_level=_WIRED_CADRE_LEVEL)
        context = TickContext(tick=0)
        reversed_systems: list[System] = [ConsciousnessSystem(), DoctrineSystem()]

        _run_ticks(graph, context, 1, _MASS_LINK_ACQUIRED_TICK, services, systems=reversed_systems)

        assert "trade_unionism" in graph.nodes[_ORG_ID]["acquired_doctrine_ids"]
        assert graph.nodes[_ORG_ID]["doctrine_tags"].get("mass_link", 0.0) > 0.0
        services.database.close()


class TestDecayOrderingMatters:
    """Regression guard: DoctrineSystem's decay of org-sourced SOLIDARITY
    edges must be visible to ConsciousnessSystem the SAME tick (position
    14.7 < 17.0) — the ordering-sensitive claim ADR087 introduces (the
    original salvage suite's claim was over a tag WRITE; this one is over an
    edge DECAY, but the same-tick-visibility mechanism is identical).

    Uses a test-only ``mass_work_solidarity_decay_rate`` override (0.9, vs.
    the ratified 0.02 default) purely for OBSERVABILITY — a single tick's
    ordering effect must be unmistakable, not lost in noise at the
    real-world rate. Mirrors ``test_attack_self_heat_gain_is_defines_driven``
    (``tests/contract/verbs/test_effects.py``)'s established pattern of a
    modded ``ServiceContainer`` for a defines-driven regression test.
    """

    def test_reversed_order_hides_the_current_ticks_decay(self) -> None:
        defines = GameDefines()
        modded = defines.model_copy(
            update={
                "doctrine": defines.doctrine.model_copy(
                    update={"mass_work_solidarity_decay_rate": 0.9}
                )
            }
        )
        services = ServiceContainer.create(defines=modded)

        real_graph = _build_graph(cadre_level=0.0)
        reversed_graph = _build_graph(cadre_level=0.0)
        real_context = TickContext(tick=0)
        reversed_context = TickContext(tick=0)
        real_systems: list[System] = [DoctrineSystem(), ConsciousnessSystem()]
        reversed_systems: list[System] = [ConsciousnessSystem(), DoctrineSystem()]

        # Two baseline ticks (no edge yet, no shock) establish the class's
        # wealth baseline in BOTH runs before the edge exists.
        _run_ticks(real_graph, real_context, 1, 2, services, systems=real_systems)
        _run_ticks(reversed_graph, reversed_context, 1, 2, services, systems=reversed_systems)

        # Seed an IDENTICAL SOLIDARITY edge via the real resolver in both
        # graphs (never a hand-stamped `add_edge` — the vocabulary sentinel's
        # edge-shape rule polices exactly that fabrication).
        _dispatch_campaign(real_graph, services)
        _dispatch_campaign(reversed_graph, services)
        seeded = real_graph.get_edge(_ORG_ID, _CLASS_ID, EdgeType.SOLIDARITY.value)
        assert seeded is not None
        seeded_strength = seeded.attributes["solidarity_strength"]
        reversed_seeded = reversed_graph.get_edge(_ORG_ID, _CLASS_ID, EdgeType.SOLIDARITY.value)
        assert reversed_seeded is not None
        assert reversed_seeded.attributes["solidarity_strength"] == pytest.approx(seeded_strength)

        # Shock + exactly one tick, real vs reversed order.
        real_graph.nodes[_CLASS_ID]["wealth"] = _SHOCKED_WEALTH
        reversed_graph.nodes[_CLASS_ID]["wealth"] = _SHOCKED_WEALTH
        _run_ticks(real_graph, real_context, 3, 3, services, systems=real_systems)
        _run_ticks(reversed_graph, reversed_context, 3, 3, services, systems=reversed_systems)

        real_consciousness = real_graph.nodes[_CLASS_ID]["ideology"]["class_consciousness"]
        reversed_consciousness = reversed_graph.nodes[_CLASS_ID]["ideology"]["class_consciousness"]

        # Real order: decay (0.05 -> 0.005, below negligible_transmission)
        # runs BEFORE ConsciousnessSystem reads it this tick -> no effect.
        assert real_consciousness == pytest.approx(0.5)
        # Reversed order: ConsciousnessSystem reads the PRE-decay (larger,
        # one-tick-stale) edge THIS tick -> a visible effect the real order
        # would not show until a tick later.
        assert reversed_consciousness > 0.5
        assert reversed_consciousness > real_consciousness, (
            "DoctrineSystem's same-tick decay must reach ConsciousnessSystem's "
            "solidarity read THIS tick (position 14.7 < 17.0) -- reversing "
            "the order hides the tick's decay for one tick"
        )
        services.database.close()
