/**
 * useScope — constructs a Scope object from the live snapshot and an entity ref.
 *
 * Convenience hook for BreakdownTooltip consumers.
 */

import { useMemo } from "react";
import { useGameStore } from "@/stores/gameStore";
import type { Scope, ScopeEntity } from "@/lib/selectors/types";

/**
 * Build a Scope from the current game snapshot and an optional entity.
 *
 * @param entity - The scope entity, or null for global scope
 * @returns A Scope object, or null if no snapshot is loaded
 */
export function useScope(entity: ScopeEntity | null = null): Scope | null {
  const snapshot = useGameStore((s) => s.snapshot);

  return useMemo(() => {
    if (!snapshot) return null;
    return { snapshot, this: entity };
  }, [snapshot, entity]);
}
