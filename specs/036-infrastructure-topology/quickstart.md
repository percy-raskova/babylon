# Quickstart: Infrastructure Topology Layer

**Feature**: 036-infrastructure-topology
**Date**: 2026-03-01

## Overview

The infrastructure topology layer adds terrain classification, edge infrastructure inventories, vertex junctions, nonlocal edges, and internet consciousness field operations to the H3 hex mesh. This quickstart shows how to use the core APIs.

## 1. Terrain Classification

Classify hexes in the tri-county mesh from Natural Earth geographic data:

```python
from babylon.infrastructure.terrain import DefaultTerrainClassifier
from babylon.data.natural_earth.reader import NaturalEarthReader

# Initialize the NE reader pointing to the external SQLite
ne_reader = NaturalEarthReader(
    db_path="/path/to/natural_earth_vector.sqlite",
)

# Create classifier with NE reader
classifier = DefaultTerrainClassifier(reader=ne_reader)

# Classify a single hex
result = classifier.classify_hex("872a1009affffff")
print(result.terrain_type)       # "LAND", "WATER", or "RESOURCE"
print(result.water_coverage_fraction)  # 0.0 to 1.0

# Classify the entire mesh
mesh_hexes = ["872a1009affffff", "872a1009bffffff", ...]
classifications = classifier.classify_mesh(mesh_hexes)

# Count terrain types
water_count = sum(
    1 for c in classifications.values() if c.terrain_type == "WATER"
)
```

## 2. Biocapacity Stocks

Initialize and extract biocapacity from WATER and RESOURCE hexes:

```python
from babylon.infrastructure.terrain import DefaultBiocapacityStore

store = DefaultBiocapacityStore(defines=game_defines)

# Initialize stocks for all non-LAND hexes
stocks = store.initialize_stocks(classifications)

# Query a specific stock
stock = store.get_stock("872a1009affffff", "FRESHWATER")
if stock:
    print(f"Initial: {stock.initial_value}, Current: {stock.current_value}")

# Extract through an edge (LAND hex extracting from adjacent WATER hex)
result = store.extract(
    source_h3="872a1009affffff",   # WATER hex
    target_h3="872a1009bffffff",   # LAND hex
    stock_type="FRESHWATER",
    infrastructure_capacity=10.0,   # From edge PORT infrastructure
    depletion_rate=0.05,            # From GameDefines
)
print(f"Extracted: {result.amount_extracted}")
print(f"Remaining: {result.remaining_stock}")
```

## 3. Edge Infrastructure

Query and modify infrastructure on edges:

```python
from babylon.infrastructure.inventory import DefaultInfrastructureInventory
from babylon.infrastructure.contracts import InfrastructureLinkState

inventory = DefaultInfrastructureInventory()

# After initialization from NE data, query an edge
links = inventory.get_edge_links("872a1009affffff", "872a1009bffffff")
for link in links:
    print(f"{link.infra_type}: {link.effective_capacity('FREIGHT')}")

# Add infrastructure (from BUILD_INFRASTRUCTURE action)
new_link = InfrastructureLinkState(
    link_id="link_001",
    infra_type="HIGHWAY",
    capacity={"FREIGHT": 100.0, "COMMUTER": 200.0},
    condition=1.0,
    owner_org_id="state_apparatus_mi",
)
inventory.add_edge_link("872a1009affffff", "872a1009bffffff", new_link)
```

## 4. Edge Capacity Computation

Compute aggregate capacity for edge weighting:

```python
from babylon.infrastructure.capacity import DefaultEdgeCapacityCalculator

calculator = DefaultEdgeCapacityCalculator(defines=game_defines)

result = calculator.compute_edge_capacity(
    source_h3="872a1009affffff",
    target_h3="872a1009bffffff",
    source_terrain="LAND",
    target_terrain="LAND",
    links=links,
    population_density=1500.0,  # people per km^2
)
print(f"Total FREIGHT capacity: {result.total_capacity['FREIGHT']}")
print(f"Total COMMUTER capacity: {result.total_capacity['COMMUTER']}")

# Compute weights for entire mesh (for weighted Laplacian)
mesh_weights = calculator.compute_mesh_weights(
    inventory=inventory,
    terrain_map=terrain_map,
    population_map=pop_map,
    edges=all_edges,
)
```

## 5. Vertex Infrastructure

Work with triple junctions and junction infrastructure:

```python
# Query a vertex
vertex = inventory.get_vertex("vtx_abc123")
if vertex:
    print(f"Adjacent hexes: {vertex.adjacent_h3}")
    for junction in vertex.junctions:
        print(f"  {junction.junction_type}: condition={junction.condition}")

# Degrade a junction (from ATTACK_INFRASTRUCTURE)
# Cascades to all 3 adjacent edges per FR-018
affected_edges = inventory.degrade_junction(
    vertex_id="vtx_abc123",
    junction_type="INTERCHANGE",
    condition_delta=0.3,
)
print(f"Cascade affected {len(affected_edges)} edges")
```

## 6. Internet Access and Consciousness Field

Initialize internet access and run consciousness propagation:

```python
from babylon.infrastructure.internet import (
    DefaultInternetAccessManager,
    DefaultInternetFieldOperator,
)

# Initialize from FCC broadband data
manager = DefaultInternetAccessManager(defines=game_defines)
access_states = manager.initialize_from_broadband(
    broadband_data={"26163": 85.0, "26125": 92.0, "26099": 88.0},
    hex_to_county=hex_county_map,
    access_threshold=0.5,
)

# Run consciousness field diffusion on internet-connected component
operator = DefaultInternetFieldOperator(manager=manager)
connected = operator.get_connected_component()
print(f"{len(connected)} hexes in internet component")

updated_consciousness = operator.propagate_consciousness(
    field_values=current_consciousness,
    diffusion_rate=0.1,
)

# Generate surveillance intelligence
surveillance = operator.generate_surveillance(
    field_values=updated_consciousness,
    state_analytical_capacity=0.7,
)
for result in surveillance:
    print(f"  Hex {result.h3_index}: intel={result.intelligence_generated:.3f}")

# Apply OPSEC (COUNTER_INTEL action)
opsec = manager.apply_opsec(
    h3_index="872a1009affffff",
    org_id="org_civil_society_001",
    opsec_investment=5.0,
    tradeoff_ratio=0.6,
)
print(f"Coupling: {opsec.coupling_before:.2f} -> {opsec.coupling_after:.2f}")
print(f"Throughput lost: {opsec.throughput_reduction:.1%}")

# State response: sever internet (visible, backfire)
response = manager.set_response_mode("872a1009affffff", "SEVER")
print(f"Backfire magnitude: {response.backfire_magnitude}")
```

## 7. Weighted Laplacian Integration

Use infrastructure-derived edge weights in the field derivative system:

```python
from babylon.engine.systems.field_derivative import FieldDerivativeSystem

# Compute mesh weights from infrastructure
weights = calculator.compute_mesh_weights(
    inventory=inventory,
    terrain_map=terrain_map,
    population_map=pop_map,
    edges=all_edges,
)

# Store weights as edge attributes on the graph
for (src, tgt), capacities in weights.items():
    graph.update_edge(
        src, tgt, "ADJACENCY",
        {"infrastructure_capacity": sum(capacities.values())},
    )

# Field derivative system uses the edge weight attribute
field_system = FieldDerivativeSystem(
    edge_weight_attr="infrastructure_capacity",
)
```

## Architecture Notes

- **Protocols**: All interfaces use ``typing.Protocol`` with ``@runtime_checkable`` for structural typing and dependency injection.
- **Frozen DTOs**: All data transfer objects are frozen Pydantic models (``ConfigDict(frozen=True)``).
- **GameDefines integration**: Capacity coefficients, depletion rates, thresholds, and tradeoff ratios are centralized in ``InfrastructureDefines`` and ``TerrainDefines`` sub-models.
- **NE data**: Read directly from the external SQLite database (no ingestion into 3NF schema). The data is static and large (423MB).
- **Separation**: Infrastructure entities are stored separately from ``WorldState.relationships`` because they represent physical substrate, not social relations.
