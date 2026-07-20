/**
 * Frontend mirror of `web/game/fog/filter.py::POLITICAL_FIELDS` /
 * `ORG_POLITICAL_FIELDS` (Track 1 Task 7, 2026-07-18) — same hand-pinned
 * single-source-of-truth pattern `lib/inspect/provenance.ts` uses against
 * `web/game/provenance.py::METRIC_PROVENANCE` (see that file's doc comment
 * for the "no runtime coupling, caught only backend-side" caveat, which
 * applies identically here).
 *
 * This is presentation only: translating a raw gated-field key into a
 * player-legible label. It does NOT decide whether a field is masked (that
 * is `readVisionMasked`'s job, reading the real `vision_masked` list the
 * bridge actually emitted) or fabricate a reason a field is masked — see
 * `adapters/fog.ts` for the single honest WHY sentence this module's
 * callers pair with the label.
 */

import type { InspectionRef } from "@/types/inspection";

/** Mirrors `POLITICAL_FIELDS` (`filter.py:59-68`) plus `ORG_INTERNAL_STATE_FIELDS`
 *  (`filter.py:79-83`) — the full political vocabulary `apply_fog` ever gates,
 *  across every choke point (`_serialize_territory`, `get_inspector_org`,
 *  `get_inspector_hex`, `get_inspector_node`'s generic branch, the hex-rollup
 *  pair, the state-apparatus dashboard). A field absent from this map still
 *  renders — via `fogFieldLabel`'s fallback — as its own raw name, never a
 *  crash, since a future bridge-side addition to `POLITICAL_FIELDS` should
 *  degrade to "unlabeled but still explained", not break the card. */
export const FOG_FIELD_LABELS: Record<string, string> = {
  heat: "Repression Heat",
  agitation: "Mass Agitation",
  solidarity_index: "Class Solidarity",
  dominant_class: "Dominant Class",
  consciousness: "Political Consciousness",
  solidarity: "Solidarity",
  dominant_community: "Dominant Community",
  colonial_stance: "Colonial Stance",
  consciousness_tendency: "Consciousness Tendency",
  cohesion: "Organizational Cohesion",
  cadre_level: "Cadre Level",
};

/** Player-legible label for a gated field name — the raw key itself
 *  (e.g. `"solidarity_index"`) when unmapped, never a thrown error. */
export function fogFieldLabel(field: string): string {
  return FOG_FIELD_LABELS[field] ?? field;
}

/**
 * Build the `fog`-kind `InspectionRef` for `field` — or `undefined` when
 * `field` is not actually in `maskedFields` (the payload's real
 * `vision_masked` list), mirroring `explainRefFor`'s "check eligibility,
 * return undefined otherwise" shape so callers never have to duplicate
 * that guard. Never invents a reason: everything the resolved frame needs
 * (`field`/`nodeType`/`nodeId`/`nodeName`) rides in `inline`, and
 * `adapters/fog.ts` derives WHY from the one invariant `apply_fog`
 * guarantees (masked ⟹ outside organizing reach), not from anything
 * fabricated here.
 */
export function fogRefFor(
  field: string,
  maskedFields: readonly string[],
  nodeType: string,
  nodeId: string,
  nodeName: string | null,
): InspectionRef | undefined {
  if (!maskedFields.includes(field)) return undefined;
  return {
    kind: "fog",
    id: `${nodeType}:${nodeId}:${field}`,
    label: fogFieldLabel(field),
    inline: { field, nodeType, nodeId, nodeName },
  };
}
