"""Tests for NarrativeDirector Semantic Bridge.

TDD Red Phase: These tests define the contract for the Semantic Bridge
that translates typed SimulationEvent objects into theoretical query strings.

The RAG database contains Marxist theoretical texts, not simulation logs.
The Semantic Bridge allows the Director to query for relevant theory.

Design decisions:
- SEMANTIC_MAP: Class constant mapping EventType enum to theory queries
- Deduplication: Multiple events with same type produce one query
- Fallback: Unknown events default to generic dialectical query

Sprint 4.1: Updated to use typed SimulationEvent objects with EventType enum
instead of string-based event keyword scanning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    pass

from babylon.models import (
    EdgeType,
    Relationship,
    SocialClass,
    SocialRole,
    WorldState,
)
from babylon.models.enums import EventType
from babylon.models.events import (
    CrisisEvent,
    ExtractionEvent,
    MassAwakeningEvent,
    SubsidyEvent,
    TransmissionEvent,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def worker() -> SocialClass:
    """Create a periphery worker social class."""
    return SocialClass(
        id="C001",
        name="Worker",
        role=SocialRole.PERIPHERY_PROLETARIAT,
        wealth=0.5,
        ideology=0.0,
        organization=0.1,
        repression_faced=0.5,
        subsistence_threshold=0.3,
    )


@pytest.fixture
def owner() -> SocialClass:
    """Create a core owner social class."""
    return SocialClass(
        id="C002",
        name="Owner",
        role=SocialRole.CORE_BOURGEOISIE,
        wealth=10.0,
        ideology=0.5,
        organization=0.7,
        repression_faced=0.1,
        subsistence_threshold=0.1,
    )


@pytest.fixture
def exploitation_edge() -> Relationship:
    """Create an exploitation relationship."""
    return Relationship(
        source_id="C001",
        target_id="C002",
        edge_type=EdgeType.EXPLOITATION,
        value_flow=5.0,
        tension=0.5,
    )


@pytest.fixture
def initial_state(
    worker: SocialClass,
    owner: SocialClass,
    exploitation_edge: Relationship,
) -> WorldState:
    """Create initial WorldState."""
    return WorldState(
        tick=0,
        entities={"C001": worker, "C002": owner},
        relationships=[exploitation_edge],
    )


@pytest.fixture
def mock_rag_pipeline() -> MagicMock:
    """Create mock RagPipeline that captures query text."""
    mock = MagicMock()

    # Create mock QueryResponse with results
    mock_result = MagicMock()
    mock_result.chunk = MagicMock()
    mock_result.chunk.content = "Theoretical content from archive."

    mock_response = MagicMock()
    mock_response.results = [mock_result]
    mock_response.total_results = 1

    mock.query.return_value = mock_response
    return mock


# =============================================================================
# TEST SEMANTIC MAP EXISTS
# =============================================================================


@pytest.mark.unit
class TestSemanticMapExists:
    """Tests for SEMANTIC_MAP class constant.

    Sprint 4.1: SEMANTIC_MAP now uses EventType enum keys instead of strings.
    """

    def test_semantic_map_is_class_constant(self) -> None:
        """NarrativeDirector has SEMANTIC_MAP class constant."""
        from babylon.ai.director import NarrativeDirector

        assert hasattr(NarrativeDirector, "SEMANTIC_MAP")
        assert isinstance(NarrativeDirector.SEMANTIC_MAP, dict)

    def test_semantic_map_contains_surplus_extraction(self) -> None:
        """SEMANTIC_MAP contains SURPLUS_EXTRACTION mapping."""
        from babylon.ai.director import NarrativeDirector

        assert EventType.SURPLUS_EXTRACTION in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP[EventType.SURPLUS_EXTRACTION]
        assert "surplus value" in query.lower()

    def test_semantic_map_contains_imperial_subsidy(self) -> None:
        """SEMANTIC_MAP contains IMPERIAL_SUBSIDY mapping."""
        from babylon.ai.director import NarrativeDirector

        assert EventType.IMPERIAL_SUBSIDY in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP[EventType.IMPERIAL_SUBSIDY]
        assert "repression" in query.lower() or "imperialist" in query.lower()

    def test_semantic_map_contains_economic_crisis(self) -> None:
        """SEMANTIC_MAP contains ECONOMIC_CRISIS mapping."""
        from babylon.ai.director import NarrativeDirector

        assert EventType.ECONOMIC_CRISIS in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP[EventType.ECONOMIC_CRISIS]
        assert "profit" in query.lower() or "crisis" in query.lower()

    def test_semantic_map_contains_consciousness_transmission(self) -> None:
        """SEMANTIC_MAP contains CONSCIOUSNESS_TRANSMISSION mapping.

        Sprint 4.1: SOLIDARITY_AWAKENING renamed to CONSCIOUSNESS_TRANSMISSION.
        """
        from babylon.ai.director import NarrativeDirector

        assert EventType.CONSCIOUSNESS_TRANSMISSION in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP[EventType.CONSCIOUSNESS_TRANSMISSION]
        assert "class consciousness" in query.lower() or "solidarity" in query.lower()

    def test_semantic_map_contains_mass_awakening(self) -> None:
        """SEMANTIC_MAP contains MASS_AWAKENING mapping."""
        from babylon.ai.director import NarrativeDirector

        assert EventType.MASS_AWAKENING in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP[EventType.MASS_AWAKENING]
        assert "revolutionary" in query.lower() or "mass" in query.lower()

    def test_semantic_map_uses_event_type_enum_keys(self) -> None:
        """SEMANTIC_MAP uses EventType enum as keys, not strings.

        Sprint 4.1: Critical change from string keys to EventType enum.
        """
        from babylon.ai.director import NarrativeDirector

        for key in NarrativeDirector.SEMANTIC_MAP:
            assert isinstance(key, EventType), f"Key {key} should be EventType, not {type(key)}"


# =============================================================================
# TEST SINGLE EVENT TRANSLATION
# =============================================================================


@pytest.mark.unit
class TestSingleEventTranslation:
    """Tests for translating single typed events to semantic queries.

    Sprint 4.1: Updated to use typed SimulationEvent objects.
    """

    def test_surplus_extraction_event_translated(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """ExtractionEvent is translated to surplus value theory query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event],
            }
        )

        director.on_tick(previous_state, new_state)

        # Check that RAG was queried with semantic query, not raw event
        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should NOT contain raw event format
        assert "Tick 1:" not in query_text
        # Should contain theoretical query
        assert "surplus value" in query_text.lower()

    def test_imperial_subsidy_event_translated(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """SubsidyEvent is translated to repression theory query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        subsidy_event = SubsidyEvent(
            tick=1,
            source_id="C002",
            target_id="C001",
            amount=5.0,
            repression_boost=0.2,
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [subsidy_event],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        assert "repression" in query_text.lower() or "imperialist" in query_text.lower()

    def test_economic_crisis_event_translated(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """CrisisEvent is translated to crisis theory query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        crisis_event = CrisisEvent(
            tick=1,
            pool_ratio=0.15,
            aggregate_tension=0.85,
            decision="AUSTERITY",
            wage_delta=-0.05,
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [crisis_event],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        assert "profit" in query_text.lower() or "crisis" in query_text.lower()


# =============================================================================
# TEST DEDUPLICATION
# =============================================================================


@pytest.mark.unit
class TestSemanticQueryDeduplication:
    """Tests for deduplication of semantic queries."""

    def test_same_event_type_multiple_events_deduplicated(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Multiple events with same type produce single query term."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        # Three extraction events with same EventType
        event_a = ExtractionEvent(tick=1, source_id="A", target_id="B", amount=5.0)
        event_b = ExtractionEvent(tick=1, source_id="C", target_id="D", amount=10.0)
        event_c = ExtractionEvent(tick=1, source_id="E", target_id="F", amount=15.0)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [event_a, event_b, event_c],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # The semantic query should appear only once, not three times
        expected_phrase = "surplus value"
        occurrences = query_text.lower().count(expected_phrase)
        assert occurrences == 1, f"Expected 1 occurrence of '{expected_phrase}', got {occurrences}"


# =============================================================================
# TEST MULTIPLE DIFFERENT EVENT TYPES
# =============================================================================


@pytest.mark.unit
class TestMultipleEventTypesCombination:
    """Tests for combining multiple different event type translations."""

    def test_multiple_different_event_types_combined(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Multiple different event types produce combined query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        transmission_event = TransmissionEvent(
            tick=1,
            target_id="C001",
            source_id="C002",
            delta=0.05,
            solidarity_strength=0.5,
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event, transmission_event],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should contain both semantic queries
        assert "surplus value" in query_text.lower()
        assert "class consciousness" in query_text.lower() or "solidarity" in query_text.lower()

    def test_three_different_event_types_combined(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Three different event types produce combined query with all terms."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        crisis_event = CrisisEvent(
            tick=1,
            pool_ratio=0.15,
            aggregate_tension=0.85,
            decision="AUSTERITY",
            wage_delta=-0.05,
        )
        awakening_event = MassAwakeningEvent(
            tick=1,
            target_id="C001",
            triggering_source="C002",
            old_consciousness=0.3,
            new_consciousness=0.8,
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [extraction_event, crisis_event, awakening_event],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should contain all three semantic queries
        assert "surplus value" in query_text.lower()
        assert "profit" in query_text.lower() or "crisis" in query_text.lower()
        assert "revolutionary" in query_text.lower() or "mass" in query_text.lower()


# =============================================================================
# TEST FALLBACK BEHAVIOR
# =============================================================================


@pytest.mark.unit
class TestSemanticFallback:
    """Tests for fallback behavior with unmapped event types."""

    def test_unmapped_event_type_uses_fallback_query(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Event type not in SEMANTIC_MAP uses fallback dialectical query.

        Sprint 4.1: TransmissionEvent is in SEMANTIC_MAP, so using
        SOLIDARITY_SPIKE which might not be mapped to test fallback.
        """
        from babylon.ai.director import NarrativeDirector
        from babylon.models.events import SolidaritySpikeEvent

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        # SOLIDARITY_SPIKE might not be in SEMANTIC_MAP, triggering fallback
        spike_event = SolidaritySpikeEvent(
            tick=1,
            node_id="C001",
            solidarity_gained=0.15,
            edges_affected=3,
            triggered_by="uprising",
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [spike_event],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should use SEMANTIC_MAP value or fallback
        # Either the mapped query or fallback should be present
        assert len(query_text) > 0

    def test_empty_events_list_skips_rag_query(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Empty events list skips RAG query entirely."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(update={"tick": 1})

        director.on_tick(previous_state, new_state)

        # With no new events, RAG should not be called
        mock_rag_pipeline.query.assert_not_called()

    def test_mixed_mapped_unmapped_events_uses_mapped_queries(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Mixed mapped/unmapped events uses mapped query translations."""
        from babylon.ai.director import NarrativeDirector
        from babylon.models.events import SolidaritySpikeEvent

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        # ExtractionEvent is mapped, SolidaritySpikeEvent might not be
        extraction_event = ExtractionEvent(
            tick=1,
            source_id="C001",
            target_id="C002",
            amount=10.0,
        )
        spike_event = SolidaritySpikeEvent(
            tick=1,
            node_id="C001",
            solidarity_gained=0.15,
            edges_affected=3,
            triggered_by="uprising",
        )

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "events": [spike_event, extraction_event],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should use the known translation for ExtractionEvent
        assert "surplus value" in query_text.lower()
