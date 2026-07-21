"""Behavioral contract for the embedding-dimension seam (D5, ADR096).

The allowlisted embedding models pin the Archive column dimension. Unknown
pins fail LOUD (III.11): a silent wrong dimension corrupts the vector space.
"""

from __future__ import annotations

import pytest

from babylon.intelligence.embedding_dims import (
    EMBEDDING_DIMENSIONS,
    EmbeddingDimensionMismatch,
    assert_store_dimension,
    dimension_for,
)


def test_allowlisted_dims_match_adr096() -> None:
    assert EMBEDDING_DIMENSIONS["@cf/baai/bge-m3"] == 1024
    assert EMBEDDING_DIMENSIONS["@cf/baai/bge-base-en-v1.5"] == 768
    assert EMBEDDING_DIMENSIONS["embeddinggemma:latest"] == 768


def test_dimension_for_returns_pinned_dim() -> None:
    assert dimension_for("@cf/baai/bge-m3") == 1024
    assert dimension_for("embeddinggemma:latest") == 768


def test_dimension_for_unknown_pin_raises_loud() -> None:
    with pytest.raises(KeyError):
        dimension_for("@cf/unknown/model")


def test_assert_store_dimension_ok_when_matched() -> None:
    # No raise == pass.
    assert_store_dimension("@cf/baai/bge-base-en-v1.5", 768)


def test_assert_store_dimension_mismatch_raises() -> None:
    with pytest.raises(EmbeddingDimensionMismatch) as exc:
        assert_store_dimension("@cf/baai/bge-m3", 768)
    assert "1024" in str(exc.value) and "768" in str(exc.value)


def test_assert_store_dimension_unknown_pin_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        assert_store_dimension("@cf/unknown/model", 768)
