/**
 * Action composer — turn submission interface implementing
 * Constitution Article V's 9-verb vocabulary.
 *
 * Flow: select org → select verb (3x3 grid) → select target → preview → submit.
 */

import { useState, useCallback } from "react";
import { useUIStore } from "@/stores/uiStore";
import { VerbSelector } from "@/components/action/VerbSelector";
import { TargetSelector } from "@/components/action/TargetSelector";
import { ActionPreview } from "@/components/action/ActionPreview";
import type { GameSnapshot, PlayerVerb, SubmitActionParams, OrgState } from "@/types/game";

/** Self-targeted verbs that skip target selection. */
const SELF_TARGETED = new Set<PlayerVerb>(["reproduce"]);

interface ActionComposerProps {
  snapshot: GameSnapshot;
  onSubmit: (params: SubmitActionParams) => Promise<void>;
  onResolve: () => Promise<void>;
  resolving: boolean;
}

export function ActionComposer({ snapshot, onSubmit, onResolve, resolving }: ActionComposerProps) {
  const pendingVerb = useUIStore((s) => s.pendingVerb);
  const pendingOrgId = useUIStore((s) => s.pendingOrgId);
  const pendingTargetId = useUIStore((s) => s.pendingTargetId);
  const setPendingAction = useUIStore((s) => s.setPendingAction);
  const setPendingTarget = useUIStore((s) => s.setPendingTarget);
  const clearPending = useUIStore((s) => s.clearPendingAction);

  const [submitting, setSubmitting] = useState(false);
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(
    snapshot.organizations.length > 0 ? snapshot.organizations[0]!.id : null,
  );

  const selectedOrg: OrgState | undefined = snapshot.organizations.find(
    (o) => o.id === selectedOrgId,
  );

  const handleVerbSelect = useCallback(
    (verb: PlayerVerb) => {
      if (!selectedOrgId) return;
      setPendingAction(verb, selectedOrgId);
    },
    [selectedOrgId, setPendingAction],
  );

  const handleSubmit = useCallback(async () => {
    if (!pendingVerb || !pendingOrgId) return;
    setSubmitting(true);
    await onSubmit({
      org_id: pendingOrgId,
      verb: pendingVerb,
      target_id: pendingTargetId ?? undefined,
    });
    clearPending();
    setSubmitting(false);
  }, [pendingVerb, pendingOrgId, pendingTargetId, onSubmit, clearPending]);

  return (
    <div className="flex h-full flex-col gap-3">
      {/* Header + Resolve */}
      <div className="flex shrink-0 items-center justify-between">
        <h3 className="m-0 text-sm font-semibold uppercase tracking-wider text-gold">Actions</h3>
        <button
          onClick={onResolve}
          disabled={resolving}
          className="rounded-md bg-gold px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-void hover:brightness-110 disabled:opacity-50"
        >
          {resolving ? "Resolving..." : "Resolve Tick"}
        </button>
      </div>

      {/* Org selector */}
      {snapshot.organizations.length > 1 && (
        <div className="shrink-0">
          <label className="mb-1 block text-[9px] uppercase tracking-widest text-ash">
            Acting Organization
          </label>
          <select
            value={selectedOrgId ?? ""}
            onChange={(e) => {
              setSelectedOrgId(e.target.value || null);
              clearPending();
            }}
            className="w-full rounded border border-soot bg-void px-2 py-1.5 text-[12px] text-bone focus:border-gold focus:outline-none"
          >
            {snapshot.organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name} ({org.org_type})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Org info pill */}
      {selectedOrg && (
        <div className="flex shrink-0 items-center gap-3 rounded border border-soot px-2 py-1 text-[10px]">
          <span className="font-semibold text-grow-purple">{selectedOrg.name}</span>
          <span className="text-ash">Budget: {selectedOrg.budget.toFixed(1)}</span>
          <span className="text-ash">Cohesion: {selectedOrg.cohesion.toFixed(2)}</span>
        </div>
      )}

      {/* Verb grid */}
      {selectedOrgId && (
        <div className="shrink-0">
          <label className="mb-1 block text-[9px] uppercase tracking-widest text-ash">
            Select Verb
          </label>
          <VerbSelector selectedVerb={pendingVerb} onSelect={handleVerbSelect} />
        </div>
      )}

      {/* Target selector */}
      {pendingVerb && !SELF_TARGETED.has(pendingVerb) && (
        <div className="min-h-0 shrink-0">
          <label className="mb-1 block text-[9px] uppercase tracking-widest text-ash">
            Select Target
          </label>
          <TargetSelector
            snapshot={snapshot}
            verb={pendingVerb}
            selectedTarget={pendingTargetId}
            onSelect={setPendingTarget}
          />
        </div>
      )}

      {/* Action preview + submit */}
      {pendingVerb && pendingOrgId && (SELF_TARGETED.has(pendingVerb) || pendingTargetId) && (
        <ActionPreview
          verb={pendingVerb}
          orgId={pendingOrgId}
          targetId={pendingTargetId}
          submitting={submitting}
          onSubmit={handleSubmit}
          onCancel={clearPending}
        />
      )}

      {/* Empty state */}
      {!selectedOrgId && snapshot.organizations.length === 0 && (
        <p className="py-6 text-center text-sm text-ash">No organizations available this tick</p>
      )}
    </div>
  );
}
