"""Entity-specific embedding integration with the RAG system.

This module provides integration between the game's Entity system and the 
sophisticated RAG (Retrieval Augmented Generation) embedding infrastructure.
It bridges the gap between game entities and the vector database system.
"""

from typing import List, Optional, Dict, Any
import logging
from dataclasses import dataclass

from babylon.core.entity import Entity
from babylon.rag.embeddings import EmbeddingManager, Embeddable
from babylon.data.chroma_manager import ChromaManager

logger = logging.getLogger(__name__)


@dataclass
class EmbeddableEntity:
    """Adapter to make Entity compatible with EmbeddingManager protocol."""
    
    id: str
    content: str
    embedding: Optional[List[float]] = None
    
    @classmethod
    def from_entity(cls, entity: Entity) -> 'EmbeddableEntity':
        """Create EmbeddableEntity from a game Entity.
        
        Args:
            entity: The Entity to wrap
            
        Returns:
            EmbeddableEntity instance compatible with EmbeddingManager
        """
        return cls(
            id=entity.id,
            content=entity.get_content_for_embedding(),
            embedding=entity.embedding.tolist() if entity.embedding is not None else None
        )
    
    def update_entity(self, entity: Entity) -> None:
        """Update the original Entity with embedding results.
        
        Args:
            entity: The Entity to update
        """
        if self.embedding is not None:
            try:
                import numpy as np
                entity.embedding = np.array(self.embedding)
            except ImportError:
                logger.warning("NumPy not available, cannot update entity embedding")


class EntityEmbeddingService:
    """High-level service for managing entity embeddings.
    
    This service provides a bridge between the game's Entity system and the
    sophisticated RAG embedding infrastructure. It leverages the existing
    EmbeddingManager for advanced features like:
    - OpenAI API integration with proper error handling and retries
    - Intelligent caching and batch processing
    - Performance metrics collection
    - Rate limiting and concurrent operations
    """
    
    def __init__(self, embedding_manager: Optional[EmbeddingManager] = None,
                 chroma_manager: Optional[ChromaManager] = None):
        """Initialize the entity embedding service.
        
        Args:
            embedding_manager: EmbeddingManager instance (creates new if None)
            chroma_manager: ChromaManager instance (creates new if None)
        """
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.chroma_manager = chroma_manager or ChromaManager()
        self._entity_collection = None
        
    @property
    def entity_collection(self):
        """Get or create the ChromaDB collection for entities."""
        if self._entity_collection is None:
            self._entity_collection = self.chroma_manager.get_or_create_collection("entities")
        return self._entity_collection
    
    def embed_entity(self, entity: Entity) -> Entity:
        """Embed a single entity using the advanced EmbeddingManager.
        
        Args:
            entity: Entity to embed
            
        Returns:
            Entity with embedding generated
            
        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Convert Entity to EmbeddingManager-compatible format
            embeddable = EmbeddableEntity.from_entity(entity)
            
            # Use the sophisticated EmbeddingManager
            embedded = self.embedding_manager.embed(embeddable)
            
            # Update the original Entity
            embedded.update_entity(entity)
            
            logger.debug(
                f"Successfully embedded entity {entity.id} using EmbeddingManager",
                extra={"entity_id": entity.id, "entity_type": entity.type}
            )
            
            return entity
            
        except Exception as e:
            logger.error(
                f"Failed to embed entity {entity.id}: {str(e)}",
                extra={"entity_id": entity.id, "entity_type": entity.type}
            )
            raise
    
    async def aembed_entity(self, entity: Entity) -> Entity:
        """Asynchronously embed a single entity.
        
        Args:
            entity: Entity to embed
            
        Returns:
            Entity with embedding generated
        """
        try:
            embeddable = EmbeddableEntity.from_entity(entity)
            embedded = await self.embedding_manager.aembed(embeddable)
            embedded.update_entity(entity)
            return entity
        except Exception as e:
            logger.error(f"Failed to async embed entity {entity.id}: {str(e)}")
            raise
    
    def embed_entities_batch(self, entities: List[Entity]) -> List[Entity]:
        """Embed multiple entities efficiently using batch processing.
        
        Args:
            entities: List of entities to embed
            
        Returns:
            List of entities with embeddings generated
        """
        try:
            # Convert all entities to embeddable format
            embeddables = [EmbeddableEntity.from_entity(entity) for entity in entities]
            
            # Use batch processing from EmbeddingManager
            embedded_results = self.embedding_manager.embed_batch(embeddables)
            
            # Update original entities
            for embedded, original in zip(embedded_results, entities):
                embedded.update_entity(original)
            
            logger.info(
                f"Successfully embedded {len(entities)} entities in batch",
                extra={"batch_size": len(entities)}
            )
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to embed entity batch: {str(e)}")
            raise
    
    async def aembed_entities_batch(self, entities: List[Entity]) -> List[Entity]:
        """Asynchronously embed multiple entities efficiently.
        
        Args:
            entities: List of entities to embed
            
        Returns:
            List of entities with embeddings generated
        """
        try:
            embeddables = [EmbeddableEntity.from_entity(entity) for entity in entities]
            embedded_results = await self.embedding_manager.aembed_batch(embeddables)
            
            for embedded, original in zip(embedded_results, entities):
                embedded.update_entity(original)
            
            return entities
        except Exception as e:
            logger.error(f"Failed to async embed entity batch: {str(e)}")
            raise
    
    def store_entities(self, entities: List[Entity]) -> None:
        """Store embedded entities in ChromaDB.
        
        Args:
            entities: List of entities with embeddings to store
            
        Raises:
            ValueError: If any entity lacks an embedding
            Exception: If storage fails
        """
        try:
            # Validate all entities have embeddings
            entities_without_embeddings = [e.id for e in entities if e.embedding is None]
            if entities_without_embeddings:
                raise ValueError(
                    f"Entities {entities_without_embeddings} must have embeddings before storage"
                )
            
            # Prepare data for ChromaDB
            documents = [entity.get_content_for_embedding() for entity in entities]
            embeddings = [entity.embedding.tolist() for entity in entities]
            metadatas = [entity.get_metadata() for entity in entities]
            ids = [entity.id for entity in entities]
            
            # Store in ChromaDB
            self.entity_collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(
                f"Successfully stored {len(entities)} entities in ChromaDB",
                extra={"entity_count": len(entities)}
            )
            
        except Exception as e:
            logger.error(f"Failed to store entities: {str(e)}")
            raise
    
    def search_similar_entities(self, query_entity: Entity, 
                               n_results: int = 5, 
                               include_distances: bool = True) -> List[Dict[str, Any]]:
        """Search for entities similar to a given entity.
        
        This is a "debedding" operation that uses vector similarity to find
        related entities in the game world.
        
        Args:
            query_entity: Entity to find similar entities for
            n_results: Number of similar entities to return
            include_distances: Whether to include similarity distances
            
        Returns:
            List of similar entities with metadata
            
        Raises:
            ValueError: If query entity lacks embedding
            Exception: If search fails
        """
        if query_entity.embedding is None:
            raise ValueError(f"Query entity {query_entity.id} must have embedding for similarity search")
        
        try:
            include_fields = ["documents", "metadatas"]
            if include_distances:
                include_fields.append("distances")
            
            results = self.entity_collection.query(
                query_embeddings=[query_entity.embedding.tolist()],
                n_results=n_results,
                include=include_fields
            )
            
            # Format results
            similar_entities = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    entity_data = {
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i]
                    }
                    if include_distances:
                        entity_data['distance'] = results['distances'][0][i]
                    similar_entities.append(entity_data)
            
            logger.debug(
                f"Found {len(similar_entities)} similar entities for {query_entity.id}",
                extra={"query_id": query_entity.id, "result_count": len(similar_entities)}
            )
            
            return similar_entities
            
        except Exception as e:
            logger.error(f"Failed to search similar entities: {str(e)}")
            raise
    
    def search_by_criteria(self, criteria: Dict[str, Any], 
                          n_results: int = 10) -> List[Dict[str, Any]]:
        """Search entities by metadata criteria.
        
        Args:
            criteria: Dictionary of metadata criteria to match
            n_results: Maximum number of results to return
            
        Returns:
            List of matching entities
        """
        try:
            results = self.entity_collection.get(
                where=criteria,
                limit=n_results,
                include=["documents", "metadatas"]
            )
            
            # Format results
            matching_entities = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    matching_entities.append({
                        'id': results['ids'][i],
                        'document': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })
            
            logger.debug(
                f"Found {len(matching_entities)} entities matching criteria {criteria}",
                extra={"criteria": criteria, "result_count": len(matching_entities)}
            )
            
            return matching_entities
            
        except Exception as e:
            logger.error(f"Failed to search by criteria: {str(e)}")
            raise
    
    def remove_embeddings(self, entities: List[Entity]) -> List[Entity]:
        """Remove embeddings from entities (debedding operation).
        
        Args:
            entities: Entities to remove embeddings from
            
        Returns:
            Entities with embeddings removed
        """
        try:
            # Convert to embeddable format and use EmbeddingManager
            embeddables = [EmbeddableEntity.from_entity(entity) for entity in entities]
            debedded = self.embedding_manager.debed_batch(embeddables)
            
            # Update original entities
            for entity in entities:
                entity.embedding = None
            
            logger.debug(
                f"Removed embeddings from {len(entities)} entities",
                extra={"entity_count": len(entities)}
            )
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to remove embeddings: {str(e)}")
            raise
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics from the EmbeddingManager.
        
        Returns:
            Dictionary containing cache performance metrics
        """
        try:
            return {
                "cache_size": self.embedding_manager.cache_size,
                "cache_dimension": self.embedding_manager.embedding_dimension,
                "batch_size": self.embedding_manager.batch_size,
                "max_cache_size": self.embedding_manager.max_cache_size
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {}
    
    def cleanup(self) -> None:
        """Cleanup resources used by the embedding service."""
        try:
            if hasattr(self.embedding_manager, 'close'):
                self.embedding_manager.close()
            self.chroma_manager.cleanup()
            logger.info("EntityEmbeddingService cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")