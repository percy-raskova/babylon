"""Embedding-lane configuration for the RAG pipeline.

ADR101: this module is the EMBEDDING lane only. The chat/generation lane
(the former DeepSeek/Workers-AI ``API_KEY``/``CHAT_MODEL``/``PROVIDER``
surface) was retired with the hand-rolled client stack — generation
configuration lives in ``babylon.intelligence.providers``
(``IntelligenceSettings``: env ``BABYLON_INTEL_*`` + ``config.toml``,
§A3 precedence). Git history is the archive for the old surface.

Embeddings default to local Ollama; OpenAI cloud embeddings remain a
configurable alternative for the RAG pipeline.
"""

import os
from typing import Final

# NOTE: this is the canonical sentence-transformers REFERENCE model (Spec 061
# FR-001 dimension-parity pin), NOT the runtime default embedder. The runtime
# default is Ollama `embeddinggemma:latest` (see EMBEDDING_MODEL below,
# LLM_EMBEDDING_PROVIDER=ollama) — it independently produces 768-dim vectors,
# which is why it matches CANONICAL_EMBEDDING_DIM without being this model.
CANONICAL_EMBEDDING_MODEL_ID: Final[str] = "sentence-transformers/all-mpnet-base-v2"
CANONICAL_EMBEDDING_DIM: Final[int] = 768
# Spec 061 T120: pinned to a specific HuggingFace commit SHA per
# Constitution III.6. Captured 2026-05-12 via HfApi().model_info().sha.
# (Pins the reference model above, not the Ollama runtime default.)
CANONICAL_EMBEDDING_REVISION: Final[str] = "e8c3b32edf5434bc2275fc9bab85f82640a19130"


class LLMConfig:
    """Embedding-lane configuration (Ollama local by default, OpenAI cloud).

    Chat/generation settings do NOT live here (ADR101) — see
    ``babylon.intelligence.providers.load_settings``.
    """

    # === Embedding Configuration (Ollama local by default) ===
    EMBEDDING_PROVIDER: Final[str] = os.getenv("LLM_EMBEDDING_PROVIDER", "ollama")
    EMBEDDING_API_BASE: Final[str] = os.getenv("LLM_EMBEDDING_API_BASE", "http://localhost:11434")
    EMBEDDING_MODEL: Final[str] = os.getenv("LLM_EMBEDDING_MODEL", "embeddinggemma:latest")

    # OpenAI-specific (cloud embeddings only)
    ORGANIZATION_ID: Final[str] = os.getenv("OPENAI_ORGANIZATION_ID", "")

    # === Rate Limiting / Batch Processing (embedding HTTP path) ===
    MAX_RETRIES: Final[int] = int(os.getenv("LLM_MAX_RETRIES", "3"))
    RATE_LIMIT_RPM: Final[int] = int(os.getenv("LLM_RATE_LIMIT_RPM", "60"))
    BATCH_SIZE: Final[int] = int(os.getenv("LLM_BATCH_SIZE", "8"))
    REQUEST_TIMEOUT: Final[float] = float(os.getenv("LLM_REQUEST_TIMEOUT", "30.0"))

    @classmethod
    def is_ollama_embeddings(cls) -> bool:
        """Check if using Ollama for embeddings (local, no API key needed)."""
        return cls.EMBEDDING_PROVIDER.lower() == "ollama"

    @classmethod
    def get_embedding_headers(cls) -> dict[str, str]:
        """Get HTTP headers for Embedding API requests.

        Ollama doesn't need auth headers; OpenAI does.
        """
        headers = {"Content-Type": "application/json"}
        if not cls.is_ollama_embeddings():
            # OpenAI embeddings need API key
            openai_key = os.getenv("OPENAI_API_KEY", "")
            if openai_key:
                headers["Authorization"] = f"Bearer {openai_key}"
            if cls.ORGANIZATION_ID:
                headers["OpenAI-Organization"] = cls.ORGANIZATION_ID
        return headers

    @classmethod
    def get_embedding_url(cls) -> str:
        """Get the embedding API URL based on provider."""
        if cls.is_ollama_embeddings():
            return f"{cls.EMBEDDING_API_BASE}/api/embeddings"
        return f"{cls.EMBEDDING_API_BASE}/v1/embeddings"

    @classmethod
    def validate_embeddings(cls) -> None:
        """Validate embedding configuration.

        For Ollama: Just check the base URL is set.
        For OpenAI: Check API key is available.

        Raises:
            ValueError: If required configuration is missing
        """
        if cls.is_ollama_embeddings():
            if not cls.EMBEDDING_API_BASE:
                raise ValueError("Ollama embedding API base URL not configured.")
        else:
            openai_key = os.getenv("OPENAI_API_KEY", "")
            if not openai_key:
                raise ValueError(
                    "OpenAI API key required for cloud embeddings. "
                    "Set OPENAI_API_KEY or switch to Ollama (LLM_EMBEDDING_PROVIDER=ollama)."
                )

    @classmethod
    def get_model_dimensions(cls) -> int:
        """Get the embedding dimensions for the configured model.

        Returns:
            Number of dimensions for the embedding model
        """
        model_dimensions: dict[str, int] = {
            # OpenAI models
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            # Ollama models
            "embeddinggemma:latest": 768,
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            "all-minilm": 384,
        }
        return model_dimensions.get(cls.EMBEDDING_MODEL, 768)
