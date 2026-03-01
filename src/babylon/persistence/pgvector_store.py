"""PgVector-based vector store for semantic search (Feature 037).

Implements ``VectorStoreProtocol`` using PostgreSQL's pgvector extension
with HNSW indexing and cosine distance for the RAG pipeline.

Usage::

    from psycopg_pool import ConnectionPool
    from babylon.persistence.pgvector_store import PgVectorStore

    pool = ConnectionPool(conninfo="dbname=babylon")
    store = PgVectorStore(pool, dimension=1536)
    store.add_chunks(chunks)
    ids, docs, embeddings, metadatas, distances = store.query_similar(
        query_embedding=embedding, k=5
    )
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


class PgVectorStore:
    """PostgreSQL pgvector implementation of VectorStoreProtocol.

    Uses HNSW index with cosine distance for approximate nearest neighbor
    search over document chunk embeddings stored in the ``document_chunk`` table.

    Attributes:
        _pool: psycopg ConnectionPool.
        _dimension: Embedding vector dimension.
        _collection: Logical collection name for namespace isolation.
    """

    def __init__(
        self,
        pool: ConnectionPool[Connection[Any]],
        dimension: int = 1536,
        collection: str = "default",
    ) -> None:
        self._pool = pool
        self._dimension = dimension
        self._collection = collection

    def add_chunks(self, chunks: list[Any]) -> None:
        """Store document chunks with their embeddings.

        Each chunk should have: id, content, embedding, metadata.

        Args:
            chunks: List of chunk objects or dicts.
        """
        if not chunks:
            return

        with self._pool.connection() as conn, conn.cursor() as cur:
            rows = []
            for chunk in chunks:
                if isinstance(chunk, dict):
                    chunk_id = chunk.get("id", str(uuid4()))
                    content = chunk.get("content", "")
                    embedding = chunk.get("embedding", [])
                    metadata = chunk.get("metadata", {})
                    source = chunk.get("source", metadata.get("source"))
                    chunk_index = chunk.get("chunk_index", metadata.get("chunk_index", 0))
                else:
                    chunk_id = getattr(chunk, "id", str(uuid4()))
                    content = getattr(chunk, "content", "")
                    embedding = getattr(chunk, "embedding", [])
                    metadata = getattr(chunk, "metadata", {})
                    source = getattr(chunk, "source", None)
                    chunk_index = getattr(chunk, "chunk_index", 0)

                rows.append(
                    (
                        str(chunk_id),
                        self._collection,
                        content,
                        embedding,
                        json.dumps(metadata) if isinstance(metadata, dict) else metadata,
                        source,
                        chunk_index,
                    )
                )

            cur.executemany(
                """
                INSERT INTO document_chunk
                    (chunk_id, collection, content, embedding, metadata, source, chunk_index)
                VALUES (%s, %s, %s, %s::vector, %s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    source = EXCLUDED.source,
                    chunk_index = EXCLUDED.chunk_index
                """,
                rows,
            )

    def query_similar(
        self,
        query_embedding: list[float],
        k: int = 10,
        where: dict[str, Any] | None = None,
        _include: list[str] | None = None,
    ) -> tuple[list[str], list[str], list[list[float]], list[dict[str, Any]], list[float]]:
        """Find the k most similar chunks using cosine distance.

        Args:
            query_embedding: Query vector.
            k: Number of results.
            where: Optional metadata filter (key-value equality).
            include: Fields to include (ignored, all returned).

        Returns:
            Tuple of (ids, documents, embeddings, metadatas, distances).
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            if where:
                # Build JSONB containment filter
                cur.execute(
                    """
                    SELECT chunk_id, content, embedding::text, metadata,
                           embedding <=> %s::vector AS distance
                    FROM document_chunk
                    WHERE collection = %s AND metadata @> %s
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (query_embedding, self._collection, json.dumps(where), k),
                )
            else:
                cur.execute(
                    """
                    SELECT chunk_id, content, embedding::text, metadata,
                           embedding <=> %s::vector AS distance
                    FROM document_chunk
                    WHERE collection = %s
                    ORDER BY distance
                    LIMIT %s
                    """,
                    (query_embedding, self._collection, k),
                )

            rows = cur.fetchall()

        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        distances: list[float] = []

        for row in rows:
            ids.append(row["chunk_id"])
            documents.append(row["content"])
            # Parse embedding from text representation
            emb_text = row.get("embedding", "[]")
            if isinstance(emb_text, str):
                emb_text = emb_text.strip("[]")
                embeddings.append([float(x) for x in emb_text.split(",")] if emb_text else [])
            else:
                embeddings.append(emb_text if isinstance(emb_text, list) else [])
            meta = row.get("metadata", {})
            if isinstance(meta, str):
                meta = json.loads(meta)
            metadatas.append(meta if isinstance(meta, dict) else {})
            distances.append(float(row.get("distance", 0.0)))

        return ids, documents, embeddings, metadatas, distances

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        """Delete chunks by their IDs.

        Args:
            chunk_ids: List of chunk IDs to remove.
        """
        if not chunk_ids:
            return

        with self._pool.connection() as conn:
            # Use ANY for batch delete
            conn.execute(
                "DELETE FROM document_chunk WHERE chunk_id = ANY(%s) AND collection = %s",
                (chunk_ids, self._collection),
            )

    def get_collection_count(self) -> int:
        """Return the total number of chunks in this collection.

        Returns:
            Count of stored chunks.
        """
        with self._pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM document_chunk WHERE collection = %s",
                (self._collection,),
            )
            result = cur.fetchone()
            if result is None:
                return 0
            count: int = result["cnt"]
            return count


__all__ = ["PgVectorStore"]
