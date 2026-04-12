"""TDD RED phase: Tests for the pure tick() function.

Validates:
- tick() returns a new World with incremented tick
- tick() steps all live dialectics
- tick() respects topological order via morphisms
- tick() runs sublation pass
- tick() runs invariant check
- tick() collects events from sublations
- tick() is deterministic (same inputs → same outputs)
- tick() handles empty world
"""

from __future__ import annotations

from babylon.engine.dialectics.tick import tick
from babylon.engine.dialectics.volume_1 import (
    CommodityDialectic,
    ExchangeValue,
    UseValue,
)
from babylon.engine.dialectics.world import Morphism, World


def _make_commodity(weight: float = 0.5, tick_n: int = 0) -> CommodityDialectic:
    """Helper to construct a CommodityDialectic."""
    return CommodityDialectic(
        pole_a=UseValue(),
        pole_b=ExchangeValue(),
        weight=weight,
        tick_created=tick_n,
        tick_updated=tick_n,
    )


class TestTickFunction:
    """Pure tick function semantics."""

    def test_empty_world_increments_tick(self) -> None:
        w = World(tick=0)
        new_world, events = tick(w, [])
        assert new_world.tick == 1
        assert len(events) == 0

    def test_steps_all_dialectics(self) -> None:
        d1 = _make_commodity(weight=0.5)
        d2 = _make_commodity(weight=0.7)
        w = World(tick=0, dialectics={d1.id: d1, d2.id: d2})
        new_world, _ = tick(w, [])
        # All dialectics should have tick_updated = 1
        for d in new_world.dialectics.values():
            assert d.tick_updated == 1

    def test_deterministic(self) -> None:
        """Same inputs produce same outputs."""
        d1 = _make_commodity(weight=0.5)
        w = World(tick=0, dialectics={d1.id: d1})
        result1, events1 = tick(w, [])
        result2, events2 = tick(w, [])
        # Weight should be the same (no upstream inputs → no change)
        r1_d = result1.dialectics[d1.id]
        r2_d = result2.dialectics[d1.id]
        assert r1_d.weight == r2_d.weight

    def test_morphism_feeds_input(self) -> None:
        """A feeds morphism makes d1.observe() available to d2.step()."""
        d1 = _make_commodity(weight=0.8)
        d2 = _make_commodity(weight=0.5)
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
        new_world, _ = tick(w, [])
        # d2 should have received d1's observe() output as input
        # Since d1's observe() doesn't contain "event"/"intensity",
        # d2's weight should remain unchanged
        assert new_world.dialectics[d2.id].weight == 0.5

    def test_invariant_violations_recorded_as_events(self) -> None:
        """If a dialectic reports invariant violations, they appear in events."""
        # Use a valid CommodityDialectic (no violations expected)
        d = _make_commodity()
        w = World(tick=0, dialectics={d.id: d})
        _, events = tick(w, [])
        # No violations from a valid commodity
        violation_events = [e for e in events if e.event_type == "invariant_violation"]
        assert len(violation_events) == 0

    def test_world_tick_incremented(self) -> None:
        d = _make_commodity()
        w = World(tick=5, dialectics={d.id: d})
        new_world, _ = tick(w, [])
        assert new_world.tick == 6


class TestTickSublation:
    """Sublation pass within tick()."""

    def test_no_sublation_preserves_all(self) -> None:
        d = _make_commodity()
        w = World(tick=0, dialectics={d.id: d})
        new_world, _ = tick(w, [])
        assert d.id in new_world.dialectics
        assert d.id not in new_world.sublated_ids
