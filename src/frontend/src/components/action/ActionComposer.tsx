/**
 * Action Composer — Right Dock tab 1. Acting-org selector (player-owned
 * orgs only — Article V's action surface never lets you act AS an enemy
 * org; enemy orgs as *targets* are fine and flow through normally, e.g.
 * Attack), the flat 9-verb grid, and the selected verb's form
 * (`VerbForm`, keyed by org+verb so switching either resets cleanly).
 * Submission mirrors the legacy app's payload exactly via the ported
 * `VerbConfig.buildPayload` (`@/lib/verbs`) — this component never
 * re-shapes the body itself.
 */

import { useState } from "react";
import { useStore } from "@/store";
import { VERB_REGISTRY } from "@/lib/verbs";
import type { PlayerVerb } from "@/types/game";
import { VerbGrid } from "./VerbGrid";
import { VerbForm } from "./VerbForm";

interface ActionComposerProps {
  gameId: string;
}

export function ActionComposer({ gameId }: ActionComposerProps): React.JSX.Element {
  const snapshot = useStore((s) => s.world.snapshot);
  const submit = useStore((s) => s.actions.submit);
  const pending = useStore((s) => s.actions.pending);
  const submitting = useStore((s) => s.actions.submitting);
  const submitError = useStore((s) => s.actions.error);

  const playerOrgs = (snapshot?.organizations ?? []).filter((o) => o.player_controlled === true);
  const [orgId, setOrgId] = useState<string>("");
  const activeOrgId = playerOrgs.some((o) => o.id === orgId) ? orgId : (playerOrgs[0]?.id ?? "");
  const [verb, setVerb] = useState<PlayerVerb | null>(null);
  const config = verb ? VERB_REGISTRY[verb] : undefined;

  function handleFormSubmit(targetId: string | null, params: Record<string, unknown>): void {
    if (!config || !verb || !activeOrgId) return;
    void submit(gameId, verb, config.buildPayload(activeOrgId, targetId, params));
  }

  return (
    <div className="flex flex-col gap-3 p-2" data-testid="action-composer">
      {playerOrgs.length === 0 && (
        <p className="py-4 text-center text-[11px] italic text-shroud">
          No player-controlled organizations this session.
        </p>
      )}

      {playerOrgs.length > 0 && (
        <>
          {playerOrgs.length > 1 && (
            <OrgSelect orgs={playerOrgs} value={activeOrgId} onChange={setOrgId} />
          )}

          <VerbGrid selectedVerb={verb} onSelect={setVerb} />

          {config && verb && (
            <VerbForm
              key={`${activeOrgId}:${verb}`}
              gameId={gameId}
              orgId={activeOrgId}
              verb={verb}
              config={config}
              snapshot={snapshot}
              submitting={submitting}
              onSubmit={handleFormSubmit}
            />
          )}

          {submitError && (
            <p role="alert" className="text-[11px] text-laser">
              {submitError}
            </p>
          )}
        </>
      )}

      {pending.length > 0 && <PendingList entries={pending} />}
    </div>
  );
}

interface OrgOption {
  id: string;
  name: string;
  short_name?: string;
}

function OrgSelect({
  orgs,
  value,
  onChange,
}: {
  orgs: OrgOption[];
  value: string;
  onChange: (id: string) => void;
}): React.JSX.Element {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[9px] uppercase tracking-widest text-ash">Acting Org</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-wet-steel bg-void px-2 py-1 text-[11px] text-bone"
      >
        {orgs.map((o) => (
          <option key={o.id} value={o.id}>
            {o.short_name ?? o.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function PendingList({
  entries,
}: {
  entries: { id: string; verb: string; targetId: string | null }[];
}): React.JSX.Element {
  return (
    <div className="border-t border-rebar pt-2" data-testid="pending-actions">
      <span className="text-[9px] uppercase tracking-widest text-ash">
        Pending this tick ({entries.length})
      </span>
      <ul className="mt-1 flex flex-col gap-0.5">
        {entries.map((p) => (
          <li key={p.id} className="text-[10px] text-fog">
            {p.verb} {p.targetId ? `→ ${p.targetId}` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
