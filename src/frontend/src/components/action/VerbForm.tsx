/**
 * One verb's target picker + param fields + submit button. Mounted keyed
 * by `${orgId}:${verb}` from `ActionComposer` so switching the acting org
 * or the selected verb resets `targetId`/`paramVals` via a clean remount
 * rather than an effect that re-derives state from a changed prop (see
 * `useVerbTargets.ts`'s docstring for why that pattern is avoided here).
 *
 * FR-116-4.3: the live per-verb cost (`useVerbTargets` cost envelope) and
 * the preview's AP cost render as a visible line above the submit button —
 * previously the only cost surface was VerbGrid's hover tooltip. Honest
 * null: the line renders only once a real cost or preview has resolved.
 */

import { useEffect, useState } from "react";
import type { LiveVerbCost, VerbConfig } from "@/lib/verbs";
import type {
  ActionPreviewResult,
  GameSnapshot,
  PlayerVerb,
  VerbEligibilityEntry,
} from "@/types/game";
import { TargetPicker } from "./TargetPicker";
import { ParamFields } from "./ParamFields";
import { useVerbTargets } from "./useVerbTargets";
import { useActionPreview } from "./useActionPreview";

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
  /** The verb's eligibility row (spec-116 FR-4.8) — feeds the reason-
   *  bearing empty state in TargetPicker; null/absent falls back to the
   *  legacy bare line. */
  eligibility?: VerbEligibilityEntry | null;
  /**
   * Track 1 Task 7 (2026-07-18): pre-seed `targetId` from a composer preset
   * (e.g. clicking a fogged field's "Investigate" link) — read only as the
   * initial `useState` value, so it applies once at mount (this component
   * already remounts on org/verb change via its `key`, matching every other
   * "seed once" pattern here). Deliberately independent of the fetched
   * `targets` list: `resolve_investigate` reads `target_id` directly off the
   * graph with no allow-list, so a target absent from the (still-mocked,
   * Task 9) discovery list still submits correctly — `initialTargetLabel`
   * renders a visible note so the player sees what's targeted even when
   * `TargetPicker` has nothing highlighted.
   */
  initialTargetId?: string | null;
  /** Display label paired with `initialTargetId` — see above. */
  initialTargetLabel?: string | null;
}

function defaultParamVals(config: VerbConfig): Record<string, unknown> {
  return Object.fromEntries(config.paramFields.map((p) => [p.key, p.defaultValue]));
}

/** Round to 2-3 significant decimals for display (the title attribute
 *  carries the full raw value). */
function formatMagnitude(value: number): string {
  return parseFloat(Math.abs(value).toPrecision(3)).toString();
}

/** One ▲/▼ delta chip for a non-zero estimated preview delta — null (no
 *  chip) for a zero or non-finite value, same honest-null convention the
 *  old constant-direction chip used. */
function DeltaChip({ value, label }: { value: number; label: string }): React.JSX.Element | null {
  if (!Number.isFinite(value) || value === 0) return null;
  const direction = value > 0 ? "up" : "down";
  const sign = value > 0 ? "+" : "-";

  return (
    <p
      data-testid="predicted-delta"
      title={`${label}: ${value > 0 ? "+" : ""}${value}`}
      className={`font-mono text-[10px] uppercase tracking-widest ${
        direction === "up" ? "text-accent-gold" : "text-accent-crimson"
      }`}
    >
      {direction === "up" ? "▲" : "▼"} {label} {sign}
      {formatMagnitude(value)}
    </p>
  );
}

/** Compose the pre-submit cost line's text and afford-state from the live
 *  per-verb cost and/or the preview's AP cost. Null iff neither has
 *  resolved yet (honest null, Constitution III.11) — factored out of
 *  `VerbForm` to keep that component's cyclomatic complexity under the
 *  repo's lint ceiling. */
function costLineContent(
  cost: LiveVerbCost | null,
  preview: ActionPreviewResult | null,
): { text: string; insufficient: boolean } | null {
  if (cost === null && preview === null) return null;
  const insufficient = cost !== null && !cost.canAfford;
  const text = [
    cost?.label,
    preview ? `${preview.action_point_cost} AP` : null,
    insufficient ? "insufficient" : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return { text, insufficient };
}

/** Compose the empty-state reason + remedy line for an ineligible verb
 *  (spec-116 FR-4.8) — null when eligible/unknown, same
 *  complexity-budget rationale as `costLineContent` above. */
function emptyReasonFor(eligibility: VerbEligibilityEntry | null | undefined): string | null {
  if (!eligibility || eligibility.eligible !== false) return null;
  return [eligibility.reason, eligibility.remedy].filter(Boolean).join(" ");
}

/** Track 1 Task 7 (2026-07-18): the visible "Targeting: X" note for a
 *  composer preset — null when no `initialTargetId` was supplied. Extracted
 *  for the same complexity-budget reason as the other `*For`/`*Content`
 *  helpers above. See `VerbFormProps.initialTargetId`'s docstring for why
 *  this note matters even though `TargetPicker` may show nothing
 *  highlighted for it. */
function presetTargetNote(
  initialTargetId: string | null | undefined,
  initialTargetLabel: string | null | undefined,
): React.JSX.Element | null {
  if (!initialTargetId) return null;
  return (
    <p data-testid="preset-target-note" className="text-[10px] italic text-fog">
      Targeting: {initialTargetLabel ?? initialTargetId}
    </p>
  );
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
  eligibility,
  initialTargetId,
  initialTargetLabel,
}: VerbFormProps): React.JSX.Element {
  const [targetId, setTargetId] = useState<string | null>(initialTargetId ?? null);
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
  const { preview } = useActionPreview(gameId, orgId, verb, config, targetId);
  const costLine = costLineContent(cost, preview);
  const emptyReason = emptyReasonFor(eligibility);

  return (
    <>
      {presetTargetNote(initialTargetId, initialTargetLabel)}

      {showPicker && (
        <TargetPicker
          targets={targets}
          loading={loading}
          error={error}
          selectedId={targetId}
          onSelect={setTargetId}
          emptyReason={emptyReason}
        />
      )}

      {config.paramFields.length > 0 && (
        <ParamFields
          fields={config.paramFields}
          values={paramVals}
          onChange={(k, v) => setParamVals((p) => ({ ...p, [k]: v }))}
        />
      )}

      {preview && (
        <div className="flex flex-col gap-1">
          <DeltaChip value={preview.estimated_consciousness_delta} label="Consciousness" />
          <DeltaChip value={preview.estimated_heat_delta} label="Heat" />
          <p
            data-testid="preview-probability"
            className="font-mono text-[10px] uppercase tracking-widest text-fog"
          >
            {Math.round(preview.success_probability * 100)}% est. success
          </p>
          {preview.warnings.length > 0 && (
            <ul
              data-testid="preview-warnings"
              className="flex flex-col gap-0.5 text-[10px] italic text-shroud"
            >
              {preview.warnings.map((warning, i) => (
                <li key={`${i}:${warning}`}>{warning}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {costLine && (
        <p
          data-testid="verb-cost"
          className={`font-mono text-[10px] uppercase tracking-widest ${
            costLine.insufficient ? "text-accent-crimson" : "text-fog"
          }`}
        >
          {costLine.text}
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
