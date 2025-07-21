#!/usr/bin/env python3
"""
Example demonstrating ChromaDB RAG integration for Babylon.

This script shows how to use the new RAG system to:
1. Ingest documents (text files or strings)
2. Query for relevant content  
3. Generate context for LLM prompts

Run with: python examples/rag_example.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the src directory to the path so we can import babylon modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from babylon.rag import RagPipeline, RagConfig

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate the RAG system capabilities."""
    
    print("🚀 Starting Babylon RAG System Demo\n")
    
    # Sample documents to ingest
    documents = [
        {
            "id": "marxist_theory",
            "content": """
            Historical materialism is the Marxist method for understanding history and society. 
            It posits that the material conditions of a society—particularly the economic base—
            fundamentally determine its social structure, politics, and culture.
            
            The dialectical process involves the interaction of opposing forces (thesis and antithesis) 
            that result in a new synthesis. In historical terms, this means that contradictions within 
            social systems eventually lead to revolutionary change.
            
            The class struggle is central to Marxist analysis. In capitalist society, the fundamental 
            contradiction exists between the bourgeoisie (who own the means of production) and the 
            proletariat (who sell their labor power).
            """
        },
        {
            "id": "babylon_lore",  
            "content": """
            In the world of Babylon, advanced AI systems have created a post-scarcity society,
            but the old class structures persist through control of information and social algorithms.
            
            The game explores themes of technological liberation versus algorithmic oppression.
            Players navigate a world where the means of production have been automated, but
            the question remains: who controls the automation?
            
            Characters in Babylon must grapple with questions of digital labor, virtual property,
            and the nature of consciousness in an age of artificial intelligence.
            """
        },
        {
            "id": "game_mechanics",
            "content": """
            Babylon uses a dialogue-driven RPG system where player choices affect both personal
            character development and broader societal changes. The game engine incorporates
            Marxist dialectical principles into its decision-making mechanics.
            
            Resource management in Babylon focuses on social capital, information access, and
            collective action rather than traditional RPG statistics like health or mana.
            
            The AI-powered narrative system adapts to player choices, creating emergent storylines
            that demonstrate materialist historical processes in action.
            """
        }
    ]
    
    # Configure the RAG system
    config = RagConfig(
        chunk_size=800,       # Smaller chunks for better retrieval granularity
        chunk_overlap=100,    # Some overlap to maintain context
        default_top_k=5,      # Return top 5 most relevant chunks
        collection_name="babylon_knowledge"
    )
    
    # Initialize the RAG pipeline
    print("📚 Initializing RAG Pipeline...")
    pipeline = RagPipeline(config=config)
    
    try:
        # Step 1: Ingest documents
        print("\n🔄 Ingesting documents into the knowledge base...")
        
        for doc in documents:
            print(f"   📄 Processing: {doc['id']}")
            result = await pipeline.aingest_text(
                content=doc['content'],
                source_id=doc['id'],
                metadata={"document_type": "game_knowledge", "category": doc['id']}
            )
            
            if result.success:
                print(f"   ✅ Ingested {result.chunks_processed} chunks in {result.processing_time_ms:.1f}ms")
            else:
                print(f"   ❌ Failed: {result.errors}")
        
        # Show system stats
        stats = pipeline.get_stats()
        print(f"\n📊 System Stats:")
        print(f"   • Total chunks in knowledge base: {stats['total_chunks']}")
        print(f"   • Embedding cache size: {stats['embedding_cache_size']}")
        print(f"   • Collection: {stats['collection_name']}")
        
        # Step 2: Query the knowledge base
        print("\n🔍 Querying the knowledge base...\n")
        
        queries = [
            "What is historical materialism?",
            "How does Babylon incorporate Marxist themes?", 
            "What are the game mechanics in Babylon?",
            "Tell me about class struggle in the context of AI",
        ]
        
        for query in queries:
            print(f"❓ Query: {query}")
            
            response = await pipeline.aquery(query, top_k=3)
            
            print(f"   ⏱️  Processing time: {response.processing_time_ms:.1f}ms")
            print(f"   📊 Found {response.total_results} relevant chunks:")
            
            for i, result in enumerate(response.results[:3], 1):
                source = result.chunk.metadata.get('category', 'unknown') if result.chunk.metadata else 'unknown'
                similarity = result.similarity_score
                content_preview = result.chunk.content[:100].replace('\n', ' ').strip()
                
                print(f"      {i}. [{source}] (similarity: {similarity:.3f})")
                print(f"         {content_preview}...")
            
            # Generate combined context suitable for LLM prompts
            context = response.get_combined_context(max_length=1500, separator="\n---\n")
            print(f"   📝 Combined context ({len(context)} chars):")
            print(f"      {context[:200].replace('\n', ' ')}...")
            print()
        
        # Step 3: Demonstrate metadata filtering
        print("🔧 Demonstrating metadata filtering...")
        
        response = await pipeline.aquery(
            "game mechanics",
            metadata_filter={"category": "game_mechanics"},
            top_k=2
        )
        
        print(f"   📊 Results filtered to 'game_mechanics' category: {response.total_results}")
        for result in response.results:
            category = result.metadata.get('category', 'unknown') if result.metadata else 'unknown'
            print(f"      • Category: {category}")
        
        print("\n✅ RAG system demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        logger.exception("Demo failed")
    
    finally:
        # Cleanup resources
        print("\n🧹 Cleaning up resources...")
        await pipeline.aclose()
        print("👋 Demo finished.")


if __name__ == "__main__":
    # Check if we have the required environment
    try:
        import chromadb
        print("✅ ChromaDB is available")
    except ImportError:
        print("❌ ChromaDB is not installed. Please install it with: pip install chromadb")
        sys.exit(1)
    
    try:
        # Note: This demo requires OpenAI API key for embeddings
        # In a real deployment, you'd want to check for this
        print("ℹ️  Note: This demo requires OpenAI API key for embeddings.")
        print("   Set OPENAI_API_KEY environment variable if not already set.\n")
        
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user.")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logger.exception("Unexpected error in demo")
        sys.exit(1)