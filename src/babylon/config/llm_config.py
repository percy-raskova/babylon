"""LLM API configuration for text generation and embeddings.

Supports DeepSeek (primary) and OpenAI (fallback) APIs.

Note: In production Babylon, we aim for full offline operation using
local models (Ollama). This config exists for development and testing
with cloud APIs when local GPU resources are unavailable.
"""

import os
from typing import Final


class LLMConfig:
    """Configuration for LLM API integration.

    Supports DeepSeek (primary) and OpenAI (fallback).
    The bourgeois cloud API is a transitional tool until local
    compute infrastructure is established.
    """

    # === API Credentials (DeepSeek priority, OpenAI fallback) ===
    API_KEY: Final[str] = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    API_BASE: Final[str] = os.getenv("LLM_API_BASE", "https://api.deepseek.com")

    # OpenAI-specific (for embeddings and legacy)
    ORGANIZATION_ID: Final[str] = os.getenv("OPENAI_ORGANIZATION_ID", "")

    # === Model Selection ===
    CHAT_MODEL: Final[str] = os.getenv("LLM_CHAT_MODEL", "deepseek-chat")
    EMBEDDING_MODEL: Final[str] = os.getenv("LLM_EMBEDDING_MODEL", "text-embedding-ada-002")

    # === Rate Limiting ===
    MAX_RETRIES: Final[int] = int(os.getenv("LLM_MAX_RETRIES", "3"))
    RETRY_DELAY: Final[float] = float(os.getenv("LLM_RETRY_DELAY", "1.0"))
    RATE_LIMIT_RPM: Final[int] = int(os.getenv("LLM_RATE_LIMIT_RPM", "60"))

    # === Batch Processing ===
    BATCH_SIZE: Final[int] = int(os.getenv("LLM_BATCH_SIZE", "8"))
    REQUEST_TIMEOUT: Final[float] = float(os.getenv("LLM_REQUEST_TIMEOUT", "30.0"))

    @classmethod
    def is_configured(cls) -> bool:
        """Check if LLM API is properly configured."""
        return bool(cls.API_KEY and cls.API_KEY != "your-api-key-here")

    @classmethod
    def get_headers(cls) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": "application/json",
        }
        if cls.ORGANIZATION_ID:
            headers["OpenAI-Organization"] = cls.ORGANIZATION_ID
        return headers

    @classmethod
    def validate(cls) -> None:
        """Validate the LLM configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if not cls.is_configured():
            raise ValueError(
                "LLM API key not configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable."
            )

    @classmethod
    def get_model_dimensions(cls) -> int:
        """Get the embedding dimensions for the configured model.

        Returns:
            Number of dimensions for the embedding model
        """
        # Embedding dimensions by model
        model_dimensions: dict[str, int] = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return model_dimensions.get(cls.EMBEDDING_MODEL, 1536)


# Backward compatibility alias
OpenAIConfig = LLMConfig
