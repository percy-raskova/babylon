# 14 — The treasure trove: what the Director's empirical data can make Babylon stop inventing

Read-only sweep, 2026-10-25. Question: **what is actually in `/media/user/data/babylon-data/`, and which
of it can replace Babylon's invented coefficients with measured rates, measured initial conditions, and
conservation identities?**

Nothing here implements or changes game law. Claims about the trove are from direct inspection
(commands listed below); claims about Babylon cite the file; proposals say **proposed**.

**Provenance.** Directory listings and `du`; `sqlite3 -readonly` against
`sqlite/marxist-data-3NF.sqlite`; `csv`/`zipfile` streaming reads of the CCC archives, the WID country
files, the Hickel/Ricci CSVs and the MIT county-presidential file; `openpyxl` read-only on the BEA/BLS
workbooks. Row counts, averages and inversions below were computed in this session, not quoted from
prior docs. The earlier cartographic survey (`project/research/16-living-map/data/babylon-data-survey.md`,
2026-07-11) remains the reference for geometry and map layers; this document does not repeat it.

**Guardrail.** The porch rules bind. Systems show, never prescribe; a participant's view is the only
view; engine abstractions stay buried (`2026-10-25-porch-01.md` §94–113, §147–171). Empirical tables are
the machine's desk drawer. What the player sees is crowds, prices, votes, hours — never a coefficient.

---

## 0. The one-line finding

The trove is not a pile of choropleths. It contains **five measured dynamical systems** — wealth shares
by class (quarterly, 2010–2024, plus a 1820–2024 annual ladder), imperial drain and price distortion
(annual, 1960–2017), unequal-exchange flows by region (1995–2007), protest events with repression
observables (2017–2026), and household time use — plus enough national-accounts material (BEA/BLS
capital, hours, output, input–output) to close the production circuit.

That is sufficient to run Babylon's mechanics from **conservation identities + measured rates + measured
initial conditions**, with no fitted response curves and no invented multipliers. The remaining
constants are unit conventions and scenario choices, which are *Designed* and labelled as such.

---

## 1. Inventory

Sizes are on-disk (`du -sh`). "Loaded" means the fact is already in the 3NF reference database; "raw"
means the CSV/XLSX/zip is the pre-ETL input.

### 1.1 The five dynamic datasets

| Path | Size | Contents | State |
|---|---|---|---|
| `piketty/` | 5.8G | World Inequality Database: 848 files, `WID_data_XX.csv` per country/region, semicolon-delimited, columns `country;variable;percentile;year;value;age;pop`. US file has **1,937 variables** and **1,220,242 rows**, years 1820–2024. Wealth shares at every percentile `p0p1…p0p99` plus cumulative `p0p50`, `p0p90`, `p0p99`, `p0p100`; income shares, composition, distributional national accounts. | raw |
| `sqlite/marxist-data-3NF.sqlite` | 4.9G | 35 dims, 36 facts, 5 bridges, 8 views. Carries `fact_fred_wealth_shares` (480 rows), `fact_fred_wealth_levels` (720), `fact_hickel_erdi_annual` (58), `fact_ricci_unequal_exchange_gvc` (51), `fact_qcew_annual` (14,670,249), `fact_productivity_annual` (17,336), `fact_census_worker_class` (900,900), `fact_census_income` (7,207,200), `dim_wealth_class` (4 — the Babylon class map is already inside the schema). | loaded |
| `babylon_hickel_final.csv` | 12K | 58 rows, 1960–2017: `annual_drain_usd_billions`, `erdi`, `alpha`, `core_gain_per_capita_usd`, `cumulative_drain`, `drain_yoy_change`, `distortion_yoy_change`, `is_anchor_year`, `china_inflection`. Idealized interpolation between Hickel–Sullivan–Zoomkawala anchor years. | raw |
| `babylon_ricci_final.csv` | 8K | 51 rows: region × year × direction × transfer type, `value_usd_billions`, `value_pct_gdp`, `gvc_share_of_total`, `edge_id`. Ricci Tables 6.2/6.4/6.6 plus aggregate rows from other sources. | raw |
| `ccc_protests/` | 38M | Crowd Counting Consortium, three Dataverse phases (2017–20, 2021–24, 2025–26), CC0, `MANIFEST.yaml` with per-file SHA-256 and **nine binding cross-phase discontinuities**. Event-level: date, county FIPS, lat/lon, `type`, `size_mean`, `arrests`, `injuries_crowd/police`, `chemical_agents`, `police_measures`, `participant_measures`, `organizations`, `issue_tags`, `valence`. | raw (zipped) |
| `elections/mit_countypres/` | 13M | MIT/MEDSL county presidential returns: `countypres_2000-2016_medsl_official.csv` (4.5M), `countypres_2000-2024_mirror.csv` (8.8M), and `countypres_2000-2024.csv` — **a 122-byte failed-download error stub, do not read it as data**. | raw |

### 1.2 Household and labour time

| Path | Size | Contents |
|---|---|---|
| `atus/` | 68K | `seed_data.yaml` (BLS ATUS Table A-1, 2022): daily hours by activity × gender, participation rates, six occupation-class multipliers, visibility weights and coefficients, shadow wage (SOC 31-1120). `visibility.py` + `models.py`: the `g₃₃` decomposition service. |
| `mass_labor_hours/` | 627M | BLS QCEW county high-level workbooks: `allhlcn15–20` (30 quarterly/annual files, restored from LFS under PER-339) and `allhlcn22` variants, plus `2022.annual.singlefile.csv` (420 MB, the full national QCEW microfile: `annual_avg_emplvl`, `total_annual_wages`, `avg_annual_pay`, location quotients, over-the-year changes). `PROVENANCE.md` records blast-radius: *no babylon code read this directory as of 2026-09-30*. |
| `qcew/` | 8.3G | 15 years of `annual.singlefile.csv`, county × industry × ownership, 2010–2024. |
| `employment_industry/` | 2.2G | 2024 QCEW split into one CSV per county (readable industry titles). |
| `lehd_qwi/` | 490M | Michigan QWI, R2026Q3: `qwi_mi_rh_f_gc_n3_op_u` and `_n4_`, 2000Q3–2021Q4, county × NAICS × race — hires, separations, payroll, job creation/destruction. `MANIFEST.yaml` with hashes. |
| `lodes/` | 7.9G | LEHD LODES origin–destination, block level, 607 files: 50 states × 2010–2021, `mi_wac` workplace-area characteristics, `us_xwalk`/`mi_xwalk` geography crosswalks. |
| `mobility-atlas/` | 351M | Opportunity Insights: county and commuting-zone intergenerational mobility (`kfr_*` by race × gender × parent-percentile cohort, 1978 vs 1992), county covariates, percentile→dollar crosswalk. |
| `hud_usps_crosswalk/` | 9.5M | ZIP↔county crosswalks, four 2025–26 vintages, `MANIFEST.yaml`. |

### 1.3 Production, capital and circulation

| Path | Size | Contents |
|---|---|---|
| `fixed-assets/` | 149M | BEA Fixed Assets: `FixedAssets.txt` (2022 and 2024 vintages), Series/Tables registers, flat-file zips. Investment and **net capital stock** by industry and asset type. |
| `productivity/` | 30M | BLS: `labor-productivity-detailed-industries.xlsx` (output/hour, hours, employment, compensation, unit labour cost, 1987–2024, NAICS detail) and `hours-employment-detailed-industries.xlsx`. |
| `gdp-by-industry/`, `value-added/`, `gross-output/`, `intermediate-output/` | 6M | BEA `GrossOutput`, `IntermediateInputs`, `ValueAdded`, `KLEMS` — the c + v + s decomposition per industry — plus duplicate single-table copies of each. |
| `input-output/` | 47M | Make, Use, Supply, Import matrices (detail/sector/summary, before and after redefinitions) plus `total-domestic-requirements/` — the Leontief inverse. |
| `bea/` | 163M | County GDP, regional tables, IO loaders (`.py`), `michigan_bea_ea.csv`, MAKE-USE and SUPPLY-USE zips. |
| `asm/` | 1M | Annual Survey of Manufactures 2022 (`AM2231GS1`): inventories by stage of fabrication, shipments, purchased materials, hours. `MANIFEST.yaml`. |
| `qcew/`, `employment_industry/`, `bls/laus/` | — | see above. **`bls/laus/` is a stale "Access Denied" HTML page, not data.** |

### 1.4 Territory, movement and the physical frame

| Path | Size | Contents |
|---|---|---|
| `tiger/` | 338M | TIGER/Line 2024/25: county, block group, place, AIANNH, area water (3,235 counties). |
| `natural-earth/` | 811M | Natural Earth v5.1.2 SQLite, 186 tables at 10m/50m/110m. |
| `dot/`, `freight/`, `bts_*` | 31.9G | HPMS 2024 road geometry, NTAD freight/rail/aviation geodatabases; FAF5.7.1 commodity flows 2018–2024; border crossings and monthly transborder freight. |
| `fcc/`, `energy/`, `epa_ghgrp/`, `raw_mats/` | 2.1G | Broadband coverage 2025; EIA Monthly Energy Review (115 tables); GHGRP emissions by unit/company; USGS Mineral Commodity Summaries 2025. |

### 1.5 Reference, provenance and the rest

| Path | Size | Contents |
|---|---|---|
| `national_reference_2024/` | 365M | ACS 2024 5-year `.dat` extracts (B01003 population, B11001/B11002 households, B19001/B19051 income, B23025 employment status, B24080 class of worker), UN WPP 2024, World Bank country GDP/population, international-identity and transport page captures — each with `.provenance.json`. |
| `census/`, `concordance/` | 56M | ACS code lists 2015–2021, CBSA delineation 2023, principal cities, Michigan place shapefile; BEA industry/commodity ↔ NAICS crosswalk. |
| `diagnostics/` | 484K | 30+ pre-load QA CSVs (table counts, coverage, tensor readiness, Detroit test case), plus two audit zips. **Historical: several row counts are zero because they predate the load. Do not quote as current state.** |
| `reference/`, `bea/*.py`, `loader_base.py`, `__init__.py` | 300K | The 3NF schema and loaders (code, not data). |
| `p27-ensemble-2026-07-29/` | 120M | The July P27 ensemble run: two seeds, both `ENGINE_FAILURE` at 294 s (tick-deterministic crash at year rollover), exported Postgres archives, and `phi_probe_full.txt` — **`Φ` going negative at industry level (NAICS 211: −172,528) and in 40 of 3,220 counties.** This is the empirical case for the closure problem in §4.1. |
| `sources/`, `corpus-additions/`, `lawvere-master/`, `external/`, `github/`, `backups/` | ~38G (almost all `backups/`) | Reading corpus (Marx, Neel, MIM, Lenin/Mao scans), `backups/` holding pre-amputation and pre-parquet copies of the reference DB, `external/*` **empty**, `github/ci-data-v8` two Parquet files (county→H3 bridge, land mask). |
| `imperial_rent/country.xlsx` | 1.8M | USITC/Census country-level import values by month, 1997–2024, `CTY_CODE` × `IJAN…IDEC`. Bilateral trade base, not a rent measure. |
| Root CSVs | 30K | `babylon_hickel_final.csv`, `babylon_ricci_final.csv`, the two NotebookLM exports, and their raw source tables (`Global South Value Drain…1960-2017`, `Babylon Simulation_ Long Format…1995-2007`). |

**NotebookLM exports.** `notebooklm_babylon_translation_guide.md` and
`notebooklm_to_babylon_mapping.csv` are a 34-parameter extraction pass over Ricci and Hickel. The guide's
own corrections are the useful part: `g₃₃` means *reproductive-labour visibility* and nothing else;
ERDI is a transformation operator, not a metric; `Differential_Fertility_Factor` is Ricardo smuggled into
a Marxian frame and must be skipped; `Price_of_Production_P` is the transformation problem Babylon
sidesteps. Treat the CSV as a **checklist of rejected mappings**, not as a parameter source.

---

## 2. What each dynamic dataset can actually determine

### 2.1 `piketty/` + FRED DFA — the 33/33/33/0 law, and its motion

The Director's law ("top 1% ≈ ⅓, next 9% ≈ ⅓, next 40% ≈ ⅓, bottom 50% ≈ 0") is confirmed, and the
confirmation is sharper than rounding.

**Stock shares**, FRED Distributional Financial Accounts, net worth, 60 quarters 2010Q1–2024Q4, averaged
(computed from `fact_fred_wealth_shares`):

| Class | FRED 2010–24 mean | WID 2024 | Babylon class (`dim_wealth_class`) |
|---|---|---|---|
| Top 1% | **30.1%** (range 28.1–31.0) | 34.8% | `core_bourgeoisie` |
| 90–99% | **38.7%** (36.4–40.1) | 34.8% (= 69.5 − 34.8) | `petty_bourgeoisie` |
| 50–90% | **29.7%** (28.1–31.6) | 29.5% (= 30.5 − 1.0) | `labor_aristocracy` |
| Bottom 50% | **1.5%** (0.4–2.7) | 1.0% | `internal_proletariat` |

**Flow shares** are the stronger statement. Net worth in trillions, 2010Q1 → 2024Q4
(`fact_fred_wealth_levels`): 16.79 → 49.84 (top 1%), 23.58 → 58.59 (90–99), 18.76 → 48.43 (50–90),
0.32 → 3.99 (bottom 50). Total 59.45 → 160.85. Of the **101.4 T created in fourteen years**:

| Class | New wealth | Share of new wealth |
|---|---|---|
| Top 1% | +33.05 T | **32.6%** |
| 90–99% | +35.01 T | **34.5%** |
| 50–90% | +29.67 T | **29.3%** |
| Bottom 50% | +3.67 T | **3.6%** |

So the ⅓/⅓/⅓ law is not a stock coincidence; it is the **stationary distribution of the flow**. That is
the single most important fact in this document for game design: the thirds are reproduced every period
by the flow rates, which means the engine can hold the *rates* (measured) and let the *stocks* fall where
they fall.

**The inversion**, which is the number the game actually wants (population owning each wealth third),
computed from the WID 2024 percentile ladder — every percentile, not four buckets:

- bottom third of wealth → owned by the bottom **91.3%** of adults
- middle third → the next **7.8%**
- top third → the top **0.96%**

`docs/reference/class-dynamics.rst` reports 90.1 / 8.3 / 1.6 for FRED 2025Q2; same structure, different
source. Both are right for their source; state which one you used.

**The long arc** (WID `shwealj999`, top-1% share, annual 1820–2024) is the game's century:

| 1820 | 1850 | 1913 | 1929 | 1950 | 1980 | 2000 | 2024 |
|---|---|---|---|---|---|---|---|
| 44.6% | **49.8%** | 46.6% | 48.7% | 29.6% | **23.2%** | 32.3% | 34.8% |

A 130-year fall then a 44-year rise. No teleology is needed and none should be implied: the curve is
produced by war, taxation, and crisis, and the game should be able to produce any segment of it from
conditions rather than replay it from a schedule. Bottom-50 share over the same span moves 2.2% → 1.0%
with a 3.6% peak in 1960 and **−1.8% in 2010** (negative net worth: debt exceeds assets).

**What is derivable, concretely:**

1. **Initial conditions** — four wealth stocks plus a population mass each, at any start year, from the
   percentile ladder. No invention required.
2. **The flow matrix** — ΔW_i per quarter over 59 transitions, with the closure Σ ΔW_i = ΔW_total. That
   is 59 observations of the four-vector field. A constrained minimum-norm decomposition (positivity,
   conservation, smoothness) yields the 12 off-diagonal flows F_ij(t) without assuming any functional form.
3. **The rates as observed data** — α_ij(t) = F_ij(t) / (W_j(t)·Δt). These are *measurements at a
   state*, not constants. They are the coefficients the current `class-dynamics.rst` replaces with
   fitted literals (α₂₁ = 0.0006, δ₁ = 0.0010, γ₃ = 0.0057, five of six α set to exactly 0.0). Those
   literals are precisely the magic numbers to retire: they were chosen to make a 40-step simulation land
   on 2025Q1, not measured.
4. **Cross-country class structure** — the same ladder exists for every country, which is how a periphery
   node gets its own distribution instead of a scaled core one (2024 top-1 / bottom-50): US 34.8 / 1.0,
   DE 27.9 / 3.4, FR 27.7 / 4.8, GB 21.3 / 4.6, CN 30.4 / 6.3, IN 40.1 / 6.4, BR 39.5 / 2.0,
   MX 39.8 / 2.0, RU 49.0 / 2.7, **ZA 54.9 / −2.5**.
5. **`r` and `g`** — `r` = (national income − compensation of employees) / household net worth, both
   numerator and denominator in the reference DB and FRED; `g` from real GDP. `r > g` becomes a computed
   reading, not an axiom. Note the mechanism that matters for play: when `r > g`, an existing stock grows
   faster than wages, so the *wealth* shares move even when nobody is "extracting" anything — that is the
   engine's honest answer to why the thirds persist.

**The 5-point source gap is a feature, not a bug.** FRED DFA (financial accounts, imputed top wealth) and
WID (survey plus national accounts) differ by ~5 pp on the top 1%: 30.1 vs 35.4 for 2010–2024. Babylon
should carry both, name which one a campaign used, and never average them. A single "true" number would
be a lie about the data; two labelled numbers are a tooltip the player can learn from.

### 2.2 `babylon_hickel_final.csv` — imperial rent Φ as a measured series

58 annual rows, 1960–2017. Verified shape:

| Year | Drain ($bn) | ERDI | Cumulative ($bn) | Drain YoY |
|---|---|---|---|---|
| 1960 | 2,000 | 3.20 | 2,000 | — |
| 1980 | 4,500 | 4.10 | 67,685 | +7.8% |
| 2000 | 6,950 | 6.60 | 183,852 | +1.6% |
| 2008 | 8,175 | 7.34 | 246,602 | +2.8% |
| 2016 | 9,975 | 8.38 | 320,102 | +2.3% |
| 2017 | 13,000 | 7.20 | 333,102 | **+30.3%** |

Mean annual growth 3.6%, standard deviation 7.4%, range −22.8% to +35.3%. ERDI range 2.40–8.38.
`core_gain_per_capita_usd` runs 2,500 → 15,000: that is the labour-aristocracy cushion as a measured
series, not a `Φ / population` guess.

**Derivable:**

- **The transfer identity.** With Hickel's price-distortion form, `D_t = (1 − 1/d_t)·X_t`, the implied
  Southern trade base is `X_t = D_t·d_t/(d_t − 1)`. For 1960 that is $2.91 T, for 2017 $15.10 T —
  a 2.9%/yr nominal path, which is plausible and internally consistent. The identity is checkable at
  every row, so `X_t` is *derived*, not assumed.
- **The local derivative of Φ with respect to distortion**, `∂D/∂d = X/d²`, read row by row. 1960:
  2.91T/10.24 = $284 bn per ERDI point. 2017: 15.10T/51.84 = $291 bn. Remarkably stable — the *level*
  of Φ is policy-determined, the *sensitivity* is structural.
- **Anchor vs interpolated rows.** `is_anchor_year` marks the real observations; the rest is linear
  interpolation. Any fitting must weight anchors 1 and interpolated rows ~0, or it will "discover"
  the interpolator.

**Caveat — the `alpha` column is undocumented and should not be trusted.** 1960 `alpha` = 0.2981 while
`1 − 1/erdi` = 0.6875; 2016 `alpha` = 1.0000 exactly. No definition in the file, the translation guide,
or the repo reproduces it. Recompute whatever rate is needed from `D`, `d` and the identity above; do not
import `alpha`.

**A flag for `Phi`'s sign.** `p27-ensemble-2026-07-29/phi_probe_full.txt` records Φ going **negative** in
NAICS 211 (−172,528) and in 40 of 3,220 counties. Hickel's Φ is a global transfer and cannot be negative;
a county with no tradable sector has no rent, not negative rent. That is a closure error in the existing
derivation, and it is the clearest argument for the conservation-first method in §4.1.

### 2.3 `babylon_ricci_final.csv` — the composition of Φ

Only the rows with `source_table` `Ricci_Table_6.2/6.4/6.6` are a consistent regional series in $bn at
current prices. The 2007 block also carries aggregate rows from other sources (`Source_3`, `Source_4`:
OECD 2,800; Non-OECD 6,700; Advanced Economies 2,800) at a different definition and scale — summing
across them double counts. Filter on `source_priority = 1`.

Consistent per-region series, transfer as a share of that region's own GDP:

| Region | Type | 1995 $bn (% GDP) | 2007 $bn (% GDP) |
|---|---|---|---|
| North America | CORE (inflow) | 70.7 (0.9%) | 255.5 (1.7%) |
| India | PERIPHERY (outflow) | 73.2 (**20.9%**) | 189.3 (**17.0%**) |
| China | SEMI_PERIPHERY (outflow) | 125.7 (17.3%) | 382.5 (**10.9%**) |

**Derivable:** extraction *intensity* (Φ_i / GDP_i) rather than Φ in dollars — the ratio that makes core
and periphery comparable and that the game can put on a node. The core absorbs ~1–2% of its own GDP; the
periphery surrenders 11–31%. That 10–20× intensity ratio is the measured basis for the solidarity
penalty: a core worker's wage and a periphery worker's wage are not two points on one labour market.

The China row is the quantitative version of the `SEMI_PERIPHERY` transition the translation guide
proposes: absolute transfer rises 3× while the share of own GDP falls by a third. A node can get richer
and stay drained. That is a genuinely interesting game state and it is measured, not invented.

### 2.4 `ccc_protests/` — agitation and repression as two coupled observed series

Streaming all three phases, harmonised by `MANIFEST.yaml` (one record per event in Phase 1, one per day in
Phases 2/3; `type='strike'` filter for strikes; valence recode at the 2020/2021 boundary):

| Year | Events | Participants | Median size | Arrests / 1k participants | Chemical-agent events | Crowd-injury events |
|---|---|---|---|---|---|---|
| 2017 | 10,873 | 7.58 M | 98 | 0.5 | 0 | 71 |
| 2018 | 21,554 | 11.46 M | 115 | 0.5 | 0 | 32 |
| 2019 | 11,420 | 3.68 M | 75 | 0.7 | 0 | 19 |
| 2020 | 28,334 | 4.47 M | 100 | **3.7** | **373** | **472** |
| 2021 | 29,409 | 1.37 M | 38 | **3.6** | 41 | 107 |
| 2022 | 37,677 | 4.82 M | 50 | 0.3 | 14 | 75 |
| 2023 | 32,370 | 9.57 M | 40 | 0.5 | 21 | 79 |
| 2024 | 40,367 | 8.48 M | 30 | 1.0 | 48 | 180 |
| 2025 | 39,152 | 10.60 M | 150 | 0.3 | —* | —* |

\* Phase 3 does not carry `chemical_agents` or `injuries_crowd_any`; zero there means *not collected*.
This is discontinuity #5 in the manifest and the most likely source of a silent error.

**Derivable, and this is the most game-relevant of the five:**

1. **Mobilisation frequency** M_t = events per 100k population (denominator available county-level from
   ACS B01003, so it can be computed per county, not just nationally).
2. **Mobilisation scale** S_t = median and mean event size. The median sits near 100 in Phase 1 and near
   30–50 in Phase 2, but the per-day recount forbids reading that as a trend; use the size *distribution*
   within a phase, not across the boundary. Note that `size_mean` is a *modelled* text-to-number
   conversion (`'hundreds'` → 200), so `size_cat` is the honest grain and `is_modeled` must be stamped if
   the mean is ingested.
3. **Repression intensity** A_t = arrests per 1,000 participants, with two distinct regimes: **3.6–3.7 in
   2020–21** against **0.3–1.0 in 2017–19 and 2022–25** — a tenfold gap between peak and trough, measured,
   with a decay path in the chemical-agent series (373 → 41 → 14 across 2020–22).
4. **The coupling** ∂A/∂M is *observable* rather than assumed: it is the slope between the 2020–21
   points and the rest. That slope, plus the decay time of A after M falls, is a two-state system
   (agitation, repression) whose coefficients are read off nine annual observations.
5. **Event-level heterogeneity** for texture the aggregate cannot give: `police_measures` categories
   (1,866 → 4,284 events from 2021 to 2024, i.e. reporting *and* practice both shifting),
   `organizations` (a join to the T6 organisation estate), `issue_tags`, `valence`.

**Honest-instrumentation caveat, from the manifest and not negotiable:** CCC's collection capacity
changed (Count Love crawl → own crawler in 2021 → social-media expansion → Telegram for right-wing
coverage from 2022). Density *trends* partly measure collection, not mobilisation. Use the spatial and
cross-sectional shape and the event-level observables. Never use the raw trend as ground truth. For the
strike spine, CCC ceases in April 2023 (Cornell took over); the licence-clean spine is BLS Work
Stoppages.

### 2.5 `elections/mit_countypres/` — the Electoral screen's empirical floor

Verified by streaming: 3,155–3,156 counties for 2000–2020; mode vocabulary is year-specific
(`TOTAL` before 2024, `TOTAL VOTES` in 2024, plus `NA`/blank rows), so a naive `mode='TOTAL'` filter
silently drops 2024 and a naive sum double counts it. Harmonised rule — per county, take
`TOTAL`/`TOTAL VOTES` if present, else sum the mode rows — reproduces 136.5 M (2016), 158.5 M (2020),
162.2 M (2024), against certified national totals of 136.7 / 158.4 / ~158 M.

National two-party shares from the same pass: 2000 48.4/47.9, 2004 48.2/50.6, 2008 52.9/45.7,
2012 51.0/47.0, 2016 48.2/46.1, 2020 52.0/46.1. Ranges of 4.7 pp in the Democratic share across six
cycles with 105–158 M votes cast.

**What this grounds, and what it does not.** It grounds **turnout and swing as observed quantities** and
their county-level dispersion — the Electoral screen's material layer. It does not ground a vote-choice
model: there is no money, no demographics, no policy position in this file. Those come from
`fact_census_income` (7.2 M rows), `fact_census_worker_class` (900 k), `national_reference_2024`
ACS extracts, and — for the money — nothing in the trove. Campaign finance is the one electoral input
that would still have to be fetched or declared *Designed*.

The honest structure for the screen, per `10-v3-electoralism-and-babylon.md`: the vote buys *space*, it
cannot reach Φ. The empirical file supports exactly that — it measures who shows up, not what they get.

### 2.6 `atus/` + `mass_labor_hours/` — household time exhaustion

From `atus/seed_data.yaml`, daily hours for all adults: housework 0.73, cooking 0.67, childcare 0.40,
eldercare 0.05, emotional support 0.82 → **2.67 h/day, 18.7 h/week** of reproductive labour; the gender
split is **3.37 h/day (23.6 h/wk) for women against 1.92 (13.4 h/wk) for men**, a ratio of 1.76.

**Derivable — the exhaustion identity.** For any household type,
`E = (T_wage + T_repro + T_commute) / 168`. Every term is measurable: `T_wage` from QCEW
(`annual_avg_emplvl` × average weekly hours) or BLS productivity `hours_worked_millions`;
`T_repro` from ATUS by class and gender; `T_commute` from LODES OD (block-level home→work pairs, 607
files) joined to ACS travel time. `E` is the state variable behind "no time to organise" — and it is a
*ratio of observed hours*, so it needs no coefficient at all.

`g₃₃` follows the same logic. The current weights (0.70 / 0.10 / 0.05 / 0.15 with coefficients
0.0 / 0.3 / 0.0 / 1.0, `expected_g33 = 0.18`) are declared estimates. Three of the four are measurable
from the trove: `state_socialized` from QCEW public-sector NAICS 61/62 employment share, `migrant_care`
from ACS noncitizen share of NAICS 62, `domestic_unpaid` from ATUS. Only `peripheral_subsistence` remains
a theoretical estimate, and the guide says so.

Caveat, stated in the seed file itself: ATUS samples ~10,000 respondents a year, national only. County
`g₃₃` is a modelling claim, not a measurement.

---

## 3. Supporting layers, briefly

- **Capital stock (c):** `fixed-assets/FixedAssets.txt`, BEA net capital stock by industry and asset type,
  2022 and 2024 vintages. This is the missing denominator for the organic composition of capital.
- **Labour time (v):** `productivity/hours-employment-detailed-industries.xlsx` — hours worked index and
  levels by NAICS, 1987–2024. Together with `fact_productivity_annual` (`hours_worked_millions`) this is
  the labour-time series the tick needs.
- **Surplus (s):** `gdp-by-industry/ValueAdded.xlsx` minus compensation, or `GrossOutput − IntermediateInputs`.
  **Do not use `view_surplus_value` as-is**: it computes s from *gross output* minus labour compensation,
  which yields an aggregate exploitation rate of 4.3–4.9 (1998–2023). That is not s/v; it is
  (c + v + s − v)/v. The defensible series is value added net of intermediates.
- **The Leontief inverse:** `input-output/total-domestic-requirements/`. This is how a demand change in
  one sector becomes hours and wages in another — the circulation circuit, measured.
- **Labour-market flows:** `lehd_qwi/` hires and separations by county × NAICS, 2000Q3–2021Q4. This is
  the reserve army as a *flow*, not a stock: JCR (job creation rate) and separations give the hiring
  and firing rates that move wages.
- **Commuting:** `lodes/od/` block-level OD, 2010–2021. Social distance in metres, not a metaphor.
- **Mobility:** `mobility-atlas/` `kfr` by race × gender × parent-percentile cohort, 1978 vs 1992 — the
  measured chance that a bottom-quintile child reaches the top quintile, by county. That is the honest
  content of "the American Dream" the Electoral screen can puncture with a number.
- **Class composition:** `fact_census_worker_class` (900,900 rows) — proletariat / petty bourgeois /
  state worker / unpaid labour by county, already in the schema.

---

## 4. The method: empirical derivative tables, not fitted curves

This is the design proposal, and it is the whole answer to "zero magic constants".

### 4.1 Conservation first

Write each state as a stock with a closed flow balance and no free additive term:

```
dW_i/dt = Σ_j F_ji(t) − Σ_j F_ij(t)          (flows between classes)
Σ_i W_i(t) = W_total(t)                       (closure)
Σ_ij F_ij = 0                                  (internal flows conserve)
```

Φ enters as an **external inflow to the core** and an equal outflow from the periphery — an entry that
appears twice with opposite sign. That single constraint would have caught the negative-Φ counties in
`phi_probe_full.txt`: a county cannot have outflow without a counterparty. In one line: *no flow without
a source, and no rent without a payer.*

### 4.2 Rates are read at the current state, not fitted globally

For each measured system, precompute a small table of `(state, rate)` pairs and interpolate.

- Wealth: 59 quarterly transitions × 4 classes → each α_ij stored with the state it was observed at
  (W_i, W_j, profit rate, unemployment); the rate is *looked up*, never modelled.
- Φ: 58 annual rows → `∂Φ/∂d` at the current `d`, read from the neighbouring rows.
- Agitation: 9 annual (M, A) points → the local slope and the decay time.
- Turnout: 7 cycles × 3,156 counties → observed turnout per county-year; covariates only stratify the
  lookup, they never extrapolate it.

Two rules make this honest:

1. **Never extrapolate.** Outside the observed range, return *unknown* and let the engine use its
   last-observed rate with an explicit staleness flag. This is the same discipline as the fog/veil rule:
   unknown renders as unknown, never as zero and never as an invented curve.
2. **Interpolate the data, not a fit.** Linear (or log-linear where the quantity is a ratio) between
   adjacent observations. A cubic spline or a logistic through the same points is a *new assumption* that
   the Constitution's ban on imposed response curves exists to prevent.

### 4.3 What this does to the existing numbers

`docs/reference/class-dynamics.rst` currently specifies six α, three δ and one γ; five α are exactly
0.0, and the rest are fitted to reproduce 2025Q1. Under this method those ten constants become:

- **α_ij(t):** measured, one row per transition, with a stated source (`fact_fred_wealth_levels`).
- **δ_i:** the observable tax-and-transfer residual — the difference between the measured flow and the
  explained flow, not a knob.
- **γ₃:** the measured `core_gain_per_capita × core population`, i.e. the Hickel drain allocated to the
  50–90% bracket by its measured share of the wealth stock — not a free injection rate.

The same treatment applies to `defines.toml`: every `[process.*]` and `[commodity.*]` block already
carries `EVIDENCE_CLASS = "Designed"`, which is the right label. The gain is that the *material* mechanics
stop needing Designed numbers, because QCEW/ASM/BEA supply the real ones for Michigan.

### 4.4 The residue that must stay Designed

Be explicit, so nobody hunts for a dataset that does not exist:

- tick length (28 days) and the campaign's opening period;
- opening commodity stocks in an authored scenario;
- the player's own allocations — the whole point of the game;
- anything outside the observed range, flagged stale rather than invented;
- campaign finance, until fetched.

Everything else has a row in the trove or an identity that closes.

---

## 5. Zero Spark, zero cluster, zero Python at runtime

The trove is 60 GB of raw material. The *runtime* needs kilobytes.

1. **Offline, once.** A repository tool reads raw sources and emits small immutable tables: the wealth
   ladder (117 years × 101 percentiles), the FRED flow matrix (58 × 4), the Φ series (58 rows), the CCC
   annual aggregates (9 rows) plus county event counts, the ATUS rows (~20), the election cycles
   (7 × 3,156). These are far below one megabyte and are pure functions of pinned inputs with recorded
   hashes.
2. **Reference build.** The output lands as the reference-build SQLite/Parquet artefacts AGENTS.md already
   names as immutable build artifacts. No Spark, no Postgres, no DuckDB at play time — the 4.9 GB
   warehouse and the 30 GB `dot/` tree never ship.
3. **Runtime.** Rust opens the campaign database (the ratified embedded SQLite, ADR287), reads a handful
   of tables at campaign start, and evaluates the coupled equations per tick in integer or fixed-point
   arithmetic so that equal input bytes produce equal output bytes. The empirical tables are
   `Observed`/`Derived`/`Calibrated` data, which is exactly the classification the Constitution requires;
   nothing is `Designed` except what §4.4 lists.
4. **Determinism.** Interpolation and rate evaluation must be order-independent and integer-stable. Where
   the data are decimal shares, store parts-per-billion integers and do the arithmetic in `i64`, so the
   `NominalWorldHash` does not depend on float rounding. No `f64` accumulation across a tick.

The July ensemble is the cautionary tale: two seeds, identical 294-second `ENGINE_FAILURE`, at year
rollover. More data would not have fixed that. Determinism and closure would have.

---

## 6. Traps found while reading

1. **`elections/mit_countypres/countypres_2000-2024.csv` is not data** — 122 bytes of HTML error JSON
   ("Guestbook response required"). The mirror file is the real one.
2. **CCC Phase 3 lacks the repression fields.** Zeros there are missing values. Any 2025 "chemical agents
   fell to zero" claim is a collection artefact.
3. **CCC Phase 1 counts multi-day events once; Phases 2/3 once per day.** Gross counts are not comparable
   across 2020/2021 without harmonisation.
4. **`babylon_hickel_final.csv` `alpha` is undocumented** and inconsistent with `1 − 1/erdi`. Do not use it.
5. **`babylon_ricci_final.csv` 2007 mixes scales.** Aggregate `Source_3`/`Source_4` rows are not
   comparable to the Ricci tables. Filter `source_priority = 1`.
6. **`view_surplus_value` overstates the exploitation rate** by using gross output as the value base.
7. **`diagnostics/` is stale.** Several coverage files are all-zero because they predate the load.
8. **`bls/laus/` is a saved "Access Denied" page.** Not data.
9. **WID and FRED disagree by ~5 pp on the top 1%.** Carry both, label both, never average.
10. **`WID_data_Al.csv` (47 bytes) and similar stubs** exist among the 848 files; validate row counts
    before loading a country.

---

## 7. What this buys the game

- **Ticker:** measured profit-rate, exploitation and Φ series, with a wage share that moves for reasons
  the player infers from events rather than from a constant.
- **Physical map:** county class composition (900 k rows), employment, wages, commuting — a county's
  character is data, not decoration.
- **Electoral:** turnout and swing distributions by county, plus mobility tables that make the promise
  falsifiable with a number.
- **Topology:** 40 k+ named organizations over nine years with county FIPS, and a repression series to
  attach to edges.
- **Wiki:** the 1820–2024 arc, which the engine can reproduce in segments without being told the ending.

The rule the trove enforces: every number the machine uses should trace to a row, an identity, or a
player's choice. If it traces to nothing it is a magic number, and the answer is to delete it, not tune it.

---

## 8. Next steps (proposed, none started)

1. Extend `tools/analyze_wealth_distribution.py` to emit the **flow matrix** and the per-transition α_ij
   table instead of the current fitted literals; keep the conservation residual as the reported
   goodness measure.
2. Build the WID ladder extractor (101 percentiles × 117 years, US plus ~20 comparator countries) into one
   small table; record provenance per country.
3. Recompute Φ from `D` and `d` with the closure rule, and re-run the county probe to confirm the negative
   counties disappear.
4. Harmonise CCC to an annual county panel with the nine manifest rules encoded as tests, then fit the
   (M, A) local slope and decay.
5. Compute the ATUS + QCEW + LODES exhaustion ratio `E` for Wayne County as the first measured state
   variable in the Michigan slice.
6. Retire the ten literals in `docs/reference/class-dynamics.rst` once (1) lands, and record the
   replacement as a calibration table with evidence classes.
