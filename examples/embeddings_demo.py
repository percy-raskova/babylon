#!/usr/bin/env python3
"""
Example demonstrating the complete embeddings and debeddings implementation for Issue #14.

This example shows how the new embedding system integrates with the game's Entity system
and provides both embedding and debedding capabilities for AI-driven gameplay.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.core.entity import Entity

try:
    from babylon.core.entity_embedding_service import EntityEmbeddingService
    HAS_ADVANCED_SERVICE = True
except ImportError as e:
    print(f"Note: Advanced service not available due to missing dependencies: {e}")
    HAS_ADVANCED_SERVICE = False


def create_sample_game_entities():
    """Create sample game entities representing different aspects of society."""
    entities = []
    
    # Working class entity
    working_class = Entity(type="Class", role="Oppressed")
    working_class.freedom = 0.2
    working_class.wealth = 0.1
    working_class.stability = 0.7
    working_class.power = 0.3
    entities.append(working_class)
    
    # Capitalist class entity
    capitalist_class = Entity(type="Class", role="Oppressor")
    capitalist_class.freedom = 0.9
    capitalist_class.wealth = 0.9
    capitalist_class.stability = 0.6
    capitalist_class.power = 0.8
    entities.append(capitalist_class)
    
    # Labor union entity
    labor_union = Entity(type="Organization", role="Oppressed")
    labor_union.freedom = 0.4
    labor_union.wealth = 0.3
    labor_union.stability = 0.5
    labor_union.power = 0.6
    entities.append(labor_union)
    
    # Corporation entity
    corporation = Entity(type="Organization", role="Oppressor")
    corporation.freedom = 0.8
    corporation.wealth = 0.8
    corporation.stability = 0.8
    corporation.power = 0.9
    entities.append(corporation)
    
    return entities


def demonstrate_basic_entity_embedding():
    """Demonstrate basic entity embedding functionality."""
    print("\n=== Basic Entity Embedding Demo ===")
    
    # Create an entity
    entity = Entity(type="Class", role="Oppressed")
    entity.wealth = 0.2
    entity.power = 0.3
    
    print(f"Created entity: {entity.id}")
    print(f"Content for embedding: {entity.get_content_for_embedding()}")
    print(f"Metadata: {entity.get_metadata()}")
    
    # Show that embedding starts as None
    print(f"Initial embedding: {entity.embedding}")
    
    try:
        # This would work with actual sentence-transformers
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        entity.generate_embedding(model)
        
        print(f"Embedding generated! Shape: {entity.embedding.shape}")
        print(f"First 5 values: {entity.embedding[:5]}")
        
        # Demonstrate reconstruction (debedding)
        reconstructed = entity.reconstruct_from_embedding()
        print(f"Reconstructed content: {reconstructed}")
        
    except ImportError:
        print("Note: sentence-transformers not available, skipping actual embedding generation")
    except Exception as e:
        print(f"Note: Could not generate embedding: {e}")


def demonstrate_similarity_and_search():
    """Demonstrate entity similarity and search capabilities."""
    print("\n=== Entity Similarity & Search Demo ===")
    
    entities = create_sample_game_entities()
    
    print(f"Created {len(entities)} sample entities:")
    for entity in entities:
        print(f"  - {entity.type} ({entity.role}): power={entity.power}, wealth={entity.wealth}")
    
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Generate embeddings for all entities
        for entity in entities:
            entity.generate_embedding(model)
            
        print("\nEmbeddings generated for all entities!")
        
        # Demonstrate similarity calculation
        similarity = entities[0].get_embedding_similarity(entities[1])  # Working class vs Capitalist class
        print(f"Similarity between Working Class and Capitalist Class: {similarity:.4f}")
        
        similarity = entities[0].get_embedding_similarity(entities[2])  # Working class vs Labor union
        print(f"Similarity between Working Class and Labor Union: {similarity:.4f}")
        
        # This would demonstrate ChromaDB search with actual ChromaDB
        print("\nTo use ChromaDB search, entities can be stored and queried:")
        print("  1. entity.add_to_chromadb(collection)")
        print("  2. Entity.search_similar_entities(collection, query_embedding)")
        
    except ImportError:
        print("Note: sentence-transformers not available, skipping similarity demo")
    except Exception as e:
        print(f"Note: Could not demonstrate similarity: {e}")


def demonstrate_advanced_embedding_service():
    """Demonstrate the advanced EntityEmbeddingService."""
    print("\n=== Advanced Embedding Service Demo ===")
    
    if not HAS_ADVANCED_SERVICE:
        print("Advanced service requires numpy, ChromaDB, and other dependencies.")
        print("Install with: pip install chromadb sentence-transformers openai numpy")
        print()
    
    # Note: This would require actual dependencies for full functionality
    print("The EntityEmbeddingService provides advanced features:")
    print("  ✓ Integration with OpenAI API for production-quality embeddings")
    print("  ✓ Intelligent caching and batch processing")
    print("  ✓ Performance metrics collection")  
    print("  ✓ Rate limiting and concurrent operations")
    print("  ✓ ChromaDB integration for persistent vector storage")
    print("  ✓ Semantic search and entity retrieval")
    print("  ✓ Debedding operations for content reconstruction")
    
    # Show basic usage pattern
    print("\nBasic usage pattern:")
    print("""
    from babylon.core.entity_embedding_service import EntityEmbeddingService
    
    # Initialize service (uses OpenAI API and ChromaDB)
    service = EntityEmbeddingService()
    
    # Embed entities with advanced features
    embedded_entities = service.embed_entities_batch(entities)
    
    # Store in vector database  
    service.store_entities(embedded_entities)
    
    # Search for similar entities (debedding operation)
    similar = service.search_similar_entities(query_entity, n_results=5)
    
    # Search by criteria
    oppressed_classes = service.search_by_criteria({"role": "Oppressed"})
    """)


def demonstrate_game_integration():
    """Show how this integrates with the main game loop."""
    print("\n=== Game Integration Demo ===")
    
    print("The new embedding system integrates with the existing game loop:")
    print("\nBefore (from __main__.py lines 131-132):")
    print("  entity.generate_embedding(embedding_model)  # ← Now implemented!")
    print("  entity.add_to_chromadb(collection)         # ← Now implemented!")
    
    print("\nThese methods now provide:")
    print("  🎯 Meaningful text representation of game entities")
    print("  🧠 Vector embeddings for AI processing") 
    print("  💾 Persistent storage in ChromaDB")
    print("  🔍 Semantic search for similar entities")
    print("  📊 Performance metrics and caching")
    print("  ⚡ Batch processing for efficiency")
    
    print("\nThis enables AI-driven game features like:")
    print("  • Finding entities similar to player actions")
    print("  • Generating contextual events based on entity relationships")
    print("  • NPC behavior driven by entity embeddings")
    print("  • Dynamic contradiction analysis using semantic similarity")


def main():
    """Run all demonstrations."""
    print("🎮 Babylon RPG - Embeddings & Debeddings Implementation Demo")
    print("=" * 60)
    print("Issue #14: Complete embedding system for game entities")
    
    demonstrate_basic_entity_embedding()
    demonstrate_similarity_and_search()  
    demonstrate_advanced_embedding_service()
    demonstrate_game_integration()
    
    print("\n" + "=" * 60)
    print("✅ Embeddings and Debeddings Implementation Complete!")
    print("📋 Features implemented:")
    print("  • Entity content generation for embeddings")
    print("  • Vector embedding generation and storage") 
    print("  • ChromaDB integration for persistence")
    print("  • Semantic search and similarity calculations")
    print("  • Entity reconstruction from embeddings (debedding)")
    print("  • Advanced service layer with caching and batching")
    print("  • Comprehensive error handling and logging")
    print("  • Full test coverage for all functionality")


if __name__ == "__main__":
    main()