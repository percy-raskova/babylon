# Feature Specification: End-to-End Leontief Imperial Rent Integration

**Feature Branch**: `057-leontief-rent-integration`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "A1-full. Wire `ProductionChainRentCalculator` end-to-end so the simulation actually computes per-county imperial rent (`phi_hour`) from BEA Leontief decomposition + periphery wage coefficients + final demand + industry-to-county QCEW allocation, replacing the no-op stub in `tick/system.py:_compute_imperial_rent`. Implement the missing `PeripheryLaborCoefficientsSource` and `FinalDemandSource` data layers and the industry-to-county allocation step. Delete the orphaned per-county TVT-axiom tests left over from commit `a5f73139`."

## Background and Motivation

Commit `a5f73139` ("feat(economics): implement Leontief production chain imperial rent", 2026-04-12) introduced a new structural model for imperial rent based on the Leontief inverse of the BEA Input-Output table, periphery-vs-core wage ratios, and final demand. The new calculator (`ProductionChainRentCalculator`) is mathematically complete and unit-tested in isolation.

That same commit also **removed** the previous per-worker calculator (TVT Axiom E3/E4 `Φ_hour = (W/τ)·(1/γ_basket) − 1`) and stubbed the simulation's per-tick imperial-rent step (`_compute_imperial_rent` in `src/babylon/economics/tick/system.py`) to write `phi_hour = 0.0` to every county "until tensor integration."

As a result, two consequential downstream behaviors are currently silent no-ops every tick:

1. The accumulation and savings dynamics (`accumulation.py`, `savings_schedule.py`) read `phi_hour` to compute `phi_adjustment = min(phi_hour · 2080 / wage, phi_cap)`. With `phi_hour = 0`, savings receive no imperial-rent contribution.
2. The graph bridge in `simulation.py` writes `phi_hour` onto the per-county node attribute, where downstream observers and the UI read it. Visualizations of imperial rent over the map are uniformly zero.

Twelve consequences of the partial migration remain visible in the test suite as 87+ test failures and 2 collection errors from tests that exercise the old per-worker calculator API. Cleaning those up is what surfaced this spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Per-county imperial rent computed every tick (Priority: P1)

When the simulation runs a tick, every county that has the data needed to participate in the Leontief calculation receives a non-trivial `phi_hour` value derived from the structural model: BEA inter-industry flow → import-share decomposition → Leontief inverse → periphery-wage coefficients → final demand → industry-level rent → county allocation by industry employment shares.

**Why this priority**: Without this, the Leontief calculator is dead code, the savings/accumulation dynamics receive zero imperial-rent input every tick, and the simulation cannot model the central thesis of MLM-TW (the imperial subsidy to core consumption).

**Independent Test**: Run a single-tick simulation across the configured scenario (Wayne County baseline). Assert that `phi_hour` is not uniformly zero across counties, that values are deterministic given fixed inputs, that the per-county allocation sums (weighted by employment) to the national total industry rent within a small tolerance, and that no county's `phi_hour` is `NaN` or infinite.

**Acceptance Scenarios**:

1. **Given** a configured simulation with the Wayne County scenario and a tick year for which BEA + QCEW data are available, **When** one tick is executed, **Then** at least one county's `phi_hour` is non-zero and the per-county distribution is reproducible across runs with identical inputs.
2. **Given** a county whose dominant industries have core/periphery wage ratios near 1.0, **When** the tick is executed, **Then** that county's `phi_hour` is correspondingly small (rent ≈ 0 when there is no wage gap to extract).
3. **Given** a county whose dominant industries have wage ratios significantly above 1.0, **When** the tick is executed, **Then** that county's `phi_hour` is positive and proportional to the size of those wage gaps weighted by the county's employment share in those industries.

---

### User Story 2 - Periphery wage coefficients from a documented dataset (Priority: P1)

The `PeripheryLaborCoefficients` input — the per-industry vector of core/periphery wage ratios — is produced by a named, documented data source whose origin (Hickel/Sullivan/Zoomkawala, ILO, Penn World Tables, etc.), units (USD/hour, PPP-adjusted or nominal), and reference year are recorded alongside the values.

**Why this priority**: The numerical credibility of every downstream `phi_hour` value depends on these wage ratios. An implementation that uses unattributed constants is indistinguishable from the current zero stub for stakeholder trust.

**Independent Test**: Inspect the data-source object: it exposes a method that returns wage ratios for a given year, and accompanying metadata identifying the source publication, the geographic definition of "periphery", the unit of the ratio, and the year of the data. The values produced for a known year fall within an empirically defended range (no negative ratios, no implausibly large values).

**Acceptance Scenarios**:

1. **Given** a request for periphery wage coefficients for year Y, **When** the source is queried, **Then** it returns one ratio per BEA industry, all finite and ≥ 1.0 (core wages are never lower than periphery wages in the structural model), and a metadata record identifying the publication and base year.
2. **Given** a year for which no source data is available, **When** the source is queried, **Then** the system either returns a clearly marked "no-data" sentinel or raises a typed exception — it does not silently substitute synthetic values.

---

### User Story 3 - Final demand sourced from BEA tables (Priority: P1)

The `final_demand` vector input is produced by a data source that reads the appropriate column of the BEA Use Table (or equivalent) for the requested year, returns one entry per BEA industry in the same ordering as the inter-industry flow matrix, and records the source year and units.

**Why this priority**: Final demand is the multiplier on the per-industry rent vector — it determines the absolute scale of computed `phi_hour`. Without a real source, results have no monetary interpretation.

**Independent Test**: Inspect the source: querying for year Y returns a vector whose length equals the number of BEA industries in the corresponding inter-industry flow, whose entries are non-negative, and whose total matches an independently recoverable national figure (BEA published GDP component) within a small tolerance.

**Acceptance Scenarios**:

1. **Given** a year for which BEA Use Table data is loaded, **When** final demand is requested, **Then** the returned vector has the same length as the BEA industry list for that year and the sum is within tolerance of published BEA GDP final demand.
2. **Given** an industry list mismatch between the inter-industry flow source and the final-demand source for the same year, **When** the calculator is invoked, **Then** the system fails fast with a clear diagnostic identifying the misalignment, rather than silently producing wrong numbers.

---

### User Story 4 - Industry-level rent allocated to counties by employment share (Priority: P2)

Per-industry imperial rent (`phi_vector`) is allocated to counties using each county's share of national employment in that industry (sourced from QCEW). Each county's `phi_hour` aggregates its allocated industry rents and normalises by the county's total employment-hours.

**Why this priority**: Without this allocation step, the calculator's per-industry output is not consumable by the per-county tick system — the rest of the simulation cannot use it. This is a P2 because the calculator-input data sources (Stories 2-3) and the calculator integration (Story 1) are prerequisites; the allocation is the bridge.

**Independent Test**: For a synthetic two-industry, two-county example with known employment shares and known per-industry rents, the allocator produces expected per-county rents and the sum across counties (weighted by employment-hours) recovers the national total within tolerance. Counties with zero employment in a given industry receive zero allocation from that industry.

**Acceptance Scenarios**:

1. **Given** per-industry rents and per-county employment shares (from QCEW), **When** allocation runs, **Then** each county receives its proportional share and the weighted sum equals the national total within a small tolerance.
2. **Given** a county with no QCEW data for the tick year (e.g., a small county or a discontinued series), **When** allocation runs, **Then** the system applies a documented fallback (carry-forward from the most recent year available, or skip that county with a logged warning) — not a silent zero.

---

### User Story 5 - Orphaned tests from the partial migration removed (Priority: P3)

The 87+ tests in `tests/unit/economics/tick/test_system.py`, the per-county TVT tests in `tests/unit/economics/melt/`, the imperial-rent factory tests in `tests/unit/economics/test_factory.py` and `test_hydrator_mutants.py`, and the legacy collection-failure modules in `tests/integration/economics/` and `tests/integration/system/test_phase1_blueprint.py` reference the deleted per-worker `ImperialRentCalculator` API and the deleted `babylon.economics.reproduction` module. After the new pipeline is in place, these tests are removed (not skipped), with the test rationale captured in the commit message and the new behaviour exercised by tests written against the new pipeline.

**Why this priority**: Stale tests for deleted code provide no regression protection and pollute the failure surface. Removing them is the cleanup that makes the rest of the cleanup tractable. P3 because it follows the implementation rather than gating it.

**Independent Test**: After this story, `poetry run pytest tests/ -m "not ai"` (excluding any unrelated pre-existing debt) produces zero failures or collection errors traceable to the imperial-rent migration. The new pipeline is exercised by tests that import from the new module paths (`babylon.economics.tensor_hierarchy.production_chain_rent`, the new sources, and the new allocator) — not the deleted ones.

**Acceptance Scenarios**:

1. **Given** the new pipeline is wired in, **When** the test suite is collected and run, **Then** no test references `babylon.economics.melt.imperial_rent`, `babylon.economics.reproduction`, `MockImperialRentCalculator`, or `imperial_rent_calculator` as a `ServiceContainer` field.
2. **Given** the new pipeline is wired in, **When** tests are run, **Then** new unit tests cover: the new data sources (Stories 2-3), the allocator (Story 4), and the integration of the calculator into the per-tick step (Story 1) — including the edge cases listed below.

---

### Edge Cases

- A tick year for which BEA Use Table or QCEW data are missing entirely → the system surfaces this as a typed "no data for year Y" condition that the caller can decide to handle (e.g., carry-forward from the previous year, or fail the tick).
- The BEA inter-industry flow's industry list and the periphery-wage source's industry list do not align (different vintages, different sector definitions) → the system fails fast with a diagnostic naming the mismatching industries, rather than silently producing wrong numbers.
- A periphery wage ratio is exactly 1.0 (no wage gap) for an industry → that industry contributes zero rent, which propagates correctly through the allocator and shows up as zero rent for any county whose employment is concentrated in that industry alone.
- A county has zero employment in every industry that appears in QCEW for that year → the allocator either produces `phi_hour = 0` for that county with a "no employment data" log entry, or applies the documented carry-forward fallback.
- The Leontief decomposition produces a result that fails the Hawkins-Simon condition (non-viable economy) for a hypothetical year → the system raises a diagnostic exception identifying the year, rather than producing infinite or negative rents.
- A county's `phi_hour` would be physically implausible (e.g., > $1000/hour or < $-1000/hour after allocation) → the system writes the value but emits a warning so calibration drift is visible to the user.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace the no-op stub `_compute_imperial_rent` in the per-tick economic system with an implementation that invokes `ProductionChainRentCalculator` and writes a non-stub `phi_hour` to each `CountyEconomicState` it returns.
- **FR-002**: System MUST source the per-industry core/periphery wage ratios (`PeripheryLaborCoefficients`) from a named external dataset, with the data source object exposing a year-keyed query method and a metadata record identifying the publication, periphery definition, units, and base year.
- **FR-003**: System MUST source the per-industry final demand vector from the BEA Use Table (or equivalent BEA series), aligned with the same industry vector as the inter-industry flow source for the same year.
- **FR-004**: System MUST allocate per-industry imperial rent to counties using each county's share of national employment in that industry from the QCEW data already loaded into the SQLite reference database, normalising by the county's total employment-hours to produce a `phi_hour` value.
- **FR-005**: System MUST inject the calculator and its data sources into the per-tick system through `ServiceContainer` (the existing dependency-injection container), so the wiring is testable with mock sources and reproducible across runs.
- **FR-006**: System MUST validate that the BEA inter-industry flow industry list, the periphery-wage source industry list, and the final-demand source industry list are aligned for the tick year before invoking the calculator, and MUST fail fast with a diagnostic identifying any mismatch — not produce silently-wrong numbers.
- **FR-007**: System MUST handle the "no data for year Y" condition by surfacing a typed signal (an explicit no-data sentinel or a typed exception) rather than substituting a zero or synthetic value silently.
- **FR-008**: System MUST emit a structured warning when an allocated per-county `phi_hour` falls outside an empirically plausible range (calibration thresholds defined alongside the data-source metadata), without aborting the tick.
- **FR-009**: System MUST delete (not skip) the orphaned tests against the removed per-worker `ImperialRentCalculator` API and the removed `babylon.economics.reproduction` module, with the deletions justified in the implementing commit message and the previously-tested behaviours superseded by tests against the new pipeline.
- **FR-010**: System MUST add tests covering: the new data sources (existence, units, metadata), the allocator (allocation correctness, conservation under simple synthetic inputs, no-data fallback behaviour), and the per-tick integration (deterministic, non-zero, plausible distribution across counties).
- **FR-011**: System MUST preserve the existing public field `CountyEconomicState.phi_hour` and the existing reads of that field in `accumulation.py`, `savings_schedule.py`, and the graph bridge in `simulation.py`. The bridge to downstream consumers does not change shape, only that the upstream value becomes meaningful.
- **FR-012**: System MUST document, in the new module's README or docstrings, the chain of computation: BEA I-O → import-share decomposition → Leontief inverse → periphery wage coefficients → industry rent → QCEW employment-share allocation → per-county `phi_hour`, with one sentence per step naming the data source.

### Key Entities

- **PeripheryLaborCoefficientsSource (data source)**: Represents the origin of per-industry core/periphery wage ratios. Yields a vector aligned with the BEA industry list for a given year, plus metadata describing the publication, periphery definition, units, and base year. Existing protocol type already declared (`PeripheryLaborCoefficients`); concrete source implementation does not yet exist.
- **FinalDemandSource (data source)**: Represents the origin of the per-industry final demand vector for a given year. Yields a numpy vector aligned with the BEA industry list, plus units and source-year metadata. Existing protocol declared (`FinalDemandSource`); concrete source implementation does not yet exist.
- **IndustryToCountyAllocator**: Translates per-industry imperial rent values into per-county `phi_hour` values using QCEW employment shares. Produces one allocated rent per (industry, county) pair, then aggregates per county and normalises by total county employment-hours. Does not yet exist.
- **CountyEconomicState (existing, modified field semantics)**: Continues to carry a `phi_hour` field. After this feature, that field's value is the output of the new pipeline rather than a constant zero. Field shape and downstream consumers are unchanged.
- **ServiceContainer (existing, extended)**: Gains injectable references to `ProductionChainRentCalculator`, the two new data sources, and the allocator, so the pipeline can be assembled at scenario-load time and substituted with mocks in tests.
- **Per-tick imperial-rent step (existing, replaced)**: The `_compute_imperial_rent` method on the per-tick economic system. Its current no-op body is replaced by a call into the new pipeline. Method signature is preserved.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the feature lands, `poetry run pytest tests/ -m "not ai"` shows zero failures and zero collection errors traceable to the imperial-rent migration (specifically: no test references `babylon.economics.melt.imperial_rent`, `babylon.economics.reproduction`, or `MockImperialRentCalculator`).
- **SC-002**: Running a single tick of the Wayne County baseline scenario produces at least one county whose computed `phi_hour` differs from `0.0` by more than `1e-6`, and the resulting per-county distribution is bit-identical across two consecutive runs with the same seed.
- **SC-003**: The allocator's per-industry-to-county allocation, summed across all counties weighted by employment-hours, recovers the national per-industry rent total within `1.0%` for at least one tick year that has complete BEA + QCEW data.
- **SC-004**: For a tick year with complete BEA + QCEW data, the computed national-total imperial rent (`phi_hour` summed across counties × employment-hours) is within an order of magnitude of an independently published estimate (e.g., Hickel et al. 2022 — drain from the Global South of approximately $2.8T for 2015), with the choice of comparison estimate documented in the source-metadata record.
- **SC-005**: Test execution time for the new pipeline's unit tests stays under 5 seconds per file, so the new tests do not push the fast `mise run check` gate beyond its current budget.
- **SC-006**: The savings-and-accumulation downstream (`savings_schedule.py`, `accumulation.py`) shows non-trivial `phi_adjustment` values during a multi-tick run after this feature lands — i.e., at least one county-tick produces a `phi_adjustment > 0`.
- **SC-007**: Stakeholders inspecting the simulation's output map can see per-county imperial-rent values that vary across counties in a way that is explainable by their dominant industries' wage gaps and employment shares — i.e., the values are not uniformly the same, not uniformly zero, and the variation has economic meaning.

## Assumptions

- The BEA Input-Output table data is already loaded into the SQLite reference database (`marxist-data-3NF.sqlite`) and accessible through the existing `DefaultInterIndustryFlowSource` and `DBImportShareSource`. The current loaders cover the years that the simulation's tick range covers; if not, a separate ingestion task is a prerequisite to running the feature in production but is not in scope here.
- QCEW per-industry per-county employment data is already loaded into the same reference database via the existing pipelines used elsewhere in the simulation, and is accessible by industry NAICS code joined to county FIPS.
- The choice of periphery-wage data source (Hickel, ILO, Penn World Tables, or another) and its specific operationalisation (PPP-adjusted vs. nominal, manufacturing-only vs. all-sector, etc.) will be made by the implementer in consultation with the project's economic theory leads. The spec does not prescribe the source; it only requires that whichever source is chosen exposes the metadata in FR-002.
- The industry-to-county allocation strategy (employment-share-weighted) is treated as the default. If subsequent calibration shows it is too coarse (e.g., it ignores intra-industry wage stratification within a county), a follow-up spec can refine the allocation weight; this spec does not block on it.
- Backward compatibility with the previously-deleted per-worker calculator API is explicitly out of scope. Tests written against that API are removed, not preserved.
- The `Department` mapping (BEA industry → Department I/IIa/IIb/III) is optional input to the calculator and is not required for this feature; if absent, the calculator's existing behaviour for the missing-mapping case applies.
- The simulation's existing observers and the dashboard graph bridge already read `phi_hour` from `CountyEconomicState`; no changes to those consumers are required.
- The savings adjustment formula (`phi_adjustment = min(phi_hour · 2080 / wage, phi_cap)`) and its `phi_cap` parameter are unchanged by this feature; only the upstream `phi_hour` input value changes from a constant zero to a structurally-computed value.

## Dependencies

- Existing module: `babylon.economics.tensor_hierarchy.production_chain_rent` — provides the `ProductionChainRentCalculator` and the `ProductionChainDecomposer` used unchanged.
- Existing module: `babylon.economics.tensor_hierarchy.inter_industry` — provides `DefaultInterIndustryFlowSource` for the BEA I-O matrix.
- Existing module: `babylon.economics.tensor_hierarchy.production_chain_rent` — also provides `DBImportShareSource` for the import-share vector (already implemented and queries the `fact_bea_io_coefficient` table).
- Existing module: `babylon.economics.tensor_hierarchy.types` — provides the `PeripheryLaborCoefficients`, `DecomposedFlow`, and `ProductionChainRentResult` types used unchanged.
- Existing reference database: `data/sqlite/marxist-data-3NF.sqlite` — provides BEA I-O, BEA Use Table, and QCEW data.
- Existing module: `babylon.engine.services.ServiceContainer` — extended with new injectable fields for the calculator, the two new data sources, and the allocator.
- Existing per-tick system: `babylon.economics.tick.system.EconomicTickSystem._compute_imperial_rent` — its body is replaced; its signature is preserved.
- Existing downstream consumers: `babylon.economics.dynamics.savings_schedule`, `babylon.economics.dynamics.accumulation`, the graph bridge in `babylon.engine.simulation` — no changes; they continue to read `phi_hour` from `CountyEconomicState`.

## Out of Scope

- Implementing alternative imperial-rent frameworks (Emmanuel-Amin, dependency-theory variants). The Leontief framework is the chosen one for this feature.
- Refactoring the existing `DefaultImperialRentComputer` in `tensor_hierarchy/geographic_flow.py`, which computes per-CFS-area rent from `GeographicFlow`. That is a separate aggregation path with its own consumers; this feature does not touch it.
- Refactoring `CountyEconomicState`'s field shape. `phi_hour` stays as a single per-county scalar.
- Changing the savings-adjustment formula in `savings_schedule.py` or the `phi_cap` parameter.
- Loading new BEA or QCEW data into the reference database. The feature consumes whatever the existing loaders have produced.
- Choosing the specific periphery-wage data publication. The spec requires a documented source; the choice is made during implementation.
- Frontend visualisation changes. The graph bridge already exposes `phi_hour` to the UI; once values become non-zero, existing visualisations will reflect them automatically.

## Risks

- **Data alignment risk**: The BEA industry list, the periphery-wage source's industry list, and the QCEW NAICS codes may not line up perfectly across vintages and revisions. Mitigation: FR-006 requires fail-fast validation with diagnostic; concrete cross-walk tables may need to be added as a prerequisite.
- **Calibration risk**: The first end-to-end run may produce per-county `phi_hour` values that are physically implausible (e.g., orders of magnitude off published estimates). Mitigation: SC-004 sets an order-of-magnitude check against a published estimate, and FR-008 emits warnings on per-county outliers; calibration is tracked as follow-up work.
- **Periphery-wage source availability risk**: The chosen wage-ratio source may not cover every BEA industry or every tick year. Mitigation: FR-007 requires a typed no-data signal so callers can decide; the simulation may need to fall back to carry-forward or skip-tick behaviour for missing years.
- **Performance risk**: The full Leontief calculation runs at every tick, currently for every county. If the BEA I-O matrix is large (~70 industries) and the calculation is repeated 3,000+ times per tick, performance may suffer. Mitigation: the BEA matrix and Leontief inverse are year-keyed and naturally cacheable across ticks within a year; the implementation should cache them.
- **Test deletion risk**: Removing 87+ tests at once may obscure what they previously protected. Mitigation: FR-010 requires new tests covering the same behaviours, written against the new pipeline; the implementing commit message lists the deleted tests and their replacements.
