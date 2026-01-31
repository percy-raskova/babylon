Simulation Protocols Reference
==============================

API reference for Babylon's GUI-facing simulation protocols and snapshot models.

These protocols define the stable interface boundary between the simulation engine
and GUI code. GUI developers should depend **only** on these protocols, never on
implementation details.

Protocol Overview
-----------------

The simulation exposes two protocols:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Protocol
     - Purpose
     - Methods
   * - ``SimulationState``
     - Read-only state access
     - ``get_current_tick()``, ``get_snapshot()``, ``get_territory_state()``, ``get_hexes_for_territory()``
   * - ``SimulationControl``
     - Simulation control
     - ``step()``, ``reset()``

**Import:**

.. code-block:: python

   from babylon.protocols import SimulationState, SimulationControl

SimulationState Protocol
------------------------

Read-only interface for querying simulation state.

.. code-block:: python

   @runtime_checkable
   class SimulationState(Protocol):
       def get_current_tick(self) -> int: ...
       def get_snapshot(self) -> SimulationSnapshot: ...
       def get_territory_state(self, territory_id: str) -> TerritoryState | None: ...
       def get_hexes_for_territory(self, territory_id: str) -> set[str]: ...

Methods
~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``get_current_tick()``
     - Returns current tick number (0 = initial state)
   * - ``get_snapshot()``
     - Returns immutable ``SimulationSnapshot`` with all state
   * - ``get_territory_state(id)``
     - Returns ``TerritoryState`` for territory or ``None`` if not found
   * - ``get_hexes_for_territory(id)``
     - Returns set of H3 index strings claimed by territory

**Example:**

.. code-block:: python

   def render_map(sim: SimulationState) -> None:
       """Render all territories using protocol interface."""
       snapshot = sim.get_snapshot()
       for territory_id, state in snapshot.territories.items():
           color = profit_rate_to_color(state.profit_rate)
           render_hexes(state.hex_claims, color)

SimulationControl Protocol
--------------------------

Write interface for controlling simulation execution.

.. code-block:: python

   @runtime_checkable
   class SimulationControl(Protocol):
       def step(self, n: int = 1) -> None: ...
       def reset(self) -> None: ...

Methods
~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``step(n=1)``
     - Advance simulation by ``n`` ticks (must be positive)
   * - ``reset()``
     - Restore simulation to initial state (tick 0)

**Determinism Guarantee:**

Calling ``step(n)`` from identical initial state always produces identical results.
This enables reproducible simulations and reliable testing.

**Example:**

.. code-block:: python

   def on_step_button_click(sim: SimulationControl) -> None:
       """GUI handler for step button."""
       sim.step()
       update_display()

   def on_reset_button_click(sim: SimulationControl) -> None:
       """GUI handler for reset button."""
       sim.reset()
       update_display()

Snapshot Models
---------------

Immutable state containers returned by ``get_snapshot()``.

TerritoryState
~~~~~~~~~~~~~~

Represents a territory (county) at a specific tick.

.. code-block:: python

   class TerritoryState(BaseModel):
       model_config = ConfigDict(frozen=True)

       territory_id: str  # 5-digit FIPS code (e.g., "26163")
       controlling_polity: str
       hex_claims: frozenset[str]  # H3 cell indices
       tick: int
       profit_rate: float  # Range [0.0, 1.0]
       equilibrium_r: float  # Territory-specific equilibrium

**Fields:**

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Field
     - Type
     - Description
   * - ``territory_id``
     - ``str``
     - 5-digit FIPS code (e.g., "26163" for Wayne County)
   * - ``controlling_polity``
     - ``str``
     - ID of controlling entity (same as territory_id for MVP)
   * - ``hex_claims``
     - ``frozenset[str]``
     - Set of H3 index strings (15 hex characters each)
   * - ``tick``
     - ``int``
     - Tick number when this state was captured
   * - ``profit_rate``
     - ``float``
     - Current profit rate, clamped to [0.0, 1.0]
   * - ``equilibrium_r``
     - ``float``
     - Territory-specific equilibrium profit rate

HexState
~~~~~~~~

Represents an H3 hexagonal cell (invariant spatial substrate).

.. code-block:: python

   class HexState(BaseModel):
       model_config = ConfigDict(frozen=True)

       h3_index: str  # 15-character hex string

SimulationSnapshot
~~~~~~~~~~~~~~~~~~

Top-level container for complete simulation state.

.. code-block:: python

   class SimulationSnapshot(BaseModel):
       model_config = ConfigDict(frozen=True)

       tick: int
       territories: dict[str, TerritoryState]
       hexes: dict[str, HexState]
       edges: list[EdgeState]  # Empty for MVP

**Example:**

.. code-block:: python

   snapshot = sim.get_snapshot()
   print(f"Tick: {snapshot.tick}")
   print(f"Territories: {len(snapshot.territories)}")
   print(f"Hex cells: {len(snapshot.hexes)}")

Initialization
--------------

SQLite Hydration
~~~~~~~~~~~~~~~~

Initialize simulation from reference database:

.. code-block:: python

   from babylon.engine.simulation import Simulation

   # Initialize with Wayne and Oakland counties
   sim = Simulation.from_sqlite(["26163", "26125"])

   # Query initial state
   wayne = sim.get_territory_state("26163")
   print(f"Wayne County profit_rate: {wayne.profit_rate:.4f}")

The hydration process:

1. Queries ``dim_county`` for county metadata
2. Queries ``bridge_county_h3`` for H3 cell mappings
3. Computes initial ``profit_rate`` from QCEW/BEA data via ``MarxianHydrator``
4. Sets ``equilibrium_r = profit_rate`` for each territory

Manual Initialization
~~~~~~~~~~~~~~~~~~~~~

For testing or custom scenarios:

.. code-block:: python

   from babylon.engine.simulation import Simulation
   from babylon.models import SimulationConfig, WorldState
   from babylon.models.snapshots import TerritoryState, HexState

   # Create state objects
   territory = TerritoryState(
       territory_id="26163",
       controlling_polity="26163",
       hex_claims=frozenset(["8528a9c9bffffff"]),
       tick=0,
       profit_rate=0.15,
       equilibrium_r=0.15,
   )
   hexes = {"8528a9c9bffffff": HexState(h3_index="8528a9c9bffffff")}

   # Initialize simulation
   sim = Simulation(WorldState(), SimulationConfig())
   sim._initialize_mvp_territories(
       territories={"26163": territory},
       hexes=hexes,
   )

Per-Tick Update Rule
--------------------

Each tick updates territory profit rates using exponential smoothing:

.. code-block:: text

   r_new = r_old * (1 - decay_rate) + equilibrium_r * decay_rate

Where:

- ``decay_rate = 0.05`` (placeholder, to be replaced by TRPF mechanics)
- ``equilibrium_r`` = territory-specific equilibrium set at hydration

This formula ensures:

- Deterministic updates (same input → same output)
- Visible change each tick for GUI visualization
- Territories maintain differentiation (Wayne ≠ Oakland)

Type Checking
-------------

Both protocols are ``@runtime_checkable``, enabling isinstance checks:

.. code-block:: python

   from babylon.protocols import SimulationState, SimulationControl

   sim = Simulation.from_sqlite(["26163"])

   assert isinstance(sim, SimulationState)   # True
   assert isinstance(sim, SimulationControl)  # True

Mock implementations can be created for testing:

.. code-block:: python

   class MockSimulation:
       def get_current_tick(self) -> int:
           return 42

       def get_snapshot(self) -> SimulationSnapshot:
           return SimulationSnapshot(tick=42, territories={}, hexes={}, edges=[])

       # ... other methods

   mock = MockSimulation()
   assert isinstance(mock, SimulationState)  # True (duck typing)

See Also
--------

- :doc:`/how-to/gui-development` - GUI development patterns
- :doc:`/reference/systems` - Simulation systems reference
- :doc:`/reference/data-models` - Core data models
- :py:mod:`babylon.protocols` - Protocol source code
- :py:mod:`babylon.models.snapshots` - Snapshot model source code
