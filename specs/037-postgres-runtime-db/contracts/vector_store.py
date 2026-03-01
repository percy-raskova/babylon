"""Contract: VectorStoreProtocol for backend-agnostic semantic search.

Feature 037: Postgres Runtime Database
Abstracts the vector store interface so that ChromaDB (current) and
pgvector (new) can both be used without changing RagPipeline.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Backend-agnostic vector storage for semantic search.

    Implementations: ChromaDB VectorStore (existing), PgVectorStore (new).
    The RagPipeline and Retriever interact only through this protocol.
    """

    def add_chunks(self, chunks: list[Any]) -> None:
        """Store document chunks with their embeddings.

        Each chunk must have: id (str), content (str), embedding (list[float]),
        and optionally metadata (dict).

        :param chunks: List of Embeddable objects with populated embeddings.
        :raises RagError: If any chunk is missing an embedding.
        """
        ...

    def query_similar(
        self,
        query_embedding: list[float],
        k: int = 10,
        where: dict | None = None,
        include: list[str] | None = None,
    ) -> tuple[list[str], list[str], list[list[float]], list[dict], list[float]]:
        """Find the k most similar chunks to the query embedding.

        :param query_embedding: The query vector.
        :param k: Number of results to return.
        :param where: Optional metadata filter (e.g., {"session_id": "abc"}).
        :param include: Fields to include in results.
        :returns: Tuple of (ids, documents, embeddings, metadatas, distances).
        """
        ...

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        """Delete chunks by their IDs.

        :param chunk_ids: List of chunk IDs to remove.
        """
        ...

    def get_collection_count(self) -> int:
        """Return the total number of chunks in the store.

        :returns: Count of stored chunks.
        """
        ...
