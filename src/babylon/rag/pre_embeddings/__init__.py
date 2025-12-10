"""Pre-embedding pipeline for RAG document processing.

This package handles the preprocessing stages before documents are
embedded into the ChromaDB vector store:

Modules:
    cache_manager: Manages embedding cache to avoid recomputation.
    chunking: Splits documents into semantically coherent chunks
        optimized for retrieval and context window limits.
    manager: Orchestrates the pre-embedding pipeline workflow.
    preprocessor: Text cleaning, normalization, and preparation
        for the embedding model.

The pipeline flow is:
    1. Preprocessor cleans raw text
    2. Chunker splits into retrieval-optimized segments
    3. Cache manager checks for existing embeddings
    4. Manager coordinates the full workflow
"""
