/**
 * One resolver per `InspectionRef.kind` (architecture.md §2.4) — maps a
 * ref to its endpoint, then its adapter, into a fully-resolved
 * `InspectionNode`. `store/slices/inspectSlice.ts` is the sole caller
 * (`push()`'s fetch); kept a pure module (no store import) so it's
 * testable standalone against MSW fixtures.
 */

import { get as apiGet, fetchExplain } from "@/api/client";
import { endpoints, type Endpoint } from "@/api/endpoints";
import type { InspectionNode, InspectionRef } from "@/types/inspection";
import { adaptHex } from "./adapters/hex";
import { adaptOrg } from "./adapters/org";
import { adaptNode } from "./adapters/node";
import { adaptEdge } from "./adapters/edge";
import { adaptCommunity } from "./adapters/community";
import { adaptMetric } from "./adapters/metric";
import type { RawEntity } from "./adapters/fields";

/** Stable cache/comparison key for an `InspectionRef` — kind+id+scope (label excluded: it's presentational, not identity). */
export function refKey(ref: InspectionRef): string {
  return `${ref.kind}:${ref.id}:${ref.scope ?? ""}`;
}

type EntityRefKind = "hex" | "org" | "node" | "edge" | "community";

const ENTITY_ENDPOINT: Record<EntityRefKind, Endpoint<unknown>> = {
  hex: endpoints.inspectorHex,
  org: endpoints.inspectorOrg,
  node: endpoints.inspectorNode,
  edge: endpoints.inspectorEdge,
  community: endpoints.inspectorCommunity,
};

const ENTITY_ADAPTER: Record<
  EntityRefKind,
  (ref: InspectionRef, data: RawEntity) => InspectionNode
> = {
  hex: adaptHex,
  org: adaptOrg,
  node: adaptNode,
  edge: adaptEdge,
  community: adaptCommunity,
};

async function resolveEntityRef(
  gameId: string,
  ref: InspectionRef,
  kind: EntityRefKind,
): Promise<InspectionNode> {
  // Inline payload the pusher already held (e.g. a map click carrying the
  // clicked feature's own state) — adapt it directly, no fetch. Keeps the
  // module pure (operates only on the ref) and correct-by-source: the same
  // authoritative per-hex data the tooltip shows, not a stubbed endpoint.
  if (ref.inline) {
    return ENTITY_ADAPTER[kind](ref, ref.inline);
  }
  const res = await apiGet<RawEntity>(ENTITY_ENDPOINT[kind].path({ id: gameId, entityId: ref.id }));
  if (res.status !== "ok") {
    throw new Error(res.message ?? `Failed to load ${kind} ${ref.id}`);
  }
  return ENTITY_ADAPTER[kind](ref, res.data ?? {});
}

async function resolveMetricRef(gameId: string, ref: InspectionRef): Promise<InspectionNode> {
  const scope = ref.scope ?? "global";
  const res = await fetchExplain(gameId, ref.id, scope);
  if (res.status !== "ok") {
    throw new Error(res.message ?? `Failed to explain ${ref.id} at ${scope}`);
  }
  return adaptMetric(ref, res.data);
}

/**
 * Resolve one `InspectionRef` into its `InspectionNode`. Throws on any
 * non-"ok" API response (loud failure — `inspectSlice` catches this and
 * puts the frame in its `error` state, per Constitution III.11: a failed
 * fetch renders a visible error, never a silently-empty card).
 */
export async function resolveRef(gameId: string, ref: InspectionRef): Promise<InspectionNode> {
  switch (ref.kind) {
    case "hex":
    case "org":
    case "node":
    case "edge":
    case "community":
      return resolveEntityRef(gameId, ref, ref.kind);
    case "metric":
    case "formula":
      // "formula" has no distinct backend endpoint today — the /explain/
      // response for a metric already IS its terminal FormulaCard, so a
      // "formula" ref (should one ever be pushed independently of a
      // metric) resolves identically.
      return resolveMetricRef(gameId, ref);
  }
}
