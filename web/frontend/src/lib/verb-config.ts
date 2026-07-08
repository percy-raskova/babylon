/**
 * Verb catalog — Constitution Article V metadata and target-type gating.
 *
 * Nine atomic player verbs with typed target constraints. Static
 * metadata only (labels, glyphs, target types, cost hints) — target
 * resolution and payload construction live in `@/lib/verbs`
 * (VERB_REGISTRY), fed by the live per-verb endpoints, never fixtures.
 */

import type { V2Verb } from "@/types/v2-types";

/** Constitution Article V — nine atomic player verbs. */
export const VERBS: V2Verb[] = [
  {
    verb: "educate",
    label: "Educate",
    glyph: "◐",
    target_type: "community",
    cost_label: "3 CL",
    desc: "Raise consciousness via political education in a target community.",
  },
  {
    verb: "aid",
    label: "Aid",
    glyph: "◇",
    target_type: "org_or_territory",
    cost_label: "$50",
    desc: "Transfer material resources to allied org or territory infrastructure.",
  },
  {
    verb: "attack",
    label: "Attack",
    glyph: "▲",
    target_type: "org_or_territory",
    cost_label: "8 CL",
    desc: "Targeted sabotage of bourgeois institution. Increases Heat.",
  },
  {
    verb: "mobilize",
    label: "Mobilize",
    glyph: "◈",
    target_type: "community",
    cost_label: "5 SL",
    desc: "Convert sympathizer labor into collective action in a community assembly.",
  },
  {
    verb: "campaign",
    label: "Campaign",
    glyph: "◢",
    target_type: "territory_or_community",
    cost_label: "4 CL",
    desc: "Sustained organizing campaign in a territory or community.",
  },
  {
    verb: "move",
    label: "Move",
    glyph: "→",
    target_type: "territory",
    cost_label: "1 CL",
    desc: "Relocate org HQ or cadre to a new territory.",
  },
  {
    verb: "investigate",
    label: "Investigate",
    glyph: "◉",
    target_type: "any",
    cost_label: "2 CL",
    desc: "Reduce opacity on a target — org, edge, territory, or community.",
  },
  {
    verb: "reproduce",
    label: "Reproduce",
    glyph: "⬡",
    target_type: "org",
    cost_label: "10 CL",
    desc: "Organizational reproduction — convert sympathizers to cadre, train successors.",
  },
  {
    verb: "negotiate",
    label: "Negotiate",
    glyph: "⇄",
    target_type: "org",
    cost_label: "1 CL",
    desc: "Open negotiation channel with another org. Risks legitimacy.",
  },
];

/** Spec 061 US5 T081 / FR-025: verbs whose engine handlers don't exist.
 *  Filtered out of the verb picker and rejected at the action-submit
 *  endpoint server-side. A follow-up spec will add real handlers and
 *  remove entries from this set.
 */
export const DISABLED_VERBS: ReadonlySet<string> = new Set(["investigate", "move", "negotiate"]);

/** VERBS minus disabled verbs — for the verb picker, NavRail, and grids. */
export const SUPPORTED_VERBS = VERBS.filter((v) => !DISABLED_VERBS.has(v.verb));

/** Helper to build the route key for a verb. */
export function verbRouteKey(verb: string): string {
  return `actions/${verb}`;
}
