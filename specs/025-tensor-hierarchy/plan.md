# Implementation Plan: Tensor Hierarchy

**Branch**: `025-tensor-hierarchy` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/025-tensor-hierarchy/spec.md`

## Summary

Implement the multi-level tensor hierarchy described in `ai-docs/brainstorms/tensor/tensor_hierarchy.md`. This adds 5 Level 1 tensors (InterIndustryFlow, VisibilityMetric, GeographicFlow, ReproductionRequirements, ClassTransitionMatrix) from federal data sources, plus 3 Level 2 derived tensors (LeontiefInverse, ImperialRentField, ShadowSubsidy). The approach: add missing schema tables and ingestion loaders where needed, then build Protocol-based tensor loaders that read from SQLite and produce frozen Pydantic models integrated with the existing TensorRegistry/NoDataSentinel patterns. VisibilityMetric wraps the existing Feature 015 gamma module rather than reimplementing.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Pydantic 2.x (frozen models), NumPy (matrix ops), SciPy (sparse matrices, eigendecomposition), SQLAlchemy 2.x (ORM), NetworkX 3.x (graph)
**Storage**: SQLite (`data/sqlite/marxist-data-3NF.sqlite` via `NormalizedBase` ORM)
**Testing**: pytest with markers: `@pytest.mark.unit`, `@pytest.mark.math`, `@pytest.mark.integration`
**Target Platform**: Linux (local simulation engine)
**Project Type**: Single project (Python package)
**Performance Goals**: Batch computation — Leontief inverse of 70x70 matrix < 1s, sparse flow matrix construction < 5s
**Constraints**: Geographic flow matrix memory < 500MB; all tensor loaders must return NoDataSentinel for missing data (no crashes)
**Scale/Scope**: ~70 BEA industries, ~130 CFS Areas, 4 Marxian departments, 6 social classes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I.2 Imperial Rent (Phi) | SUPPORTS | GeographicFlow tensor provides empirical county-level Phi from BTS FAF data |
| I.5 Department III | SUPPORTS | VisibilityMetric formalizes g_33 -> 0 for shadow labor; shadow subsidy derived |
| II.2 Primitives vs Derived | PASS | Hierarchy explicitly separates Level 0-1 (from data) from Level 2 (from math) |
| II.3 NetworkX as Discretized Manifold | PASS | Tensors are field values on the graph manifold |
| II.6 State is Data, Engine is Transformation | PASS | All tensor types are frozen Pydantic models |
| III.1 No Magic Constants | PASS | All values trace to federal statistical sources |
| III.2 Falsifiability | PASS | SC-001/003/004 define benchmark comparisons |
| III.3 Physics Cosplay Prohibition | PASS | Each tensor defines index space, transformation rule, consistency test (FR-017) |
| III.4 Data Source Traceability | FLAG | BEA, BTS, ATUS already approved. CEX and PSID are NOT in the approved list — require constitutional amendment per Art. IX |

**FLAG Resolution (III.4)**: CEX (BLS Consumer Expenditure Survey) and PSID (University of Michigan Panel Study of Income Dynamics) are standard federal/academic statistical sources used in labor economics. Both should be added to the approved list via amendment. However, both are P4/P5 priority and can be deferred if the amendment blocks. The P1-P3 stories use only already-approved sources (BEA, BTS, ATUS, QCEW).

## Project Structure

### Documentation (this feature)

```text
specs/025-tensor-hierarchy/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (Protocol interfaces)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# New data loaders and schema extensions
src/babylon/data/
├── reference/
│   └── schema.py                 # MODIFY: Add BEA I-O, FAF tables
├── bea/
│   ├── io_loader.py              # NEW: BEA I-O Use/Make table ingestion
│   └── (existing: parser.py, loader_national.py, loader_concordance.py, loader_county.py)
├── bts/
│   └── faf_loader.py             # NEW: BTS FAF freight flow ingestion
├── atus/
│   └── (existing: loader.py — needs to be RUN, not rebuilt)
├── cex/                          # NEW: Consumer Expenditure Survey (P4)
│   ├── __init__.py
│   └── loader.py
└── psid/                         # NEW: Panel Study of Income Dynamics (P5)
    ├── __init__.py
    └── loader.py

# New tensor hierarchy module
src/babylon/economics/
├── tensor.py                     # EXISTS: ValueTensor4x3, NoDataSentinel (no changes)
├── tensor_registry.py            # EXISTS: TensorRegistry (no changes)
├── tensor_hierarchy/             # NEW: Multi-level tensor hierarchy
│   ├── __init__.py               # Public exports
│   ├── types.py                  # Level 1 frozen Pydantic tensor models
│   ├── protocols.py              # Data source protocols for each tensor
│   ├── inter_industry.py         # InterIndustryFlow loader + Leontief (Level 1+2)
│   ├── visibility.py             # VisibilityMetric adapter wrapping gamma (Level 1+2)
│   ├── geographic_flow.py        # GeographicFlow loader + ImperialRentField (Level 1+2)
│   ├── reproduction.py           # ReproductionRequirements (Level 1, P4)
│   ├── class_transition.py       # ClassTransitionMatrix + stationary dist (Level 1+2, P5)
│   └── validation.py             # Three-tier validation for all tensor types
└── gamma/                        # EXISTS: 9 files, 101 tests (wrapped, not modified)

# Tests
tests/
├── unit/economics/tensor_hierarchy/   # NEW: Unit tests per module
│   ├── test_types.py
│   ├── test_inter_industry.py
│   ├── test_visibility.py
│   ├── test_geographic_flow.py
│   ├── test_reproduction.py
│   ├── test_class_transition.py
│   └── test_validation.py
├── unit/data/bea/
│   └── test_io_loader.py              # NEW: BEA I-O ingestion tests
├── unit/data/bts/
│   └── test_faf_loader.py             # NEW: BTS FAF ingestion tests
└── integration/economics/
    └── test_tensor_hierarchy.py       # NEW: End-to-end tensor pipeline tests
```

**Structure Decision**: Follows existing Babylon patterns — economics computations in `src/babylon/economics/tensor_hierarchy/`, data loaders in `src/babylon/data/{source}/`, Protocol+Default implementation pattern, frozen Pydantic models, NoDataSentinel returns.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|-----------|--------------------------------------|
| CEX/PSID not in III.4 approved sources | Reproduction requirements (P4) and class mobility (P5) need these | P4/P5 are lowest priority; can defer until constitutional amendment. P1-P3 use only approved sources |

## Post-Design Constitution Re-Check

| Principle | Status | Design Impact |
|-----------|--------|---------------|
| I.2 Imperial Rent | PASS | ImperialRentField computed from FAF antisymmetric decomposition |
| I.5 Department III | PASS | VisibilityMetric wraps gamma g_33; ShadowSubsidy derived correctly |
| II.2 Primitives vs Derived | PASS | Level 1 types store raw data; Level 2 types are computed and never stored |
| II.6 State is Data | PASS | All tensor types use `ConfigDict(frozen=True)` |
| III.1 No Magic Constants | PASS | BEA-to-department mapping in TOML data file, not hardcoded |
| III.3 Physics Cosplay | PASS | FR-017 commutativity test validates each tensor earns the name |
| III.4 Data Sources | PASS (P1-P3) | BEA, BTS, ATUS all approved. CEX/PSID deferred |
| VI.2 Zoom Where Data Exists | PASS | CFS Areas (~130) match FAF data resolution, not forced to county |

## Key Data Discovery

The `data/` directory contains manually downloaded BEA data that eliminates API dependencies for P1:

| Directory | Contents | Use |
|-----------|----------|-----|
| `data/input-output/make-use/` | IOUse_Before_Redefinitions_PRO_Summary.xlsx + 11 more | Direct requirements matrix source |
| `data/input-output/total-domestic-requirements/` | IxI_TR_Summary.xlsx + 17 more | Leontief inverse benchmark |
| `data/concordance/` | BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx | Industry-to-NAICS mapping |
| `data/gross-output/` | GrossOutput.xlsx | BEA GDP-by-industry (already loaded) |
| `data/value-added/` | ValueAdded.xlsx | Value added by industry |
| `data/intermediate-output/` | IntermediateInputs.xlsx | Intermediate inputs by industry |
| `data/fixed-assets/` | Multiple vintages (2018, 2019, 2022, 2024) | Capital stock data |
| `data/gdp-by-industry/` | GdpByInd.zip + duplicates | GDP by industry |

**Not present**: BTS FAF data (needs download), CEX data, PSID data.

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Plan | `specs/025-tensor-hierarchy/plan.md` | Complete |
| Research | `specs/025-tensor-hierarchy/research.md` | Complete (8 decisions) |
| Data Model | `specs/025-tensor-hierarchy/data-model.md` | Complete (8 entities, 2 new tables) |
| Contracts | `specs/025-tensor-hierarchy/contracts/protocols.md` | Complete (7 protocols) |
| Quickstart | `specs/025-tensor-hierarchy/quickstart.md` | Complete |
| Agent Context | `CLAUDE.md` | Updated |
