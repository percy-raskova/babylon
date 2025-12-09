"""Embedding management for the RAG system.

Supports both local (Ollama) and cloud (OpenAI) embedding providers.
Default: Ollama with embeddinggemma for fully offline operation.
"""

import asyncio
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol, TypeVar

import aiohttp
import backoff
from ratelimit import limits, sleep_and_retry

from babylon.config.llm_config import LLMConfig
from babylon.metrics.collector import MetricsCollector

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Exception raised for embedding service failures."""

    pass


class EmbeddingAPIError(EmbeddingError):
    """Exception raised for embedding API-specific errors."""

    pass


# Backward compatibility alias
OpenAIError = EmbeddingAPIError


class Embeddable(Protocol):
    """Protocol for objects that can be embedded."""

    id: str
    content: str
    embedding: list[float] | None


# TypeVar for preserving specific Embeddable subtype through operations
E = TypeVar("E", bound=Embeddable)


class EmbeddingManager:
    """Manages embeddings for RAG objects.

    The EmbeddingManager handles:
    - Generating embeddings via Ollama (local) or OpenAI (cloud) API
    - Caching embeddings for reuse with LRU eviction
    - Rate limiting and retry logic
    - Batch operations for efficiency
    - Error handling and recovery
    - Performance metrics collection
    - Concurrent operations

    Default: Ollama with embeddinggemma for fully offline operation.
    """

    def __init__(
        self,
        embedding_dimension: int | None = None,
        batch_size: int | None = None,
        max_cache_size: int = 1000,
        max_concurrent_requests: int = 4,
    ):
        """Initialize the embedding manager.

        Args:
            embedding_dimension: Size of embedding vectors (default: from LLMConfig)
            batch_size: Number of objects to embed in each batch (default: from LLMConfig)
            max_cache_size: Maximum number of embeddings to keep in cache (default: 1000)
            max_concurrent_requests: Maximum number of concurrent embedding requests (default: 4)

        Raises:
            ValueError: If embedding configuration is invalid
        """
        # Validate embedding configuration
        LLMConfig.validate_embeddings()

        # Custom dimensions must match the model's output
        if (
            embedding_dimension is not None
            and embedding_dimension != LLMConfig.get_model_dimensions()
        ):
            raise ValueError(
                f"Custom embedding dimensions not supported. "
                f"Model {LLMConfig.EMBEDDING_MODEL} outputs {LLMConfig.get_model_dimensions()} dimensions."
            )

        self.embedding_dimension = LLMConfig.get_model_dimensions()
        self.batch_size = batch_size or LLMConfig.BATCH_SIZE
        self.max_cache_size = max_cache_size
        self.max_concurrent_requests = max_concurrent_requests
        self._is_ollama = LLMConfig.is_ollama_embeddings()

        # Use OrderedDict for LRU cache implementation
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        # Use RLock (re-entrant) because cache_size property is called inside locked blocks
        self._cache_lock = threading.RLock()

        # Thread pool for concurrent operations
        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrent_requests)

        # Semaphores per event loop (lazy creation to avoid asyncio.run() deadlock)
        # Each asyncio.run() creates a new event loop, so we cache semaphores per loop
        self._semaphores: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}

        # HTTP sessions per event loop (aiohttp.ClientSession is also loop-bound)
        self._sessions: dict[asyncio.AbstractEventLoop, aiohttp.ClientSession] = {}

        # Initialize metrics collector
        self.metrics = MetricsCollector()

        # Record initialization metrics
        provider = "ollama" if self._is_ollama else "openai"
        self.metrics.record_metric(
            name="embedding_manager_init",
            value=1.0,
            context=f"provider={provider},model={LLMConfig.EMBEDDING_MODEL},dim={self.embedding_dimension}",
        )
        logger.info(
            f"EmbeddingManager initialized: provider={provider}, model={LLMConfig.EMBEDDING_MODEL}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for the current event loop.

        Each asyncio.run() call creates a new event loop. aiohttp.ClientSession
        is bound to the loop where it was created, so we must create one per loop
        to avoid 'attached to a different loop' errors.

        Returns:
            ClientSession for the currently running event loop
        """
        loop = asyncio.get_running_loop()

        # Check if we have a valid session for this loop
        if loop in self._sessions and not self._sessions[loop].closed:
            return self._sessions[loop]

        # Clean up any closed loop entries
        closed_loops = [k for k in self._sessions if k.is_closed()]
        for closed_loop in closed_loops:
            del self._sessions[closed_loop]

        # Create new session for this loop
        session = aiohttp.ClientSession(
            headers=LLMConfig.get_embedding_headers(),
            timeout=aiohttp.ClientTimeout(total=LLMConfig.REQUEST_TIMEOUT),
        )
        self._sessions[loop] = session
        return session

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for the current event loop.

        Each asyncio.run() call creates a new event loop. Semaphores are
        bound to the loop where they're created, so we must lazily create
        one per loop to avoid deadlocks when sync wrappers use asyncio.run().

        Returns:
            Semaphore for the currently running event loop
        """
        loop = asyncio.get_running_loop()

        # Check if we have a semaphore for this loop
        if loop not in self._semaphores or loop.is_closed():
            # Clean up any closed loop entries
            closed_loops = [k for k in self._semaphores if k.is_closed()]
            for closed_loop in closed_loops:
                del self._semaphores[closed_loop]

            # Create new semaphore for this loop
            self._semaphores[loop] = asyncio.Semaphore(self.max_concurrent_requests)

        return self._semaphores[loop]

    @property
    def cache_size(self) -> int:
        """Get current number of embeddings in cache."""
        with self._cache_lock:
            return len(self._cache)

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=LLMConfig.MAX_RETRIES,
        max_time=30,
    )
    @sleep_and_retry
    @limits(calls=LLMConfig.RATE_LIMIT_RPM, period=60)
    async def _generate_embedding_api(self, content: str) -> list[float]:
        """Generate embedding using configured provider (Ollama or OpenAI).

        Args:
            content: Text content to embed

        Returns:
            List[float]: Embedding vector

        Raises:
            EmbeddingAPIError: If the API request fails
        """
        session = await self._get_session()

        # Build request payload based on provider
        if self._is_ollama:
            # Ollama embedding API format
            payload = {"model": LLMConfig.EMBEDDING_MODEL, "prompt": content}
        else:
            # OpenAI embedding API format
            payload = {"input": content, "model": LLMConfig.EMBEDDING_MODEL}

        try:
            async with session.post(
                LLMConfig.get_embedding_url(),
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise EmbeddingAPIError(
                        f"Embedding API error (status {response.status}): {error_text}"
                    )

                data = await response.json()

                # Parse response based on provider
                if self._is_ollama:
                    # Ollama returns: {"embedding": [...]}
                    embedding: list[float] = data["embedding"]
                else:
                    # OpenAI returns: {"data": [{"embedding": [...]}]}
                    embedding = data["data"][0]["embedding"]

                return embedding

        except aiohttp.ClientError as e:
            raise EmbeddingAPIError(f"API request failed: {str(e)}") from e
        except TimeoutError as e:
            raise EmbeddingAPIError("API request timed out") from e
        except KeyError as e:
            raise EmbeddingAPIError(f"Unexpected API response format: {str(e)}") from e
        except EmbeddingAPIError:
            raise
        except Exception as e:
            raise EmbeddingAPIError(f"Unexpected error: {str(e)}") from e

    async def aembed(self, obj: E) -> E:
        """Asynchronously generate and attach embedding for a single object.

        Args:
            obj: Object to embed

        Returns:
            Object with embedding attached

        Raises:
            ValueError: If object content is invalid
            EmbeddingError: If embedding generation fails
        """
        if not obj.content:
            raise ValueError("Cannot embed empty content")

        start_time = time.time()
        cache_key = self._get_cache_key(obj.content)

        # Check cache first
        with self._cache_lock:
            if cache_key in self._cache:
                # Move to end to mark as most recently used
                embedding = self._cache.pop(cache_key)
                self._cache[cache_key] = embedding
                obj.embedding = embedding

                # Record cache hit
                self.metrics.record_cache_event("embedding", hit=True)
                self.metrics.record_metric(
                    name="embedding_cache_lookup_time",
                    value=time.time() - start_time,
                    context="cache_hit",
                    object_id=obj.id,
                )
                return obj

        # Record cache miss
        self.metrics.record_cache_event("embedding", hit=False)

        try:
            # Acquire semaphore to limit concurrent requests
            async with self._get_semaphore():
                # Generate new embedding
                embedding_start = time.time()
                embedding = await self._generate_embedding_api(obj.content)

                # Record embedding generation time
                self.metrics.record_metric(
                    name="embedding_generation_time",
                    value=time.time() - embedding_start,
                    context="generation",
                    object_id=obj.id,
                )

                # Add to cache with LRU eviction if needed
                with self._cache_lock:
                    if self.cache_size >= self.max_cache_size:
                        # Remove least recently used (first item)
                        self._cache.popitem(last=False)
                        self.metrics.record_metric(
                            name="cache_eviction", value=1.0, context="lru_eviction"
                        )

                    self._cache[cache_key] = embedding
                    obj.embedding = embedding

                # Record memory usage
                self.metrics.record_memory_usage(
                    len(self._cache) * self.embedding_dimension * 8  # Approximate bytes used
                )

                # Record total operation time
                self.metrics.record_metric(
                    name="embedding_total_time",
                    value=time.time() - start_time,
                    context="total",
                    object_id=obj.id,
                )

                return obj

        except Exception as e:
            # Record error
            self.metrics.record_metric(
                name="embedding_error", value=1.0, context=str(e), object_id=obj.id
            )
            logger.error(f"Failed to generate embedding for object {obj.id}: {str(e)}")
            raise

    def embed(self, obj: E) -> E:
        """Synchronously generate and attach embedding for a single object.

        This is a convenience wrapper around aembed for synchronous code.
        For better performance in async contexts, use aembed directly.

        Args:
            obj: Object to embed

        Returns:
            Object with embedding attached

        Raises:
            ValueError: If object content is invalid
            EmbeddingError: If embedding generation fails
        """
        return asyncio.run(self.aembed(obj))

    async def aembed_batch(self, objects: Sequence[E]) -> list[E]:
        """Asynchronously generate embeddings for multiple objects efficiently.

        Args:
            objects: List of objects to embed

        Returns:
            List of objects with embeddings attached

        Raises:
            EmbeddingError: If any object's embedding generation fails
        """
        start_time = time.time()
        results: list[E] = []
        batch: list[E] = []

        try:
            for obj in objects:
                if len(batch) >= self.batch_size:
                    batch_start = time.time()
                    # Process batch concurrently
                    batch_results = await asyncio.gather(*[self.aembed(obj) for obj in batch])
                    results.extend(batch_results)
                    # Record batch processing time
                    self.metrics.record_metric(
                        name="batch_processing_time",
                        value=time.time() - batch_start,
                        context=f"batch_size_{len(batch)}",
                    )
                    batch = []
                batch.append(obj)

            if batch:
                batch_start = time.time()
                # Process remaining batch concurrently
                batch_results = await asyncio.gather(*[self.aembed(obj) for obj in batch])
                results.extend(batch_results)
                self.metrics.record_metric(
                    name="batch_processing_time",
                    value=time.time() - batch_start,
                    context=f"batch_size_{len(batch)}",
                )

            # Record batch metrics
            total_time = time.time() - start_time
            self.metrics.record_metric(
                name="batch_embedding_time",
                value=total_time,
                context=f"batch_size_{len(objects)}",
            )
            self.metrics.record_metric(
                name="batch_throughput",
                value=len(objects) / total_time,
                context="objects_per_second",
            )

            return results

        except Exception as e:
            # Record error
            self.metrics.record_metric(
                name="batch_embedding_error",
                value=1.0,
                context=f"failed_at_{len(results)}_of_{len(objects)}",
            )
            # Log the error and number of successful embeddings
            logger.error(
                f"Batch embedding failed after {len(results)} successful embeddings: {str(e)}"
            )
            raise EmbeddingError(
                f"Batch embedding failed: {str(e)}. {len(results)} objects were successfully embedded."
            ) from e

    def embed_batch(self, objects: Sequence[E]) -> list[E]:
        """Synchronously generate embeddings for multiple objects efficiently.

        This is a convenience wrapper around aembed_batch for synchronous code.
        For better performance in async contexts, use aembed_batch directly.

        Args:
            objects: List of objects to embed

        Returns:
            List of objects with embeddings attached

        Raises:
            EmbeddingError: If any object's embedding generation fails
        """
        return asyncio.run(self.aembed_batch(objects))

    def debed(self, obj: E) -> E:
        """Remove embedding from an object.

        Args:
            obj: Object to remove embedding from

        Returns:
            Object with embedding removed
        """
        obj.embedding = None
        return obj

    def debed_batch(self, objects: Sequence[E]) -> list[E]:
        """Remove embeddings from multiple objects.

        Args:
            objects: List of objects to remove embeddings from

        Returns:
            List of objects with embeddings removed
        """
        return [self.debed(obj) for obj in objects]

    def _get_cache_key(self, content: str) -> str:
        """Generate cache key for content."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def close(self) -> None:
        """Close resources used by the embedding manager."""
        # Close all sessions across all event loops
        for session in self._sessions.values():
            if not session.closed:
                await session.close()
        self._sessions.clear()
        self._semaphores.clear()
        self._thread_pool.shutdown(wait=True)
