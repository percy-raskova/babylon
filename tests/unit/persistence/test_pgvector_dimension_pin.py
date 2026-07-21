"""D5 construction guard: the store dimension must match the pinned model.

No database: the guard fires in ``__init__`` before any pool use, so a bare
object stands in for the psycopg pool.
"""

from __future__ import annotations

import pytest

from babylon.intelligence.embedding_dims import EmbeddingDimensionMismatch
from babylon.persistence.pgvector_store import PgVectorStore


class _UnusedPool:
    """The guard must not touch the pool; any use is a bug."""

    def connection(self) -> object:  # pragma: no cover - must never be called
        raise AssertionError("dimension guard must not open a connection")


def test_matching_pin_constructs() -> None:
    store = PgVectorStore(_UnusedPool(), dimension=768, model_pin="@cf/baai/bge-base-en-v1.5")
    assert store is not None


def test_mismatched_pin_raises() -> None:
    with pytest.raises(EmbeddingDimensionMismatch):
        PgVectorStore(_UnusedPool(), dimension=768, model_pin="@cf/baai/bge-m3")


def test_unknown_pin_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        PgVectorStore(_UnusedPool(), dimension=768, model_pin="@cf/unknown/model")


def test_no_pin_is_backward_compatible() -> None:
    # Legacy path: no pin supplied → no guard, no raise.
    store = PgVectorStore(_UnusedPool(), dimension=768)
    assert store is not None
