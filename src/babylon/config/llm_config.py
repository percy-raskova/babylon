"""LLM API configuration for text generation and embeddings.

Supports hybrid setup:
- Chat: DeepSeek API (cloud) or OpenAI (fallback)
- Embeddings: Ollama (local, default) or OpenAI (cloud)

In production Babylon, we aim for full offline operation using
local models (Ollama). Cloud APIs are transitional tools.
"""

import os
from typing import Final


class LLMConfig:
    """Configuration for LLM API integration.

    Supports hybrid setup:
    - Chat: DeepSeek (primary) / OpenAI (fallback)
    - Embeddings: Ollama (local, default) / OpenAI (cloud)

    The bourgeois cloud API is a transitional tool until local
    compute infrastructure is fully established.
    """

    # === Chat API Credentials (DeepSeek priority, OpenAI fallback) ===
    API_KEY: Final[str] = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    API_BASE: Final[str] = os.getenv("LLM_API_BASE", "https://api.deepseek.com")

    # OpenAI-specific (for legacy compatibility)
    ORGANIZATION_ID: Final[str] = os.getenv("OPENAI_ORGANIZATION_ID", "")

    # === Chat Model Selection ===
    CHAT_MODEL: Final[str] = os.getenv("LLM_CHAT_MODEL", "deepseek-chat")

    # === Embedding Configuration (Ollama local by default) ===
    EMBEDDING_PROVIDER: Final[str] = os.getenv("LLM_EMBEDDING_PROVIDER", "ollama")
    EMBEDDING_API_BASE: Final[str] = os.getenv("LLM_EMBEDDING_API_BASE", "http://localhost:11434")
    EMBEDDING_MODEL: Final[str] = os.getenv("LLM_EMBEDDING_MODEL", "embeddinggemma:latest")

    # === Rate Limiting ===
    MAX_RETRIES: Final[int] = int(os.getenv("LLM_MAX_RETRIES", "3"))
    RETRY_DELAY: Final[float] = float(os.getenv("LLM_RETRY_DELAY", "1.0"))
    RATE_LIMIT_RPM: Final[int] = int(os.getenv("LLM_RATE_LIMIT_RPM", "60"))

    # === Batch Processing ===
    BATCH_SIZE: Final[int] = int(os.getenv("LLM_BATCH_SIZE", "8"))
    REQUEST_TIMEOUT: Final[float] = float(os.getenv("LLM_REQUEST_TIMEOUT", "30.0"))

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Chat LLM API is properly configured."""
        return bool(cls.API_KEY and cls.API_KEY != "your-api-key-here")

    @classmethod
    def is_ollama_embeddings(cls) -> bool:
        """Check if using Ollama for embeddings (local, no API key needed)."""
        return cls.EMBEDDING_PROVIDER.lower() == "ollama"

    @classmethod
    def get_headers(cls) -> dict[str, str]:
        """Get HTTP headers for Chat API requests."""
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": "application/json",
        }
        if cls.ORGANIZATION_ID:
            headers["OpenAI-Organization"] = cls.ORGANIZATION_ID
        return headers

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
    def validate(cls) -> None:
        """Validate the Chat LLM configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not cls.is_configured():
            raise ValueError(
                "LLM API key not configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable."
            )

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


# Backward compatibility alias
OpenAIConfig = LLMConfig
