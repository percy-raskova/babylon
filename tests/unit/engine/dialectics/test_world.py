"""TDD RED phase: Tests for World, Morphism, and WorldEvent models.

Validates:
- World construction with dialectics and morphisms
- Morphism typed relationships (feeds, constrains, etc.)
- WorldEvent event recording
- World.get_by_type() filtering
- World.get_inputs_for() computes TickInputs from morphisms
- World.get_live_dialectics() excludes sublated
"""

from __future__ import annotations

from uuid import uuid4

from babylon.engine.dialectics.base import TickInputs
from babylon.engine.dialectics.volume_1 import (
    CommodityDialectic,
    ExchangeValue,
    UseValue,
)
from babylon.engine.dialectics.world import Morphism, World, WorldEvent


def _make_commodity(weight: float = 0.5, tick: int = 0) -> CommodityDialectic:
    """Helper to construct a CommodityDialectic."""
    return CommodityDialectic(
        pole_a=UseValue(),
        pole_b=ExchangeValue(),
        weight=weight,
        tick_created=tick,
        tick_updated=tick,
    )


# ===========================================================================
# Morphism Tests
# ===========================================================================


class TestMorphism:
    """Typed relationship between two dialectics."""

    def test_construction(self) -> None:
        src = uuid4()
        tgt = uuid4()
        m = Morphism(source_id=src, target_id=tgt, relation="feeds", weight=1.0)
        assert m.source_id == src
        assert m.target_id == tgt
        assert m.relation == "feeds"
        assert m.weight == 1.0

    def test_valid_relations(self) -> None:
        """All five canonical relation types should be valid."""
        src, tgt = uuid4(), uuid4()
        for rel in ("feeds", "constrains", "transforms", "contains", "antagonizes"):
            m = Morphism(source_id=src, target_id=tgt, relation=rel, weight=0.5)
            assert m.relation == rel

    def test_has_id(self) -> None:
        m = Morphism(source_id=uuid4(), target_id=uuid4(), relation="feeds", weight=1.0)
        assert m.id is not None


# ===========================================================================
# WorldEvent Tests
# ===========================================================================


class TestWorldEvent:
    """Event recording for sublations, crises, etc."""

    def test_construction(self) -> None:
        evt = WorldEvent(
            event_type="sublation",
            dialectic_id=uuid4(),
            payload={"reason": "test"},
        )
        assert evt.event_type == "sublation"
        assert evt.payload["reason"] == "test"

    def test_narrative_optional(self) -> None:
        evt = WorldEvent(event_type="crisis", payload={})
        assert evt.narrative is None

    def test_narrative_present(self) -> None:
        evt = WorldEvent(
            event_type="crisis",
            payload={},
            narrative="The rate of profit fell below threshold.",
        )
        assert evt.narrative is not None


# ===========================================================================
# World Tests
# ===========================================================================


class TestWorldConstruction:
    """World construction and basic access."""

    def test_empty_world(self) -> None:
        w = World(tick=0)
        assert w.tick == 0
        assert len(w.dialectics) == 0
        assert len(w.morphisms) == 0
        assert len(w.events) == 0

    def test_world_with_dialectics(self) -> None:
        d1 = _make_commodity()
        d2 = _make_commodity()
        w = World(
            tick=1,
            dialectics={d1.id: d1, d2.id: d2},
        )
        assert len(w.dialectics) == 2

    def test_world_with_morphisms(self) -> None:
        d1 = _make_commodity()
        d2 = _make_commodity()
        m = Morphism(
            source_id=d1.id,
            target_id=d2.id,
            relation="feeds",
            weight=1.0,
        )
        w = World(
            tick=1,
            dialectics={d1.id: d1, d2.id: d2},
            morphisms=[m],
        )
        assert len(w.morphisms) == 1


class TestWorldGetByType:
    """Filter dialectics by type_tag."""

    def test_get_by_type_returns_matching(self) -> None:
        d1 = _make_commodity()
        d2 = _make_commodity()
        w = World(tick=0, dialectics={d1.id: d1, d2.id: d2})
        result = w.get_by_type("CommodityDialectic")
        assert len(result) == 2

    def test_get_by_type_empty_for_unknown(self) -> None:
        d1 = _make_commodity()
        w = World(tick=0, dialectics={d1.id: d1})
        result = w.get_by_type("NonexistentDialectic")
        assert len(result) == 0


class TestWorldGetInputsFor:
    """Compute TickInputs for a target dialectic from the morphism graph."""

    def test_inputs_from_feeds_morphism(self) -> None:
        d1 = _make_commodity(weight=0.8)
        d2 = _make_commodity(weight=0.3)
        m = Morphism(
            source_id=d1.id,
            target_id=d2.id,
            relation="feeds",
            weight=1.0,
        )
        w = World(
            tick=0,
            dialectics={d1.id: d1, d2.id: d2},
            morphisms=[m],
        )
        inputs = w.get_inputs_for(d2.id)
        assert isinstance(inputs, TickInputs)
        assert d1.id in inputs.upstream

    def test_no_inputs_when_no_morphisms(self) -> None:
        d1 = _make_commodity()
        w = World(tick=0, dialectics={d1.id: d1})
        inputs = w.get_inputs_for(d1.id)
        assert len(inputs.upstream) == 0


class TestWorldGetLiveDialectics:
    """Live dialectics = not yet sublated."""

    def test_all_live_when_no_sublation(self) -> None:
        d1 = _make_commodity()
        d2 = _make_commodity()
        w = World(tick=0, dialectics={d1.id: d1, d2.id: d2})
        live = w.get_live_dialectics()
        assert len(live) == 2

    def test_sublated_excluded(self) -> None:
        """Dialectics with a parent_id (produced by sublation) should
        still be returned — but predecessors that have been replaced
        should not. This is tracked via the sublated_ids set on World."""
        d1 = _make_commodity()
        d2 = _make_commodity()
        w = World(
            tick=0,
            dialectics={d1.id: d1, d2.id: d2},
            sublated_ids=frozenset({d1.id}),
        )
        live = w.get_live_dialectics()
        assert len(live) == 1
        assert d2.id in live
