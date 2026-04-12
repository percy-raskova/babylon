# Leontief Production Chain Imperial Rent: Claude Code Implementation Prompt

**Purpose**: Guide Claude Code through implementing production-chain-derived imperial rent (Φ) using Leontief I-O decomposition
**Target module**: `src/babylon/economics/tensor_hierarchy/production_chain_rent.py` (new)
**Dependencies**: Extends existing `inter_industry.py`, `types.py`, `protocols.py`, `validation.py`
**Date**: 2026-04-09

---

## Theoretical Motivation

The current imperial rent implementation (`babylon.economics.reproduction`) computes Φ as a simple wage differential: Φ = W_core - P_periphery. This captures the *magnitude* of unequal exchange but not its *mechanism* — the production chain. A Detroit autoworker's wages are subsidized not because they personally exploit anyone, but because the car they build embodies steel from Brazil, rubber from Indonesia, cobalt from Congo, and semiconductors from Malaysia, all purchased at prices reflecting periphery reproduction costs.

The Leontief inverse already propagates these supply chain dependencies. What we need is to decompose the I-O matrix into domestic and imported components, then compute how much periphery labor is embodied in each unit of domestic final demand.

**Core formula**:

```
A = A_d + A_m                         # Domestic + import components
L_d = (I - A_d)^{-1}                  # Domestic Leontief inverse
M = A_m @ L_d                         # Import content matrix
l_total_import = l_periphery @ M       # Periphery labor embodied per unit final demand
Φ_chain = l_total_import × (w_core/w_periphery - 1)  # Rent from wage differential
```

This replaces the lump-sum differential with an industry-decomposed production chain calculation.

---

## What Already Exists

Read these files before writing any code:

```
src/babylon/economics/tensor_hierarchy/inter_industry.py   # DefaultInterIndustryFlowSource, DefaultLeontiefComputer, DefaultDepartmentAggregator
src/babylon/economics/tensor_hierarchy/types.py            # InterIndustryFlow, LeontiefInverse, Department, IOTableType
src/babylon/economics/tensor_hierarchy/protocols.py        # LeontiefComputer protocol, ImperialRentComputer protocol
src/babylon/economics/tensor_hierarchy/validation.py       # validate_io_column_sums, validate_leontief_properties
src/babylon/economics/tensor_hierarchy/mappings/bea_to_department.toml  # BEA → Dept I/IIa/IIb/III
src/babylon/economics/reproduction.py                      # Current ImperialRentCalculator (simple differential)
src/babylon/economics/melt/imperial_rent.py                # TVT Φ_hour calculator (separate framework, coexists)
src/babylon/economics/adapters.py                          # SQLiteQCEWSource, InterpolatingBEASource, _cache_national_wages_bea
src/babylon/reference/schema.py                            # FactBEAIOCoefficient, DimBEAIndustry, BridgeNAICSBEA, FactBEANationalIndustry
```

Key facts about current state:

1. `DefaultInterIndustryFlowSource.get_direct_requirements(year)` loads the A matrix from `fact_bea_io_coefficient`. This is currently the TOTAL requirements matrix (domestic + imports combined). BEA publishes separate domestic and import use tables but we have not yet ingested the separated versions.

2. `DefaultLeontiefComputer` computes L = (I - A)^{-1} and `total_labor_coefficients(L, l_direct)`. Fully working.

3. `DefaultDepartmentAggregator` maps ~71 BEA industries → 4 Marxian departments via TOML. Fully working.

4. `_cache_national_wages_bea` table aggregates QCEW wages by BEA industry × year. This gives us the `l_direct` vector (hours/dollar) when combined with employment data.

5. Calibration targets exist: `babylon_ricci_final.csv` (GVC transfer flows by region/year, USD billions) and `babylon_hickel_final.csv` (annual drain estimates, ERDI, alpha coefficients 1960-2021).

---

## Implementation Plan

### Phase 1: Import Share Coefficients (data layer)

**Problem**: We don't have BEA's separate domestic/import use tables ingested. Rather than adding a new data ingestion pipeline (scope creep), derive import shares from existing BEA data.

**Approach**: BEA publishes import shares by commodity at the summary level. Create a static TOML mapping `import_shares_by_industry.toml` with import share coefficients per BEA industry code. These are the fraction of each industry's intermediate inputs that are imported. Source: BEA Import Matrix (Use of Imports), available at summary level.

```toml
# src/babylon/economics/tensor_hierarchy/mappings/import_shares_by_industry.toml
[import_shares]
# BEA_code = import_share (fraction of intermediate inputs that are imported)
# Source: BEA Use of Imports table, 2021 benchmark
# These are coefficients, not quantities — they transform slowly (α-smoothing candidates)
"211" = 0.35    # Oil and gas extraction (high import content)
"325" = 0.28    # Chemical products
"334" = 0.45    # Computer and electronic products (very high)
"3360A0" = 0.32 # Motor vehicles
# ... etc for all ~71 industries
```

**Type**: New frozen Pydantic model `ImportShareVector` in `types.py`:

```python
class ImportShareVector(BaseModel):
    """Import share of intermediate inputs by BEA industry.

    m_j ∈ [0, 1] is the fraction of industry j's intermediate inputs
    sourced from imports. Used to decompose A into A_d and A_m:
        A_d[i,j] = A[i,j] × (1 - m_j)
        A_m[i,j] = A[i,j] × m_j

    Source: BEA Import Matrix (Use of Imports), summary level.
    """
    model_config = ConfigDict(frozen=True)
    year: int
    industries: list[str]
    shares: np.ndarray  # shape (n,), each element ∈ [0, 1]
```

**Validation**: Add `validate_import_shares()` to validation.py — all values ∈ [0,1], vector length matches industry list.

**Source protocol**: Add `ImportShareSource` to protocols.py with `get_import_shares(year) -> ImportShareVector | NoDataSentinel`.

**Default implementation**: `TOMLImportShareSource` reads from the TOML file. Returns same shares for any year initially (benchmark year). Future: temporal interpolation from multiple benchmark years.

### Phase 2: Domestic Leontief and Import Content Matrix (computation layer)

New class `ProductionChainDecomposer` in `production_chain_rent.py`:

```python
class ProductionChainDecomposer:
    """Decomposes I-O matrix into domestic and import components.

    Given total A and import shares m:
        A_d[i,j] = A[i,j] × (1 - m_j)    # domestic direct requirements
        A_m[i,j] = A[i,j] × m_j           # imported direct requirements
        L_d = (I - A_d)^{-1}              # domestic Leontief inverse
        M = A_m @ L_d                      # import content matrix

    M[i,j] = total imported output of commodity i required (directly and
    indirectly through domestic supply chains) per unit of final demand
    for domestic industry j.
    """

    def decompose(self, flow: InterIndustryFlow, shares: ImportShareVector) -> DecomposedFlow:
        ...

    def import_content_matrix(self, decomposed: DecomposedFlow) -> np.ndarray:
        """M = A_m @ L_d — total import content per unit final demand."""
        ...
```

**New type** `DecomposedFlow` (frozen Pydantic):

```python
class DecomposedFlow(BaseModel):
    """Domestic/import decomposition of an InterIndustryFlow.

    Stores A_d, A_m, L_d as separate matrices. The total A = A_d + A_m
    is recoverable but never stored (derived, not primitive).
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    year: int
    industries: list[str]
    domestic_coefficients: np.ndarray    # A_d, shape (n, n)
    import_coefficients: np.ndarray      # A_m, shape (n, n)
    domestic_leontief: np.ndarray        # L_d = (I - A_d)^{-1}, shape (n, n)
```

**Validation**:
- A_d + A_m should reconstruct original A (within float tolerance)
- L_d must satisfy Leontief properties (non-negative, diagonal ≥ 1.0)
- Column sums of A_d must satisfy Hawkins-Simon (productive domestic economy)

**Conservation check**: The import content matrix M should have non-negative elements. Column sums of M represent total import intensity per unit of final demand — these should be economically plausible (typically 0.05–0.40 for US industries).

### Phase 3: Periphery Labor Coefficients (the wage gap)

This is where unequal exchange enters. We need a vector of "what this imported labor costs at periphery wages vs what it would cost at core wages."

**New type** `PeripheryLaborCoefficients` (frozen Pydantic):

```python
class PeripheryLaborCoefficients(BaseModel):
    """Labor cost differential between core and periphery by industry.

    wage_ratio_j = w_core_j / w_periphery_j for imported inputs to industry j.

    When wage_ratio > 1, the industry benefits from unequal exchange:
    it purchases inputs embodying periphery labor at periphery prices,
    which would cost more if produced domestically.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    year: int
    industries: list[str]
    wage_ratios: np.ndarray  # shape (n,), each > 0
```

**Source**: For MVP, derive from the Hickel ERDI (Exchange Rate Deviation Index) time series in `babylon_hickel_final.csv`. The ERDI column gives the aggregate distortion factor. Apply uniformly across industries initially, with a TODO for industry-specific ratios from Ricci's GVC data.

**Calibration target**: The aggregate Φ_chain summed across all industries × final demand should land within ±30% of Hickel's `annual_drain_usd_billions` for the corresponding year. This is directional validation, not curve-fitting.

### Phase 4: Production Chain Rent Calculator

The payoff. New class `ProductionChainRentCalculator`:

```python
class ProductionChainRentCalculator:
    """Computes imperial rent decomposed by production chain.

    For each industry j, the rent extracted through its supply chain:
        Φ_j = Σ_i M[i,j] × (wage_ratio_i - 1) × final_demand_j

    Total rent: Φ_total = Σ_j Φ_j

    This replaces the simple W - P_periphery differential with a
    structurally grounded calculation showing WHERE in the production
    chain rent is extracted.
    """

    def compute_industry_rents(
        self,
        decomposed: DecomposedFlow,
        periphery_coefficients: PeripheryLaborCoefficients,
        final_demand: np.ndarray,
    ) -> ProductionChainRentResult:
        ...

    def aggregate_to_departments(
        self,
        result: ProductionChainRentResult,
        mapping: dict[str, str],
    ) -> DepartmentRentResult:
        """Aggregate industry-level rents to 4 Marxian departments."""
        ...
```

**Result type** `ProductionChainRentResult`:

```python
class ProductionChainRentResult(BaseModel):
    """Imperial rent decomposed by industry production chain.

    phi_by_industry[j] = rent extracted through industry j's supply chain.
    import_content_by_industry[j] = total import intensity of industry j.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    year: int
    industries: list[str]
    phi_by_industry: np.ndarray       # shape (n,), rent per industry
    import_content_total: np.ndarray  # shape (n,), column sums of M
    total_phi: float                  # scalar sum
    phi_as_pct_gdp: float            # Φ / GDP for calibration comparison
```

### Phase 5: Validation and Calibration

**Unit tests** (pytest, in `tests/economics/tensor_hierarchy/test_production_chain_rent.py`):

1. **Decomposition round-trip**: A_d + A_m reconstructs A within tolerance
2. **Leontief properties on L_d**: non-negative, diagonal ≥ 1.0
3. **Zero import shares**: If all m_j = 0, Φ_chain = 0 (no imports, no rent)
4. **Uniform wage ratio**: If all ratios = 1.0, Φ_chain = 0 (equal exchange)
5. **Conservation**: Total import content is bounded [0, total_intermediate_inputs]
6. **Monotonicity**: Higher import shares → higher Φ_chain (ceteris paribus)
7. **Department aggregation**: Sum of department rents equals total rent

**Calibration test** (can be slow/integration):

1. Load real BEA I-O data for 2021
2. Apply TOML import shares
3. Apply Hickel ERDI for 2021 as uniform wage ratio
4. Compute Φ_chain
5. Compare against Hickel's `annual_drain_usd_billions` for 2021
6. Assert within ±30% (directional, not precision)

---

## Constraints and Anti-Patterns to Avoid

1. **No magic constants**: Import shares come from TOML with BEA source provenance. Wage ratios come from Hickel CSV. Every number traces to data.

2. **Primitives vs derived**: Store A_d, A_m, L_d (concrete matrices from data). Compute M, Φ_j, Φ_total as derived queries. Never persist derived quantities.

3. **No physics cosplay**: The Leontief notation earns its keep — L = (I-A)^{-1} has real matrix algebraic content (total requirements = geometric series of direct requirements). Don't add tensor indices that don't transform.

4. **Empirical/strategic separation**: Import shares and wage ratios are empirical (from data). How a player's organization responds to rent extraction is strategic (from player choice). This module is purely empirical.

5. **Coexistence with existing calculators**: This does NOT replace `reproduction.ImperialRentCalculator` or `melt.imperial_rent.ImperialRentCalculator`. All three frameworks coexist — they measure the same phenomenon from different theoretical angles. The production chain calculator provides the structural decomposition; the others provide aggregate metrics.

6. **Constitution compliance**: Check Article II (Theoretical Commitments) — imperial rent must have three components (UE, shadow, repro). The production chain calculator refines the UE component specifically. Shadow labor (Fortunati) and externalized reproduction (Meillassoux) remain separate concerns handled by the existing RentStructure.

---

## File Layout

```
src/babylon/economics/tensor_hierarchy/
├── production_chain_rent.py          # NEW: ProductionChainDecomposer, ProductionChainRentCalculator
├── types.py                          # MODIFY: Add ImportShareVector, DecomposedFlow, PeripheryLaborCoefficients, ProductionChainRentResult
├── protocols.py                      # MODIFY: Add ImportShareSource protocol, ProductionChainRentComputer protocol
├── validation.py                     # MODIFY: Add validate_import_shares(), validate_import_content()
├── inter_industry.py                 # READ ONLY: Existing Leontief machinery
├── mappings/
│   ├── bea_to_department.toml        # READ ONLY: Existing department mapping
│   └── import_shares_by_industry.toml  # NEW: BEA import shares
tests/economics/tensor_hierarchy/
└── test_production_chain_rent.py     # NEW: Unit + calibration tests
```

---

## Data Sources for Import Shares TOML

The import shares should be populated from BEA's "Use of Imports" table, available at:
https://apps.bea.gov/iTable/?reqid=150&step=2&isuri=1&categories=io

Specifically the "Import Matrix" at BEA summary level (~71 industries). For each industry j, the import share m_j = (imported intermediate inputs to j) / (total intermediate inputs to j).

If you cannot access BEA directly, use these approximate ranges as scaffolding and mark them with `# ESTIMATED — replace with BEA Import Matrix` comments:

- Extractive industries (mining, oil): 0.15–0.35
- Manufacturing (chemicals, electronics, vehicles): 0.25–0.50
- Services (finance, legal, healthcare): 0.02–0.10
- Agriculture: 0.10–0.20
- Construction: 0.10–0.20

The TOML must include `[metadata]` section with source attribution, benchmark year, and a `provenance` field for each estimate quality (EXACT, ESTIMATED, INTERPOLATED).

---

## Execution Order

1. Read all existing files listed in "What Already Exists"
2. Phase 1: Types and TOML mapping (data structures first)
3. Phase 2: Decomposition logic with validation
4. Phase 3: Periphery coefficients from Hickel CSV
5. Phase 4: Rent calculator
6. Phase 5: Tests (write tests alongside each phase, not after)

Run `pytest tests/economics/tensor_hierarchy/test_production_chain_rent.py -v` after each phase to confirm no regressions.
