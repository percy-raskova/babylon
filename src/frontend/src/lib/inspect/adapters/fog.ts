/**
 * `fog`-kind resolver adapter (Track 1 Task 7, 2026-07-18) — "no fogged dead
 * ends". A masked political field renders as `null` at the serialization
 * boundary (`web/game/fog/filter.py::apply_fog`); clicking it (see
 * `fogRefFor` in `../fogFields.ts`, wired into `genericEntity`/`org`/`hex`)
 * pushes one of these frames instead of leaving the player at a bare
 * "no data" dead end.
 *
 * Resolved synchronously from `ref.inline` (see `resolvers.ts`) — no fetch,
 * because everything the card needs was already known at push time.
 *
 * **The WHY sentence is not a guess.** `apply_fog`'s own contract (see its
 * docstring's "precedence" section) is: a node's political fields can only
 * land in `vision_masked` when that node is OUTSIDE organizing reach — the
 * "reach wins outright" branch returns before any field is ever masked. So
 * "outside your organizing reach" is the one honest, invariant-guaranteed
 * reason for ANY masked field, today and after Task 9 wires a real intel
 * ledger — `read_intel` collapses "never observed" and "observed so long
 * ago it doesn't matter" into the identical `"unknown"` tier (by design,
 * `ledger.py`'s `read_intel` discards `tick_observed` once an entry goes
 * stale), so there is no further true distinction this frame could draw
 * even if the bridge were extended to expose the raw tier.
 */

import type { InspectionNode, InspectionRef } from "@/types/inspection";
import { fogFieldLabel } from "../fogFields";
import type { RawEntity } from "./fields";

/** Player-legible noun phrase for the masked node's own type — falls back to
 *  "this" for a node type not yet named here, never a crash. */
const SUBJECT_BY_NODE_TYPE: Record<string, string> = {
  territory: "This territory",
  organization: "This organization",
  faction: "This faction",
};

function readOptionalString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function adaptFog(ref: InspectionRef, inline: RawEntity): InspectionNode {
  const field = readOptionalString(inline.field) ?? ref.label ?? ref.id;
  const nodeType = readOptionalString(inline.nodeType);
  const nodeName = readOptionalString(inline.nodeName);
  const label = fogFieldLabel(field);
  const subject = (nodeType !== null && SUBJECT_BY_NODE_TYPE[nodeType]) || "This";

  return {
    ref,
    title: `Unknown: ${label}`,
    sections: [
      {
        rows: [
          { label: "What", value: label, format: "raw" },
          {
            label: "Why",
            value:
              `${subject} is outside your organization's reach, and you hold no ` +
              "intelligence on it.",
            format: "raw",
          },
          {
            label: "Subject",
            value: nodeName ?? ref.id,
            format: "raw",
          },
        ],
      },
    ],
  };
}
