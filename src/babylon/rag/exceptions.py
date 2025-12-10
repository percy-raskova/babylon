"""Custom exceptions for the RAG system.

Defines RAG-specific exceptions that integrate with the main Babylon error hierarchy.
All RAG errors inherit from ObserverError, making them non-fatal to the simulation.

Error Code Ranges:
- RAG_001 to RAG_099: General RAG system errors
- RAG_100 to RAG_199: Lifecycle management errors
- RAG_200 to RAG_299: Embedding errors
- RAG_300 to RAG_399: Query/retrieval errors
- RAG_400 to RAG_499: Pre-embeddings errors
- RAG_500 to RAG_599: Context window errors
"""

from babylon.utils.exceptions import ObserverError


class RagError(ObserverError):
    """Unified exception class for all RAG system errors.

    Use error_code to distinguish between different error types:
    - RAG_001-099: General errors
    - RAG_1XX: Lifecycle errors (invalid objects, state transitions)
    - RAG_2XX: Embedding errors (API failures, batch errors)
    - RAG_3XX: Query/retrieval errors
    - RAG_4XX: Pre-embedding errors (chunking, preprocessing)
    - RAG_5XX: Context window errors (capacity, optimization)
    """

    def __init__(
        self,
        message: str,
        error_code: str = "RAG_001",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# All legacy exception names map to RagError for backwards compatibility.
# New code should use RagError directly with appropriate error_code.
# =============================================================================

# Lifecycle errors (RAG_1XX)
LifecycleError = RagError
InvalidObjectError = RagError
StateTransitionError = RagError
CorruptStateError = RagError

# Pre-embedding errors (RAG_4XX)
PreEmbeddingError = RagError
PreprocessingError = RagError
ChunkingError = RagError
CacheError = RagError
