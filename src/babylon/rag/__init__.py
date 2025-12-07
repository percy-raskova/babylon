"""RAG (Retrieval Augmented Generation) system implementation.

This module implements a Retrieval Augmented Generation system with:
- Object lifecycle management
- Embeddings and debeddings
- Document chunking and preprocessing
- Vector storage and retrieval
- End-to-end RAG pipeline
- Pre-embeddings system
- Context window management
- Priority queuing
- Working set management with tiered contexts

Main Components:
- RagPipeline: Main orchestrator for ingestion and querying
- DocumentProcessor: Text preprocessing and chunking
- EmbeddingManager: OpenAI-based embedding generation
- VectorStore: ChromaDB-based vector storage
- Retriever: High-level retrieval interface

Usage:
    Basic usage with the main pipeline:

    ```python
    from babylon.rag import RagPipeline, RagConfig

    # Initialize pipeline with custom config
    config = RagConfig(chunk_size=1000, default_top_k=5)
    pipeline = RagPipeline(config=config)

    # Ingest documents
    result = pipeline.ingest_text("Your document content here", "doc_1")

    # Query for relevant content
    response = pipeline.query("What is this document about?")

    # Get combined context for LLM
    context = response.get_combined_context(max_length=2000)
    ```

    Or use individual components:

    ```python
    from babylon.rag import DocumentProcessor, EmbeddingManager, VectorStore

    # Process documents
    processor = DocumentProcessor()
    chunks = processor.process_text("Your content", "source_id")

    # Generate embeddings
    embedding_manager = EmbeddingManager()
    embedded_chunks = await embedding_manager.aembed_batch(chunks)

    # Store in vector database
    vector_store = VectorStore("my_collection")
    vector_store.add_chunks(embedded_chunks)
    ```
"""

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

# Lifecycle management (existing)
from .lifecycle import LifecycleManager, ObjectState, PerformanceMetrics

# Optional imports that require external dependencies
_optional_imports_available = True
_import_errors = []

try:
    # Main RAG pipeline
    # Embeddings
    from .embeddings import EmbeddingManager
    from .rag_pipeline import (
        IngestionResult,
        RagConfig,
        RagPipeline,
        quick_ingest_text,
        quick_query,
    )

    # Vector storage and retrieval
    from .retrieval import QueryResponse, QueryResult, Retriever, VectorStore

except ImportError as e:
    _optional_imports_available = False
    _import_errors.append(str(e))

    # Define placeholder classes to maintain API consistency
    class RagPipeline:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise ImportError(
                f"RAG pipeline requires additional dependencies. Install with: pip install chromadb numpy. Errors: {_import_errors}"
            )

    class RagConfig:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise ImportError(
                f"RAG config requires additional dependencies. Install with: pip install chromadb numpy. Errors: {_import_errors}"
            )

    # Define other placeholder classes
    EmbeddingManager = VectorStore = Retriever = QueryResponse = QueryResult = None
    IngestionResult = quick_ingest_text = quick_query = None

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
    "quick_ingest_text",
    "quick_query",
    "EmbeddingManager",
    "VectorStore",
    "Retriever",
    "QueryResponse",
    "QueryResult",
]
