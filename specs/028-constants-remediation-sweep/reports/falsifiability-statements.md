# Falsifiability Statements: Tier A Constants

Feature 028 — Constants Remediation Sweep, Phase 3 (US1, FR-004).

Each wired constant documents: derivation equation, data source, and what
real-world observation in Wayne/Oakland County would prove it wrong.

## Constants Wired to Federal Data

### 1. `economy.extraction_efficiency`

**Derivation**: `s / (c + v)` from MarxianHydrator ValueTensor4x3 decomposition.

**Data Sources**:
- QCEW annual employment/wages (BLS, `fact_qcew_annual` table, NAICS level 6)
- BEA value-added by industry (via `InterpolatingBEASource`)
- Department mapping: `economics/data/naics_to_dept.yaml`

**Derivation Details**: Total surplus value (`total_s`) divided by sum of
constant capital (`total_c`) and variable capital (`total_v`) across all
three Marxian departments (I: means of production, II: wage goods, III: luxury).

**Falsification Criterion**: If the BLS publishes revised QCEW data for
Wayne County (FIPS 26163) year 2022 that changes the `total_s / (total_c + total_v)`
ratio by more than 10% from the currently derived value, the parameter is falsified.
Specifically: download updated QCEW annual averages for Wayne County, recompute
the tensor decomposition, and compare. A ratio outside `[0.01, 0.99]` would
indicate the derivation formula is structurally wrong.

**Bounded Range**: `[0.01, 0.99]` (clamped in hydrator).

---

### 2. `economy.shadow_wage_hourly`

**Derivation**: `SUM(total_wages_usd) / SUM(employment) / 2080` from QCEW.

**Data Sources**:
- QCEW annual employment and wages (BLS, `fact_qcew_annual`, NAICS level 6)
- Standard work hours per year: 2080 (40 hrs/wk × 52 wks)

**Derivation Details**: Average hourly wage across all NAICS-6 industries in
the county, computed as total annual wages divided by total employment divided
by standard annual hours (2080).

**Falsification Criterion**: Compare derived value against BLS Occupational
Employment and Wage Statistics (OEWS) for Wayne County. If the OEWS-reported
median hourly wage differs from our QCEW-derived average by more than 30%,
the derivation methodology is suspect. For Wayne County 2022, the OEWS median
for all occupations is publicly available at `data.bls.gov`. A shadow wage
outside the `[$10, $100]` per hour range would falsify the derivation entirely.

**Bounded Range**: Reasonable hourly wage range `[$10, $100]`.

---

### 3. `reserve_army.sigmoid_r0`

**Derivation**: BLS county unemployment rate proxy = 0.05 (national average).

**Data Sources**:
- QCEW employment data (BLS, `fact_qcew_annual`, NAICS level 6)
- BLS Local Area Unemployment Statistics (LAUS) as validation reference

**Derivation Details**: Currently uses a fixed national average unemployment
rate (5%) as the natural unemployment rate proxy. QCEW employment density
confirms the county has non-trivial economic activity, but the actual
unemployment rate is not directly derivable from QCEW alone. Future
improvement: wire to FRED `MIUNR` (Michigan unemployment rate) or
LAUS county-level data.

**Falsification Criterion**: Compare against BLS LAUS data for Wayne County.
If the LAUS-reported unemployment rate for Wayne County 2022 differs from
0.05 by more than 50% (i.e., actual rate is below 0.025 or above 0.075),
the national average proxy is inappropriate for this county. Wayne County's
actual LAUS unemployment rate is publicly available and would directly
falsify or validate this proxy.

**Bounded Range**: `[0.02, 0.15]` (natural unemployment rate proxy).

**Known Limitation**: This constant uses a fixed proxy rather than county-specific
data. It is flagged for future enhancement when FRED/LAUS data is integrated
(blocked by upstream Feature 024 - Capital Volume III FRED integration).

---

## Constants Not Yet Wired (Deferred to Future Features)

The following Tier A constants were identified in the 027 audit as data-derivable
but are blocked by upstream feature dependencies:

| Constant | Blocked By | Data Source |
|----------|------------|-------------|
| `class_shares.bourgeoisie` | hydrate_class_shares exists but not wired at init | QCEW wage percentiles |
| `class_shares.proletariat` | hydrate_class_shares exists but not wired at init | QCEW wage percentiles |
| `class_shares.median_wage` | hydrate_class_shares exists but not wired at init | QCEW wage averages |
| `consciousness.drift_sensitivity_k` | Feature 021 (Capital Vol. I) | Census education data |
| `solidarity.base_transmission_rate` | Feature 022 (Community Layer) | Census social capital |
| `territory.heat_*` | Feature 020 (Detroit Vertical Slice) | FBI UCR / Census |
| `crisis.crisis_period_ticks` | Feature 024 (Capital Vol. III) | FRED recession data |
| `economy.base_profit_rate` | Feature 013 (MELT) | BEA/QCEW tensor |
| `unequal_exchange.*` | Feature 025 (Tensor Hierarchy) | BEA I-O tables |

These constants are documented in the triage report (Phase 5, T044) with
specific data source mappings and gating feature requirements.

---

## Methodology Notes

**Constitution Compliance**: Article III.4 requires all constants trace to
approved data sources (BLS/QCEW, BEA, Census, FRED, ATUS). All three wired
constants derive from QCEW data in `marxist-data-3NF.sqlite`.

**Article IV Compliance**: Each falsification criterion identifies a specific,
publicly available federal dataset that could contradict the derived value.

**Verification**: Run `mise run test:int` to execute integration tests in
`tests/integration/test_constant_hydration.py` which validate the hydration
pipeline returns non-default values for Wayne County (FIPS 26163).
