"""Top-level exception re-exports for Babylon.

This module provides a convenient import path for common exceptions.

Hierarchy:
    BabylonError (base)
    ├── InfrastructureError - retryable I/O, network, database errors
    │   ├── DatabaseError
    │   └── StorageError - files, checkpoints, persistence
    ├── ValidationError - bad input, schema violations
    │   └── ConfigurationError
    ├── SimulationError - fatal engine/math failures
    │   └── TopologyError
    └── ObserverError - non-fatal AI/RAG layer errors
        ├── LLMError (alias: LLMGenerationError)
        └── RagError (in babylon.rag.exceptions)
"""

from babylon.utils.exceptions import (
    BabylonError,
    ConfigurationError,
    DatabaseError,
    InfrastructureError,
    LLMError,
    LLMGenerationError,
    ObserverError,
    SimulationError,
    StorageError,
    TopologyError,
    ValidationError,
)

__all__ = [
    "BabylonError",
    # Infrastructure layer
    "InfrastructureError",
    "DatabaseError",
    "StorageError",
    # Validation layer
    "ValidationError",
    "ConfigurationError",
    # Simulation layer
    "SimulationError",
    "TopologyError",
    # Observer layer
    "ObserverError",
    "LLMError",
    "LLMGenerationError",  # backwards compatibility alias
]
