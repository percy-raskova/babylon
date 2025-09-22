"""Tests for RAG pipeline functionality."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from babylon.rag import (
    RagPipeline,
    RagConfig,
    DocumentProcessor,
    DocumentChunk,
    VectorStore,
    Retriever,
    EmbeddingManager,
)
from babylon.rag.exceptions import RagError, ChunkingError, PreprocessingError


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    This is a sample document for testing the RAG system.
    It contains multiple paragraphs with different topics.
    
    The first paragraph discusses the basics of retrieval.
    The second paragraph explains augmented generation.
    
    Finally, this paragraph covers integration aspects of the system.
    The system should be able to chunk this text appropriately.
    """


@pytest.fixture
def mock_embedding_manager():
    """Mock embedding manager for testing."""
    manager = Mock(spec=EmbeddingManager)
    manager.aembed = AsyncMock()
    manager.aembed_batch = AsyncMock()
    manager.close = AsyncMock()
    manager.cache_size = 10
    manager.max_cache_size = 100
    
    # Mock embedding generation
    async def mock_aembed(obj):
        obj.embedding = [0.1, 0.2, 0.3] * 512  # Mock 1536-dim embedding
        return obj
    
    async def mock_aembed_batch(objects):
        for obj in objects:
            obj.embedding = [0.1, 0.2, 0.3] * 512
        return objects
    
    manager.aembed.side_effect = mock_aembed
    manager.aembed_batch.side_effect = mock_aembed_batch
    
    return manager


@pytest.fixture
def mock_chroma_manager():
    """Mock ChromaDB manager for testing."""
    manager = Mock()
    collection = Mock()
    collection.add = Mock()
    collection.query = Mock()
    collection.count = Mock(return_value=0)
    collection.delete = Mock()
    collection.get = Mock(return_value={'ids': []})
    
    manager.get_or_create_collection.return_value = collection
    manager.cleanup = Mock()
    
    return manager


class TestDocumentProcessor:
    """Tests for document processing components."""
    
    def test_process_text_basic(self, sample_text):
        """Test basic text processing."""
        processor = DocumentProcessor()
        chunks = processor.process_text(sample_text, "test_doc")
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.content.strip() for chunk in chunks)  # No empty chunks
        assert all(chunk.source_file == "test_doc" for chunk in chunks)
    
    def test_process_empty_text(self):
        """Test processing empty text."""
        processor = DocumentProcessor()
        
        with pytest.raises(PreprocessingError) as exc_info:
            processor.process_text("", "empty_doc")
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_process_file(self, sample_text, tmp_path):
        """Test file processing."""
        # Create a temporary file
        test_file = tmp_path / "test_document.txt"
        test_file.write_text(sample_text)
        
        processor = DocumentProcessor()
        chunks = processor.process_file(str(test_file))
        
        assert len(chunks) > 0
        assert all(chunk.source_file == str(test_file) for chunk in chunks)
        assert all("file_path" in chunk.metadata for chunk in chunks)
        assert all("file_name" in chunk.metadata for chunk in chunks)
    
    def test_chunk_overlap(self):
        """Test that chunk overlap works correctly."""
        content = "A" * 2000  # Long content that will be chunked
        
        processor = DocumentProcessor()
        chunks = processor.process_text(content, "overlap_test")
        
        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            assert chunks[1].start_char < chunks[0].end_char


class TestVectorStore:
    """Tests for vector storage functionality."""
    
    def test_add_chunks(self, mock_chroma_manager):
        """Test adding chunks to vector store."""
        store = VectorStore("test_collection", mock_chroma_manager)
        
        chunks = [
            DocumentChunk(
                id="chunk_1",
                content="Test content 1",
                embedding=[0.1, 0.2, 0.3],
                metadata={"key": "value1"}
            ),
            DocumentChunk(
                id="chunk_2", 
                content="Test content 2",
                embedding=[0.4, 0.5, 0.6],
                metadata={"key": "value2"}
            )
        ]
        
        store.add_chunks(chunks)
        
        # Verify the collection was called correctly
        store.collection.add.assert_called_once()
        call_args = store.collection.add.call_args
        
        assert call_args[1]['ids'] == ['chunk_1', 'chunk_2']
        assert call_args[1]['documents'] == ['Test content 1', 'Test content 2']
        assert len(call_args[1]['embeddings']) == 2
        assert len(call_args[1]['metadatas']) == 2
    
    def test_add_chunks_without_embeddings(self, mock_chroma_manager):
        """Test error when adding chunks without embeddings."""
        store = VectorStore("test_collection", mock_chroma_manager)
        
        chunks = [
            DocumentChunk(
                id="chunk_1",
                content="Test content",
                embedding=None  # Missing embedding
            )
        ]
        
        with pytest.raises(RagError) as exc_info:
            store.add_chunks(chunks)
        
        assert "missing embeddings" in str(exc_info.value).lower()
    
    def test_query_similar(self, mock_chroma_manager):
        """Test similarity query."""
        # Mock query response
        mock_chroma_manager.get_or_create_collection().query.return_value = {
            'ids': [['chunk_1', 'chunk_2']],
            'documents': [['Doc 1', 'Doc 2']],
            'distances': [[0.1, 0.2]],
            'metadatas': [[{'key': 'val1'}, {'key': 'val2'}]]
        }
        
        store = VectorStore("test_collection", mock_chroma_manager)
        query_embedding = [0.1, 0.2, 0.3]
        
        ids, docs, embeddings, metadatas, distances = store.query_similar(query_embedding, k=2)
        
        assert ids == ['chunk_1', 'chunk_2']
        assert docs == ['Doc 1', 'Doc 2']
        assert distances == [0.1, 0.2]
        assert len(metadatas) == 2


class TestRagPipeline:
    """Tests for the main RAG pipeline."""
    
    @pytest.mark.asyncio
    async def test_ingest_text(self, sample_text, mock_embedding_manager, mock_chroma_manager):
        """Test text ingestion."""
        config = RagConfig(chunk_size=500)
        pipeline = RagPipeline(
            config=config,
            chroma_manager=mock_chroma_manager,
            embedding_manager=mock_embedding_manager
        )
        
        result = await pipeline.aingest_text(sample_text, "test_doc")
        
        assert result.success
        assert result.chunks_processed > 0
        assert result.chunks_stored == result.chunks_processed
        assert result.processing_time_ms > 0
        assert result.source_files == ["test_doc"]
        
        # Verify embeddings were generated
        mock_embedding_manager.aembed_batch.assert_called_once()
        
        # Verify chunks were stored
        mock_chroma_manager.get_or_create_collection().add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query(self, mock_embedding_manager, mock_chroma_manager):
        """Test querying the pipeline."""
        # Mock query response
        mock_chroma_manager.get_or_create_collection().query.return_value = {
            'ids': [['chunk_1']],
            'documents': [['Relevant content']],
            'distances': [[0.1]],
            'metadatas': [[{'source_file': 'test_doc'}]]
        }
        
        pipeline = RagPipeline(
            chroma_manager=mock_chroma_manager,
            embedding_manager=mock_embedding_manager
        )
        
        response = await pipeline.aquery("test query")
        
        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.results[0].chunk.content == "Relevant content"
        assert response.processing_time_ms > 0
        
        # Verify embedding was generated for query
        mock_embedding_manager.aembed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ingest_file(self, sample_text, mock_embedding_manager, mock_chroma_manager, tmp_path):
        """Test file ingestion."""
        # Create temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text(sample_text)
        
        pipeline = RagPipeline(
            chroma_manager=mock_chroma_manager,
            embedding_manager=mock_embedding_manager
        )
        
        result = await pipeline.aingest_file(str(test_file))
        
        assert result.success
        assert result.chunks_processed > 0
        assert str(test_file) in result.source_files
    
    @pytest.mark.asyncio 
    async def test_ingest_multiple_files(self, sample_text, mock_embedding_manager, mock_chroma_manager, tmp_path):
        """Test ingesting multiple files."""
        # Create temporary files
        files = []
        for i in range(3):
            test_file = tmp_path / f"test_{i}.txt"
            test_file.write_text(f"{sample_text} File {i}")
            files.append(str(test_file))
        
        pipeline = RagPipeline(
            chroma_manager=mock_chroma_manager,
            embedding_manager=mock_embedding_manager
        )
        
        results = await pipeline.aingest_files(files)
        
        assert len(results) == 3
        assert all(result.success for result in results)
        assert sum(result.chunks_processed for result in results) > 0
    
    def test_get_stats(self, mock_embedding_manager, mock_chroma_manager):
        """Test getting pipeline statistics."""
        mock_chroma_manager.get_or_create_collection().count.return_value = 42
        
        pipeline = RagPipeline(
            chroma_manager=mock_chroma_manager,
            embedding_manager=mock_embedding_manager
        )
        
        stats = pipeline.get_stats()
        
        assert stats['total_chunks'] == 42
        assert 'config' in stats
        assert 'embedding_cache_size' in stats
    
    def test_clear_collection(self, mock_embedding_manager, mock_chroma_manager):
        """Test clearing the collection."""
        mock_chroma_manager.get_or_create_collection().get.return_value = {
            'ids': ['chunk_1', 'chunk_2', 'chunk_3']
        }
        
        pipeline = RagPipeline(
            chroma_manager=mock_chroma_manager,
            embedding_manager=mock_embedding_manager
        )
        
        pipeline.clear_collection()
        
        # Verify delete was called
        pipeline.vector_store.collection.delete.assert_called_once()
    
    def test_context_manager(self, mock_embedding_manager, mock_chroma_manager):
        """Test using pipeline as context manager."""
        with RagPipeline(
            chroma_manager=mock_chroma_manager,
            embedding_manager=mock_embedding_manager
        ) as pipeline:
            assert pipeline is not None
        
        # Verify cleanup was called
        mock_embedding_manager.close.assert_called_once()
        mock_chroma_manager.cleanup.assert_called_once()


class TestIntegration:
    """Integration tests for the complete RAG system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, sample_text):
        """Test complete ingestion -> query workflow with mocked dependencies."""
        
        # Mock embedding responses
        def mock_embed(obj):
            # Generate fake but consistent embeddings based on content
            import hashlib
            hash_val = int(hashlib.md5(obj.content.encode()).hexdigest()[:8], 16)
            obj.embedding = [(hash_val % 100) / 100.0] * 1536  # Consistent fake embedding
            return obj
        
        async def mock_aembed(obj):
            return mock_embed(obj)
        
        async def mock_aembed_batch(objects):
            return [mock_embed(obj) for obj in objects]
        
        with patch('babylon.rag.rag_pipeline.EmbeddingManager') as MockEmbedding, \
             patch('babylon.rag.rag_pipeline.ChromaManager') as MockChroma:
            
            # Setup mocks
            mock_embedding_manager = Mock()
            mock_embedding_manager.aembed = mock_aembed
            mock_embedding_manager.aembed_batch = mock_aembed_batch
            mock_embedding_manager.close = AsyncMock()
            mock_embedding_manager.cache_size = 0
            mock_embedding_manager.max_cache_size = 100
            
            MockEmbedding.return_value = mock_embedding_manager
            
            # Mock ChromaDB with in-memory storage
            stored_chunks = {}
            
            def mock_add(ids, documents, embeddings, metadatas):
                for i, chunk_id in enumerate(ids):
                    stored_chunks[chunk_id] = {
                        'document': documents[i],
                        'embedding': embeddings[i],
                        'metadata': metadatas[i]
                    }
            
            def mock_query(query_embeddings, n_results=10, **kwargs):
                # Simple similarity based on first embedding value
                query_emb = query_embeddings[0]
                similarities = []
                
                for chunk_id, chunk_data in stored_chunks.items():
                    # Fake similarity calculation
                    sim = 1.0 - abs(query_emb[0] - chunk_data['embedding'][0])
                    similarities.append((sim, chunk_id, chunk_data))
                
                # Sort by similarity and take top n_results
                similarities.sort(reverse=True, key=lambda x: x[0])
                top_results = similarities[:n_results]
                
                return {
                    'ids': [[r[1] for r in top_results]],
                    'documents': [[r[2]['document'] for r in top_results]],
                    'distances': [[1.0 - r[0] for r in top_results]],
                    'metadatas': [[r[2]['metadata'] for r in top_results]]
                }
            
            mock_collection = Mock()
            mock_collection.add.side_effect = mock_add
            mock_collection.query.side_effect = mock_query
            mock_collection.count.return_value = lambda: len(stored_chunks)
            
            mock_chroma_manager = Mock()
            mock_chroma_manager.get_or_create_collection.return_value = mock_collection
            mock_chroma_manager.cleanup = Mock()
            
            MockChroma.return_value = mock_chroma_manager
            
            # Run the test
            config = RagConfig(chunk_size=300, default_top_k=3)
            pipeline = RagPipeline(config=config)
            
            # 1. Ingest the document
            ingest_result = await pipeline.aingest_text(sample_text, "test_document")
            
            assert ingest_result.success
            assert ingest_result.chunks_processed > 0
            
            # 2. Query for relevant content
            query_response = await pipeline.aquery("What does this document discuss?")
            
            assert query_response.total_results >= 0
            assert len(query_response.results) <= 3  # Configured top_k
            
            # 3. Test context generation
            if query_response.results:
                context = query_response.get_combined_context(max_length=1000)
                assert isinstance(context, str)
                assert len(context) <= 1000
            
            # Cleanup
            await pipeline.aclose()


if __name__ == "__main__":
    pytest.main([__file__])