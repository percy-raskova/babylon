Object Tracking & Performance
=============================

Theoretical limits, practical working sets, and optimization strategies
for managing game objects within LLM context window constraints.

Context Window Capacity
-----------------------

Theoretical Limits
~~~~~~~~~~~~~~~~~~

With a 200k token context window:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Object Type
     - Token Estimate
     - Max Objects
   * - Simple Entity
     - ~100 tokens
     - 400-600
   * - Complex Contradiction
     - ~300-500 tokens
     - 200-300
   * - Relationship Network
     - ~200-400 tokens/network
     - Variable
   * - Event Chain
     - ~200-300 tokens
     - Variable

Token Usage Breakdown
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Component
     - Token Range
   * - Object metadata
     - 10-20 tokens
   * - Core attributes
     - 30-50 tokens
   * - Relationships
     - 20-40 tokens per connection
   * - Historical data
     - 50-100 tokens
   * - State information
     - 30-50 tokens

Practical Working Sets
----------------------

Immediate Context (Active Memory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Size**: 20-30 objects
- **Update frequency**: Every game tick
- **Access latency**: <10ms
- **Memory footprint**: ~5k tokens

Active Cache
~~~~~~~~~~~~

- **Size**: 100-200 objects
- **Update frequency**: As needed
- **Access latency**: <100ms
- **Memory footprint**: ~30k tokens

Background Context
~~~~~~~~~~~~~~~~~~

- **Size**: 300-500 objects
- **Update frequency**: Periodic
- **Access latency**: <500ms
- **Memory footprint**: ~60k tokens

Implementation
--------------

ContextWindowManager
~~~~~~~~~~~~~~~~~~~~

- Implements token counting and tracking
- Manages content prioritization based on importance scores
- Automatically optimizes context when approaching capacity threshold
  (default 75%)
- Integrates with MetricsCollector for performance tracking
- Provides configurable token limits (default 150k tokens)

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class ContextWindowConfig:
       max_token_limit: int = 150000
       capacity_threshold: float = 0.75
       prioritization_strategy: str = "hybrid"
       min_content_importance: float = 0.2

Content Management
~~~~~~~~~~~~~~~~~~

- Content is stored with metadata including token count and importance score
- Priority queue maintains content ordered by importance
- Automatic optimization removes least important content when threshold is
  reached
- Token counting supports various content types (strings, lists,
  dictionaries, objects)

Error Handling
~~~~~~~~~~~~~~

- Dedicated error codes in 2100-2199 range
- Handles capacity exceeded scenarios
- Manages content insertion and removal errors
- Provides detailed error messages with error codes

Performance Monitoring
----------------------

Key Metrics
~~~~~~~~~~~

.. code-block:: python

   class ObjectMetrics:
       def __init__(self):
           self.access_count = 0
           self.cache_hits = 0
           self.cache_misses = 0
           self.token_usage = 0
           self.load_time = 0.0
           self.last_access = None
           self.relationship_count = 0

Monitoring Points
~~~~~~~~~~~~~~~~~

**Object Access**
   - Access frequency and patterns
   - Token usage per object
   - Cache performance (hits/misses)

**Context Window**
   - Current utilization percentage
   - Token distribution across content types
   - Garbage collection triggers
   - Context switches

**Vector Database**
   - Query latency
   - Embedding generation time
   - Storage utilization
   - Index performance

Optimization Strategies
-----------------------

Client-Side Processing
~~~~~~~~~~~~~~~~~~~~~~

**Local Computations**
   - Relationship graph updates
   - Simple state changes
   - UI updates
   - Basic validation

**Caching Strategy**
   - Local object cache
   - Relationship cache
   - Embedding cache
   - State history

**Batch Operations**
   - Grouped updates
   - Bulk loading
   - Periodic synchronization
   - Deferred processing

Vector Database Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Query Optimization**
   - Relevance thresholds
   - Query batching
   - Index optimization
   - Caching layers

**Storage Strategy**
   - Compression techniques
   - Incremental updates
   - Partial loading
   - Lazy evaluation

Object Lifecycle Management
---------------------------

.. code-block:: python

   class ObjectManager:
       def __init__(self):
           self.active_objects = LRUCache(max_size=30)
           self.cached_objects = LRUCache(max_size=200)
           self.metrics = MetricsCollector()

       def get_object(self, object_id):
           self.metrics.record_access(object_id)

           if object_id in self.active_objects:
               self.metrics.record_cache_hit('active')
               return self.active_objects[object_id]

           if object_id in self.cached_objects:
               self.metrics.record_cache_hit('secondary')
               return self._promote_to_active(object_id)

           self.metrics.record_cache_miss()
           return self._load_from_vector_db(object_id)

Performance Logging
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class MetricsCollector:
       def __init__(self):
           self.logs = {
               'access_patterns': Counter(),
               'token_usage': deque(maxlen=1000),
               'cache_performance': {'hits': 0, 'misses': 0},
               'latency_metrics': {
                   'db_queries': [],
                   'context_switches': []
               }
           }

       def analyze_performance(self):
           return {
               'cache_hit_rate': self._calculate_hit_rate(),
               'avg_token_usage': self._calculate_avg_tokens(),
               'hot_objects': self._identify_hot_objects(),
               'optimization_suggestions': self._generate_suggestions()
           }

RAG + Vector Database Architecture
----------------------------------

With RAG and vector database integration:

.. mermaid::

   flowchart TB
       A["Game Objects in Vector DB<br/>(50k total)"] --> B["Query for Relevant Objects<br/>(~1000 embeddings)"]
       B --> C["Load only needed objects into context<br/>(100-200 most relevant)"]
       C --> D["Keep frequently accessed objects<br/>(20-30 working memory)"]
       D --> E["Periodically flush less relevant<br/>back to Vector DB"]
       E -.-> A

   %% Necropolis Codex styling
   classDef storage fill:#4A1818,stroke:#6B4A3A,color:#D4C9B8
   classDef process fill:#6B4A3A,stroke:#8B7B6B,color:#D4C9B8

   class A,E storage
   class B,C,D process

This architecture allows:

- Theoretically unlimited total objects in the game
- 10,000s of objects in vector DB
- Only relevant subset loaded into context
- Example distribution:

  - 50k total objects in vector DB
  - ~1000 objects' embeddings queried per turn
  - Top 100-200 most relevant loaded into context
  - 20-30 frequently accessed objects kept in "working memory"

Optimization Recommendations
----------------------------

Short-term
~~~~~~~~~~

1. Implement basic metrics collection
2. Set up client-side caching
3. Monitor token usage
4. Track access patterns

Medium-term
~~~~~~~~~~~

1. Optimize query patterns
2. Implement smart prefetching
3. Enhance client-side processing
4. Refine caching strategies

Long-term
~~~~~~~~~

1. Develop advanced compression
2. Implement predictive loading
3. Create adaptive optimization
4. Build performance analytics

Practical Limitations
---------------------

- Query latency to vector DB
- Cost of embedding generation
- Need for coherent context management
- Risk of context fragmentation
- Processing overhead for relevance sorting

The key is not trying to load everything at once, but maintaining a
dynamic "working set" of objects relevant to the current game state
and player actions.

See Also
--------

- :doc:`context-window` - Context window management details
- :doc:`ai-integration` - AI communications guide
- :doc:`/reference/context-window-api` - Complete API reference
- :doc:`/reference/error-codes` - Error code reference
- :doc:`/reference/configuration` - Configuration system
