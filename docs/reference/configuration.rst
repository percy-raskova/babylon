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
model, organized into 16 nested configuration classes:

.. code-block:: python

   from babylon.config.defines import GameDefines

   defines = GameDefines()  # Load defaults
   defines.economy.extraction_efficiency  # 0.8 default
   defines.consciousness.sensitivity  # Consciousness drift rate
   defines.carceral.control_capacity  # Guard:prisoner ratio

   # Or load from YAML
   defines = GameDefines.load_from_yaml("custom_defines.yaml")

Economy Parameters
~~~~~~~~~~~~~~~~~~

Control imperial rent extraction, TRPF mechanics, and wealth flows:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``extraction_efficiency``
     - 0.8
     - Alpha: how efficiently core extracts value from periphery
   * - ``comprador_cut``
     - 0.90
     - Fraction of wealth kept by comprador class
   * - ``base_labor_power``
     - 1.0
     - Base value produced per tick by worker
   * - ``super_wage_rate``
     - 0.20
     - Fraction of tribute paid as super-wages
   * - ``superwage_multiplier``
     - 1.0
     - PPP multiplier for labor aristocracy
   * - ``initial_rent_pool``
     - 100.0
     - Starting imperial rent pool
   * - ``pool_high_threshold``
     - 0.7
     - Pool ratio for prosperity mode
   * - ``pool_low_threshold``
     - 0.3
     - Pool ratio for austerity mode
   * - ``pool_critical_threshold``
     - 0.1
     - Pool ratio for ECONOMIC_CRISIS
   * - ``base_subsistence``
     - 0.0005
     - Fixed cost per tick (The Calorie Check)
   * - ``death_threshold``
     - 0.001
     - Wealth below which entities die (zombie prevention)
   * - ``trpf_coefficient``
     - 0.0005
     - Rate of extraction efficiency decline (TRPF surrogate)
   * - ``rent_pool_decay``
     - 0.002
     - Background evaporation of rent pool per tick
   * - ``trpf_efficiency_floor``
     - 0.1
     - Minimum extraction efficiency after TRPF decay
   * - ``bribery_wage_delta``
     - 0.05
     - Wage increase during prosperity (BRIBERY policy)
   * - ``austerity_wage_delta``
     - -0.05
     - Wage cut during low pool (AUSTERITY policy)
   * - ``iron_fist_repression_delta``
     - 0.10
     - Repression increase during high tension

Survival Parameters
~~~~~~~~~~~~~~~~~~~

Control P(S|A) and P(S|R) survival calculus:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``steepness_k``
     - 10.0
     - Sigmoid sharpness in acquiescence probability
   * - ``default_subsistence``
     - 0.3
     - Minimum wealth for survival through compliance
   * - ``default_organization``
     - 0.1
     - Fallback organization value
   * - ``default_repression``
     - 0.5
     - Fallback repression value
   * - ``revolution_threshold``
     - 1.0
     - Tipping point for P(S|R) formula
   * - ``repression_base``
     - 0.5
     - Base resistance to revolution in denominator

Vitality Parameters
~~~~~~~~~~~~~~~~~~~

Control Mass Line population mortality dynamics:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``base_mortality_factor``
     - 0.01
     - Fraction of at-risk population that dies per tick
   * - ``inequality_impact``
     - 1.0
     - How strongly inequality affects marginal wealth

Solidarity Parameters
~~~~~~~~~~~~~~~~~~~~~

Control consciousness transmission and SOLIDARITY edge dynamics:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``scaling_factor``
     - 0.5
     - Multiplier for graph edge weights affecting organization
   * - ``activation_threshold``
     - 0.3
     - Minimum source consciousness for transmission
   * - ``mass_awakening_threshold``
     - 0.6
     - Target consciousness for MASS_AWAKENING event
   * - ``negligible_transmission``
     - 0.01
     - Threshold below which transmissions are skipped
   * - ``superwage_impact``
     - 1.0
     - How much extraction affects Core wealth

Consciousness Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

Control ideology drift dynamics:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``sensitivity``
     - 0.5
     - How quickly consciousness responds to material conditions
   * - ``decay_lambda``
     - 0.1
     - Decay rate for consciousness without material basis

Territory Parameters
~~~~~~~~~~~~~~~~~~~~

Control carceral geography and heat dynamics:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``heat_decay_rate``
     - 0.1
     - Heat decay for LOW_PROFILE territories
   * - ``high_profile_heat_gain``
     - 0.15
     - Heat gain for HIGH_PROFILE territories
   * - ``eviction_heat_threshold``
     - 0.8
     - Heat threshold for eviction pipeline
   * - ``rent_spike_multiplier``
     - 1.5
     - Rent multiplier during eviction
   * - ``displacement_rate``
     - 0.1
     - Population displacement during eviction
   * - ``heat_spillover_rate``
     - 0.05
     - Heat spillover via ADJACENCY edges

Topology Parameters
~~~~~~~~~~~~~~~~~~~

Control phase transition thresholds for solidarity network analysis:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``gaseous_threshold``
     - 0.1
     - Percolation ratio below this = atomized
   * - ``condensation_threshold``
     - 0.5
     - Percolation ratio for phase transition
   * - ``vanguard_density_threshold``
     - 0.5
     - Cadre density threshold for vanguard party

Struggle Parameters
~~~~~~~~~~~~~~~~~~~

Control Agency Layer (George Floyd Dynamic):

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``spark_probability_scale``
     - 0.1
     - Base chance for EXCESSIVE_FORCE event
   * - ``resistance_threshold``
     - 0.1
     - Minimum agitation for uprising
   * - ``wealth_destruction_rate``
     - 0.05
     - Wealth destroyed during uprising
   * - ``solidarity_gain_per_uprising``
     - 0.2
     - Solidarity increase per uprising
   * - ``jackson_threshold``
     - 0.4
     - Revolutionary capacity threshold for organized response
   * - ``revolutionary_agitation_boost``
     - 0.5
     - Agitation boost during revolutionary offensive
   * - ``fascist_identity_boost``
     - 0.2
     - National identity boost during fascist turn

Metabolism Parameters
~~~~~~~~~~~~~~~~~~~~~

Control ecological limits (Metabolic Rift):

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``entropy_factor``
     - 1.2
     - Extraction costs more than it yields
   * - ``overshoot_threshold``
     - 1.0
     - Ratio triggering ECOLOGICAL_OVERSHOOT
   * - ``max_overshoot_ratio``
     - 999.0
     - Cap for overshoot when biocapacity depleted

Carceral Parameters
~~~~~~~~~~~~~~~~~~~

Control Terminal Crisis Dynamics (labor aristocracy decomposition):

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``control_capacity``
     - 4
     - Prisoners one enforcer can control (1:N ratio)
   * - ``enforcer_fraction``
     - 0.15
     - % of former LA who become guards
   * - ``proletariat_fraction``
     - 0.85
     - % of former LA who become prisoners
   * - ``revolution_threshold``
     - 0.5
     - Prisoner organization for revolution (vs genocide)
   * - ``decomposition_delay``
     - 52
     - Ticks after SUPERWAGE_CRISIS before decomposition
   * - ``control_ratio_delay``
     - 52
     - Ticks after decomposition before ratio check
   * - ``terminal_decision_delay``
     - 1
     - Ticks after crisis before TERMINAL_DECISION

Endgame Parameters
~~~~~~~~~~~~~~~~~~

Control simulation ending detection thresholds:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``revolutionary_percolation_threshold``
     - 0.7
     - Percolation ratio for revolutionary victory
   * - ``revolutionary_consciousness_threshold``
     - 0.8
     - Average consciousness for revolutionary victory
   * - ``ecological_overshoot_threshold``
     - 2.0
     - Overshoot ratio for collapse tracking
   * - ``ecological_sustained_ticks``
     - 5
     - Consecutive ticks before collapse triggers
   * - ``fascist_majority_threshold``
     - 3
     - Nodes with national_identity > class_consciousness

Precision Parameters
~~~~~~~~~~~~~~~~~~~~

Control numerical precision for deterministic simulation:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``decimal_places``
     - 6
     - Quantization precision (10^-n)
   * - ``rounding_mode``
     - ROUND_HALF_UP
     - Rounding mode for cross-platform consistency

Timescale Parameters
~~~~~~~~~~~~~~~~~~~~

Control simulation time resolution:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``tick_duration_days``
     - 7
     - Real-world days per tick (weekly)
   * - ``weeks_per_year``
     - 52
     - Weeks per year for flow conversion

Behavioral Parameters
~~~~~~~~~~~~~~~~~~~~~

Control behavioral economics:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``loss_aversion_lambda``
     - 2.25
     - Kahneman-Tversky loss aversion coefficient

Initial Conditions
~~~~~~~~~~~~~~~~~~

Control starting values for entities:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Description
   * - ``worker_wealth``
     - 0.5
     - Starting wealth for periphery worker
   * - ``owner_wealth``
     - 0.5
     - Starting wealth for core owner
   * - ``default_population``
     - 1
     - Default population for test entities

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
