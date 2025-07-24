"""Tests for EntityEmbeddingService integration."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from datetime import datetime

from babylon.core.entity import Entity
from babylon.core.entity_embedding_service import EntityEmbeddingService, EmbeddableEntity


class MockEmbeddingManager:
    """Mock EmbeddingManager for testing."""
    
    def __init__(self):
        self.cache_size = 5
        self.embedding_dimension = 384
        self.batch_size = 8
        self.max_cache_size = 100
    
    def embed(self, obj):
        # Simulate embedding generation
        obj.embedding = [0.1] * 384
        return obj
    
    async def aembed(self, obj):
        return self.embed(obj)
    
    def embed_batch(self, objects):
        return [self.embed(obj) for obj in objects]
    
    async def aembed_batch(self, objects):
        return [await self.aembed(obj) for obj in objects]
    
    def debed_batch(self, objects):
        for obj in objects:
            obj.embedding = None
        return objects


class MockChromaManager:
    """Mock ChromaManager for testing."""
    
    def __init__(self):
        self.collection = Mock()
        
    def get_or_create_collection(self, name):
        return self.collection
        
    def cleanup(self):
        pass


@pytest.fixture
def mock_embedding_manager():
    return MockEmbeddingManager()


@pytest.fixture
def mock_chroma_manager():
    return MockChromaManager()


@pytest.fixture
def entity_embedding_service(mock_embedding_manager, mock_chroma_manager):
    return EntityEmbeddingService(mock_embedding_manager, mock_chroma_manager)


@pytest.fixture
def sample_entities():
    """Create sample entities for testing."""
    entities = []
    for i in range(3):
        entity = Entity(f"Type{i}", f"Role{i}")
        entity.wealth = i * 0.1
        entity.power = i * 0.2
        entities.append(entity)
    return entities


def test_embeddable_entity_adapter():
    """Test EmbeddableEntity adapter functionality."""
    entity = Entity("Class", "Oppressed")
    entity.wealth = 0.5
    
    # Test conversion from Entity
    embeddable = EmbeddableEntity.from_entity(entity)
    assert embeddable.id == entity.id
    assert "Class" in embeddable.content
    assert "Oppressed" in embeddable.content
    assert "Wealth: 0.50" in embeddable.content
    assert embeddable.embedding is None
    
    # Test updating entity with embedding results
    embeddable.embedding = [0.1, 0.2, 0.3]
    
    with patch('numpy.array') as mock_array:
        mock_array.return_value = np.array([0.1, 0.2, 0.3])
        embeddable.update_entity(entity)
        mock_array.assert_called_once_with([0.1, 0.2, 0.3])


def test_entity_embedding_service_init():
    """Test EntityEmbeddingService initialization."""
    # Test with default managers
    service = EntityEmbeddingService()
    assert service.embedding_manager is not None
    assert service.chroma_manager is not None
    
    # Test with custom managers
    custom_em = MockEmbeddingManager()
    custom_cm = MockChromaManager()
    service = EntityEmbeddingService(custom_em, custom_cm)
    assert service.embedding_manager is custom_em
    assert service.chroma_manager is custom_cm


def test_embed_single_entity(entity_embedding_service, sample_entities):
    """Test embedding a single entity."""
    entity = sample_entities[0]
    
    # Mock numpy import for embedding update
    with patch('babylon.core.entity_embedding_service.np') as mock_np:
        mock_np.array.return_value = np.array([0.1] * 384)
        
        result = entity_embedding_service.embed_entity(entity)
        
        assert result is entity
        mock_np.array.assert_called_once()


@pytest.mark.asyncio
async def test_async_embed_single_entity(entity_embedding_service, sample_entities):
    """Test async embedding of a single entity."""
    entity = sample_entities[0]
    
    with patch('babylon.core.entity_embedding_service.np') as mock_np:
        mock_np.array.return_value = np.array([0.1] * 384)
        
        result = await entity_embedding_service.aembed_entity(entity)
        
        assert result is entity
        mock_np.array.assert_called_once()


def test_embed_entities_batch(entity_embedding_service, sample_entities):
    """Test batch embedding of multiple entities."""
    with patch('babylon.core.entity_embedding_service.np') as mock_np:
        mock_np.array.return_value = np.array([0.1] * 384)
        
        results = entity_embedding_service.embed_entities_batch(sample_entities)
        
        assert len(results) == len(sample_entities)
        assert all(result in sample_entities for result in results)
        assert mock_np.array.call_count == len(sample_entities)


@pytest.mark.asyncio
async def test_async_embed_entities_batch(entity_embedding_service, sample_entities):
    """Test async batch embedding of multiple entities."""
    with patch('babylon.core.entity_embedding_service.np') as mock_np:
        mock_np.array.return_value = np.array([0.1] * 384)
        
        results = await entity_embedding_service.aembed_entities_batch(sample_entities)
        
        assert len(results) == len(sample_entities)
        assert all(result in sample_entities for result in results)


def test_store_entities_success(entity_embedding_service, sample_entities):
    """Test successful storage of entities in ChromaDB."""
    # Give entities embeddings
    for entity in sample_entities:
        entity.embedding = np.array([0.1] * 384)
    
    entity_embedding_service.store_entities(sample_entities)
    
    # Verify ChromaDB collection.add was called
    collection = entity_embedding_service.entity_collection
    collection.add.assert_called_once()
    
    # Verify call parameters
    call_kwargs = collection.add.call_args[1]
    assert len(call_kwargs['documents']) == len(sample_entities)
    assert len(call_kwargs['embeddings']) == len(sample_entities)
    assert len(call_kwargs['metadatas']) == len(sample_entities)
    assert len(call_kwargs['ids']) == len(sample_entities)


def test_store_entities_without_embeddings(entity_embedding_service, sample_entities):
    """Test error when storing entities without embeddings."""
    # Don't generate embeddings
    with pytest.raises(ValueError, match="must have embeddings"):
        entity_embedding_service.store_entities(sample_entities)


def test_search_similar_entities(entity_embedding_service, sample_entities):
    """Test searching for similar entities."""
    query_entity = sample_entities[0]
    query_entity.embedding = np.array([0.1] * 384)
    
    # Mock ChromaDB response
    mock_results = {
        'ids': [['entity1', 'entity2']],
        'documents': [['Doc 1', 'Doc 2']],
        'metadatas': [[{'type': 'Class'}, {'type': 'Org'}]],
        'distances': [[0.1, 0.3]]
    }
    entity_embedding_service.entity_collection.query.return_value = mock_results
    
    results = entity_embedding_service.search_similar_entities(query_entity, n_results=2)
    
    # Verify query was called
    collection = entity_embedding_service.entity_collection
    collection.query.assert_called_once_with(
        query_embeddings=[query_entity.embedding.tolist()],
        n_results=2,
        include=["documents", "metadatas", "distances"]
    )
    
    # Verify results format
    assert len(results) == 2
    assert results[0]['id'] == 'entity1'
    assert results[0]['distance'] == 0.1


def test_search_similar_entities_no_embedding(entity_embedding_service, sample_entities):
    """Test error when searching with entity without embedding."""
    query_entity = sample_entities[0]  # No embedding
    
    with pytest.raises(ValueError, match="must have embedding"):
        entity_embedding_service.search_similar_entities(query_entity)


def test_search_by_criteria(entity_embedding_service):
    """Test searching entities by metadata criteria."""
    criteria = {"type": "Class", "role": "Oppressed"}
    
    mock_results = {
        'ids': ['entity1', 'entity2'],
        'documents': ['Doc 1', 'Doc 2'],
        'metadatas': [{'type': 'Class'}, {'type': 'Class'}]
    }
    entity_embedding_service.entity_collection.get.return_value = mock_results
    
    results = entity_embedding_service.search_by_criteria(criteria, n_results=5)
    
    # Verify query was called
    collection = entity_embedding_service.entity_collection
    collection.get.assert_called_once_with(
        where=criteria,
        limit=5,
        include=["documents", "metadatas"]
    )
    
    assert len(results) == 2
    assert results[0]['id'] == 'entity1'


def test_remove_embeddings(entity_embedding_service, sample_entities):
    """Test removing embeddings from entities."""
    # Give entities embeddings first
    for entity in sample_entities:
        entity.embedding = np.array([0.1] * 384)
    
    results = entity_embedding_service.remove_embeddings(sample_entities)
    
    # Verify embeddings were removed
    assert all(entity.embedding is None for entity in results)
    assert all(result in sample_entities for result in results)


def test_get_cache_stats(entity_embedding_service):
    """Test getting cache statistics."""
    stats = entity_embedding_service.get_cache_stats()
    
    assert 'cache_size' in stats
    assert 'cache_dimension' in stats
    assert 'batch_size' in stats
    assert 'max_cache_size' in stats
    assert stats['cache_size'] == 5
    assert stats['cache_dimension'] == 384


def test_cleanup(entity_embedding_service):
    """Test service cleanup."""
    # Should not raise any exceptions
    entity_embedding_service.cleanup()


def test_integration_workflow(entity_embedding_service, sample_entities):
    """Test complete integration workflow."""
    with patch('babylon.core.entity_embedding_service.np') as mock_np:
        mock_np.array.return_value = np.array([0.1] * 384)
        
        # Step 1: Embed entities
        embedded = entity_embedding_service.embed_entities_batch(sample_entities)
        assert len(embedded) == len(sample_entities)
        
        # Step 2: Store in ChromaDB  
        entity_embedding_service.store_entities(embedded)
        entity_embedding_service.entity_collection.add.assert_called_once()
        
        # Step 3: Search for similar entities
        query_entity = embedded[0]
        
        mock_search_results = {
            'ids': [['similar1']],
            'documents': [['Similar doc']],
            'metadatas': [[{'type': 'Class'}]],
            'distances': [[0.2]]
        }
        entity_embedding_service.entity_collection.query.return_value = mock_search_results
        
        similar = entity_embedding_service.search_similar_entities(query_entity, n_results=1)
        assert len(similar) == 1
        assert similar[0]['id'] == 'similar1'
        
        # Step 4: Remove embeddings
        debedded = entity_embedding_service.remove_embeddings(embedded)
        assert all(entity.embedding is None for entity in debedded)


def test_error_handling(entity_embedding_service, sample_entities):
    """Test error handling in various scenarios."""
    # Test embedding failure
    entity_embedding_service.embedding_manager.embed = Mock(side_effect=Exception("Embed failed"))
    
    with pytest.raises(Exception, match="Embed failed"):
        entity_embedding_service.embed_entity(sample_entities[0])
    
    # Test storage failure
    entity_embedding_service.entity_collection.add = Mock(side_effect=Exception("Storage failed"))
    
    # Give entity an embedding
    sample_entities[0].embedding = np.array([0.1] * 384)
    
    with pytest.raises(Exception, match="Storage failed"):
        entity_embedding_service.store_entities([sample_entities[0]])


def test_without_numpy_graceful_handling():
    """Test graceful handling when numpy is not available."""
    entity = Entity("Class", "Oppressed")
    embeddable = EmbeddableEntity.from_entity(entity)
    embeddable.embedding = [0.1, 0.2, 0.3]
    
    # Mock numpy import failure
    with patch('babylon.core.entity_embedding_service.np', None):
        with patch('babylon.core.entity_embedding_service.logger') as mock_logger:
            embeddable.update_entity(entity)
            # Should log warning but not crash
            mock_logger.warning.assert_called_once()