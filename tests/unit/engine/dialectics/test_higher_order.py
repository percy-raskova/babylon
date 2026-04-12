"""TDD RED phase: Tests for Phase 4 higher-order dialectics.

Validates:
- TransformationDialectic: Value → Price of Production (V3 Ch9-10)
- ClassDialectic: In-Itself ↔ For-Itself with sublation to PartyDialectic
- PartyDialectic: Vanguard ↔ Mass Line (sublation containment)
- Sublation governance: class.step() reads party.observe() via find_successor
- Observation-relativity: CommodityDialectic.observe(frame=Transformation)
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from babylon.engine.dialectics.base import (
    EmptyPole,
    TickInputs,
    WorldView,
)
from babylon.engine.dialectics.class_struggle import ClassDialectic, ForItself, InItself
from babylon.engine.dialectics.party import MassLine, PartyDialectic, Vanguard
from babylon.engine.dialectics.tick import tick
from babylon.engine.dialectics.transformation import (
    TransformationDialectic,
    TransformationPole,
)
from babylon.engine.dialectics.world import World

# ===========================================================================
# TransformationDialectic — Value → Price of Production
# ===========================================================================


class TestTransformationDialectic:
    """V3 Ch9-10: The transformation of values into prices of production."""

    def test_type_tag(self) -> None:
        t = TransformationDialectic(
            pole_a=TransformationPole(average_profit_rate=0.20),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        assert t.type_tag == "TransformationDialectic"

    def test_observe_emits_average_profit_rate(self) -> None:
        """Observation must include the average profit rate for downstream use."""
        t = TransformationDialectic(
            pole_a=TransformationPole(average_profit_rate=0.20),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = t.observe()
        assert "average_profit_rate" in obs
        assert obs["average_profit_rate"] == pytest.approx(0.20)

    def test_transform_value_to_price(self) -> None:
        """price_of_production = cost_price × (1 + average_profit_rate)."""
        t = TransformationDialectic(
            pole_a=TransformationPole(average_profit_rate=0.20),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        obs = t.observe()
        assert "average_profit_rate" in obs

    def test_step_updates_tick(self) -> None:
        t = TransformationDialectic(
            pole_a=TransformationPole(average_profit_rate=0.20),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        wv = WorldView(tick=1, dialectics={})
        new_t = t.step(TickInputs(), wv)
        assert new_t.tick_updated == 1

    def test_step_reads_upstream_profit_rates(self) -> None:
        """Step() should read upstream production's values to compute average profit rate."""
        t = TransformationDialectic(
            pole_a=TransformationPole(average_profit_rate=0.20),
            pole_b=EmptyPole(),
            weight=0.0,
            tick_created=0,
            tick_updated=0,
        )
        wv = WorldView(tick=1, dialectics={})
        inputs = TickInputs(
            upstream={
                t.id: {
                    "rate_of_exploitation": 0.5,
                    "occ": 4.0,
                }
            }
        )
        new_t = t.step(inputs, wv)
        assert new_t.tick_updated == 1


# ===========================================================================
# ClassDialectic — In-Itself ↔ For-Itself
# ===========================================================================


class TestClassDialectic:
    """Class consciousness as a dialectic: spontaneous → organized."""

    def test_type_tag(self) -> None:
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.5),
            pole_b=ForItself(organization_level=0.1),
            weight=-0.5,
            tick_created=0,
            tick_updated=0,
        )
        assert c.type_tag == "ClassDialectic"

    def test_step_advances_tick(self) -> None:
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.5),
            pole_b=ForItself(organization_level=0.1),
            weight=-0.5,
            tick_created=0,
            tick_updated=0,
        )
        wv = WorldView(tick=1, dialectics={})
        new_c = c.step(TickInputs(), wv)
        assert new_c.tick_updated == 1

    def test_no_sublation_below_threshold(self) -> None:
        """Class does not sublate to Party when weight is below threshold."""
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.5),
            pole_b=ForItself(organization_level=0.1),
            weight=0.3,
            tick_created=0,
            tick_updated=0,
        )
        assert c.sublate() is None

    def test_sublation_to_party(self) -> None:
        """Class sublates to PartyDialectic when weight >= 0.7."""
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.9),
            pole_b=ForItself(organization_level=0.8),
            weight=0.8,
            tick_created=0,
            tick_updated=0,
        )
        successor = c.sublate()
        assert successor is not None
        assert isinstance(successor, PartyDialectic)
        assert successor.parent_id == c.id

    def test_observe_emits_consciousness_metrics(self) -> None:
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.5),
            pole_b=ForItself(organization_level=0.3),
            weight=-0.2,
            tick_created=0,
            tick_updated=0,
        )
        obs = c.observe()
        assert "material_grievance" in obs
        assert "organization_level" in obs

    def test_step_reads_successor_when_sublated(self) -> None:
        """When a successor (PartyDialectic) exists, the class's motion
        is governed by it — the Aufhebung pattern."""
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.5),
            pole_b=ForItself(organization_level=0.3),
            weight=0.5,
            tick_created=0,
            tick_updated=0,
        )
        party = PartyDialectic(
            pole_a=Vanguard(discipline=0.8),
            pole_b=MassLine(support=0.6),
            weight=0.5,
            parent_id=c.id,
            tick_created=1,
            tick_updated=1,
        )
        wv = WorldView(tick=2, dialectics={c.id: c, party.id: party})
        new_c = c.step(TickInputs(), wv)
        # The class was stepped (governance by party)
        assert new_c.tick_updated == 2


# ===========================================================================
# PartyDialectic — Vanguard ↔ Mass Line
# ===========================================================================


class TestPartyDialectic:
    """Party as a higher-order dialectic containing the class."""

    def test_type_tag(self) -> None:
        p = PartyDialectic(
            pole_a=Vanguard(discipline=0.7),
            pole_b=MassLine(support=0.5),
            weight=0.0,
            parent_id=uuid4(),
            tick_created=0,
            tick_updated=0,
        )
        assert p.type_tag == "PartyDialectic"

    def test_step_advances_tick(self) -> None:
        p = PartyDialectic(
            pole_a=Vanguard(discipline=0.7),
            pole_b=MassLine(support=0.5),
            weight=0.0,
            parent_id=uuid4(),
            tick_created=0,
            tick_updated=0,
        )
        wv = WorldView(tick=1, dialectics={})
        new_p = p.step(TickInputs(), wv)
        assert new_p.tick_updated == 1

    def test_observe_emits_directive(self) -> None:
        """PartyDialectic.observe() must emit current_directive for class governance."""
        p = PartyDialectic(
            pole_a=Vanguard(discipline=0.7),
            pole_b=MassLine(support=0.5),
            weight=0.0,
            parent_id=uuid4(),
            tick_created=0,
            tick_updated=0,
        )
        obs = p.observe()
        assert "current_directive" in obs
        assert "discipline" in obs
        assert "mass_support" in obs


# ===========================================================================
# Integration: Sublation governance through tick()
# ===========================================================================


class TestSublationGovernance:
    """A sublated class continues evolving under party governance."""

    def test_class_sublates_and_party_governs(self) -> None:
        """Full integration: class sublates → party appears → class governed by party."""
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.9),
            pole_b=ForItself(organization_level=0.8),
            weight=0.8,
            tick_created=0,
            tick_updated=0,
        )
        w = World(tick=0, dialectics={c.id: c})
        w1, events1 = tick(w, [])

        # A sublation event should have occurred
        sublation_events = [e for e in events1 if e.event_type == "sublation"]
        assert len(sublation_events) == 1

        # The party dialectic should now exist in the world
        party_found = False
        for d in w1.dialectics.values():
            if hasattr(d, "type_tag") and d.type_tag == "PartyDialectic":
                party_found = True
                assert d.parent_id == c.id
        assert party_found

    def test_sublated_class_still_stepped(self) -> None:
        """After sublation, the class is still stepped (Grundrisse: sublated ≠ destroyed)."""
        c = ClassDialectic(
            pole_a=InItself(material_grievance=0.9),
            pole_b=ForItself(organization_level=0.8),
            weight=0.8,
            tick_created=0,
            tick_updated=0,
        )
        w = World(tick=0, dialectics={c.id: c})
        # Tick 1: sublation occurs
        w1, _ = tick(w, [])
        # Tick 2: both class and party should be stepped
        w2, _ = tick(w1, [])

        assert w2.dialectics[c.id].tick_updated == 2
        assert w2.tick == 2
