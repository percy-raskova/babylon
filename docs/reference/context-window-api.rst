Context Window API Reference
============================

API specification for the Context Window Management system. For conceptual
explanation, see :doc:`/concepts/context-window`.

Configuration
-------------

ContextWindowConfig
~~~~~~~~~~~~~~~~~~~

Configuration class for the Context Window Management system.

.. code-block:: python

   from babylon.rag.context_window import ContextWindowConfig

   class ContextWindowConfig:
       """Configuration for Context Window Management."""
       max_token_limit: int = 150000
       capacity_threshold: float = 0.75
       prioritization_strategy: str = "hybrid"
       min_content_importance: float = 0.2

.. list-table:: Configuration Parameters
   :header-rows: 1
   :widths: 30 15 55

   * - Parameter
     - Default
     - Description
   * - ``max_token_limit``
     - 150000
     - Maximum tokens allowed in context window
   * - ``capacity_threshold``
     - 0.75
     - Percentage at which auto-optimization triggers
   * - ``prioritization_strategy``
     - ``"hybrid"``
     - Strategy for content ordering (see below)
   * - ``min_content_importance``
     - 0.2
     - Minimum importance score to retain during optimization

Prioritization Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Strategy
     - Description
   * - ``relevance``
     - Prioritizes based on importance score only
   * - ``recency``
     - Prioritizes based on access time only
   * - ``hybrid``
     - Combines importance, recency, and frequency (default)

Token Capacity
--------------

Theoretical Limits
~~~~~~~~~~~~~~~~~~

Based on 200k token context window:

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

Token Usage by Component
~~~~~~~~~~~~~~~~~~~~~~~~

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

Working Set Tiers
-----------------

Immediate Context (Active Memory)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70

   * - Size
     - 20-30 objects
   * - Update frequency
     - Every game tick
   * - Access latency
     - <10ms
   * - Memory footprint
     - ~5k tokens

Active Cache
~~~~~~~~~~~~

.. list-table::
   :widths: 30 70

   * - Size
     - 100-200 objects
   * - Update frequency
     - As needed
   * - Access latency
     - <100ms
   * - Memory footprint
     - ~30k tokens

Background Context
~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70

   * - Size
     - 300-500 objects
   * - Update frequency
     - Periodic
   * - Access latency
     - <500ms
   * - Memory footprint
     - ~60k tokens

API Classes
-----------

ContextWindowManager
~~~~~~~~~~~~~~~~~~~~

Central class for managing the context window.

.. code-block:: python

   from babylon.rag.context_window import ContextWindowManager, ContextWindowConfig
   from babylon.metrics.collector import MetricsCollector

   # Initialize
   config = ContextWindowConfig(max_token_limit=100000)
   metrics = MetricsCollector()
   manager = ContextWindowManager(config=config, metrics_collector=metrics)

**Methods:**

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Method
     - Description
   * - ``add_content(content_id, content, token_count, importance)``
     - Add content to context window
   * - ``get_content(content_id)``
     - Retrieve content by ID
   * - ``remove_content(content_id)``
     - Remove content from context window
   * - ``optimize(target_tokens)``
     - Manually trigger optimization
   * - ``get_stats()``
     - Get current statistics

ObjectMetrics
~~~~~~~~~~~~~

Performance metrics for tracked objects.

.. code-block:: python

   class ObjectMetrics:
       access_count: int = 0
       cache_hits: int = 0
       cache_misses: int = 0
       token_usage: int = 0
       load_time: float = 0.0
       last_access: datetime | None = None
       relationship_count: int = 0

ObjectManager
~~~~~~~~~~~~~

Lifecycle management for game objects.

.. code-block:: python

   class ObjectManager:
       active_objects: LRUCache  # max_size=30
       cached_objects: LRUCache  # max_size=200
       metrics: MetricsCollector

**Methods:**

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Method
     - Description
   * - ``get_object(object_id)``
     - Retrieve object with caching
   * - ``_promote_to_active(object_id)``
     - Move object from cache to active
   * - ``_load_from_vector_db(object_id)``
     - Load object from ChromaDB

MetricsCollector
~~~~~~~~~~~~~~~~

Performance monitoring and analysis.

.. code-block:: python

   class MetricsCollector:
       logs: dict  # access_patterns, token_usage, cache_performance, latency_metrics

**Methods:**

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Method
     - Description
   * - ``record_access(object_id)``
     - Record object access event
   * - ``record_cache_hit(cache_level)``
     - Record cache hit (active/secondary)
   * - ``record_cache_miss()``
     - Record cache miss
   * - ``analyze_performance()``
     - Generate performance analysis report

Usage Examples
--------------

Basic Content Management
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from babylon.rag.context_window import ContextWindowManager, ContextWindowConfig

   # Create manager
   config = ContextWindowConfig(
       max_token_limit=100000,
       capacity_threshold=0.8,
       prioritization_strategy="hybrid"
   )
   manager = ContextWindowManager(config=config)

   # Add content
   manager.add_content(
       content_id="document1",
       content="Sample document text",
       token_count=5,
       importance=0.8
   )

   # Retrieve content
   content = manager.get_content("document1")

   # Remove content
   manager.remove_content("document1")

   # Get statistics
   stats = manager.get_stats()

Handling Capacity Errors
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from babylon.rag.context_window import CapacityExceededError

   try:
       manager.add_content("large_doc", "..." * 10000, 30000, 0.5)
   except CapacityExceededError as e:
       print(f"Error {e.code}: {e}")
       manager.optimize(target_tokens=50000)

Error Codes
-----------

Context window errors use codes in the 2100-2199 range.
See :doc:`/reference/error-codes` for the complete taxonomy.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 2100
     - Base Context Window Error
   * - 2101
     - Token Count Error
   * - 2102
     - Capacity Exceeded Error
   * - 2103
     - Optimization Failed Error
   * - 2110-2112
     - Content Operation Errors
   * - 2120-2122
     - Integration Errors

See Also
--------

- :doc:`/concepts/context-window` - Conceptual explanation
- :doc:`/concepts/object-tracking` - Object lifecycle and optimization
- :doc:`/reference/error-codes` - Error code reference
- :doc:`/reference/configuration` - System configuration
