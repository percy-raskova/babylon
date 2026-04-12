"""TDD RED phase: Tests for CommodityDialectic (V1 Ch1).

The CommodityDialectic models the use-value ↔ exchange-value contradiction.
Weight reflects whether the commodity is currently being held for use or
for exchange. Motion: production events shift weight toward exchange;
consumption events shift toward use.

Tests validate:
- UseValue and ExchangeValue pole construction
- CommodityDialectic type_tag
- step() shifts weight based on production/consumption inputs
- observe() returns commodity-specific measurements
- invariants() checks SNLT >= 0
- sublate() returns None (commodities don't sublate in Phase 1)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.value import ExchangeValue, UseValue
from babylon.engine.dialectics.base import TickInputs, WorldView
from babylon.engine.dialectics.volume_1 import CommodityDialectic

# ===========================================================================
# Pole Tests
# ===========================================================================


class TestUseValue:
    """UseValue pole construction and validation."""

    def test_default_construction(self) -> None:
        uv = UseValue()
        assert uv.utility >= 0.0
        assert uv.demand >= 0.0

    def test_custom_values(self) -> None:
        uv = UseValue(utility=0.8, demand=120.0)
        assert uv.utility == 0.8
        assert uv.demand == 120.0

    def test_utility_bounded_0_1(self) -> None:
        with pytest.raises(ValidationError):
            UseValue(utility=-0.1)
        with pytest.raises(ValidationError):
            UseValue(utility=1.1)


class TestExchangeValue:
    """ExchangeValue pole construction and validation."""

    def test_default_construction(self) -> None:
        ev = ExchangeValue()
        assert ev.price >= 0.0
        assert ev.snlt >= 0.0

    def test_custom_values(self) -> None:
        ev = ExchangeValue(price=50.0, snlt=40.0)
        assert ev.price == 50.0
        assert ev.snlt == 40.0

    def test_snlt_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ExchangeValue(snlt=-1.0)

    def test_price_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ExchangeValue(price=-1.0)


# ===========================================================================
# CommodityDialectic Tests
# ===========================================================================


class TestCommodityDialecticConstruction:
    """Construction and type identity."""

    def test_type_tag(self) -> None:
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert cd.type_tag == "CommodityDialectic"

    def test_poles_accessible(self) -> None:
        cd = CommodityDialectic(
            pole_a=UseValue(utility=0.9, demand=100.0),
            pole_b=ExchangeValue(price=50.0, snlt=40.0),
            weight=0.6,
            tick_created=0,
            tick_updated=0,
        )
        assert cd.pole_a.utility == 0.9
        assert cd.pole_b.price == 50.0


class TestCommodityDialecticStep:
    """Motion law: production shifts toward exchange, consumption toward use."""

    def test_production_input_shifts_toward_exchange(self) -> None:
        """Production event shifts weight toward exchange (weight increases, toward B)."""
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs(upstream={cd.id: {"event": "production", "intensity": 0.1}})
        world = WorldView(tick=1, dialectics={})
        result = cd.step(inputs, world)
        assert isinstance(result, CommodityDialectic)
        # Production shifts toward exchange: weight increases
        assert result.weight > cd.weight

    def test_consumption_input_shifts_toward_use(self) -> None:
        """Consumption event shifts weight toward use (weight decreases, toward A)."""
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs(upstream={cd.id: {"event": "consumption", "intensity": 0.1}})
        world = WorldView(tick=1, dialectics={})
        result = cd.step(inputs, world)
        assert isinstance(result, CommodityDialectic)
        # Consumption shifts toward use: weight decreases
        assert result.weight < cd.weight

    def test_no_input_preserves_weight(self) -> None:
        """No upstream input means no change in weight."""
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs()
        world = WorldView(tick=1, dialectics={})
        result = cd.step(inputs, world)
        assert result.weight == cd.weight

    def test_step_updates_tick_updated(self) -> None:
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        result = cd.step(TickInputs(), WorldView(tick=1, dialectics={}))
        assert result.tick_updated == 1

    def test_weight_clamped_at_negative_one(self) -> None:
        """Consumption can't push weight below -1."""
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=-0.99,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs(upstream={cd.id: {"event": "consumption", "intensity": 1.0}})
        result = cd.step(inputs, WorldView(tick=1, dialectics={}))
        assert result.weight >= -1.0

    def test_weight_clamped_at_positive_one(self) -> None:
        """Production can't push weight above 1."""
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=0.99,
            tick_created=0,
            tick_updated=0,
        )
        inputs = TickInputs(upstream={cd.id: {"event": "production", "intensity": 1.0}})
        result = cd.step(inputs, WorldView(tick=1, dialectics={}))
        assert result.weight <= 1.0


class TestCommodityDialecticObserve:
    """Observation projection for frontend."""

    def test_observe_includes_commodity_fields(self) -> None:
        cd = CommodityDialectic(
            pole_a=UseValue(utility=0.8, demand=100.0),
            pole_b=ExchangeValue(price=50.0, snlt=40.0),
            weight=0.7,
            tick_created=0,
            tick_updated=0,
        )
        obs = cd.observe()
        assert obs["type"] == "CommodityDialectic"
        assert obs["weight"] == 0.7
        assert "utility" in obs
        assert "price" in obs
        assert "snlt" in obs
        assert obs["utility"] == 0.8
        assert obs["price"] == 50.0
        assert obs["snlt"] == 40.0


class TestCommodityDialecticSublation:
    """Phase 1: commodities don't sublate."""

    def test_sublate_returns_none(self) -> None:
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert cd.sublate() is None


class TestCommodityDialecticInvariants:
    """Invariant checks."""

    def test_valid_state_no_violations(self) -> None:
        cd = CommodityDialectic(
            pole_a=UseValue(),
            pole_b=ExchangeValue(snlt=10.0),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert cd.invariants() == []
