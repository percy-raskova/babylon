# Babylon RAG System

This directory contains the Retrieval-Augmented Generation (RAG) system for the Babylon game engine. The RAG system enables efficient document storage, similarity search, and context retrieval for dynamic content queries.

## Overview

The RAG system integrates ChromaDB as a vector database with OpenAI embeddings to provide:

- **Document Ingestion**: Process and chunk text documents for storage
- **Vector Storage**: Store document embeddings in ChromaDB for efficient retrieval
- **Semantic Search**: Query documents using natural language for relevant content
- **Context Generation**: Assemble retrieved content for LLM prompts
- **Metadata Filtering**: Filter results by document metadata
- **Scalable Architecture**: Support both development and production configurations

## Key Components

### 1. RagPipeline

The main orchestrator that provides high-level APIs for ingestion and querying.

```python
from babylon.rag import RagPipeline, RagConfig

# Initialize with custom configuration
config = RagConfig(chunk_size=1000, default_top_k=5)
pipeline = RagPipeline(config=config)

# Ingest documents
result = await pipeline.aingest_text("Your document content", "doc_id")

# Query for relevant content
response = await pipeline.aquery("What is this document about?")
context = response.get_combined_context(max_length=2000)
```

### 2. Document Processing

Handles text preprocessing and intelligent chunking.

```python
from babylon.rag import DocumentProcessor

processor = DocumentProcessor()
chunks = processor.process_text("Your content", "source_id")
chunks = processor.process_file("path/to/document.txt")
```

### 3. Embedding Management

Generates embeddings using OpenAI API with caching and rate limiting.

```python
from babylon.rag import EmbeddingManager

embedding_manager = EmbeddingManager()
embedded_chunks = await embedding_manager.aembed_batch(chunks)
```

### 4. Vector Storage & Retrieval

ChromaDB-based storage with similarity search capabilities.

```python
from babylon.rag import VectorStore, Retriever

vector_store = VectorStore("my_collection")
retriever = Retriever(vector_store, embedding_manager)
response = await retriever.aquery("search query")
```

## Configuration

The `RagConfig` class provides comprehensive configuration options:

```python
config = RagConfig(
    # Document processing
    chunk_size=1000,
    chunk_overlap=100,
    min_chunk_length=50,

    # Embedding settings
    embedding_batch_size=10,
    max_concurrent_embeds=4,

    # Retrieval settings
    default_top_k=10,
    default_similarity_threshold=0.0,

    # Storage settings
    collection_name="my_documents",
    use_persistent_storage=True
)
```

## Setup Requirements

### Dependencies

The RAG system requires:

- `chromadb>=1.0.0` - Vector database
- OpenAI API access for embeddings (configured via existing `OpenAIConfig`)
- All existing Babylon dependencies

### Environment Variables

Ensure the following environment variables are set:

- `OPENAI_API_KEY` - Your OpenAI API key for embeddings
- `CHROMADB_DIR` - Directory for ChromaDB persistence (optional, defaults to `data/chromadb`)

### ChromaDB Storage

The system supports both persistent and in-memory storage:

- **Persistent** (default): Data stored in `data/chromadb/persist/`
- **In-memory**: For development/testing (data lost on restart)

## Usage Examples

### Basic Usage

```python
import asyncio
from babylon.rag import RagPipeline

async def main():
    pipeline = RagPipeline()

    # Ingest a document
    await pipeline.aingest_text(
        "Historical materialism is the Marxist method...",
        "marxist_theory"
    )

    # Query for relevant content
    response = await pipeline.aquery("What is historical materialism?")

    # Get context for LLM
    context = response.get_combined_context(max_length=2000)
    print(f"Relevant context: {context}")

    await pipeline.aclose()

asyncio.run(main())
```

### File Processing

```python
# Process single file
result = await pipeline.aingest_file("documents/theory.txt")

# Process multiple files concurrently
results = await pipeline.aingest_files([
    "documents/theory.txt",
    "documents/practice.txt",
    "documents/analysis.txt"
], max_concurrent=3)
```

### Advanced Querying

```python
# Query with metadata filtering
response = await pipeline.aquery(
    "game mechanics",
    top_k=5,
    similarity_threshold=0.7,
    metadata_filter={"document_type": "game_design"}
)

# Access detailed results
for result in response.results:
    print(f"Score: {result.similarity_score:.3f}")
    print(f"Source: {result.chunk.source_file}")
    print(f"Content: {result.chunk.content[:200]}...")
```

### Context Manager Usage

```python
async with RagPipeline() as pipeline:
    # Automatic cleanup when exiting context
    await pipeline.aingest_text("content", "id")
    response = await pipeline.aquery("query")
```

## Performance Considerations

### Chunking Strategy

- **Chunk Size**: Balance between context preservation and retrieval precision
- **Overlap**: Prevents information loss at chunk boundaries
- **Preserve Boundaries**: Respects sentence and paragraph structure

### Embedding Efficiency

- **Batch Processing**: Process multiple chunks simultaneously
- **Caching**: LRU cache prevents re-computing embeddings
- **Rate Limiting**: Respects OpenAI API limits
- **Concurrent Requests**: Parallel embedding generation

### Storage Optimization

- **Metadata Indexing**: Enable efficient filtering
- **Collection Organization**: Separate collections by domain
- **Persistence**: Data survives application restarts

## Integration with Babylon

The RAG system integrates seamlessly with existing Babylon components:

- **Configuration**: Uses existing `OpenAIConfig` for API settings
- **Logging**: Integrated with Babylon's logging framework
- **Exceptions**: Follows Babylon's error hierarchy
- **Metrics**: Compatible with existing metrics collection
- **Lifecycle**: Works with object lifecycle management

## Development and Testing

### Running Tests

```bash
# Run RAG-specific tests
python -m pytest tests/unit/test_rag_pipeline.py -v

# Run integration tests (requires ChromaDB)
python -m pytest tests/integration/chromadb/ -v
```

### Example Script

```bash
# Run the demo script
python examples/rag_example.py
```

### Development Mode

For development, use in-memory storage:

```python
config = RagConfig(use_persistent_storage=False)
pipeline = RagPipeline(config=config)
```

## Production Deployment

### Scaling Considerations

1. **Database**: Consider ChromaDB clustering for large deployments
1. **Embeddings**: Monitor OpenAI API usage and costs
1. **Memory**: Tune cache sizes based on available RAM
1. **Concurrency**: Adjust batch sizes and concurrent limits

### Monitoring

Key metrics to monitor:

- Embedding generation times
- Query response times
- Cache hit ratios
- Storage growth
- API usage and costs

### Backup Strategy

```python
# The ChromaDB configuration includes backup settings
from babylon.config.chromadb_config import ChromaDBConfig

# Backups stored in data/chromadb/backups/
# Maximum 5 backups retained by default
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure ChromaDB is installed
1. **API Errors**: Check OpenAI API key configuration
1. **Storage Issues**: Verify ChromaDB directory permissions
1. **Memory Issues**: Reduce batch sizes and cache limits

### Debug Logging

```python
import logging
logging.getLogger('babylon.rag').setLevel(logging.DEBUG)
```

## Future Enhancements

Planned improvements include:

- Support for additional embedding providers (Cohere, HuggingFace)
- Advanced chunking strategies (semantic segmentation)
- Hybrid search (vector + keyword)
- Real-time document updates
- Multi-modal support (images, structured data)
