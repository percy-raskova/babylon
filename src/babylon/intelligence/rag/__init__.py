"""RAG (Retrieval Augmented Generation) system implementation.

This module implements a Retrieval Augmented Generation system with:
- Object lifecycle management
- Embeddings and debeddings
- Document chunking and preprocessing
- Vector storage and retrieval via VectorStoreProtocol
- End-to-end RAG pipeline
- Pre-embeddings system
- Context window management
- Priority queuing
- Working set management with tiered contexts

Main Components:
- RagPipeline: Main orchestrator for ingestion and querying
- DocumentProcessor: Text preprocessing and chunking
- EmbeddingManager: OpenAI-based embedding generation
- Retriever: High-level retrieval interface

Usage:
    Basic usage with the main pipeline:

    ```python
    from babylon.intelligence.rag import RagPipeline, RagConfig
    from babylon.persistence.pgvector_store import PgVectorStore

    # Initialize with a vector store backend
    vector_store = PgVectorStore(pool=pool, collection="rag_documents")
    config = RagConfig(chunk_size=1000, default_top_k=5)
    pipeline = RagPipeline(vector_store=vector_store, config=config)

    # Ingest documents
    result = pipeline.ingest_text("Your document content here", "doc_1")

    # Query for relevant content
    response = pipeline.query("What is this document about?")

    # Get combined context for LLM
    context = response.get_combined_context(max_length=2000)
    ```

    Or use individual components:

    ```python
    from babylon.intelligence.rag import DocumentProcessor, EmbeddingManager

    # Process documents
    processor = DocumentProcessor()
    chunks = processor.process_text("Your content", "source_id")

    # Generate embeddings
    embedding_manager = EmbeddingManager()
    embedded_chunks = await embedding_manager.aembed_batch(chunks)
    ```
"""

from typing import Any

# Document processing (core functionality)
from .chunker import DocumentChunk, DocumentProcessor, Preprocessor, TextChunker

# Exceptions
from .exceptions import (
    CacheError,
    ChunkingError,
    CorruptStateError,
    InvalidObjectError,
    LifecycleError,
    PreEmbeddingError,
    PreprocessingError,
    RagError,
    StateTransitionError,
)

# Lifecycle management
from .lifecycle import LifecycleManager, ObjectState, PerformanceMetrics

# Optional imports that require external dependencies
_optional_imports_available = True
_import_errors: list[str] = []

# Declare module-level names with proper types for mypy
RagPipeline: type[Any]
RagConfig: type[Any]
EmbeddingManager: type[Any] | None
Retriever: type[Any] | None
QueryResponse: type[Any] | None
QueryResult: type[Any] | None
IngestionResult: type[Any] | None

try:
    # Embeddings
    from .embeddings import EmbeddingManager

    # Main RAG pipeline
    from .rag_pipeline import (
        IngestionResult,
        RagConfig,
        RagPipeline,
    )

    # Retrieval
    from .retrieval import QueryResponse, QueryResult, Retriever

except ImportError as e:
    _optional_imports_available = False
    _import_errors.append(str(e))

    # Define placeholder classes to maintain API consistency
    class _RagPipelinePlaceholder:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise ImportError(
                f"RAG pipeline requires additional dependencies. Errors: {_import_errors}"
            )

    class _RagConfigPlaceholder:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise ImportError(
                f"RAG config requires additional dependencies. Errors: {_import_errors}"
            )

    RagPipeline = _RagPipelinePlaceholder
    RagConfig = _RagConfigPlaceholder

    # Define other placeholder values
    EmbeddingManager = None
    Retriever = None
    QueryResponse = None
    QueryResult = None
    IngestionResult = None

__all__ = [
    # Always available - core functionality
    "DocumentProcessor",
    "DocumentChunk",
    "TextChunker",
    "Preprocessor",
    "LifecycleManager",
    "ObjectState",
    "PerformanceMetrics",
    "RagError",
    "LifecycleError",
    "InvalidObjectError",
    "StateTransitionError",
    "CorruptStateError",
    "PreEmbeddingError",
    "PreprocessingError",
    "ChunkingError",
    "CacheError",
    # May require optional dependencies
    "RagPipeline",
    "RagConfig",
    "IngestionResult",
    "EmbeddingManager",
    "Retriever",
    "QueryResponse",
    "QueryResult",
]
