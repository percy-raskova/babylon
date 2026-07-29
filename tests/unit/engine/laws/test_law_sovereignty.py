"""Behavioral laws for SovereigntySystem (P27 Phase-0 coverage backfill,
plan Task 11 / spec `docs/superpowers/specs/2026-07-28-program-27-refoundation-design.md`
§8.4).

Read end-to-end before writing (F1 discipline):
``src/babylon/engine/systems/sovereignty.py`` (160 lines) +
``babylon.formulas.balkanization.calculate_metabolic_impact``.

Laws pinned (each traces to a specific evidenced branch in ``step()``):

  L1 -- Claims-gated output (inactivity on empty input):
        a Territory with zero CLAIMS edges never appears as a key in
        either ``persistent_data`` dict and never triggers a
        DUAL_POWER_ACTIVE event; a graph with zero Territory nodes at
        all produces two empty dicts and zero events.
        Evidence: sovereignty.py:87-93 (``if not claims: continue``),
        sovereignty.py:126-127 (dicts are only ever populated inside the
        per-territory loop, after the claims-empty guard).

  L2 -- Effective-controller resolution (FR-020):
        for every territory present in the output,
        ``effective_controller_by_territory[t]`` is the sovereign_id of
        the claim with the strictly highest ``control_level``; ties at
        the maximum are broken by the lexicographically smallest
        ``sovereign_id``.
        Evidence: sovereignty.py:94-96 + 112 (``controller_id, _control,
        _legal = claims[0]``) composed with
        ``topology/graph.py:958`` (``rows.sort(key=lambda row: (-row[1],
        row[0]))`` -- the sort order ``query_territory_claims`` hands
        back to the system).

  L3 -- No double-counting the metabolic impact (FR-020):
        regardless of how many Sovereigns hold CLAIMS on a Territory,
        ``metabolic_impact_by_territory[t]`` is computed exactly ONCE,
        from the effective controller's OWN ``extraction_policy`` --
        never a sum or average across competing claimants -- and its
        value is always exactly one of the three canonical
        per-policy constants declared on ``services.defines.balkanization``.
        Evidence: sovereignty.py:100-111 (single
        ``calculate_metabolic_impact`` call per territory, using only
        ``controller_id``'s own policy) + ``formulas/balkanization.py``
        lines ~66-74 (the three-way policy dispatch to
        ``defines.metabolic_impact_{intensify,continue,cease}``).

  L4 -- Dual-power emission count (FR-035):
        the number of DUAL_POWER_ACTIVE events emitted in one ``step()``
        call equals exactly the number of territories with >= 2 CLAIMS
        edges whose ``control_level > 0.0``; each such event's
        ``competing_sovereign_ids`` is precisely the set of those active
        claimants' ids, and ``control_level_sum`` is the exact sum of
        their ``control_level`` values.
        Evidence: sovereignty.py:114-124 (``active_claimants = [row for
        row in claims if row[1] > 0.0]``; ``if len(active_claimants) >=
        2: dual_power_territories.append(...)``) + sovereignty.py:134-147
        (one event emitted per collected ``dual_power_territories`` row).

Caveats (recorded, not asserted as laws -- see the structured-output
``caveats`` field for the full text):

  - sovereignty.py:100-102 silently ``continue``s (drops the territory
    from BOTH output dicts) when the controller's ``extraction_policy``
    attribute is missing or unparseable via ``ExtractionPolicy(raw)``.
    This IS evidenced behavior but is deliberately NOT exercised here --
    every fixture in this file assigns each Sovereign a valid
    ``ExtractionPolicy`` member, so L1's "claims-gated" language is
    scoped to "claims present AND a resolvable policy on the
    controller", matching what the hypothesis-generated fixtures can
    produce. A dedicated deterministic regression test
    (``test_territory_dropped_when_controller_policy_unresolvable``)
    pins the line:100-102 branch directly without folding it into a
    property law, since genuinely-unparseable policy strings are a
    fixed edge case, not a distribution worth sampling.
  - control_level values are drawn from a coarse quarter-increment grid
    (multiples of 0.25 in [0, 3]) specifically so exact floating-point
    tie detection (L2's tiebreak branch) is both reachable by Hypothesis
    and safe to assert on with ``==`` (quarters are exact dyadic
    rationals in IEEE-754 double precision, and sums of a handful of
    them stay exact at this magnitude).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.sovereignty import SovereigntySystem
from babylon.models.enums import EdgeType, EventType, ExtractionPolicy, NodeType
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

_SOVEREIGN_POOL: tuple[str, ...] = ("SOV_A", "SOV_B", "SOV_C", "SOV_D")
_POLICIES: tuple[ExtractionPolicy, ...] = (
    ExtractionPolicy.INTENSIFY,
    ExtractionPolicy.CONTINUE,
    ExtractionPolicy.CEASE,
)
# Quarter-increment grid in [0, 3] -- exact dyadic rationals (see module
# docstring caveat on why this grid, not arbitrary floats).
_CONTROL_LEVELS: tuple[float, ...] = tuple(x / 4 for x in range(0, 13))


@dataclass
class _CapturedEvent:
    type: Any
    tick: int
    payload: dict[str, Any]


class _RecordingEventBus:
    def __init__(self) -> None:
        self.events: list[_CapturedEvent] = []

    def publish(self, event: Any) -> None:
        self.events.append(_CapturedEvent(type=event.type, tick=event.tick, payload=event.payload))


def _make_services() -> Any:
    """Fresh service container per Hypothesis example (mirrors the
    existing ``tests/unit/balkanization/test_sovereignty_system.py``
    fixture, but built per-call: a shared pytest fixture would leak
    ``_RecordingEventBus.events`` across Hypothesis examples within the
    same test invocation)."""
    container = MagicMock()
    container.event_bus = _RecordingEventBus()
    container.defines = GameDefines()
    return container


def _build_graph(
    policies: dict[str, ExtractionPolicy],
    claims_by_territory: dict[str, dict[str, float]],
) -> BabylonGraph:
    graph = BabylonGraph()
    for sovereign_id, policy in policies.items():
        graph.add_node(sovereign_id, NodeType.SOVEREIGN, extraction_policy=policy)
    for territory_id, claimants in claims_by_territory.items():
        graph.add_node(territory_id, NodeType.TERRITORY, habitability=0.5)
        for sovereign_id, control_level in claimants.items():
            graph.add_edge(
                sovereign_id,
                territory_id,
                EdgeType.CLAIMS,
                control_level=control_level,
                legal_status="de_facto",
            )
    return graph


def _expected_controller(claimants: dict[str, float]) -> str | None:
    """Independent reference for FR-020: max control_level, lexicographic
    sovereign_id tiebreak -- mirrors the LAW (topology/graph.py:958's sort
    key), not a call into production code."""
    if not claimants:
        return None
    return sorted(claimants.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


@st.composite
def _scenario(draw: st.DrawFn) -> tuple[dict[str, ExtractionPolicy], dict[str, dict[str, float]]]:
    policies: dict[str, ExtractionPolicy] = {
        sovereign_id: draw(st.sampled_from(_POLICIES)) for sovereign_id in _SOVEREIGN_POOL
    }
    num_territories = draw(st.integers(min_value=0, max_value=4))
    claims_by_territory: dict[str, dict[str, float]] = {}
    for i in range(num_territories):
        territory_id = f"HEX_{i:03d}"
        claimant_ids = draw(
            st.lists(
                st.sampled_from(_SOVEREIGN_POOL),
                min_size=0,
                max_size=3,
                unique=True,
            )
        )
        claims_by_territory[territory_id] = {
            sovereign_id: draw(st.sampled_from(_CONTROL_LEVELS)) for sovereign_id in claimant_ids
        }
    return policies, claims_by_territory


@given(scenario=_scenario())
@settings(max_examples=25, deadline=None)
def test_law_claims_gated_output(
    scenario: tuple[dict[str, ExtractionPolicy], dict[str, dict[str, float]]],
) -> None:
    """L1: territories with zero CLAIMS edges never appear in either
    output dict and never emit DUAL_POWER_ACTIVE."""
    policies, claims_by_territory = scenario
    graph = _build_graph(policies, claims_by_territory)
    services = _make_services()
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(graph, services, context)

    impact = context.persistent_data["balkanization.metabolic_impact_by_territory"]
    controllers = context.persistent_data["balkanization.effective_controller_by_territory"]
    bus: _RecordingEventBus = services.event_bus
    dual_power_territory_ids = {
        e.payload["territory_id"] for e in bus.events if e.type is EventType.DUAL_POWER_ACTIVE
    }

    unclaimed = {t for t, claimants in claims_by_territory.items() if not claimants}
    for territory_id in unclaimed:
        assert territory_id not in impact
        assert territory_id not in controllers
        assert territory_id not in dual_power_territory_ids


def test_law_claims_gated_output_whole_graph_empty() -> None:
    """L1 base case: zero Territory nodes at all -> two empty dicts, zero
    events. Deterministic (not hypothesis) since it is the single
    degenerate input, not a distribution."""
    graph = BabylonGraph()
    services = _make_services()
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(graph, services, context)

    assert context.persistent_data["balkanization.metabolic_impact_by_territory"] == {}
    assert context.persistent_data["balkanization.effective_controller_by_territory"] == {}
    bus: _RecordingEventBus = services.event_bus
    assert bus.events == []


@given(scenario=_scenario())
@settings(max_examples=25, deadline=None)
def test_law_effective_controller_matches_max_control_level_with_tiebreak(
    scenario: tuple[dict[str, ExtractionPolicy], dict[str, dict[str, float]]],
) -> None:
    """L2 (FR-020): effective controller = max control_level, lexicographic
    sovereign_id tiebreak."""
    policies, claims_by_territory = scenario
    graph = _build_graph(policies, claims_by_territory)
    services = _make_services()
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(graph, services, context)

    controllers = context.persistent_data["balkanization.effective_controller_by_territory"]
    for territory_id, claimants in claims_by_territory.items():
        if not claimants:
            continue
        assert controllers[territory_id] == _expected_controller(claimants)


@given(scenario=_scenario())
@settings(max_examples=25, deadline=None)
def test_law_metabolic_impact_no_double_counting(
    scenario: tuple[dict[str, ExtractionPolicy], dict[str, dict[str, float]]],
) -> None:
    """L3 (FR-020): impact is computed once from the controller's own
    policy -- never summed/averaged across competing claimants -- and is
    always exactly one of the three canonical per-policy constants."""
    policies, claims_by_territory = scenario
    graph = _build_graph(policies, claims_by_territory)
    services = _make_services()
    context = TickContext(tick=0, persistent_data={})
    defines = services.defines.balkanization
    expected_by_policy = {
        ExtractionPolicy.INTENSIFY: defines.metabolic_impact_intensify,
        ExtractionPolicy.CONTINUE: defines.metabolic_impact_continue,
        ExtractionPolicy.CEASE: defines.metabolic_impact_cease,
    }

    SovereigntySystem().step(graph, services, context)

    impact = context.persistent_data["balkanization.metabolic_impact_by_territory"]
    for territory_id, claimants in claims_by_territory.items():
        if not claimants:
            continue
        controller_id = _expected_controller(claimants)
        assert controller_id is not None
        expected = expected_by_policy[policies[controller_id]]
        assert impact[territory_id] == pytest.approx(expected)
        # Never the sum across claimants (would only coincide with the
        # single-claimant expected value by construction when len==1).
        if len(claimants) > 1:
            naive_sum = sum(expected_by_policy[policies[sid]] for sid in claimants)
            if naive_sum != pytest.approx(expected):
                assert impact[territory_id] != pytest.approx(naive_sum)


@given(scenario=_scenario())
@settings(max_examples=25, deadline=None)
def test_law_dual_power_emission_matches_active_claimant_count(
    scenario: tuple[dict[str, ExtractionPolicy], dict[str, dict[str, float]]],
) -> None:
    """L4 (FR-035): one DUAL_POWER_ACTIVE event per territory with >= 2
    active (control_level > 0.0) claimants; payload matches exactly."""
    policies, claims_by_territory = scenario
    graph = _build_graph(policies, claims_by_territory)
    services = _make_services()
    context = TickContext(tick=3, persistent_data={})

    SovereigntySystem().step(graph, services, context)

    bus: _RecordingEventBus = services.event_bus
    dual_power_events = {
        e.payload["territory_id"]: e for e in bus.events if e.type is EventType.DUAL_POWER_ACTIVE
    }

    expected_dual_power: dict[str, dict[str, float]] = {}
    for territory_id, claimants in claims_by_territory.items():
        active = {sid: lvl for sid, lvl in claimants.items() if lvl > 0.0}
        if len(active) >= 2:
            expected_dual_power[territory_id] = active

    assert set(dual_power_events) == set(expected_dual_power)
    for territory_id, active in expected_dual_power.items():
        event = dual_power_events[territory_id]
        assert event.tick == 3
        assert set(event.payload["competing_sovereign_ids"]) == set(active)
        assert event.payload["control_level_sum"] == pytest.approx(sum(active.values()))


def test_territory_dropped_when_controller_policy_unresolvable() -> None:
    """Caveat regression (sovereignty.py:100-102): a Sovereign with a
    missing/unparseable ``extraction_policy`` drops its Territory from
    BOTH output dicts entirely, even though a CLAIMS edge exists."""
    graph = BabylonGraph()
    graph.add_node("SOV_BROKEN", NodeType.SOVEREIGN)  # no extraction_policy set
    graph.add_node("HEX_000", NodeType.TERRITORY, habitability=0.5)
    graph.add_edge(
        "SOV_BROKEN",
        "HEX_000",
        EdgeType.CLAIMS,
        control_level=1.0,
        legal_status="de_facto",
    )
    services = _make_services()
    context = TickContext(tick=0, persistent_data={})

    SovereigntySystem().step(graph, services, context)

    impact = context.persistent_data["balkanization.metabolic_impact_by_territory"]
    controllers = context.persistent_data["balkanization.effective_controller_by_territory"]
    assert "HEX_000" not in impact
    assert "HEX_000" not in controllers
