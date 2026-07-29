"""Behavioral laws for DoctrineSystem / compute_doctrine (P27 Phase-0 backfill, §8.4).

Read end-to-end before writing: ``src/babylon/engine/systems/doctrine.py``
(module docstring + ``compute_doctrine``/``step_organization``/
``_apply_deltas``/``_decay_mass_work_solidarity_edges``) and the pure mechanics
it calls in ``src/babylon/domain/doctrine/mechanics.py`` (``decay_tags``,
``accrue_theoretical_labor``, ``can_acquire``, ``acquire``).

Laws pinned (grounded in the source, not assumed):

  L1 -- org-less inactivity: a graph with no ORGANIZATION nodes is untouched by
       ``compute_doctrine`` -- it returns ``[]`` and never writes the
       ``political_form_org_positions`` graph attribute. Grounded:
       doctrine.py module docstring lines 39-43 ("all SIX [qa:regression]
       scenarios carry no organization nodes ... this system is a no-op --
       draws nothing, writes nothing, and publishes no
       political_form_org_positions register -- there"); the
       ``for node in graph.query_nodes(node_type=NodeType.ORGANIZATION)`` loop
       (doctrine.py:523) has nothing to iterate when no org nodes exist; and
       the ``if positions:`` guard before ``graph.set_graph_attr(...)``
       (doctrine.py:610-611, comment: "writing an empty register would
       fabricate one (III.11)").

  L2 -- theoretical_labor clamp: after one ordinary (non-congress) tick, every
       org's ``theoretical_labor`` stays >= 0. Grounded: the ``Organization``
       model declares the field ``ge=0.0`` as an invariant, not just an
       implementation detail (models/entities/organization.py:211-214);
       ``accrue_theoretical_labor`` returns ``0.0`` on non-positive surplus and
       otherwise a non-negative product (domain/doctrine/mechanics.py:291-294);
       ``can_acquire`` gates every deliberate spend on
       ``cost_tl <= theoretical_labor`` (domain/doctrine/mechanics.py:267); and
       the directed-study branch in ``step_organization`` only subtracts when
       affordable (doctrine.py:430-431: ``if tl >= target_node.cost_tl: tl -=
       target_node.cost_tl``).

  L3 -- acquired-set monotonicity across an ordinary tick: on a non-congress
       call, ``compute_doctrine`` never REMOVES an id from
       ``acquired_doctrine_ids`` -- the resulting set is a superset of the
       starting set. Grounded: ``mechanics.acquire()`` only appends, never
       removes (domain/doctrine/mechanics.py:270-278: "Return ``acquired_ids``
       with ``node_id`` appended"); the only place ids are shed is
       ``_resolve_line_struggle`` (doctrine.py:476-495, "consolidates ... shedding
       the earlier branches"), called EXCLUSIVELY inside the
       ``if is_congress and rng is not None:`` branch (doctrine.py:527), which a
       call with the default ``tick=0, rng=None`` never enters (``is_congress``
       requires ``tick > 0 and rng is not None``, doctrine.py:522).

  L4 -- graph-shape invariance: ``compute_doctrine`` only calls
       ``graph.update_node`` / ``graph.update_edge`` / ``graph.set_graph_attr``
       -- it never adds or removes a node or an edge. The node-id set and the
       ``(source, target, edge_type)`` edge-identity set are unchanged before
       and after a call. Grounded: reading ``compute_doctrine``
       (doctrine.py:498-612) and ``_decay_mass_work_solidarity_edges``
       (doctrine.py:116-139) end-to-end, the only graph-mutating calls are
       ``update_node``/``update_edge``/``set_graph_attr``; no ``add_node``,
       ``add_edge``, ``remove_node``, or ``remove_edge`` call appears anywhere
       in this module.

CAVEAT -- an EXPECTED law that is FALSE per the source: ``doctrine_tags`` are
  NOT floored at 0 by the ordinary tick loop. ``_apply_deltas``
  (doctrine.py:94-101) adds a node's signed ``tag_deltas`` onto the float
  accumulator with no clamp, and the shipped tree has genuinely negative
  deltas (``src/babylon/data/game/doctrine_tree_mvp.json``'s
  liquidationism-branch nodes carry e.g. ``"mass_link": -4``,
  ``"class_analysis": -3``, ``"militancy": -3``) -- so a tag CAN go negative
  in production play. The ``[0, 10]`` clamped range documented on
  ``DoctrineTag`` (models/enums/doctrine.py:16-21) describes a DIFFERENT
  function, ``babylon.domain.doctrine.tags.compute_tags``, which this
  system's tick loop never calls -- doctrine.py's imports pull only
  ``evaluate_trap_condition``/``load_doctrine_tree``, ``congress``, and
  ``mechanics``, never ``domain.doctrine.tags``. Recorded as a caveat, not a
  law; no test asserts tag non-negativity.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.config.defines.doctrine import DoctrineDefines
from babylon.domain.doctrine import load_doctrine_tree
from babylon.engine.actions._mass_work import apply_mass_work_solidarity
from babylon.engine.systems.doctrine import POLITICAL_FORM_POSITIONS_ATTR, compute_doctrine
from babylon.models.entities.doctrine import DoctrineTree
from babylon.models.entities.organization import PoliticalFaction
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import (
    ClassCharacter,
    ConsciousnessTendency,
    LegalStanding,
    OrgType,
    SocialRole,
)
from babylon.models.world_state import WorldState

pytestmark = pytest.mark.unit

#: The politics coefficients compute_doctrine needs (P25 U11): an unknown
#: @coeff reference fails loud, so every call site passes them. Values mirror
#: the PoliticsDefines defaults (same constant set test_doctrine_system.py
#: uses).
_COEFFS = {
    "solidarity_liquidation_floor": 0.05,
    "co_optive_liquidation_threshold": 0.6,
    "petty_bourgeois_liquidation_threshold": 0.6,
    "office_capture_rate": 0.02,
    "reformist_theory_decay": 0.02,
    "class_analysis_veto_decay": 0.03,
    "co_optive_dependence_drift": 0.02,
    "split_asset_retention": 0.4,
}


def _tree() -> DoctrineTree:
    return load_doctrine_tree()


def _defines() -> DoctrineDefines:
    return DoctrineDefines()


def _org(**overrides: object) -> PoliticalFaction:
    """The project's real Organization factory (WorldState.to_graph() is the
    only producer of ``_node_type`` -- never hand-stamp it)."""
    base: dict[str, object] = {
        "id": "vanguard",
        "name": "Vanguard Party",
        "org_type": OrgType.POLITICAL_FACTION,
        "class_character": ClassCharacter.PROLETARIAN,
        "ideology": "marxism-leninism",
        "cohesion": 0.5,
        "cadre_level": 0.5,
        "budget": 1000.0,
        "legal_standing": LegalStanding.UNDERGROUND,
        "consciousness_tendency": ConsciousnessTendency.REVOLUTIONARY,
    }
    base.update(overrides)
    return PoliticalFaction(**base)  # type: ignore[arg-type]


class TestOrgLessInactivity:
    """L1: no ORGANIZATION nodes -> no-op, no fabricated register."""

    def test_no_org_nodes_returns_empty_and_writes_no_register(self) -> None:
        state = WorldState(tick=0, entities={}, territories={}, relationships=[])
        graph = state.to_graph()
        events = compute_doctrine(graph, _defines(), _tree(), coeffs=_COEFFS)
        assert events == []
        assert graph.get_graph_attr(POLITICAL_FORM_POSITIONS_ATTR, None) is None

    def test_territory_only_graph_is_also_a_noop(self) -> None:
        # Mirrors the qa:regression goldens' shape: territories but zero orgs.
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={},
        )
        graph = state.to_graph()
        events = compute_doctrine(graph, _defines(), _tree(), coeffs=_COEFFS)
        assert events == []
        assert graph.get_graph_attr(POLITICAL_FORM_POSITIONS_ATTR, None) is None


class TestTheoreticalLaborClamp:
    """L2: theoretical_labor never goes negative across an ordinary tick."""

    @given(
        cadre_level=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        starting_tl=st.floats(min_value=0.0, max_value=500.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_tl_stays_non_negative(self, cadre_level: float, starting_tl: float) -> None:
        org = _org(cadre_level=cadre_level, theoretical_labor=starting_tl)
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": org},
        )
        graph = state.to_graph()
        compute_doctrine(graph, _defines(), _tree(), coeffs=_COEFFS)
        assert graph.nodes["vanguard"]["theoretical_labor"] >= 0.0

    @given(
        cadre_level=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        starting_tl=st.floats(min_value=0.0, max_value=500.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_tl_stays_non_negative_with_a_study_target(
        self, cadre_level: float, starting_tl: float
    ) -> None:
        # Directed study (Unit 7b): still only ever subtracts when affordable.
        org = _org(
            cadre_level=cadre_level,
            theoretical_labor=starting_tl,
            acquired_doctrine_ids=(_tree().root_id,),
            study_target_id="democratic_centralism",
        )
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": org},
        )
        graph = state.to_graph()
        compute_doctrine(graph, _defines(), _tree(), coeffs=_COEFFS)
        assert graph.nodes["vanguard"]["theoretical_labor"] >= 0.0


class TestAcquiredSetMonotonicity:
    """L3: an ordinary (non-congress) tick only ever appends to
    acquired_doctrine_ids -- it never sheds an id."""

    @given(
        cadre_level=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        starting_tl=st.floats(min_value=0.0, max_value=200.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_acquired_ids_are_a_superset_after_one_tick(
        self, cadre_level: float, starting_tl: float
    ) -> None:
        tree = _tree()
        # A non-trivial starting held set (real tree ids) so a shed would be
        # observable, not vacuously true from an empty start.
        starting = (tree.root_id, "trade_unionism", "abstention_boycott")
        org = _org(
            cadre_level=cadre_level,
            theoretical_labor=starting_tl,
            acquired_doctrine_ids=starting,
        )
        state = WorldState(
            tick=0,
            entities={},
            territories={},
            relationships=[],
            organizations={"vanguard": org},
        )
        graph = state.to_graph()
        before = set(graph.nodes["vanguard"]["acquired_doctrine_ids"])
        # Default tick=0, rng=None: is_congress is always False regardless of
        # the tick number passed (doctrine.py:522 requires rng is not None).
        compute_doctrine(graph, _defines(), tree, coeffs=_COEFFS)
        after = set(graph.nodes["vanguard"]["acquired_doctrine_ids"])
        assert before <= after


class TestGraphShapeInvariance:
    """L4: compute_doctrine mutates existing nodes/edges in place; it never
    adds or removes a node or an edge."""

    @given(
        cadre_level=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        starting_tl=st.floats(min_value=0.0, max_value=200.0, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_node_and_edge_identity_sets_are_unchanged(
        self, cadre_level: float, starting_tl: float
    ) -> None:
        defines = _defines()
        workers = SocialClass(id="C900", name="Workers", role=SocialRole.PERIPHERY_PROLETARIAT)
        org = _org(cadre_level=cadre_level, theoretical_labor=starting_tl)
        state = WorldState(
            tick=0,
            entities={"C900": workers},
            territories={},
            organizations={"vanguard": org},
        )
        graph = state.to_graph()
        # Real producer of the SOLIDARITY edge decayed by _decay_mass_work_solidarity_edges
        # (never hand-stamp an edge -- see test_ideology.py's rationale).
        apply_mass_work_solidarity(
            graph, "vanguard", dict(graph.nodes["vanguard"]), "C900", defines
        )

        before_nodes = set(graph.nodes)
        before_edges = {(e.source_id, e.target_id, e.edge_type) for e in graph.query_edges()}
        assert before_edges, "fixture invalid: expected the seeded SOLIDARITY edge"

        compute_doctrine(graph, defines, _tree(), coeffs=_COEFFS)

        after_nodes = set(graph.nodes)
        after_edges = {(e.source_id, e.target_id, e.edge_type) for e in graph.query_edges()}
        assert after_nodes == before_nodes
        assert after_edges == before_edges
