"""Regression tests for RAG retrieval system.

Tests for QueryResult, QueryResponse, and Retriever functionality.
VectorStore-specific tests have been removed (ChromaDB removed in favor of pgvector).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from babylon.intelligence.rag.chunker import DocumentChunk
from babylon.intelligence.rag.retrieval import QueryResponse, QueryResult

# =============================================================================
# QueryResult and QueryResponse Tests
# =============================================================================


@pytest.mark.unit
class TestQueryResultProcessing:
    """Tests for QueryResult and QueryResponse processing."""

    def test_query_result_converts_similarity_to_distance(self) -> None:
        """QueryResult correctly converts similarity to distance."""
        chunk = DocumentChunk(id="test", content="Test content")
        result = QueryResult(
            chunk=chunk,
            similarity_score=0.8,
        )

        assert result.similarity_score == 0.8
        assert result.distance == pytest.approx(0.2, rel=0.01)

    def test_query_response_get_top_k(self) -> None:
        """QueryResponse.get_top_k returns correct top results."""
        results = [
            QueryResult(
                chunk=DocumentChunk(id=f"test{i}", content=f"Content {i}"),
                similarity_score=score,
            )
            for i, score in enumerate([0.5, 0.9, 0.7, 0.3])
        ]

        response = QueryResponse(
            query="test",
            results=results,
            total_results=4,
        )

        top_2 = response.get_top_k(2)
        assert len(top_2) == 2
        assert top_2[0].similarity_score == 0.9
        assert top_2[1].similarity_score == 0.7

    def test_query_response_get_combined_context_respects_max_length(self) -> None:
        """QueryResponse.get_combined_context respects max_length."""
        results = [
            QueryResult(
                chunk=DocumentChunk(id=f"test{i}", content="A" * 100),
                similarity_score=1.0 - i * 0.1,
            )
            for i in range(5)
        ]

        response = QueryResponse(
            query="test",
            results=results,
            total_results=5,
        )

        context = response.get_combined_context(max_length=250, separator="\n\n")
        assert len(context) <= 250


# =============================================================================
# Retriever Tests (with mock VectorStoreProtocol)
# =============================================================================


@pytest.mark.unit
class TestRetrieverWithProtocol:
    """Tests for Retriever using mock VectorStoreProtocol."""

    def test_retriever_returns_results(self) -> None:
        """Retriever returns results from VectorStoreProtocol."""
        from babylon.intelligence.rag.embeddings import EmbeddingManager
        from babylon.intelligence.rag.retrieval import Retriever

        # Mock vector store implementing VectorStoreProtocol
        mock_store = MagicMock()
        mock_store.query_similar.return_value = (
            ["id1", "id2"],
            ["doc content 1", "doc content 2"],
            [[0.1] * 768, [0.2] * 768],
            [{"source_file": "test1.txt"}, {"source_file": "test2.txt"}],
            [0.3, 0.4],
        )

        # Mock EmbeddingManager
        mock_embedding_manager = MagicMock(spec=EmbeddingManager)
        embedded_query = DocumentChunk(id="query", content="test query")
        embedded_query.embedding = [0.1] * 768
        mock_embedding_manager.aembed = AsyncMock(return_value=embedded_query)

        retriever = Retriever(
            vector_store=mock_store,
            embedding_manager=mock_embedding_manager,
        )

        import asyncio

        response = asyncio.run(retriever.aquery("test query", k=5))

        assert len(response.results) == 2
        assert response.results[0].similarity_score == pytest.approx(0.7)
        assert response.results[1].similarity_score == pytest.approx(0.6)

    def test_retriever_filters_by_similarity_threshold(self) -> None:
        """Retriever filters results below similarity_threshold."""
        from babylon.intelligence.rag.embeddings import EmbeddingManager
        from babylon.intelligence.rag.retrieval import Retriever

        mock_store = MagicMock()
        mock_store.query_similar.return_value = (
            ["id1", "id2"],
            ["doc1", "doc2"],
            [[0.1] * 768, [0.2] * 768],
            [{}, {}],
            [0.2, 0.9],  # 0.2 distance = 0.8 similarity, 0.9 distance = 0.1 similarity
        )

        mock_embedding_manager = MagicMock(spec=EmbeddingManager)
        embedded_query = DocumentChunk(id="query", content="test")
        embedded_query.embedding = [0.1] * 768
        mock_embedding_manager.aembed = AsyncMock(return_value=embedded_query)

        retriever = Retriever(
            vector_store=mock_store,
            embedding_manager=mock_embedding_manager,
        )

        import asyncio

        response = asyncio.run(retriever.aquery("test", k=5, similarity_threshold=0.5))

        # Only id1 (0.8 similarity) should pass threshold of 0.5
        assert len(response.results) == 1
        assert response.results[0].similarity_score == pytest.approx(0.8)
