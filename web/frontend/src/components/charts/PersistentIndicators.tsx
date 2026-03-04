/**
 * Persistent indicators — always-visible urgency-colored metrics in the top bar.
 *
 * Renders pinned indicators from uiStore using IndicatorDefinition.compute()
 * and IndicatorChip for display with threshold-based urgency coloring.
 */

import { useUIStore } from "@/stores/uiStore";
import { useGameStore } from "@/stores/gameStore";
import { getIndicatorById } from "@/lib/lensDefinitions";
import { IndicatorChip } from "@/components/ui/IndicatorChip";
import type { GameSnapshot } from "@/types/game";

interface PersistentIndicatorsProps {
  snapshot: GameSnapshot;
}

export function PersistentIndicators({ snapshot }: PersistentIndicatorsProps) {
  const pinnedIndicators = useUIStore((s) => s.pinnedIndicators);
  const tickSummaries = useGameStore((s) => s.tickSummaries);

  // Compute previous tick values for delta arrows
  const prevSummaryIndex = tickSummaries.length - 2;
  const hasPrevious = prevSummaryIndex >= 0;

  return (
    <div className="flex items-center gap-1">
      {pinnedIndicators.map((indicatorId) => {
        const definition = getIndicatorById(indicatorId);
        const value = definition.compute(snapshot);

        // For delta arrows, compute from previous snapshot if available
        let previousValue: number | undefined;
        if (hasPrevious) {
          // Use a simple heuristic: if the indicator was also computed last tick
          // We can't replay the full snapshot, so we skip delta for complex indicators
          previousValue = undefined;
        }

        return (
          <IndicatorChip
            key={indicatorId}
            definition={definition}
            value={value}
            previousValue={previousValue}
          />
        );
      })}
    </div>
  );
}
