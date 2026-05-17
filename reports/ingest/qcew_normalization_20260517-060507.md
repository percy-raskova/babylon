# QCEW Normalization Report
**Run timestamp**: 2026-05-17T05:56:44+00:00
**Migration version**: spec-067-v1.0
**Database**: `/home/user/projects/game/babylon/data/sqlite/marxist-data-3NF.sqlite`
  - SHA256 pre: `5a82b797a163f7f856c766d026941b803405561720307ff457bcdd50a84ab39e`
  - SHA256 post: `ddf4ed238d81f750e17cbfde86fa530aedefde96e81aaa4d3be2dd630b2bc4b4`
**Duration**: 490.2 s
**Git**: 067-qcew-ownership-normalization @ e9defe1ea8e769a131448e2eac9142f0d42e97d4

## Summary
- Total rows pre-migration: 43,305,794
- Total rows post-migration: 15,097,464
- Rows excluded: 28,208,330
  - NAICS-only rollups: 28,159,281
  - Ownership-only rollups: 0
  - Both axes: 49,049
  - Integrity check passed: True

## NAICS vintages
- 2010: NAICS 2007
- 2011: NAICS 2007
- 2012: NAICS 2012
- 2013: NAICS 2012
- 2014: NAICS 2012
- 2015: NAICS 2012
- 2016: NAICS 2012
- 2017: NAICS 2017
- 2018: NAICS 2017
- 2019: NAICS 2017
- 2020: NAICS 2017
- 2021: NAICS 2017
- 2022: NAICS 2022
- 2023: NAICS 2022
- 2024: NAICS 2022

## BLS-suppressed county-years
*(none flagged)*

## Per-county deltas
- Scope: Michigan-only
- Counties within ±5%: 0 (0.00%)
- Counties with |delta| > 10%: 1236
- Max |delta|: 94.04%

### Outliers (top 10)
| county_fips | year | pre_sum | post_sum | delta_pct | reason |
|---|---|---|---|---|---|
| 26001 | 2010 | 1484 | 286 | -80.73% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2011 | 1553 | 372 | -76.05% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2012 | 1550 | 398 | -74.32% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2013 | 1613 | 480 | -70.24% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2014 | 1670 | 382 | -77.13% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2015 | 1686 | 200 | -88.14% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2016 | 1718 | 174 | -89.87% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2017 | 1789 | 251 | -85.97% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2018 | 1763 | 354 | -79.92% | rollup-vs-leaves discrepancy (manual review required) |
| 26001 | 2019 | 1840 | 403 | -78.10% | rollup-vs-leaves discrepancy (manual review required) |
