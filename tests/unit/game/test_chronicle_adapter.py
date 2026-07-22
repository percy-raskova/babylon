"""Unit tests for the bus->Chronicle adapter (Program v1.0.0, Unit T4-core/C4).

Pins the three properties the program plan asked for: :func:`summarize_event`
is a deterministic, pure function of ``(event_type, payload)``; an
``EventType`` with no bespoke builder still renders — loudly, never
dropped; and :func:`chronicle_events_from_bus` is a stateless per-call
mapping (no cumulative state leaks between two calls, mirroring
``WorldState.events``'s own per-tick-not-cumulative contract). No real
engine, Postgres, or ``WorldState`` is needed — plain
:class:`~babylon.kernel.event_bus.Event` fixtures only.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from babylon.engine import event_builders as _event_builders_module
from babylon.game import chronicle_adapter as _chronicle_adapter_module
from babylon.game.chronicle_adapter import (
    chronicle_events_from_bus,
    summarize_event,
)
from babylon.kernel.event_bus import Event
from babylon.models.enums.events import EventType
from babylon.models.enums.topology import EdgeType, NodeType
from babylon.topology import BabylonGraph

pytestmark = [pytest.mark.unit]


# --------------------------------------------------------------------------- #
# summarize_event: determinism + real per-EventType content.                  #
# --------------------------------------------------------------------------- #


def test_summarize_event_is_deterministic_over_repeated_calls() -> None:
    """The SAME ``(event_type, tick, payload)`` always renders the SAME text."""
    payload = {"source_id": "C001", "target_id": "C002", "amount": 12.5, "mechanism": "wage_gap"}
    first = summarize_event(EventType.SURPLUS_EXTRACTION, 3, payload)
    second = summarize_event(EventType.SURPLUS_EXTRACTION, 3, dict(payload))
    assert first == second
    assert first == "C001 yields 12.50 in surplus to C002 via wage_gap"


def test_summarize_event_reflects_real_payload_not_a_constant() -> None:
    """Different payloads for the SAME EventType render DIFFERENT summaries —
    a pure function of the payload, not a canned string."""
    low = summarize_event(EventType.UPRISING, 1, {"node_id": "T000", "agitation": 0.1})
    high = summarize_event(EventType.UPRISING, 1, {"node_id": "T000", "agitation": 0.9})
    assert low != high
    assert "0.10" in low
    assert "0.90" in high


def test_summarize_event_covers_every_family_without_crashing() -> None:
    """A representative event from each documented family renders without
    raising and without falling through to the generic form (real coverage,
    not just the economic core)."""
    covered_samples: tuple[tuple[EventType, dict[str, object]], ...] = (
        (EventType.DOCTRINE_TRAP_SPRUNG, {"org_id": "rev_workers", "node_id": "C001"}),
        (EventType.SOVEREIGN_COLLAPSE, {"sovereign_id": "sov1", "trigger": "legitimacy_zero"}),
        (EventType.FASCIST_DRIFT, {"node_id": "C004", "fascist_pull": 0.4}),
        (EventType.ORGANIZATIONAL_ACTION, {"org_count": 2, "action_count": 3, "layer0_count": 1}),
        (
            EventType.CALIBRATION_QCEW_CARRY_FORWARD,
            {"county_fips": "26163", "look_back_year": 2019},
        ),
    )
    for event_type, payload in covered_samples:  # loop bound: len(covered_samples)
        summary = summarize_event(event_type, 5, payload)
        assert summary
        # None of these render through the generic "(tick N) — fields:" shape.
        assert "— fields:" not in summary
        assert "— no payload recorded" not in summary


def test_summarize_event_handles_missing_optional_field_honestly() -> None:
    """A field ``EVENT_BUILDERS`` itself reads with no default (e.g.
    ``profit_rate``) renders as an honest ``"?"`` when absent, never a
    fabricated number (Constitution III.11)."""
    summary = summarize_event(
        EventType.CRISIS_PHASE_TRANSITION,
        7,
        {"fips": "26163", "previous_phase": "boom", "new_phase": "bust"},
    )
    assert "profit rate ?" in summary


def test_state_repression_bulletin_names_org_and_target_with_backfire() -> None:
    """Adversary-train W2: the STATE_REPRESSION/STATE_SURVEILLANCE bulletins
    (``chronicle_adapter.py``'s ``_SUMMARY_BUILDERS`` lambdas) are the
    player-facing "the state moves against X" line the BD asked for — a
    real, readable sentence naming the acting org, the target, and the CI
    backfire the state's own action risks, never a placeholder. Payload
    keys mirror exactly what ``OODASystem``'s first-class publish loop
    sends (``org_id``/``target_id`` + ``result.direct_effects``,
    ``engine/systems/ooda.py``) and what
    ``event_builders.EVENT_BUILDERS[EventType.STATE_REPRESSION]`` reads."""
    repress_summary = summarize_event(
        EventType.STATE_REPRESSION,
        3,
        {"org_id": "ORG002", "target_id": "ORG001", "backfire_delta": 0.05},
    )
    assert repress_summary == "ORG002 represses ORG001 (backfire Δ0.05)"

    surveil_summary = summarize_event(
        EventType.STATE_SURVEILLANCE,
        3,
        {"org_id": "ORG002", "target_id": "ORG001", "backfire_delta": 0.02},
    )
    assert surveil_summary == "ORG002 surveils ORG001 (backfire Δ0.02)"

    # Real payload, real difference — not a canned string (mirrors
    # test_summarize_event_reflects_real_payload_not_a_constant's discipline).
    other_target = summarize_event(
        EventType.STATE_REPRESSION,
        3,
        {"org_id": "ORG002", "target_id": "BIZ_WAYNE_1", "backfire_delta": 0.05},
    )
    assert other_target != repress_summary
    assert "BIZ_WAYNE_1" in other_target


def test_class_decomposition_uses_the_real_wire_key_not_the_pydantic_field_name() -> None:
    """Regression for a shipped silent-fabrication bug (Constitution III.11):
    the wire payload key the engine actually publishes is ``source_class``
    (``babylon.engine.systems.decomposition``'s
    ``"source_class": la_id`` publish site; corroborated by
    ``event_builders.EVENT_BUILDERS[EventType.CLASS_DECOMPOSITION]``'s own
    ``original_id=payload.get("source_class", "")``). ``original_id`` is
    only the PYDANTIC MODEL's field name post-adaptation, never a wire key —
    reading it off the raw payload always rendered a blank subject."""
    summary = summarize_event(
        EventType.CLASS_DECOMPOSITION,
        5,
        {
            "source_class": "C_labor_aristocracy",
            "enforcer_fraction": 0.3,
            "proletariat_fraction": 0.7,
        },
    )
    assert summary == "C_labor_aristocracy decomposes: 0.30 enforcers / 0.70 proletariat"


# --------------------------------------------------------------------------- #
# Baker-equivalence: every _SUMMARY_BUILDERS lambda is cross-checked, field   #
# by field, against babylon.engine.event_builders.EVENT_BUILDERS' own wire   #
# contract — not merely claimed in prose (this is what would have caught     #
# CLASS_DECOMPOSITION's `original_id`/`source_class` mismatch pre-fix).      #
# --------------------------------------------------------------------------- #


def _dict_literal_assigned_to(module: object, name: str) -> ast.Dict:
    """Parse ``module``'s source and return the ``ast.Dict`` literal bound to
    the module-level name ``name`` (e.g. ``"_BUILDERS"``).

    :param module: an already-imported module object (its ``__file__`` is
        read via :func:`inspect.getsource` — no re-execution, just source
        text).
    :param name: the plain module-level assignment target to find.
    :returns: the dict literal AST node.
    :raises AssertionError: if no such top-level ``name = {...}`` exists —
        a structural change to the module this test would need updating for.
    """
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
            and isinstance(node.value, ast.Dict)
        ):
            return node.value
        # `_BUILDERS: dict[EventType, EventBuilder] = {...}` is an annotated
        # assignment (ast.AnnAssign, singular .target), not a plain ast.Assign.
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and isinstance(node.value, ast.Dict)
        ):
            return node.value
    raise AssertionError(f"no top-level `{name} = {{...}}` dict literal in {module.__name__}")


def _wire_keys_by_event_type(dict_literal: ast.Dict) -> dict[str, frozenset[str]]:
    """Map each ``EventType.X`` key in ``dict_literal`` to the frozenset of
    string-literal keys its lambda value reads via ``<name>.get("key", ...)``.

    This is the WIRE contract each builder actually consults from its raw
    ``payload``/``p`` dict — independent of whatever a pydantic model on the
    far end chooses to NAME that field. Loop bound: ``len(dict_literal.keys)``
    (== ``len(EventType)``, 84).

    :param dict_literal: a dict literal AST node whose keys are
        ``EventType.X`` attributes and whose values are lambdas.
    :returns: ``EventType`` member name -> frozenset of wire keys read.
    """
    result: dict[str, frozenset[str]] = {}
    pairs = zip(dict_literal.keys, dict_literal.values, strict=True)
    for key_node, value_node in pairs:  # loop bound: len(EventType), 84
        assert isinstance(key_node, ast.Attribute), f"expected `EventType.X` key, got {key_node}"
        get_calls = [
            call
            for call in ast.walk(value_node)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "get"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        ]
        result[key_node.attr] = frozenset(call.args[0].value for call in get_calls)
    return result


def test_summary_builders_only_read_wire_keys_event_builders_also_reads() -> None:
    """The load-bearing cross-check: every wire-payload key a
    ``_SUMMARY_BUILDERS`` lambda reads, for a given ``EventType``, must be a
    key ``EVENT_BUILDERS``' OWN builder for that SAME ``EventType`` also
    reads. ``EVENT_BUILDERS`` is ground truth for the wire contract — it IS
    the tested bus->pydantic path (``tests/unit/engine/
    test_event_builders.py``). A summary builder reading any other key
    silently renders a blank/default field forever — exactly what
    ``CLASS_DECOMPOSITION``'s ``original_id`` (a pydantic FIELD name, never a
    wire key) did before this test existed. Parses BOTH registries' real
    source (no hand-maintained key lists to go stale)."""
    engine_keys = _wire_keys_by_event_type(
        _dict_literal_assigned_to(_event_builders_module, "_BUILDERS")
    )
    summary_keys = _wire_keys_by_event_type(
        _dict_literal_assigned_to(_chronicle_adapter_module, "_SUMMARY_BUILDERS")
    )

    shared_event_types = sorted(set(engine_keys) & set(summary_keys))
    assert len(shared_event_types) == 64, (
        "expected _SUMMARY_BUILDERS' coverage to match EVENT_BUILDERS' 64 — "
        "a change to either registry's coverage should be a deliberate, "
        "reviewed widening/narrowing, not silent drift"
    )

    for name in shared_event_types:  # loop bound: len(EventType), 84
        extra = summary_keys[name] - engine_keys[name]
        assert not extra, (
            f"{name}: chronicle_adapter's summary builder reads wire key(s) "
            f"{sorted(extra)} that event_builders.EVENT_BUILDERS' OWN builder "
            f"for {name} never reads. Cross-check against the real wire "
            f"contract (EVENT_BUILDERS' `payload.get(...)` calls), not a "
            f"pydantic model's field name."
        )


# --------------------------------------------------------------------------- #
# Unknown EventType: loud generic form, never dropped.                        #
# --------------------------------------------------------------------------- #


def test_unknown_event_type_gets_the_loud_generic_form() -> None:
    """An ``EventType`` with no bespoke builder (a genuinely never-emitted
    value, e.g. ``ENDGAME_REACHED`` — see the module docstring) still renders
    a real, honest summary naming the raw type and the fields present."""
    summary = summarize_event(EventType.ENDGAME_REACHED, 42, {"outcome": "unresolved"})
    assert "endgame_reached" in summary
    assert "42" in summary
    assert "outcome" in summary


def test_unknown_event_type_with_no_payload_says_so_honestly() -> None:
    """An unclassified type with a genuinely empty payload renders the
    honest "no payload recorded" form rather than a blank/fabricated line."""
    summary = summarize_event(EventType.PATTERN_SHIFT, 9, {})
    assert summary == "pattern_shift (tick 9) — no payload recorded"


def test_unknown_event_type_is_never_dropped_from_the_chronicle() -> None:
    """A bus event of an unclassified-but-real EventType still produces a
    ChronicleEvent — the Chronicle never silently drops it."""
    raw = [Event(type=EventType.ENDGAME_REACHED.value, tick=1, payload={"outcome": "unresolved"})]
    result = chronicle_events_from_bus(raw)
    assert len(result) == 1
    assert result[0].event_type is EventType.ENDGAME_REACHED
    assert result[0].summary  # non-empty, real content


# --------------------------------------------------------------------------- #
# chronicle_events_from_bus: shape, malformed-type loudness, per-tick semantics. #
# --------------------------------------------------------------------------- #


def test_chronicle_events_from_bus_preserves_order_and_data() -> None:
    """One ``ChronicleEvent`` per input event, same order, payload preserved
    verbatim in ``.data``."""
    raw = [
        Event(type=EventType.LIFECYCLE_TRANSITION.value, tick=4, payload={"territory_id": "T000"}),
        Event(type=EventType.ORGANIZATIONAL_ACTION.value, tick=4, payload={"org_count": 1}),
    ]
    result = chronicle_events_from_bus(raw)
    assert [ev.event_type for ev in result] == [
        EventType.LIFECYCLE_TRANSITION,
        EventType.ORGANIZATIONAL_ACTION,
    ]
    assert result[0].data == {"territory_id": "T000"}
    assert result[1].data == {"org_count": 1}
    assert all(ev.tick == 4 for ev in result)


def test_chronicle_events_from_bus_empty_history_is_empty() -> None:
    """A tick with genuinely no events yields ``()`` — never fabricated."""
    assert chronicle_events_from_bus([]) == ()


def test_chronicle_events_from_bus_raises_on_a_malformed_event_type() -> None:
    """A bus event carrying a non-``EventType`` string is a bug elsewhere —
    it raises loudly (Constitution III.11) rather than being silently
    dropped from the Chronicle."""
    raw = [Event(type="not_a_real_event_type", tick=1, payload={})]
    with pytest.raises(ValueError, match="not_a_real_event_type"):
        chronicle_events_from_bus(raw)


def test_chronicle_events_from_bus_is_per_tick_not_cumulative() -> None:
    """Two independent calls never leak state into each other — mirrors
    ``WorldState.events``'s own per-tick, never-cumulative contract. The
    adapter has no memory: tick 2's result contains ONLY tick 2's events."""
    tick1_events = [
        Event(type=EventType.LIFECYCLE_TRANSITION.value, tick=1, payload={"territory_id": "T000"})
    ]
    tick2_events = [
        Event(type=EventType.ORGANIZATIONAL_ACTION.value, tick=2, payload={"org_count": 1})
    ]

    first_call = chronicle_events_from_bus(tick1_events)
    second_call = chronicle_events_from_bus(tick2_events)

    assert len(first_call) == 1
    assert len(second_call) == 1
    assert second_call[0].event_type is EventType.ORGANIZATIONAL_ACTION
    assert second_call[0].tick == 2
    # No trace of tick 1's event survives into tick 2's result.
    assert all(ev.event_type is not EventType.LIFECYCLE_TRANSITION for ev in second_call)

    # And re-processing tick 1's own (unchanged) events again reproduces the
    # exact same result — determinism, not first-call-wins caching.
    replayed_tick1 = chronicle_events_from_bus(tick1_events)
    assert replayed_tick1 == first_call


# --------------------------------------------------------------------------- #
# Event-to-territory anchoring (Unit U5): a class/org node_id in the payload  #
# gains a resolved territory anchor when a live graph is threaded through.    #
# --------------------------------------------------------------------------- #


def _graph_with_tenancy(class_id: str = "C001", territory_id: str = "T001") -> BabylonGraph:
    """A minimal live graph: one social_class TENANCY-linked to one territory."""
    graph = BabylonGraph()
    graph.add_node(territory_id, NodeType.TERRITORY, name="Wayne County")
    graph.add_node(class_id, NodeType.SOCIAL_CLASS, name="Periphery Proletariat")
    graph.add_edge(class_id, territory_id, EdgeType.TENANCY)
    return graph


def test_uprising_on_a_tenancy_linked_class_resolves_its_territory_anchor() -> None:
    """UPRISING's ``node_id`` is a social_class id (``struggle.py``'s own
    ``node.id``) — with a live graph carrying that class's TENANCY edge, the
    ChronicleEvent gains a real ``data["anchor"]`` AND the human summary
    stops showing a bare, unanchored node id."""
    graph = _graph_with_tenancy()
    raw = [
        Event(
            type=EventType.UPRISING.value,
            tick=9,
            payload={"node_id": "C001", "trigger": "spark", "agitation": 0.8, "repression": 0.3},
        )
    ]
    result = chronicle_events_from_bus(raw, graph=graph)
    assert result[0].data["anchor"] == {"territory_id": "T001", "territory_name": "Wayne County"}
    assert "Wayne County" in result[0].summary
    # The raw payload is preserved verbatim alongside the anchor, not replaced.
    assert result[0].data["node_id"] == "C001"


def test_uprising_with_no_node_id_stays_clean() -> None:
    """A payload that never carries the anchor-eligible key resolves to no
    anchor at all — honest absence, not a fabricated one."""
    graph = _graph_with_tenancy()
    raw = [Event(type=EventType.UPRISING.value, tick=9, payload={"trigger": "spark"})]
    result = chronicle_events_from_bus(raw, graph=graph)
    assert "anchor" not in result[0].data


def test_uprising_on_a_class_with_no_tenancy_edge_stays_unanchored() -> None:
    """A real node_id with NO TENANCY edge into any territory resolves to no
    anchor — Constitution III.11, never a guessed territory."""
    graph = _graph_with_tenancy()
    raw = [Event(type=EventType.UPRISING.value, tick=9, payload={"node_id": "C999"})]
    result = chronicle_events_from_bus(raw, graph=graph)
    assert "anchor" not in result[0].data


def test_anchoring_is_deterministic_over_repeated_calls() -> None:
    """The SAME graph + SAME events always resolve the SAME anchor —
    Constitution III.7 determinism, not a first-call-wins cache."""
    graph = _graph_with_tenancy()
    raw = [Event(type=EventType.UPRISING.value, tick=9, payload={"node_id": "C001"})]
    first = chronicle_events_from_bus(raw, graph=graph)
    second = chronicle_events_from_bus(raw, graph=graph)
    assert first == second
    assert first[0].data["anchor"] == second[0].data["anchor"]


def test_no_graph_threaded_preserves_the_pre_existing_unanchored_behavior() -> None:
    """Callers that never thread a graph through (the default) get exactly
    the pre-U5 behavior — no ``anchor`` key, no crash. Backward compatible
    with every pre-existing call site/test."""
    raw = [Event(type=EventType.UPRISING.value, tick=9, payload={"node_id": "C001"})]
    result = chronicle_events_from_bus(raw)
    assert "anchor" not in result[0].data


def test_event_type_with_no_anchor_field_never_gains_one_even_with_a_graph() -> None:
    """An EventType outside the anchor-field registry (e.g.
    ORGANIZATIONAL_ACTION, which has no class/org subject at all) never
    gains a fabricated anchor just because a graph happens to be present."""
    graph = _graph_with_tenancy()
    raw = [
        Event(
            type=EventType.ORGANIZATIONAL_ACTION.value,
            tick=9,
            payload={"org_count": 2, "action_count": 3, "layer0_count": 1},
        )
    ]
    result = chronicle_events_from_bus(raw, graph=graph)
    assert "anchor" not in result[0].data


@pytest.mark.parametrize(
    ("event_type", "field"),
    [
        (EventType.EXCESSIVE_FORCE, "node_id"),
        (EventType.SOLIDARITY_SPIKE, "node_id"),
        (EventType.FASCIST_DRIFT, "node_id"),
        (EventType.POGROM, "target_id"),
        (EventType.LOCKOUT, "target_id"),
        (EventType.VIGILANTISM, "target_id"),
    ],
)
def test_other_class_scoped_event_types_also_anchor(event_type: EventType, field: str) -> None:
    """Every other verified class-scoped ``EventType`` (struggle.py's
    EXCESSIVE_FORCE/SOLIDARITY_SPIKE sharing UPRISING's own ``node.id``;
    ``reactionary.py``'s FASCIST_DRIFT; the reactionary-verb family's
    ``target_id`` — the SAME ``target_id`` the legacy
    ``web/game/engine_bridge.py::_TERRITORY_ANCHORED_VERB_EVENTS`` precedent
    already anchors) resolves through the same mechanism, not just UPRISING."""
    graph = _graph_with_tenancy()
    raw = [Event(type=event_type.value, tick=9, payload={field: "C001"})]
    result = chronicle_events_from_bus(raw, graph=graph)
    assert result[0].data["anchor"] == {"territory_id": "T001", "territory_name": "Wayne County"}
