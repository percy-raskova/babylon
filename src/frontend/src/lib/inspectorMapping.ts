/**
 * Maps a classified event's linked-entity type to the Inspector's
 * `InspectorKind` — the join between the Bottom Strip's events feed and
 * `mapSlice.setSelection` (spec-110 B3 stage 2's "autopause deep-link":
 * clicking an event selects the entity it references).
 *
 * `institution` has no dedicated `InspectorKind` (the inspector endpoint
 * set is `node | org | community | edge | hex`) — it falls back to the
 * generic `node` kind rather than being silently dropped.
 */

import type { ClassifiedEvent } from "@/types/game";
import type { InspectorKind } from "@/store";

const LINKED_ENTITY_TO_INSPECTOR_KIND: Record<
  NonNullable<ClassifiedEvent["linkedEntityType"]>,
  InspectorKind
> = {
  territory: "hex",
  organization: "org",
  institution: "node",
  hyperedge: "community",
};

/** Resolve the `InspectorKind` a classified event's linked entity maps to, or `null` if unlinked. */
export function inspectorKindForEvent(event: ClassifiedEvent): InspectorKind | null {
  if (!event.linkedEntityType || !event.linkedEntityId) return null;
  return LINKED_ENTITY_TO_INSPECTOR_KIND[event.linkedEntityType];
}
