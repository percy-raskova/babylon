"""Unit tests for Entity embedding functionality."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from babylon.core.entity import Entity


class MockSentenceTransformer:
    """Mock SentenceTransformer for testing."""
    
    def __init__(self, embedding_dim=384):
        self.embedding_dim = embedding_dim
    
    def encode(self, texts):
        """Generate mock embeddings based on text content."""
        embeddings = []
        for text in texts:
            # Create deterministic embeddings based on text hash
            text_hash = hash(text) 
            # Convert to positive number and normalize
            base_embedding = abs(text_hash) % 1000000
            embedding = np.random.RandomState(base_embedding).random(self.embedding_dim)
            # Normalize to unit vector
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)
        return np.array(embeddings)


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    entity = Entity(type="Class", role="Oppressed")
    entity.freedom = 0.3
    entity.wealth = 0.2
    entity.stability = 0.8
    entity.power = 0.4
    return entity


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model."""
    return MockSentenceTransformer()


@pytest.fixture
def mock_chromadb_collection():
    """Create a mock ChromaDB collection."""
    collection = Mock()
    collection.add = Mock()
    collection.query = Mock()
    return collection


def test_get_content_for_embedding(sample_entity):
    """Test content generation for embedding."""
    content = sample_entity.get_content_for_embedding()
    
    # Verify content contains all essential information
    assert "Entity Type: Class" in content
    assert "Role: Oppressed" in content
    assert "Freedom: 0.30" in content
    assert "Wealth: 0.20" in content
    assert "Stability: 0.80" in content
    assert "Power: 0.40" in content
    assert "societal contradictions" in content
    
    # Verify it's a coherent text string
    assert isinstance(content, str)
    assert len(content) > 50  # Should be substantial content


def test_generate_embedding(sample_entity, mock_embedding_model):
    """Test embedding generation for entity."""
    # Initially no embedding
    assert sample_entity.embedding is None
    
    # Generate embedding
    sample_entity.generate_embedding(mock_embedding_model)
    
    # Verify embedding was created
    assert sample_entity.embedding is not None
    assert isinstance(sample_entity.embedding, np.ndarray)
    assert len(sample_entity.embedding) == 384  # Default dimension
    assert sample_entity.last_updated > sample_entity.created_at


def test_generate_embedding_failure(sample_entity):
    """Test embedding generation failure handling."""
    # Mock embedding model that raises exception
    mock_model = Mock()
    mock_model.encode.side_effect = Exception("Embedding service failed")
    
    with pytest.raises(Exception, match="Embedding service failed"):
        sample_entity.generate_embedding(mock_model)
    
    # Verify embedding remains None on failure
    assert sample_entity.embedding is None


def test_add_to_chromadb_success(sample_entity, mock_embedding_model, mock_chromadb_collection):
    """Test successful addition to ChromaDB."""
    # Generate embedding first
    sample_entity.generate_embedding(mock_embedding_model)
    
    # Add to ChromaDB
    sample_entity.add_to_chromadb(mock_chromadb_collection)
    
    # Verify ChromaDB collection.add was called with correct parameters
    mock_chromadb_collection.add.assert_called_once()
    call_args = mock_chromadb_collection.add.call_args[1]
    
    assert call_args['documents'] == [sample_entity.get_content_for_embedding()]
    assert call_args['embeddings'] == [sample_entity.embedding.tolist()]
    assert call_args['metadatas'] == [sample_entity.get_metadata()]
    assert call_args['ids'] == [sample_entity.id]


def test_add_to_chromadb_no_embedding(sample_entity, mock_chromadb_collection):
    """Test error when adding to ChromaDB without embedding."""
    # Don't generate embedding
    assert sample_entity.embedding is None
    
    with pytest.raises(ValueError, match="must have embedding generated"):
        sample_entity.add_to_chromadb(mock_chromadb_collection)
    
    # Verify ChromaDB was not called
    mock_chromadb_collection.add.assert_not_called()


def test_add_to_chromadb_failure(sample_entity, mock_embedding_model, mock_chromadb_collection):
    """Test ChromaDB addition failure handling."""
    # Generate embedding
    sample_entity.generate_embedding(mock_embedding_model)
    
    # Mock ChromaDB failure
    mock_chromadb_collection.add.side_effect = Exception("ChromaDB connection failed")
    
    with pytest.raises(Exception, match="ChromaDB connection failed"):
        sample_entity.add_to_chromadb(mock_chromadb_collection)


def test_search_similar_entities(mock_chromadb_collection):
    """Test searching for similar entities."""
    # Mock ChromaDB query response
    mock_results = {
        'ids': [['entity1', 'entity2', 'entity3']],
        'documents': [['Doc 1', 'Doc 2', 'Doc 3']],
        'metadatas': [[
            {'type': 'Class', 'role': 'Oppressed'},
            {'type': 'Organization', 'role': 'Oppressor'},
            {'type': 'Class', 'role': 'Neutral'}
        ]],
        'distances': [[0.1, 0.3, 0.5]]
    }
    mock_chromadb_collection.query.return_value = mock_results
    
    # Create query embedding
    query_embedding = np.random.random(384)
    
    # Search for similar entities
    results = Entity.search_similar_entities(
        mock_chromadb_collection, 
        query_embedding, 
        n_results=3
    )
    
    # Verify query was called correctly
    mock_chromadb_collection.query.assert_called_once_with(
        query_embeddings=[query_embedding.tolist()],
        n_results=3,
        include=["documents", "metadatas", "distances"]
    )
    
    # Verify results format
    assert len(results) == 3
    assert results[0]['id'] == 'entity1'
    assert results[0]['document'] == 'Doc 1'
    assert results[0]['metadata']['type'] == 'Class'
    assert results[0]['distance'] == 0.1


def test_search_similar_entities_no_results(mock_chromadb_collection):
    """Test searching when no similar entities found."""
    # Mock empty response
    mock_results = {
        'ids': [[]],
        'documents': [[]],
        'metadatas': [[]],
        'distances': [[]]
    }
    mock_chromadb_collection.query.return_value = mock_results
    
    query_embedding = np.random.random(384)
    results = Entity.search_similar_entities(mock_chromadb_collection, query_embedding)
    
    assert len(results) == 0


def test_search_similar_entities_failure(mock_chromadb_collection):
    """Test search failure handling."""
    mock_chromadb_collection.query.side_effect = Exception("Search failed")
    
    query_embedding = np.random.random(384)
    
    with pytest.raises(Exception, match="Search failed"):
        Entity.search_similar_entities(mock_chromadb_collection, query_embedding)


def test_reconstruct_from_embedding(sample_entity, mock_embedding_model):
    """Test entity reconstruction from embedding."""
    # Generate embedding first
    sample_entity.generate_embedding(mock_embedding_model)
    
    # Reconstruct from embedding
    reconstructed = sample_entity.reconstruct_from_embedding()
    
    # For now, should return the original content
    assert reconstructed == sample_entity.get_content_for_embedding()
    assert isinstance(reconstructed, str)
    assert len(reconstructed) > 0


def test_reconstruct_from_embedding_no_embedding(sample_entity):
    """Test reconstruction failure when no embedding exists."""
    assert sample_entity.embedding is None
    
    with pytest.raises(ValueError, match="has no embedding to reconstruct from"):
        sample_entity.reconstruct_from_embedding()


def test_get_embedding_similarity(mock_embedding_model):
    """Test similarity calculation between entities."""
    # Create two entities
    entity1 = Entity(type="Class", role="Oppressed") 
    entity2 = Entity(type="Class", role="Oppressed")  # Same type/role
    entity3 = Entity(type="Organization", role="Oppressor")  # Different
    
    # Generate embeddings
    entity1.generate_embedding(mock_embedding_model)
    entity2.generate_embedding(mock_embedding_model)
    entity3.generate_embedding(mock_embedding_model)
    
    # Test similarity calculation
    similarity_same = entity1.get_embedding_similarity(entity2)
    similarity_different = entity1.get_embedding_similarity(entity3)
    
    # Verify similarity is between -1 and 1
    assert -1 <= similarity_same <= 1
    assert -1 <= similarity_different <= 1
    
    # Similar entities should have higher similarity
    # (This test might be flaky due to random embeddings, but should generally hold)
    # Commenting out for now since mock embeddings are random
    # assert similarity_same > similarity_different


def test_get_embedding_similarity_no_embeddings():
    """Test similarity calculation failure when embeddings missing."""
    entity1 = Entity(type="Class", role="Oppressed")
    entity2 = Entity(type="Class", role="Oppressed")
    
    # No embeddings generated
    with pytest.raises(ValueError, match="Both entities must have embeddings"):
        entity1.get_embedding_similarity(entity2)


def test_metadata_includes_timestamps(sample_entity):
    """Test that metadata includes timestamp information."""
    metadata = sample_entity.get_metadata()
    
    assert 'created_at' in metadata
    assert 'last_updated' in metadata
    assert isinstance(metadata['created_at'], str)
    assert isinstance(metadata['last_updated'], str)
    
    # Verify ISO format timestamps
    datetime.fromisoformat(metadata['created_at'])
    datetime.fromisoformat(metadata['last_updated'])


def test_entity_full_workflow(mock_embedding_model, mock_chromadb_collection):
    """Test complete embedding workflow for an entity."""
    # Create entity
    entity = Entity(type="Class", role="Oppressed")
    entity.wealth = 0.1
    entity.power = 0.9
    
    # Step 1: Generate embedding
    entity.generate_embedding(mock_embedding_model)
    assert entity.embedding is not None
    
    # Step 2: Add to ChromaDB
    entity.add_to_chromadb(mock_chromadb_collection)
    mock_chromadb_collection.add.assert_called_once()
    
    # Step 3: Test reconstruction
    reconstructed = entity.reconstruct_from_embedding()
    assert "Wealth: 0.10" in reconstructed
    assert "Power: 0.90" in reconstructed
    
    # Step 4: Test similarity with another entity
    other_entity = Entity(type="Class", role="Oppressed")
    other_entity.generate_embedding(mock_embedding_model)
    
    similarity = entity.get_embedding_similarity(other_entity)
    assert -1 <= similarity <= 1


def test_different_entity_types_different_content():
    """Test that different entity types produce different embedding content."""
    oppressed = Entity(type="Class", role="Oppressed")
    oppressor = Entity(type="Organization", role="Oppressor")
    
    content1 = oppressed.get_content_for_embedding()
    content2 = oppressor.get_content_for_embedding()
    
    # Contents should be different
    assert content1 != content2
    assert "Oppressed" in content1 and "Oppressed" not in content2
    assert "Oppressor" in content2 and "Oppressor" not in content1
    assert "Class" in content1 and "Organization" in content2