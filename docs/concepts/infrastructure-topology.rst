Material Geography: Infrastructure as Historical Force
======================================================

The infrastructure topology layer (Feature 036) models the material geography
that constrains all economic, military, and ideological flows in the simulation.
Terrain is not a backdrop — it is the substrate on which class struggle unfolds.
Roads, railroads, ports, and internet cables are not neutral conduits; they are
instruments of accumulation whose capacity ceilings determine what flows are
possible and whose degradation determines when those flows collapse.

This document explains *why* the infrastructure layer exists, *how* it fits
with the existing topology, and *what* political economy it encodes.

.. contents:: On this page
   :local:
   :depth: 2

Why Material Geography Matters
------------------------------

The simulation's fundamental theorem asserts that revolution in the core is
impossible when wages exceed value produced. But the *rate* at which imperial
rent extracts value depends on the physical infrastructure connecting core
and periphery. A highway carries freight; a railroad carries different
freight at different volumes; an airport collapses distance. The
:doc:`dialectical-field-theory` computes contradiction fields on the graph,
but the *edge weights* of that graph — the capacity of each connection —
are determined by what physical infrastructure exists on each edge.

Without an infrastructure layer, all edges in the simulation carry equal
weight. This is a political fiction: the material conditions of the Great
Lakes Rust Belt are not the same as suburban Atlanta, and pretending they
are flattens the very spatial inequality that drives the simulation's
dynamics. Infrastructure capacity creates *chokepoints* where
contradictions concentrate, *corridors* where consciousness diffuses
rapidly, and *dead zones* where isolation breeds atomization.

The infrastructure layer grounds the abstract topology in geography.

Terrain as Substrate
--------------------

Every H3 resolution-7 hex in the simulation mesh receives a terrain
classification: ``LAND``, ``WATER``, or ``RESOURCE``. These are not
arbitrary labels — they are computed by spatial intersection of the hex
boundary polygon with Natural Earth geographic features.

The algorithm converts each H3 cell boundary to a Shapely polygon (swapping
H3's ``(lat, lon)`` to Shapely's ``(lon, lat)`` convention), then intersects
it with NE lake polygons and resource region polygons. Coverage is the ratio
of intersection area to hex area. If water coverage exceeds the majority
threshold (default 0.5), the hex is ``WATER``. Otherwise, if resource
coverage exceeds the threshold, it is ``RESOURCE``. The remainder is
``LAND``.

**Why hexagons?** H3's hexagonal mesh has uniform adjacency — every hex
borders exactly six neighbors (ignoring pentagons at icosahedron vertices),
and every neighbor is equidistant. This eliminates the directional bias of
square grids, where diagonal neighbors are :math:`\sqrt{2}` farther than
cardinal neighbors. For a simulation where solidarity transmission and
consciousness diffusion depend on neighbor distance, uniform adjacency is
not a convenience — it is a requirement for unbiased field operations.

**Why majority threshold?** A hex straddling a lake shore could be 40%
water. The majority coverage threshold (configurable via
:py:class:`~babylon.config.defines.InfraTerrainDefines`) determines when
a hex *becomes* water rather than land with some water. The default 0.5
means a hex is what covers more than half its area — a simple, defensible
heuristic that avoids over-classifying shoreline hexes.

Biocapacity and Ecological Limits
---------------------------------

Non-``LAND`` hexes carry biocapacity stocks — renewable resources that
can be extracted but deplete over time. This connects the infrastructure
layer to the simulation's metabolic rift mechanics.

``WATER`` hexes initialize three stock types: ``FRESHWATER`` (potable
water), ``FISHERY`` (lacustrine food production), and ``SHIPPING_ACCESS``
(navigable waterway throughput). ``RESOURCE`` hexes initialize
``MINERAL``, ``TIMBER``, and ``HYDROELECTRIC``. Initial values and
per-tick depletion rates are configured in
:py:class:`~babylon.config.defines.InfraTerrainDefines`.

Extraction through an edge is bounded by the *minimum* of three
constraints:

.. math::

   E = \min(C_{\text{infra}},\; r \cdot S_{\text{current}},\; S_{\text{current}})

where :math:`C_{\text{infra}}` is the edge's infrastructure capacity for
``RESOURCE_EXTRACTION``, :math:`r` is the per-tick depletion rate, and
:math:`S_{\text{current}}` is the remaining stock. Infrastructure capacity
acts as a *ceiling* on extraction — you cannot extract what you cannot
transport. The depletion rate acts as a *sustainable yield* bound. And
the stock itself acts as the absolute limit.

This triple-bounded extraction is the mechanism through which ecological
overshoot enters the simulation. When infrastructure capacity exceeds
sustainable yield, extraction depletes the stock faster than it
regenerates. When the stock reaches zero, the hex is marked
``depleted`` and no further extraction occurs — a permanent loss that
no amount of infrastructure investment can reverse.

.. seealso::

   :doc:`/concepts/economics-pipeline-theory` for how biocapacity connects
   to the broader economics pipeline, and :py:func:`babylon.formulas.metabolic.calculate_biocapacity_delta`
   for the metabolic rift formula.

Infrastructure as Capacity Constraint
-------------------------------------

Physical infrastructure lives on the edges and vertices of the H3 mesh.
Each infrastructure *link* — a highway segment, a railroad section, a
pipeline — is a typed object placed on an edge between two adjacent hexes.
Links have a type (one of eight
:py:class:`~babylon.models.enums.InfrastructureType` values), per-category
capacity values, a condition scalar, and optional ownership.

**Typed capacity** means that a highway carries freight and commuters but
not energy, while a transmission line carries energy but not people. The
five :py:class:`~babylon.models.enums.FlowCategory` values — ``FREIGHT``,
``COMMUTER``, ``VALUE``, ``ENERGY``, ``CONSCIOUSNESS`` — partition the
flow space. Each link declares its capacity per category, and the edge's
total capacity is the sum across all links.

**Condition** is a health scalar in ``[0.0, 1.0]``. A pristine highway
operates at full rated capacity; a degraded one (condition 0.5) operates
at half capacity. Effective capacity per category is
:math:`\text{capacity} \times \text{condition}`. Degradation models
neglect, sabotage, natural disaster, or deliberate state destruction of
infrastructure.

**Natural capacity** exists for ``LAND``-``LAND`` edges even without any
infrastructure links. People walk. Ideas spread through conversation.
The ``natural_capacity_coefficient`` in
:py:class:`~babylon.config.defines.InfrastructureDefines` provides
baseline ``COMMUTER`` and ``CONSCIOUSNESS`` capacity on land edges.
``WATER``-``WATER`` edges have zero capacity — you cannot walk across
a lake.

The total edge capacity becomes the edge weight in the simulation's
weighted Laplacian, directly controlling how much flow each connection
can carry.

Vertices and Junction Cascade
-----------------------------

Vertices sit at the triple-points where three hexes meet. In the H3
mesh, each vertex is the shared corner of exactly three cells. The
simulation identifies vertices by the canonical sorted triple of
adjacent hex indices, and positions them at the centroid of the three
hex centers.

Vertices host *junction* infrastructure: airports, ports, highway
interchanges, rail junctions, and power substations. Junctions are
qualitatively different from edge links — they are point features
that serve all three adjacent edges simultaneously.

When a junction degrades, the damage *cascades* to all three adjacent
edges. This models the real-world dynamics of hub failure: when a port
is damaged, all shipping routes through that port suffer. The cascade
ratio (currently 50%) means that degrading a junction's condition by
0.2 degrades each adjacent edge's links by 0.1.

This cascade mechanic creates *vulnerability concentrations* at junction
vertices. A territory with a single critical port or airport is fragile
in a way that a territory with distributed local roads is not. The
topology of vulnerability is itself a political fact — it determines
where sabotage is most effective and where state investment in
protection is most concentrated.

Nonlocal Edges
--------------

The H3 mesh constrains adjacency to immediate neighbors. But airports
connect Detroit to Atlanta in two hours, collapsing the geographical
distance that would otherwise require traversing dozens of hexes. Shipping
lanes connect Great Lakes ports across water that has zero capacity for
land-based movement.

Nonlocal edges model these distance-collapsing connections. They are
generated by pairing vertices that host matching junction types — airport
vertices connect to other airport vertices via ``AIR_LINK``, port
vertices connect to other port vertices via ``SHIPPING_LANE``. Distance
is computed via the Haversine formula (great-circle distance on a sphere),
and each edge is classified by its locality: ``LOCAL`` (within 3 hex
diameters), ``SEMI_LOCAL`` (3-20 hex diameters), or ``NONLOCAL``
(20+ hex diameters).

Nonlocal edges matter for two dynamics. First, consciousness diffusion:
an organizer who flies from Detroit to Atlanta carries ideas across a
gap that local solidarity transmission cannot bridge. Nonlocal edges
with ``CONSCIOUSNESS`` capacity create shortcuts in the consciousness
field, enabling coordination between distant movements. Second, freight:
nonlocal shipping and air cargo enable imperial rent extraction from
distant peripheries, sustaining the core's consumption beyond what
local production supports.

Capacity on nonlocal edges scales by the minimum ``natlscale`` (Natural
Earth scale attribute) of both endpoints — a small regional airport
connecting to O'Hare is bottlenecked by the regional airport's capacity,
not O'Hare's.

The Internet Dialectic
----------------------

The internet is the most politically charged infrastructure in the
simulation because it simultaneously serves two antagonistic functions:
it *accelerates consciousness diffusion* and *enables state surveillance*.
This is not a simplification — it is the central contradiction of
digital communication under capitalism.

**Access and quality.** Per-hex internet access is initialized from FCC
broadband coverage data, mapped through county-to-hex spatial assignment.
Hexes with broadband penetration above the access threshold (default 50%)
receive ``internet_access=True``. Quality reflects the fraction of
high-speed connections. ``WATER`` hexes receive no internet access
regardless of county data — there is no broadband infrastructure in
the middle of a lake.

**Consciousness diffusion.** Internet-enabled hexes form a *connected
component* — the set of hexes with access and without a ``SEVER`` response
mode. Consciousness diffuses across this component via a mean-field
approximation: each hex moves toward the component mean at a rate
proportional to ``diffusion_rate * quality * throughput_factor``.

.. math::

   f_i' = f_i + \alpha \cdot q_i \cdot \tau_i \cdot (\bar{f} - f_i)

where :math:`f_i` is the consciousness field value at hex :math:`i`,
:math:`\alpha` is the base diffusion rate, :math:`q_i` is internet
quality, :math:`\tau_i` is the throughput factor (1.0 for ``PERMIT``,
reduced for ``THROTTLE``), and :math:`\bar{f}` is the mean field
value across the connected component.

This mean-field approach is computationally cheaper than full graph
diffusion and captures the essential dynamics: the internet flattens
local consciousness gradients, pulling isolated communities toward the
national discourse and pulling radicalized communities toward the mean.

**Surveillance.** The same connections that carry consciousness also
carry data visible to the state apparatus. Each hex has a
``surveillance_coupling`` — the fraction of consciousness flow that
generates intelligence for the state. Surveillance intelligence at
each hex is:

.. math::

   I_i = F_i \cdot \sigma_i \cdot A

where :math:`F_i` is consciousness flow magnitude, :math:`\sigma_i`
is surveillance coupling, and :math:`A` is the state's analytical
capacity. Higher surveillance coupling means the state sees more of
what flows through that hex.

**OPSEC tradeoff.** Organizations can invest in operational security
(``COUNTER_INTEL`` actions) to reduce surveillance coupling at a hex.
But OPSEC comes at a cost: reducing surveillance coupling also reduces
consciousness throughput. Encrypted communications are harder for the
state to read, but they are also harder for potential sympathizers to
encounter. The ``opsec_tradeoff_ratio`` controls this coupling — a
ratio of 0.5 means that every unit of surveillance reduction costs
0.5 units of consciousness throughput.

This is the fundamental dilemma of underground organization: perfect
security means perfect isolation.

**State response modes.** The state apparatus can set three internet
response modes per hex:

- **PERMIT** (default): Full consciousness throughput, full surveillance.
  The state sees everything but interferes with nothing.
- **THROTTLE**: Reduced throughput (default 30%), maintained surveillance.
  Covert — the target community cannot detect throttling. The state
  slows consciousness diffusion without losing its intelligence stream.
- **SEVER**: Zero throughput, zero surveillance. The hex is disconnected
  from the internet component. This is *overt* — the target community
  knows the internet has been cut. Severing generates a
  ``backfire_magnitude`` proportional to the hex's surveillance coupling,
  representing the consciousness boost that occurs when people realize
  the state fears their communication enough to silence it.

The SEVER backfire mechanic encodes a historical pattern: internet
shutdowns during the Arab Spring, Indian farmer protests, and Myanmar
coup all *increased* political consciousness rather than suppressing it.
The state pays for blunt repression with accelerated radicalization.

Integration with Field Topology
-------------------------------

The infrastructure layer does not operate in isolation. Its primary
integration point is the weighted Laplacian used by the
:doc:`dialectical-field-theory` system.

The graph Laplacian of a contradiction field computes how much each
node's field value differs from its neighbors — a spatial gradient
that identifies pressure peaks and troughs. In the *unweighted*
Laplacian, all edges contribute equally. The infrastructure layer
replaces this with a *weighted* Laplacian where edge weights are
total capacity values.

This has precise political meaning. The Laplacian of the exploitation
field at a node tells us whether contradiction is concentrated here
relative to neighbors. When infrastructure capacity is high between
two nodes, their contradiction values are tightly coupled — a crisis
in one quickly propagates to the other. When capacity is low (degraded
infrastructure, geographic isolation), the nodes are decoupled — crises
remain local.

The Ollivier-Ricci curvature computation similarly uses weighted
probability measures derived from infrastructure capacity. Positive
curvature (well-connected regions) means contradiction diffuses
quickly. Negative curvature (bottleneck regions) means contradiction
concentrates. Infrastructure-poor boundaries between well-connected
regions create *steep contradiction gradients* — exactly the places
where phase transitions are most likely.

This is the deepest connection between infrastructure and revolutionary
dynamics: material geography shapes the topology of contradictions, and
the topology of contradictions determines where and when qualitative
transitions occur.

.. seealso::

   :doc:`/reference/infrastructure-topology` for complete API reference.
   :doc:`dialectical-field-theory` for the contradiction field framework.
   :doc:`topology` for percolation theory and phase transition detection.
