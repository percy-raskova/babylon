---
date: 2026-01-06T11:28:25-05:00
researcher: Claude
git_commit: 0f96664
branch: dev
repository: babylon
topic: "Epoch 2 Documentation Gap Analysis"
tags: [research, epoch2, documentation, data-infrastructure, visualization, geography]
status: complete
last_updated: 2026-01-06
last_updated_by: Claude
---

# Research: Epoch 2 Documentation Gap Analysis

**Date**: 2026-01-06T11:28:25-05:00
**Researcher**: Claude
**Git Commit**: 0f96664
**Branch**: dev
**Repository**: babylon

## Research Question

What is missing from `ai-docs/epochs/epoch2/` that either:
1. Already exists elsewhere in `ai-docs/` and should be linked/incorporated
2. Is a glaringly obvious gap that needs to be documented

## Summary

The Epoch 2 documentation has significant gaps across four categories:

| Category | Documents in ai-docs/ NOT in epoch2/ | Obvious Missing Specs |
|----------|-------------------------------------|----------------------|
| **Data Infrastructure** | census-data-loader.yaml, fred-api.yaml, database-spec.yaml | Schema Integration spec (2.7) |
| **Visualization** | dpg-patterns.yaml, echarts-patterns.yaml, synopticon-spec.yaml, design-system.yaml, ui-wireframes.yaml | PyQt patterns spec |
| **Geography/Topology** | graph-abstraction-spec.yaml, carceral-geography.yaml, territorial-schema.yaml, topology-system.yaml | Territory type migration spec |
| **Economic Flows** | imperial-circuit.yaml, political-economy-liquidity.yaml, metabolic-slice.yaml, class-dynamics.yaml | (Already covered by lodes-freight-flows.yaml) |

**Critical Finding**: The `graph-abstraction-spec.yaml` is explicitly an Epoch 2 deliverable (GraphProtocol interface for NetworkX→DuckDB migration) but is not in `epochs/epoch2/`.

---

## Detailed Findings

### 1. Data Infrastructure Gaps

#### Already Documented in ai-docs/ but NOT in epoch2/

| File | What It Documents | Relationship to Epoch 2 |
|------|-------------------|------------------------|
| `census-data-loader.yaml` | ACS loader with race disaggregation, DimRace, DimMetroArea | **NEW LOADER** not listed in epoch2/data-infrastructure.yaml |
| `fred-api.yaml` | FRED API details, rate limits, Marxian formulas | **EXTENDS** epoch2 fred loader with patterns |
| `census-insights.yaml` | MLM-TW analysis of ACS data | Game design, not infrastructure |
| `database-spec.yaml` | Game simulation database (babylon.db) | **SEPARATE SYSTEM** - Ledger layer, not research data |

**Key Gap**: `census-data-loader.yaml` documents the **ACS (American Community Survey)** loader which provides demographic/income data with race disaggregation. This is DISTINCT from:
- `census_qcew` (employment data) - already in epoch2
- `census_cbp` (business patterns) - already in epoch2

The ACS loader adds:
- `DimRace` dimension with 10 race codes (MLM-TW indigenous/Hispanic analysis)
- `DimMetroArea` dimension for MSA/CSA aggregation
- `BridgeCountyMetro` many-to-many bridge table
- Race-disaggregated income and employment facts

**Recommendation**: Add to `epochs/epoch2/data-infrastructure.yaml`:
```yaml
loaders:
  complete:
    - census_acs: "American Community Survey (income, demographics, race)"
```

#### Schema Integration (Slice 2.7) - NOT DOCUMENTED

The overview mentions Slice 2.7 "Schema Integration" as PLANNED but there's no spec file. This slice bridges:
- Research database (`research.sqlite`) → Simulation entities
- FIPS codes → Territory node IDs
- Census demographics → SocialClass initialization
- QCEW employment → Economic flow parameters

**Recommendation**: Create `epochs/epoch2/schema-integration.yaml` documenting:
- Hydration patterns (database → Pydantic → WorldState)
- Census data → SocialClass field mappings
- FIPS → Territory ID resolution (or H3 mapping)
- Time dimension handling (which year's data initializes simulation)

---

### 2. Visualization Gaps

#### Already Documented in ai-docs/ but NOT in epoch2/

| File | What It Documents | Relationship to Epoch 2 |
|------|-------------------|------------------------|
| `dpg-patterns.yaml` | DearPyGui patterns (current implementation) | **MIGRATION SOURCE** for PyQt |
| `echarts-patterns.yaml` | ECharts patterns for web-based charts | **REUSABLE** in QWebEngineView |
| `synopticon-spec.yaml` | Observer system, Lens filter, degradation model | **INFORMS** dashboard requirements |
| `design-system.yaml` | Bunker Constructivism palette, typography | **SOURCE OF TRUTH** for all UI |
| `ui-wireframes.yaml` | Current DearPyGui layout (1460×820) | **MIGRATION SOURCE** for PyQt |

**Key Gap**: `epochs/epoch2/pyqt-visualization.yaml` exists but is a skeleton. It needs:

1. **Qt Layout Patterns**: Translate `ui-wireframes.yaml` two-column layout to QVBoxLayout/QHBoxLayout/QSplitter
2. **Qt Theming**: Convert `design-system.yaml` RGBA tuples to Qt stylesheets (QSS)
3. **Real-Time Plot Migration**: How to achieve 60 FPS updates in Qt (QCustomPlot vs embedded ECharts)
4. **Event Log Migration**: `dpg-patterns.yaml` scrollable log → QTextEdit with rich text
5. **Simulation Loop Integration**: QTimer + QThread patterns for non-blocking updates

**Components Needing PyQt Equivalents**:

| DearPyGui Component | PyQt6 Equivalent | Notes |
|---------------------|------------------|-------|
| `dpg.add_plot()` | `QCustomPlot` or `QWebEngineView` + ECharts | Need performance testing |
| `dpg.add_child_window()` | `QScrollArea` | Scrollable containers |
| `dpg.add_button()` | `QPushButton` | Direct mapping |
| `dpg.add_text()` | `QLabel` or `QTextEdit` | Rich text for logs |
| `dpg.draw_rect()` | `QProgressBar` or custom `QPainter` | Gauge rendering |
| `dpg.theme()` | Qt Stylesheets (QSS) | Global theming |

**Recommendation**: Expand `epochs/epoch2/pyqt-visualization.yaml` with migration patterns from `dpg-patterns.yaml`.

---

### 3. Geography/Topology Gaps

#### Already Documented in ai-docs/ but NOT in epoch2/

| File | What It Documents | Relationship to Epoch 2 |
|------|-------------------|------------------------|
| `graph-abstraction-spec.yaml` | GraphProtocol interface (NetworkX→DuckDB) | **EPOCH 2 DELIVERABLE** - should be in epoch2/ |
| `carceral-geography.yaml` | Displacement pipeline, sink nodes | Informs Territory type design |
| `territorial-schema.yaml` | OGV/OPC/Frontier territory types | Design rationale for H3 integration |
| `topology-system.yaml` | Percolation theory, phase states | No changes needed for H3 |

**Critical Gap**: `graph-abstraction-spec.yaml` explicitly describes the GraphProtocol interface needed for Epoch 2→3 migration. It defines:

1. **GraphProtocol Interface**: 16 methods for backend-agnostic graph operations
2. **Data Models**: GraphNode, GraphEdge, TraversalQuery, TraversalResult
3. **Adapters**: InMemoryAdapter (NetworkX, current) → ColumnarAdapter (DuckDB+DuckPGQ, Epoch 3)
4. **Franchise Schema**: OrganizationUnit, Territory subtypes, PopFragment (scale model)

The spec states:
> "Technology Bridge: Gradual migration from direct NetworkX to GraphProtocol-mediated access"

This is the Epoch 2 "Schema Integration" work that enables Epoch 3 scale.

**Recommendation**: Either:
- Move `graph-abstraction-spec.yaml` to `epochs/epoch2/` as it's an Epoch 2 deliverable
- OR create `epochs/epoch2/graph-abstraction.yaml` that references it

#### H3 Integration Points (from graph-abstraction-spec.yaml)

The spec identifies these H3 touchpoints that `h3-geographic-system.yaml` should address:

1. **Territory.id** change: `T[0-9]{3}` → H3 hex string (`8928308280fffff`)
2. **ADJACENCY auto-generation**: `h3.grid_ring(h3_index, 1)` replaces manual edge creation
3. **Data bridge**: `dim_county.fips_code` → `h3_res4` mapping
4. **Multi-resolution hierarchy**: res4 (county) → res7 (neighborhood) for Franchise schema

---

### 4. Economic Flow Gaps

#### Already Documented in ai-docs/

| File | What It Documents | Relationship to Epoch 2 |
|------|-------------------|------------------------|
| `imperial-circuit.yaml` | 4-node value extraction model | **THEORETICAL BASIS** for LODES/FAF integration |
| `political-economy-liquidity.yaml` | Money as constraint, fiscal mechanics | Informs data requirements |
| `metabolic-slice.yaml` | Biocapacity, extraction intensity | FAF tonnage → extraction_intensity |
| `class-dynamics.yaml` | ODE system for wealth flows | LODES geography → class mapping |

**Assessment**: `epochs/epoch2/lodes-freight-flows.yaml` is well-designed and covers the right scope. The economic flow documents in ai-docs/ provide theoretical context that LODES/FAF data operationalizes.

**No Gap**: The relationship is: theory (ai-docs/) → data (epoch2/) → simulation (epoch3/)

---

### 5. Glaringly Obvious Gaps NOT in ai-docs/

#### 5.1 Data Quality & Error Handling Spec

The current loaders have ad-hoc error handling. Epoch 2 should document:
- API failure recovery (rate limits, timeouts, HTTP errors)
- Missing data handling (which counties lack QCEW data? What's the fallback?)
- Data validation (sanity checks, outlier detection)
- Incremental loading (don't re-download unchanged data)

**Recommendation**: Create `epochs/epoch2/data-quality.yaml`

#### 5.2 API Key Management Spec

Current state: API keys in environment variables. Needs documentation for:
- Required keys: CENSUS_API_KEY, FRED_API_KEY, FCC credentials, ENERGY_API_KEY
- Key registration URLs
- Rate limit documentation per API
- Testing without keys (mock mode)

**Recommendation**: Add to `epochs/epoch2/data-infrastructure.yaml` or separate `api-keys.yaml`

#### 5.3 Database Migration Spec

How do we upgrade the schema when new loaders are added? Needs:
- SQLAlchemy Alembic migration patterns (or alternative)
- Schema versioning
- Data preservation during schema changes

**Recommendation**: Document in Schema Integration spec

#### 5.4 CLI Commands Spec

`epochs/epoch2/data-infrastructure.yaml` lists some CLI commands but they're incomplete. Full spec needed for:
- `mise run data:*` namespace
- Loader selection (which loaders to run)
- Database initialization vs incremental load
- Progress reporting

**Location**: `ai-docs/tooling.yaml` has some commands but Epoch 2 data CLI is sparse.

---

## Recommended Actions

### Priority 1: Add Missing Epoch 2 Specs

| File to Create | Content |
|----------------|---------|
| `epochs/epoch2/schema-integration.yaml` | Slice 2.7 spec: database → simulation bridge |
| `epochs/epoch2/graph-protocol.yaml` | Link to `graph-abstraction-spec.yaml`, Epoch 2 scope |
| `epochs/epoch2/data-quality.yaml` | Error handling, validation, incremental loading |

### Priority 2: Update Existing Epoch 2 Specs

| File to Update | Changes |
|----------------|---------|
| `epochs/epoch2/data-infrastructure.yaml` | Add `census_acs` loader, API key docs |
| `epochs/epoch2/pyqt-visualization.yaml` | Add migration patterns from dpg-patterns.yaml |
| `epochs/epoch2/h3-geographic-system.yaml` | Add graph-abstraction integration points |

### Priority 3: Cross-Reference Existing ai-docs/

| epoch2/ Spec | Should Reference |
|--------------|------------------|
| `data-infrastructure.yaml` | `census-data-loader.yaml`, `fred-api.yaml` |
| `pyqt-visualization.yaml` | `dpg-patterns.yaml`, `design-system.yaml`, `ui-wireframes.yaml` |
| `h3-geographic-system.yaml` | `graph-abstraction-spec.yaml`, `territorial-schema.yaml` |
| `lodes-freight-flows.yaml` | `imperial-circuit.yaml`, `metabolic-slice.yaml` |

---

## Architecture Documentation

### Current epoch2/ Structure

```
ai-docs/epochs/epoch2/
├── overview.md                    # Summary, slice status
├── data-infrastructure.yaml       # Slice 2.1-2.4 (COMPLETE)
├── h3-geographic-system.yaml      # Slice 2.5 (PLANNED)
├── pyqt-visualization.yaml        # Slice 2.6 (PLANNED)
├── lodes-freight-flows.yaml       # Slice 2.8 (PLANNED)
└── ideological-geography.yaml     # Slice 2.9 (PLANNED)
```

### Recommended epoch2/ Structure

```
ai-docs/epochs/epoch2/
├── overview.md                    # Update slice table
├── data-infrastructure.yaml       # Add census_acs, API keys
├── schema-integration.yaml        # NEW: Slice 2.7 spec
├── graph-protocol.yaml            # NEW: GraphProtocol scope
├── data-quality.yaml              # NEW: Error handling spec
├── h3-geographic-system.yaml      # Add graph-abstraction links
├── pyqt-visualization.yaml        # Add migration patterns
├── lodes-freight-flows.yaml       # Add theory cross-refs
└── ideological-geography.yaml     # No changes needed
```

---

## Code References

- `src/babylon/data/normalize/schema.py` - 3NF schema (33 dims, 28 facts)
- `src/babylon/data/census/loader_3nf.py` - ACS loader (not in epoch2 docs)
- `src/babylon/ui/dpg_runner.py` - Current DearPyGui dashboard
- `src/babylon/ui/design_system.py` - Color constants
- `src/babylon/models/world_state.py` - `to_graph()`/`from_graph()` methods

---

## Historical Context (from thoughts/)

No directly relevant prior research found for this topic.

---

## Related Research

- `thoughts/shared/plans/2026-01-06-data-infrastructure-gaps.md` - Physical geography data plan

---

## Open Questions

1. Should `graph-abstraction-spec.yaml` move to `epochs/epoch2/` or remain in root ai-docs/?
2. Is Schema Integration (Slice 2.7) part of Epoch 2 or Epoch 3? The overview says PLANNED but no spec exists.
3. Should we create a `pyqt-patterns.yaml` analogous to `dpg-patterns.yaml` as a separate reference doc?
