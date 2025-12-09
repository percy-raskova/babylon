"""Tests for EmbeddingManager asyncio event loop compatibility.

TDD Red Phase: These tests expose a critical bug where asyncio.Semaphore
is created during __init__ without an event loop, then used inside
asyncio.run() which creates a NEW event loop - causing deadlock.

Bug Analysis:
1. EmbeddingManager.__init__() creates asyncio.Semaphore(4) at line 115
2. No event loop is running during __init__ in typical sync code
3. When sync wrappers call asyncio.run(self.aembed(...)), a NEW loop is created
4. The semaphore is bound to the implicit/no loop from __init__
5. Attempting to acquire semaphore in different loop context = DEADLOCK

The fix must ensure that asyncio primitives are created in the same
event loop where they are used, OR use thread-safe alternatives.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_llm_config() -> MagicMock:
    """Mock LLMConfig to avoid needing real config."""
    with patch("babylon.rag.embeddings.LLMConfig") as mock:
        mock.validate_embeddings.return_value = None
        mock.get_model_dimensions.return_value = 768
        mock.BATCH_SIZE = 10
        mock.is_ollama_embeddings.return_value = True
        mock.EMBEDDING_MODEL = "test-model"
        mock.get_embedding_headers.return_value = {}
        mock.get_embedding_url.return_value = "http://localhost:11434/api/embeddings"
        mock.REQUEST_TIMEOUT = 30.0
        mock.MAX_RETRIES = 3
        mock.RATE_LIMIT_RPM = 60
        yield mock


@pytest.fixture
def mock_metrics_collector() -> MagicMock:
    """Mock MetricsCollector to avoid side effects."""
    with patch("babylon.rag.embeddings.MetricsCollector") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


# =============================================================================
# TEST ASYNCIO EVENT LOOP COMPATIBILITY
# =============================================================================


@pytest.mark.unit
@pytest.mark.usefixtures("mock_llm_config", "mock_metrics_collector")
class TestEmbeddingManagerEventLoop:
    """Tests for asyncio event loop compatibility in EmbeddingManager.

    These tests verify that the sync wrappers (embed(), embed_batch())
    work correctly when called from sync code that has no running event loop.
    """

    def test_semaphore_not_created_in_init(self) -> None:
        """Semaphore should be created lazily, not in __init__.

        Creating asyncio.Semaphore in __init__ without a running event loop
        causes issues when asyncio.run() creates a new loop later.
        """
        from babylon.rag.embeddings import EmbeddingManager

        manager = EmbeddingManager()

        # After the fix, we use _semaphores dict for lazy per-loop creation
        # Check that the old _request_semaphore attribute no longer exists
        assert not hasattr(manager, "_request_semaphore"), (
            "Old _request_semaphore attribute still exists. "
            "Should use _semaphores dict for lazy per-loop creation."
        )

        # Check that _semaphores dict exists and is empty (lazy creation)
        assert hasattr(
            manager, "_semaphores"
        ), "Missing _semaphores dict for lazy semaphore creation."
        assert len(manager._semaphores) == 0, (
            "Semaphores should not be created in __init__. "
            "Must be lazy to work with asyncio.run()."
        )

    def test_sync_embed_completes_within_timeout(self) -> None:
        """Sync embed() should complete within reasonable timeout.

        If the event loop bug exists, this will hang indefinitely.
        We use a timeout to detect the hang.
        """
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.embeddings import EmbeddingManager

        manager = EmbeddingManager()
        chunk = DocumentChunk(id="test", content="Test content for embedding")

        # Mock aiohttp session to avoid network AND bypass rate limit decorators
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"embedding": [0.1] * 768})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False

        # Patch _get_session to return our mock
        async def mock_get_session() -> MagicMock:
            return mock_session

        with patch.object(manager, "_get_session", new=mock_get_session):
            # Run in separate thread with timeout to detect hang
            result_container: list[DocumentChunk | Exception] = []

            def run_embed() -> None:
                try:
                    result = manager.embed(chunk)
                    result_container.append(result)
                except Exception as e:
                    result_container.append(e)

            thread = threading.Thread(target=run_embed)
            thread.start()
            thread.join(timeout=5.0)  # 5 second timeout

            if thread.is_alive():
                pytest.fail(
                    "embed() hung - likely asyncio event loop deadlock. "
                    "The asyncio.Semaphore was created in a different event loop "
                    "than the one running asyncio.run()."
                )

            # Check result
            assert len(result_container) == 1
            if isinstance(result_container[0], Exception):
                raise result_container[0]

            result = result_container[0]
            assert result.embedding is not None
            assert len(result.embedding) == 768

    def test_multiple_sync_embeds_do_not_deadlock(self) -> None:
        """Multiple sequential sync embed() calls should not deadlock.

        Each asyncio.run() creates a new event loop. If the semaphore
        is bound to the first loop, subsequent calls will deadlock.
        """
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.embeddings import EmbeddingManager

        manager = EmbeddingManager()

        # Mock the API call
        async def mock_generate(_content: str) -> list[float]:
            return [0.1] * 768

        with patch.object(manager, "_generate_embedding_api", new=mock_generate):
            chunks = [DocumentChunk(id=f"test{i}", content=f"Test content {i}") for i in range(3)]

            # Run multiple embeds with timeout detection
            def run_sequential_embeds() -> list[DocumentChunk]:
                results = []
                for chunk in chunks:
                    result = manager.embed(chunk)
                    results.append(result)
                return results

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_sequential_embeds)
                try:
                    results = future.result(timeout=10.0)
                except concurrent.futures.TimeoutError:
                    pytest.fail(
                        "Sequential embed() calls hung - event loop deadlock. "
                        "Each asyncio.run() creates new loop but semaphore is "
                        "bound to first loop."
                    )

            assert len(results) == 3
            for result in results:
                assert result.embedding is not None

    def test_sync_embed_batch_completes_within_timeout(self) -> None:
        """Sync embed_batch() should complete within reasonable timeout."""
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.embeddings import EmbeddingManager

        manager = EmbeddingManager()
        chunks = [DocumentChunk(id=f"test{i}", content=f"Test content {i}") for i in range(5)]

        # Mock the API call
        async def mock_generate(_content: str) -> list[float]:
            return [0.1] * 768

        with patch.object(manager, "_generate_embedding_api", new=mock_generate):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(manager.embed_batch, chunks)
                try:
                    results = future.result(timeout=15.0)
                except concurrent.futures.TimeoutError:
                    pytest.fail("embed_batch() hung - likely asyncio event loop deadlock.")

            assert len(results) == 5
            for result in results:
                assert result.embedding is not None


@pytest.mark.unit
@pytest.mark.usefixtures("mock_llm_config", "mock_metrics_collector")
class TestEmbeddingManagerSessionLifecycle:
    """Tests for aiohttp.ClientSession lifecycle management.

    The session must be created in the same event loop where it's used.
    """

    def test_session_created_lazily_per_loop(self) -> None:
        """HTTP session should be created lazily within the async context.

        Creating session in __init__ and using it in asyncio.run() causes
        'attached to a different loop' errors.
        """
        from babylon.rag.embeddings import EmbeddingManager

        manager = EmbeddingManager()

        # Sessions dict should be empty before any async call
        assert hasattr(manager, "_sessions"), "Missing _sessions dict for lazy session creation."
        assert len(manager._sessions) == 0, (
            "Sessions should not be created in __init__. "
            "Must be lazy to work with asyncio.run()."
        )

    def test_session_works_across_multiple_asyncio_run_calls(self) -> None:
        """Session should work across multiple asyncio.run() calls.

        Each asyncio.run() creates a new event loop. The session must
        either be recreated per loop or handle this gracefully.
        """
        from babylon.rag.chunker import DocumentChunk
        from babylon.rag.embeddings import EmbeddingManager

        manager = EmbeddingManager()

        async def mock_generate(_content: str) -> list[float]:
            await asyncio.sleep(0.001)  # Simulate async work
            return [0.1] * 768

        with patch.object(manager, "_generate_embedding_api", new=mock_generate):
            # First call - creates session in loop 1
            chunk1 = DocumentChunk(id="test1", content="Content 1")
            result1 = manager.embed(chunk1)
            assert result1.embedding is not None

            # Second call - new loop created by asyncio.run()
            # If session is bound to loop 1, this will fail
            chunk2 = DocumentChunk(id="test2", content="Content 2")
            result2 = manager.embed(chunk2)
            assert result2.embedding is not None


@pytest.mark.unit
@pytest.mark.usefixtures("mock_llm_config", "mock_metrics_collector")
class TestRetrievalEventLoop:
    """Tests for Retriever asyncio event loop compatibility.

    The Retriever.query() sync wrapper must work correctly when called
    from code without a running event loop.
    """

    def test_retriever_query_sync_completes_within_timeout(self) -> None:
        """Retriever.query() sync wrapper should complete without hanging."""
        from babylon.rag.embeddings import EmbeddingManager
        from babylon.rag.retrieval import Retriever, VectorStore

        # Create mocks
        mock_vector_store = MagicMock(spec=VectorStore)
        mock_vector_store.query_similar.return_value = (
            ["id1"],  # ids
            ["doc content"],  # documents
            [[0.1] * 768],  # embeddings
            [{"source_file": "test.txt"}],  # metadatas
            [0.1],  # distances
        )

        manager = EmbeddingManager()

        async def mock_generate(_content: str) -> list[float]:
            return [0.1] * 768

        retriever = Retriever(
            vector_store=mock_vector_store,
            embedding_manager=manager,
        )

        with patch.object(manager, "_generate_embedding_api", new=mock_generate):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(retriever.query, "test query", 5)
                try:
                    response = future.result(timeout=10.0)
                except concurrent.futures.TimeoutError:
                    pytest.fail(
                        "Retriever.query() hung - asyncio event loop deadlock. "
                        "EmbeddingManager semaphore bound to wrong loop."
                    )

            assert response is not None
            assert response.query == "test query"


@pytest.mark.unit
@pytest.mark.usefixtures("mock_llm_config", "mock_metrics_collector")
class TestRagPipelineEventLoop:
    """Tests for RagPipeline asyncio event loop compatibility."""

    def test_rag_pipeline_query_sync_completes_within_timeout(self) -> None:
        """RagPipeline.query() sync wrapper should complete without hanging."""
        from babylon.rag.rag_pipeline import RagConfig, RagPipeline

        # Mock ChromaManager to avoid real DB
        with patch("babylon.rag.rag_pipeline.ChromaManager") as mock_chroma:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 10
            mock_collection.query.return_value = {
                "ids": [["id1"]],
                "documents": [["test doc"]],
                "embeddings": [[[0.1] * 768]],
                "metadatas": [[{"source_file": "test.txt"}]],
                "distances": [[0.1]],
            }
            mock_chroma.return_value.get_or_create_collection.return_value = mock_collection

            # Mock embedding generation
            with patch(
                "babylon.rag.embeddings.EmbeddingManager._generate_embedding_api"
            ) as mock_embed:

                async def mock_generate(_content: str) -> list[float]:
                    return [0.1] * 768

                mock_embed.side_effect = mock_generate

                config = RagConfig(collection_name="test_collection")
                pipeline = RagPipeline(config=config)

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(pipeline.query, "test query", 3)
                    try:
                        response = future.result(timeout=10.0)
                    except concurrent.futures.TimeoutError:
                        pytest.fail("RagPipeline.query() hung - asyncio event loop deadlock.")

                # If we got here, no deadlock occurred
                assert response is not None
