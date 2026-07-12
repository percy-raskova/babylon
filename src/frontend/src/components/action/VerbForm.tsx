/**
 * One verb's target picker + param fields + submit button. Mounted keyed
 * by `${orgId}:${verb}` from `ActionComposer` so switching the acting org
 * or the selected verb resets `targetId`/`paramVals` via a clean remount
 * rather than an effect that re-derives state from a changed prop (see
 * `useVerbTargets.ts`'s docstring for why that pattern is avoided here).
 */

import { useEffect, useState } from "react";
import { evaluatePredictedEffect } from "@/lib/verbs";
import type { LiveVerbCost, VerbConfig } from "@/lib/verbs";
import type { GameSnapshot, PlayerVerb } from "@/types/game";
import { TargetPicker } from "./TargetPicker";
import { ParamFields } from "./ParamFields";
import { useVerbTargets } from "./useVerbTargets";

interface VerbFormProps {
  gameId: string;
  orgId: string;
  verb: PlayerVerb;
  config: VerbConfig;
  snapshot: GameSnapshot | null;
  submitting: boolean;
  onSubmit: (targetId: string | null, params: Record<string, unknown>) => void;
  /** Notifies the sibling VerbGrid of this verb's live cost as it
   *  resolves, so the selected verb's button can show it instead of the
   *  static cost_label hint. */
  onCostChange?: (cost: LiveVerbCost | null) => void;
}

function defaultParamVals(config: VerbConfig): Record<string, unknown> {
  return Object.fromEntries(config.paramFields.map((p) => [p.key, p.defaultValue]));
}

export function VerbForm({
  gameId,
  orgId,
  verb,
  config,
  snapshot,
  submitting,
  onSubmit,
  onCostChange,
}: VerbFormProps): React.JSX.Element {
  const [targetId, setTargetId] = useState<string | null>(null);
  const [paramVals, setParamVals] = useState<Record<string, unknown>>(() =>
    defaultParamVals(config),
  );
  const { targets, loading, error, cost } = useVerbTargets(gameId, verb, config, orgId, snapshot);

  useEffect(() => {
    onCostChange?.(cost);
  }, [cost, onCostChange]);

  const targetRequired = config.targetRequired ?? true;
  const canSubmit = Boolean(orgId && (targetId || !targetRequired) && !submitting);
  const showPicker = !(targetRequired === false && targets.length === 0 && !loading);
  const predicted = evaluatePredictedEffect(config, snapshot, targetId);

  return (
    <>
      {showPicker && (
        <TargetPicker
          targets={targets}
          loading={loading}
          error={error}
          selectedId={targetId}
          onSelect={setTargetId}
        />
      )}

      {config.paramFields.length > 0 && (
        <ParamFields
          fields={config.paramFields}
          values={paramVals}
          onChange={(k, v) => setParamVals((p) => ({ ...p, [k]: v }))}
        />
      )}

      {predicted && (
        <p
          data-testid="predicted-delta"
          title={`${predicted.label}: ${predicted.value > 0 ? "+" : ""}${predicted.value}`}
          className={`font-mono text-[10px] uppercase tracking-widest ${
            predicted.direction === "up" ? "text-accent-gold" : "text-accent-crimson"
          }`}
        >
          {predicted.direction === "up" ? "▲" : "▼"} {predicted.label}
        </p>
      )}

      <button
        onClick={() => onSubmit(targetId, paramVals)}
        disabled={!canSubmit}
        className="rounded-md bg-spire px-3 py-2 text-[11px] font-bold uppercase tracking-widest text-void disabled:cursor-not-allowed disabled:opacity-40"
      >
        {submitting ? "Submitting…" : `Submit ${config.label}`}
      </button>
    </>
  );
}
