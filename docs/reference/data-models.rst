Data Models Reference
=====================

Complete specification of Babylon's data structures, entity collections,
and constrained types.

Constrained Types
-----------------

Babylon uses constrained Pydantic types to enforce valid ranges:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Type
     - Range
     - Usage
   * - ``Probability``
     - [0.0, 1.0]
     - Organization, consciousness, survival probability
   * - ``Currency``
     - >= 0.0
     - Wealth, wages, tribute amounts
   * - ``Intensity``
     - [0.0, 1.0]
     - Tension, heat, solidarity strength
   * - ``Ideology``
     - [-1.0, 1.0]
     - -1 = revolutionary, +1 = fascist
   * - ``Coefficient``
     - Unbounded float
     - Formula parameters, multipliers

**Import:**

.. code-block:: python

   from babylon.models import Probability, Currency, Intensity, Ideology

Core Entity Models
------------------

SocialClass
~~~~~~~~~~~

Represents a social class in the simulation.

.. code-block:: python

   class SocialClass(BaseModel):
       id: str = Field(pattern=r"^C[0-9]{3}$")
       role: SocialRole
       name: str
       wealth: Currency = Field(ge=0.0)
       organization: Probability
       consciousness: Probability
       ideology: Ideology
       repression: Intensity
       tension: Intensity

**Enums:**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - SocialRole
     - Values
   * - ``PROLETARIAT``
     - Working class (wage laborers)
   * - ``BOURGEOISIE``
     - Capitalist class (owners)
   * - ``LUMPENPROLETARIAT``
     - Excluded/marginalized class
   * - ``PETIT_BOURGEOISIE``
     - Small business owners
   * - ``LABOR_ARISTOCRACY``
     - Privileged workers (core nations)

Territory
~~~~~~~~~

Represents a spatial location with state attention dynamics.

.. code-block:: python

   class Territory(BaseModel):
       id: str = Field(pattern=r"^T[0-9]{3}$")
       name: str
       sector_type: SectorType
       territory_type: TerritoryType = "core"
       host_id: str | None = None
       occupant_id: str | None = None
       profile: OperationalProfile = "low_profile"
       heat: Intensity = 0.0
       rent_level: Currency = 1.0
       population: int = 0
       under_eviction: bool = False

**Enums:**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - SectorType
     - Values
   * - ``INDUSTRIAL``
     - Factory/manufacturing sector
   * - ``RESIDENTIAL``
     - Housing/living areas
   * - ``COMMERCIAL``
     - Business/retail sector
   * - ``UNIVERSITY``
     - Educational institutions
   * - ``DOCKS``
     - Port/shipping sector
   * - ``GOVERNMENT``
     - State administrative sector

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - TerritoryType
     - Values
   * - ``CORE``
     - Imperial core territory
   * - ``PERIPHERY``
     - Exploited peripheral territory
   * - ``RESERVATION``
     - Indigenous containment zone
   * - ``PENAL_COLONY``
     - Carceral territory
   * - ``CONCENTRATION_CAMP``
     - Extreme detention territory

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - OperationalProfile
     - Values
   * - ``HIGH_PROFILE``
     - Visible activity, generates heat
   * - ``LOW_PROFILE``
     - Covert activity, heat decays naturally

Relationship
~~~~~~~~~~~~

Represents an edge in the topology graph.

.. code-block:: python

   class Relationship(BaseModel):
       source: str
       target: str
       edge_type: EdgeType
       weight: float = 1.0

Graph Structure
---------------

Node Types
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Type
     - ID Pattern
     - Attributes
   * - ``social_class``
     - C001, C002, ...
     - wealth, organization, ideology, consciousness
   * - ``territory``
     - T001, T002, ...
     - heat, profile, sector_type, territory_type

Edge Types
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - EdgeType
     - Direction
     - Meaning
   * - ``EXPLOITATION``
     - bourgeoisie → proletariat
     - Economic extraction relationship
   * - ``SOLIDARITY``
     - bidirectional
     - Class consciousness connection
   * - ``WAGES``
     - employer → worker
     - Labor-wage payment flow
   * - ``TRIBUTE``
     - periphery → core
     - Imperial value transfer
   * - ``TENANCY``
     - class → territory
     - Spatial occupation
   * - ``ADJACENCY``
     - territory → territory
     - Spatial proximity (spillover routes)

Entity Collections
------------------

The Ledger stores 16 JSON entity collections in ``src/babylon/data/game/``:

.. list-table::
   :header-rows: 1
   :widths: 35 65

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
   * - ``cultures.json``
     - Cultural identity definitions
   * - ``factions.json``
     - Political groupings with agendas
   * - ``ideologies.json``
     - Ideological positions with drift modifiers
   * - ``institutions.json``
     - State and civil society institutions
   * - ``laws.json``
     - Legal framework definitions
   * - ``movements.json``
     - Social movement definitions
   * - ``policies.json``
     - Government policy definitions
   * - ``resources.json``
     - Raw materials for production
   * - ``revolts.json``
     - Uprising condition definitions
   * - ``sentiments.json``
     - Public sentiment data
   * - ``technologies.json``
     - Technology definitions

State Transformation API
------------------------

Converting between Pydantic and Graph representations:

.. code-block:: python

   from babylon.models import WorldState

   # Pydantic → Graph (for computation)
   graph: nx.DiGraph = world_state.to_graph()

   # Graph operations (mutation allowed)
   engine.run_tick(graph, services, context)

   # Graph → Pydantic (for validation)
   new_state = WorldState.from_graph(graph, old_state.tick + 1)

See Also
--------

- :doc:`/concepts/architecture` - Why this architecture
- :doc:`/reference/systems` - Systems that operate on these models
- :doc:`/reference/configuration` - Configuration parameters
- :py:mod:`babylon.models` - Source code
