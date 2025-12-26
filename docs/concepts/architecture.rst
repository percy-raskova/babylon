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

The Ledger contains 18 JSON entity collections in ``src/babylon/data/game/``:

.. list-table:: Entity Collections
   :header-rows: 1
   :widths: 30 70

   * - Collection
     - Purpose
   * - ``classes.json``
     - Class definitions (proletariat, bourgeoisie, etc.)
   * - ``locations.json``
     - Spatial locations with operational profiles
   * - ``relationships.json``
     - Initial edge definitions (solidarity, exploitation)
   * - ``contradictions.json``
     - Tension templates and resolution types
   * - ``crises.json``
     - Economic and political crisis definitions
   * - ``factions.json``
     - Political groupings with agendas
   * - ``ideologies.json``
     - Ideological positions with drift modifiers
   * - ``institutions.json``
     - State and civil society institutions
   * - ``cultures.json``, ``laws.json``, ``movements.json``
     - Cultural, legal, and social movement data
   * - ``policies.json``, ``resources.json``, ``technologies.json``
     - Economic policy, resource, and technology definitions
   * - ``revolts.json``, ``sentiments.json``
     - Uprising conditions and public sentiment data

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
   └── Attributes: heat, profile, sector_type, territory_type

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

   from babylon.rag.retrieval import VectorStore, Retriever
   from babylon.rag.chunker import DocumentChunk

   # Initialize store
   store = VectorStore(collection_name="events")

   # Store document chunks
   chunks = [
       DocumentChunk(
           content="The workers seized the factory...",
           metadata={"tick": 42, "class_id": "C001"}
       )
   ]
   store.add_chunks(chunks)

   # Query similar content
   retriever = Retriever(store)
   results = retriever.query(query="factory occupation", k=5)

The Archive enables:

- AI narrative generation from simulation state
- Pattern matching for event prediction
- Theory-grounded responses via RAG

Engine Architecture
-------------------

The simulation engine orchestrates the three layers:

.. mermaid::

   flowchart TB
       subgraph Input
           WS[WorldState]
           SC[SimulationConfig]
       end
       WS --> step["step()"]
       SC --> step
       step -->|"to_graph()"| G[NetworkX DiGraph]
       subgraph Engine["SimulationEngine.run_tick()"]
           G --> S1[1. ImperialRentSystem]
           S1 --> S2[2. SolidaritySystem]
           S2 --> S3[3. ConsciousnessSystem]
           S3 --> S4[4. SurvivalSystem]
           S4 --> S5[5. StruggleSystem]
           S5 --> S6[6. ContradictionSystem]
           S6 --> S7[7. TerritorySystem]
       end
       S7 --> OBS[Observers]
       OBS -->|"from_graph()"| WS2[New WorldState]

Dependency Injection
^^^^^^^^^^^^^^^^^^^^

The engine uses dependency injection via ``ServiceContainer``:

.. code-block:: python

   from babylon.engine import ServiceContainer, EventBus
   from babylon.engine.formula_registry import FormulaRegistry
   from babylon.engine.database import DatabaseConnection
   from babylon.config.defines import GameDefines
   from babylon.models import SimulationConfig

   services = ServiceContainer(
       config=SimulationConfig(),
       database=DatabaseConnection(":memory:"),
       event_bus=EventBus(),
       formulas=FormulaRegistry(),
       defines=GameDefines(),
   )

This enables:

- Easy testing with mock services
- Formula hot-swapping for experimentation
- Clean separation of infrastructure concerns

Observer Pattern
^^^^^^^^^^^^^^^^

Observers implement the ``SimulationObserver`` protocol to receive state
change notifications without modifying state:

.. code-block:: python

   from babylon.engine.observer import SimulationObserver

   class MyObserver(SimulationObserver):
       @property
       def name(self) -> str:
           return "MyObserver"

       def on_simulation_start(self, initial_state, config): ...
       def on_tick(self, previous_state, new_state): ...
       def on_simulation_end(self, final_state): ...

Current observers:

- **TopologyMonitor** - Tracks solidarity network condensation via percolation theory
- **EconomyMonitor** - Detects economic crises (>20% imperial rent pool drops)
- **CausalChainObserver** - Detects Shock Doctrine pattern (crash → austerity → radicalization)

Validation utilities (in ``babylon.engine.observers``):

- ``validate_narrative_frame()`` - Validate NarrativeFrame against JSON Schema
- ``is_valid_narrative_frame()`` - Boolean validation check

Data Flow Summary
-----------------

.. mermaid::

   flowchart TB
       subgraph TICK["SIMULATION TICK"]
           subgraph LEDGER["LEDGER (Pydantic)"]
               WS[WorldState<br/>- classes<br/>- territories<br/>- relationships]
           end
           subgraph TOPOLOGY["TOPOLOGY (NetworkX)"]
               G[nx.DiGraph<br/>- nodes<br/>- edges]
           end
           subgraph OUTPUT["OUTPUT"]
               NS[New State<br/>validated]
               ARCHIVE[ARCHIVE<br/>ChromaDB]
           end
           WS -->|"to_graph()"| G
           G -->|"Systems mutate graph"| G
           G -->|"from_graph()"| NS
           G -->|"Store event narratives"| ARCHIVE
       end

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
- :doc:`/concepts/simulation-systems` - System architecture explanation
- :doc:`/reference/data-models` - Complete entity and type specifications
- :doc:`/reference/systems` - Systems API reference
- :doc:`/api/engine` - Engine API reference
