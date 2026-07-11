/**
 * Frontend mirror of `web/game/provenance.py::METRIC_PROVENANCE` (spec-113
 * Lane C, architecture.md §2.4) — same single-source-of-truth pattern
 * `lib/lens.ts` uses against `map_contract.py`.
 *
 * This lets `ValueRow`/adapters decide whether a raw field is explainable
 * (and for which scope kinds) WITHOUT a probe request: a field only gets
 * an "explain" affordance when its name is a key here AND the requesting
 * scope kind is in its `supportedScopes`. The manifest names, scopes, and
 * human labels are hand-pinned against the backend module (see
 * `provenance.test.ts`'s doc comment for the pairing) — if the backend
 * manifest gains/loses an entry, this file needs a matching edit (no
 * runtime coupling, so nothing fails loudly if it drifts; caught by
 * `web/game/tests/test_provenance.py`'s manifest-contract test only on
 * the backend side).
 */

import type { InspectionRef } from "@/types/inspection";

/** The three scope kinds the `/explain/` endpoint's grammar supports. */
export type ExplainScopeKind = "global" | "hex" | "org";

interface ProvenanceMirrorEntry {
  /** Human label for the metric itself (used when no row already labels it). */
  label: string;
  supportedScopes: readonly ExplainScopeKind[];
}

/** Mirrors `web/game/provenance.py::METRIC_PROVENANCE`'s keys + `supported_scopes`. */
export const METRIC_PROVENANCE_MIRROR: Record<string, ProvenanceMirrorEntry> = {
  value_extraction_ratio: { label: "Exchange ratio", supportedScopes: ["global"] },
  exploitation_rate: { label: "Exploitation rate", supportedScopes: ["global"] },
  profit_rate: { label: "Profit rate", supportedScopes: ["global", "hex"] },
  occ: { label: "Organic composition of capital", supportedScopes: ["global", "hex"] },
  imperial_rent: { label: "Imperial rent Φ", supportedScopes: ["global"] },
  labor_aristocracy_ratio: { label: "Labor aristocracy ratio", supportedScopes: ["org"] },
  revolution_probability: { label: "Revolution probability", supportedScopes: ["org"] },
  acquiescence_probability: { label: "Acquiescence probability", supportedScopes: ["org"] },
  consciousness_drift: { label: "Consciousness drift", supportedScopes: ["org"] },
};

/** Whether `metric` is explainable for `scopeKind` per the mirrored manifest. */
export function isExplainableMetric(metric: string, scopeKind: ExplainScopeKind): boolean {
  const entry = METRIC_PROVENANCE_MIRROR[metric];
  return entry !== undefined && entry.supportedScopes.includes(scopeKind);
}

/**
 * Build the `metric`-kind `InspectionRef` for `metric` at `scope`
 * (canonical string form, e.g. `"global"`/`"hex:<h3>"`/`"org:<id>"`) — or
 * `undefined` when the mirrored manifest doesn't recognize `metric` for
 * `scopeKind` (rendered as a plain, non-explainable row; never a fabricated
 * affordance for data the backend can't actually resolve).
 */
export function explainRefFor(
  metric: string,
  scope: string,
  scopeKind: ExplainScopeKind,
  label?: string,
): InspectionRef | undefined {
  if (!isExplainableMetric(metric, scopeKind)) return undefined;
  return { kind: "metric", id: metric, scope, label };
}
