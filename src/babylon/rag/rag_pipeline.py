"""Main RAG pipeline service that orchestrates document ingestion and query processing."""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from babylon.data.chroma_manager import ChromaManager
from babylon.rag.chunker import DocumentProcessor
from babylon.rag.embeddings import EmbeddingManager
from babylon.rag.exceptions import RagError
from babylon.rag.retrieval import QueryResponse, Retriever, VectorStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of document ingestion process."""

    success: bool
    chunks_processed: int
    chunks_stored: int
    processing_time_ms: float
    embedding_time_ms: float
    storage_time_ms: float
    errors: list[str]
    source_files: list[str]


@dataclass
class RagConfig:
    """Configuration for RAG pipeline."""

    # Document processing config
    chunk_size: int = 1000
    chunk_overlap: int = 100
    min_chunk_length: int = 50
    max_chunk_length: int = 100000

    # Embedding config
    embedding_batch_size: int = 10
    max_concurrent_embeds: int = 4

    # Retrieval config
    default_top_k: int = 10
    default_similarity_threshold: float = 0.0

    # Storage config
    collection_name: str = "rag_documents"
    use_persistent_storage: bool = True


class RagPipeline:
    """Main RAG pipeline that orchestrates ingestion and retrieval."""

    def __init__(
        self,
        config: RagConfig | None = None,
        chroma_manager: ChromaManager | None = None,
        embedding_manager: EmbeddingManager | None = None,
    ):
        """Initialize the RAG pipeline.

        Args:
            config: RAG configuration (uses default if None)
            chroma_manager: ChromaDB manager (creates new if None)
            embedding_manager: Embedding manager (creates new if None)
        """
        self.config = config or RagConfig()
        self.chroma_manager = chroma_manager or ChromaManager()
        self.embedding_manager = embedding_manager or EmbeddingManager(
            batch_size=self.config.embedding_batch_size,
            max_concurrent_requests=self.config.max_concurrent_embeds,
        )

        # Initialize components
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore(
            collection_name=self.config.collection_name,
            chroma_manager=self.chroma_manager,
        )
        self.retriever = Retriever(
            vector_store=self.vector_store,
            embedding_manager=self.embedding_manager,
        )

        logger.info(f"Initialized RAG pipeline with collection '{self.config.collection_name}'")

    async def aingest_text(
        self,
        content: str,
        source_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Asynchronously ingest text content into the RAG system.

        Args:
            content: Text content to ingest
            source_id: Unique identifier for the content source
            metadata: Optional metadata to attach to chunks

        Returns:
            IngestionResult with processing statistics

        Raises:
            RagError: If ingestion fails
        """
        start_time = time.perf_counter()
        errors = []

        try:
            # Process document into chunks
            process_start = time.perf_counter()
            chunks = self.document_processor.process_text(
                content=content,
                source_file=source_id,
                metadata=metadata,
            )
            process_time = (time.perf_counter() - process_start) * 1000

            if not chunks:
                return IngestionResult(
                    success=False,
                    chunks_processed=0,
                    chunks_stored=0,
                    processing_time_ms=process_time,
                    embedding_time_ms=0.0,
                    storage_time_ms=0.0,
                    errors=["No chunks generated from content"],
                    source_files=[source_id],
                )

            # Generate embeddings
            embed_start = time.perf_counter()
            embedded_chunks = await self.embedding_manager.aembed_batch(chunks)
            embed_time = (time.perf_counter() - embed_start) * 1000

            # Store in vector database
            store_start = time.perf_counter()
            self.vector_store.add_chunks(embedded_chunks)
            store_time = (time.perf_counter() - store_start) * 1000

            total_time = (time.perf_counter() - start_time) * 1000

            logger.info(
                f"Ingested '{source_id}': {len(chunks)} chunks in {total_time:.2f}ms "
                f"(processing: {process_time:.2f}ms, embedding: {embed_time:.2f}ms, storage: {store_time:.2f}ms)"
            )

            return IngestionResult(
                success=True,
                chunks_processed=len(chunks),
                chunks_stored=len(embedded_chunks),
                processing_time_ms=total_time,
                embedding_time_ms=embed_time,
                storage_time_ms=store_time,
                errors=errors,
                source_files=[source_id],
            )

        except Exception as e:
            error_msg = f"Ingestion failed for '{source_id}': {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)

            total_time = (time.perf_counter() - start_time) * 1000

            return IngestionResult(
                success=False,
                chunks_processed=0,
                chunks_stored=0,
                processing_time_ms=total_time,
                embedding_time_ms=0.0,
                storage_time_ms=0.0,
                errors=errors,
                source_files=[source_id],
            )

    def ingest_text(
        self,
        content: str,
        source_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """Synchronously ingest text content into the RAG system.

        This is a convenience wrapper around aingest_text for synchronous code.
        For better performance in async contexts, use aingest_text directly.

        Args:
            content: Text content to ingest
            source_id: Unique identifier for the content source
            metadata: Optional metadata to attach to chunks

        Returns:
            IngestionResult with processing statistics
        """
        return asyncio.run(self.aingest_text(content, source_id, metadata))

    async def aingest_file(self, file_path: str, encoding: str = "utf-8") -> IngestionResult:
        """Asynchronously ingest a text file into the RAG system.

        Args:
            file_path: Path to the text file
            encoding: File encoding (default: utf-8)

        Returns:
            IngestionResult with processing statistics

        Raises:
            FileNotFoundError: If file doesn't exist
            RagError: If ingestion fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(path, encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError as e:
            raise RagError(
                message=f"Failed to decode file with encoding {encoding}: {str(e)}",
                error_code="RAG_403",
                details={"file_path": file_path},
            ) from e

        metadata = {
            "source_type": "file",
            "file_path": str(path.absolute()),
            "file_name": path.name,
            "file_size": path.stat().st_size,
        }

        return await self.aingest_text(content, str(path), metadata)

    def ingest_file(self, file_path: str, encoding: str = "utf-8") -> IngestionResult:
        """Synchronously ingest a text file into the RAG system.

        Args:
            file_path: Path to the text file
            encoding: File encoding (default: utf-8)

        Returns:
            IngestionResult with processing statistics
        """
        return asyncio.run(self.aingest_file(file_path, encoding))

    async def aingest_files(
        self,
        file_paths: list[str],
        encoding: str = "utf-8",
        max_concurrent: int = 5,
    ) -> list[IngestionResult]:
        """Asynchronously ingest multiple files concurrently.

        Args:
            file_paths: List of file paths to ingest
            encoding: File encoding (default: utf-8)
            max_concurrent: Maximum number of concurrent ingestions

        Returns:
            List of IngestionResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def ingest_with_semaphore(file_path: str) -> IngestionResult:
            async with semaphore:
                return await self.aingest_file(file_path, encoding)

        tasks = [ingest_with_semaphore(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed IngestionResult objects
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    IngestionResult(
                        success=False,
                        chunks_processed=0,
                        chunks_stored=0,
                        processing_time_ms=0.0,
                        embedding_time_ms=0.0,
                        storage_time_ms=0.0,
                        errors=[str(result)],
                        source_files=[file_paths[i]],
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def ingest_files(
        self,
        file_paths: list[str],
        encoding: str = "utf-8",
        max_concurrent: int = 5,
    ) -> list[IngestionResult]:
        """Synchronously ingest multiple files.

        Args:
            file_paths: List of file paths to ingest
            encoding: File encoding (default: utf-8)
            max_concurrent: Maximum number of concurrent ingestions

        Returns:
            List of IngestionResult objects
        """
        return asyncio.run(self.aingest_files(file_paths, encoding, max_concurrent))

    async def aquery(
        self,
        query: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> QueryResponse:
        """Asynchronously query the RAG system for relevant content.

        Args:
            query: Query text to search for
            top_k: Number of results to return (uses config default if None)
            similarity_threshold: Minimum similarity score (uses config default if None)
            metadata_filter: Optional filters for chunk metadata

        Returns:
            QueryResponse with search results

        Raises:
            RagError: If query processing fails
        """
        k = top_k if top_k is not None else self.config.default_top_k
        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else self.config.default_similarity_threshold
        )

        return await self.retriever.aquery(
            query=query,
            k=k,
            similarity_threshold=threshold,
            metadata_filter=metadata_filter,
        )

    def query(
        self,
        query: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> QueryResponse:
        """Synchronously query the RAG system for relevant content.

        Args:
            query: Query text to search for
            top_k: Number of results to return (uses config default if None)
            similarity_threshold: Minimum similarity score (uses config default if None)
            metadata_filter: Optional filters for chunk metadata

        Returns:
            QueryResponse with search results
        """
        return asyncio.run(self.aquery(query, top_k, similarity_threshold, metadata_filter))

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the RAG system.

        Returns:
            Dictionary with system statistics
        """
        try:
            collection_count = self.vector_store.get_collection_count()
            embedding_cache_size = self.embedding_manager.cache_size

            return {
                "collection_name": self.config.collection_name,
                "total_chunks": collection_count,
                "embedding_cache_size": embedding_cache_size,
                "embedding_cache_max": self.embedding_manager.max_cache_size,
                "config": {
                    "chunk_size": self.config.chunk_size,
                    "chunk_overlap": self.config.chunk_overlap,
                    "default_top_k": self.config.default_top_k,
                    "embedding_batch_size": self.config.embedding_batch_size,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get RAG stats: {str(e)}")
            return {"error": str(e)}

    def clear_collection(self) -> None:
        """Clear all documents from the collection.

        WARNING: This will delete all ingested documents!
        """
        try:
            # Get all chunk IDs and delete them
            results = self.vector_store.collection.get()
            if results and results.get("ids"):
                chunk_ids = results["ids"]
                self.vector_store.delete_chunks(chunk_ids)
                logger.info(
                    f"Cleared {len(chunk_ids)} chunks from collection '{self.config.collection_name}'"
                )
            else:
                logger.info(f"Collection '{self.config.collection_name}' is already empty")
        except Exception as e:
            logger.error(f"Failed to clear collection: {str(e)}")
            raise RagError(
                message=f"Failed to clear collection: {str(e)}",
                error_code="RAG_320",
                details={"collection_name": self.config.collection_name},
            ) from e

    async def aclose(self) -> None:
        """Asynchronously close the RAG pipeline and clean up resources."""
        try:
            await self.embedding_manager.close()
            self.chroma_manager.cleanup()
            logger.info("RAG pipeline closed successfully")
        except Exception as e:
            logger.error(f"Error closing RAG pipeline: {str(e)}")

    def close(self) -> None:
        """Synchronously close the RAG pipeline and clean up resources."""
        asyncio.run(self.aclose())

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()


# Convenience functions for quick RAG operations
async def quick_ingest_text(
    content: str, source_id: str, collection_name: str = "quick_rag"
) -> IngestionResult:
    """Quickly ingest text content using default settings.

    Args:
        content: Text content to ingest
        source_id: Unique identifier for the content
        collection_name: ChromaDB collection name

    Returns:
        IngestionResult with processing statistics
    """
    config = RagConfig(collection_name=collection_name)
    pipeline = RagPipeline(config=config)
    try:
        return await pipeline.aingest_text(content, source_id)
    finally:
        await pipeline.aclose()


async def quick_query(
    query: str, collection_name: str = "quick_rag", top_k: int = 5
) -> QueryResponse:
    """Quickly query the RAG system using default settings.

    Args:
        query: Query text to search for
        collection_name: ChromaDB collection name
        top_k: Number of results to return

    Returns:
        QueryResponse with search results
    """
    config = RagConfig(collection_name=collection_name, default_top_k=top_k)
    pipeline = RagPipeline(config=config)
    try:
        return await pipeline.aquery(query)
    finally:
        await pipeline.aclose()
