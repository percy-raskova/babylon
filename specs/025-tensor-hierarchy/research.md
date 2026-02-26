# Research: Tensor Hierarchy

**Feature**: 025-tensor-hierarchy | **Date**: 2026-02-26

## Decision 1: BEA I-O Data Source Format

**Decision**: Parse the already-downloaded BEA XLSX files at `data/input-output/` directly. No API needed.

**Rationale**: The user has manually downloaded the complete BEA I-O dataset:
- `data/input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx` — the Use table (industries × commodities) at ~70 summary-level industries
- `data/input-output/make-use/IOMake_Before_Redefinitions_PRO_Summary.xlsx` — the Make table
- `data/input-output/total-domestic-requirements/IxI_TR_Summary.xlsx` — Total Requirements (industry-by-industry), which IS the Leontief inverse
- `data/input-output/total-domestic-requirements/IxI_Domestic_Summary.xlsx` — Domestic-only requirements
- `data/concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` — official BEA-NAICS mapping
- Three resolution levels available: Sector (~15), Summary (~70), Detail (~400). Spec selects Summary.

**Alternatives considered**:
- BEA API: Would require API key registration; adds external dependency. Rejected because data is already local.
- CSV export: BEA doesn't publish I-O as CSV. The canonical format is XLSX workbooks.

## Decision 2: Which I-O Table to Use for Coefficient Matrix A

**Decision**: Use the "Use Before Redefinitions (Producers' Prices)" at Summary level. This table shows commodities consumed by each industry.

**Rationale**: The Use table in producers' prices represents the actual technical structure of production — how industries use commodities. Dividing each column by the industry's total output yields the direct requirements coefficient matrix A. The "Before Redefinitions" version preserves the full Make-Use accounting identity. Summary level (~70 industries) matches the spec assumption.

**Verification**: The downloaded `IxI_TR_Summary.xlsx` (Total Requirements, Industry-by-Industry) IS the pre-computed Leontief inverse L = (I-A)^{-1}. We can use this to validate our computed Leontief inverse from the Use table coefficients.

**Alternatives considered**:
- Supply-Use tables: More modern SNA framework but adds complexity (rectangular matrices). Rejected for initial implementation.
- Direct Requirements table: Would skip the Use → coefficient derivation step but doesn't teach the pipeline. We compute it ourselves and validate against BEA's published total requirements.

## Decision 3: Existing Gamma Module Integration Strategy

**Decision**: Create a thin adapter in `tensor_hierarchy/visibility.py` that wraps the existing gamma calculators and expresses their output as a VisibilityMetric tensor type.

**Rationale**: Feature 015 (gamma visibility) is complete with 101 tests. Key classes to wrap:
- `DefaultGammaIIICalculator.compute(year)` → `GammaIII` (contains `gamma_iii` = g_33)
- `DefaultShadowSubsidyCalculator.compute_phi_iii(gamma_iii, melt)` → `ShadowSubsidy`
- Adapter constructs `VisibilityMetric` (diagonal 4x4 matrix) by setting g_33 from gamma_iii and g_11, g_22a, g_22b from QCEW (all ≈ 1.0 since Depts I/IIa/IIb are mostly paid labor).

**No modifications to gamma module itself.** The adapter is a one-way dependency: tensor_hierarchy → gamma. Tests exercise the adapter, not the wrapped calculators.

## Decision 4: BTS FAF Data Acquisition

**Decision**: Build a new FAF ingestion loader that downloads FAF5 data from the BTS website and populates the `fact_commodity_flow` table at CFS Area resolution.

**Rationale**: No FAF data is currently in the `data/` directory. FAF5 (Freight Analysis Framework v5) provides origin-destination commodity flows for ~130 CFS Areas. BTS publishes FAF5 as downloadable CSV/ZIP at https://www.bts.gov/faf. The existing `fact_commodity_flow` table in the 3NF schema can store this data, and the `dim_cfs_area` dimension table exists but has 0 rows.

**Alternatives considered**:
- Census CFS API: Already has a loader (`cfs/loader.py`) but it notes CFS doesn't provide true O-D pairs. FAF is the correct source for inter-area flows.
- Synthetic/imputed flows: Rejected — violates III.1 (No Magic Constants).

## Decision 5: Schema Extensions Needed

**Decision**: Add the following tables to `reference/schema.py`:

| New Table | Purpose | Columns (key) |
|-----------|---------|----------------|
| `fact_bea_io_coefficient` | BEA I-O direct requirements matrix | year, source_industry_id, target_industry_id, coefficient |
| `dim_bea_io_table_type` | Distinguish Use/Make/Supply/TR tables | table_type, description |

**Existing tables that need population (already defined, 0 rows)**:
- `dim_cfs_area` — CFS Area dimension
- `fact_commodity_flow` — O-D commodity flows (repurpose for FAF)
- `dim_sctg_commodity` — SCTG commodity codes
- `dim_atus_activity_category` — ATUS activity categories
- `fact_atus_reproductive_labor` — ATUS time use data

**No schema changes needed for**:
- VisibilityMetric: Uses gamma module (in-memory)
- ClassTransitionMatrix: Accepts programmatic input or loads from PSID (P5, deferred)
- ReproductionRequirements: Uses CEX (P4, deferred)

## Decision 6: Industry-to-Department Mapping

**Decision**: Create a TOML/YAML mapping file at `src/babylon/economics/tensor_hierarchy/mappings/bea_to_department.toml` that maps each of the ~70 BEA summary industries to one of the 4 Marxian departments.

**Rationale**: The mapping is a domain knowledge artifact, not code logic. Following the project's data-driven design pattern (Paradox Pattern from CLAUDE.md), the mapping should be in a data file, not hardcoded conditionals.

**Mapping principles**:
- Dept I (Means of Production): Mining, Manufacturing (capital goods), Construction
- Dept IIa (Necessary Consumption): Agriculture, Food manufacturing, Housing, Utilities, Healthcare, Education
- Dept IIb (Luxury Consumption): Luxury goods, Entertainment, Finance, Professional services
- Dept III (Social Reproduction): Household services, Child care, Elder care
- Industries with mixed character are split by BEA's own value-added data

## Decision 7: TensorRegistry Integration

**Decision**: New tensors are NOT stored in the existing `TensorRegistry` (which is specific to `ValueTensor4x3`). Instead, each tensor type has its own registry/cache following the same pattern.

**Rationale**: `TensorRegistry` is tightly coupled to `ValueTensor4x3` — its `get()` returns `ValueTensor4x3 | NoDataSentinel`, and its aggregate computation sums department rows. The new tensors have different shapes (70x70 matrix, 130x130 sparse matrix, 4x4 diagonal) and different aggregation semantics. Creating separate registries per tensor type preserves type safety and avoids a god-object.

**Pattern to follow**: Each tensor module exports a `get_{tensor_type}(year, **params) -> TensorType | NoDataSentinel` function that handles caching internally.

## Decision 8: CEX and PSID (P4/P5) Deferral Strategy

**Decision**: P4 (ReproductionRequirements from CEX) and P5 (ClassTransitionMatrix from PSID) are spec'd but deferred until:
1. Constitutional amendment adds CEX and PSID to III.4 approved data sources
2. Data files are obtained (CEX public-use, PSID with registration)

**Rationale**: P1-P3 use only already-approved data sources (BEA, BTS, ATUS, QCEW). The tensor type definitions and computation logic for P4/P5 can be implemented and tested with synthetic data, but the production loaders require the amendment.

**Implementation approach**: Define the frozen Pydantic models and computation functions in `reproduction.py` and `class_transition.py`. Write tests with synthetic matrices. Defer loader implementations to a follow-up feature.
