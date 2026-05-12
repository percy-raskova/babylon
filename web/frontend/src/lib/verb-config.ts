/**
 * Verb registry — target-type gating, per-verb parameter schemas.
 *
 * Constitution Article V: nine atomic player verbs with typed target constraints.
 * Per Article IV (dual graph), hyperedges and dyadic nodes are NEVER conflated.
 */

import type { V2VerbKey, V2VerbParam, V2ResolvedTarget } from "@/types/v2-types";
import {
  ORGS,
  TERRITORIES,
  COMMUNITIES,
  EDGES,
  VERBS,
  CLASS_COLORS,
  EDGE_COLORS,
} from "@/fixtures/v2-mock-data";

export { VERBS };

/** Spec 061 US5 T081 / FR-025: verbs whose engine handlers don't exist.
 *  Filtered out of the verb picker and rejected at the action-submit
 *  endpoint server-side. A follow-up spec will add real handlers and
 *  remove entries from this set.
 */
export const DISABLED_VERBS: ReadonlySet<string> = new Set(["investigate", "move", "negotiate"]);

/** VERBS minus disabled verbs — for the verb picker, NavRail, and grids. */
export const SUPPORTED_VERBS = VERBS.filter((v) => !DISABLED_VERBS.has(v.verb));

/**
 * Resolve eligible targets for a verb, gated by target_type.
 * CRITICAL: never one big dropdown. Per Constitution Article IV,
 * hyperedges and dyadic nodes are NEVER conflated.
 */
export function resolveTargets(targetType: string): V2ResolvedTarget[] {
  if (targetType === "community") {
    return COMMUNITIES.map((c) => ({
      id: c.id,
      type: "community",
      label: c.name,
      sub: `${c.composition.join(" · ")} · ${c.members.toLocaleString()} ppl`,
      color: CLASS_COLORS[c.dominant_class] ?? "#787878",
      meta: c,
      telemetry: { CON: c.con, SOL: c.sol },
    }));
  }
  if (targetType === "territory") {
    return TERRITORIES.map((t) => ({
      id: t.id,
      type: "territory",
      label: t.name,
      sub: `${t.county} County · pop ${t.pop.toLocaleString()}`,
      color: "#80b0e0",
      meta: t,
      telemetry: { HEAT: t.heat, RENT: t.rent },
    }));
  }
  if (targetType === "org") {
    return ORGS.map((o) => ({
      id: o.id,
      type: "org",
      label: o.short,
      sub: `${o.name}${o.player_controlled ? " · ALLIED" : " · ENEMY"}`,
      color: CLASS_COLORS[o.class_character] ?? "#787878",
      meta: o,
      telemetry: { COH: o.cohesion, OPC: o.opacity },
    }));
  }
  if (targetType === "org_or_territory") {
    return [
      ...ORGS.filter((o) => !o.player_controlled).map((o) => ({
        id: o.id,
        type: "org" as const,
        label: o.short,
        sub: `${o.name} · ENEMY`,
        color: CLASS_COLORS[o.class_character] ?? "#787878",
        meta: o,
        telemetry: { COH: o.cohesion, OPC: o.opacity },
      })),
      ...TERRITORIES.map((t) => ({
        id: t.id,
        type: "territory" as const,
        label: t.name,
        sub: `${t.county} County · pop ${t.pop.toLocaleString()}`,
        color: "#80b0e0",
        meta: t,
        telemetry: { HEAT: t.heat, RENT: t.rent },
      })),
    ];
  }
  if (targetType === "territory_or_community") {
    return [
      ...TERRITORIES.map((t) => ({
        id: t.id,
        type: "territory" as const,
        label: t.name,
        sub: `${t.county} County`,
        color: "#80b0e0",
        meta: t,
        telemetry: { HEAT: t.heat, RENT: t.rent },
      })),
      ...COMMUNITIES.map((c) => ({
        id: c.id,
        type: "community" as const,
        label: c.name,
        sub: c.composition.join(" · "),
        color: CLASS_COLORS[c.dominant_class] ?? "#787878",
        meta: c,
        telemetry: { CON: c.con, SOL: c.sol },
      })),
    ];
  }
  if (targetType === "any") {
    return [
      ...ORGS.filter((o) => !o.player_controlled).map((o) => ({
        id: o.id,
        type: "org" as const,
        label: o.short,
        sub: `${o.name} · ENEMY`,
        color: CLASS_COLORS[o.class_character] ?? "#787878",
        meta: o,
        telemetry: { OPC: o.opacity },
      })),
      ...EDGES.map((e) => ({
        id: e.id,
        type: "edge" as const,
        label: e.type,
        sub: `${e.source} → ${e.target} · ${(e.intensity * 100).toFixed(0)}%`,
        color: EDGE_COLORS[e.type] ?? "#787878",
        meta: e,
        telemetry: { INT: e.intensity },
      })),
      ...TERRITORIES.map((t) => ({
        id: t.id,
        type: "territory" as const,
        label: t.name,
        sub: `${t.county} County`,
        color: "#80b0e0",
        meta: t,
        telemetry: { HEAT: t.heat },
      })),
      ...COMMUNITIES.map((c) => ({
        id: c.id,
        type: "community" as const,
        label: c.name,
        sub: c.composition.join(" · "),
        color: CLASS_COLORS[c.dominant_class] ?? "#787878",
        meta: c,
        telemetry: { CON: c.con },
      })),
    ];
  }
  return [];
}

/**
 * Per-verb form parameter schemas.
 */
export function getVerbParams(verb: V2VerbKey): V2VerbParam[] {
  switch (verb) {
    case "educate":
      return [
        {
          key: "method",
          label: "Method",
          kind: "radio",
          options: ["Study Circle", "Mass Line", "Agitation"],
        },
        {
          key: "intensity",
          label: "Cadre commitment",
          kind: "slider",
          min: 1,
          max: 8,
          default: 3,
          unit: "CL",
        },
      ];
    case "mobilize":
      return [
        {
          key: "vehicle",
          label: "Vehicle",
          kind: "radio",
          options: ["Mass Action", "General Strike", "Block Org"],
        },
        {
          key: "intensity",
          label: "Sympathizer draw",
          kind: "slider",
          min: 1,
          max: 12,
          default: 5,
          unit: "SL",
        },
      ];
    case "aid":
      return [
        {
          key: "kind",
          label: "Aid kind",
          kind: "radio",
          options: ["Material", "Legal", "Medical", "Financial"],
        },
        {
          key: "amount",
          label: "Amount",
          kind: "slider",
          min: 10,
          max: 200,
          default: 50,
          unit: "$",
        },
      ];
    case "attack":
      return [
        {
          key: "method",
          label: "Method",
          kind: "radio",
          options: ["Sabotage", "Disruption", "Direct Action"],
        },
        { key: "force", label: "Force", kind: "slider", min: 2, max: 12, default: 6, unit: "CL" },
        { key: "expose", label: "Accept exposure (+heat)", kind: "toggle", default: false },
      ];
    case "campaign":
      return [
        {
          key: "frame",
          label: "Framing",
          kind: "radio",
          options: ["Class", "Anti-Imperialist", "Communal"],
        },
        {
          key: "duration",
          label: "Sustained ticks",
          kind: "slider",
          min: 1,
          max: 6,
          default: 2,
          unit: "ticks",
        },
      ];
    case "move":
      return [
        {
          key: "what",
          label: "Move",
          kind: "radio",
          options: ["HQ", "Cadre Cell", "Sympathizer Network"],
        },
      ];
    case "investigate":
      return [
        {
          key: "depth",
          label: "Depth",
          kind: "radio",
          options: ["Surveil", "Penetrate", "Forensic"],
        },
        {
          key: "intensity",
          label: "Cadre commitment",
          kind: "slider",
          min: 1,
          max: 6,
          default: 2,
          unit: "CL",
        },
      ];
    case "reproduce":
      return [
        {
          key: "track",
          label: "Track",
          kind: "radio",
          options: ["Convert SL→CL", "Train Successor", "Found Cell"],
        },
        {
          key: "intensity",
          label: "Resources",
          kind: "slider",
          min: 5,
          max: 20,
          default: 10,
          unit: "CL",
        },
      ];
    case "negotiate":
      return [
        {
          key: "stance",
          label: "Stance",
          kind: "radio",
          options: ["Coalition", "Cease-Fire", "Tactical Alliance"],
        },
        { key: "concede", label: "Willing to concede", kind: "toggle", default: false },
      ];
    default:
      return [];
  }
}

/** Helper to build the route key for a verb. */
export function verbRouteKey(verb: string): string {
  return `actions/${verb}`;
}
