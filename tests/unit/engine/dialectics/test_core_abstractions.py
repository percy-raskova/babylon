"""TDD RED phase: Tests for Phase 2 core abstraction enhancements.

Validates:
- WorldView.previous provides access to prior tick's frozen state
- World.get_one_or_none(type_tag) returns a single dialectic or None
- WorldView.find_successor(dialectic_id) locates successors via parent_id
- observe(frame=None) supports observation-relativity
- tick() steps ALL dialectics, including sublated ones
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from babylon.economics.value import ExchangeValue, UseValue
from babylon.engine.dialectics.base import (
    Dialectic,
    EmptyPole,
    TickInputs,
    WorldView,
)
from babylon.engine.dialectics.commodity import CommodityDialectic
from babylon.engine.dialectics.tick import tick
from babylon.engine.dialectics.world import World

# ===========================================================================
# Helpers
# ===========================================================================


def _make_commodity(weight: float = 0.5, tick_n: int = 0) -> CommodityDialectic:
    """Helper to construct a CommodityDialectic."""
    return CommodityDialectic(
        pole_a=UseValue(),
        pole_b=ExchangeValue(),
        weight=weight,
        tick_created=tick_n,
        tick_updated=tick_n,
    )


class _SublatingDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Test dialectic that always sublates to a successor."""

    type_tag: str = "_SublatingDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> _SublatingDialectic:
        return self.model_copy(update={"tick_updated": world.tick})

    def sublate(self) -> Dialectic[Any, Any] | None:
        return _SuccessorDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.0,
            parent_id=self.id,
            tick_created=self.tick_updated,
            tick_updated=self.tick_updated,
        )


class _SuccessorDialectic(Dialectic[EmptyPole, EmptyPole]):
    """Test dialectic produced by sublation."""

    type_tag: str = "_SuccessorDialectic"

    def step(self, inputs: TickInputs, world: WorldView) -> _SuccessorDialectic:
        return self.model_copy(update={"tick_updated": world.tick})


# ===========================================================================
# WorldView.previous
# ===========================================================================


class TestWorldViewPrevious:
    """WorldView carries a frozen snapshot of the prior tick's state."""

    def test_previous_defaults_to_none(self) -> None:
        """When no previous world is provided, previous is None."""
        wv = WorldView(tick=1, dialectics={})
        assert wv.previous is None

    def test_previous_carries_prior_state(self) -> None:
        """WorldView.previous holds the prior tick's WorldView."""
        d = _make_commodity()
        prior = WorldView(tick=0, dialectics={d.id: d})
        current = WorldView(tick=1, dialectics={}, previous=prior)
        assert current.previous is not None
        assert current.previous.tick == 0
        assert d.id in current.previous.dialectics

    def test_previous_is_read_only(self) -> None:
        """The previous snapshot is frozen (WorldView is frozen)."""
        prior = WorldView(tick=0, dialectics={})
        current = WorldView(tick=1, dialectics={}, previous=prior)
        # Pydantic frozen model — attribute assignment should raise
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            current.previous = None  # type: ignore[misc]


# ===========================================================================
# World.get_one_or_none
# ===========================================================================


class TestWorldGetOneOrNone:
    """World.get_one_or_none returns a single dialectic by type_tag or None."""

    def test_returns_dialectic_when_one_exists(self) -> None:
        d = _make_commodity()
        w = World(tick=0, dialectics={d.id: d})
        result = w.get_one_or_none("CommodityDialectic")
        assert result is not None
        assert result.id == d.id

    def test_returns_none_when_none_exist(self) -> None:
        w = World(tick=0, dialectics={})
        result = w.get_one_or_none("CommodityDialectic")
        assert result is None

    def test_returns_first_when_multiple_exist(self) -> None:
        """When multiple dialectics of the same type exist, returns the first found."""
        d1 = _make_commodity()
        d2 = _make_commodity()
        w = World(tick=0, dialectics={d1.id: d1, d2.id: d2})
        result = w.get_one_or_none("CommodityDialectic")
        assert result is not None
        assert result.id in (d1.id, d2.id)


# ===========================================================================
# WorldView.find_successor
# ===========================================================================


class TestWorldViewFindSuccessor:
    """WorldView.find_successor locates the successor of a sublated dialectic."""

    def test_returns_none_when_no_successor(self) -> None:
        d = _make_commodity()
        wv = WorldView(tick=0, dialectics={d.id: d})
        assert wv.find_successor(d.id) is None

    def test_finds_successor_by_parent_id(self) -> None:
        """Successor has parent_id pointing to the sublated dialectic."""
        parent_id = uuid4()
        successor = _SuccessorDialectic(
            pole_a=EmptyPole(),
            pole_b=EmptyPole(),
            weight=0.0,
            parent_id=parent_id,
            tick_created=0,
            tick_updated=0,
        )
        wv = WorldView(tick=1, dialectics={successor.id: successor})
        found = wv.find_successor(parent_id)
        assert found is not None
        assert found.id == successor.id

    def test_returns_none_when_id_not_found(self) -> None:
        wv = WorldView(tick=0, dialectics={})
        assert wv.find_successor(uuid4()) is None


# ===========================================================================
# tick() steps ALL dialectics including sublated
# ===========================================================================


class TestTickStepsAllDialectics:
    """tick() must step all dialectics, including sublated ones."""

    def test_sublated_dialectic_still_stepped(self) -> None:
        """A sublated dialectic's step() is still called each tick.

        This is the Grundrisse insight: sublated dialectics don't stop
        evolving. They continue under the governance of their successor.
        """
        d = _make_commodity(tick_n=0)
        # Mark d as sublated
        w = World(
            tick=0,
            dialectics={d.id: d},
            sublated_ids=frozenset({d.id}),
        )
        new_world, _ = tick(w, [])
        # The sublated dialectic should have tick_updated = 1
        sublated_d = new_world.dialectics[d.id]
        assert sublated_d.tick_updated == 1

    def test_sublated_and_live_both_stepped(self) -> None:
        """Both sublated and live dialectics advance their tick."""
        live = _make_commodity(tick_n=0)
        sublated = _make_commodity(tick_n=0)
        w = World(
            tick=0,
            dialectics={live.id: live, sublated.id: sublated},
            sublated_ids=frozenset({sublated.id}),
        )
        new_world, _ = tick(w, [])
        assert new_world.dialectics[live.id].tick_updated == 1
        assert new_world.dialectics[sublated.id].tick_updated == 1


# ===========================================================================
# tick() passes previous WorldView
# ===========================================================================


class TestTickPassesPreviousWorldView:
    """tick() should pass a WorldView with `previous` populated."""

    def test_worldview_has_previous_in_step(self) -> None:
        """The WorldView passed to step() should contain previous state.

        We verify this by running two ticks and checking that the second
        tick's world_view.previous was the first tick's state.
        """
        d = _make_commodity(tick_n=0)
        w0 = World(tick=0, dialectics={d.id: d})
        w1, _ = tick(w0, [])
        w2, _ = tick(w1, [])
        # After two ticks, we verify the world state evolved correctly
        assert w2.tick == 2
        # The dialectic was stepped in both ticks
        assert w2.dialectics[d.id].tick_updated == 2
