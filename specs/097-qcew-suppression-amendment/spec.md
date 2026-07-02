# Spec-097: QCEW BLS Suppression Spec Amendment — Decision Record

**Status**: FINAL (decision ratified 2026-07-02)
**Created**: 2026-05-16 (deferred from spec-067 T036 finding)
**Renumbered**: 2026-05-17 (was spec-070; relocated to free the audit-assigned
spec-070 slot for Sovereign Topology + Faction Influence + Balkanization per
`reports/aidocs-vs-code-audit-2026-05-16.md` Part 3-FULL Wave 1)
**Finalized**: 2026-07-02
**Owner**: Persephone Raskova (BD)

## Decision

**Strategy 4 — synthetic imputation — is adopted, in the generalized form
specified by spec-086 (`specs/086-qcew-loader-imputation/spec.md`).**

Rather than persisting only a per-(county, year) imputed-total row (the
minimal form of strategy 4 enumerated below), spec-086 reimplements the QCEW
loader (deleted in spec-037) and reconstructs **every** BLS-suppressed
detail cell, constrained by the BLS-published higher-aggregation totals in
the same source file (county Total Covered, county-by-ownership, and the
NAICS 2/3/4/5-digit subtotals), apportioned by establishment counts (which
BLS publishes even when employment and wages are withheld). Every stored
magnitude carries an observed/imputed provenance marker.

### Re-based acceptance targets

The spec-067 ±5 %-on-raw-leaves targets were empirically infeasible (see
Problem below) and are superseded as follows:

| Old target (spec-067) | Disposition |
|---|---|
| FR-006 (±5 % BLS agreement, every county-year) | Superseded by spec-086 FR-002 + SC-001/SC-002: post-imputation reconciliation within **±2 %** for ≥ 99 % of county-years |
| SC-001 (Wayne County MI 2010 within ±5 %) | Superseded by spec-086 SC-003 (Wayne 2010 within ±2 % post-imputation; was −14.6 % on raw leaves) |
| SC-007 (≥ 95 % of MI county-years within ±5 %) | Superseded by spec-086 SC-001/SC-002 (≥ 99 % of ALL county-years within ±2 % post-imputation) |
| SC-006 (originally ±5 % BLS agreement) | Already re-purposed 2026-05-17 into the ε-determinism reproducibility criterion; no further change |

Until spec-086 ships, downstream consumers MUST continue to treat post-067
`v` and `employment_proxy` values as lower-bound estimates of the BLS
publication totals (10–30 % low).

### Rationale

- Strategies 1–3 each trade away something Babylon needs: (1) loosening
  tolerance to ±20–30 % silently corrupts every downstream Marxian quantity
  (v, rate of exploitation, imperial rent) by a county-varying margin;
  (2) `naics_level=4` leaves lose the 6-digit industry detail the tensor
  pipeline joins on; (3) retaining the rollup row restores the exact
  double-count trap spec-067 existed to remove.
- Strategy 4 (generalized) is the only option that reconciles to BLS
  publication AND preserves the canonical 6-digit grain AND keeps the
  spec-067 no-rollup-rows invariant — at the cost of an imputation step,
  which is made auditable via provenance markers and a per-load report
  (spec-086 US3/FR-005/FR-009).
- Establishment counts survive suppression in the staged source (verified
  in the 2023 singlefile), giving a principled apportionment basis;
  hierarchical IPF/RAS-style reconciliation makes the reconstruction
  deterministic (spec-086 FR-008).

### Consequences

- `specs/067-qcew-ownership-normalization/spec.md` FR-006 / SC-001 / SC-007
  carry amendment notes pointing here (applied 2026-07-02).
- Spec-067 remains correct as shipped: rollup deletion eliminated the
  double-count trap; the infeasible band was a data property, not an
  implementation bug.
- The formal ADR for the imputation architecture is recorded at spec-086
  delivery time (next free ADR number). This document is the decision
  record in the interim. (The original acceptance criterion here named
  "ADR046 or an ADR045 amendment", but ADR046 was subsequently consumed by
  the spec-068 BEA I-O ingest.)
- Loader home (owner decision, 2026-07-02): the reimplemented QCEW loader
  lives in the external `babylon-data` package (minimal viable packaging in
  spec-086; full packaging of the remaining ~24 loaders in spec-098). See
  spec-086 Assumptions.

## Problem (as found by spec-067 T036)

Spec-067 successfully normalized `fact_qcew_annual` by deleting BLS-published
rollup rows (NAICS levels 0/2/3/4/5/98/99 + own_code='0'), keeping only the
canonical leaves (`naics_level=6` × `own_code ∈ {'1','2','3','5'}`). However,
the spec's acceptance criteria SC-001 (Wayne County 2010 employment within
±5% of BLS publication), SC-007 (≥95% of Michigan county-years within
±5% of BLS), and FR-006 (general ±5% agreement target) **proved infeasible**
empirically because BLS QCEW suppresses 6-digit National Industry detail
cells for employer confidentiality (low-establishment-count cells are
withheld from publication). The result: `SUM(canonical-leaf employment)` is
systematically 10-30% LOWER than the BLS-published Total Covered rollup value
across Michigan county-years (mean delta -61%; 0% within the spec's ±5%
band; Wayne County 2010: rollup 657,150 vs post-067 SUM 561,173 = −14.6 %).
The spec-067 migration is correct; the data property is what makes the band
target unattainable at `naics_level=6` aggregation.

## Options considered (preserved as evaluated 2026-05-16)

1. **Loosen tolerance to ±20-30%**: Pragmatic acceptance of QCEW's
   confidentiality-protection floor. Lets the spec close as-shipped.
   Implication: downstream consumers must understand that `v` and
   `employment_proxy` are now lower-bound estimates, not the
   BLS-publication ground truth. **Rejected** — silently biases every
   downstream economic quantity.

2. **Use `naics_level=4` leaves**: 4-digit industry-group is closer to the
   BLS Total Covered rollup (~6% delta empirically vs the 14.6% at level 6).
   Requires re-running `tools/normalize_qcew_rollups.py` against the
   backup table with a different predicate (`naics_level NOT IN (0, 5, 6,
   98, 99)`), preserving levels 2-4. Trade-off: loses fine-grained
   industry detail in `dim_industry` joins. **Rejected** — loses the
   6-digit grain the tensor/department mapping consumes.

3. **Retain the `naics_level=0 AND own_code='0'` rollup row** as the
   canonical Total Covered data source: Back to spec-066's pattern, but
   with explicit `WHERE industry_id=1 AND ownership_id=1` filter
   documented in `contracts/post_067_query_contract.md`. Defeats the
   spec-067 "remove the trap" goal but restores BLS-publication fidelity.
   **Rejected** — reintroduces the rollup-vs-leaves double-count trap.

4. **Synthetic imputed totals**: Reconstruct withheld magnitudes so leaves
   reconcile to published totals, with explicit imputation flags.
   **ADOPTED**, generalized from a single imputed-total row to full
   hierarchical cell reconstruction — see Decision above and spec-086.

## Inputs

- spec-067 T036 finding (research.md "T036 finding" section + ADR045
  negative consequences).
- spec-067 audit-report artifact under
  `reports/ingest/qcew_normalization_*.{md,json}` — provides empirical
  per-county delta distribution across all Michigan county-years.
- BLS QCEW confidentiality-protection methodology documentation
  (external, https://www.bls.gov/cew/about-data/confidentiality-protection.htm).
- Consumer code paths in `src/babylon/persistence/{hex_hydrator,
  county_aggregation}.py` — continue to SUM the canonical leaves; spec-086
  FR-010 guarantees they need no further changes.

## Related

- spec-066 (Marx-Coherence Fixes; introduced the defensive filter pattern
  that spec-067 normalized).
- spec-067 (QCEW Ownership and NAICS Hierarchy Normalization; the spec
  amended by this decision).
- **spec-086 (QCEW Loader Reimplementation with Synthetic Suppression
  Imputation; implements this decision)**.
- spec-098 (planned: reference-DB reproducible build pipeline; generalizes
  the loader-restoration pattern spec-086 establishes).
