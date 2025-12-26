"""Tests for Pydantic event models.

Sprint 3.1+: Expanded event type hierarchy.

Tests verify:
- All event types can be instantiated with required fields
- Events are frozen (immutable)
- Events have correct default event_type
- Required field validation works
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from babylon.models.enums import EventType
from babylon.models.events import (
    ConsciousnessEvent,
    ContradictionEvent,
    CrisisEvent,
    EconomicEvent,
    # Concrete economic events
    ExtractionEvent,
    MassAwakeningEvent,
    # Concrete contradiction events
    RuptureEvent,
    # Base classes
    SimulationEvent,
    SolidaritySpikeEvent,
    # Concrete struggle events
    SparkEvent,
    StruggleEvent,
    SubsidyEvent,
    # Concrete consciousness events
    TransmissionEvent,
    UprisingEvent,
)

# =============================================================================
# Base Class Tests
# =============================================================================


class TestSimulationEvent:
    """Tests for SimulationEvent base class."""

    def test_simulation_event_requires_event_type(self) -> None:
        """SimulationEvent requires an event_type."""
        with pytest.raises(ValidationError):
            SimulationEvent(tick=0)  # type: ignore[call-arg]

    def test_simulation_event_requires_tick(self) -> None:
        """SimulationEvent requires a tick."""
        with pytest.raises(ValidationError):
            SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION)  # type: ignore[call-arg]

    def test_simulation_event_is_frozen(self) -> None:
        """SimulationEvent should be immutable (frozen)."""
        event = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=0)
        with pytest.raises(ValidationError):
            event.tick = 1  # type: ignore[misc]

    def test_simulation_event_has_timestamp_default(self) -> None:
        """SimulationEvent should auto-generate timestamp."""
        event = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=0)
        assert isinstance(event.timestamp, datetime)


class TestEconomicEvent:
    """Tests for EconomicEvent base class."""

    def test_economic_event_requires_amount(self) -> None:
        """EconomicEvent requires an amount field."""
        with pytest.raises(ValidationError):
            EconomicEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=0)  # type: ignore[call-arg]

    def test_economic_event_amount_must_be_non_negative(self) -> None:
        """EconomicEvent amount must be >= 0."""
        with pytest.raises(ValidationError):
            EconomicEvent(
                event_type=EventType.SURPLUS_EXTRACTION,
                tick=0,
                amount=-1.0,
            )


class TestConsciousnessEvent:
    """Tests for ConsciousnessEvent base class."""

    def test_consciousness_event_requires_target_id(self) -> None:
        """ConsciousnessEvent requires a target_id field."""
        with pytest.raises(ValidationError):
            ConsciousnessEvent(
                event_type=EventType.CONSCIOUSNESS_TRANSMISSION,
                tick=0,
            )  # type: ignore[call-arg]

    def test_consciousness_event_is_frozen(self) -> None:
        """ConsciousnessEvent should be immutable."""
        event = ConsciousnessEvent(
            event_type=EventType.CONSCIOUSNESS_TRANSMISSION,
            tick=0,
            target_id="C001",
        )
        with pytest.raises(ValidationError):
            event.target_id = "C002"  # type: ignore[misc]


class TestStruggleEvent:
    """Tests for StruggleEvent base class."""

    def test_struggle_event_requires_node_id(self) -> None:
        """StruggleEvent requires a node_id field."""
        with pytest.raises(ValidationError):
            StruggleEvent(
                event_type=EventType.EXCESSIVE_FORCE,
                tick=0,
            )  # type: ignore[call-arg]

    def test_struggle_event_is_frozen(self) -> None:
        """StruggleEvent should be immutable."""
        event = StruggleEvent(
            event_type=EventType.EXCESSIVE_FORCE,
            tick=0,
            node_id="C001",
        )
        with pytest.raises(ValidationError):
            event.node_id = "C002"  # type: ignore[misc]


class TestContradictionEvent:
    """Tests for ContradictionEvent base class."""

    def test_contradiction_event_requires_edge(self) -> None:
        """ContradictionEvent requires an edge field."""
        with pytest.raises(ValidationError):
            ContradictionEvent(
                event_type=EventType.RUPTURE,
                tick=0,
            )  # type: ignore[call-arg]

    def test_contradiction_event_is_frozen(self) -> None:
        """ContradictionEvent should be immutable."""
        event = ContradictionEvent(
            event_type=EventType.RUPTURE,
            tick=0,
            edge="C001->C002",
        )
        with pytest.raises(ValidationError):
            event.edge = "C003->C004"  # type: ignore[misc]


# =============================================================================
# Concrete Event Tests
# =============================================================================


class TestExtractionEvent:
    """Tests for ExtractionEvent (SURPLUS_EXTRACTION)."""

    def test_extraction_event_instantiation(self) -> None:
        """ExtractionEvent can be created with required fields."""
        event = ExtractionEvent(
            tick=5,
            source_id="C001",
            target_id="C002",
            amount=15.5,
        )
        assert event.event_type == EventType.SURPLUS_EXTRACTION
        assert event.tick == 5
        assert event.source_id == "C001"
        assert event.target_id == "C002"
        assert event.amount == 15.5
        assert event.mechanism == "imperial_rent"  # default

    def test_extraction_event_is_frozen(self) -> None:
        """ExtractionEvent should be immutable."""
        event = ExtractionEvent(
            tick=0,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        with pytest.raises(ValidationError):
            event.amount = 20.0  # type: ignore[misc]

    def test_extraction_event_default_event_type(self) -> None:
        """ExtractionEvent should default to SURPLUS_EXTRACTION."""
        event = ExtractionEvent(
            tick=0,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        assert event.event_type == EventType.SURPLUS_EXTRACTION


class TestSubsidyEvent:
    """Tests for SubsidyEvent (IMPERIAL_SUBSIDY)."""

    def test_subsidy_event_instantiation(self) -> None:
        """SubsidyEvent can be created with required fields."""
        event = SubsidyEvent(
            tick=5,
            source_id="C002",
            target_id="C003",
            amount=100.0,
            repression_boost=0.25,
        )
        assert event.event_type == EventType.IMPERIAL_SUBSIDY
        assert event.tick == 5
        assert event.source_id == "C002"
        assert event.target_id == "C003"
        assert event.amount == 100.0
        assert event.repression_boost == 0.25

    def test_subsidy_event_is_frozen(self) -> None:
        """SubsidyEvent should be immutable."""
        event = SubsidyEvent(
            tick=0,
            source_id="C002",
            target_id="C003",
            amount=50.0,
            repression_boost=0.1,
        )
        with pytest.raises(ValidationError):
            event.repression_boost = 0.5  # type: ignore[misc]

    def test_subsidy_event_default_event_type(self) -> None:
        """SubsidyEvent should default to IMPERIAL_SUBSIDY."""
        event = SubsidyEvent(
            tick=0,
            source_id="C002",
            target_id="C003",
            amount=50.0,
            repression_boost=0.1,
        )
        assert event.event_type == EventType.IMPERIAL_SUBSIDY


class TestCrisisEvent:
    """Tests for CrisisEvent (ECONOMIC_CRISIS)."""

    def test_crisis_event_instantiation(self) -> None:
        """CrisisEvent can be created with required fields."""
        event = CrisisEvent(
            tick=10,
            pool_ratio=0.15,
            aggregate_tension=0.7,
            decision="CRISIS",
            wage_delta=-0.05,
        )
        assert event.event_type == EventType.ECONOMIC_CRISIS
        assert event.tick == 10
        assert event.pool_ratio == 0.15
        assert event.aggregate_tension == 0.7
        assert event.decision == "CRISIS"
        assert event.wage_delta == -0.05

    def test_crisis_event_is_frozen(self) -> None:
        """CrisisEvent should be immutable."""
        event = CrisisEvent(
            tick=0,
            pool_ratio=0.2,
            aggregate_tension=0.5,
            decision="AUSTERITY",
            wage_delta=-0.02,
        )
        with pytest.raises(ValidationError):
            event.decision = "BRIBERY"  # type: ignore[misc]

    def test_crisis_event_default_event_type(self) -> None:
        """CrisisEvent should default to ECONOMIC_CRISIS."""
        event = CrisisEvent(
            tick=0,
            pool_ratio=0.1,
            aggregate_tension=0.9,
            decision="IRON_FIST",
            wage_delta=0.0,
        )
        assert event.event_type == EventType.ECONOMIC_CRISIS


class TestTransmissionEvent:
    """Tests for TransmissionEvent (CONSCIOUSNESS_TRANSMISSION)."""

    def test_transmission_event_instantiation(self) -> None:
        """TransmissionEvent can be created with required fields."""
        event = TransmissionEvent(
            tick=3,
            target_id="C001",
            source_id="C002",
            delta=0.05,
            solidarity_strength=0.8,
        )
        assert event.event_type == EventType.CONSCIOUSNESS_TRANSMISSION
        assert event.tick == 3
        assert event.target_id == "C001"
        assert event.source_id == "C002"
        assert event.delta == 0.05
        assert event.solidarity_strength == 0.8

    def test_transmission_event_is_frozen(self) -> None:
        """TransmissionEvent should be immutable."""
        event = TransmissionEvent(
            tick=0,
            target_id="C001",
            source_id="C002",
            delta=0.1,
            solidarity_strength=0.5,
        )
        with pytest.raises(ValidationError):
            event.delta = 0.2  # type: ignore[misc]

    def test_transmission_event_default_event_type(self) -> None:
        """TransmissionEvent should default to CONSCIOUSNESS_TRANSMISSION."""
        event = TransmissionEvent(
            tick=0,
            target_id="C001",
            source_id="C002",
            delta=0.1,
            solidarity_strength=0.5,
        )
        assert event.event_type == EventType.CONSCIOUSNESS_TRANSMISSION


class TestMassAwakeningEvent:
    """Tests for MassAwakeningEvent (MASS_AWAKENING)."""

    def test_mass_awakening_event_instantiation(self) -> None:
        """MassAwakeningEvent can be created with required fields."""
        event = MassAwakeningEvent(
            tick=7,
            target_id="C001",
            old_consciousness=0.4,
            new_consciousness=0.7,
            triggering_source="C002",
        )
        assert event.event_type == EventType.MASS_AWAKENING
        assert event.tick == 7
        assert event.target_id == "C001"
        assert event.old_consciousness == 0.4
        assert event.new_consciousness == 0.7
        assert event.triggering_source == "C002"

    def test_mass_awakening_event_is_frozen(self) -> None:
        """MassAwakeningEvent should be immutable."""
        event = MassAwakeningEvent(
            tick=0,
            target_id="C001",
            old_consciousness=0.3,
            new_consciousness=0.6,
            triggering_source="C002",
        )
        with pytest.raises(ValidationError):
            event.new_consciousness = 0.9  # type: ignore[misc]

    def test_mass_awakening_event_default_event_type(self) -> None:
        """MassAwakeningEvent should default to MASS_AWAKENING."""
        event = MassAwakeningEvent(
            tick=0,
            target_id="C001",
            old_consciousness=0.3,
            new_consciousness=0.6,
            triggering_source="C002",
        )
        assert event.event_type == EventType.MASS_AWAKENING


class TestSparkEvent:
    """Tests for SparkEvent (EXCESSIVE_FORCE)."""

    def test_spark_event_instantiation(self) -> None:
        """SparkEvent can be created with required fields."""
        event = SparkEvent(
            tick=5,
            node_id="C001",
            repression=0.8,
            spark_probability=0.4,
        )
        assert event.event_type == EventType.EXCESSIVE_FORCE
        assert event.tick == 5
        assert event.node_id == "C001"
        assert event.repression == 0.8
        assert event.spark_probability == 0.4

    def test_spark_event_is_frozen(self) -> None:
        """SparkEvent should be immutable."""
        event = SparkEvent(
            tick=0,
            node_id="C001",
            repression=0.5,
            spark_probability=0.25,
        )
        with pytest.raises(ValidationError):
            event.repression = 0.9  # type: ignore[misc]

    def test_spark_event_default_event_type(self) -> None:
        """SparkEvent should default to EXCESSIVE_FORCE."""
        event = SparkEvent(
            tick=0,
            node_id="C001",
            repression=0.5,
            spark_probability=0.25,
        )
        assert event.event_type == EventType.EXCESSIVE_FORCE


class TestUprisingEvent:
    """Tests for UprisingEvent (UPRISING)."""

    def test_uprising_event_instantiation(self) -> None:
        """UprisingEvent can be created with required fields."""
        event = UprisingEvent(
            tick=8,
            node_id="C001",
            trigger="spark",
            agitation=0.9,
            repression=0.7,
        )
        assert event.event_type == EventType.UPRISING
        assert event.tick == 8
        assert event.node_id == "C001"
        assert event.trigger == "spark"
        assert event.agitation == 0.9
        assert event.repression == 0.7

    def test_uprising_event_is_frozen(self) -> None:
        """UprisingEvent should be immutable."""
        event = UprisingEvent(
            tick=0,
            node_id="C001",
            trigger="revolutionary_pressure",
            agitation=0.6,
            repression=0.4,
        )
        with pytest.raises(ValidationError):
            event.trigger = "spark"  # type: ignore[misc]

    def test_uprising_event_default_event_type(self) -> None:
        """UprisingEvent should default to UPRISING."""
        event = UprisingEvent(
            tick=0,
            node_id="C001",
            trigger="spark",
            agitation=0.5,
            repression=0.3,
        )
        assert event.event_type == EventType.UPRISING


class TestSolidaritySpikeEvent:
    """Tests for SolidaritySpikeEvent (SOLIDARITY_SPIKE)."""

    def test_solidarity_spike_event_instantiation(self) -> None:
        """SolidaritySpikeEvent can be created with required fields."""
        event = SolidaritySpikeEvent(
            tick=6,
            node_id="C001",
            solidarity_gained=0.3,
            edges_affected=2,
            triggered_by="uprising",
        )
        assert event.event_type == EventType.SOLIDARITY_SPIKE
        assert event.tick == 6
        assert event.node_id == "C001"
        assert event.solidarity_gained == 0.3
        assert event.edges_affected == 2
        assert event.triggered_by == "uprising"

    def test_solidarity_spike_event_is_frozen(self) -> None:
        """SolidaritySpikeEvent should be immutable."""
        event = SolidaritySpikeEvent(
            tick=0,
            node_id="C001",
            solidarity_gained=0.2,
            edges_affected=1,
            triggered_by="uprising",
        )
        with pytest.raises(ValidationError):
            event.solidarity_gained = 0.5  # type: ignore[misc]

    def test_solidarity_spike_event_default_event_type(self) -> None:
        """SolidaritySpikeEvent should default to SOLIDARITY_SPIKE."""
        event = SolidaritySpikeEvent(
            tick=0,
            node_id="C001",
            solidarity_gained=0.1,
            edges_affected=1,
            triggered_by="uprising",
        )
        assert event.event_type == EventType.SOLIDARITY_SPIKE


class TestRuptureEvent:
    """Tests for RuptureEvent (RUPTURE)."""

    def test_rupture_event_instantiation(self) -> None:
        """RuptureEvent can be created with required fields."""
        event = RuptureEvent(
            tick=12,
            edge="C001->C002",
        )
        assert event.event_type == EventType.RUPTURE
        assert event.tick == 12
        assert event.edge == "C001->C002"

    def test_rupture_event_is_frozen(self) -> None:
        """RuptureEvent should be immutable."""
        event = RuptureEvent(
            tick=0,
            edge="C001->C002",
        )
        with pytest.raises(ValidationError):
            event.edge = "C003->C004"  # type: ignore[misc]

    def test_rupture_event_default_event_type(self) -> None:
        """RuptureEvent should default to RUPTURE."""
        event = RuptureEvent(
            tick=0,
            edge="C001->C002",
        )
        assert event.event_type == EventType.RUPTURE


# =============================================================================
# Field Validation Tests
# =============================================================================


class TestEventFieldValidation:
    """Tests for field validation across event types."""

    def test_tick_must_be_non_negative(self) -> None:
        """tick must be >= 0 for all events."""
        with pytest.raises(ValidationError):
            ExtractionEvent(
                tick=-1,
                source_id="C001",
                target_id="C002",
                amount=10.0,
            )

    def test_source_id_cannot_be_empty(self) -> None:
        """source_id must have at least one character."""
        with pytest.raises(ValidationError):
            ExtractionEvent(
                tick=0,
                source_id="",
                target_id="C002",
                amount=10.0,
            )

    def test_target_id_cannot_be_empty(self) -> None:
        """target_id must have at least one character."""
        with pytest.raises(ValidationError):
            ExtractionEvent(
                tick=0,
                source_id="C001",
                target_id="",
                amount=10.0,
            )

    def test_amount_must_be_non_negative(self) -> None:
        """amount must be >= 0 for EconomicEvents."""
        with pytest.raises(ValidationError):
            SubsidyEvent(
                tick=0,
                source_id="C002",
                target_id="C003",
                amount=-10.0,
                repression_boost=0.1,
            )

    def test_edges_affected_must_be_non_negative(self) -> None:
        """edges_affected must be >= 0 for SolidaritySpikeEvent."""
        with pytest.raises(ValidationError):
            SolidaritySpikeEvent(
                tick=0,
                node_id="C001",
                solidarity_gained=0.1,
                edges_affected=-1,
                triggered_by="uprising",
            )
