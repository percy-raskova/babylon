# Research: Capital Volume II Integration

**Feature**: 023-capital-volume-ii
**Date**: 2026-02-25
**Status**: Complete

## Research Questions & Findings

### R1: How does existing CapitalStockCalculator relate to fixed capital decomposition?

**Decision**: Extend, don't replace. The existing `CapitalStockCalculator` computes aggregate K from undifferentiated `total_c`. A new `FixedCirculatingDecomposer` will split `total_c` into fixed and circulating portions using industry-level BEA ratios, feeding the fixed portion to the existing PIM while the circulating portion turns over completely each cycle.

**Rationale**: The existing calculator is well-tested and thread-safe with caching. Replacing it would risk regressions in Features 012-021 which depend on it. Instead, layering decomposition on top preserves backward compatibility.

**Alternatives considered**:
- Replace CapitalStockCalculator entirely: Too risky, would break 6+ features
- Modify DepartmentRow to store fixed_c and circulating_c separately: Would break ValueTensor4x3 contract and all hydrators
- Store decomposition ratio on DepreciationConfig: Too narrow, ratio varies by industry not just rate

**Key findings**:
- `DepreciationConfig` at `src/babylon/economics/depreciation.py:74` — single δ = 0.07, no category split
- `CapitalStockCalculator` at `src/babylon/economics/capital_stock.py:65` — uses `tensor.total_c` (all 4 depts summed) as single investment flow
- Three preset rates exist (slow=0.05, default=0.07, fast=0.10) but only for sensitivity analysis
- No field anywhere distinguishes fixed from circulating constant capital

### R2: What is the tick-to-time mapping?

**Decision**: Use the existing temporal semantics. 1 tick = 1 week, annual pipeline fires every 52 ticks. Turnover profiles express durations in days. Turnovers-per-year = 365 / turnover_time_days. Circuit phase transitions are simulated within the annual pipeline call as sub-steps, similar to how crisis detection does 4 quarterly evaluations per annual tick.

**Rationale**: The simulation's temporal resolution is weekly ticks but the economics pipeline only fires annually. Turnover dynamics operate on a yearly timescale (turnovers per year) which aligns with this annual cadence. Finer-grained simulation would require restructuring the entire tick system.

**Key findings**:
- `WEEKS_PER_YEAR = 52` at `system.py:66`
- Pipeline gate: `if tick % WEEKS_PER_YEAR != 0: return` at `system.py:131`
- Year derivation: `base_year + tick // WEEKS_PER_YEAR` at `system.py:218-240`
- Crisis already does quarterly sub-stepping (4 evals per annual tick) — established pattern

### R3: How should Volume II crisis integrate with existing TRPF crisis?

**Decision**: Parallel detection with separate state fields. A new `CirculationCrisisState` is added as an additional field on `CountyEconomicState`, alongside the existing `crisis_state` (TRPF). Both detectors run independently within the annual pipeline. Downstream consumers (narrative, UI, endgame) can read both signals.

**Rationale**: Volume II crises (realization, disproportionality, turnover disruption) are theoretically distinct from TRPF. A county can have a stable profit rate but face realization crisis (can't sell). Merging them into a single phase lifecycle would lose this distinction.

**Alternatives considered**:
- Extend `CrisisPhase` enum with new values (REALIZATION, DISPROPORTIONALITY): Would complicate the existing 5-phase lifecycle and PhasedAmplificationProfile table
- Replace `MultiPeriodCrisisDetector` with a unified detector: Too disruptive, Feature 018 is well-tested
- Store circulation crisis as graph attributes only (no CountyEconomicState field): Would lose cross-tick state tracking

**Key findings**:
- `CountyEconomicState` at `tick/types.py:262` — already composes `crisis_state` and `bifurcation_risk` as direct fields
- Graph bridge flattens to `tick_` prefixed attributes — new fields follow same pattern
- `EventType` enum has slots for new crisis event types
- Extension pattern: add field with factory default, serialize in graph bridge

### R4: What department structure exists for reproduction schema?

**Decision**: Use existing `ValueTensor4x3` departments directly. Simple reproduction condition combines IIa and IIb as a single "Department II". No new department models needed — the reproduction checker takes `DepartmentRow` instances from the existing tensor.

**Rationale**: The four-department structure (I, IIa, IIb, III) is already richer than Marx's original two-department schema. Combining IIa+IIb for the reproduction condition I(v+s)=IIc is straightforward. Department III is already modeled, enabling the extended reproduction check.

**Key findings**:
- `DepartmentRow` at `tensor.py:133` — has c, v, s fields, all `LaborHours`
- `ValueTensor4x3` at `tensor.py:211` — has dept_I, dept_IIa, dept_IIb, dept_III
- NO reproduction schema checker exists anywhere in the codebase
- `reproduction.py` is about imperial rent (Emmanuel-Amin), not Marx Vol II reproduction

### R5: What BEA/Census data is available for turnover profiles?

**Decision**: Use BEA Fixed Asset Tables for fixed/circulating capital ratios and Census M3 inventory-to-sales ratios for sale time proxies. Initial implementation uses hardcoded industry-level defaults derived from these sources, with a data loader protocol for future federal data integration.

**Rationale**: The existing project pattern (see MELT, gamma, throughput modules) seeds from hardcoded defaults with Protocol-based data source injection. This avoids blocking feature implementation on data pipeline work.

**Alternatives considered**:
- Build data loaders first: Would delay feature implementation significantly
- Use single flat defaults for all industries: Would lose the industry-variation insight that is Volume II's key contribution
- Use Census QFR for all data: QFR is quarterly and sector-level, not county-level

**Key findings**:
- III.4 approved data sources include BEA and Census — no new source approval needed
- Existing pattern: `CountyHydrator` Protocol for lazy data injection (`tensor_registry.py:54-73`)
- BEA Fixed Asset Tables provide: gross/net stock by industry, depreciation by industry, average service lives
- Census M3 provides: manufacturers' inventory-to-sales ratios by industry
- Industry-level data maps via existing NAICS → Department infrastructure

### R6: What is the source structure pattern for new economics subpackages?

**Decision**: Follow the established `economics/gamma/` and `economics/crisis/` pattern: a subpackage with `types.py`, formula modules, `__init__.py` with `__all__`, and corresponding `tests/unit/economics/circulation/` test directory.

**Rationale**: Consistency with established project patterns (Features 015, 018) reduces cognitive overhead and ensures CI/linting compatibility.

**Key findings**:
- `economics/gamma/` has: `types.py`, `calculator.py`, `validation.py`, `__init__.py` (9 source files, 101 tests)
- `economics/crisis/` has: `bifurcation.py`, `wage_compression.py`, `__init__.py`
- All use frozen Pydantic models with `ConfigDict(frozen=True)`
- Protocol + Default implementation pattern for DI
- `NoDataSentinel` pattern for missing data graceful handling
