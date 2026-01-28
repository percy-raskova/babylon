"""Data layer package for Babylon simulation.

This package manages all data persistence and access, including:

- **Game data**: Static entity definitions (characters, classes, factions)
  loaded from JSON files in the ``game/`` subpackage.
- **External data**: Real-world economic data from BLS, Census, and FRED
  APIs in the ``external/`` subpackage.
- **ChromaDB**: Vector database management for the RAG Archive layer
  via :mod:`babylon.data.chroma_manager`.
- **Schema**: JSON Schema validation and data contracts.
- **Loader infrastructure**: Unified DataLoader base class for consistent
  data ingestion into the 3NF normalized schema.

Subpackages:
    external: Bureau of Labor Statistics, Census, and FRED data integrations.
    game: Static game entity JSON data files.
    models: Pydantic models for data serialization.
    normalize: 3NF normalized database and ETL infrastructure.
    parsers: Data parsing utilities.

Modules:
    chroma_manager: ChromaDB collection and embedding management.
    database: SQLite database utilities for the Ledger layer.
    loader_base: DataLoader ABC and LoadStats for unified data ingestion.
    schema: JSON Schema validation and type contracts.
"""

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats

__all__ = [
    "DataLoader",
    "LoaderConfig",
    "LoadStats",
]
