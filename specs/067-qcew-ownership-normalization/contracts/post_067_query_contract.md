# Post-067 Query Contract for Downstream Consumers of `fact_qcew_annual`

**Status**: contract document; binding on `src/babylon/persistence/hex_hydrator.py` and `src/babylon/persistence/county_aggregation.py` and any future consumer of QCEW data.

## Summary

After spec-067 lands, the `fact_qcew_annual` table contains **only the canonical-leaf rows** — one row per `(county, NAICS 6-digit National Industry, canonical ownership level, time, establishment-size class)`. The BLS-published rollup rows (NAICS levels 0-5; "Total Covered" ownership) are no longer present.

Consumers MUST update their queries from the **SELECT-rollup-row** pattern (which spec-066 introduced as a hotfix) to the **SUM-the-leaves** pattern. This document specifies the contract.

---

## Pre-067 (spec-066 hotfix) query pattern — DEPRECATED post-067

```sql
SELECT
    fq.total_wages_usd,
    fq.employment
FROM fact_qcew_annual fq
JOIN dim_time t ON fq.time_id = t.time_id
WHERE fq.county_id = ?
  AND t.year = ?
  AND fq.industry_id = 1       -- BLS "All Industries" rollup (the "10" supersector)
  AND fq.ownership_id = 1;     -- BLS "Total Covered" ownership rollup (own_code '0')
```

**Result post-067**: Zero rows. The filter selects rollup rows that have been DELETE'd.

---

## Post-067 query pattern — REQUIRED

```sql
SELECT
    SUM(fq.total_wages_usd) AS total_wages,
    SUM(fq.employment)      AS total_employment
FROM fact_qcew_annual fq
JOIN dim_time t ON fq.time_id = t.time_id
WHERE fq.county_id = ?
  AND t.year = ?;
-- No industry filter needed (only naics_level=6 rows remain).
-- No ownership filter needed (only canonical ownership rows remain).
```

**Result post-067**: A single row containing the SUM across all 6-digit National Industries × 4 canonical ownership levels × all establishment-size codes for the (county, year). This SUM is the BLS-agreement total within ±5% per FR-006.

---

## Variant: private-sector-only totals

If a consumer specifically needs private-sector totals (e.g., for variable-capital `v` in the Marxian sense — capital paying wage labor, excluding government employment), the post-067 query MUST explicitly filter by the `is_private` flag on `dim_ownership`:

```sql
SELECT
    SUM(fq.total_wages_usd) AS private_total_wages,
    SUM(fq.employment)      AS private_total_employment
FROM fact_qcew_annual fq
JOIN dim_time t ON fq.time_id = t.time_id
JOIN dim_ownership o ON fq.ownership_id = o.ownership_id
WHERE fq.county_id = ?
  AND t.year = ?
  AND o.is_private = TRUE;
```

This is explicit, self-documenting, and resilient to future changes in the rollup-vs-leaf encoding.

**Note**: This is NOT a defensive filter (the kind spec-067 removes). It is a semantically-justified filter selecting a meaningful subset of the canonical data. The post-067 contract preserves the per-ownership-level granularity expressly so consumers can express such selections clearly.

---

## Variant: per-industry-class totals (e.g., manufacturing only)

Similarly, per-industry filtering MUST use the `dim_industry` semantic columns:

```sql
SELECT
    i.naics_code,
    i.industry_title,
    SUM(fq.employment) AS sector_employment
FROM fact_qcew_annual fq
JOIN dim_time t ON fq.time_id = t.time_id
JOIN dim_industry i ON fq.industry_id = i.industry_id
WHERE fq.county_id = ?
  AND t.year = ?
  AND i.sector_code = '31'   -- Manufacturing (2-digit NAICS sector)
GROUP BY i.naics_code, i.industry_title;
```

Note that grouping by `naics_code` rather than `industry_id` yields the National-Industry breakdown directly.

---

## Backward-compatibility for retained code paths

Queries that legitimately ARE filtering for a specific ownership or industry (i.e., not the rollup-as-denominator pattern) remain valid:

```sql
-- Legitimate: Federal-government-only employment in Wayne County 2010.
WHERE fq.ownership_id = (SELECT ownership_id FROM dim_ownership WHERE own_code = '1');
```

These queries work identically pre- and post-067, because the filtered row is a canonical leaf, not a rollup.

The grep-based enforcement (per R6) targets only the spec-066 hotfix pattern (`= 1` against the rollup IDs in our local schema), not legitimate per-ownership / per-industry filters that join through the `dim_*.own_code` / `naics_code` semantic columns.

---

## Performance contract

Per spec-067 plan.md R2 risk register:
- Pre-067 SELECT pattern: O(1) primary-key lookup, ~1ms per query.
- Post-067 SUM pattern: O(N_industries × N_ownerships) per query — approximately 1000 × 4 = 4000 row aggregation per (county, year). With the existing `idx_qcew_county_time` index this is ~10–50ms per query.

For the 520-tick Michigan-Canada canonical run, the consumer code path executes ~166K such queries (83 counties × 2 fetches × 520 ticks × 2 query types). Estimated wallclock impact: +30 min versus pre-067, within the spec-066-relaxed 90-min budget. **Spec-069 (SQLite read caching, separate deferred follow-up) will reclaim this and tighten the budget further.**

---

## Acceptance test

After every spec-067 implementation commit, the following test MUST pass:

```python
def test_post_067_consumer_queries_produce_bls_agreement():
    """Acceptance test for spec-067 FR-003 + SC-001 + SC-007."""
    session = get_reference_session()

    # Wayne County 2010 (SC-001).
    total = session.execute(
        "SELECT SUM(employment) FROM fact_qcew_annual fq "
        "JOIN dim_county c ON fq.county_id = c.county_id "
        "JOIN dim_time t ON fq.time_id = t.time_id "
        "WHERE c.fips_code = '26163' AND t.year = 2010"
    ).scalar()
    assert 627_000 <= total <= 693_000, (
        f"Wayne 2010 employment {total} outside BLS-publication ±5% band"
    )

    # Every Michigan county-year (SC-007): ≥95% within ±5% BLS band.
    counts = session.execute(...).fetchall()
    within_band = sum(1 for r in counts if abs(r.delta_pct) <= 5)
    assert within_band / len(counts) >= 0.95, (
        f"Only {within_band}/{len(counts)} county-years within BLS ±5% band"
    )
```

---

## Forward compatibility

If a future spec re-introduces rollup rows (e.g., as a denormalization performance optimization), it MUST:

1. Add a discriminator column (`is_rollup BOOLEAN`) to `fact_qcew_annual`.
2. Update this contract to require `WHERE is_rollup = FALSE` on all consumer queries.
3. Run a fresh audit comparable to the spec-067 audit-report format.

This contract document is the schema-stability anchor — schema changes that break it require an explicit spec amendment.

---

## Known limitation: BLS confidentiality suppression at 6-digit NAICS (2026-05-16)

The post-067 SUM-the-leaves pattern returns a value that is **systematically lower** than the BLS-published Total Covered rollup by **10-30%** for QCEW data, due to BLS's confidentiality suppression of low-establishment-count 6-digit cells. Wayne County, MI 2010 example: pre-067 rollup row returned 657,150 employment; post-067 SUM(leaves) returns 561,173 (−14.6%).

**Implications for consumers**:

- The acceptance test at the bottom of this document assumes `SUM(leaves) ∈ [627K, 693K]` (Wayne 2010 ±5% band). That assumption is **false** for QCEW data; the post-067 SUM is closer to 561K. Either:
  - The test target should be widened to ±20-30% (the empirically-observed QCEW suppression band), OR
  - The query should aggregate from a coarser NAICS level (e.g., `naics_level=4` industry-group) that retains more of the suppressed leaf data.
- Consumers that need BLS-publication-fidelity totals (not approximate sums) should use the variant queries described above with explicit `WHERE` clauses against `dim_industry.naics_level` or use a higher-aggregation rollup that's been retained — see spec-070 stub for the four mitigation options being evaluated.
- The spec-067 migration itself is **correct**: the rollup rows ARE redundant when summed alongside the leaves, and removing them eliminates the double-count trap. The trade-off is purely about the fidelity of the resulting aggregate vs. the BLS publication.

See `specs/067-qcew-ownership-normalization/research.md` "T036 finding" and `ai-docs/decisions/ADR045_qcew_normalization.yaml` "negative consequences" for the full empirical analysis and mitigation options.
