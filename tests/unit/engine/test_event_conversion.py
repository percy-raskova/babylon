"""Tests for _convert_bus_event_to_pydantic() function.

Sprint 3.1+: Event conversion from EventBus Events to typed Pydantic models.

Tests verify:
- Each EventType is correctly converted to its corresponding Pydantic class
- Payload fields are correctly extracted
- Unsupported event types return None (graceful degradation)
- String event types are normalized to EventType enum
"""

from datetime import datetime

from babylon.engine.event_bus import Event
from babylon.engine.simulation_engine import _convert_bus_event_to_pydantic
from babylon.models.enums import EventType
from babylon.models.events import (
    CrisisEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    RuptureEvent,
    SolidaritySpikeEvent,
    SparkEvent,
    SubsidyEvent,
    TransmissionEvent,
    UprisingEvent,
)


class TestExtractionEventConversion:
    """Tests for SURPLUS_EXTRACTION event conversion."""

    def test_converts_surplus_extraction_event(self) -> None:
        """SURPLUS_EXTRACTION events convert to ExtractionEvent."""
        bus_event = Event(
            type=EventType.SURPLUS_EXTRACTION,
            tick=5,
            payload={
                "source_id": "C001",
                "target_id": "C002",
                "amount": 15.5,
                "mechanism": "imperial_rent",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, ExtractionEvent)
        assert result.event_type == EventType.SURPLUS_EXTRACTION
        assert result.tick == 5
        assert result.source_id == "C001"
        assert result.target_id == "C002"
        assert result.amount == 15.5
        assert result.mechanism == "imperial_rent"

    def test_extraction_with_string_event_type(self) -> None:
        """String event types are normalized to EventType enum."""
        bus_event = Event(
            type="surplus_extraction",  # type: ignore[arg-type]
            tick=3,
            payload={
                "source_id": "C001",
                "target_id": "C002",
                "amount": 10.0,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, ExtractionEvent)
        assert result.event_type == EventType.SURPLUS_EXTRACTION


class TestSubsidyEventConversion:
    """Tests for IMPERIAL_SUBSIDY event conversion."""

    def test_converts_imperial_subsidy_event(self) -> None:
        """IMPERIAL_SUBSIDY events convert to SubsidyEvent."""
        bus_event = Event(
            type=EventType.IMPERIAL_SUBSIDY,
            tick=7,
            payload={
                "source_id": "C002",
                "target_id": "C003",
                "amount": 100.0,
                "repression_boost": 0.25,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, SubsidyEvent)
        assert result.event_type == EventType.IMPERIAL_SUBSIDY
        assert result.tick == 7
        assert result.source_id == "C002"
        assert result.target_id == "C003"
        assert result.amount == 100.0
        assert result.repression_boost == 0.25


class TestCrisisEventConversion:
    """Tests for ECONOMIC_CRISIS event conversion."""

    def test_converts_economic_crisis_event(self) -> None:
        """ECONOMIC_CRISIS events convert to CrisisEvent."""
        bus_event = Event(
            type=EventType.ECONOMIC_CRISIS,
            tick=10,
            payload={
                "pool_ratio": 0.15,
                "aggregate_tension": 0.7,
                "decision": "CRISIS",
                "wage_delta": -0.05,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, CrisisEvent)
        assert result.event_type == EventType.ECONOMIC_CRISIS
        assert result.tick == 10
        assert result.pool_ratio == 0.15
        assert result.aggregate_tension == 0.7
        assert result.decision == "CRISIS"
        assert result.wage_delta == -0.05


class TestTransmissionEventConversion:
    """Tests for CONSCIOUSNESS_TRANSMISSION event conversion."""

    def test_converts_consciousness_transmission_event(self) -> None:
        """CONSCIOUSNESS_TRANSMISSION events convert to TransmissionEvent."""
        bus_event = Event(
            type=EventType.CONSCIOUSNESS_TRANSMISSION,
            tick=3,
            payload={
                "source_id": "C002",
                "target_id": "C001",
                "delta": 0.05,
                "solidarity_strength": 0.8,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, TransmissionEvent)
        assert result.event_type == EventType.CONSCIOUSNESS_TRANSMISSION
        assert result.tick == 3
        assert result.source_id == "C002"
        assert result.target_id == "C001"
        assert result.delta == 0.05
        assert result.solidarity_strength == 0.8


class TestMassAwakeningEventConversion:
    """Tests for MASS_AWAKENING event conversion."""

    def test_converts_mass_awakening_event(self) -> None:
        """MASS_AWAKENING events convert to MassAwakeningEvent."""
        bus_event = Event(
            type=EventType.MASS_AWAKENING,
            tick=7,
            payload={
                "target_id": "C001",
                "old_consciousness": 0.4,
                "new_consciousness": 0.7,
                "triggering_source": "C002",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, MassAwakeningEvent)
        assert result.event_type == EventType.MASS_AWAKENING
        assert result.tick == 7
        assert result.target_id == "C001"
        assert result.old_consciousness == 0.4
        assert result.new_consciousness == 0.7
        assert result.triggering_source == "C002"


class TestSparkEventConversion:
    """Tests for EXCESSIVE_FORCE event conversion."""

    def test_converts_excessive_force_event(self) -> None:
        """EXCESSIVE_FORCE events convert to SparkEvent."""
        bus_event = Event(
            type=EventType.EXCESSIVE_FORCE,
            tick=5,
            payload={
                "node_id": "C001",
                "repression": 0.8,
                "spark_probability": 0.4,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, SparkEvent)
        assert result.event_type == EventType.EXCESSIVE_FORCE
        assert result.tick == 5
        assert result.node_id == "C001"
        assert result.repression == 0.8
        assert result.spark_probability == 0.4


class TestUprisingEventConversion:
    """Tests for UPRISING event conversion."""

    def test_converts_uprising_event(self) -> None:
        """UPRISING events convert to UprisingEvent."""
        bus_event = Event(
            type=EventType.UPRISING,
            tick=8,
            payload={
                "node_id": "C001",
                "trigger": "spark",
                "agitation": 0.9,
                "repression": 0.7,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, UprisingEvent)
        assert result.event_type == EventType.UPRISING
        assert result.tick == 8
        assert result.node_id == "C001"
        assert result.trigger == "spark"
        assert result.agitation == 0.9
        assert result.repression == 0.7


class TestSolidaritySpikeEventConversion:
    """Tests for SOLIDARITY_SPIKE event conversion."""

    def test_converts_solidarity_spike_event(self) -> None:
        """SOLIDARITY_SPIKE events convert to SolidaritySpikeEvent."""
        bus_event = Event(
            type=EventType.SOLIDARITY_SPIKE,
            tick=6,
            payload={
                "node_id": "C001",
                "solidarity_gained": 0.3,
                "edges_affected": 2,
                "triggered_by": "uprising",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, SolidaritySpikeEvent)
        assert result.event_type == EventType.SOLIDARITY_SPIKE
        assert result.tick == 6
        assert result.node_id == "C001"
        assert result.solidarity_gained == 0.3
        assert result.edges_affected == 2
        assert result.triggered_by == "uprising"


class TestRuptureEventConversion:
    """Tests for RUPTURE event conversion."""

    def test_converts_rupture_event(self) -> None:
        """RUPTURE events convert to RuptureEvent."""
        bus_event = Event(
            type=EventType.RUPTURE,
            tick=12,
            payload={
                "edge": "C001->C002",
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert isinstance(result, RuptureEvent)
        assert result.event_type == EventType.RUPTURE
        assert result.tick == 12
        assert result.edge == "C001->C002"


class TestGracefulDegradation:
    """Tests for unsupported event types and edge cases."""

    def test_unknown_string_event_type_returns_none(self) -> None:
        """Unknown string event types return None."""
        bus_event = Event(
            type="unknown_event_type",  # type: ignore[arg-type]
            tick=0,
            payload={},
        )
        result = _convert_bus_event_to_pydantic(bus_event)
        assert result is None

    def test_solidarity_awakening_returns_none_until_implemented(self) -> None:
        """SOLIDARITY_AWAKENING returns None (not yet implemented)."""
        bus_event = Event(
            type=EventType.SOLIDARITY_AWAKENING,
            tick=0,
            payload={"node_id": "C001"},
        )
        result = _convert_bus_event_to_pydantic(bus_event)
        # SOLIDARITY_AWAKENING doesn't have a dedicated event class yet
        assert result is None

    def test_preserves_timestamp(self) -> None:
        """Timestamp from bus event is preserved in converted event."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        bus_event = Event(
            type=EventType.SURPLUS_EXTRACTION,
            tick=0,
            timestamp=timestamp,
            payload={
                "source_id": "C001",
                "target_id": "C002",
                "amount": 10.0,
            },
        )
        result = _convert_bus_event_to_pydantic(bus_event)

        assert result is not None
        assert result.timestamp == timestamp
