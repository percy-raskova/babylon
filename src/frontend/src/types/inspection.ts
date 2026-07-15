/**
 * The frozen InspectionStack data model (architecture.md §2.2). Lane A owns
 * this contract as *types only* — the resolvers, adapters, store slice
 * (`store/slices/inspectSlice.ts`), and rendering components
 * (`components/inspect/*`) belong to Lane C; the additive `/explain/`
 * backend belongs to Lane D. Both consume these shapes without
 * modification.
 *
 * Recursion is uniform: an `InspectionNode` renders as a card of
 * `InspectionSection`s of `InspectionRow`s; any row carrying a `ref`
 * pushes a new `InspectionNode` frame when clicked (entity → metric →
 * formula → input-metric → …), bottoming out at constants/state values.
 */

import type { ConsciousnessVector } from "@/types/game";

/** What an `InspectionRef` points at — one resolver per kind (Lane C). */
export type InspectionRefKind =
  "hex" | "org" | "node" | "edge" | "community" | "metric" | "formula";

/**
 * A pointer to something inspectable. `scope` disambiguates instance data
 * from global aggregates, e.g. `"hex:<h3>"`, `"org:<id>"`, `"global"`.
 *
 * `label` (Lane C, additive — DESIGN_BIBLE.md §4 "same-name discipline"):
 * when a ref is pushed from a click on an `InspectionRow`, the pusher sets
 * `label` to that row's exact `label` text, so the resolved child frame's
 * title can equal the parent row's label verbatim rather than the
 * resolver re-deriving a (possibly differently-worded) title from the
 * fetched payload. Root frames pushed from outside a row (StatChip, map
 * selection) omit it — their title falls back to the resolved entity's
 * own name field.
 */
export interface InspectionRef {
  kind: InspectionRefKind;
  id: string;
  scope?: string;
  label?: string;
  /**
   * A pre-fetched payload the pusher already holds (Lane C, additive). When a
   * map click selects a hex, the clicked deck.gl feature already carries that
   * hex's authoritative per-tick state (the same object the hover `HexTooltip`
   * renders) — attaching it here lets the resolver adapt it directly instead of
   * round-tripping `get_inspector_hex` (stubbed today). Fields the click did not
   * carry stay absent so the adapter renders them as honest nulls (III.11), and
   * the resolver stays pure: `inline` is part of the ref, not a store read.
   * Omitted for refs pushed from a row/provenance click, which fetch as before.
   */
  inline?: Record<string, unknown>;
}

/**
 * How `InspectionRow.value` should be rendered by the `BblData` formatting
 * layer (Lane C's `ValueRow`). Constitution III.11 null-honesty: a `null`
 * value renders "no data" regardless of `format`, never a fabricated 0.
 */
export type BblFormat = "integer" | "decimal2" | "decimal3" | "percent" | "raw";

/** One slice of a composition/breakdown row (consciousness vector, wealth_by_class_role, …). */
export interface InspectionCompositionEntry {
  key: string;
  value: number;
  color?: string;
}

/** One labeled value in an `InspectionSection`. */
export interface InspectionRow {
  label: string;
  value: number | string | null;
  format: BblFormat;
  /** Present when this row is itself explainable — clicking pushes a child frame. */
  ref?: InspectionRef;
  /** Present for composition/breakdown rows rendered as a `BreakdownBar`. */
  composition?: InspectionCompositionEntry[];
  /**
   * Comparison baseline (DESIGN_BIBLE.md §4 "every stat row shows its
   * comparison baseline") — a per-tick series ending at the row's current
   * value, rendered as a `Sparkline` with realized min/max labeled inline.
   * Omitted (not `[]`) when the backing endpoint carries no history for
   * this row — absence, not an empty series, is the honest signal.
   */
  history?: number[];
  /**
   * Marks this row's value as a placeholder for a feature that does not
   * exist in the codebase yet (owner's mock doctrine, Program 17 Wave 1 /
   * W1.4) — still rendered, never silently omitted, but visibly badged.
   * `ValueRow` renders a small `MockBadge` next to the label when `true`.
   */
  mock?: boolean;
  /**
   * Present when this row IS the 4-node imperial-circuit mini-Sankey
   * (Program 17 Wave 1 / W1.6, `EngineBridge.get_inspector_node`'s
   * `circuit_flows`). `ValueRow` renders `ImperialCircuitFlow` instead of a
   * plain value/composition when set.
   */
  circuitFlows?: CircuitFlows;
}

/**
 * One node in the 4-node imperial-circuit Sankey (`circuit_flows.nodes`).
 * Resolved by `SocialRole` on the backend, never a hardcoded id — a scenario
 * missing a role (wayne_county has no `comprador_bourgeoisie` class) simply
 * omits that node, never fabricates one (Constitution III.11).
 */
export interface CircuitFlowNode {
  role: string;
  id: string;
  name: string;
}

/** One directed value-flow link in the imperial circuit (`circuit_flows.links`). */
export interface CircuitFlowLink {
  source_role: string;
  target_role: string;
  source_id: string;
  target_id: string;
  value_flow: number;
}

/**
 * The 4-node imperial-circuit Sankey data
 * (`EngineBridge.get_inspector_node`'s `circuit_flows` key, Program 17 Wave 1
 * / W1.6): Periphery Proletariat -> Comprador Bourgeoisie -> Core Bourgeoisie
 * -> Labor Aristocracy. A role/hop a scenario does not seed is honestly
 * absent from `nodes`/`links` rather than fabricated.
 */
export interface CircuitFlows {
  nodes: CircuitFlowNode[];
  links: CircuitFlowLink[];
}

/** A grouped block of rows within an `InspectionNode`; `label` is optional (ungrouped). */
export interface InspectionSection {
  label?: string;
  rows: InspectionRow[];
}

/** One fully-resolved InspectionStack frame's content. */
export interface InspectionNode {
  ref: InspectionRef;
  title: string;
  sections: InspectionSection[];
}

/**
 * `GET /api/games/:id/explain/?metric=<name>&scope=<scope>` response body
 * (architecture.md §2.4, `web/game/api.py::_explain_result_to_dict`).
 * Additive — Lane D's live contract, mirrored here so
 * `lib/inspect/adapters/metric.ts` and `api/client.ts::fetchExplain` share
 * one typed shape instead of `Record<string, unknown>`.
 */
export interface ExplainInput {
  name: string;
  label: string;
  value: number | string | null;
  kind: "metric" | "constant" | "state";
  ref: string | null;
}

export interface ExplainFormula {
  name: string | null;
  expression: string;
  doc: string;
}

export interface ExplainResponse {
  metric: string;
  scope: string;
  value: number | null;
  formula: ExplainFormula;
  inputs: ExplainInput[];
  constants: ExplainInput[];
}

/**
 * `GET /api/games/:id/node/:entityId/` response body (architecture.md §2.4,
 * `EngineBridge.get_inspector_node`). Two shapes share one endpoint: a
 * `social_class` node gets the wage-pairing/ideology/circuit fields below;
 * every other node type gets an honest enum-normalized dump of its own real
 * fields (Constitution III.11) — hence the index signature for fields this
 * interface does not enumerate. `lib/inspect/adapters/node.ts` discriminates
 * on `type`.
 */
export interface InspectorNodeResponse {
  id: string;
  type: string;
  name: string;
  // social_class-only fields (undefined for every other node type)
  role?: string | null;
  wealth?: number;
  core_wages?: number;
  imperial_rent_gap?: number;
  unearned_increment?: number | null;
  ppp_multiplier?: number | null;
  effective_wealth?: number | null;
  population?: number | null;
  organization?: number | null;
  repression_faced?: number | null;
  subsistence_threshold?: number | null;
  class_consciousness?: number | null;
  national_identity?: number | null;
  agitation?: number | null;
  /** Survival Calculus (Wave 2 W2.5a/W2.5b): `Sigmoid(Wealth - Subsistence)` —
   *  survival probability via acquiescence. Undefined/null until Backend-3
   *  wires `_social_class_inspector_fields` to carry `SurvivalSystem.step`'s
   *  `p_acquiescence` (survival.py:143). */
  p_acquiescence?: number | null;
  /** Survival Calculus: `Organization / Repression` — survival probability
   *  via revolution. Same exposure gap as `p_acquiescence` above. */
  p_revolution?: number | null;
  consciousness?: ConsciousnessVector | null;
  inequality?: number | null;
  class_position?: string;
  class_position_mock?: boolean;
  circuit_flows?: CircuitFlows;
  apologist_claim?: string;
  apologist_refutation?: string;
  [key: string]: unknown;
}
