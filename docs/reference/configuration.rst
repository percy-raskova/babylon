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

Economy Parameters
~~~~~~~~~~~~~~~~~~

Control imperial rent extraction and wealth flows:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``extraction_efficiency``
     - 0.8
     - Fraction of surplus captured as imperial rent
   * - ``tribute_rate``
     - 0.1
     - Base rate of tribute extraction per tick
   * - ``wage_floor``
     - 0.05
     - Minimum wage (prevents zero-wealth)
   * - ``wealth_transfer_rate``
     - 0.15
     - Rate of wealth movement along edges

Consciousness Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

Control ideology drift and bifurcation:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``drift_sensitivity_k``
     - 0.1
     - How fast ideology changes per tick
   * - ``agitation_threshold``
     - 0.3
     - Minimum agitation to trigger drift
   * - ``consciousness_cap``
     - 1.0
     - Maximum consciousness value
   * - ``bifurcation_enabled``
     - True
     - Enable George Jackson model

Solidarity Parameters
~~~~~~~~~~~~~~~~~~~~~

Control SOLIDARITY edge dynamics:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``decay_base``
     - 0.95
     - Solidarity decay per tick (0.95 = 5% decay)
   * - ``transmission_rate``
     - 0.1
     - Consciousness spread along edges
   * - ``formation_threshold``
     - 0.3
     - Consciousness needed to form new edges
   * - ``min_strength``
     - 0.05
     - Edges below this are pruned

Survival Parameters
~~~~~~~~~~~~~~~~~~~

Control survival calculus:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``subsistence_threshold``
     - 0.2
     - Wealth level for basic survival
   * - ``sigmoid_steepness``
     - 10.0
     - Steepness of P(S|A) sigmoid curve
   * - ``loss_aversion``
     - 2.0
     - Kahneman-Tversky loss aversion factor
   * - ``revolution_damping``
     - 0.5
     - Reduces P(S|R) (revolution is risky)

Territory Parameters
~~~~~~~~~~~~~~~~~~~~

Control carceral geography:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``heat_threshold``
     - 0.8
     - Heat level triggering eviction
   * - ``heat_decay``
     - 0.1
     - Heat reduction per tick
   * - ``spillover_coefficient``
     - 0.2
     - Heat transferred on displacement
   * - ``detention_duration``
     - 5
     - Ticks in detention before incarceration
   * - ``displacement_priority``
     - BALANCED
     - Default mode (LABOR_SCARCE/BALANCED/ELIMINATION)

See :doc:`/how-to/parameter-tuning` for usage examples and tuning workflows.

Best Practices
--------------

1. **Use environment variables** for sensitive information
2. **Keep defaults reasonable** for development environments
3. **Document all configuration changes** in commit messages
4. **Validate configuration at startup** using Pydantic validation
5. **Use type hints** for all settings

See Also
--------

- :doc:`/how-to/parameter-tuning` - Parameter tuning workflow guide
- :py:mod:`babylon.config` - Configuration module API
- :doc:`error-codes` - Error code reference
