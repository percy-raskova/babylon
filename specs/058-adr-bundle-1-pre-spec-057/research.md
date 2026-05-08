# Phase 0 Research: ADR Bundle 1

**Status**: Complete
**Date**: 2026-05-08
**Branch**: `058-adr-bundle-1-pre-spec-057`

This document resolves the planner-determined questions from `plan.md`. It is the foundation for `data-model.md` and `contracts/` in Phase 1.

---

## R1 — Bundle ordering: validate FR-011's US5 → US3 → US1 → US2 → US4 sequence

**Decision**: Adopt FR-011's ordering with **one refinement**: split US3 into two commits (US3a = enums; US3b = defines) so the enums split lands before the defines split. Rationale: `defines.py` imports from `enums.py` (`from babylon.models.enums import ...`); if `enums.py` is split first, `defines.py`'s imports continue to resolve via the re-export `__init__.py` and the per-category `defines/` files can be authored knowing the new `enums/` shape. Splitting `defines.py` first would force a follow-up edit when `enums.py` splits.

**Final commit order** (7 commits):

1. `refactor(ooda): extract _compute_membership_overlap helper` (US5 — smallest blast radius)
2. `refactor(models): split enums.py into enums/ package` (US3a)
3. `refactor(config): split defines.py into defines/ package` (US3b)
4. `feat(core): add protocol_kit with DataSource, CachedSource, SourceRegistry` (US1 step 1 — pure-add, no migration)
5. `refactor(economics): migrate melt/ + gamma/ Default* classes to CachedSource[T]` (US1 step 2 — 10-class migration)
6. `refactor(economics): replace factory.py wiring with SourceRegistry.builtin_economics()` (US1 step 3)
7. `refactor(economics): decompose tick/system.py into focused subcomponents + type bea_to_department mapping` (US2 + US4 bundled — both touch `economics/` and ship together for atomic post-bundle baseline)

**Rationale**:
- Commit 1 has zero dependencies on anything in the bundle (smallest blast radius, smallest diff).
- Commits 2 and 3 must be in this order because `defines.py` imports from `enums.py`; the reverse would break commit 2's CI gate.
- Commit 4 has zero dependencies on commits 2/3 (`protocol_kit.py` imports only from `tensor.py` and stdlib); could ship between 1 and 2 if needed, but landing it after the splits keeps the "structural prep" → "new abstractions" → "migration" narrative clean.
- Commit 5 must follow 4 (depends on `CachedSource[T]`).
- Commit 6 must follow 5 (depends on the migrated classes existing).
- Commit 7 (US2 + US4 bundled): the tick/system decomposition does not depend on commits 4–6, but bundling US2 and US4 into one commit is correct because both touch `economics/` and the behavioral-fence test from FR-007 needs the typed `BEAMappings` to round-trip cleanly through `_compute_imperial_rent` (even though the latter is a stub — see commit-7 acceptance below).

**Alternatives considered**:
- *Land US4 before US2*: rejected because US4 is P2 (smaller benefit) and bundling with US2 lets the behavioral-fence test cover both at once.
- *Split US1 into 5 commits (one per `Default*` migration)*: rejected as too granular; the 10 classes share a common pattern and migrate as one logical unit.
- *Land US3 as one commit (enums + defines together)*: rejected because it would push the diff past easy-review size (~50 new files in one commit). Two commits (enums then defines) keep each diff under ~25 files.

---

## R2 — Import-graph clustering algorithm for `enums.py` and `defines.py`

**Decision**: Use **manual co-occurrence clustering** seeded by ADR-001's category sketches, validated by an `ast`-based co-import check.

**Algorithm**:

1. **Extract** every `from babylon.models.enums import …` statement across `src/` and `tests/` (`git grep -E "from babylon.models.enums import" src/ tests/ | sed 's/.*import //' | tr ',' '\n'`). For each call site, record the *set* of enum types it imports together (one set per source file).
2. **Build** a co-occurrence matrix: `M[i][j]` = number of files that import both enum `i` and enum `j`. Symbols that always appear together belong in the same sub-module.
3. **Compare** the resulting clusters against ADR-001's seed list:
   - `topology.py`: EdgeType, EdgeMode, TopologyType
   - `social.py`: SocialRole, ClassCharacter, MembershipRole, OrgType
   - `consciousness.py`: ConsciousnessTendency, IntensityLevel, ContradictionCharacter, ContradictionType
   - `territory.py`: TerritoryType, OperationalProfile, SectorType, DisplacementPriorityMode
   - `events.py`: EventType, ResolutionType, GameOutcome
   - `legal.py`: LegitimationClassification, LegalStatus, LegalStanding, DispossessionType, ExploitationMode
   - `community.py`: CommunityType, HyperedgeCategory
4. **Reconcile**: if the co-occurrence clustering produces materially different categories from the ADR-001 seed (e.g., consistently splits `social.py` into two clusters), prefer the empirical clustering and document the deviation in the relevant commit message.
5. **Per-file LOC check**: each candidate sub-module is sized (`wc -l` on the proposed slice of `enums.py`); if any sub-module exceeds 600 LOC, split further.

**Same algorithm for `defines.py`** seeded by ADR-001's defines sketch (`crisis.py`, `economy.py`, `consciousness.py`, `struggle.py`, `territory.py`, `ooda.py`, `state_apparatus.py`, `tunables.py`).

**Rationale**: Pure topological clustering (e.g., spectral graph partitioning on `co_import_graph`) is overkill for 45 enums and 42 `*Defines` classes. Co-occurrence clustering — a simple count-based signal — captures the "what gets imported together" semantics that matter for bytecode-cache locality (the actual benefit of the split per ADR-001's "Positive Consequences"). The ADR-001 seed lists are documented expert intuition; treating them as a *prior* and validating empirically is faster than building a clustering pipeline from scratch.

**Alternatives considered**:
- *Spectral graph partitioning*: rejected — over-engineered for 45/42 nodes; tooling complexity not justified.
- *Adopt ADR-001's seed lists verbatim*: rejected — Q1 clarification explicitly rejected pure prescription. Empirical validation against the 90/65 importer call sites catches drift between the ADR's expert intuition (May 2026) and the current code.
- *Cluster by file naming convention only*: rejected — `defines.py` has no internal naming convention to cluster on; many `*Defines` classes have ambiguous names (e.g., `EconomyDefines` vs `CreditDefines` vs `MonetaryDefines`).

---

## R3 — MRO inspection for `CachedSource[T]` migration

**Decision**: All 10 `Default*` classes in `melt/` (6) and `gamma/` (4) are MRO-clean for `CachedSource[T]` migration based on a `class … :` grep showing no multiple inheritance. Exact verification deferred to commit 5's pre-flight (`python -c "from babylon.economics.melt.melt_calculator import DefaultMELTCalculator; print(DefaultMELTCalculator.__mro__)"` for each class).

**Surveyed classes**:

| File | Class (likely name) | Single-base check |
|------|---------------------|-------------------|
| `melt/melt_calculator.py` | `DefaultMELTCalculator` | TBD at commit 5 |
| `melt/basket_visibility.py` | `DefaultBasketVisibility…` | TBD |
| `melt/class_position.py` | `DefaultClassPosition…` | TBD |
| `melt/rent_differential.py` | `DefaultRentDifferential…` | TBD |
| `melt/wealth_proxy.py` | `DefaultWealthProxy…` | TBD |
| `melt/unified_classifier.py` | `DefaultUnifiedClassifier` | TBD |
| `gamma/gamma_iii.py` | `DefaultGammaIII…` | TBD |
| `gamma/gamma_basket.py` | `DefaultGammaBasket…` | TBD |
| `gamma/gamma_import.py` | `DefaultGammaImport…` | TBD |
| `gamma/shadow_subsidy.py` | `DefaultShadowSubsidy…` | TBD |

**Fallback per the spec's Risks section**: if any class MRO-conflicts with `CachedSource[T]`, swap it for a different `Default*` class from `economics/credit/`, `economics/throughput/`, `economics/rent/`, or another package (28 candidates total). Document the swap in commit 5's message. SC-005 ("at least 10") gives slack for one or two swaps.

**Rationale**: ADR-002's Negative Consequences section states "most `Default*` classes inherit only from `object` today" — Babylon's `Protocol + Default*` pattern is conventionally single-inheritance because Protocols are structural (no runtime base required). MRO conflicts are unlikely but possible; the spec's mitigation is sufficient.

**Alternatives considered**:
- *Pre-inspect every class before commit 5*: rejected — adds a mid-stream survey commit with no acceptance criteria; the inspection happens naturally during the migration.
- *Use composition instead of inheritance for `CachedSource`*: rejected — would break the ADR-002 design (`CachedSource[T]` is explicitly a mixin/ABC, not a delegate); composition would require boilerplate `self._cached.get(...)` at every call site.

---

## R4 — `tick/system.py` method clustering for the 8 sub-modules

**Decision**: Cluster the 33 methods into 9 sub-modules (8 functional + the facade `__init__.py`), based on functional cohesion observed by reading method names and method order in the source file. Per-cluster LOC estimates (rough — based on line ranges from `grep -nE "    def "`):

| Sub-module | Methods (count) | LOC estimate | Notes |
|------------|-----------------|--------------|-------|
| `__init__.py` (facade) | `__init__`, `name`, `step` (3) | ~150 LOC | The 200-LOC SC-002 cap binds here |
| `initialization.py` | `_determine_year`, `_get_territory_fips`, `_bootstrap_county_states` (3) | ~80 LOC | Covers tick startup; `_write_hex_substrate` could go here OR in `county_distribution.py` (planner picks) |
| `national_parameters.py` | `_compute_national_params`, `_update_coefficients` (2) | ~85 LOC | Pure national-tier computation |
| `county_distribution.py` | `_compute_county_states`, `_derive_precarity`, `_write_hex_substrate` (3) | ~140 LOC | County-tier distribution from national parameters |
| `imperial_rent.py` | `_compute_imperial_rent` (1) | ~25 LOC | Stub today; spec-057 lands its real Leontief impl here. **Quarantine preserved** per FR-008 |
| `crisis.py` | `_check_crisis_triggers`, `_emit_crisis_event`, `_check_dispossession_cascade`, `_get_profit_rate` (4) | ~280 LOC | Largest cluster; if >400 LOC, split crisis ⇆ dispossession |
| `volume_layers.py` | `_compute_vol1_layer`, `_compute_vol1_county_state`, `_compute_circulation_layer`, `_compute_national_circulation_state`, `_compute_county_circulation_state`, `_compute_financial_layer`, `_compute_national_financial_state`, `_compute_county_financial_state`, `_assess_county_financial_crisis` (9) | ~385 LOC | At the 400-LOC cap; if exceeded, split `volume_layers.py` into `vol1.py`, `circulation.py`, `financial.py` (3 files instead of 1) |
| `tensor_helpers.py` | `_get_best_tensor_year`, `_get_county_profit_rate`, `_get_county_surplus` (3) | ~75 LOC | Cross-cluster lookup helpers |
| `bifurcation.py` | `_compute_bifurcation_risk`, `_emit_bifurcation_event` (2) | ~100 LOC | George Jackson Bifurcation per Constitution I.4 |
| `transitions.py` | `_simulate_transitions`, `_validate_distributions`, `_compute_tick_summary` (3) | ~200 LOC | End-of-tick wrap-up |

**LOC estimate sum**: ~1520 LOC of method bodies + ~150 LOC of facade = ~1670 LOC, leaving ~35 LOC of margin against the 1705-LOC original (consistent with light shared-import overhead from package re-exports).

**Risk**: `volume_layers.py` is at the 400-LOC ceiling. Mitigation: if the actual line count from extracting these 9 methods exceeds 400, split into `volume_layers/vol1.py`, `volume_layers/circulation.py`, `volume_layers/financial.py` (a sub-package within the sub-package — Python supports arbitrary nesting). The 400-LOC cap is per *file*, not per package.

**Per-cluster shared state**:
- `_get_territory_fips(graph)` is a pure helper consumed by ~5 other methods. Moves to `tick/system/_helpers.py` (private to the package).
- `_get_best_tensor_year`, `_get_county_profit_rate`, `_get_county_surplus` are also pure helpers — moved to `tensor_helpers.py` already (see table above).
- All cross-method state lives on the `WorldState` graph nodes (graph mutations), not on `self`. The 33 methods on `TickDynamicsSystem` rarely set `self.X = Y`; they mutate the graph and pass it to the next method. This is the ADR-006.3 enabling property: the methods are *almost* pure functions of `(graph, services, context)`.

**Rationale**: The clustering follows the natural functional boundaries already implicit in the source file's method ordering (initialization → national → county → imperial-rent → crisis → vol1 → circulation → financial → bifurcation → transitions → wrap-up). Splitting along these boundaries gives the smallest per-file LOC and minimizes inter-file coupling.

**Alternatives considered**:
- *Split by Marx Volume (Vol I, Vol II, Vol III)*: rejected — would put `_check_crisis_triggers` (Vol III) next to `_compute_imperial_rent` (Vol I) only if we squint; the existing method ordering already encodes the planner's mental model better than Volume taxonomy.
- *Single `economics.py` file with all 27 economic methods + `bifurcation.py` + `transitions.py`*: rejected — would be ~1300 LOC, far over the 400-LOC cap.

---

## R5 — Spec discrepancy reconciliation

The spec contains three numerical claims that don't match the actual `wc -l` / `grep -c` results from `dev` HEAD as of 2026-05-08. None affect the bundle's correctness; flagging here for transparency.

| Spec claim | Actual | Source command | Implication |
|------------|--------|----------------|-------------|
| `enums.py` has 25 enum types (Background; Key Entities) | **45 enum types** | `grep -cE "^class [A-Z]" src/babylon/models/enums.py` → 45 | Spec was conservative; 45 is more than the ADR-001 seed list of 25 names. The clustering pass (R2) discovers the additional 20; the 600-LOC cap still binds and is unaffected. |
| `defines.py` has 4157 lines (Background; FR-011 reference) | **4168 lines** | `wc -l src/babylon/config/defines.py` → 4168 | +11 lines of drift since the spec was authored. Well within rounding. |
| `economics/factory.py` has "seven `create_*_services()` functions" (Background) | **4 `create_*_services()` + 3 `load_*_series_from_db` helpers** | `grep -nE "^def [a-z]" src/babylon/economics/factory.py` → 7 total, 4 matching `create_*_services` | Spec mistakenly counted helpers as create-services. FR-006 ("replace … `create_*_services()` factory functions" plus "retaining the old function names as thin shims") still applies cleanly: 4 shims, not 7. The 3 `load_*` helpers can either: (a) move to a new `economics/_db_helpers.py` module, or (b) inline into the relevant `Default*` `_fetch` body now that those classes use `CachedSource[T]`. Planner picks at commit 6 time. |

**Action**: spec is *not* edited — these are clarifications, not changes to the contract. The minor numerical drift is normal between spec authorship (May 6) and plan generation (May 8).

---

## Phase 0 verdict

All planner questions resolved. Zero `NEEDS CLARIFICATION` markers remain in `plan.md`'s Technical Context. Ready for Phase 1 (data-model.md, contracts/, quickstart.md).
