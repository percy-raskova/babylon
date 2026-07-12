/**
 * Shared flat-cost parsing for the verbs whose GET .../targets/ endpoint
 * returns the identical `{action_points, cadre_labor, sympathizer_labor,
 * material, can_afford, over_budget, over_budget_penalty}` shape under a
 * top-level `cost` key: educate, aid, reproduce, investigate, move,
 * negotiate (web/game/engine_bridge.py:3216-3223, 3315-3323 (aid),
 * 3587-3595 (reproduce), 3662-3670 (investigate), 3751-3759 (move),
 * 3805-3813 (negotiate)). attack and mobilize have their own custom
 * shapes and parse `raw` directly in their own verb config files instead
 * of using this module.
 */

import type { LiveVerbCost } from "./types";

/** The subset of the flat cost shape this module reads. */
export interface FlatCostFields {
  cadre_labor?: number;
  sympathizer_labor?: number;
  material?: number;
}

/**
 * Format a flat cost as "2 CL + 5 SL + $100", joining only the non-zero
 * components. All-zero (or entirely absent) components format as "Free"
 * (negotiate's real cost, per engine_bridge.py:3805-3813).
 */
export function formatFlatCost(cost: FlatCostFields): string {
  const parts: string[] = [];
  if (cost.cadre_labor) parts.push(`${cost.cadre_labor} CL`);
  if (cost.sympathizer_labor) parts.push(`${cost.sympathizer_labor} SL`);
  if (cost.material) parts.push(`$${cost.material}`);
  return parts.length > 0 ? parts.join(" + ") : "Free";
}

/**
 * Parse the raw verb-target payload's `cost` envelope into a
 * `LiveVerbCost`. Returns null (honest-null, Constitution III.11) when
 * `raw.cost` is absent or not an object — the caller falls back to the
 * static `cost_label` hint rather than rendering a fabricated value.
 */
export function parseFlatCost(raw: Record<string, unknown>): LiveVerbCost | null {
  const cost = raw.cost;
  if (!cost || typeof cost !== "object") return null;

  const c = cost as FlatCostFields & { can_afford?: boolean };
  return { label: formatFlatCost(c), canAfford: Boolean(c.can_afford) };
}
