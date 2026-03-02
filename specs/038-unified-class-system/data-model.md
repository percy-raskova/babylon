# Data Model: Unified Class System (038)

**Date**: 2026-03-01
**Spec**: `specs/038-unified-class-system/spec.md`
**Research**: `specs/038-unified-class-system/research.md`

---

## Entity Map

```
ClassSystemDefines (GameDefines sub-model)
  ├── trust_land_discount: float
  ├── documentation_exclusion_factor: float
  ├── equity_factor: float
  ├── base_class_solidarity: dict[str, dict[str, float]]  # 5x5 symmetric matrix
  └── get_base_solidarity(class_a, class_b) -> float

FiltrationResult (frozen Pydantic model)
  ├── original_wealth_percentile: float
  ├── effective_wealth_percentile: float
  ├── original_precarity: PrecarityStatus
  ├── effective_precarity: PrecarityStatus
  ├── applied_predicates: list[str]
  └── most_restrictive_community: CommunityType | None

UnifiedClassifier (Protocol + Default impl)
  ├── classify_with_filtration(wealth_pct, precarity, memberships, states) -> ClassPosition
  ├── apply_filtration(wealth_pct, precarity, memberships, states) -> FiltrationResult
  └── classify_dual_criteria(wealth_pct, precarity, memberships, states, v_produced, v_reproduction) -> DualCriteriaResult

DualCriteriaResult (frozen Pydantic model)
  ├── wealth_class: ClassPosition
  ├── accounting_class: ClassPosition
  ├── agrees: bool
  └── magnitude: float

RentDifferentialCalculator (Protocol + Default impl)
  ├── compute_differential(fips, nation, naics, year) -> float | NoDataSentinel
  └── compute_county_aggregate(fips, nation, year) -> float | NoDataSentinel

RentDifferentialResult (frozen Pydantic model)
  ├── fips: str
  ├── nation: CommunityType
  ├── year: int
  ├── differential: float
  ├── naics_count: int
  └── suppressed_count: int
```

---

## Entity Definitions

### 1. ClassSystemDefines

**Purpose**: Centralizes all tunable coefficients for the unified class system (FR-011).

**Location**: `src/babylon/config/defines.py` (new sub-model on GameDefines)

**Relationships**: Read by `UnifiedClassifier`, `calculate_solidarity_potential`, `CommunitySystem`

```python
class ClassSystemDefines(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Filtration parameters (FR-003)
    trust_land_discount: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Fed SCF / BIA: discount on effective wealth for FIRST_NATIONS "
                    "trust land property. 0.5 = 50% reduction in effective wealth percentile.",
    )
    documentation_exclusion_factor: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Game design: discount on effective wealth for UNDOCUMENTED households. "
                    "0.6 = 40% reduction. Reflects structural exclusion from formal "
                    "property/banking/labor protections.",
    )

    # Home ownership proxy (FR-005)
    equity_factor: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="Fed SCF: fraction of homeowners with meaningful equity. "
                    "Calibrated: 65% ownership * 0.6 = 39% ≈ 40% LA share.",
    )

    # Solidarity matrix (FR-006)
    base_class_solidarity: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "BOURGEOISIE": {
                "BOURGEOISIE": 0.70,
                "PETIT_BOURGEOISIE": 0.30,
                "LABOR_ARISTOCRACY": 0.10,
                "PROLETARIAT": 0.00,
                "LUMPENPROLETARIAT": 0.00,
            },
            "PETIT_BOURGEOISIE": {
                "PETIT_BOURGEOISIE": 0.50,
                "LABOR_ARISTOCRACY": 0.40,
                "PROLETARIAT": 0.15,
                "LUMPENPROLETARIAT": 0.05,
            },
            "LABOR_ARISTOCRACY": {
                "LABOR_ARISTOCRACY": 0.60,
                "PROLETARIAT": 0.30,
                "LUMPENPROLETARIAT": 0.10,
            },
            "PROLETARIAT": {
                "PROLETARIAT": 0.80,
                "LUMPENPROLETARIAT": 0.50,
            },
            "LUMPENPROLETARIAT": {
                "LUMPENPROLETARIAT": 0.60,
            },
        },
        description="Game design: symmetric 5x5 class-pair base solidarity matrix. "
                    "15 unique values (upper triangle including diagonal). "
                    "Class proximity yields higher base solidarity.",
    )

    def get_base_solidarity(self, class_a: str, class_b: str) -> float:
        """Symmetric lookup: get(A, B) == get(B, A). Returns 0.0 for unknown pairs."""
        if class_a in self.base_class_solidarity:
            inner = self.base_class_solidarity[class_a]
            if class_b in inner:
                return inner[class_b]
        if class_b in self.base_class_solidarity:
            inner = self.base_class_solidarity[class_b]
            if class_a in inner:
                return inner[class_a]
        return 0.0
```

**Validation Rules**:
- All float fields have `ge=0.0, le=1.0` bounds
- Matrix values checked at construction: each entry `ge=0.0` (negative base solidarity is not valid — that's the rent_differential_penalty's job)
- No cross-field validators needed (each field is independent)

---

### 2. FiltrationResult

**Purpose**: Output of applying community filtration predicates to classification inputs. Captures what changed and why.

**Location**: `src/babylon/economics/melt/filtration.py`

**Relationships**: Produced by `apply_filtration()`, consumed by `UnifiedClassifier`

```python
class FiltrationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_wealth_percentile: float = Field(ge=0.0, le=100.0)
    effective_wealth_percentile: float = Field(ge=0.0, le=100.0)
    original_precarity: PrecarityStatus
    effective_precarity: PrecarityStatus
    applied_predicates: list[str] = Field(
        default_factory=list,
        description="Names of filtration predicates that fired (e.g., 'FIRST_NATIONS_trust_land').",
    )
    most_restrictive_community: CommunityType | None = Field(
        default=None,
        description="CommunityType that produced the most restrictive effective result.",
    )
```

**Validation Rules**:
- `effective_wealth_percentile <= original_wealth_percentile` (filtration only reduces)
- `effective_precarity` can only be equal to or more severe than `original_precarity` (severity order: STABLE < PRECARIOUS < MARGINALLY_ATTACHED < EXCLUDED)

**State Transitions**: None (immutable result object, not stateful)

---

### 3. DualCriteriaResult

**Purpose**: Result of FR-002 dual-criteria validation — compares accounting criterion vs wealth percentile classification.

**Location**: `src/babylon/economics/melt/unified_classifier.py`

**Relationships**: Produced by `classify_dual_criteria()`, consumed by event bus (CALIBRATION_DISAGREEMENT)

```python
class DualCriteriaResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    wealth_class: ClassPosition
    accounting_class: ClassPosition
    agrees: bool = Field(
        description="True if both criteria produce the same ClassPosition.",
    )
    magnitude: float = Field(
        ge=0.0,
        description="Magnitude of disagreement in percentile-equivalent terms. "
                    "0.0 when agrees=True.",
    )
```

**Validation Rules**:
- `agrees` must be `True` iff `wealth_class == accounting_class`
- `magnitude == 0.0` when `agrees == True`

---

### 4. RentDifferentialResult

**Purpose**: Result of computing nation-specific Phi_hour differential for a county (FR-007).

**Location**: `src/babylon/economics/melt/rent_differential.py`

**Relationships**: Produced by `RentDifferentialCalculator`, consumed by solidarity potential computation

```python
class RentDifferentialResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    fips: str = Field(pattern=r"^\d{5}$")
    nation: CommunityType
    year: int = Field(ge=2010, le=2030)
    differential: float = Field(
        description="Employment-weighted Phi_differential. Positive = settler earns more.",
    )
    naics_count: int = Field(
        ge=0,
        description="Number of NAICS codes with valid data for both settler and nation.",
    )
    suppressed_count: int = Field(
        ge=0,
        description="Number of NAICS codes suppressed for this nation (NoDataSentinel).",
    )
```

**Validation Rules**:
- `naics_count + suppressed_count > 0` (at least one NAICS code attempted)
- `fips` matches 5-digit FIPS pattern

---

### 5. EventType Extension

**Purpose**: New event type for calibration disagreement logging (FR-002).

**Location**: `src/babylon/models/enums.py` (extend existing `EventType` enum)

```python
# Added to EventType enum:
CALIBRATION_DISAGREEMENT = "calibration_disagreement"
```

**Event Payload Schema**:
```python
{
    "agent_id": str,           # Entity/household identifier
    "tick": int,               # Current simulation tick
    "accounting_class": str,   # ClassPosition.name from V_produced vs V_reproduction
    "wealth_class": str,       # ClassPosition.name from wealth percentile
    "magnitude": float,        # Abs difference in percentile-equivalent terms
    "filtration_applied": bool, # Whether community filtration was active
}
```

---

## Relationship Diagram

```
GameDefines
  └── ClassSystemDefines
        ├── trust_land_discount ──────► FiltrationPredicates (FIRST_NATIONS)
        ├── documentation_exclusion_factor ─► FiltrationPredicates (UNDOCUMENTED)
        ├── equity_factor ────────────► WealthProxyCalculator (existing)
        └── base_class_solidarity ────► calculate_solidarity_potential() (existing formula)

CommunityState (existing, Feature 029)
  ├── reproduction_cost_modifier ──► FiltrationPredicates (DISABLED)
  └── rent_access_modifier ────────► (future: rent adjustment)

UnifiedClassifier
  ├── reads: ClassSystemDefines (filtration params)
  ├── reads: CommunityState[] (per-community modifiers)
  ├── wraps: DefaultClassPositionClassifier (existing)
  ├── produces: FiltrationResult
  ├── produces: DualCriteriaResult
  └── emits: CALIBRATION_DISAGREEMENT events

RentDifferentialCalculator
  ├── reads: ACS earnings data (external)
  ├── reads: QCEW employment data (for weighting)
  ├── produces: RentDifferentialResult | NoDataSentinel
  └── consumed by: calculate_solidarity_potential()

CommunitySystem.step() (existing, extended)
  ├── reads: ClassSystemDefines.base_class_solidarity
  ├── reads: RentDifferentialCalculator results
  ├── calls: calculate_solidarity_potential() with class-pair matrix lookup
  └── writes: solidarity_potential on SOLIDARITY edges
```

---

## File Layout

```
src/babylon/
├── config/
│   └── defines.py                    # +ClassSystemDefines sub-model
├── economics/
│   └── melt/
│       ├── class_position.py         # (existing — unchanged)
│       ├── filtration.py             # NEW: FiltrationResult, apply_filtration()
│       ├── unified_classifier.py     # NEW: UnifiedClassifier protocol + default impl
│       ├── rent_differential.py      # NEW: RentDifferentialCalculator + result type
│       ├── wealth_proxy.py           # (existing — unchanged)
│       └── __init__.py               # +export new modules
├── formulas/
│   └── community.py                  # (existing — calculate_solidarity_potential unchanged)
├── models/
│   └── enums.py                      # +CALIBRATION_DISAGREEMENT EventType
└── engine/
    └── systems/
        └── community.py              # (existing — extended to use class-pair matrix)

tests/
├── unit/
│   └── economics/
│       └── melt/
│           ├── test_filtration.py         # NEW
│           ├── test_unified_classifier.py # NEW
│           └── test_rent_differential.py  # NEW
└── constants.py                           # +ClassSystem test constant group
```
