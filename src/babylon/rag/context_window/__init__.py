"""Context window management for the RAG system."""

from babylon.rag.context_window.config import ContextWindowConfig
from babylon.rag.context_window.manager import ContextWindowManager
from babylon.rag.context_window.token_counter import count_tokens
from babylon.rag.exceptions import RagError

# Backward compatibility aliases - all context window errors are now RagError
ContextWindowError = RagError
TokenCountError = RagError
CapacityExceededError = RagError
OptimizationFailedError = RagError
ContentPriorityError = RagError
ContentRemovalError = RagError
ContentInsertionError = RagError

__all__ = [
    "ContextWindowManager",
    "ContextWindowConfig",
    "ContextWindowError",
    "TokenCountError",
    "CapacityExceededError",
    "OptimizationFailedError",
    "ContentPriorityError",
    "ContentRemovalError",
    "ContentInsertionError",
    "count_tokens",
]
