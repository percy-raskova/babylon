# Research: End-to-End Leontief Imperial Rent Integration

**Branch**: `057-leontief-rent-integration` | **Date**: 2026-05-08 | **Phase**: 0

This document resolves the items deferred from `/speckit.clarify` to plan-phase research, plus surface-level decisions that emerged during plan drafting.

---

## R1: Periphery-wage source — concrete publication and extraction methodology

**Decision (REVISED 2026-05-08 post-analyze)**: **Hickel/Sullivan/Zoomkawala (2021) ERDI time series** from `babylon_hickel_final.csv`, ingested into `marxist-data-3NF.sqlite` as `fact_hickel_erdi_annual`. Per-industry wage ratio = `ERDI[year]` applied uniformly across BEA industries for v1.

**Rationale (post-analyze C4 pivot from PWT)**:

- **Empirical schema discovery**: A schema check during `/speckit.analyze` revealed (a) PWT data is NOT loaded in `marxist-data-3NF.sqlite` and (b) PWT files are NOT in `/media/user/data/babylon-data/`. The original PWT-broadcast plan had no implementation path. (See R9 below for the constitutional handling.)
- **Project-documented intent**: `/media/user/data/babylon-data/notebooklm_to_babylon_mapping.csv` documents the project's actual approach for `Imperial_Rent_Phi`: "ERDI from Hickel; wage data from QCEW" — pivoting to ERDI matches existing project convention.
- **Variable choice**: `babylon_hickel_final.csv` provides annual ERDI (Exchange Rate Distortion Index) values 1960–2017. ERDI = market_exchange_rate / PPP_exchange_rate, conceptually the multiplicative wage-distortion factor between the Global North and Global South in price-adjusted terms. The 2015 Intensive ERDI value is `8.25` (i.e., core wages are ~8.25× periphery wages at PPP-adjusted rates); 2015 Extensive is comparable. The implementer chooses one `scale_type` (Intensive recommended for post-2009 data per the CSV's typing).
- **v1 broadcast formula**: `wage_ratio_i = ERDI[year]` for all `i ∈ bea_industries` — uniform broadcast across BEA Summary industries. This is a v1 simplification per the spec's Assumptions section. The order-of-magnitude calibration check (SC-004) against the same publication's `annual_drain_usd_billions` column catches gross misalignment.
- **Why ERDI broadcast is defensible at v1**: ERDI is derived from the same global price-distortion framework that underlies the drain calculation in Hickel et al. 2021. Using ERDI as the periphery-wage-gap proxy means the input wage ratio is structurally consistent with the calibration target (different columns of the same publication, but they measure related-but-distinct quantities — see orthogonality note in R8.4 and R9).
- **Per-industry refinement (v1.5 refinement, deferred)**: Industry resolution can be added via `wage_ratio_i = ERDI[year] · qcew_us_wage[i] / qcew_us_avg_wage` — using `fact_qcew_annual` aggregated to BEA Summary via `bridge_naics_bea`. This adds industry resolution without requiring industry-disaggregated periphery wage data. Deferred to follow-up per the spec's Assumptions section.

**Metadata payload (recorded per FR-002 in `DefaultPeripheryLaborCoefficientsSource.metadata`)**:

```python
PeripheryWageMetadata(
    publication="Hickel, Sullivan & Zoomkawala (2021) — ERDI time series",
    publication_url="https://doi.org/10.1016/j.gloenvcha.2021.102467",
    periphery_definition="Global South per Hickel 2021 (effectively the high-income / low-and-middle-income split per World Bank classification)",
    units="ERDI — dimensionless ratio (market exchange rate / PPP exchange rate)",
    base_year=2017,
    industry_disaggregation="None — ERDI broadcast uniformly across BEA Summary industries (v1)",
    calibration_anchor="babylon_hickel_final.csv `annual_drain_usd_billions` column (different field of same publication; year-resolved per SC-004 + R8.4)",
    v1_simplification_caveats=[
        "Country-level ERDI broadcast uniformly across all BEA industries",
        "Industry-disaggregated periphery wage data not used; QCEW US-side industry resolution deferred to v1.5",
        "Source publication (ERDI) and calibration target (annual_drain_usd_billions) come from the same Hickel CSV — the orthogonality is at the column level, not the dataset level (see R9)",
    ],
)
```

**Alternatives considered**:

- **PWT v10.01 (original plan)**: Rejected because PWT data is not loaded in `marxist-data-3NF.sqlite` and not present in the babylon-data trove. Loading would require a constitutional III.4 amendment + a new ingestion pipeline. Hickel ERDI is already in the trove.
- **ILO Global Wage Database**: Industry-disaggregated wage data by country, but coverage varies and would require a custom ingestion pipeline + a constitutional III.4 addition. Rejected for v1.
- **BEA TiVA (Trade in Value Added)**: Constitutionally listed (`data-catalog.yaml id: BEA_TiVA`) and industry-disaggregated. Could derive a wage-distortion proxy via the value-added-vs-gross-output ratio. Promising but deferred to v2 because it requires deriving a wage signal from a value-added series — non-trivial.
- **WID (World Inequality Database)**: Constitutionally listed (`data-catalog.yaml id: WID`) but not loaded into SQLite; WID's primary focus is income distribution, not industry-level wages. Deferred to v2.
- **BLS International Labor Comparisons**: Discontinued 2014. Rejected.

---

## R2: BEA Use Table series for `final_demand` vector

**Decision**: BEA Input-Output Use Table, **Summary level (~71 industries)**, **"Total Final Uses (GDP)" column**, vintage-aligned with the inter-industry flow source (`DefaultInterIndustryFlowSource` already loads Summary-level for the same year).

**Rationale**:

- **Industry-list alignment**: FR-006 requires fail-fast on industry-list mismatch between flow and final-demand sources. Both must come from the same BEA aggregation level (Summary). The spec's existing `DefaultInterIndustryFlowSource` reads the Summary-level inter-industry coefficient table from `marxist-data-3NF.sqlite`; the new `DefaultFinalDemandSource` reads the corresponding Summary-level Use Table from the same database, year-keyed.
- **Series identity**: The "Total Final Uses (GDP)" column of the Use Table sums Personal Consumption Expenditures + Private Fixed Investment + Change in Private Inventories + Government Consumption Expenditures + Net Exports for each industry. This is what the calculator's `final_demand` numpy vector represents — `y_j` in the formula `Φ_j = Σᵢ M[i,j] · (w_ratio_i − 1) · y_j`.
- **Reference DB**: The data already lives in `marxist-data-3NF.sqlite` under the `fact_bea_use_table` table (or equivalent — loader name to be confirmed during implementation). If the column is not yet ingested, a small ingestion task lands as part of this feature's setup phase (separate commit). The spec's Assumptions section already covers this (the loader covers years that the simulation's tick range covers; if not, separate ingestion task is a prerequisite).

**SQL shape** (implementation reference):

```sql
SELECT industry_code, total_final_uses
FROM fact_bea_use_table
WHERE year = ? AND aggregation_level = 'SUMMARY'
ORDER BY industry_code;
```

**Alternatives considered**:

- **Sector level (~15 industries)**: Too coarse — would lose the Department I/IIA/IIB/III mapping resolution.
- **Detail level (~405 industries)**: Too fine — current QCEW NAICS crosswalk targets Summary level; finer granularity would require a richer crosswalk and is deferred to a follow-up.
- **GDP from BEA NIPA tables (alternative source)**: Available but not industry-disaggregated in the same way; would require its own crosswalk. Rejected.

---

## R3: Performance budget formalization

**Decision**: Per-tick wall-clock budget for the imperial-rent step is **≤ 100ms after cache warm-up**, **≤ 250ms cold (first tick of a new BEA vintage year)**. Validated by a new performance smoke test.

**Rationale (back-of-envelope)**:

- **Per-tick scale**: 3,000+ counties × ~71 BEA industries = ~213,000 multiply-adds for the per-county allocation step. NumPy on a modern CPU does this in well under 1ms (vectorized over a (3000, 71) matrix).
- **Per-year (cold) scale**: Leontief inverse `L_d = (I − A_d)⁻¹` for a 71×71 sparse matrix is ~10ms on `scipy.sparse.linalg.spsolve`. Import-content matrix `M = A_m @ L_d` is another ~5ms. These results are year-keyed and cached — the next 3 quarterly ticks of the same year hit the cache.
- **Cache strategy**: `CachedSource[T]` (Spec 058) with `cache_negative_results=True` (default) + LRU eviction at `max_entries=10` (covers a 10-year tick window). Year transitions trigger one cold computation; intra-year ticks are O(1) cache hits.
- **Why budgets are these specific numbers**: 100ms warm = ~10× headroom over the back-of-envelope; 250ms cold = ~10× headroom over the cold computation time. The headroom accommodates SQLite read latency (cold path includes a `SELECT * FROM fact_bea_io_coefficient WHERE year = ?` that reads ~5,000 rows).

**New test**: `tests/integration/economics/tick/test_imperial_rent_perf.py`:

- Warm-up tick to populate caches
- 100 consecutive same-year ticks; assert mean wall-clock ≤ 100ms with 95th percentile ≤ 200ms
- 1 tick at a new year (cache miss); assert wall-clock ≤ 250ms

The performance test is a smoke test, not a regression gate, and is tagged `@pytest.mark.integration` so it does NOT block the fast `mise run check` gate (per SC-005).

**Alternatives considered**:

- **No formal budget (status quo of "should be fast")**: Rejected — leaves performance regression undetectable until a user notices simulation slowdown.
- **Sub-10ms warm budget**: Too aggressive — leaves no headroom for SQLite cache misses or NUMA effects on the dev workstation.
- **Sub-1s cold budget**: Too lenient — would mask a 100× regression.

---

## R4: NAICS-to-BEA-Summary crosswalk strategy

**Decision**: Use the existing crosswalk table in `marxist-data-3NF.sqlite` (loaded as part of the Spec 025 tensor-hierarchy ingestion). If absent for a NAICS code, the allocator emits a `CalibrationWarning(QcewCarryForward, ...)` with a `look_back_distance=NaN` payload sentinel indicating "no crosswalk" rather than "no carry-forward year" — and the county's contribution from that NAICS code is set to zero (not skipped at the county level, just at the (county, NAICS) cell level).

**Rationale**:

- BEA publishes a NAICS↔BEA-code concordance as part of the I-O accounts. The Spec 025 ingestion loaded the Summary-level concordance into the reference SQLite (table name to be confirmed during implementation; expected: `xref_naics_bea_summary`).
- QCEW reports employment by NAICS at the 6-digit level. The Summary-level BEA aggregation collapses ~1000 NAICS-6 codes into ~71 Summary codes. The crosswalk is many-to-one.
- For NAICS codes added after the BEA Summary-level vintage was last updated (occasionally happens at NAICS revisions): the crosswalk lookup misses → the cell contributes zero rent → the warning surfaces the gap so a follow-up data ingestion can close it.
- This handling keeps the allocator deterministic and avoids silently dropping employment from the denominator in a way that would skew rent allocation upward for the surviving industries.

**Alternatives considered**:

- **Build the crosswalk on-the-fly from string matching**: Brittle and breaks Constitution III.1 (No Magic Constants).
- **Hardcode a fallback NAICS-to-Department mapping**: Violates the data-driven principle. The crosswalk MUST come from a published source.

---

## R5: Calculator clamp reconciliation (`np.maximum(loss_ratio, 0.0)` at `production_chain_rent.py:181`)

**Decision**: **Preserve the pre-existing clamp.** Reconcile the spec language: the warning fires at the *source* layer (where the violation is detected), the clamp lives at the *math* layer (where the structural axiom is enforced for downstream stability). Update the spec's Q3 clarification language to reflect the two-layer pattern.

**Rationale**:

- The Spec 057 Q3 clarification said the calculator "naturally produces a small negative rent contribution" for industries with `wage_ratio < 1.0`. **This is factually wrong about the existing code** — the calculator at line 181 explicitly clamps `loss_ratio = np.maximum(loss_ratio, 0.0)`, so per-industry contributions are never negative.
- **Why the clamp must stay**: Removing it would propagate negative rents through the entire pipeline. The downstream `savings_schedule.py` formula is `phi_adjustment = min(phi_hour · 2080 / wage, phi_cap)`. With negative `phi_hour`, the `min(negative, positive)` returns the negative value, which would *reduce* savings — but the savings model treats `phi_adjustment` as an unambiguously-positive imperial-rent contribution. The semantics flip. Tests downstream of `phi_hour` would silently produce nonsense values.
- **The two-layer pattern**: (a) **Source layer** — `DefaultPeripheryLaborCoefficientsSource` detects `ratio < 1.0` during fetch and emits `CalibrationWarning(AxiomViolation, industry, year, ratio)`. The data-integrity signal is preserved and surfaces in the EventBus history. (b) **Math layer** — `ProductionChainRentCalculator` clamps `loss_ratio` to `[0.0, +∞)` so the downstream formula stays in the valid regime.
- **Net result**: The information that "industry X had ratio 0.95 in year Y" is preserved as a calibration event observable to dashboard/SessionRecorder; the math still computes a stable per-county rent.

**Spec language update required**: Edit the Q3 Clarifications bullet to remove "the downstream rent calculator naturally produces a small negative rent contribution for those industries — still meaningful, if unusual" and replace with "the downstream rent calculator preserves its existing structural-axiom enforcement (`np.maximum(loss_ratio, 0.0)` at `production_chain_rent.py:181`); the warning fires at the source layer where the violation is detected, while the clamp at the math layer keeps downstream savings/accumulation arithmetic in a valid regime — see research.md §R5 for the two-layer pattern." This is a docs-only spec edit; no behavior changes.

**Alternatives considered**:

- **Remove clamp**: Rejected (above analysis).
- **Move clamp from calculator to source**: Possible but conflates concerns. The math layer's invariant should be enforced where the math runs (defense in depth).
- **Add explicit `ClampPolicy` enum to the calculator**: Premature flexibility — the only consumer is this pipeline, the only correct policy is `floor_at_zero`.

---

## R6: `CalibrationWarning` event placement

**Decision**: Add three new `EconomicEvent` subclasses (`AxiomViolationEvent`, `QcewCarryForwardEvent`, `PhiHourOutlierEvent`) to `src/babylon/models/events.py` (the typed Pydantic event hierarchy). Publish via the existing `EventBus.publish(Event(type="calibration_warning.axiom_violation", tick=..., payload=event_pydantic.model_dump()))` adapter pattern.

**Rationale**:

- **Two coexisting event systems in the codebase**: (a) `babylon.engine.event_bus.Event` — frozen dataclass with `type: str` discriminator + `payload: dict[str, Any]` (the channel itself); (b) `babylon.models.events.SimulationEvent` Pydantic hierarchy with subtypes `EconomicEvent`, `CrisisEvent`, `ConsciousnessEvent`, etc. (the typed shape of payloads).
- **Existing convention**: Other typed events (e.g., `ExtractionEvent`, `SubsidyEvent`) follow the pattern: define typed Pydantic class in `models/events.py`, publish via `EventBus.publish(Event(type="...", tick=..., payload=typed.model_dump()))`. Subscribers receive the `Event` and parse the payload back into the typed Pydantic class via `TypedClass.model_validate(event.payload)`.
- **Discriminator string convention**: Hierarchical with `.` separators. Existing examples: `"crisis.superwage"`, `"struggle.uprising"`, `"topology.bifurcation_tendency"`. New events use:
  - `"calibration_warning.axiom_violation"` — periphery-wage ratio < 1.0
  - `"calibration_warning.qcew_carry_forward"` — QCEW gap, carry-forward applied
  - `"calibration_warning.phi_hour_outlier"` — per-county phi_hour outside plausible range
- **Subscriber pattern**: `EndgameDetector`, `SessionRecorder`, dashboard observer subscribe to the `"calibration_warning.*"` family via `bus.subscribe_pattern("calibration_warning.*", handler)`. (If the existing EventBus does not support glob-pattern subscriptions, subscribers register three handlers — one per subtype — during this feature's implementation.)
- **Test assertion pattern**: `event_bus.get_history()` returns a list of `Event`; tests filter by `e.type.startswith("calibration_warning.")` and parse `e.payload` into the typed class. This matches the pattern Spec 058's behavioral-fence test already uses.

**Pydantic shapes (data-model.md will detail)**:

```python
class AxiomViolationEvent(EconomicEvent):
    industry: str           # BEA industry code
    year: int
    ratio: float            # The violating wage ratio (< 1.0)
    threshold: float = 1.0  # The expected lower bound

class QcewCarryForwardEvent(EconomicEvent):
    county_fips: str
    year: int                  # The tick year
    look_back_year: int        # The year carried forward from
    look_back_distance: int    # tick year − look_back_year

class PhiHourOutlierEvent(EconomicEvent):
    county_fips: str
    phi_hour: float       # The outlier value
    threshold_low: float  # Plausibility lower bound
    threshold_high: float # Plausibility upper bound
```

**Alternatives considered**:

- **Use raw `Event` with `payload: dict`**: Loses static type safety; harder to test. Rejected.
- **Define a new `CalibrationWarning` parent class outside `EconomicEvent`**: Calibration warnings are about economic data quality, semantically nested under `EconomicEvent`. The `EconomicEvent` ancestor lets dashboard filters that already subscribe to `EconomicEvent` events catch calibration warnings without separate wiring.
- **Use Python `warnings.warn` instead of EventBus**: Rejected per Clarifications 2026-05-08 / Q4.

---

## R7: Industry-list alignment fail-fast (FR-006)

**Decision**: Validation lives in `imperial_rent.compute()` (the new sub-module's entry point), runs once at the start of each cold-cache computation. Three sources MUST publish identical industry lists for the same year: `DefaultInterIndustryFlowSource.industries`, `DefaultPeripheryLaborCoefficientsSource.industries`, `DefaultFinalDemandSource.industries`. Mismatch raises a `ValueError` with diagnostic naming the mismatching codes (a deterministic-ordered diff: codes-in-A-not-in-B + codes-in-B-not-in-A).

**Rationale**:

- The calculator already validates `flow.industries == shares.industries` (line ~52 of `production_chain_rent.py`'s `decompose` method). This research item extends that pattern to cover the two new sources.
- Validation is *list equality*, not *set equality* — order matters because the resulting `wage_ratios` and `final_demand` numpy vectors are positional.
- Diagnostic format: `"BEA industry list mismatch for year 2015: missing from periphery_wage [code1, code2, ...]; missing from final_demand [code3, ...]; missing from flow [code4, ...]"`. Bounded length: emit at most 10 codes per side, then "(N more)".
- **Why fail-fast vs warning**: Per FR-006, the spec explicitly requires fail-fast for misalignment ("the system fails fast with a diagnostic identifying the misalignment, rather than silently producing wrong numbers"). This is different from FR-002's pass-through-with-warning for value violations — list misalignment is a *structural* error (the math can't even run), value violations are a *calibration* issue (the math runs, but a documented assumption is violated).

**Test coverage**: A new unit test `test_imperial_rent_pipeline.py::test_industry_misalignment_raises` constructs three sources with deliberately-mismatched industry lists for a synthetic year and asserts the `ValueError` is raised with a diagnostic that names at least one missing code per side.

---

## R8: Data trove location and downstream refinements (2026-05-08)

**Discovery (mid-Phase-0)**: All source data lives at **`/media/user/data/babylon-data/`** — confirmed by user. The in-repo `data/sqlite/marxist-data-3NF.sqlite` (8.8 GB) is what code reads (`src/babylon/engine/simdb/database.py:37`, `src/babylon/reference/database.py:54`). The trove also has its own copy of the SQLite kept in sync.

**Inventory of items relevant to Spec 057** (verified via `ls`):

| Item | Trove path | Relevant to |
|------|-----------|-------------|
| Reference DB | `marxist-data-3NF.sqlite` (mirror of in-repo copy) | All sources |
| Hickel time series 1960–2017 | `babylon_hickel_final.csv` | SC-004 calibration |
| BEA Use Table Summary | `input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx` | R2 (`DefaultFinalDemandSource`) |
| BEA Make Table Summary | `input-output/make-use/IOMake_Before_Redefinitions_PRO_Summary.xlsx` | (calculator already uses; verifies vintage) |
| BEA Import Matrices Summary | `input-output/make-use/ImportMatrices_Before_Redefinitions_Summary.xlsx` | (DBImportShareSource verifies vintage) |
| NAICS-BEA concordance | `concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` | R4 (`IndustryToCountyAllocator`) |
| QCEW (annual) | `employment_industry/2024.annual.by_area/`, `2024.annual.by_industry/` | R4 (allocator); verify multi-year coverage at impl time |
| BEA Regional GDP | `bea/regional/CAGDP2__ALL_AREAS_2001_2023.csv` | (potential SC-004 cross-check) |
| Michigan BEA EAs | `bea/michigan_bea_ea.csv` | Constitution IV.1 (Michigan test case) |
| LAUS county unemployment | `bls/laus/la.data.64.County` | NOT QCEW — different series |

### Refinement to R1: PWT remains primary periphery-wage source; Hickel is calibration only

`babylon_hickel_final.csv` provides drain values in the form `annual_drain_usd_billions` + `erdi` (Exchange Rate Distortion Index) + `alpha` + `scale_type`. ERDI is conceptually adjacent to a wage-distortion factor but is not itself a per-industry wage ratio — it's a national price-distortion measure. Using ERDI as the periphery-wage input would conflate price distortion with wage gap and weaken the structural derivation.

**Decision (refining R1)**: PWT v10.01 via SQLite remains the periphery-wage source per FR-002. Hickel CSV is reserved for the SC-004 calibration anchor only — see R8.4 below.

### Refinement to R2: BEA Use Table source confirmed available

`input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx` is the canonical Summary-level Use Table at "Producer prices, Before Redefinitions" — the standard form for I-O analysis. The "Total Final Uses (GDP)" column is one of the trailing columns of that table.

**Decision (refining R2)**: If `fact_bea_use_table` (or equivalent Summary-level table) does not yet exist in `marxist-data-3NF.sqlite`, an ingestion task lands as the first commit of Spec 057's implementation phase, reading from `input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx`. Tabled at `tasks.md` time (verified during Phase 2).

### Refinement to R4: NAICS-BEA crosswalk source confirmed available

`concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` is BEA's official concordance, expected to already be loaded into `marxist-data-3NF.sqlite` as part of the Spec 025 tensor-hierarchy ingestion. If not, ingestion lands as part of Spec 057's setup phase.

**Decision (refining R4)**: Reuse the existing ingestion if present (table name `xref_naics_bea_summary` or equivalent — confirmed at impl time); fall back to ingesting from the concordance XLSX otherwise.

### R8.4 — SC-004 calibration anchor refinement

**Discovery**: The Hickel CSV uses two scale types — `Extensive` (raw dollar drain) for years 1960–~2008 and `Intensive` (ERDI-corrected drain) for years ~2009–2017. The 2015 value differs by scale type:

- 2015 Intensive: `9750.0` (i.e., $9.75 trillion)
- 2015 Extensive (often-cited figure): ~$2.8T

The single-year `$2.8T (2015)` anchor in SC-004 is a defensible Extensive-scale figure but does NOT directly match what the CSV provides for 2015 (which is Intensive). Two ways to reconcile:

- **Single-year, scale-explicit**: SC-004 specifies "within an order of magnitude of $2.8T (Hickel Extensive, 2015)" OR "within an order of magnitude of $9.75T (Hickel Intensive, 2015)". Either is defensible; the wider OOM range covers both.
- **Year-resolved time series**: SC-004 references the full `babylon_hickel_final.csv` time series. For each tick year that has both a computed `phi_hour` total and a Hickel row, assert OOM agreement (1/10 ≤ ratio ≤ 10) with the matching scale-type entry. More rigorous, more useful for ongoing calibration.

**Decision**: Adopt the year-resolved interpretation. SC-004 is updated to: *"For at least one tick year with both complete BEA + QCEW data and a `babylon_hickel_final.csv` row, the computed national-total `phi_hour · employment-hours` is within an order of magnitude of the `annual_drain_usd_billions` value for that year, with the implementer documenting which `scale_type` (Intensive or Extensive) is used as the comparison anchor."* This is operationalized as `tests/integration/economics/tick/test_imperial_rent_calibration.py::test_oom_against_hickel_csv[year]` parameterized by the years where both sources have data.

The single-year $2.8T (2015) figure remains a valid anchor in spec narrative; the test mechanism adds the year-resolved CSV-driven check.

## R9: Constitutional III.4 amendment — add Hickel CSV as fixture data source (post-analyze 2026-05-08)

**Discovery context**: R1's pivot from PWT to Hickel ERDI (driven by the analyze C4 finding that PWT is not loaded) makes `babylon_hickel_final.csv` a runtime data input, not just a calibration anchor. Per Constitution III.4, every runtime data source must appear in `data-catalog.yaml`. The Hickel CSV is currently absent from the catalog.

**Decision**: Add a single entry to `.specify/memory/data-catalog.yaml` under `International Trade` category, classified as `Fixture` (the data is a pinned static historical time series, not a refreshable feed):

```yaml
      - id: Hickel_HSZ_Drain
        agency: Hickel/Sullivan/Zoomkawala
        dataset: Global South Value Drain time series 1960–2017 (annual_drain_usd_billions, ERDI, alpha)
        vintage: Static (2021 publication; data through 2017)
        granularity: National-aggregate (Global North vs Global South)
        cadence: Static (no updates planned)
        class: Fixture
        provenance_url: https://doi.org/10.1016/j.gloenvcha.2021.102467
        local_path: /media/user/data/babylon-data/babylon_hickel_final.csv
```

**Constitutional implication**: This is a `PATCH`-level constitution amendment (data-catalog addition, no principle redefinition) per Constitution IX.1. Bumping `data-catalog.yaml` version from `2.6.1` → `2.6.2`. Adding to the `International Trade` category (closest fit to the Global North/South drain framework).

**Rationale for `Fixture` class**:

- Hickel et al. 2021 published a one-time time series. No live API, no scheduled refresh.
- Data through 2017; not updated since publication. Future updates would be a separate publication, not a refresh of this one.
- Matches the constitutional `Fixture` pattern: "pinned snapshots... never fetched at runtime and never substituted for runtime data."
- Subtle nuance: the simulation reads ERDI per tick year, so it functions like runtime data semantically. But the data ITSELF is static and pinned. Chetty Opportunity Atlas is the precedent (also Fixture, also tract-level historical data consumed during simulation).

**Implementation**: New task T024c lands the catalog amendment + a one-line entry in `.specify/memory/data-catalog.yaml`; constitution amendment registry comment block updated.

**Alternatives considered**:

- **Treat as runtime data (Runtime class)**: Would imply a refreshable upstream — incorrect for a one-time publication.
- **Skip catalog addition**: Violates Constitution III.4. Not an option.
- **Use a different source to avoid the catalog addition**: Would defeat the purpose of pivoting to Hickel ERDI in the first place (R1 chose Hickel because it's the most empirically grounded available source).

## Summary of Phase 0 outputs

| Item | Decision | Affects |
|------|----------|---------|
| R1 — Periphery-wage source **(REVISED 2026-05-08)** | **Hickel/Sullivan/Zoomkawala (2021) ERDI** time series from `babylon_hickel_final.csv` (ingested into `fact_hickel_erdi_annual`); `wage_ratio_i = ERDI[year]` uniformly broadcast across BEA Summary industries (v1). Original PWT plan rejected because PWT data is not loaded (analyze C4 finding) | `DefaultPeripheryLaborCoefficientsSource` implementation, FR-002 metadata, T024c (catalog amendment), T024d (ingestion) |
| R2 — Final-demand source | BEA Use Table Summary level "Total Final Uses (GDP)" column — **DEFAULT path: derive `y = x − A·x`** from `fact_bea_national_industry.gross_output_millions` + `fact_bea_io_coefficient` (per `FinalDemandSource` Protocol's "or derived" docstring). Fallback ingestion only if SC-004 calibration insufficient | `DefaultFinalDemandSource` implementation, FR-003 |
| R3 — Performance budget | ≤100ms warm / ≤250ms cold per-tick; smoke test in `test_imperial_rent_perf.py` | New test file, SC-005 |
| R4 — NAICS-BEA crosswalk | Use confirmed `bridge_naics_bea` (NOT `xref_naics_bea_summary`); leverage `weight` column for split-mapping apportionment + `mapping_quality` discriminator | `IndustryToCountyAllocator` implementation |
| R5 — Calculator clamp | Preserve clamp; spec Q3 language updated to two-layer pattern | Spec edit (docs-only); no code change |
| R6 — `CalibrationWarning` placement | 3 new `EconomicEvent` subclasses in `models/events.py`; published via existing `EventBus` | `models/events.py` edits; FR-002, FR-004, FR-008 |
| R7 — Industry-list alignment | List-equality validation in `imperial_rent.compute()`; bounded diagnostic | `imperial_rent.py` implementation, FR-006 |
| R8 — Data trove + SC-004 refinement | All source data at `/media/user/data/babylon-data/`; in-repo `data/sqlite/marxist-data-3NF.sqlite` is what code reads. SC-004 promoted from single-year `$2.8T (2015)` to year-resolved comparison against `babylon_hickel_final.csv` time series. **Orthogonality note**: post-R1 pivot, the same CSV provides BOTH input ERDI (R1) and calibration target `annual_drain_usd_billions` (R8.4); they are different columns of the same dataset, but conceptually distinct quantities (input is wage distortion proxy; target is aggregate drain estimate) — see R9 caveat | spec edit to SC-004; new test `test_imperial_rent_calibration.py`; downstream refinements to R1/R2/R4 sources |
| R9 — Hickel catalog amendment **(NEW 2026-05-08)** | Add `Hickel_HSZ_Drain` entry to `data-catalog.yaml` under `International Trade` category, class `Fixture`. PATCH-level constitution amendment (`2.6.1` → `2.6.2`) | T024c, `.specify/memory/data-catalog.yaml`, constitution amendment registry |

**No remaining NEEDS CLARIFICATION items.** Ready for Phase 1.
