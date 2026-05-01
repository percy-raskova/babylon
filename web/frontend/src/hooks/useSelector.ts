/**
 * useSelector — React hook to evaluate a ScriptValue against the live snapshot.
 *
 * Returns the evaluated value and breakdown, recomputing when the snapshot
 * or scope entity changes.
 */

import { useMemo } from "react";
import { useGameStore } from "@/stores/gameStore";
import { selectors } from "@/lib/selectors";
import type { Scope, ScopeEntity, Breakdown } from "@/lib/selectors";

interface SelectorResult {
  value: number;
  breakdown: Breakdown;
}

/**
 * Evaluate a registered selector by name, scoped to an optional entity.
 *
 * @param name     - Registered selector name (e.g. "hex.heat", "org.effective_cadre")
 * @param entity   - Optional scope entity, or null for global
 * @returns          The value and breakdown, or 0/{total:0,contributors:[]} if snapshot unavailable
 */
export function useSelector(name: string, entity: ScopeEntity | null = null): SelectorResult {
  const snapshot = useGameStore((s) => s.snapshot);

  return useMemo(() => {
    if (!snapshot) {
      return { value: 0, breakdown: { total: 0, contributors: [] } };
    }

    const sv = selectors.get(name);
    const scope: Scope = { snapshot, this: entity };

    return {
      value: sv.evaluate(scope),
      breakdown: sv.breakdown(scope),
    };
  }, [snapshot, name, entity]);
}
