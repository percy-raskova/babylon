"""Behavioral law for CommunitySystem (P27 Phase-0 backfill, §8.4).

Laws pinned (grounded by reading ``CommunitySystem.step()`` end-to-end plus
the formulas it calls -- src/babylon/engine/systems/community.py,
src/babylon/formulas/community.py):

  L1 -- inactivity, no hypergraph config: ``_get_community_states_from_services``
       returns ``{}`` whenever ``services.community_hypergraph is None``
       (community.py, ``_get_community_states_from_services``), and
       ``step()``'s very first line is ``if not community_states: return``
       -- so with the default (no) service config, step() never touches a
       node, an edge, or ``community_states`` for ANY starting graph state.

  L2 -- inactivity, no memberships anywhere: even with a non-empty
       ``community_states`` config, ``step()`` calls
       ``_collect_memberships(graph)`` and immediately returns
       (``if not all_memberships: return``) before hypergraph construction,
       solidarity amplification, threat scoring, cost-modifier writes, OR
       community-state decay run -- so a graph where every SOCIAL_CLASS
       node's ``community_memberships`` list is empty leaves both the
       nodes/edges AND the ``community_states`` dict byte-identical after
       step(), regardless of the configured heat/cohesion values.

  L3 -- threat_score bounds: ``calculate_threat_score`` (formulas/community.py)
       sums ``heat * effective_visibility * role_weight * legal_status_mult``
       across memberships -- every factor is non-negative by domain
       construction (heat/visibility are ``Probability`` in [0, 1];
       ``ROLE_STRENGTH_WEIGHTS``/``LEGAL_STATUS_MULTIPLIERS`` are fixed
       positive tables in models/entities/community.py) -- so the sum, and
       hence ``threat_score``, is never negative. Separately,
       ``_compute_threat_scores`` explicitly writes ``threat_score=0.0`` for
       any agent with an empty memberships list (community.py, the
       ``if not memberships: graph.update_node(node_id, threat_score=0.0)``
       branch) -- never computed, always the literal zero.

  L4 -- decay bounds (fixed default defines config): ``_apply_community_decay``
       computes ``new_heat = heat * (1 - heat_decay_alpha)`` and
       ``new_cohesion = cohesion * (1 - cohesion_decay_alpha)`` with NO
       maintenance/counteracting term for either field (only infrastructure
       has one) and ``heat_decay_alpha``/``cohesion_decay_alpha`` are
       ``CommunityDefines`` fields constrained ``[0, 1]``
       (config/defines/organizations.py) -- so for any starting heat/cohesion,
       one step of decay never INCREASES either value. Infrastructure DOES
       have a CORE_ORGANIZER maintenance term that can push it back up, but
       ``calculate_infrastructure_decay`` clamps the result with
       ``max(0.0, min(1.0, new_value))`` (formulas/community.py) -- so
       infrastructure always stays in [0, 1] regardless of organizer count.

Caveats (not laws):
  - Infrastructure is NOT monotonically non-increasing like heat/cohesion --
    CORE_ORGANIZER maintenance can raise it tick-over-tick. Only the [0, 1]
    clamp is pinned as a law for infrastructure.
  - L1/L2 are two DISTINCT inactivity gates (config-level vs
    membership-level) -- both must independently trip for step() to be a
    no-op; a graph with configured community_states AND at least one
    membership runs the full pipeline even if that one membership belongs
    to an otherwise-irrelevant community.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.community import CommunitySystem
from babylon.models.entities.community import CommunityMembership, CommunityState
from babylon.models.enums import CommunityType, EdgeType, MembershipRole, NodeType
from babylon.topology.graph import BabylonGraph

# Bounded, NaN/inf-free float strategy for [0, 1]-domain quantities
# (heat, cohesion, infrastructure, visibility are all Probability-typed).
_UNIT_INTERVAL = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_WEALTH_STRATEGY = st.floats(
    min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False
)
_ROLE_STRATEGY = st.sampled_from(list(MembershipRole))


def _make_social_class_node(
    graph: BabylonGraph,
    node_id: str,
    memberships: list[CommunityMembership] | None = None,
    **extra_attrs: object,
) -> None:
    """Add a SOCIAL_CLASS node shaped exactly as CommunitySystem reads it.

    Mirrors tests/unit/engine/systems/test_community_system.py's
    ``_make_graph_with_solidarity_edge`` helper: nodes carry the real
    ``NodeType.SOCIAL_CLASS`` marker (never a hand-stamped raw string,
    per the vocabulary-sentinel law) and ``community_memberships`` as
    the plain-dict shape ``_extract_memberships_from_node`` reads
    (community.py).
    """
    graph.add_node(
        node_id,
        node_type=NodeType.SOCIAL_CLASS,
        active=True,
        community_memberships=[m.model_dump() for m in (memberships or [])],
        **extra_attrs,
    )


def _make_services(
    community_states: dict[CommunityType, CommunityState] | None = None,
) -> ServiceContainer:
    """Default GameDefines service container, optionally with community config.

    ``community_hypergraph`` defaults to ``None`` (matches
    ``ServiceContainer.create``'s own default) -- the exact condition L1
    exercises.
    """
    if community_states is None:
        return ServiceContainer.create()
    return ServiceContainer.create(
        community_hypergraph={"community_states": community_states},
    )


class TestCommunityInactivityNoConfigLaw:
    """L1 -- with no community_hypergraph service config, step() is a no-op."""

    @given(wealth=_WEALTH_STRATEGY)
    @settings(max_examples=25, deadline=None)
    def test_no_config_leaves_graph_untouched(self, wealth: float) -> None:
        graph = BabylonGraph()
        _make_social_class_node(graph, "A1", wealth=wealth, threat_score=0.0)
        _make_social_class_node(graph, "A2", wealth=wealth)
        graph.add_edge("A1", "A2", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.5)

        services = _make_services(community_states=None)

        before_a1 = dict(graph.nodes["A1"])
        before_a2 = dict(graph.nodes["A2"])
        before_edge = dict(graph.edges["A1", "A2"])

        CommunitySystem().step(graph, services, TickContext(tick=1))

        assert dict(graph.nodes["A1"]) == before_a1
        assert dict(graph.nodes["A2"]) == before_a2
        assert dict(graph.edges["A1", "A2"]) == before_edge


class TestCommunityInactivityEmptyMembershipLaw:
    """L2 -- configured community_states but zero agent memberships is a no-op."""

    @given(heat=_UNIT_INTERVAL, cohesion=_UNIT_INTERVAL)
    @settings(max_examples=25, deadline=None)
    def test_empty_memberships_freeze_nodes_and_community_state(
        self, heat: float, cohesion: float
    ) -> None:
        graph = BabylonGraph()
        _make_social_class_node(graph, "A1", wealth=10.0)
        _make_social_class_node(graph, "A2", wealth=10.0)
        graph.add_edge("A1", "A2", edge_type=EdgeType.SOLIDARITY, solidarity_strength=0.5)

        state = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            heat=heat,  # type: ignore[arg-type]
            cohesion=cohesion,  # type: ignore[arg-type]
        )
        community_states = {CommunityType.NEW_AFRIKAN: state}
        services = _make_services(community_states=community_states)

        before_a1 = dict(graph.nodes["A1"])
        before_a2 = dict(graph.nodes["A2"])
        before_edge = dict(graph.edges["A1", "A2"])

        CommunitySystem().step(graph, services, TickContext(tick=1))

        assert dict(graph.nodes["A1"]) == before_a1
        assert dict(graph.nodes["A2"]) == before_a2
        assert dict(graph.edges["A1", "A2"]) == before_edge
        # The community_states dict itself (same object, passed by
        # reference through the services config) is untouched -- decay
        # never ran.
        unchanged = community_states[CommunityType.NEW_AFRIKAN]
        assert unchanged is state
        assert float(unchanged.heat) == float(state.heat)
        assert float(unchanged.cohesion) == float(state.cohesion)


class TestCommunityThreatScoreLaw:
    """L3 -- threat_score is never negative; no-membership agents get exact 0.0."""

    @given(
        heat=_UNIT_INTERVAL,
        visibility=_UNIT_INTERVAL,
        role=_ROLE_STRATEGY,
    )
    @settings(max_examples=25, deadline=None)
    def test_threat_score_nonnegative_and_zero_for_no_membership(
        self, heat: float, visibility: float, role: MembershipRole
    ) -> None:
        graph = BabylonGraph()
        membership = CommunityMembership(
            agent_id="A1",
            community_type=CommunityType.NEW_AFRIKAN,
            role=role,
            visibility=visibility,  # type: ignore[arg-type]
        )
        _make_social_class_node(graph, "A1", memberships=[membership], wealth=10.0)
        _make_social_class_node(graph, "A2", memberships=[], wealth=10.0)

        community_states = {
            CommunityType.NEW_AFRIKAN: CommunityState(
                community_type=CommunityType.NEW_AFRIKAN,
                heat=heat,  # type: ignore[arg-type]
            ),
        }
        services = _make_services(community_states=community_states)

        CommunitySystem().step(graph, services, TickContext(tick=1))

        assert graph.nodes["A1"]["threat_score"] >= 0.0
        assert graph.nodes["A2"]["threat_score"] == 0.0


class TestCommunityDecayBoundsLaw:
    """L4 -- heat/cohesion never increase per tick; infrastructure stays in [0, 1]."""

    @given(
        heat=_UNIT_INTERVAL,
        cohesion=_UNIT_INTERVAL,
        infrastructure=_UNIT_INTERVAL,
        organizer_count=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=25, deadline=None)
    def test_heat_cohesion_never_increase_infra_stays_clamped(
        self,
        heat: float,
        cohesion: float,
        infrastructure: float,
        organizer_count: int,
    ) -> None:
        graph = BabylonGraph()
        memberships = [
            CommunityMembership(
                agent_id=f"A{i}",
                community_type=CommunityType.NEW_AFRIKAN,
                role=MembershipRole.CORE_ORGANIZER,
            )
            for i in range(organizer_count)
        ]
        if not memberships:
            # Step()'s all_memberships guard needs at least ONE membership
            # anywhere to clear L2's early return; a non-organizer role
            # keeps organizer_count at 0 for this community as intended.
            memberships = [
                CommunityMembership(
                    agent_id="A0",
                    community_type=CommunityType.NEW_AFRIKAN,
                    role=MembershipRole.PERIPHERAL,
                )
            ]
        for i, mem in enumerate(memberships):
            _make_social_class_node(graph, f"A{i}", memberships=[mem], wealth=10.0)

        state = CommunityState(
            community_type=CommunityType.NEW_AFRIKAN,
            heat=heat,  # type: ignore[arg-type]
            cohesion=cohesion,  # type: ignore[arg-type]
            infrastructure=infrastructure,  # type: ignore[arg-type]
        )
        # Read back the STORED (grid-quantized) starting values rather than
        # the raw hypothesis floats -- Probability fields snap to a 1e-5
        # grid at construction (models/types.py SnapToGrid), so the input
        # draw and the field's actual value can differ by up to half a
        # grid tick.
        starting_heat = float(state.heat)
        starting_cohesion = float(state.cohesion)

        community_states = {CommunityType.NEW_AFRIKAN: state}
        services = _make_services(community_states=community_states)

        CommunitySystem().step(graph, services, TickContext(tick=1))

        new_state = community_states[CommunityType.NEW_AFRIKAN]
        assert float(new_state.heat) <= starting_heat + 1e-9
        assert float(new_state.cohesion) <= starting_cohesion + 1e-9
        assert 0.0 <= float(new_state.infrastructure) <= 1.0
