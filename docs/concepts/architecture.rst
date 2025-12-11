Architecture: The Embedded Trinity
===================================

Babylon's architecture is built on three interconnected data layers that work
together to simulate class struggle as a deterministic output of material
conditions.

Overview
--------

The simulation runs locally without external servers, using what we call
the **Embedded Trinity**:

.. note::
   Architecture diagram (The Embedded Trinity) planned for future addition.

1. **The Ledger** - Rigid material state (Pydantic/SQLite)
2. **The Topology** - Fluid relational state (NetworkX)
3. **The Archive** - Semantic history (ChromaDB)

This architecture separates concerns:

- **State is pure data** - Pydantic models with strict validation
- **Engine is pure transformation** - Stateless functions on graphs
- **They never mix** - Clean separation enables testing and reasoning

The Ledger: Material State
--------------------------

The Ledger stores **rigid, quantitative state** that changes discretely:

- Economic values (wealth, wages, tribute)
- Political attributes (repression, organization)
- Class positions (proletariat, bourgeoisie, lumpen)
- Territorial properties (heat, operational profile)

Data Storage
^^^^^^^^^^^^

The Ledger uses two complementary systems:

**Pydantic Models**
   In-memory state with strict validation. All game entities derive from
   Pydantic ``BaseModel`` with constrained types:

   .. code-block:: python

      from babylon.models import SocialClass, Probability, Currency

      class SocialClass(BaseModel):
          id: str = Field(pattern=r"^C[0-9]{3}$")
          role: SocialRole
          wealth: Currency = Field(ge=0.0)
          organization: Probability  # Constrained to [0, 1]

**SQLite Database**
   Persistent storage for history and checkpoints. The
   :py:class:`~babylon.engine.database.DatabaseConnection` class manages
   SQLAlchemy sessions.

Entity Collections
^^^^^^^^^^^^^^^^^^

The Ledger contains 17 JSON entity collections in ``src/babylon/data/game/``:

.. list-table:: Entity Collections
   :header-rows: 1
   :widths: 30 70

   * - Collection
     - Purpose
   * - ``social_classes.json``
     - Class definitions (proletariat, bourgeoisie, etc.)
   * - ``territories.json``
     - Spatial locations with operational profiles
   * - ``relationships.json``
     - Initial edge definitions
   * - ``contradictions.json``
     - Tension templates and resolution types
   * - ``events.json``
     - Trigger-effect definitions
   * - ...
     - (13 additional collections)

The Topology: Relational State
------------------------------

The Topology stores **fluid, relational state** that changes continuously:

- Class solidarity networks
- Economic extraction flows
- Territorial adjacency
- Imperial tribute chains

Graph Structure
^^^^^^^^^^^^^^^

Babylon uses a NetworkX ``DiGraph`` (directed graph) with two node types
and multiple edge types:

**Node Types:**

.. code-block:: text

   social_class (C001, C002, ...)
   └── Attributes: wealth, organization, ideology, consciousness

   territory (T001, T002, ...)
   └── Attributes: heat, operational_profile, displacement_priority

**Edge Types:**

.. list-table:: Edge Types
   :header-rows: 1
   :widths: 20 20 60

   * - Edge Type
     - Direction
     - Meaning
   * - EXPLOITATION
     - bourgeoisie → proletariat
     - Economic extraction relationship
   * - SOLIDARITY
     - bidirectional
     - Class consciousness connection
   * - WAGES
     - employer → worker
     - Labor-wage payment flow
   * - TRIBUTE
     - periphery → core
     - Imperial value transfer
   * - TENANCY
     - class → territory
     - Spatial occupation
   * - ADJACENCY
     - territory → territory
     - Spatial proximity (spillover routes)

State Transformation
^^^^^^^^^^^^^^^^^^^^

The simulation transforms between Pydantic and graph representations:

.. code-block:: python

   # Pydantic → Graph (for computation)
   graph: nx.DiGraph = world_state.to_graph()

   # Graph operations (mutation allowed)
   engine.run_tick(graph, services, context)

   # Graph → Pydantic (for validation)
   new_state = WorldState.from_graph(graph, old_state.tick + 1)

This pattern allows:

- Flexible graph algorithms during simulation
- Strict validation on state boundaries
- Clear separation of concerns

The Archive: Semantic History
-----------------------------

The Archive stores **semantic, narrative state** for AI integration:

- Event narratives as embeddings
- Historical patterns for retrieval
- Theory corpus for RAG queries

ChromaDB Integration
^^^^^^^^^^^^^^^^^^^^

Babylon uses ChromaDB as a vector database:

.. code-block:: python

   from babylon.rag import retrieval

   # Store event narrative
   retrieval.add_event_narrative(
       event_id="E001",
       narrative="The workers seized the factory...",
       metadata={"tick": 42, "class": "C001"}
   )

   # Retrieve similar events
   similar = retrieval.query_similar_events(
       query="factory occupation",
       n_results=5
   )

The Archive enables:

- AI narrative generation from simulation state
- Pattern matching for event prediction
- Theory-grounded responses via RAG

Engine Architecture
-------------------

The simulation engine orchestrates the three layers:

.. code-block:: text

   step(WorldState, SimulationConfig) → WorldState
        │
        ├── 1. Convert to graph: state.to_graph()
        │
        ├── 2. Run systems on graph:
        │      ├── ImperialRentSystem
        │      ├── SolidaritySystem
        │      ├── ConsciousnessSystem
        │      ├── SurvivalSystem
        │      ├── ContradictionSystem
        │      ├── TerritorySystem
        │      └── StruggleSystem
        │
        ├── 3. Notify observers: TopologyMonitor
        │
        └── 4. Convert back: WorldState.from_graph()

Dependency Injection
^^^^^^^^^^^^^^^^^^^^

The engine uses dependency injection via ``ServiceContainer``:

.. code-block:: python

   from babylon.engine import ServiceContainer, EventBus

   services = ServiceContainer(
       event_bus=EventBus(),
       formula_registry=FormulaRegistry(),
       db_connection=DatabaseConnection(":memory:")
   )

This enables:

- Easy testing with mock services
- Formula hot-swapping for experimentation
- Clean separation of infrastructure concerns

Observer Pattern
^^^^^^^^^^^^^^^^

Observers receive state change notifications without modifying state:

.. code-block:: python

   class TopologyMonitor:
       def on_simulation_start(self, state, config): ...
       def on_tick(self, prev_state, new_state): ...
       def on_simulation_end(self, final_state): ...

Current observers:

- **TopologyMonitor** - Tracks solidarity network condensation
- (Future: NarrativeObserver, MetricsObserver)

Data Flow Summary
-----------------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                    SIMULATION TICK                          │
   ├─────────────────────────────────────────────────────────────┤
   │                                                             │
   │   LEDGER (Pydantic)                                         │
   │   ┌─────────────┐                                           │
   │   │ WorldState  │──────┐                                    │
   │   │ - classes   │      │ to_graph()                         │
   │   │ - territories      │                                    │
   │   │ - relationships    │                                    │
   │   └─────────────┘      ▼                                    │
   │                   ┌─────────────┐                           │
   │   TOPOLOGY        │  nx.DiGraph │                           │
   │                   │  - nodes    │◄── Systems mutate graph   │
   │                   │  - edges    │                           │
   │                   └─────────────┘                           │
   │                        │                                    │
   │                        │ from_graph()                       │
   │                        ▼                                    │
   │   ┌─────────────┐ ┌─────────────┐                           │
   │   │ New State   │ │  ARCHIVE    │                           │
   │   │ (validated) │ │  (ChromaDB) │◄── Store event narratives │
   │   └─────────────┘ └─────────────┘                           │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘

Key Design Principles
---------------------

1. **Determinism**
   Given the same initial state and configuration, the simulation
   produces identical results. Random seeds are explicit.

2. **Immutability at Boundaries**
   Pydantic models are frozen. Only graphs are mutable during computation.

3. **Validation on Entry/Exit**
   All data is validated when entering or leaving the Ledger.

4. **Graph + Math = History**
   Complex emergent behavior arises from simple topological operations
   and mathematical formulas.

See Also
--------

- :doc:`/concepts/topology` - Graph structure details
- :doc:`/api/engine` - Engine API reference
- :doc:`/guides/simulation-systems` - System implementation guide
