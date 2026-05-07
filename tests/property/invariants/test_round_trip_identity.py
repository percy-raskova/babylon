"""Property-based tests for the WorldState graph round-trip identity bound
invariant (INV-012 / spec-055 US4).

See ``specs/055-topology-invariants/contracts/round_trip_identity.md`` for
the full predicate specification. Encodes Constitution II.6 (State is
Data, Engine is Transformation) — the round-trip is the operational
definition of "State is Data."

Three predicates:

  Predicate A — round-trip preserves model_dump exactly (T022)
  Predicate B — round-trip works at maximum supported size (T023)
  Predicate C — every legal EdgeType round-trips faithfully (T024)
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings

from babylon.models.entities.relationship import Relationship
from babylon.models.entities.social_class import SocialClass
from babylon.models.enums import EdgeType, SocialRole
from babylon.models.world_state import (
    SOCIAL_CLASS_COMPUTED_FIELDS,
    TERRITORY_EXCLUDED_FIELDS,
    WorldState,
)
from tests.property.strategies.worldstate import worldstate_strategy

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _build_exclude_paths_from_production() -> dict[str, set]:
    """Read the from_graph exclude rules from production at runtime.

    Pydantic v2's ``model_dump(exclude=...)`` accepts nested-path dicts.
    Maps top-level WorldState fields to per-element exclude sets:

        {
            "tick": True,                                  # whole field
            "entities": {"__all__": SOCIAL_CLASS_COMPUTED_FIELDS},
            "territories": {"__all__": TERRITORY_EXCLUDED_FIELDS},
        }

    Reading from production guarantees that any future addition to the
    computed-field sets in ``world_state.py`` is reflected automatically
    (FR-010 — single source of truth).
    """
    return {
        "tick": True,
        "entities": {"__all__": set(SOCIAL_CLASS_COMPUTED_FIELDS)},
        "territories": {"__all__": set(TERRITORY_EXCLUDED_FIELDS)},
    }


def _normalize_relationships_order(dump: dict) -> dict:
    """Sort the relationships list in a model_dump for order-insensitive comparison.

    The ``WorldState.from_graph()`` round-trip is order-lossy on the
    relationships list because ``nx.DiGraph.edges()`` does not guarantee
    insertion order. The contract is multiset-equality on relationships,
    not list-equality; this helper normalizes both pre and post dumps
    by sorting relationships under a stable key.
    """
    if "relationships" in dump and isinstance(dump["relationships"], list):
        dump = dict(dump)
        dump["relationships"] = sorted(
            dump["relationships"],
            key=lambda r: (
                r.get("source_id", ""),
                r.get("target_id", ""),
                str(r.get("edge_type", "")),
            ),
        )
    return dump


def _build_state_with_one_edge_per_type() -> WorldState:
    """Construct a WorldState with one Relationship per legal EdgeType."""
    edge_types = list(EdgeType)
    # Need enough entities so source != target for each edge
    n_entities = max(2, len(edge_types) + 1)
    entities: dict[str, SocialClass] = {}
    for i in range(n_entities):
        eid = f"C{i:03d}"
        entities[eid] = SocialClass(
            id=eid,
            name=f"Entity {i}",
            role=SocialRole.PERIPHERY_PROLETARIAT,
            wealth=10.0,
        )
    entity_ids = list(entities.keys())
    relationships: list[Relationship] = []
    for i, edge_type in enumerate(edge_types):
        src = entity_ids[i % len(entity_ids)]
        tgt = entity_ids[(i + 1) % len(entity_ids)]
        relationships.append(
            Relationship(
                source_id=src,
                target_id=tgt,
                edge_type=edge_type,
                value_flow=1.0,
                tension=0.5,
            )
        )
    return WorldState(tick=0, entities=entities, relationships=relationships)


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestRoundTripIdentity:
    """INV-012: from_graph(state.to_graph()) preserves model_dump exactly."""

    @given(state=worldstate_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_round_trip_preserves_model_dump(self, state: WorldState) -> None:
        """Predicate A: round-trip preserves model_dump (modulo computed fields)."""
        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=state.tick)
        exclude = _build_exclude_paths_from_production()
        pre_dump = _normalize_relationships_order(state.model_dump(exclude=exclude))
        post_dump = _normalize_relationships_order(restored.model_dump(exclude=exclude))
        assert post_dump == pre_dump

    @given(state=worldstate_strategy(max_entities=8, max_relationships=8))
    @settings(
        max_examples=20,
        deadline=2000,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_round_trip_at_max_size(self, state: WorldState) -> None:
        """Predicate B: round-trip on larger states still preserves model_dump."""
        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=state.tick)
        exclude = _build_exclude_paths_from_production()
        pre_dump = _normalize_relationships_order(state.model_dump(exclude=exclude))
        post_dump = _normalize_relationships_order(restored.model_dump(exclude=exclude))
        assert post_dump == pre_dump

    def test_round_trip_preserves_every_edge_type(self) -> None:
        """Predicate C: every legal EdgeType round-trips faithfully."""
        state = _build_state_with_one_edge_per_type()
        graph = state.to_graph()
        restored = WorldState.from_graph(graph, tick=state.tick)

        pre_edge_types = sorted(rel.edge_type for rel in state.relationships)
        post_edge_types = sorted(rel.edge_type for rel in restored.relationships)
        assert pre_edge_types == post_edge_types

        # Per-edge field-level equality (matched by source/target/edge_type)
        pre_index = {(r.source_id, r.target_id, r.edge_type): r for r in state.relationships}
        post_index = {(r.source_id, r.target_id, r.edge_type): r for r in restored.relationships}
        assert pre_index.keys() == post_index.keys()
        for key, pre_rel in pre_index.items():
            post_rel = post_index[key]
            assert pre_rel.value_flow == pytest.approx(post_rel.value_flow)
            assert pre_rel.tension == pytest.approx(post_rel.tension)
