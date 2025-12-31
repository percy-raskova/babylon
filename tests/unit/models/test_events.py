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
from tests.constants import TestConstants

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

TC = TestConstants

# =============================================================================
# Base Class Tests
# =============================================================================


class TestSimulationEvent:
    """Tests for SimulationEvent base class."""

    def test_simulation_event_requires_event_type(self) -> None:
        """SimulationEvent requires an event_type."""
        with pytest.raises(ValidationError):
            SimulationEvent(tick=TC.Event.TICK_ZERO)  # type: ignore[call-arg]

    def test_simulation_event_requires_tick(self) -> None:
        """SimulationEvent requires a tick."""
        with pytest.raises(ValidationError):
            SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION)  # type: ignore[call-arg]

    def test_simulation_event_is_frozen(self) -> None:
        """SimulationEvent should be immutable (frozen)."""
        event = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=TC.Event.TICK_ZERO)
        with pytest.raises(ValidationError):
            event.tick = 1  # type: ignore[misc]

    def test_simulation_event_has_timestamp_default(self) -> None:
        """SimulationEvent should auto-generate timestamp."""
        event = SimulationEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=TC.Event.TICK_ZERO)
        assert isinstance(event.timestamp, datetime)


class TestEconomicEvent:
    """Tests for EconomicEvent base class."""

    def test_economic_event_requires_amount(self) -> None:
        """EconomicEvent requires an amount field."""
        with pytest.raises(ValidationError):
            EconomicEvent(event_type=EventType.SURPLUS_EXTRACTION, tick=TC.Event.TICK_ZERO)  # type: ignore[call-arg]

    def test_economic_event_amount_must_be_non_negative(self) -> None:
        """EconomicEvent amount must be >= 0."""
        with pytest.raises(ValidationError):
            EconomicEvent(
                event_type=EventType.SURPLUS_EXTRACTION,
                tick=TC.Event.TICK_ZERO,
                amount=-1.0,  # Boundary violation
            )


class TestConsciousnessEvent:
    """Tests for ConsciousnessEvent base class."""

    def test_consciousness_event_requires_target_id(self) -> None:
        """ConsciousnessEvent requires a target_id field."""
        with pytest.raises(ValidationError):
            ConsciousnessEvent(
                event_type=EventType.CONSCIOUSNESS_TRANSMISSION,
                tick=TC.Event.TICK_ZERO,
            )  # type: ignore[call-arg]

    def test_consciousness_event_is_frozen(self) -> None:
        """ConsciousnessEvent should be immutable."""
        event = ConsciousnessEvent(
            event_type=EventType.CONSCIOUSNESS_TRANSMISSION,
            tick=TC.Event.TICK_ZERO,
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
                tick=TC.Event.TICK_ZERO,
            )  # type: ignore[call-arg]

    def test_struggle_event_is_frozen(self) -> None:
        """StruggleEvent should be immutable."""
        event = StruggleEvent(
            event_type=EventType.EXCESSIVE_FORCE,
            tick=TC.Event.TICK_ZERO,
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
                tick=TC.Event.TICK_ZERO,
            )  # type: ignore[call-arg]

    def test_contradiction_event_is_frozen(self) -> None:
        """ContradictionEvent should be immutable."""
        event = ContradictionEvent(
            event_type=EventType.RUPTURE,
            tick=TC.Event.TICK_ZERO,
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
            tick=TC.Event.TICK_MID,
            source_id="C001",
            target_id="C002",
            amount=TC.Event.EXTRACTION_MODERATE,
        )
        assert event.event_type == EventType.SURPLUS_EXTRACTION
        assert event.tick == TC.Event.TICK_MID
        assert event.source_id == "C001"
        assert event.target_id == "C002"
        assert event.amount == TC.Event.EXTRACTION_MODERATE
        assert event.mechanism == "imperial_rent"  # default

    def test_extraction_event_is_frozen(self) -> None:
        """ExtractionEvent should be immutable."""
        event = ExtractionEvent(
            tick=TC.Event.TICK_ZERO,
            source_id="C001",
            target_id="C002",
            amount=TC.Event.EXTRACTION_SMALL,
        )
        with pytest.raises(ValidationError):
            event.amount = 20.0  # type: ignore[misc]

    def test_extraction_event_default_event_type(self) -> None:
        """ExtractionEvent should default to SURPLUS_EXTRACTION."""
        event = ExtractionEvent(
            tick=TC.Event.TICK_ZERO,
            source_id="C001",
            target_id="C002",
            amount=TC.Event.EXTRACTION_SMALL,
        )
        assert event.event_type == EventType.SURPLUS_EXTRACTION


class TestSubsidyEvent:
    """Tests for SubsidyEvent (IMPERIAL_SUBSIDY)."""

    def test_subsidy_event_instantiation(self) -> None:
        """SubsidyEvent can be created with required fields."""
        event = SubsidyEvent(
            tick=TC.Event.TICK_MID,
            source_id="C002",
            target_id="C003",
            amount=TC.Event.SUBSIDY_LARGE,
            repression_boost=TC.Event.REPRESSION_BOOST_MODERATE,
        )
        assert event.event_type == EventType.IMPERIAL_SUBSIDY
        assert event.tick == TC.Event.TICK_MID
        assert event.source_id == "C002"
        assert event.target_id == "C003"
        assert event.amount == TC.Event.SUBSIDY_LARGE
        assert event.repression_boost == TC.Event.REPRESSION_BOOST_MODERATE

    def test_subsidy_event_is_frozen(self) -> None:
        """SubsidyEvent should be immutable."""
        event = SubsidyEvent(
            tick=TC.Event.TICK_ZERO,
            source_id="C002",
            target_id="C003",
            amount=TC.Event.EXTRACTION_LARGE,
            repression_boost=TC.Event.REPRESSION_BOOST_LOW,
        )
        with pytest.raises(ValidationError):
            event.repression_boost = TC.Event.REPRESSION_BOOST_HIGH  # type: ignore[misc]

    def test_subsidy_event_default_event_type(self) -> None:
        """SubsidyEvent should default to IMPERIAL_SUBSIDY."""
        event = SubsidyEvent(
            tick=TC.Event.TICK_ZERO,
            source_id="C002",
            target_id="C003",
            amount=TC.Event.EXTRACTION_LARGE,
            repression_boost=TC.Event.REPRESSION_BOOST_LOW,
        )
        assert event.event_type == EventType.IMPERIAL_SUBSIDY


class TestCrisisEvent:
    """Tests for CrisisEvent (ECONOMIC_CRISIS)."""

    def test_crisis_event_instantiation(self) -> None:
        """CrisisEvent can be created with required fields."""
        event = CrisisEvent(
            tick=TC.Event.TICK_LATE,
            pool_ratio=TC.GlobalEconomy.CRISIS_THRESHOLD + TC.Event.SMALL_DELTA,
            aggregate_tension=TC.Probability.HIGH,
            decision="CRISIS",
            wage_delta=TC.Event.WAGE_CUT_MODERATE,
        )
        assert event.event_type == EventType.ECONOMIC_CRISIS
        assert event.tick == TC.Event.TICK_LATE
        assert event.pool_ratio == TC.GlobalEconomy.CRISIS_THRESHOLD + TC.Event.SMALL_DELTA
        assert event.aggregate_tension == TC.Probability.HIGH
        assert event.decision == "CRISIS"
        assert event.wage_delta == TC.Event.WAGE_CUT_MODERATE

    def test_crisis_event_is_frozen(self) -> None:
        """CrisisEvent should be immutable."""
        event = CrisisEvent(
            tick=TC.Event.TICK_ZERO,
            pool_ratio=TC.GlobalEconomy.AUSTERITY_THRESHOLD - TC.GlobalEconomy.CRISIS_THRESHOLD,
            aggregate_tension=TC.Probability.MIDPOINT,
            decision="AUSTERITY",
            wage_delta=TC.Event.WAGE_CUT_SMALL,
        )
        with pytest.raises(ValidationError):
            event.decision = "BRIBERY"  # type: ignore[misc]

    def test_crisis_event_default_event_type(self) -> None:
        """CrisisEvent should default to ECONOMIC_CRISIS."""
        event = CrisisEvent(
            tick=TC.Event.TICK_ZERO,
            pool_ratio=TC.GlobalEconomy.CRISIS_THRESHOLD,
            aggregate_tension=TC.Probability.EXTREME,
            decision="IRON_FIST",
            wage_delta=TC.Event.WAGE_NO_CHANGE,
        )
        assert event.event_type == EventType.ECONOMIC_CRISIS


class TestTransmissionEvent:
    """Tests for TransmissionEvent (CONSCIOUSNESS_TRANSMISSION)."""

    def test_transmission_event_instantiation(self) -> None:
        """TransmissionEvent can be created with required fields."""
        event = TransmissionEvent(
            tick=TC.Event.TICK_EARLY,
            target_id="C001",
            source_id="C002",
            delta=TC.Event.SMALL_DELTA,
            solidarity_strength=TC.EconomicFlow.STRONG_SOLIDARITY,
        )
        assert event.event_type == EventType.CONSCIOUSNESS_TRANSMISSION
        assert event.tick == TC.Event.TICK_EARLY
        assert event.target_id == "C001"
        assert event.source_id == "C002"
        assert event.delta == TC.Event.SMALL_DELTA
        assert event.solidarity_strength == TC.EconomicFlow.STRONG_SOLIDARITY

    def test_transmission_event_is_frozen(self) -> None:
        """TransmissionEvent should be immutable."""
        event = TransmissionEvent(
            tick=TC.Event.TICK_ZERO,
            target_id="C001",
            source_id="C002",
            delta=TC.Event.MODERATE_DELTA,
            solidarity_strength=TC.EconomicFlow.ACTUAL_SOLIDARITY,
        )
        with pytest.raises(ValidationError):
            event.delta = TC.Event.LARGE_DELTA  # type: ignore[misc]

    def test_transmission_event_default_event_type(self) -> None:
        """TransmissionEvent should default to CONSCIOUSNESS_TRANSMISSION."""
        event = TransmissionEvent(
            tick=TC.Event.TICK_ZERO,
            target_id="C001",
            source_id="C002",
            delta=TC.Event.MODERATE_DELTA,
            solidarity_strength=TC.EconomicFlow.ACTUAL_SOLIDARITY,
        )
        assert event.event_type == EventType.CONSCIOUSNESS_TRANSMISSION


class TestMassAwakeningEvent:
    """Tests for MassAwakeningEvent (MASS_AWAKENING)."""

    def test_mass_awakening_event_instantiation(self) -> None:
        """MassAwakeningEvent can be created with required fields."""
        event = MassAwakeningEvent(
            tick=TC.Event.TICK_SEVEN,
            target_id="C001",
            old_consciousness=TC.Probability.BELOW_MIDPOINT,
            new_consciousness=TC.Consciousness.AWAKENING,
            triggering_source="C002",
        )
        assert event.event_type == EventType.MASS_AWAKENING
        assert event.tick == TC.Event.TICK_SEVEN
        assert event.target_id == "C001"
        assert event.old_consciousness == TC.Probability.BELOW_MIDPOINT
        assert event.new_consciousness == TC.Consciousness.AWAKENING
        assert event.triggering_source == "C002"

    def test_mass_awakening_event_is_frozen(self) -> None:
        """MassAwakeningEvent should be immutable."""
        event = MassAwakeningEvent(
            tick=TC.Event.TICK_ZERO,
            target_id="C001",
            old_consciousness=TC.Probability.MODERATE,
            new_consciousness=TC.Solidarity.MASS_AWAKENING_THRESHOLD,
            triggering_source="C002",
        )
        with pytest.raises(ValidationError):
            event.new_consciousness = TC.Consciousness.REVOLUTIONARY  # type: ignore[misc]

    def test_mass_awakening_event_default_event_type(self) -> None:
        """MassAwakeningEvent should default to MASS_AWAKENING."""
        event = MassAwakeningEvent(
            tick=TC.Event.TICK_ZERO,
            target_id="C001",
            old_consciousness=TC.Probability.MODERATE,
            new_consciousness=TC.Solidarity.MASS_AWAKENING_THRESHOLD,
            triggering_source="C002",
        )
        assert event.event_type == EventType.MASS_AWAKENING


class TestSparkEvent:
    """Tests for SparkEvent (EXCESSIVE_FORCE)."""

    def test_spark_event_instantiation(self) -> None:
        """SparkEvent can be created with required fields."""
        event = SparkEvent(
            tick=TC.Event.TICK_MID,
            node_id="C001",
            repression=TC.Probability.VERY_HIGH,
            spark_probability=TC.Event.SPARK_MODERATE,
        )
        assert event.event_type == EventType.EXCESSIVE_FORCE
        assert event.tick == TC.Event.TICK_MID
        assert event.node_id == "C001"
        assert event.repression == TC.Probability.VERY_HIGH
        assert event.spark_probability == TC.Event.SPARK_MODERATE

    def test_spark_event_is_frozen(self) -> None:
        """SparkEvent should be immutable."""
        event = SparkEvent(
            tick=TC.Event.TICK_ZERO,
            node_id="C001",
            repression=TC.Probability.MIDPOINT,
            spark_probability=TC.Event.SPARK_LOW,
        )
        with pytest.raises(ValidationError):
            event.repression = TC.Probability.EXTREME  # type: ignore[misc]

    def test_spark_event_default_event_type(self) -> None:
        """SparkEvent should default to EXCESSIVE_FORCE."""
        event = SparkEvent(
            tick=TC.Event.TICK_ZERO,
            node_id="C001",
            repression=TC.Probability.MIDPOINT,
            spark_probability=TC.Event.SPARK_LOW,
        )
        assert event.event_type == EventType.EXCESSIVE_FORCE


class TestUprisingEvent:
    """Tests for UprisingEvent (UPRISING)."""

    def test_uprising_event_instantiation(self) -> None:
        """UprisingEvent can be created with required fields."""
        event = UprisingEvent(
            tick=TC.Event.TICK_EIGHT,
            node_id="C001",
            trigger="spark",
            agitation=TC.Probability.EXTREME,
            repression=TC.Probability.HIGH,
        )
        assert event.event_type == EventType.UPRISING
        assert event.tick == TC.Event.TICK_EIGHT
        assert event.node_id == "C001"
        assert event.trigger == "spark"
        assert event.agitation == TC.Probability.EXTREME
        assert event.repression == TC.Probability.HIGH

    def test_uprising_event_is_frozen(self) -> None:
        """UprisingEvent should be immutable."""
        event = UprisingEvent(
            tick=TC.Event.TICK_ZERO,
            node_id="C001",
            trigger="revolutionary_pressure",
            agitation=TC.Probability.ELEVATED,
            repression=TC.Probability.BELOW_MIDPOINT,
        )
        with pytest.raises(ValidationError):
            event.trigger = "spark"  # type: ignore[misc]

    def test_uprising_event_default_event_type(self) -> None:
        """UprisingEvent should default to UPRISING."""
        event = UprisingEvent(
            tick=TC.Event.TICK_ZERO,
            node_id="C001",
            trigger="spark",
            agitation=TC.Probability.MIDPOINT,
            repression=TC.Probability.MODERATE,
        )
        assert event.event_type == EventType.UPRISING


class TestSolidaritySpikeEvent:
    """Tests for SolidaritySpikeEvent (SOLIDARITY_SPIKE)."""

    def test_solidarity_spike_event_instantiation(self) -> None:
        """SolidaritySpikeEvent can be created with required fields."""
        event = SolidaritySpikeEvent(
            tick=TC.Event.TICK_SIX,
            node_id="C001",
            solidarity_gained=TC.Event.SOLIDARITY_GAIN_LARGE,
            edges_affected=TC.Event.EDGES_AFFECTED_FEW,
            triggered_by="uprising",
        )
        assert event.event_type == EventType.SOLIDARITY_SPIKE
        assert event.tick == TC.Event.TICK_SIX
        assert event.node_id == "C001"
        assert event.solidarity_gained == TC.Event.SOLIDARITY_GAIN_LARGE
        assert event.edges_affected == TC.Event.EDGES_AFFECTED_FEW
        assert event.triggered_by == "uprising"

    def test_solidarity_spike_event_is_frozen(self) -> None:
        """SolidaritySpikeEvent should be immutable."""
        event = SolidaritySpikeEvent(
            tick=TC.Event.TICK_ZERO,
            node_id="C001",
            solidarity_gained=TC.Event.SOLIDARITY_GAIN_MODERATE,
            edges_affected=TC.Event.EDGES_AFFECTED_ONE,
            triggered_by="uprising",
        )
        with pytest.raises(ValidationError):
            event.solidarity_gained = TC.EconomicFlow.ACTUAL_SOLIDARITY  # type: ignore[misc]

    def test_solidarity_spike_event_default_event_type(self) -> None:
        """SolidaritySpikeEvent should default to SOLIDARITY_SPIKE."""
        event = SolidaritySpikeEvent(
            tick=TC.Event.TICK_ZERO,
            node_id="C001",
            solidarity_gained=TC.Event.SOLIDARITY_GAIN_SMALL,
            edges_affected=TC.Event.EDGES_AFFECTED_ONE,
            triggered_by="uprising",
        )
        assert event.event_type == EventType.SOLIDARITY_SPIKE


class TestRuptureEvent:
    """Tests for RuptureEvent (RUPTURE)."""

    def test_rupture_event_instantiation(self) -> None:
        """RuptureEvent can be created with required fields."""
        event = RuptureEvent(
            tick=TC.Event.TICK_ENDGAME,
            edge="C001->C002",
        )
        assert event.event_type == EventType.RUPTURE
        assert event.tick == TC.Event.TICK_ENDGAME
        assert event.edge == "C001->C002"

    def test_rupture_event_is_frozen(self) -> None:
        """RuptureEvent should be immutable."""
        event = RuptureEvent(
            tick=TC.Event.TICK_ZERO,
            edge="C001->C002",
        )
        with pytest.raises(ValidationError):
            event.edge = "C003->C004"  # type: ignore[misc]

    def test_rupture_event_default_event_type(self) -> None:
        """RuptureEvent should default to RUPTURE."""
        event = RuptureEvent(
            tick=TC.Event.TICK_ZERO,
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
                tick=-1,  # Boundary violation
                source_id="C001",
                target_id="C002",
                amount=TC.Event.EXTRACTION_SMALL,
            )

    def test_source_id_cannot_be_empty(self) -> None:
        """source_id must have at least one character."""
        with pytest.raises(ValidationError):
            ExtractionEvent(
                tick=TC.Event.TICK_ZERO,
                source_id="",
                target_id="C002",
                amount=TC.Event.EXTRACTION_SMALL,
            )

    def test_target_id_cannot_be_empty(self) -> None:
        """target_id must have at least one character."""
        with pytest.raises(ValidationError):
            ExtractionEvent(
                tick=TC.Event.TICK_ZERO,
                source_id="C001",
                target_id="",
                amount=TC.Event.EXTRACTION_SMALL,
            )

    def test_amount_must_be_non_negative(self) -> None:
        """amount must be >= 0 for EconomicEvents."""
        with pytest.raises(ValidationError):
            SubsidyEvent(
                tick=TC.Event.TICK_ZERO,
                source_id="C002",
                target_id="C003",
                amount=-10.0,  # Boundary violation
                repression_boost=TC.Event.REPRESSION_BOOST_LOW,
            )

    def test_edges_affected_must_be_non_negative(self) -> None:
        """edges_affected must be >= 0 for SolidaritySpikeEvent."""
        with pytest.raises(ValidationError):
            SolidaritySpikeEvent(
                tick=TC.Event.TICK_ZERO,
                node_id="C001",
                solidarity_gained=TC.Event.SOLIDARITY_GAIN_SMALL,
                edges_affected=-1,  # Boundary violation
                triggered_by="uprising",
            )
