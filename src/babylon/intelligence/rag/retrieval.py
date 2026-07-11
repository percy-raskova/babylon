"""Query and retrieval interface for the RAG system.

Uses VectorStoreProtocol from babylon.persistence for backend-agnostic
vector storage. Implementations include PgVectorStore (Feature 037).
"""

import logging
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from babylon.intelligence.rag.chunker import DocumentChunk
from babylon.intelligence.rag.embeddings import EmbeddingManager
from babylon.intelligence.rag.exceptions import RagError

if TYPE_CHECKING:
    from babylon.persistence.protocols import VectorStoreProtocol

logger = logging.getLogger(__name__)


class QueryResult(BaseModel):
    """Represents a single query result with similarity score."""

    model_config = ConfigDict(validate_assignment=True)

    chunk: DocumentChunk
    similarity_score: float
    distance: float = 0.0
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def convert_similarity_to_distance(self) -> "QueryResult":
        """Convert similarity score to distance if not provided."""
        if self.distance == 0.0 and self.similarity_score > 0.0:
            # Convert cosine similarity to distance
            object.__setattr__(self, "distance", 1.0 - self.similarity_score)
        return self


class QueryResponse(BaseModel):
    """Represents the complete response to a query."""

    model_config = ConfigDict(validate_assignment=True)

    query: str
    results: list[QueryResult] = Field(default_factory=list)
    total_results: int = 0
    processing_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    search_time_ms: float = 0.0
    metadata: dict[str, Any] | None = None

    def get_top_k(self, k: int) -> list[QueryResult]:
        """Get the top k results by similarity score."""
        return sorted(self.results, key=lambda x: x.similarity_score, reverse=True)[:k]

    def get_combined_context(self, max_length: int = 4000, separator: str = "\n\n") -> str:
        """Combine result chunks into a single context string."""
        context_parts = []
        current_length = 0

        for result in sorted(self.results, key=lambda x: x.similarity_score, reverse=True):
            chunk_text = result.chunk.content
            if current_length + len(chunk_text) + len(separator) <= max_length:
                context_parts.append(chunk_text)
                current_length += len(chunk_text) + len(separator)
            else:
                # Try to fit partial content
                remaining = max_length - current_length - len(separator)
                if remaining > 100:  # Only add if meaningful amount left
                    context_parts.append(chunk_text[:remaining] + "...")
                break

        return separator.join(context_parts)


class Retriever:
    """High-level retrieval interface for RAG queries.

    Uses VectorStoreProtocol for backend-agnostic similarity search.
    """

    def __init__(
        self,
        vector_store: "VectorStoreProtocol",
        embedding_manager: EmbeddingManager,
    ):
        """Initialize the retriever.

        Args:
            vector_store: Any VectorStoreProtocol implementation
            embedding_manager: EmbeddingManager for query embedding
        """
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    async def aquery(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.0,
        metadata_filter: dict[str, Any] | None = None,
    ) -> QueryResponse:
        """Asynchronously query for relevant document chunks.

        Args:
            query: Query text to search for
            k: Number of results to return
            similarity_threshold: Minimum similarity score for results
            metadata_filter: Optional filters for chunk metadata

        Returns:
            QueryResponse with results and timing information

        Raises:
            RagError: If query processing fails
        """
        start_time = time.perf_counter()

        try:
            # Create a temporary object for embedding the query
            query_obj = DocumentChunk(id="query", content=query)

            # Generate embedding for the query
            embed_start = time.perf_counter()
            embedded_query = await self.embedding_manager.aembed(query_obj)
            embed_time = (time.perf_counter() - embed_start) * 1000

            if embedded_query.embedding is None:
                raise RagError(
                    message="Failed to generate query embedding",
                    error_code="RAG_311",
                    details={"query": query[:100]},
                )

            # Search for similar chunks
            search_start = time.perf_counter()
            ids, documents, embeddings, metadatas, distances = self.vector_store.query_similar(
                query_embedding=embedded_query.embedding,
                k=k,
                where=metadata_filter,
            )
            search_time = (time.perf_counter() - search_start) * 1000

            # Convert results to QueryResult objects
            results = []
            for _i, (chunk_id, doc, embedding, metadata, distance) in enumerate(
                zip(ids, documents, embeddings, metadatas, distances, strict=False)
            ):
                similarity_score = max(0.0, 1.0 - distance)

                if similarity_score >= similarity_threshold:
                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=doc,
                        source_file=metadata.get("source_file") if metadata else None,
                        chunk_index=metadata.get("chunk_index", 0) if metadata else 0,
                        start_char=metadata.get("start_char", 0) if metadata else 0,
                        end_char=metadata.get("end_char", 0) if metadata else 0,
                        metadata=metadata,
                        embedding=embedding,
                    )

                    result = QueryResult(
                        chunk=chunk,
                        similarity_score=similarity_score,
                        distance=distance,
                        metadata=metadata,
                    )
                    results.append(result)

            total_time = (time.perf_counter() - start_time) * 1000

            response = QueryResponse(
                query=query,
                results=results,
                total_results=len(results),
                processing_time_ms=total_time,
                embedding_time_ms=embed_time,
                search_time_ms=search_time,
                metadata={
                    "requested_k": k,
                    "similarity_threshold": similarity_threshold,
                    "metadata_filter": metadata_filter,
                },
            )

            logger.info(
                f"Query processed in {total_time:.2f}ms: {len(results)} results for '{query[:50]}...'"
            )

            return response

        except Exception as e:
            raise RagError(
                message=f"Query processing failed: {str(e)}",
                error_code="RAG_310",
                details={"query": query[:100]},
            ) from e

    def query(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.0,
        metadata_filter: dict[str, Any] | None = None,
    ) -> QueryResponse:
        """Synchronously query for relevant document chunks.

        Args:
            query: Query text to search for
            k: Number of results to return
            similarity_threshold: Minimum similarity score for results
            metadata_filter: Optional filters for chunk metadata

        Returns:
            QueryResponse with results and timing information

        Raises:
            RagError: If query processing fails
        """
        import asyncio

        return asyncio.run(self.aquery(query, k, similarity_threshold, metadata_filter))
