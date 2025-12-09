"""ChromaDB configuration for the Archive layer.

The Archive stores the semantic history and ideological context.
It is the collective unconscious of the simulation.
"""

import os
from pathlib import Path
from typing import Final

from chromadb.config import Settings


class ChromaDBConfig:
    """Configuration for ChromaDB vector database.

    The Archive persists embeddings locally using DuckDB+Parquet.
    No external servers required - fully embedded, fully materialist.
    """

    # === Storage Configuration ===
    BASE_DIR: Final[Path] = Path(os.getenv("CHROMADB_PERSIST_DIR", "./chromadb"))

    # === Collection Names ===
    THEORY_COLLECTION: Final[str] = "marxist_theory"
    HISTORY_COLLECTION: Final[str] = "game_history"
    ENTITIES_COLLECTION: Final[str] = "entity_embeddings"

    # === Performance Tuning ===
    BATCH_SIZE: Final[int] = int(os.getenv("CHROMADB_BATCH_SIZE", "100"))
    SEARCH_LIMIT: Final[int] = int(os.getenv("CHROMADB_SEARCH_LIMIT", "10"))
    DISTANCE_THRESHOLD: Final[float] = float(os.getenv("CHROMADB_DISTANCE_THRESHOLD", "0.4"))

    @classmethod
    def get_settings(cls) -> Settings:
        """Get ChromaDB Settings object for client initialization.

        Uses the new ChromaDB 1.x API. Note: persist_directory is no longer
        passed here - it's passed directly to PersistentClient(path=...).
        """
        return Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        )

    @classmethod
    def get_persist_directory(cls) -> str:
        """Get the persistence directory as a string."""
        return str(cls.BASE_DIR)
