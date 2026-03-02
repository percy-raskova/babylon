# Research: Unified Class System (038)

**Date**: 2026-03-01
**Spec**: `specs/038-unified-class-system/spec.md`
**Branch**: `038-unified-class-system`

---

## R-001: Classifier Architecture — Extend vs Wrap

**Context**: FR-012 requires backward compatibility: existing `ClassPositionClassifier` protocol and `DefaultClassPositionClassifier` must continue to work for callers that do not supply community membership data. FR-003 requires community filtration to modify classification inputs.

**Decision**: Decorator/Wrapper pattern — new `UnifiedClassifier` wraps existing `DefaultClassPositionClassifier`.

**Rationale**:
- The existing `ClassPositionClassifier` protocol (6 methods) remains valid as-is
- A new `UnifiedClassifier` class adds filtration-aware methods that pre-process inputs (apply community modifiers to wealth percentile and precarity) then delegate to the base classifier
- Callers that don't need filtration continue to use the base protocol unchanged
- Callers that need filtration instantiate the wrapper with community state

**Alternatives Rejected**:
- Extend `DefaultClassPositionClassifier` directly: Mixes concerns, violates SRP, forces all callers to handle `Optional[community_memberships]` even when they don't care
- Subclass `DefaultClassPositionClassifier`: Project uses Protocol pattern for DI, not inheritance

**Code Location**: `src/babylon/economics/melt/unified_classifier.py`

---

## R-002: Household vs SocialClass — Unit of Analysis

**Context**: The spec defines Household as the unit of class analysis. Currently `SocialClass` is the simulation's entity, and at county resolution these represent statistical class blocks, not individual households.

**Decision**: No new `Household` model. The unified classifier operates on function arguments (`wealth_percentile`, `precarity`, `community_memberships`), not entity references.

**Rationale**:
- Spec clarification (2026-02-25): "The spec is agnostic — works either way"
- Spec assumption A-006: At county resolution, "most disadvantaged membership" rule is adequate
- `SocialClass` already carries `community_memberships` (list) and `wealth` fields
- `ClassDistribution` (Feature 016) already models county-level class shares
- Adding a `Household` entity would require: WorldState schema change, graph bridge `to_graph()`/`from_graph()` changes, new `_node_type` discriminator, all 7+ systems to become aware of a new node type
- The classification functions are stateless — they take numeric inputs and return `ClassPosition`. They work identically whether called for an individual household or a statistical block.

**When to Revisit**: If/when the simulation moves to individual-level household agents (not current scope, explicitly noted in spec's "What This Spec Does NOT Include").

---

## R-003: CommunityType Name Mapping (INDIGENOUS vs FIRST_NATIONS)

**Context**: The spec uses "INDIGENOUS" throughout (e.g., "INDIGENOUS filtration", "INDIGENOUS trust_land_discount"). The codebase enum uses `CommunityType.FIRST_NATIONS`.

**Decision**: The spec's "INDIGENOUS" maps to `CommunityType.FIRST_NATIONS` in code. No new enum value.

**Rationale**:
- `CommunityType.FIRST_NATIONS` (value: `"first_nations"`) already exists in `src/babylon/models/enums.py:518`
- It is categorized as `HyperedgeCategory.CONTRADICTION_PAIR` (Category 1, marginalized side)
- The `COLONIAL_AXIS` contradiction axis already lists `FIRST_NATIONS` as a marginalized community alongside `NEW_AFRIKAN` and `CHICANO`
- Adding a separate `INDIGENOUS` value would create a taxonomy collision and violate the existing constitutional framework (II.7)

**Implementation Note**: All filtration code will use `CommunityType.FIRST_NATIONS`. Documentation and comments will note "INDIGENOUS filtration" as the conceptual label for this predicate.

---

## R-004: Filtration Module Location

**Context**: FR-003 defines four community-specific filtration predicates. Where should the filtration logic live?

**Decision**: New module `src/babylon/economics/melt/filtration.py`.

**Rationale**:
- Filtration modifies classification inputs (wealth percentile, precarity status) before classification
- Classification lives in `economics/melt/class_position.py`
- Filtration is a pre-processing step for classification — same subsystem boundary
- The `CommunityState.reproduction_cost_modifier` and `rent_access_modifier` are community-side state (read-only inputs to filtration); the filtration logic reads these values and produces modified classification inputs
- Follows existing package convention: `economics/melt/` = classification subsystem

**Alternatives Rejected**:
- `formulas/filtration.py`: Filtration is not a pure stateless formula — it reads community state and applies per-community-type rules. Project convention is pure formulas in `formulas/`, stateful/Protocol-based calculators in `economics/`.
- `models/entities/community.py`: Filtration is a computation, not a data model. CommunityState stores the modifiers; filtration applies them.

---

## R-005: base_class_solidarity Matrix in GameDefines

**Context**: FR-006 specifies a symmetric 5x5 class-pair matrix (15 unique values) for `base_class_solidarity`. The clarification (2026-03-01) confirms: "Symmetric 5x5 class-pair matrix. Two proletarians share higher base solidarity than a bourgeois-proletariat pair."

**Decision**: New `ClassSystemDefines` sub-model in GameDefines with a nested `dict[str, dict[str, float]]` for the upper triangle, plus a `get_base_solidarity(class_a, class_b) -> float` accessor method that handles symmetry.

**Rationale**:
- 15 unique values = upper triangle of 5x5 matrix including diagonal (5+4+3+2+1 = 15)
- Nested dict is YAML-serializable (for `defines.yaml`) and human-readable
- Accessor handles symmetry: `get(A, B) == get(B, A)`
- ClassPosition enum `.name` property provides the string keys
- Follows the existing pattern of accessor methods in GameDefines sub-models (e.g., `InfraTerrainDefines.get_initial_stock`, `OODADefines.get_base_cost`)

**Default Values** (game design, tunable — theoretical basis in parentheses):

| Pair | Value | Basis |
|------|-------|-------|
| PROLETARIAT-PROLETARIAT | 0.80 | Shared exploitation, shared relation to production |
| PROLETARIAT-LUMPENPROLETARIAT | 0.50 | Shared poverty but different labor market position |
| LUMPENPROLETARIAT-LUMPENPROLETARIAT | 0.60 | Shared exclusion, mutual aid networks |
| LABOR_ARISTOCRACY-LABOR_ARISTOCRACY | 0.60 | Shared property but competitive (housing market) |
| LABOR_ARISTOCRACY-PROLETARIAT | 0.30 | Material interests diverge (LA benefits from imperial rent) |
| LABOR_ARISTOCRACY-LUMPENPROLETARIAT | 0.10 | Maximum structural distance within non-bourgeois classes |
| PETIT_BOURGEOISIE-PETIT_BOURGEOISIE | 0.50 | Small capital solidarity (chambers of commerce) |
| PETIT_BOURGEOISIE-LABOR_ARISTOCRACY | 0.40 | Aspiration alignment, shared property ideology |
| PETIT_BOURGEOISIE-PROLETARIAT | 0.15 | Some populist alignment possible but weak |
| PETIT_BOURGEOISIE-LUMPENPROLETARIAT | 0.05 | Almost no structural basis |
| BOURGEOISIE-BOURGEOISIE | 0.70 | Class solidarity of capital (Davos, industry groups) |
| BOURGEOISIE-PETIT_BOURGEOISIE | 0.30 | Extraction relationship but shared property ideology |
| BOURGEOISIE-LABOR_ARISTOCRACY | 0.10 | Bribery relationship via imperial rent distribution |
| BOURGEOISIE-PROLETARIAT | 0.00 | Fundamental antagonism (primary contradiction) |
| BOURGEOISIE-LUMPENPROLETARIAT | 0.00 | No structural basis (reserve army, not solidarity) |

---

## R-006: CalibrationLog Implementation

**Context**: FR-002 requires logging disagreements between accounting criterion and wealth percentile classification, recording: household identifier, tick, accounting classification, wealth classification, magnitude of disagreement.

**Decision**: Use the existing event bus pattern. Emit `CALIBRATION_DISAGREEMENT` events that observers can capture.

**Rationale**:
- The project has `EventBus` with `EventType` enum and publish/subscribe pattern
- Adding a new `EventType.CALIBRATION_DISAGREEMENT` follows the existing pattern (12+ event types already exist)
- Events are captured by `SessionRecorder` (black box debugging) and any other observer
- No new persistence layer needed — observers handle storage
- Consistent with II.5 (AI Observes, Never Controls): disagreements are state observations

**Event Payload Shape**:
```python
{
    "agent_id": str,           # Household/agent identifier
    "tick": int,
    "accounting_class": str,   # ClassPosition.name from V_produced vs V_reproduction
    "wealth_class": str,       # ClassPosition.name from wealth percentile
    "magnitude": float,        # Abs difference in percentile-equivalent terms
}
```

**Alternatives Rejected**:
- New `CalibrationLog` Pydantic model with list accumulation: Requires WorldState schema change or `context.persistent_data` usage. Overly complex for a logging concern.
- Python `logging` module: Too informal, doesn't integrate with simulation state or observers.

---

## R-007: Rent Differential Module Structure

**Context**: FR-007 requires nation-specific Phi_hour differentials from ACS median earnings by race x NAICS at county level. Suppressed data → `NoDataSentinel`.

**Decision**: New module `src/babylon/economics/melt/rent_differential.py` following Protocol + Default impl pattern.

**Rationale**:
- Rent differential is a measurement derived from ACS data, not simulation dynamics
- Lives alongside `imperial_rent.py` in `economics/melt/` (both compute Phi-related quantities)
- Protocol enables testing with mock ACS data
- Returns `NoDataSentinel` for suppressed cells (follows `tensor.py` pattern from MEMORY.md)
- Employment-weighted county aggregation follows existing QCEW weighting patterns in `economics/throughput/`

**Protocol Shape**:
```python
class RentDifferentialCalculator(Protocol):
    def compute_differential(
        self, fips: str, nation: CommunityType, naics: str, year: int,
    ) -> float | NoDataSentinel: ...

    def compute_county_aggregate(
        self, fips: str, nation: CommunityType, year: int,
    ) -> float | NoDataSentinel: ...
```

---

## R-008: Integration Points with Engine Systems

**Context**: Where does the unified class system connect to the existing engine?

**Decision**: Two integration points, both in CommunitySystem:

1. **CommunitySystem.step()** — After hypergraph construction, compute `solidarity_potential` for each SOLIDARITY edge pair using the new class-pair matrix lookup for `base_class_solidarity`. The existing `calculate_solidarity_potential` formula signature already matches FR-006; only the `base_solidarity` argument source changes (from a flat constant to a matrix lookup).

2. **EventType.CALIBRATION_DISAGREEMENT** — New event type emitted when dual-criteria validation detects disagreement (R-006). Captured by existing observers.

**What Does NOT Change**:
- `SolidaritySystem`: Continues transmitting consciousness via SOLIDARITY edges. It reads `solidarity_strength` from edges; the unified class system produces/modifies that attribute upstream.
- `ConsciousnessSystem`: Continues ideology drift. No interaction with class position.
- Bifurcation analysis (`bifurcation/analysis.py`): Continues consuming SOLIDARITY edges and community overlap. The improved solidarity potential with class-pair matrix will be visible as better edge weights.
- `LifecycleSystem`: DPD' integration (FR-008) will read class position from the unified classifier when computing inheritance flows. This is a new call site, not a modification to existing logic.

**Timing**: The unified classifier runs at data hydration time (county setup) and optionally per-tick when crisis events modify wealth. The solidarity potential update runs during `CommunitySystem.step()`, which executes after economic systems in the tick order.

---

## R-009: Filtration Predicate Default Values

**Context**: FR-003 specifies four filtration predicates. The spec provides default values for two. Research validates completeness.

| Parameter | Default | Source | Spec Reference |
|-----------|---------|--------|----------------|
| `trust_land_discount` | 0.5 | BIA trust land property regime analysis | FR-003, spec body |
| `documentation_exclusion_factor` | 0.6 | Structural exclusion from formal banking/property | FR-003, Clarification 2026-03-01 |
| `incarcerated_precarity_override` | `EXCLUDED` | Total labor market severance | FR-003 |
| `equity_factor` | 0.6 | Fed SCF calibration (65% ownership × 0.6 ≈ 40% LA) | FR-005, wealth_proxy.py |
| `community_bonus` | 0.1 | Already in CommunityDefines | FR-006, defines.py:1423 |
| `rent_differential_penalty` | 0.05 | Already in CommunityDefines | FR-006, defines.py:1428 |

**Note**: `reproduction_cost_modifier` for DISABLED filtration is already on `CommunityState` (default 1.0). The filtration predicate reads this value — no new default needed in GameDefines. The modifier is set per-community-state instance, reflecting specific disability accommodation costs.

---

## R-010: Existing Formula Reuse Assessment

| Requirement | Existing Code | Reuse Plan |
|-------------|---------------|------------|
| FR-001 (Household Classification) | `DefaultClassPositionClassifier.classify_by_wealth_and_precarity()` | Direct reuse — wrap with filtration |
| FR-003 (Community Filtration) | `CommunityState.reproduction_cost_modifier`, `rent_access_modifier` | Read these as filtration inputs |
| FR-005 (Home Ownership LA Proxy) | `DefaultWealthProxyCalculator.estimate_la_share()` | Direct reuse — already implements `LA = ownership × equity_factor` |
| FR-006 (Solidarity Potential) | `calculate_solidarity_potential()` in `formulas/community.py` | Direct reuse — only change: `base_solidarity` arg comes from matrix lookup instead of flat constant |
| FR-007 (Rent Differential) | `DefaultImperialRentCalculator.compute_phi_hour()` | New — compute differential between settler and nation-specific Phi, not per-individual Phi |
| FR-008 (DPD' Inheritance) | `DefaultInheritanceCalculator` in `economics/lifecycle/` | Extend — add class-position-differentiated inheritance amounts |
| FR-010 (Crisis Dispossession) | `DispossessionDefines` in GameDefines | Extend — add community-specific dispossession rate modifiers |

**DRY Assessment**: 5 of 7 core requirements can reuse existing code. 2 require new modules. 0 require rewriting existing code.

---

## R-011: WealthProxyCalculator Equity Factor Source

**Context**: FR-005 requires `equity_factor` in GameDefines (per FR-011). The existing `DefaultWealthProxyCalculator` has `EQUITY_FACTOR = 0.6` as a hardcoded module constant. This creates duplication with `ClassSystemDefines.equity_factor` and violates both FR-011 ("all coefficients in GameDefines, not hardcoded") and constitution III.1 (No Magic Constants).

**Decision**: Update `DefaultWealthProxyCalculator` to accept `equity_factor` from `ClassSystemDefines` via constructor injection, removing the hardcoded constant. Also enable `trust_land_discount` application to reservation-county home ownership rates.

**Rationale**:
- FR-011 explicitly requires all tunable parameters in GameDefines
- Constitution III.1 requires all numbers trace to data sources or GameDefines
- The hardcoded `EQUITY_FACTOR = 0.6` duplicates `ClassSystemDefines.equity_factor`
- Constructor injection follows the existing DI pattern (Protocol + Default impl)
- Reservation-county LA proxy modification requires `trust_land_discount` from `ClassSystemDefines`
- `wealth_proxy.py` moves from UNCHANGED to EXTENDED (~10 lines modified)

**Alternatives Rejected**:
- Leave hardcoded and document as tech debt: Violates FR-011 and III.1, creates silent duplication risk
- Remove equity_factor from ClassSystemDefines: Would leave the parameter undiscoverable and non-tunable
