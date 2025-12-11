Context Window Management
=========================

The Context Window Management system maintains and prioritizes content
within token limitations for the RAG (Retrieval Augmented Generation)
system, ensuring the most relevant information is preserved when
constraints are reached.

Purpose
-------

Efficiently manage token usage while prioritizing relevant content to
optimize the use of the available context window (typically 200k tokens
for Claude models).

Architecture
------------

Core Components
~~~~~~~~~~~~~~~

**ContextWindowManager**
   Central class that manages the context window:

   - Tracks token usage and content prioritization
   - Implements automatic optimization when approaching capacity threshold
   - Integrates with MetricsCollector for performance tracking

**ContextWindowConfig**
   Configuration class for the Context Window Management system:

   - Defines token limits, capacity thresholds, and prioritization strategies
   - Provides default values and integration with BaseConfig

**Token Counter**
   Utility for counting tokens in various content types:

   - Supports strings, lists, dictionaries, and objects
   - Provides consistent token counting across the system

**Error Handling**
   Dedicated error codes in the 2100-2199 range with specialized
   exceptions for different error scenarios.

Data Structures
~~~~~~~~~~~~~~~

**Content Storage**
   Dictionary-based storage for content items with metadata:

   - Token count
   - Importance score
   - Last access time
   - Access frequency

**Priority Queue**
   Maintains content ordered by importance:

   - Supports hybrid prioritization based on multiple factors
   - Enables efficient optimization when capacity threshold is reached

Configuration Options
---------------------

.. code-block:: python

   class ContextWindowConfig:
       """Configuration for the Context Window Management system."""
       max_token_limit: int = 150000       # Default to 150k tokens
       capacity_threshold: float = 0.75    # Default to 75% capacity
       prioritization_strategy: str = "hybrid"  # relevance, recency, hybrid
       min_content_importance: float = 0.2  # Minimum importance to keep

Content Prioritization
----------------------

The system prioritizes content based on a combination of factors:

**Importance Score**
   Explicitly assigned importance value (0.0-1.0)

**Recency**
   How recently the content was accessed

**Access Frequency**
   How often the content is accessed

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

Optimization Process
--------------------

When the context window approaches the capacity threshold (default 75%):

1. Calculate priority scores for all content items
2. Sort content by priority (lowest first)
3. Remove lowest priority items until below target capacity
4. Update metrics and statistics

Integration Points
------------------

MetricsCollector Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Records token usage for performance monitoring
- Tracks optimization events and content management
- Provides statistics for analysis and optimization

LifecycleManager Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Prepares for integration with object lifecycle management
- Will coordinate with lifecycle events for content management
- Enables seamless integration with the broader RAG system

BaseConfig Integration
~~~~~~~~~~~~~~~~~~~~~~

- Uses configuration values from BaseConfig when available
- Falls back to sensible defaults when not configured
- Provides a consistent configuration approach

Error Handling
--------------

Error Codes (2100-2199)
~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   flowchart TB
       CWE["ContextWindowError (2100)"] --> TCE["TokenCountError (2101)"]
       CWE --> CEE["CapacityExceededError (2102)"]
       CWE --> OFE["OptimizationFailedError (2103)"]
       CWE --> CPE["ContentPriorityError (2110)"]
       CWE --> CRE["ContentRemovalError (2111)"]
       CWE --> CIE["ContentInsertionError (2112)"]
       CWE --> LIE["LifecycleIntegrationError (2120)"]
       CWE --> MCE["MetricsCollectionError (2121)"]
       CWE --> CFE["ConfigurationError (2122)"]

See :doc:`/reference/error-codes` for the complete error code reference.

Usage Examples
--------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from babylon.rag.context_window import ContextWindowManager, ContextWindowConfig
   from babylon.metrics.collector import MetricsCollector

   # Create configuration
   config = ContextWindowConfig(
       max_token_limit=100000,
       capacity_threshold=0.8,
       prioritization_strategy="hybrid"
   )

   # Create manager
   metrics_collector = MetricsCollector()
   context_window = ContextWindowManager(
       config=config,
       metrics_collector=metrics_collector
   )

   # Add content
   context_window.add_content(
       content_id="document1",
       content="This is a sample document",
       token_count=5,
       importance=0.8
   )

   # Get content
   content = context_window.get_content("document1")

   # Remove content
   context_window.remove_content("document1")

   # Get statistics
   stats = context_window.get_stats()

Handling Optimization
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Manually trigger optimization
   context_window.optimize(target_tokens=50000)

   # Automatic optimization occurs when adding content
   # that would exceed threshold
   try:
       context_window.add_content(
           "large_content", "..." * 10000, 30000, 0.5
       )
   except CapacityExceededError as e:
       print(f"Error {e.code}: {e}")

Current Status
--------------

**Implemented:**

- Token counting and tracking
- Content prioritization
- Automatic optimization
- MetricsCollector integration
- Comprehensive error handling
- Unit tests with >80% coverage

**Pending:**

- LifecycleManager integration
- More sophisticated prioritization algorithms
- Performance optimizations for large content sets

Key Considerations
------------------

- Performance is critical as this system operates in the critical path
- Token counting must be consistent with the underlying model's tokenization
- Prioritization logic may need tuning based on specific use cases
- Error handling should be robust to prevent cascading failures
- Memory usage should be optimized for large content sets

See Also
--------

- :doc:`object-tracking` - Object lifecycle and RAG optimization
- :doc:`ai-integration` - AI communications guide
- :doc:`/reference/error-codes` - Error code reference
- :doc:`/reference/configuration` - Configuration system
