"""Unit tests for PgVectorStore (mocked psycopg).

Phase 9 (T050-T053): Semantic search with pgvector.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.persistence.pgvector_store import PgVectorStore

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def mock_cursor() -> MagicMock:
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone = MagicMock(return_value=None)
    cursor.fetchall = MagicMock(return_value=[])
    return cursor


@pytest.fixture()
def mock_conn(mock_cursor: MagicMock) -> MagicMock:
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor = MagicMock(return_value=mock_cursor)
    return conn


@pytest.fixture()
def mock_pool(mock_conn: MagicMock) -> MagicMock:
    pool = MagicMock()

    @contextmanager
    def mock_connection() -> Any:
        yield mock_conn

    pool.connection = mock_connection
    return pool


@pytest.fixture()
def store(mock_pool: MagicMock) -> PgVectorStore:
    return PgVectorStore(mock_pool, dimension=384, collection="test_collection")


# ══════════════════════════════════════════════════════════════════════
# add_chunks
# ══════════════════════════════════════════════════════════════════════


class TestAddChunks:
    """Tests for PgVectorStore.add_chunks."""

    def test_adds_dict_chunks(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """add_chunks inserts chunk dicts with embeddings."""
        chunks = [
            {
                "id": "chunk_1",
                "content": "Workers of the world unite",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"source": "manifesto.txt", "page": 1},
            },
        ]

        store.add_chunks(chunks)

        assert mock_cursor.executemany.called
        sql = mock_cursor.executemany.call_args[0][0]
        rows = mock_cursor.executemany.call_args[0][1]

        assert "INSERT INTO document_chunk" in sql
        assert "ON CONFLICT" in sql
        assert len(rows) == 1
        assert rows[0][0] == "chunk_1"  # chunk_id
        assert rows[0][1] == "test_collection"  # collection
        assert rows[0][2] == "Workers of the world unite"  # content

    def test_adds_object_chunks(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """add_chunks handles objects with attributes."""

        class MockChunk:
            def __init__(self) -> None:
                self.id = "chunk_obj_1"
                self.content = "The proletariat has nothing to lose"
                self.embedding = [0.4, 0.5, 0.6]
                self.metadata = {"chapter": 4}

        store.add_chunks([MockChunk()])

        rows = mock_cursor.executemany.call_args[0][1]
        assert rows[0][0] == "chunk_obj_1"

    def test_empty_chunks_is_noop(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """add_chunks returns early on empty list."""
        store.add_chunks([])
        assert mock_cursor.executemany.call_count == 0


# ══════════════════════════════════════════════════════════════════════
# query_similar
# ══════════════════════════════════════════════════════════════════════


class TestQuerySimilar:
    """Tests for PgVectorStore.query_similar."""

    def test_returns_similar_chunks(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """query_similar returns structured results."""
        mock_cursor.fetchall.return_value = [
            {
                "chunk_id": "c1",
                "content": "Document 1",
                "embedding": "[0.1,0.2,0.3]",
                "metadata": {"source": "a.txt"},
                "distance": 0.15,
            },
            {
                "chunk_id": "c2",
                "content": "Document 2",
                "embedding": "[0.4,0.5,0.6]",
                "metadata": {"source": "b.txt"},
                "distance": 0.25,
            },
        ]

        ids, docs, embs, metas, dists = store.query_similar(query_embedding=[0.1, 0.2, 0.3], k=5)

        assert ids == ["c1", "c2"]
        assert docs == ["Document 1", "Document 2"]
        assert len(embs) == 2
        assert embs[0] == [0.1, 0.2, 0.3]
        assert metas[0] == {"source": "a.txt"}
        assert dists == [0.15, 0.25]

    def test_cosine_distance_query(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """query_similar uses cosine distance operator (<=>)."""
        mock_cursor.fetchall.return_value = []

        store.query_similar(query_embedding=[0.1, 0.2], k=3)

        sql = mock_cursor.execute.call_args[0][0]
        assert "<=>" in sql  # cosine distance operator
        assert "ORDER BY distance" in sql
        assert "LIMIT" in sql

    def test_metadata_filter(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """query_similar applies JSONB containment filter."""
        mock_cursor.fetchall.return_value = []

        store.query_similar(query_embedding=[0.1], k=5, where={"source": "manifesto.txt"})

        sql = mock_cursor.execute.call_args[0][0]
        assert "metadata @>" in sql

    def test_returns_empty_on_no_results(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """query_similar returns empty lists when no matches."""
        mock_cursor.fetchall.return_value = []

        ids, docs, embs, metas, dists = store.query_similar(query_embedding=[0.1], k=5)

        assert ids == []
        assert docs == []
        assert embs == []
        assert metas == []
        assert dists == []


# ══════════════════════════════════════════════════════════════════════
# delete_chunks
# ══════════════════════════════════════════════════════════════════════


class TestDeleteChunks:
    """Tests for PgVectorStore.delete_chunks."""

    def test_deletes_by_ids(
        self,
        store: PgVectorStore,
        mock_conn: MagicMock,
    ) -> None:
        """delete_chunks removes chunks by ID list."""
        store.delete_chunks(["c1", "c2", "c3"])

        mock_conn.execute.assert_called_once()
        sql = mock_conn.execute.call_args[0][0]
        assert "DELETE FROM document_chunk" in sql
        assert "ANY" in sql

    def test_empty_ids_is_noop(
        self,
        store: PgVectorStore,
        mock_conn: MagicMock,
    ) -> None:
        """delete_chunks returns early on empty list."""
        store.delete_chunks([])
        assert mock_conn.execute.call_count == 0


# ══════════════════════════════════════════════════════════════════════
# get_collection_count
# ══════════════════════════════════════════════════════════════════════


class TestGetCollectionCount:
    """Tests for PgVectorStore.get_collection_count."""

    def test_returns_count(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """get_collection_count returns chunk count."""
        mock_cursor.fetchone.return_value = {"cnt": 42}

        count = store.get_collection_count()

        assert count == 42
        sql = mock_cursor.execute.call_args[0][0]
        assert "COUNT(*)" in sql
        assert "collection" in sql

    def test_returns_zero_when_empty(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """get_collection_count returns 0 for empty collection."""
        mock_cursor.fetchone.return_value = {"cnt": 0}
        assert store.get_collection_count() == 0

    def test_returns_zero_when_no_result(
        self,
        store: PgVectorStore,
        mock_cursor: MagicMock,
    ) -> None:
        """get_collection_count returns 0 when query returns None."""
        mock_cursor.fetchone.return_value = None
        assert store.get_collection_count() == 0
