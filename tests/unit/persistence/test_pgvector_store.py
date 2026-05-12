"""Unit tests for PgVectorStore (mocked psycopg).

Phase 9 (T050-T053): Semantic search with pgvector.
Spec 061 US1 (T026-T028): canonical 768-dim default + FR-002 dimension preflight.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest

from babylon.config.llm_config import CANONICAL_EMBEDDING_DIM
from babylon.persistence.pgvector_store import (
    EmbeddingDimensionError,
    PgVectorStore,
)

# All embeddings in this file are 384-dim to match the test fixture's store.
# Spec 061 FR-002 (T030) now preflights the dimension before issuing any
# SQL, so embeddings of the wrong length would raise EmbeddingDimensionError
# in mock-based tests too. The TestDimensionPreflight class below exercises
# the failure path explicitly.
_TEST_DIM = 384


def _emb(seed: float) -> list[float]:
    """Return a 384-dim embedding seeded by ``seed`` (for variety in test data)."""
    return [seed] * _TEST_DIM


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
                "embedding": _emb(0.1),
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
                self.embedding = _emb(0.4)
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


# ══════════════════════════════════════════════════════════════════════
# spec 061 US1 T026-T028: dimension preflight + canonical default
# ══════════════════════════════════════════════════════════════════════


class TestCanonicalDimensionDefault:
    """T029: PgVectorStore() without an explicit dimension uses 768."""

    def test_default_dimension_is_canonical_768(self) -> None:
        pool = MagicMock()
        store = PgVectorStore(pool)
        assert store._dimension == CANONICAL_EMBEDDING_DIM == 768


class TestDimensionPreflight:
    """T028 / FR-002: dimension mismatch raises before any SQL is issued."""

    def test_add_chunks_rejects_wrong_dimension(self) -> None:
        """A 384-dim embedding fed to a 768-dim store raises before any
        connection is acquired. Asserts ``pool.connection`` was never
        called, so no SQL was issued."""
        pool = MagicMock()
        store = PgVectorStore(pool)  # canonical 768-dim
        wrong = [0.0] * 384

        with pytest.raises(EmbeddingDimensionError) as exc_info:
            store.add_chunks(
                [
                    {
                        "id": "bad-chunk",
                        "content": "x",
                        "embedding": wrong,
                        "metadata": {},
                    }
                ]
            )

        message = str(exc_info.value)
        assert "384" in message
        assert "768" in message
        assert "bad-chunk" in message
        pool.connection.assert_not_called()

    def test_empty_list_is_noop_and_does_not_raise(self) -> None:
        """add_chunks([]) skips the preflight loop AND the SQL call."""
        pool = MagicMock()
        store = PgVectorStore(pool)
        store.add_chunks([])
        pool.connection.assert_not_called()

    def test_preflight_uses_overridden_dimension(self) -> None:
        """A non-canonical dimension argument is honored by the preflight."""
        pool = MagicMock()
        store = PgVectorStore(pool, dimension=384)
        with pytest.raises(EmbeddingDimensionError):
            store.add_chunks(
                [
                    {
                        "id": "wrong",
                        "content": "x",
                        "embedding": [0.0] * 768,  # canonical dim but wrong here
                        "metadata": {},
                    }
                ]
            )
        pool.connection.assert_not_called()


# ══════════════════════════════════════════════════════════════════════
# spec 061 US1 T026-T027: roundtrip against real Postgres
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPgVectorStoreRoundtrip:
    """T026 + T027: ingest + query against the ``babylon_test`` database.

    Uses ``pg_pool`` fixture (port 5433). Skipped when no test DB is
    available.
    """

    _COLLECTION = "spec-061-us1"

    @pytest.fixture
    def live_store(self, pg_pool) -> PgVectorStore:
        # The babylon_test database may not have the pgvector extension or
        # the document_chunk table provisioned (depends on whether the spec
        # 061 migration set has been applied to the test DB). Skip cleanly
        # rather than fail loudly — the mock-based tests above cover the
        # FR-001/FR-002 contract on every test run.
        from psycopg.errors import UndefinedTable

        try:
            with pg_pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM document_chunk WHERE collection = %s",
                    (self._COLLECTION,),
                )
        except UndefinedTable:
            pytest.skip(
                "document_chunk table not present in babylon_test — apply spec 061 "
                "migrations 0006-0010 to the test DB to enable this test"
            )
        return PgVectorStore(pg_pool, collection=self._COLLECTION)

    def test_add_chunks_succeeds_with_canonical_dim(self, live_store: PgVectorStore) -> None:
        """T026: five 768-dim chunks ingest cleanly."""
        chunks = [
            {
                "id": f"chunk-{i}",
                "content": f"sample content {i}",
                "embedding": [float(i) / 100.0] * CANONICAL_EMBEDDING_DIM,
                "metadata": {"src": "spec-061-us1"},
            }
            for i in range(5)
        ]
        live_store.add_chunks(chunks)
        assert live_store.get_collection_count() == 5

    def test_query_similar_returns_k_results(self, live_store: PgVectorStore) -> None:
        """T027: query k=3 against 5 ingested chunks → 3 results, distances ascending."""
        chunks = []
        for i in range(5):
            embedding = [0.0] * CANONICAL_EMBEDDING_DIM
            embedding[i] = 1.0
            chunks.append(
                {
                    "id": f"q-{i}",
                    "content": f"q content {i}",
                    "embedding": embedding,
                    "metadata": {},
                }
            )
        live_store.add_chunks(chunks)

        query = [0.0] * CANONICAL_EMBEDDING_DIM
        query[0] = 1.0
        ids, _docs, _embeddings, _metadatas, distances = live_store.query_similar(
            query_embedding=query, k=3
        )

        assert len(ids) == 3
        assert ids[0] == "q-0"
        for a, b in zip(distances, distances[1:], strict=False):
            assert a <= b, f"distances not sorted ascending: {distances}"
