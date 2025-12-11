Configuration System
====================

The configuration system provides centralized management of application
settings through environment variables, configuration files, and runtime
configuration.

Overview
--------

Configuration in Babylon is managed through several modules:

- :py:mod:`babylon.config.base` - Base configuration class
- :py:mod:`babylon.config.defines` - Game parameter definitions (GameDefines)
- :py:mod:`babylon.config.chromadb_config` - ChromaDB vector database settings
- :py:mod:`babylon.config.llm_config` - LLM/AI integration settings
- :py:mod:`babylon.config.logging_config` - Logging configuration

Base Configuration
------------------

The ``BaseConfig`` class serves as the foundation for all configuration
management.

Database Settings
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Setting
     - Description
   * - ``DATABASE_URL``
     - SQLite connection string (default: ``sqlite:///babylon.db``)

ChromaDB Settings
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Setting
     - Description
   * - ``CHROMA_PERSIST_DIR``
     - Vector database persistence directory
   * - ``CHROMA_COLLECTION_NAME``
     - Default collection name
   * - ``EMBEDDING_MODEL``
     - Model name for embeddings

Metrics Collection
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Setting
     - Description
   * - ``METRICS_ENABLED``
     - Enable/disable metrics collection
   * - ``METRICS_INTERVAL``
     - Collection interval in seconds
   * - ``METRICS_RETENTION_DAYS``
     - Data retention period

Logging Configuration
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Setting
     - Description
   * - ``LOG_LEVEL``
     - Minimum logging level
   * - ``LOG_FORMAT``
     - Log message format
   * - ``LOG_DIR``
     - Log file directory

Performance Thresholds
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Setting
     - Description
   * - ``MAX_QUERY_LATENCY_MS``
     - Maximum acceptable query latency
   * - ``MIN_CACHE_HIT_RATE``
     - Minimum acceptable cache hit rate
   * - ``MAX_MEMORY_USAGE_GB``
     - Maximum memory usage threshold

Usage Examples
--------------

Accessing configuration:

.. code-block:: python

   from babylon.config.base import BaseConfig

   # Access configuration
   db_url = BaseConfig.DATABASE_URL
   log_level = BaseConfig.LOG_LEVEL

   # Override settings
   BaseConfig.METRICS_ENABLED = False

Environment Variables
---------------------

The following environment variables can be used to override default settings:

.. code-block:: bash

   # Database (SQLite)
   DATABASE_URL=sqlite:///babylon.db

   # ChromaDB
   BABYLON_CHROMA_PERSIST_DIR=/path/to/persist
   BABYLON_EMBEDDING_MODEL=all-MiniLM-L6-v2

   # Metrics
   BABYLON_METRICS_ENABLED=true
   BABYLON_METRICS_INTERVAL=60

   # Logging
   BABYLON_LOG_LEVEL=INFO
   BABYLON_LOG_DIR=/path/to/logs

GameDefines
-----------

All tunable game coefficients are centralized in the ``GameDefines`` Pydantic
model:

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()  # Load defaults from pyproject.toml
   defines.economy.extraction_efficiency  # 0.8 default
   defines.consciousness.drift_sensitivity_k  # Consciousness drift rate

Categories include:

- ``economy`` - Economic parameters (extraction, wages, rent)
- ``consciousness`` - Ideology drift parameters
- ``solidarity`` - SOLIDARITY edge decay and transmission
- ``survival`` - P(S|A), P(S|R) calculation parameters
- ``territory`` - Heat, eviction, displacement parameters

See :doc:`/guides/configuration` for detailed usage examples.

Best Practices
--------------

1. **Use environment variables** for sensitive information
2. **Keep defaults reasonable** for development environments
3. **Document all configuration changes** in commit messages
4. **Validate configuration at startup** using Pydantic validation
5. **Use type hints** for all settings

See Also
--------

- :doc:`/guides/configuration` - Configuration how-to guide
- :py:mod:`babylon.config` - Configuration module API
- :doc:`error-codes` - Error code reference
