"""Behavioral laws for EpistemicHorizonSystem (P27 Phase-0 backfill, Task 11).

System under law: ``src/babylon/engine/systems/epistemic_horizon.py``
(``EpistemicHorizonSystem`` / ``compute_epistemic_horizon`` /
``mass_receptivity_of``). Phase 1 SHADOW ONLY: this system writes
``mass_receptivity`` / ``intel_confidence`` / ``vision_state`` onto TERRITORY
nodes; nothing downstream reads them yet (no masking/reveal-gating in Phase 1).

Laws pinned (grounded in reading step()/compute_epistemic_horizon() end-to-end
first, per F1 discipline):

  L1 -- honest inactivity (Constitution III.11): a territory with NO tenant
        class carrying positive population gets NONE of
        mass_receptivity/intel_confidence/vision_state written -- never a
        fabricated 0.0 (epistemic_horizon.py:92-93 per-tenant skip,
        :108-110 total_population<=0 early-return, :168-171 continue).
  L2 -- mass_receptivity is bounded to [0, 1] whenever its inputs
        (p_acquiescence, class_consciousness) are themselves in the
        validated [0, 1] domain (as the real ``Probability``-typed
        SocialClass fields enforce) -- a population-weighted mean of
        per-class terms that are each a product of three [0, 1] factors
        stays in [0, 1] (epistemic_horizon.py:80-110). CAVEAT: the reader
        itself does NOT clamp -- ``mass_receptivity_of`` casts
        ``p_acquiescence``/``class_consciousness`` straight from graph
        attrs with no internal clamp (lines 91, 95-96), so this law only
        holds for validated-domain inputs, not arbitrary graph state.
  L3 -- vision_state is a pure deterministic function of the computed
        mass_receptivity against the defines threshold table: "desert"
        below ``desert_threshold``, "water" at/above ``water_threshold``,
        "mud" in between (epistemic_horizon.py:197-202). Tested against the
        real ``EpistemicHorizonDefines`` defaults (0.2 / 0.8) since
        ``ServiceContainer.create()`` supplies unmodified defaults.
  L4 -- intel_confidence is always clamped to [0, 1]
        (epistemic_horizon.py:189-195, ``max(0.0, min(1.0, ...))``),
        regardless of how far cadre presence + an injected
        ``investigation_intel`` push the raw pre-clamp sum in either
        direction.

Fixture note: the three graph builders below mirror
``tests/unit/engine/systems/test_epistemic_horizon.py``'s ``_territory`` /
``_tenant`` / ``_player_org_presence`` -- the project's real, already-shipped
EpistemicHorizon fixture idiom (real ``BabylonGraph`` API, real
``EdgeType.TENANCY`` / ``EdgeType.PRESENCE`` vocabulary, real
``social_class``/``territory``/``organization`` node-type strings already
exercised by that shipped, green suite). Duplicated locally rather than
cross-module-imported because the source helpers are module-private
(leading underscore = not a public fixture API).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.epistemic_horizon import EpistemicHorizonSystem
from babylon.models.enums import EdgeType, SocialRole
from babylon.topology.graph import BabylonGraph

pytestmark = pytest.mark.unit

# EpistemicHorizonDefines defaults (config/defines/epistemic_horizon.py) --
# ServiceContainer.create() supplies these unmodified.
_DEFAULT_DESERT_THRESHOLD = 0.2
_DEFAULT_WATER_THRESHOLD = 0.8


def _territory(graph: BabylonGraph, tid: str) -> None:
    graph.add_node(tid, _node_type="territory", id=tid, name=tid)


def _tenant(
    graph: BabylonGraph,
    cid: str,
    tid: str,
    *,
    role: str,
    population: float,
    p_acquiescence: float,
    class_consciousness: float,
) -> None:
    """Add a social_class node TENANCY-linked to ``tid``."""
    graph.add_node(
        cid,
        _node_type="social_class",
        id=cid,
        role=role,
        population=population,
        p_acquiescence=p_acquiescence,
        ideology={
            "class_consciousness": class_consciousness,
            "national_identity": 0.5,
            "agitation": 0.0,
        },
    )
    graph.add_edge(cid, tid, edge_type=EdgeType.TENANCY)


def _player_org_presence(graph: BabylonGraph, org_id: str, tid: str) -> None:
    graph.add_node(org_id, _node_type="organization", id=org_id, is_player=True)
    graph.add_edge(org_id, tid, edge_type=EdgeType.PRESENCE)


_ROLE_STRATEGY = st.sampled_from(list(SocialRole))
_UNIT_FLOAT = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_POPULATION = st.floats(
    min_value=1e-3, max_value=1_000_000.0, allow_nan=False, allow_infinity=False
)
_TENANT_STRATEGY = st.tuples(_ROLE_STRATEGY, _POPULATION, _UNIT_FLOAT, _UNIT_FLOAT)


@given(
    include_zero_population_tenant=st.booleans(),
    role=_ROLE_STRATEGY,
    p_acquiescence=_UNIT_FLOAT,
    class_consciousness=_UNIT_FLOAT,
)
@settings(max_examples=25, deadline=None)
def test_no_positive_population_tenant_writes_no_shadow_attrs(
    include_zero_population_tenant: bool,
    role: SocialRole,
    p_acquiescence: float,
    class_consciousness: float,
) -> None:
    """L1: no positive-population tenant -> no shadow attrs at all."""
    graph = BabylonGraph()
    _territory(graph, "T001")
    if include_zero_population_tenant:
        _tenant(
            graph,
            "C001",
            "T001",
            role=str(role),
            population=0.0,
            p_acquiescence=p_acquiescence,
            class_consciousness=class_consciousness,
        )

    EpistemicHorizonSystem().step(graph, ServiceContainer.create(), TickContext())

    attrs = graph.get_node("T001").attributes
    assert "mass_receptivity" not in attrs
    assert "intel_confidence" not in attrs
    assert "vision_state" not in attrs


@given(tenants=st.lists(_TENANT_STRATEGY, min_size=1, max_size=3))
@settings(max_examples=25, deadline=None)
def test_mass_receptivity_is_bounded_to_unit_interval(
    tenants: list[tuple[SocialRole, float, float, float]],
) -> None:
    """L2: M_r, a population-weighted mean of [0,1] products, stays in [0,1]."""
    graph = BabylonGraph()
    _territory(graph, "T001")
    for i, (role, population, p_acquiescence, class_consciousness) in enumerate(tenants):
        _tenant(
            graph,
            f"C{i:03d}",
            "T001",
            role=str(role),
            population=population,
            p_acquiescence=p_acquiescence,
            class_consciousness=class_consciousness,
        )

    EpistemicHorizonSystem().step(graph, ServiceContainer.create(), TickContext())

    attrs = graph.get_node("T001").attributes
    assert 0.0 <= attrs["mass_receptivity"] <= 1.0


@given(tenants=st.lists(_TENANT_STRATEGY, min_size=1, max_size=3))
@settings(max_examples=25, deadline=None)
def test_vision_state_matches_threshold_table(
    tenants: list[tuple[SocialRole, float, float, float]],
) -> None:
    """L3: vision_state is a pure function of M_r against the threshold table."""
    graph = BabylonGraph()
    _territory(graph, "T001")
    for i, (role, population, p_acquiescence, class_consciousness) in enumerate(tenants):
        _tenant(
            graph,
            f"C{i:03d}",
            "T001",
            role=str(role),
            population=population,
            p_acquiescence=p_acquiescence,
            class_consciousness=class_consciousness,
        )

    EpistemicHorizonSystem().step(graph, ServiceContainer.create(), TickContext())

    attrs = graph.get_node("T001").attributes
    mass_receptivity = attrs["mass_receptivity"]
    vision_state = attrs["vision_state"]
    if mass_receptivity < _DEFAULT_DESERT_THRESHOLD:
        assert vision_state == "desert"
    elif mass_receptivity >= _DEFAULT_WATER_THRESHOLD:
        assert vision_state == "water"
    else:
        assert vision_state == "mud"


@given(
    investigation_intel=st.floats(
        min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False
    ),
    grant_cadre_presence=st.booleans(),
    p_acquiescence=_UNIT_FLOAT,
    class_consciousness=_UNIT_FLOAT,
)
@settings(max_examples=25, deadline=None)
def test_intel_confidence_is_clamped_to_unit_interval(
    investigation_intel: float,
    grant_cadre_presence: bool,
    p_acquiescence: float,
    class_consciousness: float,
) -> None:
    """L4: I_c = max(0, min(1, B_o + C_p*M_r + intel)) regardless of magnitude."""
    graph = BabylonGraph()
    _territory(graph, "T001")
    _tenant(
        graph,
        "C001",
        "T001",
        role=str(SocialRole.PERIPHERY_PROLETARIAT),
        population=1000.0,
        p_acquiescence=p_acquiescence,
        class_consciousness=class_consciousness,
    )
    if grant_cadre_presence:
        _player_org_presence(graph, "ORG001", "T001")
    graph.update_node("T001", investigation_intel=investigation_intel)

    EpistemicHorizonSystem().step(graph, ServiceContainer.create(), TickContext())

    attrs = graph.get_node("T001").attributes
    assert 0.0 <= attrs["intel_confidence"] <= 1.0
