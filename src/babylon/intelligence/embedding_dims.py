"""The embedding-dimension seam (D5, ADR096).

The allowlisted embedding models pin the Archive's ``vector(N)`` column
dimension: bge-m3 → 1024 (dense dim verified 2026-07-20 from BAAI's model
card / config.json hidden_size), bge-base-en-v1.5 → 768, the Ollama default
embeddinggemma → 768. All are under the pgvector HNSW 2000-dim index cap.

A campaign's column dimension is fixed at creation (III.6 pins); changing the
embedding model mid-campaign is a schema migration, not a config change. This
module is the single source of truth reconciling three numbers: the pinned
model, the store's configured dimension, and the DB column type. An unknown
pin fails LOUD (KeyError) — a silently-wrong dimension corrupts the space.
"""

from __future__ import annotations

from typing import Final

#: Allowlisted embedding pins → dense dimension. Mirrors the api-worker
#: EMBED_MODELS allowlist plus the Ollama detected-external default.
EMBEDDING_DIMENSIONS: Final[dict[str, int]] = {
    "@cf/baai/bge-m3": 1024,
    "@cf/baai/bge-base-en-v1.5": 768,
    "embeddinggemma:latest": 768,
}


class EmbeddingDimensionMismatch(ValueError):
    """A store/column dimension does not match the pinned model's dimension."""


def dimension_for(model_pin: str) -> int:
    """Dense dimension for an allowlisted embedding pin.

    Raises:
        KeyError: the pin is not allowlisted — loud by design (III.11).
    """
    return EMBEDDING_DIMENSIONS[model_pin]


def assert_store_dimension(model_pin: str, store_dimension: int) -> None:
    """Assert a store/column dimension matches the pinned model's dimension.

    Raises:
        KeyError: the pin is not allowlisted.
        EmbeddingDimensionMismatch: allowlisted, but the store dimension
            disagrees with the pin's dimension.
    """
    expected = dimension_for(model_pin)
    if store_dimension != expected:
        raise EmbeddingDimensionMismatch(
            f"embedding pin {model_pin!r} is {expected}-dimensional but the store "
            f"column is {store_dimension}-dimensional; the campaign's vector(N) column "
            f"is fixed at creation — changing models is a schema migration, not config."
        )
