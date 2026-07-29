"""Behavioral laws for OODASystem (P27 Phase-0 coverage backfill, §8.4).

OODASystem (``src/babylon/engine/systems/ooda.py``) orchestrates three
phases each tick: Layer 0 (automatic Business metabolism), the initiative-
ordered Action Phase, and Layer 3 (consequence propagation). These laws
pin invariants read directly off ``step()`` / ``_resolve_for_organization``
and their helpers (``ooda/initiative.py``, ``ooda/layer0.py``,
``ooda/npc_stub.py``) -- NOT re-derivations of the full resolver math
(verb effects, layer3 propagation), which are covered elsewhere.

Laws pinned:
  L1 -- initiative-score conservation: every organization node in the graph
        yields EXACTLY ONE ``InitiativeScore`` in the published
        ``turn_resolution["initiative_order"]``. The score-computation loop
        (ooda.py:136-167) iterates unconditionally over every collected org
        node (``_collect_org_nodes`` filters only on
        ``_node_type == "organization"``, ooda.py:452-454; no org_type
        filter), and ``resolve_action_order`` (initiative.py:66-75) is a
        pure ``sorted()`` over that list -- it can reorder but never drop
        or add entries. So len(initiative_order) == count of organization
        nodes, for counts below the ``max_orgs = 1000`` loop-safety cap
        (ooda.py:137-138).
  L2 -- Business-org exclusion from the action phase: no ``ActionResult``
        in ``action_phase_results`` has an ``action.org_id`` belonging to
        a BUSINESS-type organization. ``_resolve_for_organization`` returns
        ``[]`` immediately when ``org_data.get("org_type") ==
        OrgType.BUSINESS.value`` (ooda.py:304-306) -- Business orgs are
        handled exclusively by Layer 0 (``process_layer0``), never by the
        initiative-ordered action phase.
  L3 -- action-count clamp: ``len(action_phase_results) <= 500`` always,
        regardless of how many organizations are eligible to act, because
        the resolution loop breaks the instant the running total reaches
        ``max_actions_total = 500`` (ooda.py:184-187).
  L4 -- inactivity on org-free input: a graph with zero organization nodes
        (empty graph, or a graph containing only non-organization nodes)
        produces an EMPTY ``layer0_results`` and an EMPTY
        ``action_phase_results``. ``process_layer0`` only ever collects
        nodes with both ``_node_type == "organization"`` AND
        ``org_type == OrgType.BUSINESS.value`` (layer0.py:37-42), and the
        Action Phase's own org collection uses the same
        ``_node_type == "organization"`` filter (ooda.py:452-454) -- with
        no org nodes, both phases have nothing to iterate and produce no
        results.

Caveat (NOT a law): NPC action selection (``select_npc_actions``) is NOT
guaranteed to return a non-empty action list for every non-Business org
(eligibility checks / action-point exhaustion can yield zero actions), so
"every non-Business org produces >= 1 action_phase_result" is FALSE in
general and is deliberately not pinned here.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines import GameDefines
from babylon.engine.context import TickContext
from babylon.engine.systems.ooda import OODASystem
from babylon.models.enums import OrgType
from babylon.topology.graph import BabylonGraph

# The four OrgType values the real NPC priority-queue table
# (ooda/npc_stub.py's ``_NPC_PRIORITIES``) and Layer 0's Business filter
# both key on. Kept small + closed so hypothesis-generated graphs stay
# cheap and every generated org_type is one the production code actually
# branches on (no invented enum members).
_ORG_TYPES = [
    OrgType.BUSINESS,
    OrgType.POLITICAL_FACTION,
    OrgType.STATE_APPARATUS,
    OrgType.CIVIL_SOCIETY,
]


def _make_services() -> MagicMock:
    """Real ``GameDefines`` + a mock event bus (mirrors
    ``tests/unit/ooda/test_ooda_system.py::_make_services`` -- the
    project's established OODASystem test fixture pattern)."""
    services = MagicMock()
    services.defines = GameDefines()
    services.event_bus = MagicMock()
    return services


def _graph_with_orgs(org_types: list[OrgType]) -> BabylonGraph:
    """Build a graph with one organization node per entry in *org_types*,
    plus the territory they all claim. Uses the real ``BabylonGraph.add_node``
    API and the real ``_node_type``/``org_type`` vocabulary strings --
    never hand-stamped ad hoc (vocabulary-sentinel law)."""
    graph = BabylonGraph()
    graph.add_node("home_territory", _node_type="territory")
    for idx, org_type in enumerate(org_types):
        graph.add_node(
            f"org_{idx}",
            _node_type="organization",
            org_type=org_type.value,
            territory_ids=["home_territory"],
            # No ooda_profile stamp: no production seeder ever stamps it
            # (vocabulary-sentinel exemption ledger, tracking #45), so every
            # real game runs on the default OODAProfile() — the law tests
            # the shape reality actually has.
        )
    return graph


@given(org_types=st.lists(st.sampled_from(_ORG_TYPES), min_size=0, max_size=12))
@settings(max_examples=25, deadline=None)
def test_initiative_order_conserves_every_org_node(org_types: list[OrgType]) -> None:
    """L1: one InitiativeScore per organization node, no drops/adds."""
    graph = _graph_with_orgs(org_types)
    services = _make_services()
    context = TickContext(tick=1)

    OODASystem().step(graph, services, context)

    resolution = context.persistent_data["turn_resolution"]
    assert len(resolution["initiative_order"]) == len(org_types)
    scored_org_ids = {score["org_id"] for score in resolution["initiative_order"]}
    expected_org_ids = {f"org_{idx}" for idx in range(len(org_types))}
    assert scored_org_ids == expected_org_ids


@given(org_types=st.lists(st.sampled_from(_ORG_TYPES), min_size=1, max_size=12))
@settings(max_examples=25, deadline=None)
def test_business_orgs_never_appear_in_action_phase_results(org_types: list[OrgType]) -> None:
    """L2: Business orgs are Layer-0-only; never in the action phase."""
    graph = _graph_with_orgs(org_types)
    services = _make_services()
    context = TickContext(tick=1)

    OODASystem().step(graph, services, context)

    resolution = context.persistent_data["turn_resolution"]
    business_org_ids = {
        f"org_{idx}" for idx, org_type in enumerate(org_types) if org_type == OrgType.BUSINESS
    }
    action_phase_org_ids = {
        result["action"]["org_id"] for result in resolution["action_phase_results"]
    }
    assert not (business_org_ids & action_phase_org_ids), (
        f"Business org(s) {business_org_ids & action_phase_org_ids} leaked into "
        "action_phase_results -- Business orgs must be handled exclusively by "
        "Layer 0 (process_layer0), never the initiative-ordered action phase."
    )


def test_action_phase_results_clamped_to_500_regardless_of_org_count() -> None:
    """L3: the 500-action cap holds even with far more eligible orgs.

    520 POLITICAL_FACTION orgs (each with a nonzero action-point budget,
    so each is expected to produce at least one NPC action) exceeds the
    ``max_actions_total = 500`` cap (ooda.py:184-187) -- this pins the
    clamp fires rather than merely never being exercised.
    """
    org_types = [OrgType.POLITICAL_FACTION] * 520
    graph = _graph_with_orgs(org_types)
    services = _make_services()
    context = TickContext(tick=1)

    OODASystem().step(graph, services, context)

    resolution = context.persistent_data["turn_resolution"]
    assert len(resolution["action_phase_results"]) <= 500


def test_empty_graph_produces_no_layer0_or_action_phase_results() -> None:
    """L4a: zero organization nodes at all -> zero results in both phases."""
    graph = BabylonGraph()
    services = _make_services()
    context = TickContext(tick=0)

    OODASystem().step(graph, services, context)

    resolution = context.persistent_data["turn_resolution"]
    assert resolution["layer0_results"] == []
    assert resolution["action_phase_results"] == []


def test_org_free_graph_with_other_node_types_produces_no_results() -> None:
    """L4b: non-organization nodes present, but no organization nodes ->
    still zero results in both phases (the org-collection filter is on
    ``_node_type``, not node presence in general)."""
    graph = BabylonGraph()
    graph.add_node("lonely_territory", _node_type="territory")
    graph.add_node("lonely_class", _node_type="social_class")
    services = _make_services()
    context = TickContext(tick=0)

    OODASystem().step(graph, services, context)

    resolution = context.persistent_data["turn_resolution"]
    assert resolution["layer0_results"] == []
    assert resolution["action_phase_results"] == []
