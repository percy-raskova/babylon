# Phase 0 Research: Cross-Scale Integration

**Feature**: 062-cross-scale-integration
**Date**: 2026-05-12
**Status**: Complete

Six items required Phase 0 resolution: five deferred from `/speckit.clarify` (Q5 + three architectural-input uncertainties), and one constitutional gap surfaced during the gate review (Detroit-Windsor / Canada).

Each item is documented in the speckit-canonical `Decision / Rationale / Alternatives considered` format.

---

## §1 — α_annual empirical calibration target (R1)

**Decision**: `α_annual = 0.01` (matches existing `HexEqualizationComputer.equalize_capital(grid, alpha=0.01)`). Runtime derives `α_weekly = 1 − (1 − α_annual)^(1/52) ≈ 1.931e-4`. Empirical re-calibration against historical BEA county-level rate-of-profit convergence is deferred to a separate downstream spec (not blocking).

**Rationale**:
- The existing codebase already uses `0.01` as the α coefficient in `HexEqualizationComputer`. Adopting it as `α_annual` preserves the prior empirical calibration without churning every place that calls the equalizer.
- The geometric weekly form gives a half-life equalization horizon of `ln(2) / ln(1 − α_weekly) ≈ 3,585` weeks ≈ 69 years. This is "substantially longer than one tick" per FR-029 (orders of magnitude beyond the 780-tick Detroit scenario).
- Constitution III.1 (No Magic Constants) traces this number to the prior prototype's calibration choice. The prototype itself derived `0.01` from per-tick stability analysis (the existing code is the documented source).
- The startup invariant `α_weekly < 1/52` (FR-029a) is satisfied by a large margin: `1.93e-4 < 1/52 ≈ 1.92e-2`.

**Alternatives considered**:
- `α_annual = 0.10` (faster ~7-year half-life): no empirical justification; would change the qualitative behavior of equalization on the Detroit test case without supporting data.
- Zero default with mandatory pre-session configuration: over-strict; blocks turnkey scenario runs and adds friction without reducing risk.
- Two-tier (`α_annual_within_industry` + `α_annual_cross_industry`): premature optimization. The spec's FR-029/FR-030 already treats equalization as within-industry-only across hexes; there is no cross-industry equalization to tune separately.

---

## §2 — BoundaryFlowRegister hex-pair dimensional fields (R2)

**Decision**: Extend the `boundary_flow_register` row schema with **three** dimensional fields: `source_node_id TEXT`, `dest_node_id TEXT`, `node_kind_discriminator TEXT` (enum: `'hex' | 'county' | 'state' | 'national' | 'external'`). The discriminator distinguishes which ID space each end of the dyadic flow lives in; the IDs themselves are H3 hex indexes, FIPS codes, "USA", or external-node identifiers.

Worked example rows:

| tick | source_node_id | source_kind | dest_node_id | dest_kind | flow_type | magnitude |
|---|---|---|---|---|---|---|
| 137 | `872d34a89ffffff` (hex) | hex | `872d34b0bffffff` (hex) | hex | `vol_ii_commute_v` | 12.4 |
| 137 | `china_aggregate` (ext) | external | `26163` (Wayne County FIPS) | county | `phi_drain` | 18432.7 |
| 137 | `872d34c14ffffff` (hex) | hex | `rest_of_usa` (ext) | external | `vol_ii_commute_v_out` | 3.1 |

**Rationale**:
- The architectural input flagged ~75% confidence on whether per-hex precision was needed. The Detroit-Windsor case (workers commuting at specific hex pairs across the Canadian border) requires per-hex precision for any subsequent political-economic analysis at the boundary. Without it, the boundary register is a county-level aggregate and the hex-grid investment is wasted at the boundary.
- TEXT columns + a single `node_kind_discriminator` enum is more compact than separate `source_hex / source_county / source_state / source_external` sparse columns. Index queries (`WHERE source_kind = 'hex' AND source_node_id = $hex_id`) remain fast with appropriate B-tree indexes.
- Constitution II.9 (Morphism as Dyadic Relation) is satisfied — each row is one dyadic source→dest flow.
- The fields enable the queries that User Story 6's acceptance scenarios already assume (e.g., "the recorded tuple identifies the source hex, the destination external node, the flow type, the magnitude, and the tick").

**Alternatives considered**:
- Separate `source_hex / source_county / source_external` columns: more strictly typed but creates sparse rows where most columns are NULL. The discriminator-enum pattern is the standard JSON/relational approach.
- Single JSON column for source/dest objects: too unstructured for index queries; PostgreSQL JSONB indexes exist but are not as fast as B-tree on TEXT for this query shape.
- Keep aggregate-only register without hex-pair precision: rejected — violates Detroit-Windsor analytical requirements and would force a re-design of the register schema later.

---

## §3 — Crisis machinery weekly-cadence verification (R3)

**Decision**: The existing `ContradictionField + FieldDerivative + EdgeTransition` machinery is tick-frequency-agnostic and operates correctly under weekly cadence. The verification action is a **property test suite** (Hypothesis-based, per the Spec 053–056 harness) that confirms:

1. Threshold crossings produce categorical coefficient resets within a single tick (per Constitution II.4 — crisis is discontinuous, not gradual);
2. Sub-tick dynamics that would resolve in less than one week (e.g., a 3-day financial panic) aggregate into a single tick's coefficient reset without violating per-tick conservation;
3. Each crisis-reset event is logged in the conservation audit log with `severity='alarm'` per FR-046 + FR-047, including identification of which threshold was crossed.

The verification suite lives at `tests/property/test_crisis_machinery_weekly_cadence.py` (new) and runs as part of `mise run test:int`.

**Rationale**:
- Constitution II.4 (Quantities vs Coefficients) states that crisis is a discontinuous coefficient reset, not gradual drift. This property is tick-frequency-independent: whether the tick is quarterly or weekly, a threshold crossing at tick `t` produces a reset at exactly `t`. The geometry doesn't change with tick frequency.
- The architectural input's ~70% confidence reflected uncertainty about whether the existing code respected this. The correct closing move is **verification (property test), not redesign**.
- The audit log integration is the new wiring: FR-046/FR-047 require crisis-reset events to appear as `severity='alarm'` audit rows so they're forensically traceable. This is testable.

**Alternatives considered**:
- Redesign crisis machinery for explicit weekly cadence: out of scope and likely unnecessary; would also touch many specs unrelated to 062.
- Disable crisis machinery during weekly-cadence simulations until verified: rejected because it removes load-bearing behavior the spec depends on (the audit log alarm path).
- Treat crisis as multi-tick by smoothing the reset over N ticks: violates Constitution II.4 (no gradual quality gradients; transitions are discrete).

---

## §4 — Canada (Windsor) as Detroit-Windsor boundary node (R4, GATE-5)

**Decision**: Add **Canada** as a first-class international boundary external node alongside the existing seven world-region nodes (China, EU, India, Sub-Saharan Africa, Latin America, Russia/CSI, Southeast Asia). Canada's external node carries Canada-specific state: bilateral trade volumes (from Comtrade/Ricci for US-Canada), water-rights edges (Great Lakes Compact), and cross-border commute flows (LODES MI-ON border subset).

The Detroit-Windsor corridor (Constitution IV.1) uses Canada as the destination/source for cross-border commute, automotive supply chain (Big Three plants in Windsor + Brampton), and water rights. **FR-036 is updated** to include Canada in the minimum external node list, raising the count from 7 to 8.

**Rationale**:
- Constitution IV.1 makes Detroit-Windsor a required boundary condition, not optional. Rest-of-USA cannot absorb Canada-bound flows because Canada is a sovereign nation with different citizenship regime, different labor laws, different repression budget — all of which are politically and economically distinct from internal US flows.
- Detroit's tri-county study area has substantial cross-border economic flow (automotive supply chain, water, energy). Collapsing into Rest-of-USA loses the analytical surface that Constitution IV.1 mandates be preserved.
- Constitutional Gate-5 closes here.

**Alternatives considered**:
- Defer Canada to a future spec: rejected — Constitution IV.1 is non-negotiable and violating it would block downstream Detroit-Windsor work.
- Use a hyperedge (USMCA / North American free trade bloc) to capture multi-country trade: rejected — IV.1 names Canada specifically. USMCA could be a future hyperedge overlay but doesn't replace the dyadic Canada boundary.
- Model Windsor as a US-side boundary hex: rejected — Windsor is sovereign Canadian territory. Treating it as a US hex would violate Constitution I.20 (Spatial Substrate as Immutable Ground Truth — federal data + H3 grid are the substrate; political boundaries are overlays).

**Spec amendment**: An addendum to `spec.md` FR-036 adds Canada to the minimum external node list. The amendment is captured in the Clarifications section as a v2 entry under the same session date.

---

## §5 — Subsystem table ownership registry (R5, GATE-3)

**Decision**: Each new table family is owned by exactly one subsystem. Cross-subsystem reads happen through declared interfaces (Python typed protocols + SQL views), satisfying Constitution II.11.

| Table family / view | Owner subsystem | Declared cross-subsystem read interface |
|---|---|---|
| `immutable_reference_*` (table family) | `persistence` | `ImmutableReferenceLookup` Python protocol (typed) |
| `dynamic_hex_state` (table) | `persistence` | NetworkX hydration via `PostgresRuntime.hydrate_state()` |
| `dynamic_external_node_state` (table) | `persistence` | NetworkX hydration via `PostgresRuntime.hydrate_state()` |
| `boundary_flow_register` (table) | `economics` | `BoundaryFlowRegister.query(tick, source, dest, …)` Python facade |
| `conservation_audit_log` (table) | `persistence` | `ConservationAuditQuery.fetch(tick, scale, invariant, …)` Python facade |
| `v_county_value_aggregate` (view) | `persistence` | View IS the interface (read SELECT permitted from any subsystem) |
| `v_state_value_aggregate` (view) | `persistence` | View IS the interface |
| `v_national_value_aggregate` (view) | `persistence` | View IS the interface |
| `v_global_phi_balance` (view) | `economics` | View IS the interface |

**Rationale**:
- Constitution II.11 explicitly permits three cross-subsystem read patterns: "SQL views with explicit contracts, RPC boundaries, or event streams". The chosen pattern is SQL views (for aggregations) + Python typed-protocol facades (for filtered row queries with type-aware deserialization).
- All raw-state tables go to `persistence` (consistent with existing Spec 037 conventions). Derived/computed tables (`boundary_flow_register` is computed during the economics-stage of the tick) go to `economics`.
- The two view-owners (`persistence` for hierarchical aggregates of value-substance; `economics` for the global Φ-balance which spans periphery/core) are split because the aggregation logic differs: hierarchical aggregates are pure SQL `SUM` over child hexes; the Φ-balance requires economics knowledge of which external nodes are "periphery" and which are "core".

**Alternatives considered**:
- Single-subsystem ownership (`persistence` for everything): rejected because `boundary_flow_register` writes happen inside the economics-stage of the tick; ownership should track write authority, not just table location.
- No declared interfaces, just direct table access: violates Constitution II.11. Would create undefined behavior per the principle.
- Event-stream pattern for every cross-subsystem read: over-engineered for a read-mostly aggregation workload. Events make sense for write notifications, not for bulk reads.

---

## §6 — Vol II circulation as min-cost flow component (R6, GATE-4)

**Decision**: Vol II circulation in this feature uses the **min-cost flow component** of Constitution II.13 Transport Substrate — specifically, the LODES OD (origin-destination) matrix is treated as a static deterministic routing tableau (one annual matrix per simulated year, applied uniformly across the 52 weeks per FR-028). The matrix is represented as `scipy.sparse.csr_matrix` per Constitution II.12. Slime-mold conductivity routing (the emergent informal-economy component of II.13) is **explicitly out of scope for v1 of this feature** and is deferred to a downstream spec.

**Rationale**:
- Constitution II.13 names both mechanisms. The LODES dataset (Longitudinal Employer-Household Dynamics workplace-area characteristics) is the federal-statistics-grounded deterministic commute matrix; it fits the min-cost flow form and provides empirical calibration for the Detroit tri-county.
- Slime-mold conductivity routing requires informal-economy survey data (e.g., migrant labor networks, off-the-books supply chains) that isn't part of the existing fixture data catalog (Constitution III.4.1) and would need new sources, new constitutional approvals, and new calibration work. Including it in v1 of this feature is scope creep per VI.3.
- The deterministic component is what's load-bearing for SC-011 (per-stage conservation) and User Story 4 acceptance scenarios. Adding slime-mold later as an overlay does not break any v1 invariants.
- A forward-pointer comment in the implementation marks the integration point for the future spec (likely 063 or 064): the LODES OD matrix is the "base layer" over which slime-mold conductivity will route additional flows.

**Alternatives considered**:
- Build full Transport Substrate (both mechanisms) in this spec: scope creep per VI.3; violates "Flag Scope Creep — Must trace to Detroit prediction or improve falsifiability. Otherwise DEFER."
- Skip Vol II entirely until full Transport Substrate is designed: rejected — FR-028 is load-bearing and the deterministic LODES component is well-defined.
- Use a simpler nearest-neighbor flow without referring to Transport Substrate at all: violates Constitution II.13. Even if minimal, the Vol II circulation MUST be grounded in the II.13 framework.

---

## Summary of Phase 0 Outputs

| Item | Resolved? | Spec amendment? | Downstream spec spawned? |
|---|---|---|---|
| R1 α_annual | ✅ (0.01) | No — already configurable in GameDefines | Yes (empirical re-calibration, future) |
| R2 Hex-pair fields | ✅ (TEXT + discriminator) | No — implementation detail of FR-040 | No |
| R3 Crisis weekly cadence | ✅ (property test) | No | No |
| R4 Canada boundary | ✅ (8th external node) | **Yes — FR-036 update + Clarifications addendum** | No |
| R5 Table ownership | ✅ (registry table) | No — Phase 1 data-model.md captures it | No |
| R6 Vol II = min-cost flow | ✅ (slime-mold out of scope) | No | Yes (slime-mold conductivity, future) |

All constitutional gates close. Phase 1 design proceeds.
