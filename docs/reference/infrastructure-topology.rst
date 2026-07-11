Infrastructure Topology Layer
=============================

API reference for the infrastructure topology layer (Feature 036). For
conceptual background, see :doc:`/concepts/infrastructure-topology`.

.. contents:: On this page
   :local:
   :depth: 2

Module Overview
---------------

The :py:mod:`babylon.domain.geography` package contains six submodules:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Submodule
     - Responsibility
   * - :py:mod:`~babylon.domain.geography.types`
     - 12 frozen Pydantic DTOs
   * - :py:mod:`~babylon.domain.geography.protocols`
     - 7 ``@runtime_checkable`` Protocol interfaces
   * - :py:mod:`~babylon.domain.geography.terrain`
     - ``DefaultTerrainClassifier``, ``DefaultBiocapacityStore``
   * - :py:mod:`~babylon.domain.geography.inventory`
     - ``DefaultInfrastructureInventory``
   * - :py:mod:`~babylon.domain.geography.capacity`
     - ``DefaultEdgeCapacityCalculator``
   * - :py:mod:`~babylon.domain.geography.internet`
     - ``DefaultInternetAccessManager``, ``DefaultInternetFieldOperator``
   * - :py:mod:`~babylon.domain.geography.snapping`
     - ``DefaultSpatialSnapper``
   * - :py:mod:`~babylon.domain.geography.nonlocal_edges`
     - ``generate_airport_edges()``, ``generate_shipping_edges()``

Enumerations
------------

All enumerations are ``StrEnum`` subclasses defined in
:py:mod:`babylon.models.enums`.

TerrainType
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Member
     - Value
     - Description
   * - ``LAND``
     - ``"land"``
     - Default — no dominant water or resource coverage
   * - ``WATER``
     - ``"water"``
     - Majority water coverage (lakes, rivers)
   * - ``RESOURCE``
     - ``"resource"``
     - Majority resource region coverage (ranges, deltas, wetlands)

BiocapacityType
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Member
     - Value
     - Description
   * - ``FRESHWATER``
     - ``"freshwater"``
     - Potable water extraction capacity
   * - ``FISHERY``
     - ``"fishery"``
     - Marine/lacustrine food production
   * - ``SHIPPING_ACCESS``
     - ``"shipping_access"``
     - Navigable waterway throughput
   * - ``MINERAL``
     - ``"mineral"``
     - Extractable mineral resources
   * - ``TIMBER``
     - ``"timber"``
     - Harvestable timber stock
   * - ``HYDROELECTRIC``
     - ``"hydroelectric"``
     - Hydroelectric generation capacity

``WATER`` hexes initialize ``FRESHWATER``, ``FISHERY``, ``SHIPPING_ACCESS``.
``RESOURCE`` hexes initialize ``MINERAL``, ``TIMBER``, ``HYDROELECTRIC``.

InfrastructureType
~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Member
     - Value
     - Description
   * - ``HIGHWAY``
     - ``"highway"``
     - Major highway / interstate (high FREIGHT + COMMUTER)
   * - ``ARTERIAL``
     - ``"arterial"``
     - Secondary highway (moderate FREIGHT + COMMUTER)
   * - ``LOCAL_ROAD``
     - ``"local_road"``
     - Local / county road (low capacity, commuter-focused)
   * - ``RAIL``
     - ``"rail"``
     - Railroad line (high FREIGHT, low COMMUTER)
   * - ``PIPELINE``
     - ``"pipeline"``
     - Energy pipeline (ENERGY only)
   * - ``TRANSMISSION``
     - ``"transmission"``
     - Power transmission line (ENERGY only)
   * - ``SHIPPING_LANE``
     - ``"shipping_lane"``
     - Navigable waterway or sea lane (FREIGHT only)
   * - ``AIR_LINK``
     - ``"air_link"``
     - Air route between airports (all categories, nonlocal)

FlowCategory
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Member
     - Value
     - Description
   * - ``FREIGHT``
     - ``"freight"``
     - Physical goods movement
   * - ``COMMUTER``
     - ``"commuter"``
     - Human movement (labor, consumption)
   * - ``VALUE``
     - ``"value"``
     - Financial/value flow
   * - ``ENERGY``
     - ``"energy"``
     - Energy transmission
   * - ``CONSCIOUSNESS``
     - ``"consciousness"``
     - Ideology/information diffusion

JunctionType
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Member
     - Value
     - Description
   * - ``INTERCHANGE``
     - ``"interchange"``
     - Highway interchange (roads intersection)
   * - ``SUBSTATION``
     - ``"substation"``
     - Power substation (energy distribution)
   * - ``RAIL_JUNCTION``
     - ``"rail_junction"``
     - Railroad junction (freight routing)
   * - ``PORT``
     - ``"port"``
     - Seaport or river port (shipping + freight)
   * - ``AIRPORT``
     - ``"airport"``
     - Airport terminal (air link generation)

LocalityClass
~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Member
     - Value
     - Description
   * - ``LOCAL``
     - ``"local"``
     - Within 3 hex diameters (adjacent-equivalent)
   * - ``SEMI_LOCAL``
     - ``"semi_local"``
     - 3--20 hex diameters (regional)
   * - ``NONLOCAL``
     - ``"nonlocal"``
     - 20+ hex diameters (transcontinental)

Ratio = ``distance_km / avg_hex_diameter_km``.

InternetResponseMode
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Member
     - Value
     - Description
   * - ``PERMIT``
     - ``"permit"``
     - Full throughput, full surveillance
   * - ``THROTTLE``
     - ``"throttle"``
     - Reduced throughput, maintained surveillance, covert
   * - ``SEVER``
     - ``"sever"``
     - Zero throughput, zero surveillance, overt with backfire

Data Types
----------

All data types are frozen Pydantic ``BaseModel`` subclasses defined in
:py:mod:`babylon.domain.geography.types`.

TerrainClassification
~~~~~~~~~~~~~~~~~~~~~

Terrain classification result for a single hex.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   * - Field
     - Type
     - Constraints
     - Description
   * - ``h3_index``
     - ``str``
     -
     - H3 cell identifier
   * - ``terrain_type``
     - ``str``
     -
     - ``LAND``, ``WATER``, or ``RESOURCE``
   * - ``water_coverage_fraction``
     - ``float``
     - [0.0, 1.0]
     - Fraction of hex area covered by water polygons
   * - ``resource_coverage_fraction``
     - ``float``
     - [0.0, 1.0]
     - Fraction of hex area covered by resource region polygons
   * - ``source_features``
     - ``list[str]``
     -
     - NE feature names contributing to classification

BiocapacityStockState
~~~~~~~~~~~~~~~~~~~~~

Current state of a biocapacity stock on a non-``LAND`` hex.

.. list-table::
   :header-rows: 1
   :widths: 28 15 15 42

   * - Field
     - Type
     - Constraints
     - Description
   * - ``h3_index``
     - ``str``
     -
     - H3 cell identifier
   * - ``stock_type``
     - ``str``
     -
     - BiocapacityType value
   * - ``initial_value``
     - ``float``
     - >= 0.0
     - Stock at initialization
   * - ``current_value``
     - ``float``
     - >= 0.0
     - Current stock level
   * - ``depletion_history``
     - ``list[float]``
     -
     - Extraction amounts per tick
   * - ``depleted``
     - ``bool``
     -
     - ``True`` when ``current_value == 0.0``

ExtractionResult
~~~~~~~~~~~~~~~~

Result of biocapacity extraction through an edge.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   * - Field
     - Type
     - Constraints
     - Description
   * - ``source_h3``
     - ``str``
     -
     - Resource hex (WATER/RESOURCE)
   * - ``target_h3``
     - ``str``
     -
     - Extracting LAND hex
   * - ``stock_type``
     - ``str``
     -
     - BiocapacityType value
   * - ``amount_extracted``
     - ``float``
     - >= 0.0
     - Units extracted this tick
   * - ``remaining_stock``
     - ``float``
     - >= 0.0
     - Stock after extraction
   * - ``infrastructure_constraint``
     - ``float``
     - >= 0.0
     - Max extraction allowed by edge infrastructure

InfrastructureLinkState
~~~~~~~~~~~~~~~~~~~~~~~

State of a single infrastructure link on an edge or vertex.

.. list-table::
   :header-rows: 1
   :widths: 25 20 15 40

   * - Field
     - Type
     - Constraints
     - Description
   * - ``link_id``
     - ``str``
     -
     - Unique identifier for this link
   * - ``infra_type``
     - ``str``
     -
     - InfrastructureType value
   * - ``capacity``
     - ``dict[str, float]``
     -
     - Capacity per FlowCategory
   * - ``condition``
     - ``float``
     - [0.0, 1.0]
     - Health scalar (0.0 = destroyed, 1.0 = pristine)
   * - ``owner_org_id``
     - ``str | None``
     -
     - Owning organization node ID
   * - ``ne_source_id``
     - ``str | None``
     -
     - Natural Earth feature ID for provenance

Method: ``effective_capacity(category: str) -> float`` returns
``capacity.get(category, 0.0) * condition``.

EdgeCapacityResult
~~~~~~~~~~~~~~~~~~

Aggregate capacity computation result for an edge.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``source_h3``
     - ``str``
     - Source hex H3 index
   * - ``target_h3``
     - ``str``
     - Target hex H3 index
   * - ``aggregate_capacity``
     - ``dict[str, float]``
     - Sum of effective link capacities per FlowCategory
   * - ``natural_capacity``
     - ``dict[str, float]``
     - Minimal natural capacity for LAND-LAND edges (COMMUTER, CONSCIOUSNESS)
   * - ``total_capacity``
     - ``dict[str, float]``
     - ``aggregate + natural`` per FlowCategory, used as edge weight

JunctionState
~~~~~~~~~~~~~

State of junction infrastructure at a vertex.

.. list-table::
   :header-rows: 1
   :widths: 28 20 15 37

   * - Field
     - Type
     - Constraints
     - Description
   * - ``junction_type``
     - ``str``
     -
     - JunctionType value
   * - ``capacity_contribution``
     - ``float``
     - >= 0.0
     - Capacity added to adjacent edges
   * - ``condition``
     - ``float``
     - [0.0, 1.0]
     - Health/degradation scalar
   * - ``owner_org_id``
     - ``str | None``
     -
     - Owning organization node ID
   * - ``ne_source_id``
     - ``str | None``
     -
     - Natural Earth feature ID for provenance

VertexState
~~~~~~~~~~~

State of a vertex (triple junction) in the hex mesh.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``vertex_id``
     - ``str``
     - Canonical ID (sorted triple hash)
   * - ``adjacent_h3``
     - ``tuple[str, str, str]``
     - Three adjacent hex H3 indices (ordered)
   * - ``lat``
     - ``float``
     - Latitude (centroid of 3 hex centroids)
   * - ``lon``
     - ``float``
     - Longitude (centroid of 3 hex centroids)
   * - ``junctions``
     - ``list[JunctionState]``
     - Junction infrastructure inventory

NonlocalEdgeState
~~~~~~~~~~~~~~~~~

State of a nonlocal edge connecting non-adjacent vertices.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Field
     - Type
     - Description
   * - ``source_vertex_id``
     - ``str``
     - Origin vertex ID
   * - ``target_vertex_id``
     - ``str``
     - Destination vertex ID
   * - ``link``
     - ``InfrastructureLinkState``
     - The infrastructure creating this edge
   * - ``distance_km``
     - ``float``
     - Great-circle distance between vertices (> 0.0)
   * - ``locality_class``
     - ``str``
     - ``LOCAL``, ``SEMI_LOCAL``, or ``NONLOCAL``
   * - ``origin_feature``
     - ``str``
     - NE feature that generated this edge

InternetAccessState
~~~~~~~~~~~~~~~~~~~

Per-hex internet connectivity state.

.. list-table::
   :header-rows: 1
   :widths: 28 15 15 42

   * - Field
     - Type
     - Constraints
     - Description
   * - ``h3_index``
     - ``str``
     -
     - H3 cell identifier
   * - ``internet_access``
     - ``bool``
     -
     - Whether broadband is available at this hex
   * - ``internet_quality``
     - ``float``
     - [0.0, 1.0]
     - Coverage quality scalar derived from FCC data
   * - ``surveillance_coupling``
     - ``float``
     - [0.0, 1.0]
     - Fraction of consciousness flow visible to the state
   * - ``response_mode``
     - ``str``
     -
     - ``PERMIT``, ``THROTTLE``, or ``SEVER``

SurveillanceResult
~~~~~~~~~~~~~~~~~~

Result of surveillance intelligence generation for a tick.

.. list-table::
   :header-rows: 1
   :widths: 28 15 15 42

   * - Field
     - Type
     - Constraints
     - Description
   * - ``h3_index``
     - ``str``
     -
     - H3 cell where surveillance occurred
   * - ``flow_magnitude``
     - ``float``
     - >= 0.0
     - Consciousness flow magnitude through this hex
   * - ``surveillance_coupling``
     - ``float``
     - [0.0, 1.0]
     - Current coupling value at this hex
   * - ``intelligence_generated``
     - ``float``
     - >= 0.0
     - Intelligence added to state observation graph
   * - ``org_ids_observed``
     - ``list[str]``
     -
     - Organization node IDs observed at this hex

OpsecResult
~~~~~~~~~~~

Result of ``COUNTER_INTEL`` action on internet surveillance coupling.

.. list-table::
   :header-rows: 1
   :widths: 28 15 15 42

   * - Field
     - Type
     - Constraints
     - Description
   * - ``h3_index``
     - ``str``
     -
     - H3 cell where OPSEC was applied
   * - ``org_id``
     - ``str``
     -
     - Organization that invested in OPSEC
   * - ``coupling_before``
     - ``float``
     - [0.0, 1.0]
     - Surveillance coupling before OPSEC
   * - ``coupling_after``
     - ``float``
     - [0.0, 1.0]
     - Surveillance coupling after OPSEC
   * - ``throughput_reduction``
     - ``float``
     - [0.0, 1.0]
     - Fraction of consciousness throughput lost

InternetResponseResult
~~~~~~~~~~~~~~~~~~~~~~

Result of state apparatus internet response mode change.

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Field
     - Type
     - Constraints
     - Description
   * - ``h3_index``
     - ``str``
     -
     - H3 cell targeted
   * - ``previous_mode``
     - ``str``
     -
     - Previous response mode
   * - ``new_mode``
     - ``str``
     -
     - New response mode
   * - ``throughput_effect``
     - ``float``
     - [0.0, 1.0]
     - Remaining throughput fraction (1.0 = full, 0.0 = severed)
   * - ``surveillance_effect``
     - ``float``
     - [0.0, 1.0]
     - Remaining surveillance fraction
   * - ``visibility``
     - ``bool``
     -
     - Whether the mode change is visible to target community
   * - ``backfire_magnitude``
     - ``float``
     - >= 0.0
     - Consciousness backfire effect (signals state fear)

Protocols
---------

All protocols are ``@runtime_checkable`` and defined in
:py:mod:`babylon.domain.geography.protocols`.

TerrainClassifier
~~~~~~~~~~~~~~~~~

Classifies hex cells by terrain type from NE geographic data.

.. py:method:: classify_hex(h3_index: str) -> TerrainClassification

   Classify a single hex by terrain type.

   :param h3_index: H3 cell identifier at resolution 7.
   :returns: ``TerrainClassification`` with terrain type and coverage fractions.

.. py:method:: classify_mesh(h3_indices: Sequence[str]) -> dict[str, TerrainClassification]

   Classify all hexes in a mesh.

   :param h3_indices: Collection of H3 cell identifiers.
   :returns: Dict mapping h3_index to ``TerrainClassification``.

BiocapacityStore
~~~~~~~~~~~~~~~~

Manages biocapacity stocks on ``WATER`` and ``RESOURCE`` hexes.

.. py:method:: initialize_stocks(classifications: dict[str, TerrainClassification]) -> dict[str, list[BiocapacityStockState]]

   Initialize biocapacity stocks for all non-``LAND`` hexes.

   :param classifications: Terrain classifications for the mesh.
   :returns: Dict mapping h3_index to list of ``BiocapacityStockState``.

.. py:method:: get_stock(h3_index: str, stock_type: str) -> BiocapacityStockState | None

   Get current stock state for a hex and type.

   :param h3_index: H3 cell identifier.
   :param stock_type: ``BiocapacityType`` value.
   :returns: Current stock state, or ``None`` if not found.

.. py:method:: extract(source_h3: str, target_h3: str, stock_type: str, infrastructure_capacity: float, depletion_rate: float) -> ExtractionResult

   Extract biocapacity from a resource hex through an edge.

   :param source_h3: Resource hex (WATER/RESOURCE).
   :param target_h3: Extracting LAND hex.
   :param stock_type: ``BiocapacityType`` value.
   :param infrastructure_capacity: Max extraction from edge infrastructure.
   :param depletion_rate: Per-tick depletion rate from ``GameDefines``.
   :returns: ``ExtractionResult`` with amount extracted and remaining stock.

InfrastructureInventory
~~~~~~~~~~~~~~~~~~~~~~~

Manages infrastructure links on edges and junctions on vertices.

.. py:method:: get_edge_links(source_h3: str, target_h3: str) -> list[InfrastructureLinkState]

   Get all infrastructure links on an edge.

.. py:method:: add_edge_link(source_h3: str, target_h3: str, link: InfrastructureLinkState) -> None

   Add an infrastructure link to an edge.

.. py:method:: degrade_link(link_id: str, condition_delta: float) -> InfrastructureLinkState

   Degrade an infrastructure link's condition.

   :param link_id: Unique identifier of the link.
   :param condition_delta: Amount to reduce condition by (positive).
   :returns: Updated link state.
   :raises KeyError: If ``link_id`` not found.

.. py:method:: get_vertex(vertex_id: str) -> VertexState | None

   Get vertex state by ID.

.. py:method:: degrade_junction(vertex_id: str, junction_type: str, condition_delta: float) -> list[tuple[str, str]]

   Degrade a junction's condition, cascading to adjacent edges.

   Cascade ratio: 50%. Each adjacent edge's links are degraded by
   ``condition_delta * 0.5``.

   :param vertex_id: Vertex containing the junction.
   :param junction_type: ``JunctionType`` value.
   :param condition_delta: Amount to reduce condition by.
   :returns: List of ``(source_h3, target_h3)`` edge pairs affected.
   :raises KeyError: If vertex or junction type not found.

.. py:method:: get_nonlocal_edges() -> list[NonlocalEdgeState]

   Get all nonlocal edges in the mesh.

EdgeCapacityCalculator
~~~~~~~~~~~~~~~~~~~~~~

Computes aggregate edge capacity from infrastructure inventory.

.. py:method:: compute_edge_capacity(source_h3: str, target_h3: str, source_terrain: str, target_terrain: str, links: Sequence[InfrastructureLinkState], population_density: float) -> EdgeCapacityResult

   Compute total capacity for an edge.

   Algorithm:

   1. Sum ``effective_capacity`` across all links per FlowCategory
   2. For LAND-LAND edges, add ``natural_capacity_coefficient`` to
      COMMUTER and CONSCIOUSNESS
   3. For WATER-WATER edges, force all capacities to zero
   4. ``total = aggregate + natural``

   :param source_h3: Source hex H3 index.
   :param target_h3: Target hex H3 index.
   :param source_terrain: ``TerrainType`` of source hex.
   :param target_terrain: ``TerrainType`` of target hex.
   :param links: Infrastructure links on this edge.
   :param population_density: Average population density of adjacent hexes.
   :returns: ``EdgeCapacityResult`` with per-category capacity breakdown.

.. py:method:: compute_mesh_weights(inventory: InfrastructureInventory, terrain_map: dict[str, str], population_map: dict[str, float], edges: Sequence[tuple[str, str]]) -> dict[tuple[str, str], dict[str, float]]

   Compute total capacity for all edges in the mesh. Only includes edges
   with nonzero total capacity.

SpatialSnapper
~~~~~~~~~~~~~~

Snaps Natural Earth features to H3 mesh edges and vertices.

.. py:method:: snap_linear_features(edges: Sequence[tuple[str, str]]) -> dict[tuple[str, str], list[InfrastructureLinkState]]

   Snap NE linear features (roads, railroads) to H3 edges.

   Algorithm:

   1. Compute mesh bounding box from all edge cells
   2. Load NE roads and railroads in the bounding box
   3. For each edge, compute shared boundary polygon
   4. Buffer boundary by ``hex_diameter * snap_buffer_fraction``
   5. Test each feature against the buffered boundary
   6. Classify road type: ``expressway=1`` or ``Major Highway`` -> HIGHWAY,
      ``Secondary Highway`` -> ARTERIAL, else LOCAL_ROAD

.. py:method:: snap_point_features(vertices: Sequence[VertexState]) -> dict[str, list[JunctionState]]

   Snap NE point features (airports, ports) to H3 vertices.

   Finds the nearest vertex within tolerance
   (``_MAX_SNAP_DISTANCE_DEG = 0.2`` degrees, ~20 km at 42N) and
   creates a ``JunctionState`` with ``capacity_contribution`` set to
   the NE feature's ``natlscale``.

InternetAccessManager
~~~~~~~~~~~~~~~~~~~~~

Manages per-hex internet access state and mutations.

.. py:method:: get_state(h3_index: str) -> InternetAccessState | None

   Get internet state for a hex.

.. py:method:: set_state(state: InternetAccessState) -> None

   Set internet state for a hex.

.. py:method:: get_all_states() -> dict[str, InternetAccessState]

   Get all internet states.

.. py:method:: initialize_from_broadband(broadband: dict[str, float], hex_to_county: dict[str, str], quality_data: dict[str, float] | None, water_hexes: set[str] | None) -> None

   Initialize internet access from FCC broadband data.

   ``broadband`` maps county FIPS to penetration fraction (``pct_25_3 / 100``).
   ``quality_data`` maps county FIPS to high-speed fraction
   (``pct_100_20 / 100``). WATER hexes forced to ``internet_access=False``
   regardless of county data.

.. py:method:: apply_opsec(h3_index: str, org_id: str, opsec_investment: float, infra_defines: InfrastructureDefines) -> OpsecResult

   Apply OPSEC to reduce surveillance coupling at a hex.

   Coupling reduction: ``opsec_investment * opsec_tradeoff_ratio``.
   Throughput reduction: ``(coupling_before - coupling_after) * opsec_tradeoff_ratio``.

   :raises KeyError: If hex not found.

.. py:method:: set_response_mode(h3_index: str, mode: str, infra_defines: InfrastructureDefines) -> InternetResponseResult

   Set state apparatus internet response mode.

   Effects by mode:

   - **PERMIT**: throughput 1.0, surveillance 1.0, not visible, no backfire
   - **THROTTLE**: throughput = ``throttle_throughput_fraction``, surveillance 1.0,
     not visible, no backfire
   - **SEVER**: throughput 0.0, surveillance 0.0, visible,
     backfire = ``surveillance_coupling + 0.1``

   :raises KeyError: If hex not found.

InternetFieldOperator
~~~~~~~~~~~~~~~~~~~~~

Manages internet consciousness field diffusion operations.

.. py:method:: get_connected_component() -> set[str]

   Get the set of internet-enabled hex indices forming the connected
   component. Includes hexes with ``internet_access=True`` and
   ``response_mode != SEVER``.

.. py:method:: propagate_consciousness(field_values: dict[str, float], diffusion_rate: float) -> dict[str, float]

   Run consciousness field diffusion on the internet-connected component.

   Mean-field approximation: each hex moves toward the component mean.

   .. math::

      f_i' = f_i + \alpha \cdot q_i \cdot \tau_i \cdot (\bar{f} - f_i)

   where :math:`\alpha` = ``diffusion_rate``, :math:`q_i` = ``internet_quality``,
   :math:`\tau_i` = throughput factor (1.0 for PERMIT,
   ``throttle_throughput_fraction`` for THROTTLE), and :math:`\bar{f}` =
   mean field value across the connected component.

   Requires at least 2 active hexes; returns unchanged values otherwise.

.. py:method:: generate_surveillance(flow_magnitudes: dict[str, float], analytical_capacity: float) -> list[SurveillanceResult]

   Generate surveillance intelligence from consciousness flow.

   .. math::

      I_i = F_i \cdot \sigma_i \cdot A

   where :math:`F_i` = flow magnitude, :math:`\sigma_i` = surveillance
   coupling, :math:`A` = analytical capacity.

Implementations
---------------

DefaultTerrainClassifier
~~~~~~~~~~~~~~~~~~~~~~~~

:py:mod:`babylon.domain.geography.terrain`

**Constructor**:
``DefaultTerrainClassifier(reader, defines)``

:param reader: ``NaturalEarthReader``
:param defines: ``InfraTerrainDefines``

Classifies H3 hexes by spatial intersection with NE lake and resource
region polygons. Converts H3 ``(lat, lon)`` boundaries to Shapely
``(lon, lat)`` polygons. Coverage = ``intersection_area / hex_area``.
Classification: ``WATER`` if water coverage >= threshold, else
``RESOURCE`` if resource coverage >= threshold, else ``LAND``.

DefaultBiocapacityStore
~~~~~~~~~~~~~~~~~~~~~~~

:py:mod:`babylon.domain.geography.terrain`

**Constructor**: ``DefaultBiocapacityStore(defines: InfraTerrainDefines)``

Internally mutable store tracking biocapacity stocks per hex. Returns
frozen ``BiocapacityStockState`` DTOs via protocol methods.

Extraction formula:

.. math::

   E = \min(C_{\text{infra}},\; r \cdot S,\; S)

where :math:`C_{\text{infra}}` = infrastructure capacity, :math:`r` =
depletion rate, :math:`S` = current stock.

Supports serialization via ``to_dict()`` / ``from_dict()`` for
tick-snapshot compatibility.

DefaultInfrastructureInventory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:py:mod:`babylon.domain.geography.inventory`

**Constructor**: ``DefaultInfrastructureInventory()``

Stores infrastructure links indexed by canonical edge keys
(``tuple(sorted([source, target]))``), vertices indexed by vertex ID,
and nonlocal edges in a flat list. Canonical key ordering prevents
A->B vs B->A duplication.

Junction cascade ratio: ``condition_delta * 0.5`` applied to all links
on the three edges adjacent to a degraded junction's vertex.

Supports serialization via ``to_dict()`` / ``from_dict()``.

DefaultEdgeCapacityCalculator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:py:mod:`babylon.domain.geography.capacity`

**Constructor**: ``DefaultEdgeCapacityCalculator(defines: InfrastructureDefines)``

Computes per-edge aggregate capacity. WATER-WATER edges forced to zero.
LAND-LAND edges receive natural capacity for COMMUTER and CONSCIOUSNESS.
Total = aggregate + natural.

DefaultSpatialSnapper
~~~~~~~~~~~~~~~~~~~~~

:py:mod:`babylon.domain.geography.snapping`

**Constructor**:
``DefaultSpatialSnapper(reader, defines)``

:param reader: ``NaturalEarthReader``
:param defines: ``InfrastructureDefines``

Snaps NE linear features to H3 edges via buffered shared-boundary
intersection. Road classification:

.. list-table::
   :header-rows: 1
   :widths: 40 30

   * - NE Feature Attribute
     - InfrastructureType
   * - ``expressway=1`` or ``road_type="Major Highway"``
     - HIGHWAY
   * - ``road_type="Secondary Highway"``
     - ARTERIAL
   * - All other roads
     - LOCAL_ROAD
   * - Railroads
     - RAIL

Link IDs are deterministic SHA-256 hashes of
``source_table:ogc_fid:edge_key``, truncated to 16 characters.

Point features snapped to nearest vertex within
``_MAX_SNAP_DISTANCE_DEG = 0.2`` degrees (~20 km at latitude 42N).

DefaultInternetAccessManager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:py:mod:`babylon.domain.geography.internet`

**Constructor**: ``DefaultInternetAccessManager(defines: InfraTerrainDefines)``

Stores mutable internet state per hex. Initialization from FCC broadband
data maps county penetration to per-hex access. WATER hexes always
``internet_access=False``.

DefaultInternetFieldOperator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:py:mod:`babylon.domain.geography.internet`

**Constructor**:
``DefaultInternetFieldOperator(manager, infra_defines=None)``

:param manager: ``DefaultInternetAccessManager``
:param infra_defines: ``InfrastructureDefines | None``

Operates on the connected component of internet-enabled, non-SEVER hexes.
Consciousness diffuses via mean-field approximation. Surveillance
intelligence generated proportional to flow, coupling, and analytical
capacity.

Nonlocal Edge Generators
------------------------

Two module-level functions in :py:mod:`babylon.domain.geography.nonlocal_edges`.

.. py:function:: generate_airport_edges(airport_vertices: Sequence[VertexState], all_airports: Sequence[VertexState], defines: InfrastructureDefines, avg_hex_diameter_km: float) -> list[NonlocalEdgeState]

   Generate ``AIR_LINK`` nonlocal edges between airport vertices.
   Creates edges from each airport in ``airport_vertices`` to every
   other airport in ``all_airports`` (excluding self-loops). Deduplicates
   via canonical sorted vertex ID pairs. Capacity scaled by
   ``min(source_natlscale, dest_natlscale) / 100.0``.

.. py:function:: generate_shipping_edges(port_vertices: Sequence[VertexState], defines: InfrastructureDefines, avg_hex_diameter_km: float) -> list[NonlocalEdgeState]

   Generate ``SHIPPING_LANE`` nonlocal edges between all pairs of port
   vertices. Capacity scaled by ``min(source_natlscale, dest_natlscale) / 100.0``.

Configuration
-------------

InfraTerrainDefines
~~~~~~~~~~~~~~~~~~~

:py:class:`babylon.config.defines.InfraTerrainDefines` — terrain classification
and biocapacity coefficients.

.. list-table::
   :header-rows: 1
   :widths: 30 10 10 50

   * - Parameter
     - Type
     - Default
     - Description
   * - ``majority_coverage_threshold``
     - ``float``
     - 0.5
     - Coverage fraction for WATER/RESOURCE classification
   * - ``initial_freshwater``
     - ``float``
     - 100.0
     - Initial FRESHWATER stock for WATER hexes
   * - ``initial_fishery``
     - ``float``
     - 80.0
     - Initial FISHERY stock for WATER hexes
   * - ``initial_shipping_access``
     - ``float``
     - 50.0
     - Initial SHIPPING_ACCESS stock for WATER hexes
   * - ``initial_mineral``
     - ``float``
     - 120.0
     - Initial MINERAL stock for RESOURCE hexes
   * - ``initial_timber``
     - ``float``
     - 90.0
     - Initial TIMBER stock for RESOURCE hexes
   * - ``initial_hydroelectric``
     - ``float``
     - 60.0
     - Initial HYDROELECTRIC stock for RESOURCE hexes
   * - ``depletion_freshwater``
     - ``float``
     - 0.05
     - Per-tick depletion rate for FRESHWATER
   * - ``depletion_fishery``
     - ``float``
     - 0.04
     - Per-tick depletion rate for FISHERY
   * - ``depletion_shipping_access``
     - ``float``
     - 0.02
     - Per-tick depletion rate for SHIPPING_ACCESS
   * - ``depletion_mineral``
     - ``float``
     - 0.03
     - Per-tick depletion rate for MINERAL
   * - ``depletion_timber``
     - ``float``
     - 0.04
     - Per-tick depletion rate for TIMBER
   * - ``depletion_hydroelectric``
     - ``float``
     - 0.01
     - Per-tick depletion rate for HYDROELECTRIC
   * - ``internet_access_threshold``
     - ``float``
     - 0.5
     - Min FCC broadband penetration for internet_access=True
   * - ``default_surveillance_coupling``
     - ``float``
     - 0.3
     - Default surveillance coupling at internet-connected hexes

Methods:

- ``get_initial_stock(stock_type: str) -> float``
- ``get_depletion_rate(stock_type: str) -> float``

InfrastructureDefines
~~~~~~~~~~~~~~~~~~~~~

:py:class:`babylon.config.defines.InfrastructureDefines` — infrastructure
capacity and internet operation coefficients.

**Per-type base capacity coefficients** (``{infra_type}_{flow_category}``):

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15 15 20

   * - Type
     - FREIGHT
     - COMMUTER
     - VALUE
     - ENERGY
     - CONSCIOUSNESS
   * - HIGHWAY
     - 1.0
     - 1.0
     - 0.5
     - --
     - 0.3
   * - ARTERIAL
     - 0.6
     - 0.7
     - 0.3
     - --
     - 0.2
   * - LOCAL_ROAD
     - 0.2
     - 0.4
     - 0.1
     - --
     - 0.3
   * - RAIL
     - 1.2
     - 0.3
     - 0.2
     - --
     - 0.1
   * - PIPELINE
     - --
     - --
     - --
     - 1.5
     - --
   * - TRANSMISSION
     - --
     - --
     - --
     - 1.0
     - --
   * - SHIPPING_LANE
     - 1.5
     - --
     - --
     - --
     - --
   * - AIR_LINK
     - 0.3
     - 0.8
     - 0.5
     - --
     - 0.5

``--`` indicates zero capacity (parameter not defined for that combination).

**Other parameters**:

.. list-table::
   :header-rows: 1
   :widths: 35 10 10 45

   * - Parameter
     - Type
     - Default
     - Description
   * - ``natural_capacity_coefficient``
     - ``float``
     - 0.1
     - Base natural capacity for LAND-LAND edges (COMMUTER, CONSCIOUSNESS)
   * - ``minimum_capacity_threshold``
     - ``float``
     - 0.01
     - Edge capacity below which flow is zero
   * - ``opsec_tradeoff_ratio``
     - ``float``
     - 0.5
     - Surveillance coupling reduction per unit of OPSEC investment
   * - ``throttle_throughput_fraction``
     - ``float``
     - 0.3
     - Consciousness throughput under THROTTLE response mode
   * - ``snap_buffer_fraction``
     - ``float``
     - 0.3
     - Buffer around shared boundary as fraction of hex diameter
   * - ``local_ratio_threshold``
     - ``float``
     - 3.0
     - Distance/hex ratio below which nonlocal edge is LOCAL
   * - ``semi_local_ratio_threshold``
     - ``float``
     - 20.0
     - Distance/hex ratio below which nonlocal edge is SEMI_LOCAL

Method: ``get_capacity(infra_type: str, flow_category: str) -> float``
returns the capacity value via attribute lookup on
``{infra_type}_{flow_category}``, or 0.0 if not defined.

Key Algorithms
--------------

Terrain Classification
~~~~~~~~~~~~~~~~~~~~~~

1. Convert H3 cell boundary to Shapely polygon (``(lat, lon)`` -> ``(lon, lat)``)
2. Intersect with NE lakes -> compute ``water_coverage = sum(intersection_area) / hex_area``
3. Intersect with NE resource regions -> compute ``resource_coverage``
4. Clamp both to [0.0, 1.0]
5. If ``water_coverage >= majority_coverage_threshold``: ``WATER``
6. Else if ``resource_coverage >= majority_coverage_threshold``: ``RESOURCE``
7. Else: ``LAND``

Edge Capacity Aggregation
~~~~~~~~~~~~~~~~~~~~~~~~~

For each edge ``(source, target)``:

.. math::

   C_{\text{total}}^{(k)} = \underbrace{\sum_{l \in \text{links}} c_l^{(k)} \cdot d_l}_{\text{aggregate}} + \underbrace{n^{(k)}}_{\text{natural}}

where :math:`k` is the flow category, :math:`c_l^{(k)}` is link :math:`l`'s
capacity for category :math:`k`, :math:`d_l` is the link's condition, and
:math:`n^{(k)}` is the natural capacity (nonzero only for LAND-LAND edges
and only for COMMUTER and CONSCIOUSNESS categories).

WATER-WATER edges: all capacities forced to zero.

Mean-Field Consciousness Diffusion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. math::

   f_i' = f_i + \alpha \cdot q_i \cdot \tau_i \cdot (\bar{f} - f_i)

- :math:`\alpha`: base ``diffusion_rate``
- :math:`q_i`: ``internet_quality`` at hex :math:`i`
- :math:`\tau_i`: 1.0 if PERMIT, ``throttle_throughput_fraction`` if THROTTLE
- :math:`\bar{f}`: mean field value across connected component

Computed only when ``|active| >= 2``.

Surveillance Intelligence
~~~~~~~~~~~~~~~~~~~~~~~~~

.. math::

   I_i = F_i \cdot \sigma_i \cdot A

- :math:`F_i`: consciousness flow magnitude at hex :math:`i`
- :math:`\sigma_i`: surveillance coupling
- :math:`A`: state analytical capacity [0.0, 1.0]

OPSEC Coupling Reduction
~~~~~~~~~~~~~~~~~~~~~~~~~

.. math::

   \sigma' = \max(0,\; \sigma - \omega \cdot \rho)

.. math::

   \Delta\tau = (\sigma - \sigma') \cdot \rho

where :math:`\omega` is ``opsec_investment``, :math:`\rho` is
``opsec_tradeoff_ratio``, and :math:`\Delta\tau` is the consciousness
throughput reduction incurred.

Haversine Distance
~~~~~~~~~~~~~~~~~~

.. math::

   d = 2R \cdot \arctan2\!\left(\sqrt{a},\; \sqrt{1 - a}\right)

.. math::

   a = \sin^2\!\left(\frac{\Delta\phi}{2}\right) + \cos\phi_1 \cdot \cos\phi_2 \cdot \sin^2\!\left(\frac{\Delta\lambda}{2}\right)

where :math:`R = 6371` km (WGS-84 mean radius), :math:`\phi` = latitude
in radians, :math:`\lambda` = longitude in radians.

Locality Classification
~~~~~~~~~~~~~~~~~~~~~~~~

.. math::

   \text{ratio} = d / d_{\text{hex}}

- ``ratio < 3.0``: LOCAL
- ``ratio < 20.0``: SEMI_LOCAL
- ``ratio >= 20.0``: NONLOCAL
