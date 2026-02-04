# Pre-Implementation Requirements Quality Checklist

**Feature**: 015-gamma-visibility-tensor
**Created**: 2026-02-04
**Scope**: Comprehensive (Formula/Math, Data Integration, Validation Ranges)
**Timing**: Pre-Implementation Review
**Priority**: All High-Priority Gates

## CHK001-CHK010: Formula & Math Correctness

### CHK001: γ_III Formula Completeness
- [ ] Formula `γ_III = L_paid_care / (L_paid_care + L_unpaid_care)` is explicitly stated
- [ ] Denominator cannot be zero (both hours cannot be zero simultaneously)
- [ ] Division by zero handling is specified (NoDataSentinel or explicit error)

**Source**: FR-001, data-model.md:23

### CHK002: Fortunati Exploitation Rate Formula
- [ ] Formula `e = (1 - γ_III) / γ_III` is documented
- [ ] Edge case: γ_III = 0 produces infinite exploitation (handled?)
- [ ] Expected range [2.0, 3.0] documented for validation

**Source**: FR-001, research.md:200-205

### CHK003: γ_import Formula Completeness
- [ ] Formula `γ_import = Σ(import_share[i] × 1/ERDI[i])` is stated
- [ ] Import shares must sum to 1.0 ± tolerance (validation rule)
- [ ] ERDI > 0 constraint is enforced (no division by zero)

**Source**: FR-003, data-model.md:73

### CHK004: γ_basket Formula Correctness
- [ ] Formula `γ_basket = 1 / (α/γ_import + (1-α))` is documented
- [ ] Edge case α = 0 produces γ_basket = 1.0 (all domestic)
- [ ] Edge case α = 1 produces γ_basket = γ_import (all imports)
- [ ] Constraint γ_basket ≥ γ_import is validated

**Source**: FR-005, data-model.md:127-155

### CHK005: Shadow Subsidy Φ_III Formula
- [ ] Formula `Φ_III = (1 - γ_III) × L_unpaid × τ` is stated
- [ ] τ (MELT) dependency is explicit
- [ ] Labor-hours fallback when MELT unavailable is specified

**Source**: FR-006, data-model.md:163-208

### CHK006: Shadow Subsidy Φ_imperial Formula
- [ ] Formula `Φ_imperial = (1 - γ_basket) × Consumption` is stated
- [ ] Consumption data source (BEA) is specified
- [ ] Output in dollars (not labor-hours)

**Source**: FR-008, data-model.md:174

### CHK007: Harmonic Mean Justification
- [ ] γ_basket uses harmonic mean, not arithmetic mean
- [ ] Rationale: visibility is intensive property under aggregation
- [ ] Warning if γ_basket > 1.0 (should be impossible)

**Source**: research.md:136-155

### CHK008: Care Fraction Coefficients
- [ ] NAICS 61 (Education) care fraction ~0.60 documented
- [ ] NAICS 62 (Healthcare) care fraction ~0.30 documented
- [ ] NAICS 624 (Social Assistance) care fraction ~0.80 documented
- [ ] NAICS 814 (Private Households) care fraction ~1.00 documented
- [ ] Coefficients have source citations

**Source**: research.md:80-96

### CHK009: Employment to Hours Conversion
- [ ] Formula `annual_hours = employment × 2080` documented
- [ ] 2080 = 40 hours/week × 52 weeks (FTE assumption)
- [ ] Part-time worker handling specified (or explicitly out of scope)

**Source**: research.md:65-67

### CHK010: Aggregation Rules
- [ ] γ values aggregate via weighted-average (intensive property)
- [ ] Formula: `γ_agg = Σ(weight × γ) / Σ(weight)`
- [ ] Warning: γ values should NOT be summed directly

**Source**: quickstart.md:254-258

---

## CHK011-CHK020: Data Integration Requirements

### CHK011: ATUS Data Source
- [ ] Unpaid care hours from `ATUSHouseholdSummary.unpaid_care_hours_weekly`
- [ ] Annual conversion: `weekly × 52 × US_households`
- [ ] US_households estimate (~130M) is sourced/documented

**Source**: FR-002, research.md:36-43

### CHK012: QCEW Data Source
- [ ] Paid care hours from QCEW employment data
- [ ] NAICS codes explicitly listed: 61, 62, 624, 814
- [ ] Double-counting handled (624 is subset of 62)

**Source**: FR-002, research.md:44-59

### CHK013: Penn World Tables ERDI
- [ ] MVP hardcoded values documented with source
- [ ] Reference year (2019) specified
- [ ] Top 10 trading partners covered: CHN, MEX, CAN, VNM, DEU, JPN, KOR, IND, TWN
- [ ] Fallback values: Core=1.0, Periphery=2.0

**Source**: FR-003, data-model.md:246-263

### CHK014: Import Share Data
- [ ] Import share source specified (Census Bureau or equivalent)
- [ ] Shares sum to 1.0 validation
- [ ] "Other" category handling for unlisted countries

**Source**: FR-003, research.md:100-117

### CHK015: MELT Integration
- [ ] Reuses existing `DefaultMELTCalculator` from Feature 013
- [ ] τ ≈ $65/hour for 2022 (approximate expectation)
- [ ] NoDataSentinel handling when MELT unavailable

**Source**: FR-006, quickstart.md:124-132

### CHK016: BEA Consumption Data
- [ ] Consumption data source (BEA PCE) specified
- [ ] US consumption ~$15T/year (order of magnitude)
- [ ] Year alignment with other data sources

**Source**: FR-008

### CHK017: NoDataSentinel Protocol
- [ ] All calculators return `GammaXXX | NoDataSentinel`
- [ ] NoDataSentinel includes `reason` field
- [ ] Pattern matches `babylon.economics.tensor` existing implementation

**Source**: quickstart.md:264-266, plan.md:234-245

### CHK018: Data Year Constraints
- [ ] γ_III requires year ≥ 2003 (ATUS availability)
- [ ] ERDI data year documented (Penn World Tables 10.01 = 2019)
- [ ] Year mismatch handling (e.g., 2022 request vs 2019 ERDI data)

**Source**: data-model.md:33, 83, 239

### CHK019: MVP vs Full Data Mode
- [ ] `is_mvp` flag on GammaImport indicates hardcoded values
- [ ] `is_estimated` flag on GammaIII indicates estimated values
- [ ] Future enhancement path documented (FE-002: PennWorldTablesLoader)

**Source**: data-model.md:93-95, 46-48

### CHK020: Existing Infrastructure Reuse
- [ ] ATUS: `babylon.data.atus.MockReproductionLoader`
- [ ] QCEW: `babylon.economics.throughput.SQLiteQCEWCountyNAICSSource`
- [ ] MELT: `babylon.economics.melt.DefaultMELTCalculator`
- [ ] No duplicate data loaders created

**Source**: research.md:226-231

---

## CHK021-CHK030: Validation Ranges & Error Handling

### CHK021: γ_III Expected Range
- [ ] Expected: [0.20, 0.40]
- [ ] Warning: [0.10, 0.50]
- [ ] Fail: < 0 or > 1

**Source**: data-model.md:286

### CHK022: γ_import Expected Range
- [ ] Expected: [0.40, 0.70]
- [ ] Warning: [0.30, 0.80]
- [ ] Fail: ≤ 0 or > 1

**Source**: data-model.md:287

### CHK023: γ_basket Expected Range
- [ ] Expected: [0.60, 0.85]
- [ ] Warning: [0.40, 0.95]
- [ ] Fail: ≤ 0 or > 1

**Source**: data-model.md:288

### CHK024: Shadow Subsidy Φ_III Magnitude
- [ ] Expected: $1.5-3.5 trillion/year
- [ ] Warning: $0.5-5.0 trillion/year
- [ ] Fail: < 0

**Source**: data-model.md:289

### CHK025: Shadow Subsidy Φ_imperial Magnitude
- [ ] Expected: $1.0-4.0 trillion/year
- [ ] Warning: $0.5-6.0 trillion/year
- [ ] Fail: < 0

**Source**: data-model.md:290

### CHK026: Fortunati Exploitation Rate Range
- [ ] Expected: [2.0, 3.0]
- [ ] Computed from γ_III: e = (1 - γ)/γ
- [ ] γ_III = 0.33 → e ≈ 2.0 (validated)

**Source**: research.md:197-205

### CHK027: ERDI Value Constraints
- [ ] ERDI > 0 always (positive)
- [ ] Core countries: ERDI ≈ 1.0
- [ ] Periphery countries: ERDI > 1.0 (typically 1.5-3.0)
- [ ] No country should have ERDI < 0.5 (warning)

**Source**: data-model.md:221-244

### CHK028: Import Share Validation
- [ ] Sum of shares = 1.0 ± 0.01 tolerance
- [ ] Individual shares ∈ [0, 1]
- [ ] No negative shares

**Source**: data-model.md:99

### CHK029: Division by Zero Prevention
- [ ] γ_III: denominator = paid + unpaid > 0
- [ ] Fortunati: γ_III > 0 required
- [ ] γ_import: ERDI > 0 for all countries
- [ ] γ_basket: γ_import > 0 required

**Source**: Derived from formulas

### CHK030: Validation Function Signatures
- [ ] `validate_gamma_iii(value: float) -> tuple[bool, str | None]`
- [ ] `validate_gamma_import(value: float) -> tuple[bool, str | None]`
- [ ] `validate_gamma_basket(value: float) -> tuple[bool, str | None]`
- [ ] Return: (valid, warning_message)

**Source**: quickstart.md:163-184

---

## CHK031-CHK040: Constitution Compliance

### CHK031: No Magic Constants (III.1)
- [ ] ERDI values trace to Penn World Tables
- [ ] Care fractions trace to documented sources
- [ ] No unexplained numeric literals in code

**Source**: plan.md:39

### CHK032: Data Source Traceability (III.4)
- [ ] ATUS source documented
- [ ] QCEW source documented
- [ ] Penn World Tables source documented
- [ ] BEA source documented (for consumption)

**Source**: plan.md:40

### CHK033: Constants Without Data Sources (VII.6)
- [ ] MVP ERDI hardcoded with explicit data source reference
- [ ] Care fraction coefficients have literature citations
- [ ] FTE hours (2080) derivation documented

**Source**: plan.md:41

### CHK034: Primitives vs Derived (II.2)
- [ ] γ is derived from labor-hour primitives
- [ ] Labor hours are primitives (from ATUS, QCEW)
- [ ] Shadow subsidies are derived from γ values

**Source**: plan.md:36

### CHK035: State is Data, Engine is Transformation (II.6)
- [ ] All γ types are frozen Pydantic models
- [ ] Calculators are stateless transformations
- [ ] No mutable state in Calculator classes

**Source**: plan.md:38

### CHK036: Imperial Rent Alignment (I.2)
- [ ] γ measures visibility of labor transfer mechanisms
- [ ] Shadow subsidies quantify invisible value transfers
- [ ] Consistent with imperial rent framework

**Source**: plan.md:33

### CHK037: Department III Alignment (I.5)
- [ ] γ_III implements Fortunati visibility coefficient
- [ ] Reproductive labor properly categorized
- [ ] Care sector definition matches Department III scope

**Source**: plan.md:34

### CHK038: No Modification of Existing melt/
- [ ] `melt/basket_visibility.py` is NOT modified
- [ ] New gamma/ package is created separately
- [ ] Class position calculation remains in melt/

**Source**: research.md:143-146, 210-224

### CHK039: NetworkX Not Required (II.3)
- [ ] No graph topology changes in gamma module
- [ ] Pure calculation, no network structure
- [ ] N/A for NetworkX requirements

**Source**: plan.md:37

### CHK040: AI Observes, Never Controls (II.5)
- [ ] Calculation module only, no AI interaction
- [ ] No LLM calls in gamma calculators
- [ ] Deterministic computation

**Source**: plan.md:35

---

## CHK041-CHK050: Edge Cases & Boundary Conditions

### CHK041: Zero Unpaid Care Hours
- [ ] If unpaid_care_hours = 0: γ_III = 1.0 (all care is paid)
- [ ] This is theoretically possible but unlikely
- [ ] Should trigger warning, not error

**Source**: Derived from formula

### CHK042: Zero Paid Care Hours
- [ ] If paid_care_hours = 0: γ_III = 0.0 (all care is unpaid)
- [ ] This represents pre-commodification society
- [ ] Fortunati exploitation = infinite (handle!)

**Source**: Derived from formula

### CHK043: Zero Total Care Hours
- [ ] If both paid = 0 AND unpaid = 0: division by zero
- [ ] Return NoDataSentinel with reason
- [ ] This should never happen with real ATUS data

**Source**: Derived from formula

### CHK044: α = 0 (No Imports)
- [ ] γ_basket = 1.0 (fully domestic, fully visible)
- [ ] Formula: 1 / (0/γ_import + 1) = 1.0
- [ ] Valid edge case, no error

**Source**: data-model.md:150

### CHK045: α = 1 (All Imports)
- [ ] γ_basket = γ_import
- [ ] Formula: 1 / (1/γ_import + 0) = γ_import
- [ ] Valid edge case, no error

**Source**: data-model.md:151

### CHK046: γ_import = 0 (Impossible)
- [ ] Would require all ERDI = ∞
- [ ] Model constraint: ERDI > 0 always
- [ ] Division check in γ_basket formula

**Source**: data-model.md:101

### CHK047: MELT Unavailable
- [ ] Φ_III_dollars = None
- [ ] Φ_III_labor_hours is always available
- [ ] total_shadow_dollars = None (cannot compute)

**Source**: data-model.md:187-189, 205-207

### CHK048: Missing Country ERDI
- [ ] Fallback: Core = 1.0, Periphery = 2.0
- [ ] Classification criteria for Core vs Periphery
- [ ] Warning when using fallback values

**Source**: data-model.md:260-262

### CHK049: Year Out of Range
- [ ] γ_III: year < 2003 returns NoDataSentinel
- [ ] γ_import: year > 2030 returns NoDataSentinel
- [ ] Clear error messages with reason

**Source**: data-model.md:33, 83

### CHK050: Import Share Sum ≠ 1.0
- [ ] Tolerance: ± 0.01
- [ ] If outside tolerance: warning or error?
- [ ] Normalization option (divide by sum)?

**Source**: data-model.md:99

---

## Summary

| Category | Items | Critical |
|----------|-------|----------|
| Formula & Math | CHK001-CHK010 | CHK001, CHK003, CHK005 |
| Data Integration | CHK011-CHK020 | CHK011, CHK012, CHK017 |
| Validation Ranges | CHK021-CHK030 | CHK021, CHK024, CHK029 |
| Constitution | CHK031-CHK040 | CHK031, CHK032, CHK038 |
| Edge Cases | CHK041-CHK050 | CHK043, CHK046, CHK047 |

**Total Items**: 50
**Critical Items**: 15 (must pass before implementation begins)

## Sign-Off

- [ ] All critical items reviewed and confirmed
- [ ] No blocking ambiguities remain
- [ ] Ready for `/speckit.tasks` task generation

**Reviewer**: _________________ **Date**: _________________
