"""Regression tests for RAG retrieval system.

These tests ensure we don't regress on bugs fixed during development.

Bug History:
- NoneType subscript error when ChromaDB returns None for "embeddings" key
  (fixed: lines 189-196 in retrieval.py with safe falsy checks)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_chroma_manager() -> MagicMock:
    """Create a mock ChromaManager."""
    manager = MagicMock()
    manager.get_or_create_collection.return_value = MagicMock()
    return manager


@pytest.fixture
def mock_collection() -> MagicMock:
    """Create a mock ChromaDB collection."""
    return MagicMock()


# =============================================================================
# REGRESSION: ChromaDB None Results Bug
# =============================================================================


@pytest.mark.unit
class TestVectorStoreQueryNoneHandling:
    """Tests for handling None values in ChromaDB query results.

    ChromaDB returns None for keys not included in the 'include' parameter.
    Before the fix, this caused:
        TypeError: 'NoneType' object is not subscriptable

    The fix ensures safe access with falsy checks:
        embeddings_result = results.get("embeddings")
        embeddings = embeddings_result[0] if embeddings_result else []
    """

    def test_handles_none_embeddings_in_query_results(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.query_similar handles None embeddings gracefully.

        This was the original bug: ChromaDB returns None for "embeddings"
        when not in include list, causing crash on results["embeddings"][0].
        """
        from babylon.rag.retrieval import VectorStore

        # Simulate ChromaDB returning None for embeddings (not in include list)
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "embeddings": None,  # THE BUG: None when not included
            "metadatas": [[{"source": "test1"}, {"source": "test2"}]],
            "distances": [[0.1, 0.2]],
        }
        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        # This should NOT raise TypeError
        ids, documents, embeddings, metadatas, distances = vector_store.query_similar(
            query_embedding=[0.1] * 768,
            k=5,
            include=["documents", "metadatas", "distances"],  # No embeddings
        )

        assert ids == ["id1", "id2"]
        assert documents == ["doc1", "doc2"]
        assert embeddings == []  # Should be empty list, not crash
        assert metadatas == [{"source": "test1"}, {"source": "test2"}]
        assert distances == [0.1, 0.2]

    def test_handles_none_documents_in_query_results(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.query_similar handles None documents gracefully."""
        from babylon.rag.retrieval import VectorStore

        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": None,  # None when not included
            "embeddings": [[[0.1] * 768]],
            "metadatas": [[{"source": "test"}]],
            "distances": [[0.1]],
        }
        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        ids, documents, embeddings, metadatas, distances = vector_store.query_similar(
            query_embedding=[0.1] * 768,
            k=5,
        )

        assert ids == ["id1"]
        assert documents == []  # Empty list, not crash
        assert len(embeddings) == 1

    def test_handles_none_metadatas_in_query_results(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.query_similar handles None metadatas gracefully."""
        from babylon.rag.retrieval import VectorStore

        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "embeddings": None,
            "metadatas": None,  # None when not included
            "distances": [[0.1]],
        }
        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        ids, documents, embeddings, metadatas, distances = vector_store.query_similar(
            query_embedding=[0.1] * 768,
            k=5,
        )

        assert ids == ["id1"]
        assert metadatas == []  # Empty list, not crash

    def test_handles_none_distances_in_query_results(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.query_similar handles None distances gracefully."""
        from babylon.rag.retrieval import VectorStore

        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "embeddings": None,
            "metadatas": [[{}]],
            "distances": None,  # None edge case
        }
        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        ids, documents, embeddings, metadatas, distances = vector_store.query_similar(
            query_embedding=[0.1] * 768,
            k=5,
        )

        assert distances == []  # Empty list, not crash

    def test_handles_empty_ids_in_query_results(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.query_similar handles empty results gracefully."""
        from babylon.rag.retrieval import VectorStore

        mock_collection.query.return_value = {
            "ids": [[]],  # Empty results
            "documents": [[]],
            "embeddings": None,
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        ids, documents, embeddings, metadatas, distances = vector_store.query_similar(
            query_embedding=[0.1] * 768,
            k=5,
        )

        assert ids == []
        assert documents == []
        assert embeddings == []
        assert metadatas == []
        assert distances == []

    def test_handles_missing_ids_key_entirely(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.query_similar handles missing keys gracefully."""
        from babylon.rag.retrieval import VectorStore

        # Extreme edge case: keys missing entirely
        mock_collection.query.return_value = {}
        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        ids, documents, embeddings, metadatas, distances = vector_store.query_similar(
            query_embedding=[0.1] * 768,
            k=5,
        )

        # All should be empty lists, not crashes
        assert ids == []
        assert documents == []
        assert embeddings == []
        assert metadatas == []
        assert distances == []


# =============================================================================
# REGRESSION: Query Result Processing
# =============================================================================


@pytest.mark.unit
class TestQueryResultProcessing:
    """Tests for QueryResult and QueryResponse processing."""

    def test_query_result_converts_similarity_to_distance(self) -> None:
        """QueryResult correctly converts similarity to distance."""
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.retrieval import QueryResult

        chunk = DocumentChunk(id="test", content="Test content")
        result = QueryResult(
            chunk=chunk,
            similarity_score=0.8,
            # distance not provided, should be calculated
        )

        assert result.similarity_score == 0.8
        assert result.distance == pytest.approx(0.2, rel=0.01)

    def test_query_response_get_top_k(self) -> None:
        """QueryResponse.get_top_k returns correct top results."""
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.retrieval import QueryResponse, QueryResult

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
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.retrieval import QueryResponse, QueryResult

        # Create chunks with known content lengths
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

        # Request max 250 chars - should get 2 full chunks + separator
        context = response.get_combined_context(max_length=250, separator="\n\n")

        # Should be under limit
        assert len(context) <= 250


# =============================================================================
# REGRESSION: VectorStore Add/Delete Operations
# =============================================================================


@pytest.mark.unit
class TestVectorStoreOperations:
    """Tests for VectorStore add and delete operations."""

    def test_add_chunks_validates_embeddings(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.add_chunks raises error for chunks without embeddings."""
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.exceptions import RagError
        from babylon.rag.retrieval import VectorStore

        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        # Chunk without embedding
        chunk = DocumentChunk(id="test", content="Test content")

        with pytest.raises(RagError) as exc_info:
            vector_store.add_chunks([chunk])

        assert exc_info.value.error_code == "RAG_301"
        assert "missing embeddings" in exc_info.value.message.lower()

    def test_add_chunks_handles_empty_list(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.add_chunks handles empty list gracefully."""
        from babylon.rag.retrieval import VectorStore

        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        # Should not raise
        vector_store.add_chunks([])

        # Collection.add should not be called
        mock_collection.add.assert_not_called()

    def test_delete_chunks_handles_empty_list(
        self, mock_chroma_manager: MagicMock, mock_collection: MagicMock
    ) -> None:
        """VectorStore.delete_chunks handles empty list gracefully."""
        from babylon.rag.retrieval import VectorStore

        mock_chroma_manager.get_or_create_collection.return_value = mock_collection

        vector_store = VectorStore(
            collection_name="test",
            chroma_manager=mock_chroma_manager,
        )

        # Should not raise
        vector_store.delete_chunks([])

        # Collection.delete should not be called
        mock_collection.delete.assert_not_called()
