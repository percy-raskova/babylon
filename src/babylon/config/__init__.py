"""Configuration package for Babylon/Babylon.

The configuration hierarchy:
1. Environment variables (.env file)
2. Default values (defined in each config class)

All configs are immutable after initialization.
"""

from babylon.config.base import BaseConfig
from babylon.config.chromadb_config import ChromaDBConfig
from babylon.config.defines import GameDefines
from babylon.config.llm_config import LLMConfig, OpenAIConfig
from babylon.config.logging_config import setup_logging
from babylon.config.testing import TestingConfig

__all__ = [
    "BaseConfig",
    "ChromaDBConfig",
    "GameDefines",
    "LLMConfig",
    "OpenAIConfig",  # Backward compatibility alias
    "TestingConfig",
    "setup_logging",
]
