"""Query and retrieval interface for the RAG system."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import time

import chromadb
import numpy as np
from babylon.rag.exceptions import RagError
from babylon.rag.embeddings import EmbeddingManager
from babylon.rag.chunker import DocumentChunk
from babylon.data.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Represents a single query result with similarity score."""
    
    chunk: DocumentChunk
    similarity_score: float
    distance: float
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Convert similarity score to distance if not provided."""
        if self.distance == 0.0 and self.similarity_score > 0.0:
            # Convert cosine similarity to distance
            self.distance = 1.0 - self.similarity_score


@dataclass 
class QueryResponse:
    """Represents the complete response to a query."""
    
    query: str
    results: List[QueryResult] = field(default_factory=list)
    total_results: int = 0
    processing_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    search_time_ms: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    
    def get_top_k(self, k: int) -> List[QueryResult]:
        """Get the top k results by similarity score."""
        return sorted(self.results, key=lambda x: x.similarity_score, reverse=True)[:k]
    
    def get_combined_context(self, max_length: int = 4000, separator: str = "\n\n") -> str:
        """Combine result chunks into a single context string."""
        context_parts = []
        current_length = 0
        
        for result in sorted(self.results, key=lambda x: x.similarity_score, reverse=True):
            chunk_text = result.chunk.content
            if current_length + len(chunk_text) + len(separator) <= max_length:
                context_parts.append(chunk_text)
                current_length += len(chunk_text) + len(separator)
            else:
                # Try to fit partial content
                remaining = max_length - current_length - len(separator)
                if remaining > 100:  # Only add if meaningful amount left
                    context_parts.append(chunk_text[:remaining] + "...")
                break
        
        return separator.join(context_parts)


class VectorStore:
    """Interface to ChromaDB for storing and retrieving document vectors."""
    
    def __init__(
        self,
        collection_name: str = "documents",
        chroma_manager: Optional[ChromaManager] = None,
    ):
        """Initialize the vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            chroma_manager: Optional ChromaManager instance (creates new if None)
        """
        self.collection_name = collection_name
        self.chroma_manager = chroma_manager or ChromaManager()
        self._collection = None
        
    @property
    def collection(self) -> Any:
        """Get or create the ChromaDB collection."""
        if self._collection is None:
            self._collection = self.chroma_manager.get_or_create_collection(self.collection_name)
        return self._collection
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Add document chunks to the vector store.
        
        Args:
            chunks: List of DocumentChunk objects with embeddings
            
        Raises:
            RagError: If chunks are missing embeddings or storage fails
        """
        if not chunks:
            return
        
        # Validate that all chunks have embeddings
        chunks_without_embeddings = [c for c in chunks if not c.embedding]
        if chunks_without_embeddings:
            raise RagError(
                message=f"{len(chunks_without_embeddings)} chunks are missing embeddings",
                error_code="RAG_301",
                details={"chunk_ids": [c.id for c in chunks_without_embeddings[:5]]},
            )
        
        try:
            # Prepare data for ChromaDB
            ids = [chunk.id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            embeddings = [chunk.embedding for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                metadata = chunk.metadata.copy() if chunk.metadata else {}
                metadata.update({
                    'source_file': chunk.source_file,
                    'chunk_index': chunk.chunk_index,
                    'start_char': chunk.start_char,
                    'end_char': chunk.end_char,
                    'content_length': len(chunk.content),
                })
                metadatas.append(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            
            logger.info(f"Added {len(chunks)} chunks to vector store collection '{self.collection_name}'")
            
        except Exception as e:
            raise RagError(
                message=f"Failed to add chunks to vector store: {str(e)}",
                error_code="RAG_302",
                details={"collection_name": self.collection_name},
            ) from e
    
    def query_similar(
        self, 
        query_embedding: List[float], 
        k: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Tuple[List[str], List[str], List[List[float]], List[Dict[str, Any]], List[float]]:
        """Query for similar chunks using embedding.
        
        Args:
            query_embedding: Query vector embedding
            k: Number of results to return
            where: Optional metadata filters
            include: Fields to include in results
            
        Returns:
            Tuple of (ids, documents, embeddings, metadatas, distances)
            
        Raises:
            RagError: If query fails
        """
        try:
            include = include or ['documents', 'metadatas', 'distances']
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
                include=include,
            )
            
            # Unpack results (ChromaDB returns lists of lists)
            ids = results['ids'][0] if 'ids' in results else []
            documents = results['documents'][0] if 'documents' in results else []
            embeddings = results.get('embeddings', [[]])[0]
            metadatas = results['metadatas'][0] if 'metadatas' in results else []
            distances = results['distances'][0] if 'distances' in results else []
            
            return ids, documents, embeddings, metadatas, distances
            
        except Exception as e:
            raise RagError(
                message=f"Failed to query vector store: {str(e)}",
                error_code="RAG_303",
                details={"collection_name": self.collection_name},
            ) from e
    
    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Delete chunks from the vector store.
        
        Args:
            chunk_ids: List of chunk IDs to delete
            
        Raises:
            RagError: If deletion fails
        """
        if not chunk_ids:
            return
        
        try:
            self.collection.delete(ids=chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks from vector store")
            
        except Exception as e:
            raise RagError(
                message=f"Failed to delete chunks from vector store: {str(e)}",
                error_code="RAG_304",
                details={"chunk_ids": chunk_ids[:5]},
            ) from e
    
    def get_collection_count(self) -> int:
        """Get the number of chunks in the collection."""
        try:
            return self.collection.count()
        except Exception as e:
            raise RagError(
                message=f"Failed to get collection count: {str(e)}",
                error_code="RAG_305",
                details={"collection_name": self.collection_name},
            ) from e


class Retriever:
    """High-level retrieval interface for RAG queries."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_manager: EmbeddingManager,
    ):
        """Initialize the retriever.
        
        Args:
            vector_store: VectorStore instance for similarity search
            embedding_manager: EmbeddingManager for query embedding
        """
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
    
    async def aquery(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> QueryResponse:
        """Asynchronously query for relevant document chunks.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            similarity_threshold: Minimum similarity score for results
            metadata_filter: Optional filters for chunk metadata
            
        Returns:
            QueryResponse with results and timing information
            
        Raises:
            RagError: If query processing fails
        """
        start_time = time.perf_counter()
        
        try:
            # Create a temporary object for embedding the query
            @dataclass
            class QueryObject:
                id: str = "query"
                content: str = query
                embedding: Optional[List[float]] = None
            
            query_obj = QueryObject(content=query)
            
            # Generate embedding for the query
            embed_start = time.perf_counter()
            embedded_query = await self.embedding_manager.aembed(query_obj)
            embed_time = (time.perf_counter() - embed_start) * 1000
            
            # Search for similar chunks
            search_start = time.perf_counter()
            ids, documents, embeddings, metadatas, distances = self.vector_store.query_similar(
                query_embedding=embedded_query.embedding,
                k=k,
                where=metadata_filter,
            )
            search_time = (time.perf_counter() - search_start) * 1000
            
            # Convert results to QueryResult objects
            results = []
            for i, (chunk_id, doc, embedding, metadata, distance) in enumerate(
                zip(ids, documents, embeddings, metadatas, distances)
            ):
                similarity_score = max(0.0, 1.0 - distance)  # Convert distance to similarity
                
                if similarity_score >= similarity_threshold:
                    chunk = DocumentChunk(
                        id=chunk_id,
                        content=doc,
                        source_file=metadata.get('source_file') if metadata else None,
                        chunk_index=metadata.get('chunk_index', 0) if metadata else 0,
                        start_char=metadata.get('start_char', 0) if metadata else 0,
                        end_char=metadata.get('end_char', 0) if metadata else 0,
                        metadata=metadata,
                        embedding=embedding,
                    )
                    
                    result = QueryResult(
                        chunk=chunk,
                        similarity_score=similarity_score,
                        distance=distance,
                        metadata=metadata,
                    )
                    results.append(result)
            
            total_time = (time.perf_counter() - start_time) * 1000
            
            response = QueryResponse(
                query=query,
                results=results,
                total_results=len(results),
                processing_time_ms=total_time,
                embedding_time_ms=embed_time,
                search_time_ms=search_time,
                metadata={
                    'requested_k': k,
                    'similarity_threshold': similarity_threshold,
                    'metadata_filter': metadata_filter,
                },
            )
            
            logger.info(
                f"Query processed in {total_time:.2f}ms: {len(results)} results for '{query[:50]}...'"
            )
            
            return response
            
        except Exception as e:
            raise RagError(
                message=f"Query processing failed: {str(e)}",
                error_code="RAG_310",
                details={"query": query[:100]},
            ) from e
    
    def query(
        self,
        query: str,
        k: int = 10,
        similarity_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> QueryResponse:
        """Synchronously query for relevant document chunks.
        
        This is a convenience wrapper around aquery for synchronous code.
        For better performance in async contexts, use aquery directly.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            similarity_threshold: Minimum similarity score for results
            metadata_filter: Optional filters for chunk metadata
            
        Returns:
            QueryResponse with results and timing information
            
        Raises:
            RagError: If query processing fails
        """
        import asyncio
        return asyncio.run(self.aquery(query, k, similarity_threshold, metadata_filter))