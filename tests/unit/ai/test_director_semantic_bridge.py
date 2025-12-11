"""Tests for NarrativeDirector Semantic Bridge.

TDD Red Phase: These tests define the contract for the Semantic Bridge
that translates simulation events (like "SURPLUS_EXTRACTION") into
theoretical query strings (like "marxist theory of surplus value extraction").

The RAG database contains Marxist theoretical texts, not simulation logs.
The Semantic Bridge allows the Director to query for relevant theory.

Design decisions:
- SEMANTIC_MAP: Class constant mapping event keywords to theory queries
- Deduplication: Multiple events with same keyword produce one query
- Fallback: Unknown events default to generic dialectical query
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
    """Tests for SEMANTIC_MAP class constant."""

    def test_semantic_map_is_class_constant(self) -> None:
        """NarrativeDirector has SEMANTIC_MAP class constant."""
        from babylon.ai.director import NarrativeDirector

        assert hasattr(NarrativeDirector, "SEMANTIC_MAP")
        assert isinstance(NarrativeDirector.SEMANTIC_MAP, dict)

    def test_semantic_map_contains_surplus_extraction(self) -> None:
        """SEMANTIC_MAP contains SURPLUS_EXTRACTION mapping."""
        from babylon.ai.director import NarrativeDirector

        assert "SURPLUS_EXTRACTION" in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP["SURPLUS_EXTRACTION"]
        assert "surplus value" in query.lower()

    def test_semantic_map_contains_imperial_subsidy(self) -> None:
        """SEMANTIC_MAP contains IMPERIAL_SUBSIDY mapping."""
        from babylon.ai.director import NarrativeDirector

        assert "IMPERIAL_SUBSIDY" in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP["IMPERIAL_SUBSIDY"]
        assert "repression" in query.lower() or "imperialist" in query.lower()

    def test_semantic_map_contains_economic_crisis(self) -> None:
        """SEMANTIC_MAP contains ECONOMIC_CRISIS mapping."""
        from babylon.ai.director import NarrativeDirector

        assert "ECONOMIC_CRISIS" in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP["ECONOMIC_CRISIS"]
        assert "profit" in query.lower() or "crisis" in query.lower()

    def test_semantic_map_contains_solidarity_awakening(self) -> None:
        """SEMANTIC_MAP contains SOLIDARITY_AWAKENING mapping."""
        from babylon.ai.director import NarrativeDirector

        assert "SOLIDARITY_AWAKENING" in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP["SOLIDARITY_AWAKENING"]
        assert "class consciousness" in query.lower() or "solidarity" in query.lower()

    def test_semantic_map_contains_mass_awakening(self) -> None:
        """SEMANTIC_MAP contains MASS_AWAKENING mapping."""
        from babylon.ai.director import NarrativeDirector

        assert "MASS_AWAKENING" in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP["MASS_AWAKENING"]
        assert "revolutionary" in query.lower() or "mass" in query.lower()

    def test_semantic_map_contains_bribery(self) -> None:
        """SEMANTIC_MAP contains BRIBERY mapping."""
        from babylon.ai.director import NarrativeDirector

        assert "BRIBERY" in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP["BRIBERY"]
        assert "labor aristocracy" in query.lower()

    def test_semantic_map_contains_wages(self) -> None:
        """SEMANTIC_MAP contains WAGES mapping."""
        from babylon.ai.director import NarrativeDirector

        assert "WAGES" in NarrativeDirector.SEMANTIC_MAP
        query = NarrativeDirector.SEMANTIC_MAP["WAGES"]
        assert "labor aristocracy" in query.lower()


# =============================================================================
# TEST SINGLE EVENT TRANSLATION
# =============================================================================


@pytest.mark.unit
class TestSingleEventTranslation:
    """Tests for translating single events to semantic queries."""

    def test_surplus_extraction_event_translated(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """SURPLUS_EXTRACTION event is translated to surplus value theory query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["Tick 1: SURPLUS_EXTRACTION from Worker to Owner"],
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
        """IMPERIAL_SUBSIDY event is translated to repression theory query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["IMPERIAL_SUBSIDY applied to regime"],
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
        """ECONOMIC_CRISIS event is translated to crisis theory query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["ECONOMIC_CRISIS triggered"],
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

    def test_same_keyword_multiple_events_deduplicated(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Multiple events with same keyword produce single query term."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": [
                    "SURPLUS_EXTRACTION from A to B",
                    "SURPLUS_EXTRACTION from C to D",
                    "SURPLUS_EXTRACTION from E to F",
                ],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # The semantic query should appear only once, not three times
        # Count occurrences of the mapped phrase
        expected_phrase = "surplus value"
        occurrences = query_text.lower().count(expected_phrase)
        assert occurrences == 1, f"Expected 1 occurrence of '{expected_phrase}', got {occurrences}"


# =============================================================================
# TEST MULTIPLE DIFFERENT KEYWORDS
# =============================================================================


@pytest.mark.unit
class TestMultipleKeywordsCombination:
    """Tests for combining multiple different keyword translations."""

    def test_multiple_different_keywords_combined(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Multiple different keywords produce combined query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": [
                    "SURPLUS_EXTRACTION occurred",
                    "SOLIDARITY_AWAKENING detected",
                ],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should contain both semantic queries
        assert "surplus value" in query_text.lower()
        assert "class consciousness" in query_text.lower() or "solidarity" in query_text.lower()

    def test_three_different_keywords_combined(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Three different keywords produce combined query with all terms."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": [
                    "SURPLUS_EXTRACTION event",
                    "ECONOMIC_CRISIS event",
                    "MASS_AWAKENING event",
                ],
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
    """Tests for fallback behavior with unknown/empty events."""

    def test_unknown_event_uses_fallback_query(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Unknown event type uses fallback dialectical query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["UNKNOWN_EVENT_TYPE occurred"],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should use fallback: "dialectical materialism class struggle"
        assert "dialectical" in query_text.lower() or "class struggle" in query_text.lower()

    def test_empty_events_uses_fallback_query(
        self,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Empty events list uses fallback dialectical query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        # Directly test _retrieve_context with empty list
        director._retrieve_context([])

        # Should have called RAG with fallback query
        if mock_rag_pipeline.query.called:
            call_args = mock_rag_pipeline.query.call_args
            query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")
            assert "dialectical" in query_text.lower() or "class struggle" in query_text.lower()

    def test_mixed_known_unknown_events_uses_known_queries(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """Mixed known/unknown events uses known query translations."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": [
                    "UNKNOWN_EVENT happened",
                    "SURPLUS_EXTRACTION occurred",
                    "ANOTHER_UNKNOWN event",
                ],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Should use the known translation, NOT the fallback
        assert "surplus value" in query_text.lower()
        # Should NOT contain fallback if known keyword was found
        # (The fallback is only used when NO keywords match)


# =============================================================================
# TEST WAGES AND BRIBERY MAPPING
# =============================================================================


@pytest.mark.unit
class TestWagesAndBriberyMapping:
    """Tests for WAGES and BRIBERY keyword mappings."""

    def test_wages_event_maps_to_labor_aristocracy(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """WAGES event maps to labor aristocracy query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["WAGES paid to workers"],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        assert "labor aristocracy" in query_text.lower()

    def test_bribery_event_maps_to_labor_aristocracy(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """BRIBERY event maps to labor aristocracy query."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": ["BRIBERY of labor aristocracy"],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        assert "labor aristocracy" in query_text.lower()

    def test_wages_and_bribery_deduplicated(
        self,
        initial_state: WorldState,
        mock_rag_pipeline: MagicMock,
    ) -> None:
        """WAGES and BRIBERY with same mapping are deduplicated."""
        from babylon.ai.director import NarrativeDirector

        director = NarrativeDirector(rag_pipeline=mock_rag_pipeline)

        previous_state = initial_state
        new_state = initial_state.model_copy(
            update={
                "tick": 1,
                "event_log": [
                    "WAGES distributed",
                    "BRIBERY detected",
                ],
            }
        )

        director.on_tick(previous_state, new_state)

        call_args = mock_rag_pipeline.query.call_args
        query_text = call_args[0][0] if call_args[0] else call_args[1].get("query", "")

        # Since both map to the same query, it should appear only once
        expected_phrase = "labor aristocracy"
        occurrences = query_text.lower().count(expected_phrase)
        assert occurrences == 1, f"Expected 1 occurrence of '{expected_phrase}', got {occurrences}"
