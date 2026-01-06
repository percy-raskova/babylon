# Epochs Architecture Refactoring Plan

## Implementation Status

| Phase | Status | Completed |
|-------|--------|-----------|
| 0. Epoch 1 Closure Tasks | PENDING | - |
| 1. Directory Restructure | PENDING | - |
| 2. Epoch 1 Documentation | PENDING | - |
| 3. Epoch 2 Documentation | PENDING | - |
| 4. Epoch 3 Documentation | PENDING | - |
| 5. Epoch 4 Documentation | PENDING | - |
| 6. Index and Cross-References | PENDING | - |
| 7. Archive Old Structure | PENDING | - |

## Overview

Refactor `ai-docs/` to establish a coherent Epochs model that accurately reflects completed work, current progress, and future roadmap. This plan:

1. Declares **Epoch 1 complete** (simulation mechanics validated)
2. Creates **Epoch 2: The Foundation** for data infrastructure and visualization work
3. Renumbers existing **Epoch 2 specs to Epoch 3** (game features)
4. Establishes **Epoch 4** vision for platform scaling

## Current State Analysis

### Documentation vs Reality

| Documented | Actual | Gap |
|------------|--------|-----|
| 10 Systems | 13 Systems | +3 undocumented |
| 13 EventTypes | 25 EventTypes | +12 undocumented |
| 3,050 tests | 4,133 tests | +1,083 tests |
| Epoch 2 = Game Features | Epoch 2 specs written but data layer built instead | Major scope shift |
| No data layer epoch | 10+ API loaders, 3NF schema complete | New work stream |
| No visualization research | PyQt+pydeck, H3 hexagons researched | New work stream |

### Key Discoveries

1. **Epoch 1 is mechanically complete** (`thoughts/shared/research/2026-01-05-epoch1-completion-status.md`)
   - All survival calculus formulas working
   - Bifurcation routing verified
   - 13 Systems in strict execution order
   - Only UI polish gaps remain (Rift Chart, Endgame Screen)

2. **Massive data infrastructure built** (`thoughts/shared/plans/2026-01-05-circulatory-api-loaders.md`)
   - 3NF SQLite schema with 20+ tables
   - Loaders: Census, FRED, Energy, QCEW, Trade, Materials, HIFLD, MIRTA, FCC
   - Not accounted for in any Epoch document

3. **Visualization evolution researched** (`thoughts/shared/research/2026-01-05-pyqt-pydeck-integration.md`)
   - DearPyGui inadequate for 74,000 territories
   - PyQt6 + QWebEngineView + pydeck architecture designed
   - H3 hexagonal coordinate system integration planned

4. **Epoch 2 specs are game features** (`ai-docs/epoch2/`)
   - 18 comprehensive spec files
   - Demographics, Warfare, Balkanization, etc.
   - These require the data/visualization foundation first

## Desired End State

After this refactoring:

```
ai-docs/
├── README.md                    # Updated index
├── epochs/
│   ├── overview.md              # Master epochs overview
│   ├── epoch1-complete.md       # Epoch 1 completion record
│   ├── epoch2/                  # The Foundation (new)
│   │   ├── overview.md
│   │   ├── data-infrastructure.yaml
│   │   ├── h3-geographic-system.yaml
│   │   └── pyqt-visualization.yaml
│   ├── epoch3/                  # The Game (renumbered from epoch2/)
│   │   ├── overview.md
│   │   ├── demographics-spec.yaml
│   │   ├── vanguard-economy.yaml
│   │   └── ... (18 files total)
│   └── epoch4/                  # The Platform (new)
│       ├── overview.md
│       └── vision.yaml
├── architecture.yaml            # Unchanged
├── decisions/                   # Unchanged
└── ... (other existing files)
```

### Success Verification

```bash
# Verify new structure
ls -la ai-docs/epochs/

# Verify epoch numbering consistency
grep -r "epoch:" ai-docs/epochs/ | grep -v "epoch: [1-4]"  # Should be empty

# Verify cross-references work
grep -r "epoch2/" ai-docs/ | wc -l  # Should be 0 after update
```

## What We're NOT Doing

1. **Not rewriting Epoch 2 specs** - Just renumbering to Epoch 3
2. **Not implementing any code** - This is documentation refactoring only
3. **Not changing CLAUDE.md** - Will update after plan is complete
4. **Not archiving research** - `thoughts/` stays as-is
5. **Not modifying ADRs** - Decisions are historical records

## Implementation Approach

Execute in phases:
1. **Phase 0**: Complete Epoch 1 UI gaps (prerequisite)
2. **Phase 1**: Create new directory structure
3. **Phase 2-5**: Write epoch documentation in order
4. **Phase 6**: Update indexes and cross-references
5. **Phase 7**: Archive old structure, update CLAUDE.md

---

## Phase 0: Epoch 1 Closure Tasks

### Overview
Complete the remaining Epoch 1 UI work before refactoring documentation.

### Changes Required

#### 1. Rift Trend Sparkline
**File**: `src/babylon/ui/dpg_runner.py`
**Changes**: Add line series showing overshoot_ratio history over ticks

```python
# Track overshoot history
self._overshoot_history: list[float] = []
MAX_HISTORY = 100

# In update loop:
overshoot = calculate_overshoot_ratio(...)
self._overshoot_history.append(overshoot)
if len(self._overshoot_history) > MAX_HISTORY:
    self._overshoot_history.pop(0)

# Render sparkline
dpg.set_value("rift_trend_series", [list(range(len(self._overshoot_history))), self._overshoot_history])
```

#### 2. Basic Endgame Screen
**File**: `src/babylon/ui/dpg_runner.py`
**Changes**: Add modal window that displays on ENDGAME_REACHED event

```python
def _show_endgame_screen(self, outcome: EndgameOutcome, stats: dict) -> None:
    """Display endgame modal with outcome and statistics."""
    with dpg.window(label="Simulation Complete", modal=True, ...):
        dpg.add_text(f"Outcome: {outcome.value}")
        dpg.add_text(f"Ticks Survived: {stats['ticks']}")
        # ... additional stats
```

### Success Criteria

#### Automated Verification:
- [ ] All tests pass: `mise run test:unit`
- [ ] Type checking passes: `mise run typecheck`
- [ ] Dashboard launches without error: `mise run ui`

#### Manual Verification:
- [ ] Rift trend sparkline visible and updates each tick
- [ ] Endgame screen appears when simulation reaches terminal state
- [ ] Outcome correctly identified (Revolutionary Victory, Ecological Collapse, or Fascist Consolidation)

**Implementation Note**: Complete this phase before proceeding. These are ~5 hours of work total.

---

## Phase 1: Directory Restructure

### Overview
Create new `ai-docs/epochs/` directory structure.

### Changes Required

#### 1. Create epochs directory structure
**Commands**:
```bash
mkdir -p ai-docs/epochs/epoch2
mkdir -p ai-docs/epochs/epoch3
mkdir -p ai-docs/epochs/epoch4
mkdir -p ai-docs/archive/epoch2-original
```

#### 2. Move existing epoch2/ contents to epoch3/
**Commands**:
```bash
# Preserve original for reference
cp -r ai-docs/epoch2/* ai-docs/archive/epoch2-original/

# Move to new location
mv ai-docs/epoch2/* ai-docs/epochs/epoch3/
rmdir ai-docs/epoch2
```

### Success Criteria

#### Automated Verification:
- [x] New directory exists: `ls ai-docs/epochs/epoch3/`
- [x] Original epoch2/ removed: `! test -d ai-docs/epoch2`
- [x] Archive contains backup: `ls ai-docs/archive/epoch2-original/`

---

## Phase 2: Epoch 1 Documentation

### Overview
Create comprehensive Epoch 1 completion documentation.

### Changes Required

#### 1. Update existing epoch1-mvp-complete.md
**File**: `ai-docs/epochs/epoch1-complete.md` (move from `ai-docs/epoch1-mvp-complete.md`)
**Changes**: Comprehensive update with final metrics

```markdown
# Epoch 1: The Engine - COMPLETE

**Status**: COMPLETE
**Version**: v1.0.0
**Completion Date**: 2026-01-05
**Theme**: "Graph + Math = History"

## Summary

Epoch 1 established the core simulation engine with:
- 13 deterministic Systems in strict execution order
- 25 EventTypes covering all game domains
- 17 formulas implementing MLM-TW survival calculus
- 4,133 tests ensuring mechanical correctness
- GraphProtocol abstraction enabling future database swaps

## Systems Inventory

| # | System | File | Purpose |
|---|--------|------|---------|
| 1 | ImperialRentSystem | `systems/economic.py` | Wealth extraction via imperial rent |
| 2 | SolidaritySystem | `systems/solidarity.py` | Consciousness transmission |
| 3 | ConsciousnessSystem | `systems/ideology.py` | Ideology drift & bifurcation |
| 4 | SurvivalSystem | `systems/survival.py` | P(S|A), P(S|R) calculations |
| 5 | StruggleSystem | `systems/struggle.py` | George Floyd Dynamic |
| 6 | ContradictionSystem | `systems/contradiction.py` | Tension/rupture dynamics |
| 7 | TerritorySystem | `systems/territory.py` | Heat, eviction, carceral geography |
| 8 | MetabolismSystem | `systems/metabolism.py` | Metabolic rift calculations |
| 9 | EndgameSystem | `systems/endgame.py` | Terminal state detection |
| 10 | DecompositionSystem | `systems/decomposition.py` | Class decomposition |
| 11 | ControlRatioSystem | `systems/control_ratio.py` | Control ratio tracking |
| 12 | EventTemplateSystem | `systems/event_template.py` | Event generation |
| 13 | ResourceSystem | `systems/resource.py` | Resource management |

## Slices Completed

| Slice | Name | Status |
|-------|------|--------|
| 1.1 | Core Types | COMPLETE |
| 1.2 | Economic Flow | COMPLETE |
| 1.3 | Survival Calculus | COMPLETE |
| 1.4 | Consciousness Drift | COMPLETE |
| 1.5 | Synopticon Dashboard | COMPLETE |
| 1.6 | Endgame Resolution | COMPLETE |
| 1.7 | Graph Bridge | COMPLETE |
| 1.8 | Carceral Geography | COMPLETE |

## Key Achievements

1. **Fundamental Theorem Implemented**: Revolution impossible when W_c > V_c
2. **Bifurcation Formula Working**: Agitation routes to class consciousness OR fascism based on solidarity edges
3. **Survival Calculus Verified**: P(S|A) and P(S|R) with Kahneman-Tversky loss aversion (λ=2.25)
4. **George Floyd Dynamic**: EXCESSIVE_FORCE → UPRISING event chain
5. **Endgame Detection**: Three outcomes (Revolutionary Victory, Ecological Collapse, Fascist Consolidation)

## Metrics

- **Tests**: 4,133 (729 test classes)
- **Systems**: 13
- **EventTypes**: 25
- **Formulas**: 17
- **ADRs**: 29

## Next Steps

Epoch 1 provides the validated simulation core. Epoch 2 builds the data infrastructure needed for continental-scale simulation.
```

### Success Criteria

#### Automated Verification:
- [ ] File exists: `test -f ai-docs/epochs/epoch1-complete.md`
- [ ] Old location removed: `! test -f ai-docs/epoch1-mvp-complete.md`

---

## Phase 3: Epoch 2 Documentation

### Overview
Create Epoch 2 (The Foundation) documentation for data infrastructure work.

### Changes Required

#### 1. Epoch 2 Overview
**File**: `ai-docs/epochs/epoch2/overview.md`

```markdown
# Epoch 2: The Foundation

**Status**: IN PROGRESS
**Theme**: "Real Data, Real Geography, Real Scale"

## Summary

Epoch 2 builds the infrastructure needed for continental-scale simulation:
- Real economic data from federal APIs (Census, FRED, BLS)
- Real coercive infrastructure data (HIFLD prisons, police; MIRTA military)
- H3 hexagonal coordinate system for geographic precision
- PyQt + pydeck visualization capable of rendering 74,000+ territories

## Why This Epoch Exists

Epoch 1 validated mechanics with abstract territories (T001, T002...).
Epoch 3 requires simulating the actual United States with:
- 50 states
- 3,000+ counties
- 70,000+ cities/townships

This requires:
1. **Real Data**: Economic flows, demographics, infrastructure
2. **Real Geography**: H3 hexagonal coordinates for precise positioning
3. **Scalable Visualization**: DearPyGui cannot render 74,000 territories

## Slices

| Slice | Name | Status | Description |
|-------|------|--------|-------------|
| 2.1 | 3NF Schema | COMPLETE | SQLite schema with dim/fact tables |
| 2.2 | Census Loaders | COMPLETE | QCEW, CBP, population data |
| 2.3 | Economic Loaders | COMPLETE | FRED, Energy, Trade, Materials |
| 2.4 | Circulatory Loaders | COMPLETE | HIFLD, MIRTA, FCC broadband |
| 2.5 | H3 Geographic System | PLANNED | Hexagonal territory coordinates |
| 2.6 | PyQt Visualization | PLANNED | Replace DearPyGui |
| 2.7 | Schema Integration | PLANNED | Bridge data layer to simulation |

## Dependencies

- Epoch 1 must be complete (simulation mechanics)
- API keys required: CENSUS_API_KEY, FRED_API_KEY, FCC credentials

## Success Criteria

Epoch 2 is complete when:
1. All API loaders operational and tested
2. H3 coordinates assigned to all territories
3. PyQt dashboard renders 3,000+ county hexagons
4. Simulation can hydrate state from database
```

#### 2. Data Infrastructure Spec
**File**: `ai-docs/epochs/epoch2/data-infrastructure.yaml`

```yaml
# Epoch 2: Data Infrastructure Specification

meta:
  epoch: 2
  slice: "2.1-2.4"
  status: COMPLETE
  purpose: "3NF database schema and API loaders for real-world data"

schema:
  location: "src/babylon/data/normalize/schema.py"

  dimensions:
    - DimState: "50 US states + territories"
    - DimCounty: "3,200+ counties via 5-digit FIPS"
    - DimMetroArea: "MSA/CSA codes"
    - DimIndustry: "NAICS codes"
    - DimCommodity: "HS codes for trade"
    - DimCoerciveType: "Prison, police, military categories"
    - DimDataSource: "Provenance tracking"

  facts:
    - FactEmployment: "QCEW employment by county/industry"
    - FactGDP: "FRED GDP time series"
    - FactEnergy: "EIA energy production/consumption"
    - FactTrade: "Census trade flows"
    - FactCoerciveInfrastructure: "Prison beds, police stations"
    - FactBroadbandCoverage: "FCC broadband metrics"
    - FactElectricGrid: "Substations, transmission lines"

loaders:
  complete:
    - census_qcew: "Quarterly Census of Employment & Wages"
    - census_cbp: "County Business Patterns"
    - fred: "Federal Reserve Economic Data"
    - energy: "EIA energy statistics"
    - trade: "Census foreign trade"
    - materials: "USGS materials flow"
    - hifld_prisons: "DHS prison boundaries"
    - hifld_police: "DHS law enforcement locations"
    - hifld_electric: "DHS electric grid"
    - mirta: "DoD military installations"
    - fcc: "FCC broadband coverage"

  deferred:
    - census_cfs: "Commodity Flow Survey - needs geographic hierarchy"

cli_commands:
  - "mise run data:load --loaders=census,fred,energy"
  - "mise run data:hifld-prisons"
  - "mise run data:fcc-download && mise run data:fcc"
```

#### 3. H3 Geographic System Spec
**File**: `ai-docs/epochs/epoch2/h3-geographic-system.yaml`

```yaml
# Epoch 2: H3 Hexagonal Coordinate System

meta:
  epoch: 2
  slice: "2.5"
  status: PLANNED
  purpose: "Replace abstract territory IDs with H3 hexagonal coordinates"
  research: "thoughts/shared/research/2026-01-05-h3-hexagonal-integration.md"

overview:
  what: "Uber H3 discrete global grid system"
  why: |
    - Equidistant neighbors (all 6 neighbors same distance)
    - Optimal tessellation (no gaps, no overlaps)
    - Hierarchical (aperture 7: each cell has 7 children)
    - Matches county grain at resolution 4 (~1,770 km²)

resolution_strategy:
  epoch2: "Resolution 4 (~county scale, 288,000 cells for continental US)"
  epoch3: "Resolution 5-6 (~city/township scale)"
  epoch4: "Resolution 7-9 (~neighborhood/block scale)"

integration_points:
  territory_model:
    current: "id pattern ^T[0-9]{3}$ (abstract)"
    target: "h3_index: 15-character hex string"

  adjacency_edges:
    current: "Manual edge creation"
    target: "Auto-generate via h3.grid_ring(cell, 1)"

  database:
    current: "dim_county with FIPS codes"
    target: "Add h3_res4 column, bridge to Territory"

implementation_tasks:
  - Add h3-py dependency to pyproject.toml
  - Add h3_index field to Territory model
  - Create county_fips → h3_res4 mapping table
  - Update WorldState.to_graph() to use H3 as node IDs
  - Implement adjacency edge generation via H3 neighbors
```

#### 4. PyQt Visualization Spec
**File**: `ai-docs/epochs/epoch2/pyqt-visualization.yaml`

```yaml
# Epoch 2: PyQt + pydeck Visualization System

meta:
  epoch: 2
  slice: "2.6"
  status: PLANNED
  purpose: "Replace DearPyGui with PyQt6 + QWebEngineView + pydeck"
  research: "thoughts/shared/research/2026-01-05-pyqt-pydeck-integration.md"

rationale:
  problem: "DearPyGui canvas cannot render 74,000+ territories"
  solution: "Embed deck.gl via QWebEngineView for WebGL-accelerated hexagons"

architecture:
  layers:
    - PyQt6: "Native Qt widgets for panels, controls, status"
    - QWebEngineView: "Chromium-based web view for map"
    - pydeck: "Python → deck.gl HTML generation"
    - deck.gl: "WebGL hexagon rendering (H3HexagonLayer)"

key_patterns:
  html_generation: |
    # Generate pydeck HTML
    deck = pydeck.Deck(layers=[H3HexagonLayer(data=h3_cells)])
    html = deck.to_html(as_string=True)

    # Load into QWebEngineView
    self.map_view.setHtml(html)

  event_bridge: |
    # QWebChannel for Python↔JavaScript communication
    channel = QWebChannel(self.map_view.page())
    channel.registerObject("bridge", self.bridge_object)

  threading: |
    # Simulation in QThreadPool, GUI updates via signals
    worker.signals.map_updated.connect(self.on_map_update)

implementation_tasks:
  - Add PyQt6, PyQt6-WebEngine, pydeck to dependencies
  - Create MapWidget(QWebEngineView) component
  - Implement DashboardWindow with Qt layout
  - Create H3HexagonLayer renderer
  - Port DearPyGui panels to Qt widgets
  - Implement simulation→map signal bridge
```

### Success Criteria

#### Automated Verification:
- [ ] All files created: `ls ai-docs/epochs/epoch2/`
- [ ] YAML valid: `poetry run yamllint ai-docs/epochs/epoch2/`

---

## Phase 4: Epoch 3 Documentation

### Overview
Update renumbered Epoch 3 files (formerly Epoch 2) with correct epoch references.

### Changes Required

#### 1. Create Epoch 3 Overview
**File**: `ai-docs/epochs/epoch3/overview.md`

```markdown
# Epoch 3: The Game

**Status**: PLANNED
**Theme**: "From Theory to Strategy"

## Summary

Epoch 3 transforms the simulation engine into a playable game with:
- Demographics and population dynamics
- Vanguard resource economy
- Fog of war and information asymmetry
- Kinetic warfare and system disruption
- Balkanization and territorial fracture
- Doctrine trees and strategic choices

## Prerequisites

- Epoch 2 complete (data infrastructure, H3 geography, PyQt visualization)
- Real US data loaded (counties, infrastructure, economics)

## Sub-Epochs

| Sub-Epoch | Name | Focus |
|-----------|------|-------|
| 3A | Materialism | Demographics, Vanguard Economy |
| 3B | Organization | Cohesion Mechanic |
| 3C | Information | Fog of War, The Wire, Repression |
| 3D | Conflict | Warfare, Balkanization, Doctrine |

## Slices

| Slice | Name | Spec File | Sub-Epoch |
|-------|------|-----------|-----------|
| 3.1 | Demographics | demographics-spec.yaml | 3A |
| 3.2 | Vanguard Economy | vanguard-economy.yaml | 3A |
| 3.3 | Cohesion Mechanic | cohesion-mechanic.yaml | 3B |
| 3.4 | Fog of War | fog-of-war.yaml | 3C |
| 3.5 | The Wire | gramscian-wire-*.yaml | 3C |
| 3.6 | Repression Logic | repression-logic.yaml | 3C |
| 3.7 | State Attention | state-attention-economy.yaml | 3C |
| 3.8 | Kinetic Warfare | kinetic-warfare.yaml | 3D |
| 3.9 | Balkanization | balkanization-spec.yaml | 3D |
| 3.10 | Doctrine Tree | doctrine-tree.yaml | 3D |
| 3.11 | Strategy Layer | strategy-layer.yaml | 3D |
| 3.12 | Reactionary Subject | reactionary-subject.yaml | 3D |
```

#### 2. Update epoch references in all moved files
**Files**: All YAML files in `ai-docs/epochs/epoch3/`
**Changes**: Update `epoch: 2` to `epoch: 3` in meta sections

```bash
# Batch update epoch references
for f in ai-docs/epochs/epoch3/*.yaml; do
  sed -i 's/epoch: 2/epoch: 3/g' "$f"
  sed -i 's/sub_epoch: "2/sub_epoch: "3/g' "$f"
  sed -i 's/slice: "2\./slice: "3./g' "$f"
done
```

### Success Criteria

#### Automated Verification:
- [ ] Overview exists: `test -f ai-docs/epochs/epoch3/overview.md`
- [ ] No epoch 2 references: `! grep -r "epoch: 2" ai-docs/epochs/epoch3/`
- [ ] All files have epoch 3: `grep -l "epoch: 3" ai-docs/epochs/epoch3/*.yaml | wc -l` equals file count

---

## Phase 5: Epoch 4 Documentation

### Overview
Create Epoch 4 (The Platform) vision documentation.

### Changes Required

#### 1. Epoch 4 Overview
**File**: `ai-docs/epochs/epoch4/overview.md`

```markdown
# Epoch 4: The Platform

**Status**: VISION
**Theme**: "From Game to Engine"

## Summary

Epoch 4 scales Babylon from a single-player game to a reusable simulation platform:
- DuckDB unification (Ledger + Topology in one database)
- RAG-powered narrative generation
- Multi-scenario parallel simulation
- API layer for external integrations

## Prerequisites

- Epoch 3 complete (full game feature set)
- Performance profiled at continental scale

## Slices

| Slice | Name | Description |
|-------|------|-------------|
| 4.1 | DuckDB Migration | Unify SQLite + NetworkX into DuckDB + DuckPGQ |
| 4.2 | Native H3 | Use DuckDB H3 extension for spatial queries |
| 4.3 | RAG Integration | ChromaDB narrative generation with Marxist corpus |
| 4.4 | Multi-Scenario | Parallel simulation branches, A/B testing |
| 4.5 | API Layer | REST/GraphQL API for simulation-as-service |
| 4.6 | Persistence | Save/load game state, checkpointing |

## Key Architectural Changes

### DuckDB Unification

Currently:
- SQLite for Ledger (cold storage)
- NetworkX for Topology (hot compute)
- Hydration/dehydration between layers

Target:
- DuckDB for both Ledger AND Topology
- DuckPGQ for native graph queries
- H3 extension for spatial operations
- Single database file, no layer translation
```

#### 2. Epoch 4 Vision Spec
**File**: `ai-docs/epochs/epoch4/vision.yaml`

```yaml
# Epoch 4: The Platform - Vision Specification

meta:
  epoch: 4
  status: VISION
  purpose: "Scale Babylon from game to reusable simulation platform"

duckdb_migration:
  rationale: |
    DuckDB + DuckPGQ enables both relational queries (Ledger) AND
    graph queries (Topology) in a single embedded database.

  benefits:
    - Single database file for entire game state
    - Native graph algorithms (shortest path, centrality)
    - SQL + GQL in same query
    - Better performance for 74,000+ nodes
    - Simplified persistence (no hydration/dehydration)

  migration_path:
    - "4.1.1: Implement GraphProtocol.DuckDBAdapter"
    - "4.1.2: Migrate dim/fact tables to DuckDB"
    - "4.1.3: Enable DuckPGQ for Topology queries"
    - "4.1.4: Deprecate SQLite, remove NetworkX"

rag_integration:
  location: "src/babylon/rag/"
  corpus: "Marxist theoretical texts in ChromaDB"
  purpose: "Generate narrative responses to simulation events"

  components:
    - NarrativeDirector: "Orchestrates RAG queries"
    - BondiAlgorithm: "Dramatic arc generation"
    - TheoryMatcher: "Map events to theoretical concepts"

api_layer:
  purpose: "Expose simulation as service for tooling/education"
  endpoints:
    - "POST /simulation/create"
    - "POST /simulation/{id}/tick"
    - "GET /simulation/{id}/state"
    - "GET /simulation/{id}/events"
```

### Success Criteria

#### Automated Verification:
- [ ] All files created: `ls ai-docs/epochs/epoch4/`
- [ ] YAML valid: `poetry run yamllint ai-docs/epochs/epoch4/`

---

## Phase 6: Index and Cross-References

### Overview
Create master index and update cross-references throughout ai-docs/.

### Changes Required

#### 1. Master Epochs Overview
**File**: `ai-docs/epochs/overview.md`

```markdown
# Babylon Epochs Overview

## The Four Epochs

| Epoch | Name | Theme | Status |
|-------|------|-------|--------|
| 1 | The Engine | "Graph + Math = History" | COMPLETE |
| 2 | The Foundation | "Real Data, Real Geography, Real Scale" | IN PROGRESS |
| 3 | The Game | "From Theory to Strategy" | PLANNED |
| 4 | The Platform | "From Game to Engine" | VISION |

## Epoch 1: The Engine (COMPLETE)

Validated core simulation mechanics:
- 13 deterministic Systems
- Survival calculus (P(S|A), P(S|R))
- Bifurcation formula
- DearPyGui dashboard

[Full documentation](./epoch1-complete.md)

## Epoch 2: The Foundation (IN PROGRESS)

Building infrastructure for continental scale:
- 3NF database schema (COMPLETE)
- 10+ API data loaders (COMPLETE)
- H3 hexagonal coordinates (PLANNED)
- PyQt + pydeck visualization (PLANNED)

[Full documentation](./epoch2/overview.md)

## Epoch 3: The Game (PLANNED)

Game features and mechanics:
- Demographics and population
- Vanguard resource economy
- Fog of war and information
- Kinetic warfare
- Balkanization

[Full documentation](./epoch3/overview.md)

## Epoch 4: The Platform (VISION)

Scaling to simulation platform:
- DuckDB migration
- RAG narrative generation
- Multi-scenario support
- API layer

[Full documentation](./epoch4/overview.md)
```

#### 2. Update ai-docs/README.md
**File**: `ai-docs/README.md`
**Changes**: Update catalog to reference new epochs structure

#### 3. Update epochs-overview.md (old file)
**File**: `ai-docs/epochs-overview.md`
**Changes**: Replace with redirect to `epochs/overview.md` or delete

### Success Criteria

#### Automated Verification:
- [ ] Master overview exists: `test -f ai-docs/epochs/overview.md`
- [ ] README updated: `grep "epochs/" ai-docs/README.md`
- [ ] Old epochs-overview.md handled

---

## Phase 7: Archive and Finalize

### Overview
Archive old structure and update CLAUDE.md references.

### Changes Required

#### 1. Archive old files
**Commands**:
```bash
# Move old epoch files to archive
mv ai-docs/epochs-overview.md ai-docs/archive/
mv ai-docs/epoch1-mvp-complete.md ai-docs/archive/
```

#### 2. Update CLAUDE.md epoch references
**File**: `CLAUDE.md`
**Changes**: Update any references to old epoch structure

#### 3. Update state.yaml
**File**: `ai-docs/state.yaml`
**Changes**: Update epoch status and metrics

### Success Criteria

#### Automated Verification:
- [ ] Archive contains old files: `ls ai-docs/archive/`
- [ ] No broken cross-references: `grep -r "epoch2/" ai-docs/ | grep -v archive | wc -l` equals 0
- [ ] Lint passes: `mise run lint`

#### Manual Verification:
- [ ] Read through `ai-docs/epochs/overview.md` for coherence
- [ ] Verify epoch progression makes logical sense
- [ ] Confirm no orphaned documentation

---

## Testing Strategy

### Documentation Validation:
- YAML lint: `poetry run yamllint ai-docs/epochs/`
- Markdown lint: Check for broken links
- Cross-reference audit: No references to old paths

### Coherence Checks:
- Each epoch has clear entry criteria (prerequisites)
- Each epoch has clear exit criteria (completion definition)
- Slice numbering is consistent within epochs
- Status tags are consistent (COMPLETE, IN PROGRESS, PLANNED, VISION)

---

## References

### Research Documents:
- `thoughts/shared/research/2026-01-05-epoch1-completion-status.md`
- `thoughts/shared/research/2026-01-05-h3-hexagonal-integration.md`
- `thoughts/shared/research/2026-01-05-pyqt-pydeck-integration.md`

### Implementation Plans:
- `thoughts/shared/plans/2026-01-05-circulatory-api-loaders.md`
- `thoughts/shared/plans/2026-01-05-qcew-api-migration.md`

### ADRs:
- `ai-docs/decisions/ADR029_hybrid_graph_architecture.yaml`
- `ai-docs/decisions/ADR011_pure_graph_architecture.yaml`
