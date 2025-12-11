Error Codes
===========

This document defines the error code taxonomy used throughout the Babylon
simulation engine. Error codes are organized into ranges by subsystem.

System Metrics (1000-1999)
--------------------------

Core system resource monitoring errors.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 1000
     - Invalid CPU usage value
   * - 1001
     - Invalid memory usage value
   * - 1002
     - Invalid disk usage value
   * - 1003
     - GPU metrics collection failed
   * - 1004
     - System metrics validation failed

Metrics Collection (1500-1599)
------------------------------

Performance metrics recording and analysis errors.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 1500
     - Failed to record metric
   * - 1501
     - Invalid metric name
   * - 1502
     - Invalid metric value
   * - 1503
     - Metric validation failed
   * - 1504
     - Context validation failed
   * - 1505
     - Failed to save metrics to disk
   * - 1506
     - Failed to load metrics from disk
   * - 1507
     - Failed to analyze metrics
   * - 1508
     - Failed to generate suggestions
   * - 1509
     - Failed to calculate statistics

AI Metrics (2000-2999)
----------------------

AI subsystem and embedding errors.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 2000
     - Query latency exceeds threshold
   * - 2001
     - Memory usage exceeds threshold
   * - 2002
     - Cache hit rate below threshold
   * - 2003
     - Invalid embedding dimension
   * - 2004
     - Token count validation failed

Context Window Errors (2100-2199)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Errors specific to the Context Window Management system.

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
   * - 2110
     - Content Priority Error
   * - 2111
     - Content Removal Error
   * - 2112
     - Content Insertion Error
   * - 2120
     - Lifecycle Integration Error
   * - 2121
     - Metrics Collection Error
   * - 2122
     - Configuration Error

**Error Hierarchy:**

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

Context Window Error Categories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Token counting issues** (2101): Invalid token count or counting failure
- **Capacity management** (2102, 2103): Context window full or optimization failed
- **Content operations** (2110-2112): Priority, removal, or insertion failures
- **Integration issues** (2120-2122): Lifecycle, metrics, or config problems

Recovery Patterns
^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Recovery Strategy
   * - 2102
     - Trigger manual optimization with ``context_window.optimize(target_tokens)``
   * - 2103
     - Reduce ``min_content_importance`` or increase ``capacity_threshold``
   * - 2110
     - Verify importance scores are in range [0.0, 1.0]
   * - 2111
     - Check content_id exists before removal
   * - 2112
     - Verify content format and token count before insertion
   * - 2122
     - Validate ``ContextWindowConfig`` parameters against defaults

Gameplay Metrics (3000-3999)
----------------------------

Simulation and gameplay event errors.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 3000
     - Invalid session duration
   * - 3001
     - Event count validation failed
   * - 3002
     - User choice validation failed
   * - 3003
     - Contradiction intensity validation failed

Collection Errors (4000-4999)
-----------------------------

Data collection and persistence errors.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 4000
     - Metrics collection failed
   * - 4001
     - Persistence operation failed
   * - 4002
     - Alert threshold exceeded
   * - 4003
     - Metric validation failed

Integration Errors (5000-5999)
------------------------------

External system integration errors.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 5000
     - ChromaDB operation failed
   * - 5001
     - Entity registry operation failed
   * - 5002
     - Concurrent operation failed
   * - 5003
     - Persistence verification failed

Backup Errors (6000-6999)
-------------------------

Backup and restore operation errors.

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Code
     - Description
   * - 6000
     - Backup creation failed
   * - 6001
     - Backup verification failed
   * - 6002
     - Insufficient disk space
   * - 6003
     - Backup path inaccessible
   * - 6004
     - Backup metadata corruption
   * - 6005
     - Backup compression failed
   * - 6006
     - Restore operation failed
   * - 6007
     - Backup integrity check failed
   * - 6008
     - Backup cleanup failed
   * - 6009
     - Concurrent backup conflict

Backup Error Categories
~~~~~~~~~~~~~~~~~~~~~~~

- **Space validation failures** (6002): Insufficient disk space for backup
- **Access permission issues** (6003): Cannot access backup path
- **Data integrity problems** (6004, 6007): Corrupted or invalid backup data
- **Operation failures** (6000, 6005, 6006): Backup/restore operations failed
- **Resource cleanup issues** (6008): Failed to clean up old backups

See Also
--------

- :doc:`/concepts/context-window` - Context window management details
- :doc:`configuration` - Configuration system documentation
