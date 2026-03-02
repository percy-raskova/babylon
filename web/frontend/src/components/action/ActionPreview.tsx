/**
 * Action preview — shows a summary of the pending action before submission.
 *
 * Displays the selected verb, acting org, target, and submit button.
 * Feedforward preview (predicted effects) requires a backend endpoint
 * that doesn't exist yet — for now shows the submission payload.
 */

import type { PlayerVerb } from "@/types/game";

interface ActionPreviewProps {
  verb: PlayerVerb;
  orgId: string;
  targetId: string | null;
  submitting: boolean;
  onSubmit: () => void;
  onCancel: () => void;
}

const VERB_LABELS: Record<PlayerVerb, string> = {
  educate: "Educate",
  reproduce: "Reproduce",
  investigate: "Investigate",
  attack: "Attack",
  mobilize: "Mobilize",
  campaign: "Campaign",
  aid: "Aid",
  move: "Move",
  negotiate: "Negotiate",
};

export function ActionPreview({
  verb,
  orgId,
  targetId,
  submitting,
  onSubmit,
  onCancel,
}: ActionPreviewProps) {
  return (
    <div className="flex flex-col gap-2 rounded border border-gold/30 bg-gold/5 p-2">
      <div className="text-[10px] font-bold uppercase tracking-widest text-gold">
        Action Preview
      </div>

      <div className="flex flex-col gap-1 text-[11px]">
        <div className="flex justify-between">
          <span className="text-ash">Verb</span>
          <span className="font-semibold text-bone">{VERB_LABELS[verb]}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ash">Organization</span>
          <span className="font-mono text-royal-blue">{orgId}</span>
        </div>
        {targetId && (
          <div className="flex justify-between">
            <span className="text-ash">Target</span>
            <span className="font-mono text-gold">{targetId}</span>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={onSubmit}
          disabled={submitting}
          className="flex-1 rounded bg-gold px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-void hover:brightness-110 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Submit Action"}
        </button>
        <button
          onClick={onCancel}
          disabled={submitting}
          className="rounded border border-wet-concrete px-3 py-1.5 text-[11px] text-ash hover:text-silver disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
