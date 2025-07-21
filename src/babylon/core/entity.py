import uuid
from datetime import datetime
from typing import Any, Optional, List
import logging

try:
    from numpy.typing import NDArray
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    # For testing without numpy
    NDArray = Any
    np = None
    HAS_NUMPY = False

logger = logging.getLogger(__name__)


class Entity:
    """Base class for all game entities."""

    def __init__(self, type: str, role: str):
        """Initialize a new Entity.

        Args:
            type: Classification of the entity (e.g., 'Class', 'Organization')
            role: The entity's role in contradictions (e.g., 'Oppressor', 'Oppressed')
        """
        # Generate a unique ID
        self.id = str(uuid.uuid4())

        # Core identity attributes
        self.type = type
        self.role = role

        # Quantitative attributes that influence contradictions
        self.freedom = 1.0  # Degree of autonomy and self-determination
        self.wealth = 1.0  # Economic and material resources
        self.stability = 1.0  # Internal cohesion and resistance to change
        self.power = 1.0  # Ability to influence other entities

        # Vector embedding (initialized as None)
        self.embedding: NDArray | None = None

        # Lifecycle tracking
        self.created_at = datetime.now()
        self.last_updated = self.created_at

    def get_metadata(self) -> dict[str, Any]:
        """Get the entity's metadata for ChromaDB storage.

        Returns:
            Dict[str, Any]: A dictionary containing the entity's attributes
        """
        return {
            "type": self.type,
            "role": self.role,
            "freedom": float(self.freedom),
            "wealth": float(self.wealth),
            "stability": float(self.stability),
            "power": float(self.power),
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    def get_content_for_embedding(self) -> str:
        """Generate text content representing this entity for embedding.

        Creates a meaningful text representation that captures the entity's essence
        for AI systems to understand and process.

        Returns:
            str: Text representation suitable for embedding
        """
        return (
            f"Entity Type: {self.type}. "
            f"Role: {self.role}. "
            f"Characteristics - Freedom: {self.freedom:.2f}, "
            f"Wealth: {self.wealth:.2f}, "
            f"Stability: {self.stability:.2f}, "
            f"Power: {self.power:.2f}. "
            f"This entity represents a {self.type.lower()} with {self.role.lower()} role "
            f"in societal contradictions."
        )

    def generate_embedding(self, embedding_model) -> None:
        """Generate vector embedding for this entity.

        Uses the provided embedding model to create a vector representation
        of this entity's content. Updates the embedding field in place.

        Args:
            embedding_model: Model to use for generating embeddings
                           (e.g., SentenceTransformer instance)

        Raises:
            Exception: If embedding generation fails
        """
        if not HAS_NUMPY:
            raise ImportError("NumPy is required for embedding generation")
            
        try:
            content = self.get_content_for_embedding()
            # Generate embedding using the model
            self.embedding = embedding_model.encode([content])[0]
            self.last_updated = datetime.now()
            
            logger.debug(
                f"Generated embedding for entity {self.id} ({self.type})",
                extra={"entity_id": self.id, "content_length": len(content)}
            )
        except Exception as e:
            logger.error(
                f"Failed to generate embedding for entity {self.id}: {str(e)}",
                extra={"entity_id": self.id, "entity_type": self.type}
            )
            raise

    def add_to_chromadb(self, collection) -> None:
        """Add this entity to a ChromaDB collection.

        Stores the entity's embedding and metadata in the specified ChromaDB collection.
        The entity must have an embedding generated before calling this method.

        Args:
            collection: ChromaDB collection to add the entity to

        Raises:
            ValueError: If embedding has not been generated
            Exception: If storage in ChromaDB fails
        """
        if self.embedding is None:
            raise ValueError(f"Entity {self.id} must have embedding generated before adding to ChromaDB")

        try:
            collection.add(
                documents=[self.get_content_for_embedding()],
                embeddings=[self.embedding.tolist()],
                metadatas=[self.get_metadata()],
                ids=[self.id]
            )
            
            logger.debug(
                f"Added entity {self.id} to ChromaDB collection",
                extra={"entity_id": self.id, "entity_type": self.type}
            )
        except Exception as e:
            logger.error(
                f"Failed to add entity {self.id} to ChromaDB: {str(e)}",
                extra={"entity_id": self.id, "entity_type": self.type}
            )
            raise

    @classmethod
    def search_similar_entities(cls, collection, query_embedding: NDArray, 
                               n_results: int = 5) -> List[dict[str, Any]]:
        """Search for entities similar to a given embedding.

        This is a "debedding" operation that retrieves entities based on
        vector similarity rather than exact matches.

        Args:
            collection: ChromaDB collection to search in
            query_embedding: Embedding vector to search for
            n_results: Number of similar entities to return

        Returns:
            List[dict]: List of similar entities with their metadata and distances

        Raises:
            Exception: If search fails
        """
        try:
            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results for easier consumption
            similar_entities = []
            if results['ids'][0]:  # Check if we got any results
                for i in range(len(results['ids'][0])):
                    similar_entities.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i]
                    })
            
            logger.debug(
                f"Found {len(similar_entities)} similar entities",
                extra={"query_results": len(similar_entities)}
            )
            
            return similar_entities
        except Exception as e:
            logger.error(f"Failed to search similar entities: {str(e)}")
            raise

    def reconstruct_from_embedding(self) -> str:
        """Reconstruct a description of this entity from its embedding.

        This is a "debedding" operation that attempts to generate meaningful
        content from the entity's vector representation.

        Returns:
            str: Reconstructed description of the entity

        Raises:
            ValueError: If no embedding exists
        """
        if self.embedding is None:
            raise ValueError(f"Entity {self.id} has no embedding to reconstruct from")

        # For now, return the original content since we don't have
        # a trained decoder model. In a full implementation, this would
        # use a model to reconstruct content from the embedding.
        return self.get_content_for_embedding()

    def get_embedding_similarity(self, other: 'Entity') -> float:
        """Calculate similarity between this entity and another.

        Args:
            other: Another Entity to compare with

        Returns:
            float: Cosine similarity score between -1 and 1

        Raises:
            ValueError: If either entity lacks an embedding
        """
        if not HAS_NUMPY:
            raise ImportError("NumPy is required for similarity calculation")
            
        if self.embedding is None or other.embedding is None:
            raise ValueError("Both entities must have embeddings for similarity calculation")

        # Calculate cosine similarity
        dot_product = np.dot(self.embedding, other.embedding)
        norm_a = np.linalg.norm(self.embedding)
        norm_b = np.linalg.norm(other.embedding)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        similarity = dot_product / (norm_a * norm_b)
        return float(similarity)
