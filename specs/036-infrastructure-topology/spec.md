# Feature Specification: Infrastructure Topology Layer

**Feature Branch**: `036-infrastructure-topology`
**Created**: 2026-03-01
**Status**: Draft
**Depends On**: Feature 026 (Tri-County Economic Substrate), Feature 002 (Dialectical Field Topology), Feature 032 (OODA Loop System)
**Input**: Design session modeling infrastructure as typed entities on the H3 cell complex (edges and vertices), terrain classification on hex cells with biocapacity stocks, nonlocal "wormhole" edges for air/shipping connectivity, and internet as a node-level consciousness field operation with class-asymmetric surveillance properties.

## Overview

The simulation currently treats hex cells as the primary spatial objects -- containers for economic state, contradiction fields, and population. Edges between hexes exist implicitly (H3 adjacency) and carry computed quantities (field gradients, Laplacian contributions) but have no material content of their own. Vertices (triple junctions where three hexes meet) are not represented at all.

Real economic geography is not just about what occupies space -- it is about what *connects* spaces, what *obstructs* connection, and what *resources* the terrain contains. A highway carries freight between two hexes. A bridge spans a river that would otherwise sever the flow graph. An airport creates a direct link between two points that are nowhere near each other in the spatial grid. Mountains block easy transit but contain extractable mineral wealth. The Great Lakes are simultaneously obstacles to land flow, shipping corridors, and freshwater biocapacity stores that enabled Detroit's industrialization.

This feature promotes edges and vertices from implicit geometric artifacts to first-class simulation objects carrying typed infrastructure inventories. It adds terrain classification to hex cells with a three-way typology (LAND, WATER, RESOURCE) where non-LAND hexes carry biocapacity stocks subject to extraction by adjacent hexes. It introduces nonlocal edges (airports, shipping lanes) that modify the effective topology of the discretized manifold. And it models internet connectivity as a node attribute with a global consciousness field operation, where surveillance coupling is determined by who owns the local access infrastructure.

### Core Theoretical Contributions

- **Cell complex as material geography**: Hex cells carry terrain type (habitability + biocapacity), edges carry infrastructure inventory (flow capacity), vertices carry junction infrastructure (convergence points). The three geometric elements of the discretized manifold each have distinct material content.
- **Three-way terrain typology**: LAND (habitable, standard production), WATER (uninhabitable, blocks land flow, carries shipping potential + freshwater biocapacity), RESOURCE (low habitability, impedes transit, carries extractable biocapacity -- minerals, timber, hydroelectric). Terrain features are simultaneously obstacles and resource stores.
- **Biocapacity as terrain stock**: Non-LAND hexes carry extractable natural resource value that feeds into adjacent LAND hexes' production. The extraction mechanic: LAND hexes with edges touching resource-bearing terrain hexes can extract value, degrading biocapacity over time. The terrain hex is a stock, adjacent edges are extraction channels, extraction rate is constrained by infrastructure (you need a mine, a dam, a port).
- **Infrastructure-derived edge capacity**: Edge flow capacity is not a magic constant -- it is derived from the typed infrastructure inventory on that edge. An edge with I-75 and a rail line has different capacity profile than an edge with a two-lane road. Data source: Natural Earth (`ne_10m_roads`, `ne_10m_railroads`), supplemented by HIFLD where higher detail is needed.
- **Nonlocal edges as topological surgery**: Airports and shipping lanes create edges between non-adjacent hexes, modifying the graph topology that all field systems compute over. These edges have strongly negative Ollivier-Ricci curvature (bottleneck, no redundancy), which means they sustain steep gradients without diffusion -- the topological signature of imperial rent extraction.
- **Internet as node attribute, not edge**: Internet connectivity is a per-hex boolean (with quality scalar) derived from FCC broadband data. Any internet-enabled hex can participate in a global consciousness field diffusion operation each tick. This is not O(n^2) edges -- it is a field operation on the connected component of internet-enabled nodes. Surveillance coupling lives on the node (determined by ISP/platform ownership of local access), not on edges.
- **Terrain as flow graph topology**: Geographic features (lakes, mountains, rivers) manifest as modified cells and severed edges, creating holes and bottlenecks in the flow graph that infrastructure must explicitly bridge. No geology simulation -- terrain classification at initialization determines the topology.
- **Fractal decomposition**: At resolution N, an edge is a single corridor with aggregate capacity. At resolution N+1, that edge becomes a band of cells through which individual infrastructure links trace specific paths. The resolution at which a geographic feature or infrastructure element "matters" falls out of the ratio of its physical extent to the hex diameter.

## Data Source Strategy

All terrain and coarse infrastructure data derives from a single source: the **Natural Earth Vector SQLite database** (`natural_earth_vector.sqlite`, v5.1.2, public domain, maintained by NACIS). Babylon uses the 1:10m (most detailed) tables exclusively, queried by `ne_10m_*` prefix.

Natural Earth tables used:

| Table | Purpose | Spec Reference |
|-------|---------|----------------|
| `ne_10m_lakes` + `ne_10m_lakes_north_america` | WATER hex classification (Great Lakes, reservoirs) | US1, FR-001 |
| `ne_10m_rivers_lake_centerlines` + `ne_10m_rivers_north_america` | River edge identification, WATER hex classification for major rivers | US1, FR-001 |
| `ne_10m_geography_regions_polys` | RESOURCE hex classification (Range/mtn, Plateau, etc.) | US1, FR-003 |
| `ne_10m_airports` | Nonlocal edge anchor points (DTW: scalerank 3, iata DTW) | US4, FR-015 |
| `ne_10m_ports` | Nonlocal edge anchor points, PORT vertex classification (Detroit: scalerank 4) | US4, FR-016 |
| `ne_10m_roads` + `ne_10m_roads_north_america` | Edge infrastructure initialization (highway corridors; NA supplement has prefix/number for route ID e.g. I-75, I-94) | US2, FR-011 |
| `ne_10m_railroads` + `ne_10m_railroads_north_america` | Edge infrastructure initialization (rail corridors) | US2, FR-011 |

**Verified data availability** (2026-03-01 against v5.1.2 SQLite):
- Michigan interstates present in `ne_10m_roads_north_america`: I-75 (scalerank 3), I-94 (scalerank 5), I-96 (scalerank 5-6), I-275/375/475/696 (scalerank 4-6)
- Great Lakes present in `ne_10m_lakes`: Lake Erie (scalerank 0), Lake Huron (scalerank 0), Lake Michigan (scalerank 0). Lake St. Clair not found in `ne_10m_lakes` -- requires NA supplement or manual polygon.
- DTW airport present: scalerank 3 (major), iata_code DTW, natlscale 75.0
- Detroit port present: scalerank 4, natlscale 50.0. Great Lakes ports include Windsor, Rouge River, Sault Ste Marie, Saginaw, Muskegon, Gary, Waukegan, etc.
- Geography regions featurecla types include: Range/mtn, Plateau, Desert, Valley, Basin, Wetlands, Delta, Depression (southeastern Michigan is flat -- RESOURCE hexes expected to be zero or near-zero for tri-county)
- NA roads supplement provides prefix+number for route identification (e.g. prefix="I", number="75" for I-75)

This replaces the need for complex federal API integration (HIFLD GeoJSON, BTS freight APIs) for MVP. HIFLD and BTS provide higher-resolution data and remain available for future refinement -- the architecture supports upgrading data sources without changing the simulation model.

For internet coverage, the existing `FCCBroadbandLoader` (in `src/babylon/data/fcc/`) provides county-level or tract-level broadband penetration rates sufficient for MVP.

**Database Location**: `/media/user/data/babylon-data/natural-earth/packages/natural_earth_vector.sqlite`
**License**: Public domain. No restrictions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 -- Terrain Classification, Null Cells, and Biocapacity (Priority: P1)

As a simulation developer, I need each hex in the tri-county mesh classified by terrain type so that uninhabitable hexes are excluded from standard economic computation, their edges have appropriate flow restrictions, and terrain-based resource stocks are initialized for the biocapacity extraction mechanic.

**Why this priority**: Without terrain classification, the flow graph treats every hex as equivalent and every edge as traversable. Lake St. Clair and the Detroit River are not optional geography -- they define the fundamental topology of the tri-county area. Biocapacity stocks on WATER and RESOURCE hexes are the material basis for extraction mechanics that explain why Detroit industrialized where it did. This must precede infrastructure placement because infrastructure exists to *bridge* terrain-imposed gaps and *access* terrain-held resources.

**Independent Test**: Can be fully tested by generating the tri-county hex mesh, classifying terrain from Natural Earth polygons, and verifying that WATER hexes have zero population, zero production, appropriate biocapacity initialization, and that edges touching WATER hexes have zero natural land-flow capacity. Delivers correct topology and resource distribution independent of infrastructure or simulation dynamics.

**Acceptance Scenarios**:

1. **Given** the tri-county H3 resolution 7 hex mesh and Natural Earth lake polygons (`ne_10m_lakes`), **When** terrain classification runs, **Then** hexes whose area is majority-covered by water are classified as WATER.
2. **Given** Natural Earth river centerlines (`ne_10m_rivers_lake_centerlines`), **When** terrain classification runs, **Then** hexes through which major rivers pass (Detroit River, Rouge River) are classified as WATER if the river width at 10m scale dominates the hex area, or remain LAND with a river-crossing edge impedance if the river is narrower than hex scale.
3. **Given** a WATER-classified hex, **When** economic initialization runs, **Then** the hex receives zero population, zero employment, zero c/v/s, and is excluded from exploitation rate and profit rate computation.
4. **Given** a WATER hex representing part of Lake St. Clair, **When** biocapacity is initialized, **Then** the hex carries a freshwater biocapacity stock with initial value derived from the lake's area and ecological productivity estimates. The stock is typed (FRESHWATER, FISHERY, SHIPPING_ACCESS).
5. **Given** two adjacent hexes where one is WATER and one is LAND, **When** edge natural capacity is computed, **Then** the LAND-WATER edge has zero natural capacity for freight and commuter flow types, but the LAND hex MAY extract biocapacity from the WATER hex through that edge if appropriate infrastructure (PORT, INTAKE) exists.
6. **Given** the classified hex mesh, **When** the total number of WATER hexes is counted, **Then** the count is consistent with the known water area of Lake St. Clair, the Detroit River, and portions of Lake Erie within the tri-county coverage (expected: 50-150 hexes at resolution 7, validated against Natural Earth polygon area).
7. **Given** a RESOURCE-classified hex (if any exist in the tri-county area -- this is primarily a national-scale feature), **When** biocapacity is initialized, **Then** the hex carries extractable resource stocks typed by resource class (MINERAL, TIMBER, HYDROELECTRIC).

---

### User Story 2 -- Infrastructure Inventory on Edges (Priority: P1)

As a simulation developer, I need edges between hexes to carry typed infrastructure inventories derived from Natural Earth vector data so that flow capacity between hexes is determined by real infrastructure corridors, not uniform assumptions.

**Why this priority**: Infrastructure capacity is the material basis for all inter-hex flows -- value circulation (Volume II), commuter flows (LODES), freight, and consciousness propagation through physical encounter. Without typed infrastructure on edges, the simulation cannot distinguish a highway corridor from a residential boundary, and the BUILD_INFRASTRUCTURE / ATTACK_INFRASTRUCTURE actions (Feature 032) have no spatial target.

**Independent Test**: Can be tested by loading Natural Earth road and railroad data for the tri-county area, snapping linear features to the H3 edge grid, and verifying that known highway corridors (I-75, I-94, I-96) appear as entries on the correct edges. Delivers infrastructure-attributed edges independent of simulation dynamics.

**Acceptance Scenarios**:

1. **Given** Natural Earth road data (`ne_10m_roads`, `ne_10m_roads_north_america`) and the tri-county hex mesh, **When** infrastructure snapping runs, **Then** each road segment is assigned to the H3 edge(s) it crosses, with infrastructure type (HIGHWAY, ARTERIAL) derived from Natural Earth's `type`, `scalerank`, and `class` attributes.
2. **Given** Natural Earth railroad data (`ne_10m_railroads`, `ne_10m_railroads_north_america`), **When** infrastructure snapping runs, **Then** rail lines are assigned to edges with type RAIL and capacity derived from Natural Earth's classification attributes.
3. **Given** an edge with multiple infrastructure links (e.g., a highway and a rail line), **When** edge capacity is queried, **Then** the total capacity is the sum of individual link capacities by flow type (freight capacity = highway freight + rail freight; commuter capacity = highway commuter + rail commuter).
4. **Given** an edge with no infrastructure links and two adjacent LAND hexes, **When** edge capacity is queried, **Then** a minimal default natural capacity exists (foot traffic, local streets below data resolution) derived from population density of adjacent hexes -- not a magic constant.
5. **Given** the infrastructure-snapped mesh, **When** I-75's path from southern Wayne through Oakland is traced, **Then** it appears as a continuous sequence of edges with HIGHWAY infrastructure, and the corridor is identifiable in the edge data.

---

### User Story 3 -- Junction Infrastructure on Vertices (Priority: P2)

As a simulation developer, I need vertices (triple junctions where three hexes meet) to carry junction infrastructure so that interchanges, substations, and junctions have a spatial representation distinct from the hexes that surround them, enabling strategic targeting by BUILD_INFRASTRUCTURE and ATTACK_INFRASTRUCTURE actions.

**Why this priority**: Vertices are where multiple corridors converge. Destroying a vertex-sited interchange degrades three edges simultaneously, producing cascade effects that edge-only infrastructure cannot model. This enables meaningful strategic gameplay around chokepoints and critical junctions.

**Independent Test**: Can be tested by identifying H3 vertices in the tri-county mesh, snapping point infrastructure (airports, ports from Natural Earth) to nearest vertices, and verifying correct typing and adjacency.

**Acceptance Scenarios**:

1. **Given** the tri-county hex mesh, **When** vertices are enumerated, **Then** each vertex is identified by the ordered triple of H3 indices of its three adjacent hexes, and the total vertex count is consistent with Euler's formula for the mesh topology.
2. **Given** Natural Earth point infrastructure data (`ne_10m_airports`, `ne_10m_ports`), **When** junction snapping runs, **Then** each point feature within the tri-county area is assigned to the nearest vertex with infrastructure type (AIRPORT, PORT).
3. **Given** a vertex with junction infrastructure, **When** the junction is destroyed (ATTACK_INFRASTRUCTURE action), **Then** all three adjacent edges have their capacity reduced by the junction's contribution, not just one edge.
4. **Given** a vertex where Wayne, Oakland, and Macomb county hexes meet, **When** I query the vertex's adjacent counties, **Then** it returns all three counties, identifying it as a tri-county contact point.

---

### User Story 4 -- Nonlocal Edges: Airports and Shipping Lanes (Priority: P2)

As a simulation developer, I need airports and ports to generate nonlocal edges connecting distant vertices so that the simulation models long-range value transfer, the class asymmetry of nonlocal connectivity, and the topological signature of imperial rent extraction.

**Why this priority**: Without nonlocal edges, the simulation treats all connectivity as local, which cannot reproduce the actual structure of imperial value extraction (thin, high-curvature links between core and periphery). Airports are also critical to modeling the bourgeoisie's coordination capacity -- finance capital operates through nonlocal edges.

**Independent Test**: Can be tested by placing DTW (Detroit Metropolitan Airport) on a vertex, generating nonlocal edges to known destinations (O'Hare, JFK, LAX as stub external nodes), and verifying that the resulting edges have correct capacity, strongly negative Ollivier-Ricci curvature, and participate correctly in the weighted Laplacian computation.

**Acceptance Scenarios**:

1. **Given** an airport vertex (DTW from `ne_10m_airports`) and a set of destination airport vertices, **When** nonlocal edges are generated, **Then** each edge connects the two vertices directly with infrastructure type AIR_LINK and capacity derived from Natural Earth's airport classification attributes (scalerank, natlscale). Future refinement: BTS T-100 traffic data for empirical passenger/freight volumes.
2. **Given** a nonlocal air edge, **When** Ollivier-Ricci curvature is computed (Feature 002), **Then** the curvature is strongly negative (< -0.5), indicating bottleneck topology with no alternative routing.
3. **Given** a nonlocal air edge between DTW and an external stub node, **When** the weighted Laplacian is computed for a contradiction field, **Then** the external node's field value contributes to the local node's Laplacian weighted by the air edge's capacity relative to total edge capacity -- a small but nonzero coupling to distant conditions.
4. **Given** a port vertex on a WATER hex boundary, **When** nonlocal edges are generated to other Great Lakes ports (from `ne_10m_ports`), **Then** the edges are typed SHIPPING with capacity derived from port classification.
5. **Given** all nonlocal edges in the simulation, **When** edge ownership is queried, **Then** airports and shipping lanes are controlled by Business or StateApparatus organizations, never by CivilSocietyOrg or unaffiliated PoliticalFaction -- modeling the class asymmetry of nonlocal infrastructure access.

---

### User Story 5 -- Internet as Node-Level Consciousness Field (Priority: P3)

As a simulation developer, I need internet connectivity modeled as a per-hex attribute enabling participation in a global consciousness field diffusion operation, with surveillance coupling determined by local access ownership, so that digital organizing simultaneously transmits ideas and feeds state intelligence -- creating the OPSEC tradeoff central to modern revolutionary organizing.

**Why this priority**: The internet is the primary mechanism by which the proletariat could build nonlocal consciousness connectivity to match the bourgeoisie's air/financial network. But its transparency to surveillance makes it a trap as well as a tool. Modeling it as a node attribute with a field operation (rather than O(n^2) pairwise edges) is both computationally tractable and theoretically more honest -- the physical infrastructure is purely local (last-mile ISP connection), while the logical connectivity is global.

**Independent Test**: Can be tested by marking hexes as internet-enabled based on FCC broadband data, running the consciousness field diffusion operation, and verifying that (a) consciousness propagates globally among enabled hexes, (b) state intelligence on participating nodes increases proportionally to surveillance coupling, and (c) player OPSEC investment reduces coupling at the cost of throughput.

**Acceptance Scenarios**:

1. **Given** FCC broadband coverage data (from existing `FCCBroadbandLoader`), **When** internet attributes are initialized, **Then** every hex with broadband penetration above a configurable threshold has `internet_access: True` and `internet_quality: float` in [0.0, 1.0] derived from coverage rate.
2. **Given** the set of internet-enabled hexes, **When** the consciousness field diffusion operation runs during Layer 3, **Then** consciousness values propagate among all enabled hexes as a single field operation on the internet-connected component -- not as pairwise edge flows.
3. **Given** an internet-enabled hex, **When** consciousness propagates through it, **Then** the state apparatus's intelligence on organizations operating in that hex increases by an amount proportional to: `flow_magnitude * node_surveillance_coupling * state_analytical_capacity`.
4. **Given** a hex's `surveillance_coupling` attribute, **When** its value is queried, **Then** it reflects the ownership of the local access provider -- a major-ISP-served hex has high coupling (platform can be compelled to provide surveillance access); a community mesh network has low coupling. The coupling is a property of the ownership relation, not the technology.
5. **Given** a player organization investing in OPSEC (modeled as COUNTER_INTEL action targeting their own hex's internet attributes), **When** consciousness propagation runs, **Then** `surveillance_coupling` is reduced proportionally to OPSEC investment, but consciousness throughput for that organization is also reduced (encrypted channels are slower, reach fewer people).
6. **Given** the state apparatus choosing to sever a hex's internet access (ATTACK_INFRASTRUCTURE targeting the local ISP infrastructure), **Then** the hex loses `internet_access`, consciousness can no longer reach or leave that hex via the internet field operation, AND state surveillance of that hex drops to zero -- organizing returns to local physical edges. The severing is visible to all and has consciousness backfire effects (signals state fear).
7. **Given** a hex whose internet access is severed, **When** consciousness propagation runs, **Then** the hex is excluded from the internet-connected component. It can still propagate consciousness through local physical edges (face-to-face, physical media) at much lower rates.

---

### User Story 6 -- Flow System Integration (Priority: P3)

As a simulation developer, I need the Layer 0 economic metabolism and Layer 3 consequence propagation to route flows through infrastructure-capacitated edges so that the existing Volume II circulation, field gradient computation, and consciousness propagation respect the material geography of the simulation.

**Why this priority**: Infrastructure topology has no gameplay consequence unless the existing systems actually *use* it. This story wires the infrastructure layer into the simulation's core flow computations, making terrain and infrastructure matter for every tick.

**Independent Test**: Can be tested by comparing simulation outputs with and without infrastructure constraints -- identical initial conditions should produce different profit rate distributions, different contradiction field gradients, and different consciousness propagation patterns when infrastructure capacity constrains flows.

**Acceptance Scenarios**:

1. **Given** Volume II wage circulation (Feature 026), **When** commuter flows are routed through the hex mesh, **Then** flows are constrained by edge capacity -- an edge with only minimal natural capacity carries fewer commuters than an edge with HIGHWAY + RAIL infrastructure.
2. **Given** the field derivative system (Feature 002), **When** the weighted Laplacian is computed, **Then** edge weights are derived from infrastructure capacity, replacing the current unweighted assumption (Feature 002, A-002). Edges with zero capacity contribute zero to the Laplacian.
3. **Given** consciousness propagation in Layer 3, **When** consciousness spreads between adjacent hexes via physical encounter, **Then** the propagation rate is modulated by the communication-relevant infrastructure capacity of the connecting edge -- edges with higher foot traffic and transit carry consciousness faster than isolated boundaries.
4. **Given** a BUILD_INFRASTRUCTURE action (Feature 032) targeting an edge, **When** the action resolves, **Then** a new infrastructure link is added to the edge's inventory with type and capacity determined by the action parameters, and subsequent flow computations reflect the increased capacity.
5. **Given** an ATTACK_INFRASTRUCTURE action targeting a vertex, **When** the action resolves, **Then** the junction infrastructure is degraded and all three adjacent edges lose the capacity contribution from that junction, producing a cascade effect on flows through the area.
6. **Given** a LAND hex adjacent to a WATER hex with FRESHWATER biocapacity, **When** the hex has PORT or INTAKE infrastructure on the connecting edge, **Then** the LAND hex can extract biocapacity value from the WATER hex during Layer 0, increasing its own production capacity while depleting the WATER hex's biocapacity stock.

---

### Edge Cases

- **EC-001: Hex on county boundary overlapping water.** A hex whose centroid is on land but majority area is water. Resolution: classify by majority area coverage, not centroid. If exactly 50/50, classify as LAND (conservative -- allows economic activity).
- **EC-002: Infrastructure crossing water hex.** A bridge or tunnel crosses a WATER hex. Resolution: the bridge/tunnel is infrastructure on the LAND-WATER or LAND-LAND edge that spans the water obstacle. The WATER hex remains uninhabitable; the edge gains infrastructure capacity.
- **EC-003: Airport hex footprint.** DTW occupies multiple resolution 7 hexes. Resolution: the airport generates nonlocal edges from its primary vertex (nearest to terminal centroid). The hex footprint is LAND terrain with modified economic activity (airport employment, not standard production).
- **EC-004: Nonlocal edge to external node.** An air link to O'Hare connects to a node outside the tri-county simulation boundary. Resolution: external nodes are stub nodes with fixed field values (updated from external data or set as boundary conditions). They participate in the Laplacian but are not simulated internally.
- **EC-005: Natural Earth resolution vs H3 resolution mismatch.** Natural Earth 10m data may not perfectly align with H3 hex boundaries. Resolution: snapping uses spatial intersection (does the Natural Earth feature cross this edge / fall within this hex?) with configurable tolerance. Minor misalignment is acceptable -- this is a game, not a surveying tool.
- **EC-006: Infrastructure link with zero capacity.** A road exists in the data but has negligible capacity. Resolution: infrastructure links with capacity below a configurable minimum threshold are excluded during snapping. Threshold is a GameDefines coefficient.
- **EC-007: Vertex shared by WATER and LAND hexes.** A vertex at the shoreline where one hex is WATER and two are LAND. Resolution: the vertex exists and can carry PORT-type junction infrastructure. It is the natural site for harbor/marina infrastructure bridging land and water networks.
- **EC-008: Biocapacity stock initialization for unknown regions.** Natural Earth geographic region polygons may not carry explicit resource data. Resolution: stock values for identified region types (Range/mtn, Plateau, etc.) use SYNTHETIC defaults from GameDefines, flagged as synthetic per project convention. The Detroit test case relies primarily on WATER biocapacity (Great Lakes) where the stock initialization is more straightforward.
- **EC-009: Internet access in WATER hexes.** WATER hexes have no population but may have internet infrastructure (undersea cables, offshore platforms). Resolution: WATER hexes have `internet_access: False` by default. Exception only for hexes with explicit telecom infrastructure.
- **EC-010: Lake St. Clair missing from `ne_10m_lakes`.** Verified: Lake St. Clair does not appear in the `ne_10m_lakes` table by name. Resolution: check `ne_10m_lakes_north_america` supplement table. If absent there, use the H3 spatial utility to identify water hexes via the Detroit River centerline buffer or a manually defined polygon for Lake St. Clair. Document the data gap and flag as requiring verification.

## Requirements *(mandatory)*

### Functional Requirements

#### Terrain Classification and Biocapacity

- **FR-001**: System MUST classify every hex in the tri-county mesh with a terrain type from a fixed enumeration: LAND, WATER, RESOURCE. Classification derived from Natural Earth 10m physical vector data at simulation initialization.
- **FR-002**: Terrain classification MUST be static after initialization. Terrain does not change during simulation. Biocapacity stocks on terrain hexes deplete through extraction but the terrain type itself does not change (a depleted lake is still WATER).
- **FR-003**: WATER hexes MUST be identified by spatial intersection of hex polygons with Natural Earth lake polygons (`ne_10m_lakes`, `ne_10m_lakes_north_america`) and major river polygons (buffered `ne_10m_rivers_lake_centerlines`, `ne_10m_rivers_north_america`). RESOURCE hexes MUST be identified by intersection with Natural Earth geographic region polygons (`ne_10m_geography_regions_polys`) where the featurecla indicates extractable terrain (Range/mtn, Plateau, Basin, Delta, Wetlands). All remaining hexes are LAND.
- **FR-004**: WATER and RESOURCE hexes MUST have zero or minimal population, zero or minimal employment, and correspondingly zero or minimal standard economic tensor values. They are excluded from standard production/exploitation computation but remain in the H3 grid.
- **FR-005**: WATER hexes MUST carry typed biocapacity stocks initialized at simulation start. Initial stock types: FRESHWATER (industrial/municipal water supply), FISHERY (extractable food production), SHIPPING_ACCESS (enables maritime flow on adjacent edges). Stock values are derived from the water body's area and type (Great Lake vs river vs reservoir), not magic constants.
- **FR-006**: RESOURCE hexes MUST carry typed biocapacity stocks. Initial stock types: MINERAL, TIMBER, HYDROELECTRIC. Stock values are derived from geographic region attributes where available, or estimated from region type as SYNTHETIC defaults. Note: the tri-county Detroit area is flat -- RESOURCE hexes are primarily a national-scale feature. For the Detroit test case, WATER biocapacity (Great Lakes) is the relevant resource mechanic.
- **FR-007**: Biocapacity extraction MUST operate through edges connecting LAND hexes to WATER or RESOURCE hexes. Extraction rate is constrained by: (a) the infrastructure on the connecting edge (requires PORT, MINE, DAM, or equivalent), (b) a per-stock depletion rate in GameDefines, and (c) the remaining stock level. Extraction feeds into the adjacent LAND hex's production capacity (increases effective constant capital).
- **FR-008**: Biocapacity stocks MUST deplete over time when extracted. Depletion is tracked per-hex, per-stock-type, per-tick. When a stock reaches zero, extraction from that hex ceases for that stock type. Stocks do NOT regenerate in MVP (ecological regeneration is a future extension).

#### Edge Infrastructure

- **FR-009**: System MUST define an extensible set of infrastructure types. Initial types: HIGHWAY, ARTERIAL, LOCAL_ROAD, RAIL, PIPELINE, TRANSMISSION, SHIPPING_LANE, AIR_LINK. Each type declares which flow categories it serves (freight, commuter, value, energy).
- **FR-010**: Each edge in the hex mesh MUST carry a typed infrastructure inventory -- a collection of zero or more infrastructure links, each with a type and a capacity value per flow category it serves.
- **FR-011**: Infrastructure inventory MUST be initialized from Natural Earth vector data by snapping linear features to H3 edges. Roads from `ne_10m_roads` and `ne_10m_roads_north_america` are typed by Natural Earth's `type`/`scalerank`/`class` attributes. Railroads from `ne_10m_railroads` and `ne_10m_railroads_north_america` are typed as RAIL. The snapping algorithm assigns each linear segment to the edge(s) it crosses.
- **FR-012**: Edge flow capacity MUST be computed as the sum of individual infrastructure link capacities per flow category. No magic constant -- capacity derives from the infrastructure inventory. Capacity values per infrastructure type are GameDefines coefficients with provenance documented.
- **FR-013**: Edges touching a WATER hex MUST have zero natural capacity for non-maritime flow types. WATER-WATER edges MUST have zero capacity unless SHIPPING_LANE infrastructure is present. LAND-WATER edges may carry PORT infrastructure enabling biocapacity extraction.
- **FR-014**: LAND-LAND edges with an empty infrastructure inventory MUST receive a minimal natural capacity for commuter and consciousness flow types, derived from the population density of adjacent hexes (modeling foot traffic and local streets below data resolution) -- not a magic constant.

#### Vertex Infrastructure

- **FR-015**: System MUST enumerate vertices in the hex mesh, identifying each by the ordered triple of adjacent H3 indices.
- **FR-016**: Vertices MUST carry a typed junction infrastructure inventory (zero or more entries). Initial types: INTERCHANGE, SUBSTATION, RAIL_JUNCTION, PORT, AIRPORT.
- **FR-017**: Airports and ports MUST be initialized from Natural Earth point data (`ne_10m_airports`, `ne_10m_ports`) by snapping to the nearest vertex.
- **FR-018**: Degradation or destruction of vertex junction infrastructure MUST reduce the capacity of all three adjacent edges by the junction's contribution, not just one edge.

#### Nonlocal Edges

- **FR-019**: System MUST support nonlocal edges connecting non-adjacent vertices. Nonlocal edges participate in the same graph as local edges -- all field systems (Laplacian, gradient, Ricci curvature) compute over them.
- **FR-020**: Airport vertices MUST generate nonlocal edges of type AIR_LINK connecting to destination airport vertices. For MVP, capacity is derived from Natural Earth airport classification (major international > regional > local, using scalerank and natlscale). Future refinement: BTS T-100 air traffic data.
- **FR-021**: Port vertices MUST generate nonlocal edges of type SHIPPING_LANE connecting to other Great Lakes port vertices. Capacity derived from Natural Earth port classification (scalerank, natlscale).
- **FR-022**: Nonlocal edges MUST be typed as LOCAL, SEMI_LOCAL, or NONLOCAL based on the ratio of edge distance to average hex diameter. Field systems MAY treat these categories differently (e.g., separate computation passes for diffusion vs coupling).

#### Internet and Consciousness

- **FR-023**: Internet connectivity MUST be modeled as a per-hex node attribute, not as edges. Each hex carries: `internet_access: bool` (whether broadband is available), `internet_quality: float` in [0.0, 1.0] (coverage quality), and `surveillance_coupling: float` in [0.0, 1.0] (fraction of consciousness flow visible to the state).
- **FR-024**: Internet access MUST be derived from FCC broadband data (existing `FCCBroadbandLoader`). Hexes with broadband penetration above a configurable threshold in GameDefines are internet-enabled. For MVP, county-level or tract-level penetration rates from existing data are sufficient.
- **FR-025**: Internet consciousness propagation MUST be implemented as a field diffusion operation on the connected component of internet-enabled hexes during Layer 3. This is NOT pairwise edges -- it is a single computation pass that propagates consciousness values among all enabled hexes simultaneously.
- **FR-026**: `surveillance_coupling` MUST be determined by the ownership of local internet access infrastructure. Platform-mediated access (major ISP) has high default coupling. Community-owned infrastructure has low default coupling. Ownership is modeled as which Business or StateApparatus organization controls the local ISP infrastructure. Default values are SYNTHETIC, derived from political analysis of ISP market share.
- **FR-027**: Each tick that consciousness propagates through the internet field, the state apparatus's intelligence on organizations in internet-enabled hexes MUST increase by: `flow_magnitude * node_surveillance_coupling * state_analytical_capacity`. Intelligence is a node attribute on the state apparatus's observation graph.
- **FR-028**: The COUNTER_INTEL action (Feature 032), when targeting an organization's own internet presence, MUST reduce `surveillance_coupling` at the hex(es) where the organization operates, at the cost of reduced consciousness throughput for that organization. The tradeoff ratio is a GameDefines coefficient.
- **FR-029**: The state apparatus MUST have three response modes for hex internet access: PERMIT (default -- full consciousness throughput, full surveillance), THROTTLE (reduced throughput via partial ATTACK_INFRASTRUCTURE, surveillance maintained, not directly visible to target without INVESTIGATE action), SEVER (full ATTACK_INFRASTRUCTURE on local ISP -- zero throughput, zero surveillance, visible to all, consciousness backfire on target community).

#### Conservation and Integration

- **FR-030**: Infrastructure capacity MUST be used as edge weights in the weighted Laplacian computation (upgrading Feature 002 assumption A-002). Zero-capacity edges contribute zero to the Laplacian.
- **FR-031**: Volume II circulation (Feature 026) MUST respect edge capacity constraints when routing commuter and freight flows. Flows exceeding capacity are redistributed to alternative paths or queued.
- **FR-032**: All infrastructure links and biocapacity stocks MUST be persisted in tick-keyed state, enabling time-series queries and replay.
- **FR-033**: Conservation of total flow MUST be maintained when flows are constrained by edge capacity. Flow blocked by insufficient capacity is not destroyed -- it is redirected, queued, or generates a realization problem (value stuck in commodity form per Feature 023).

### Key Entities

- **TerrainType**: Enumeration of hex terrain classifications (LAND, WATER, RESOURCE). Determines habitability, default edge traversability, and biocapacity stock types. Static after initialization.
- **BiocapacityStock**: A typed, depletable resource stock on a WATER or RESOURCE hex. Types: FRESHWATER, FISHERY, SHIPPING_ACCESS, MINERAL, TIMBER, HYDROELECTRIC. Carries current stock level and depletion history. Extracted through adjacent edges with appropriate infrastructure.
- **InfrastructureType**: Enumeration of infrastructure link types (HIGHWAY, ARTERIAL, LOCAL_ROAD, RAIL, PIPELINE, TRANSMISSION, SHIPPING_LANE, AIR_LINK). Each declares served flow categories.
- **InfrastructureLink**: A single infrastructure element on an edge or vertex. Carries type, capacity per flow category, condition (health/degradation state as scalar [0.0, 1.0]), and owning organization. First-class entity with its own lifecycle.
- **EdgeInfrastructure**: The collection of InfrastructureLinks on a single edge. Derives aggregate capacity per flow category. Participates in edge weight computation for the weighted Laplacian.
- **JunctionType**: Enumeration of vertex junction types (INTERCHANGE, SUBSTATION, RAIL_JUNCTION, PORT, AIRPORT). Connects to adjacent edges.
- **NonlocalEdge**: An edge connecting two non-adjacent vertices. Subtype of the standard edge with additional metadata: distance, locality class (LOCAL/SEMI_LOCAL/NONLOCAL), and origin infrastructure (which airport/port generated it).
- **InternetAccess**: Per-hex node attributes: `internet_access: bool`, `internet_quality: float`, `surveillance_coupling: float`. Determines participation in the global consciousness field operation and state intelligence generation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every hex in the tri-county mesh has a terrain classification, and the WATER hex count is within 20% of the expected count derived from Natural Earth lake polygon area (expected 50-150 hexes at resolution 7).
- **SC-002**: Known major infrastructure corridors (I-75, I-94, I-96 where identifiable in Natural Earth data) appear as continuous sequences of edges with correct infrastructure typing.
- **SC-003**: The weighted Laplacian computed with infrastructure-derived edge weights produces measurably different field dynamics than the unweighted Laplacian -- specifically, contradiction gradients across infrastructure-poor boundaries (e.g., across the Detroit River) are steeper and more persistent than gradients across infrastructure-rich boundaries (e.g., along the I-75 corridor).
- **SC-004**: Nonlocal air edges from DTW have Ollivier-Ricci curvature < -0.5 (strongly negative), confirming bottleneck topology.
- **SC-005**: Internet consciousness field operation produces measurable state intelligence increases at participating nodes. COUNTER_INTEL actions measurably reduce surveillance coupling.
- **SC-006**: BUILD_INFRASTRUCTURE and ATTACK_INFRASTRUCTURE actions (Feature 032) produce measurable changes in edge capacity and subsequent flow patterns.
- **SC-007**: Conservation of total flow is maintained within tolerance (1e-10) when edge capacity constraints redirect or queue flows.
- **SC-008**: Biocapacity extraction from WATER hexes adjacent to LAND hexes with PORT infrastructure produces measurable increases in LAND hex production capacity and measurable decreases in WATER hex biocapacity stock.

## Dependencies

- **Requires**: Feature 026 (Tri-County Economic Substrate) -- provides the H3 resolution 7 hex mesh, county assignments, and economic tensor hydration that infrastructure topology builds upon.
- **Requires**: Feature 002 (Dialectical Field Topology) -- provides the field derivative system (gradient, Laplacian, Ricci curvature) that infrastructure edge weights feed into. Specifically upgrades assumption A-002 (unweighted Laplacian) to weighted.
- **Requires**: Feature 032 (OODA Loop System) -- defines BUILD_INFRASTRUCTURE and ATTACK_INFRASTRUCTURE action types that target infrastructure entities on edges and vertices.
- **Integrates with**: Feature 023 (Capital Volume II) -- edge capacity constraints affect wage circulation routing.
- **Integrates with**: Feature 029 (Community Hyperedge Upgrade) -- internet surveillance coupling feeds state intelligence about community-level organizing.
- **Data Sources**: Natural Earth Vector SQLite (`natural_earth_vector.sqlite` v5.1.2) for terrain, infrastructure, airports, ports. FCC broadband data (existing `FCCBroadbandLoader`) for internet access. All other data sources (HIFLD, BTS T-100, Army Corps waterborne commerce) are future refinements, not MVP requirements.

## Assumptions

- **A-001**: Natural Earth 10m vector data provides sufficient resolution for terrain classification and coarse infrastructure identification at H3 resolution 7. The 10m scale (1 cm = 100 km on paper) translates to features resolvable at roughly 1-2 km, well within the ~2.3 km hex diameter.
- **A-002**: Natural Earth `ne_10m_roads` and `ne_10m_roads_north_america` capture major highways (interstates, US routes) but may not capture all arterials and local roads in the tri-county area. This is acceptable for MVP -- the simulation needs to know "is there a major corridor here," not "what is the exact road network." HIFLD data is available for future refinement.
- **A-003**: The tri-county area has a manageable number of nonlocal edges. DTW connects to ~20-30 major airports identifiable in Natural Earth; Great Lakes shipping connects to ~5-10 ports. This is O(50) nonlocal edges, not O(n^2).
- **A-004**: Internet consciousness propagation as a field operation on the internet-connected component is computationally tractable. For ~1,500-2,500 hexes with ~80-95% internet coverage, this is a diffusion computation on ~1,200-2,300 nodes -- well within single-tick performance budget.
- **A-005**: Terrain classification uses a three-way LAND/WATER/RESOURCE typology. For the Detroit test case, RESOURCE hexes are likely zero or near-zero (southeastern Michigan is flat). RESOURCE classification is primarily relevant for national-scale federated instances (Appalachian coal, Rocky Mountain minerals, Pacific Northwest timber).
- **A-006**: Infrastructure link condition uses a simple scalar [0.0, 1.0] for MVP. Detailed damage models are deferred.
- **A-007**: Surveillance coupling coefficients are SYNTHETIC for MVP (derived from political analysis of ISP market structure, not empirically measured). Flagged as such per project convention.
- **A-008**: Biocapacity stock initial values are SYNTHETIC for MVP. Ecological/geological surveys could provide empirical calibration in future, but for gameplay purposes, the relative magnitudes matter more than absolute values.
- **A-009**: The existing `FCCBroadbandLoader` provides sufficient data for internet access classification. The FCC BDC Public Data API offers richer per-location data but requires account registration and token management; it is deferred to a future refinement pass.
- **A-010**: Lake St. Clair may require manual polygon definition or use of the `ne_10m_lakes_north_america` supplement, as it does not appear in the primary `ne_10m_lakes` table. This is a known data gap to be resolved during implementation.

## Scope Exclusions

- **Geology simulation**: No water flow, erosion, or terrain modification. Terrain is static after initialization.
- **Ecological regeneration**: Biocapacity stocks deplete but do not regenerate in MVP. Ecological dynamics are a future extension.
- **Traffic simulation**: No vehicle-level routing, congestion modeling, or traffic signal timing. Capacity is aggregate throughput.
- **Detailed telecommunications modeling**: No frequency allocation, bandwidth contention, or network protocol simulation. Internet connectivity is boolean with a quality scalar.
- **Infrastructure construction costs**: BUILD_INFRASTRUCTURE resolves as an action with AP cost (Feature 032). Material and financial costs are deferred to Vanguard Economy (Epoch 3).
- **International connectivity**: Nonlocal edges to nodes outside the US (e.g., Windsor, Canada) are deferred.
- **Dynamic terrain**: Flooding, environmental disaster, climate change effects are deferred.
- **Multi-resolution infrastructure decomposition**: The fractal behavior (H3 edge to H4 band of cells) is architecturally anticipated but not implemented. MVP operates at resolution 7 only.
- **FCC BDC API integration**: The FCC Broadband Data Collection Public Data API provides detailed per-location coverage data but requires account setup and token management. Deferred in favor of existing `FCCBroadbandLoader` data for MVP.

## Constitutional Compliance

- **I.6 (Five Edge Modes)**: Infrastructure edges are orthogonal to edge modes. An edge can be EXTRACTIVE and carry HIGHWAY infrastructure simultaneously -- the mode describes the social relation, the infrastructure describes the material substrate. No conflict.
- **II.1 (Primitives vs Derived)**: Edge capacity is derived from infrastructure inventory, never stored directly. Infrastructure links are primitives (data-sourced). Biocapacity stocks are primitives. Compliant.
- **III.1 (No Magic Constants)**: All capacity values derive from Natural Earth classification attributes mapped through GameDefines coefficients with documented provenance. Biocapacity initial values are flagged SYNTHETIC. Surveillance coupling coefficients are flagged SYNTHETIC.
- **III.3 (Physics Cosplay Prohibition)**: The "wormhole" terminology is informal. The formal content is: nonlocal edges modify graph topology, which changes the Laplacian, Ricci curvature, and gradient computations already justified by Feature 002. No new formalism introduced.
- **III.4 (Data Source Traceability)**: Natural Earth (NACIS, public domain) has been added to the approved source list via constitutional amendment (v1.8.2, commit 6a2a453).
- **III.5 (Empirical vs Strategic Separation)**: Terrain classification and infrastructure initialization are empirical (from data). Biocapacity stocks are empirical (from geographic data, with SYNTHETIC flag where estimated). Player BUILD/ATTACK actions and OPSEC investment are strategic (from player choice). Compliant.
- **V.1 (Material Base First)**: Infrastructure and terrain are material base. Computed in Layer 0 before actions and consciousness propagation. Compliant.

## Theoretical Predictions (Falsifiable Hypotheses)

- **P-001**: Edges crossing the Detroit River (with bridge/tunnel infrastructure) sustain steeper contradiction gradients than edges along the I-75 corridor (with dense highway infrastructure), when controlling for field magnitude at endpoints. The infrastructure-poor boundary resists equilibration.
- **P-002**: Nonlocal edges from DTW have Ollivier-Ricci curvature at least 0.3 units more negative than the median local edge curvature in the tri-county mesh, confirming the topological distinction between local mesh and nonlocal links.
- **P-003**: Removing (simulating destruction of) the Ambassador Bridge and Detroit-Windsor Tunnel edges produces a measurable discontinuity in Wayne County's field dynamics, demonstrating that a small number of infrastructure links on key edges have disproportionate topological impact.
- **P-004**: The class asymmetry in nonlocal connectivity is measurable: organizations of type Business and StateApparatus have access to more total nonlocal edge capacity than CivilSocietyOrg and PoliticalFaction combined, in the initialized simulation state.
- **P-005**: Hexes adjacent to Great Lakes WATER hexes with PORT infrastructure show higher historical production capacity (calibrated against QCEW data) than comparable inland hexes, consistent with the biocapacity extraction thesis.

## Sequencing Recommendation

This feature sits at the boundary between Epoch 1 (Demonstration) and Epoch 2 (Game). The terrain and infrastructure initialization (US1-US2) are Epoch 1 concerns -- they establish the material geography that the simulation computes over. The vertices, nonlocal edges, internet/surveillance mechanics, and flow integration (US3-US6) are Epoch 2 concerns -- they introduce gameplay-relevant strategic decisions.

Recommended implementation order within the spec:

1. **US1 (Terrain + Biocapacity)** -- immediate, unblocks correct topology and resource stocks for all downstream systems.
2. **US2 (Edge Infrastructure)** -- immediate after US1, provides infrastructure-derived edge weights for weighted Laplacian.
3. **US6 (Flow Integration)** -- wires infrastructure into existing systems, making US1-US2 consequential.
4. **US3 (Vertex Infrastructure)** -- adds strategic depth to infrastructure targeting.
5. **US4 (Nonlocal Edges)** -- adds airports/shipping, requires external stub nodes.
6. **US5 (Internet/Surveillance)** -- adds consciousness field operation and OPSEC mechanics, most gameplay-dependent.

The feature MAY be split into two implementation phases: **Phase A** (US1 + US2 + US6, Epoch 1) establishing material geography, and **Phase B** (US3 + US4 + US5, Epoch 2) adding strategic infrastructure mechanics. This split respects the Material Base First principle -- geography before gameplay.
