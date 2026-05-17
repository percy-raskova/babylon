# Spec-070: QCEW BLS Suppression Spec Amendment (placeholder)

**Status**: PLACEHOLDER (deferred from spec-067 T036 finding)
**Created**: 2026-05-16
**Owner**: TBD

## Scope (one-paragraph stub)

Spec-067 successfully normalized `fact_qcew_annual` by deleting BLS-published
rollup rows (NAICS levels 0/2/3/4/5/98/99 + own_code='0'), keeping only the
canonical leaves (`naics_level=6` × `own_code ∈ {'1','2','3','5'}`). However,
the spec's acceptance criteria SC-001 (Wayne County 2010 employment within
±5% of BLS publication), SC-006/SC-007 (≥95% of Michigan county-years within
±5% of BLS), and FR-006 (general ±5% agreement target) **proved infeasible**
empirically because BLS QCEW suppresses 6-digit National Industry detail
cells for employer confidentiality (low-establishment-count cells are
withheld from publication). The result: `SUM(canonical-leaf employment)` is
systematically 10-30% LOWER than the BLS-published Total Covered rollup value
across Michigan county-years (mean delta -61%; 0% within the spec's ±5%
band). The spec-067 migration is correct; the data property is what makes
the band target unattainable at `naics_level=6` aggregation.

## Decision needed

Spec-070 will pick ONE of these four mitigation strategies and amend the
SC-001 / SC-006 / SC-007 / FR-006 numeric targets accordingly:

1. **Loosen tolerance to ±20-30%**: Pragmatic acceptance of QCEW's
   confidentiality-protection floor. Lets the spec close as-shipped.
   Implication: downstream consumers must understand that `v` and
   `employment_proxy` are now lower-bound estimates, not the
   BLS-publication ground truth.

2. **Use `naics_level=4` leaves**: 4-digit industry-group is closer to the
   BLS Total Covered rollup (~6% delta empirically vs the 14.6% at level 6).
   Requires re-running `tools/normalize_qcew_rollups.py` against the
   backup table with a different predicate (`naics_level NOT IN (0, 5, 6,
   98, 99)`), preserving levels 2-4. Trade-off: loses fine-grained
   industry detail in `dim_industry` joins.

3. **Retain the `naics_level=0 AND own_code='0'` rollup row** as the
   canonical Total Covered data source: Back to spec-066's pattern, but
   with explicit `WHERE industry_id=1 AND ownership_id=1` filter
   documented in `contracts/post_067_query_contract.md`. Defeats the
   spec-067 "remove the trap" goal but restores BLS-publication fidelity.
   Pragmatic when the spec-067 migration tool is retained for its
   ergonomic value (one less rollup-vs-leaves trap during consumer
   query writing).

4. **Synthetic imputed-total row**: Compute the per-(county, year) total
   as `MAX(naics_level=0 sum, SUM(naics_level=6 leaves))` and persist as
   a flagged `is_imputed_total = TRUE` row. Consumers explicitly select
   this row for "BLS-fidelity total" use cases. Most complex; introduces
   a new data attribute. Reserved for the case where spec-070 also
   wants to support sub-(county, year) granularity recovery for
   suppressed cells.

## Inputs

- spec-067 T036 finding (research.md "T036 finding" section + ADR045
  negative consequences).
- spec-067 audit-report artifact under
  `reports/ingest/qcew_normalization_*.{md,json}` — provides empirical
  per-county delta distribution across all Michigan county-years.
- BLS QCEW confidentiality-protection methodology documentation
  (external, https://www.bls.gov/cew/about-data/confidentiality-protection.htm).
- Consumer code paths in `src/babylon/persistence/{hex_hydrator,
  county_aggregation}.py` — currently SUM the canonical leaves;
  potentially need re-refactor depending on chosen strategy.

## Acceptance criteria (high-level)

- Spec-070 selects one of strategies (1)-(4) with documented rationale
  in `decisions/` ADR046 (or amendment to ADR045).
- spec-067 SC-001 / SC-006 / SC-007 / FR-006 targets are updated in
  `specs/067-qcew-ownership-normalization/spec.md` to reflect the
  chosen tolerance.
- If strategy (2) or (3) is selected, spec-070 ships the migration-
  rerun or query-pattern restoration as a coordinated change.
- All 70 spec-067 tasks marked complete in `tasks.md` (the four
  blocked-on-amendment SCs are now resolvable).

## Dependencies

- spec-067 T036 completion (audit-report artifact must exist).
- Cross-references ADR045 mitigation options as starting point.

## Related

- spec-066 (Marx-Coherence Fixes; introduced the defensive filter pattern
  that spec-067 normalized).
- spec-067 (QCEW Ownership and NAICS Hierarchy Normalization; this is the
  spec being amended).
- spec-086 (QCEW Loader Reimplementation; would close the long-deferred
  ingestion gap that prevents alternative strategies like re-ingesting
  with `agglvl_code` preserved).
