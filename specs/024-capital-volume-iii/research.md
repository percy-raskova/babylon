# Research: Capital Volume III Integration

**Feature**: 024-capital-volume-iii | **Date**: 2026-02-25

## R1: National vs County Financial Data Granularity

**Decision**: Hybrid model — national financial state shared; rent/housing county-specific.

**Rationale**: FRED interest rates, credit aggregates, and fictitious capital data (Z.1) are national-level. Only BEA rental income and Census/ACS housing data have county-level granularity. The existing tick system already uses this hybrid pattern: `NationalTickParameters` holds tau, gamma values shared by all counties, while `CountyEconomicState` holds county-specific capital stock, throughput, employment.

**Alternatives considered**:
- All financial data allocated to counties via GDP weighting: Rejected — would create false precision. A rural county and a financial hub county do not have meaningfully different "share" of national interest rates.
- All financial data national-only with no county adjustment: Rejected — counties with different profit rates face different interest burdens even under the same national rate.

## R2: Surplus Distribution Method

**Decision**: Data-driven from federal sources. Profit of enterprise as residual.

**Rationale**: Matches established hydration pattern (QCEW → employment, BEA → GDP, then derived metrics). Interest comes from FRED (national net interest income), rent from BEA (rental income of persons), taxes from IRS (corporate income tax). The residual `p = s - i - r - t` preserves the accounting identity without requiring a formula to independently compute profit.

**Alternatives considered**:
- Model-driven formula computing shares from simulation state: Rejected — would require calibrating a profit share model without empirical grounding. Data-driven is consistent with III.4 (Data Source Traceability).
- Hybrid with data initialization + simulation dynamics: Deferred to future iteration — could allow crisis dynamics to shift shares, but initial implementation should establish the baseline data pipeline first.

## R3: FRED API Integration Pattern

**Decision**: Extend existing `FredAPIClient` with new series; add financial series to `FredLoader`.

**Rationale**: The codebase already has a production-grade FRED client (`src/babylon/data/fred/api_client.py`) using httpx with rate limiting and retries. It already defines `NATIONAL_SERIES` and `DFA_WEALTH_LEVEL_SERIES` constants. Adding new series (FEDFUNDS, T10Y2Y, BAA-AAA, TCMDO, GFDEBTN, WILSHIRE) follows the established pattern.

**Alternatives considered**:
- Install `fredapi` PyPI package: Rejected — the project already has a hand-rolled client with project-specific rate limiting. Adding a dependency for the same functionality increases surface area.
- Create separate financial API client: Rejected — would duplicate rate limiting, retry logic, and API key management.

## R4: Fed Z.1 Financial Accounts Data

**Decision**: New `z1_loader.py` in `src/babylon/data/fred/` parsing the Z.1 data release.

**Rationale**: The Z.1 Financial Accounts of the United States contains quarterly balance sheet data for all sectors. Key tables: L.1 (credit market debt outstanding), B.103 (household balance sheet), L.213 (corporate equities). The data is available as bulk CSV from the Fed's website. This is a new data source requiring Constitution III.4 amendment.

**Key series**:
- FL894104005.Q: Total credit market debt outstanding (TCMDO equivalent)
- FL153064005.Q: Household total assets
- FL103164003.Q: Corporate equities outstanding
- FL313161105.Q: Federal government debt securities outstanding

## R5: Credit Cycle State Machine

**Decision**: Directed cycle with stagnation shortcuts.

**Rationale**: The main cycle (EXPANSION → OVEREXTENSION → CRISIS → RECOVERY → EXPANSION) models Marx's credit cycle from Capital III Ch. 30. STAGNATION as a reachable-but-not-returnable state from OVEREXTENSION or RECOVERY models secular stagnation (insufficient profit rate for new expansion, insufficient crisis for devaluation). This matches the existing `CrisisPhase` pattern in Feature 018 which also has a directed lifecycle.

**Transition triggers**:
- EXPANSION → OVEREXTENSION: Credit growth positive while profit rate trend negative
- OVEREXTENSION → CRISIS: Default rate exceeds threshold
- OVEREXTENSION → STAGNATION: Credit growth near zero, profit rate stable but low
- CRISIS → RECOVERY: Profit rate above threshold for M consecutive periods
- RECOVERY → EXPANSION: Credit growth resumes positive
- RECOVERY → STAGNATION: Credit growth stalls, profit rate flat

## R6: Negative Surplus and Debt Accumulation

**Decision**: Enterprise profit absorbs shortfall; separate debt accumulation tracks cumulative deficit.

**Rationale**: Interest and rent are contractual obligations — they persist even when surplus is insufficient. This models the real dynamics where firms borrow to service debt (debt spiral). The `DebtAccumulation` entity at county level accumulates when `p < 0` and drains when `p > 0`, providing a leading indicator for crisis severity.

**Integration with crisis**: When `accumulated_debt / county_surplus > threshold`, this feeds into the integrated financial crisis assessment as a profit squeeze signal.

## R7: Transformation Problem Non-Requirement

**Decision**: Not required. County-aggregate surplus distribution uses Marx's first equality.

**Rationale**: At the aggregate level, total surplus value = total profit (Marx's first aggregate equality). Since the system operates at county-aggregate granularity (not per-industry within county), the transformation from values to prices of production does not change the total surplus available for distribution. Federal data sources (BEA, FRED, IRS) already report in price-space, so the distribution shares are inherently post-transformation.

## R8: Existing FredAPIClient Series Catalog

**Decision**: Extend `NATIONAL_SERIES` dict in `api_client.py` with Volume III series.

**New series to add**:

| Series ID | Description | Use |
|-----------|-------------|-----|
| FEDFUNDS | Federal Funds Effective Rate | Base interest rate |
| DGS10 | 10-Year Treasury Constant Maturity | Risk-free benchmark |
| BAA10Y | Moody's Baa Corporate Bond Yield Relative to 10-Year Treasury | Credit spread |
| TCMDO | Total Credit Market Debt Outstanding | Credit aggregate |
| GFDEBTN | Federal Debt: Total Public Debt | Government fictitious capital |
| WILL5000PR | Wilshire 5000 Price Index | Equity market cap proxy |
| BOGZ1FL894104005Q | Total Credit Market Instruments (Z.1) | Sectoral credit |
| B230RC0Q173SBEA | Rental Income of Persons (BEA NIPA) | Ground rent proxy |
| A054RC1Q027SBEA | Taxes on Corporate Income (BEA NIPA) | Tax on surplus |

## R9: Census/ACS Housing Data Integration

**Decision**: Protocol-based loader for Census/ACS housing tables.

**Key variables**:
- B25077: Median Value of Owner-Occupied Housing (county-level)
- B25064: Median Gross Rent (county-level)
- Construction Cost Index: RSMeans or Census Value of Construction Put in Place

**Pattern**: New `HousingDataSource` protocol in `rent/data_sources.py` with `DefaultCensusHousingSource` implementation querying ACS 5-year estimates via Census API or bulk download.
