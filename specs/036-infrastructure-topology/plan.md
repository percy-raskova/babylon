# Implementation Plan: Infrastructure Topology Layer

**Branch**: `036-infrastructure-topology` | **Date**: 2026-03-01 | **Spec**: `specs/036-infrastructure-topology/spec.md`
**Input**: Feature specification from `/specs/036-infrastructure-topology/spec.md`

## Summary

Add terrain classification (LAND/WATER/RESOURCE), typed infrastructure inventories on H3 edges and vertices, nonlocal edges for airports and shipping, biocapacity stock extraction, internet consciousness field operations with surveillance coupling, and weighted Laplacian integration to the simulation's H3 hex mesh. Infrastructure capacity derives from Natural Earth vector data snapped to the H3 cell complex, providing material geography that constrains all flow computations.

## Technical Context

**Language/Version**: Python 3.12+ (existing project standard)
**Primary Dependencies**: Pydantic 2.x (frozen models, validation), NetworkX 3.x (GraphProtocol via NetworkXAdapter), h3 4.2 (spatial indexing), Shapely 2.x (spatial intersection for NE snapping), SciPy (weighted curvature LP)
**Storage**: In-memory via GraphProtocol. No new database tables. Infrastructure entities stored separately from WorldState.relationships. Natural Earth SQLite (423MB) read-only external data source. FCC broadband data via existing FCCBroadbandLoader.
**Testing**: pytest (unit + integration). Contract tests for Protocol compliance. Spatial tests against known NE features (DTW, I-75, Great Lakes).
**Target Platform**: Linux (local simulation engine)
**Project Type**: Single project (extends existing `src/babylon/` tree)
**Performance Goals**: Infrastructure initialization <5s for tri-county mesh (~1,500-2,500 hexes at r7). Weighted Laplacian computation within existing per-tick budget. NE snapping O(features * edges) ≈ O(750K) operations — fast enough without spatial indexing for MVP.
**Constraints**: Frozen Pydantic models for all DTOs. Protocol-based DI. No magic constants (III.1). SYNTHETIC flag on estimated values. All capacity coefficients in GameDefines with provenance.
**Scale/Scope**: ~1,500-2,500 hexes, ~4,500-7,500 edges, ~3,000-5,000 vertices, O(100) NE road features, O(50) NE railroad features, O(5) airports, O(10) ports, O(50) nonlocal edges.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.6 (Solidarity as Edge Mode) | PASS | Infrastructure edges are orthogonal to social edge modes. An edge can be EXTRACTIVE and carry HIGHWAY infrastructure simultaneously. |
| I.7 (Quantitative → Qualitative) | PASS | Biocapacity stocks are quantities (deplete via float). Terrain type is a quality (enum, static). Infrastructure condition is a quantity; destruction at 0.0 is a qualitative transition. |
| I.12 (Catastrophe Surface) | PASS | Infrastructure destruction at condition=0.0 is a fold crossing. Internet SEVER is a discrete state transition. |
| II.1 (Primitives vs Derived) | PASS | Infrastructure links are primitives (data-sourced). Edge capacity is derived from link inventory. Never store derived capacity directly. |
| II.3 (NetworkX as Manifold) | PASS | Infrastructure adds edge/node attributes to the existing graph manifold. Nonlocal edges modify graph topology. |
| II.6 (State is Data, Engine is Transformation) | PASS | Infrastructure state is frozen Pydantic data. Snapping, capacity computation, and field operations are pure transformations. |
| III.1 (No Magic Constants) | PASS | All capacity values derive from NE classification × GameDefines coefficients with provenance. Biocapacity initial values flagged SYNTHETIC. Surveillance coupling flagged SYNTHETIC. |
| III.3 (Physics Cosplay Prohibition) | PASS | "Wormhole" terminology informal. Formal content: nonlocal edges modify graph topology for existing justified field computations. No new formalism. |
| III.4 (Data Source Traceability) | PASS | Natural Earth added to approved sources via constitutional amendment v1.8.2. FCC data already approved. |
| III.5 (Empirical vs Strategic) | PASS | Terrain/infrastructure initialization is empirical (from data). Player BUILD/ATTACK/OPSEC actions are strategic (from choice). |

**Post-Phase 1 Re-check**: All gates still pass. No new constitutional concerns introduced by the data model or contract design.

## Project Structure

### Documentation (this feature)

```text
specs/036-infrastructure-topology/
├── plan.md              # This file
├── spec.md              # Feature specification (33 FRs, 10 ECs, 8 SCs)
├── research.md          # Phase 0: 7 research decisions (R1-R7)
├── data-model.md        # Phase 1: 7 entities, 7 enumerations, state relationships
├── quickstart.md        # Phase 1: Usage examples for all subsystems
├── checklists/
│   └── requirements.md  # Specification quality validation (all passed)
├── contracts/
│   ├── terrain.py       # TerrainClassifier, BiocapacityStore protocols
│   ├── infrastructure.py # InfrastructureInventory, EdgeCapacityCalculator, SpatialSnapper protocols
│   └── internet.py      # InternetFieldOperator, InternetAccessManager protocols
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/babylon/
├── infrastructure/                   # NEW: Infrastructure topology module
│   ├── __init__.py                   # Package exports
│   ├── terrain.py                    # DefaultTerrainClassifier, DefaultBiocapacityStore
│   ├── inventory.py                  # DefaultInfrastructureInventory (edges + vertices)
│   ├── capacity.py                   # DefaultEdgeCapacityCalculator
│   ├── internet.py                   # DefaultInternetAccessManager, DefaultInternetFieldOperator
│   ├── snapping.py                   # DefaultSpatialSnapper (NE features → H3 mesh)
│   └── nonlocal.py                   # Nonlocal edge generation (airports, shipping)
├── data/
│   └── natural_earth/                # NEW: Natural Earth data reader
│       ├── __init__.py
│       └── reader.py                 # NaturalEarthReader (read-only SQLite access)
├── config/
│   └── defines.py                    # MODIFIED: Add InfrastructureDefines, TerrainDefines
├── models/
│   └── enums.py                      # MODIFIED: Add InfrastructureType, FlowCategory, etc.
├── engine/
│   └── systems/
│       └── field_derivative.py       # MODIFIED: Optional weighted Laplacian (edge_weight_attr)
├── formulas/
│   └── curvature.py                  # MODIFIED: Weighted distance and probability measure
└── data/h3/
    └── mesh.py                       # NEW: H3 edge/vertex enumeration utilities

tests/
├── unit/
│   └── infrastructure/               # NEW: Unit tests
│       ├── test_terrain.py           # Terrain classification tests
│       ├── test_inventory.py         # Infrastructure inventory tests
│       ├── test_capacity.py          # Edge capacity computation tests
│       ├── test_internet.py          # Internet field operation tests
│       ├── test_snapping.py          # Spatial snapping tests
│       └── test_nonlocal.py          # Nonlocal edge tests
├── contract/
│   └── test_infrastructure_contracts.py  # Protocol compliance tests
└── integration/
    └── test_infrastructure_integration.py  # End-to-end initialization + field computation
```

**Structure Decision**: Single project extension following the established pattern. New `src/babylon/infrastructure/` module for domain logic, `src/babylon/data/natural_earth/` for data reading (read-only, following the DataLoader pattern but without 3NF ingestion). Modifications to existing modules (`defines.py`, `enums.py`, `field_derivative.py`, `curvature.py`) are minimal and backward-compatible.

## Complexity Tracking

> No constitutional violations to justify. All design decisions comply with existing principles.
