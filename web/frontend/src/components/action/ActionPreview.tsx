/**
 * Action preview — shows a summary of the pending action before submission.
 *
 * Calls the backend preview endpoint to display estimated effects
 * (consciousness delta, heat delta, success probability, warnings).
 */

import { useState, useEffect } from "react";
import { useParams } from "react-router";
import type { PlayerVerb, ActionPreviewResult } from "@/types/game";

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
  const { id: gameId = "" } = useParams<{ id: string }>();
  const [preview, setPreview] = useState<ActionPreviewResult | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch preview from backend when action params change
  useEffect(() => {
    const controller = new AbortController();
    async function fetchPreview() {
      setLoading(true);
      try {
        const res = await fetch(`/api/games/${gameId}/actions/preview/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ org_id: orgId, verb, target_id: targetId }),
          signal: controller.signal,
        });
        if (res.ok) {
          const json = await res.json();
          setPreview(json.data as ActionPreviewResult);
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
      } finally {
        setLoading(false);
      }
    }
    fetchPreview();
    return () => controller.abort();
  }, [gameId, orgId, verb, targetId]);

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

      {/* Estimated effects from backend */}
      {loading && (
        <div className="flex items-center gap-2 text-[10px] text-ash">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border border-gold border-t-transparent" />
          Estimating effects...
        </div>
      )}
      {preview && !loading && (
        <div className="flex flex-col gap-1 border-t border-soot pt-1 text-[11px]">
          <div className="flex justify-between">
            <span className="text-ash">Consciousness</span>
            <DeltaValue value={preview.estimated_consciousness_delta} />
          </div>
          <div className="flex justify-between">
            <span className="text-ash">Heat</span>
            <DeltaValue value={preview.estimated_heat_delta} />
          </div>
          <div className="flex justify-between">
            <span className="text-ash">AP Cost</span>
            <span className="font-mono text-gold">{preview.action_point_cost}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ash">Success</span>
            <span className="font-mono text-bone">
              {(preview.success_probability * 100).toFixed(0)}%
            </span>
          </div>
          {preview.warnings.length > 0 && (
            <div className="mt-1 flex flex-col gap-0.5">
              {preview.warnings.map((w, i) => (
                <span key={i} className="text-[10px] text-warning-amber">
                  {w}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={onSubmit}
          disabled={submitting || loading}
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

/** Renders a delta value with color coding (green for positive, red for negative). */
function DeltaValue({ value }: { value: number }) {
  if (Math.abs(value) < 0.001) {
    return <span className="font-mono text-ash">-</span>;
  }
  const sign = value > 0 ? "+" : "";
  const color = value > 0 ? "text-data-green" : "text-crimson";
  return (
    <span className={`font-mono ${color}`}>
      {sign}
      {value.toFixed(3)}
    </span>
  );
}
