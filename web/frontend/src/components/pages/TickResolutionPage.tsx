/**
 * TickResolutionPage — the end-of-turn resolution surface.
 *
 * Spec 092: ports the animated step-through chrome of
 * `design/mockups/ui_kits/webapp/TickResolution.jsx` (design reference
 * only — fresh code against real data, not a JSX port). The mockup's
 * fabricated OBSERVE/ORIENT/DECIDE/ACT/RESPOND phase narration doesn't
 * exist in the engine, so steps are grounded in real data instead:
 * `snapshot.events` (the just-resolved tick's events) grouped by
 * severity, ascending in drama, followed by a final "State Response" step
 * sourced from the real `get_alerts_dashboard` endpoint (`useAlerts`) —
 * satisfying R-CONS's requirement that the alerts endpoint gets a real
 * consumer.
 *
 * Spec-092 review fix (Defect B): severity buckets are read directly from
 * the backend's `GameEvent.severity` (spec-061 FR-012: critical/warning/
 * informational) rather than re-derived via `lib/eventClassifier.ts` —
 * that classifier's map is keyed by UPPERCASE event-type names while real
 * `EventType` values are lowercase snake_case, so every event used to
 * bucket into the single OBSERVED step regardless of actual severity.
 */

import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { BblBadge } from "@/components/bbl";
import { useAlerts } from "@/hooks/useAlerts";
import { useGameState } from "@/hooks/useGameState";
import type { GameEvent } from "@/types/game";

const STEP_DELAY_MS = 1100;

interface Step {
  label: string;
  color: string;
  lines: string[];
}

/** Ascending drama: routine flow first, alarming last (mirrors the mockup's
 *  OBSERVE→RESPOND escalation without fabricating phase names). */
const SEVERITY_ORDER: GameEvent["severity"][] = ["informational", "warning", "critical"];

const SEVERITY_LABEL: Record<GameEvent["severity"], string> = {
  informational: "OBSERVED",
  warning: "ESCALATION",
  critical: "RUPTURE",
};

const SEVERITY_COLOR: Record<GameEvent["severity"], string> = {
  informational: "#4dd9e6",
  warning: "#d97a2c",
  critical: "#ff3344",
};

function lineFor(e: GameEvent): string {
  return e.body || e.title;
}

export function TickResolutionPage() {
  const navigate = useNavigate();
  const { id: gameId } = useParams<{ id: string }>();
  const { snapshot } = useGameState(gameId ?? null);
  const { data: alertsData } = useAlerts(gameId ?? null);

  const tick = snapshot?.tick ?? 0;
  const prevTick = Math.max(tick - 1, 0);

  const steps: Step[] = useMemo(() => {
    const events = snapshot?.events ?? [];
    const bySeverity: Step[] = SEVERITY_ORDER.filter((sev) =>
      events.some((e) => e.severity === sev),
    ).map((sev) => ({
      label: SEVERITY_LABEL[sev],
      color: SEVERITY_COLOR[sev],
      lines: events.filter((e) => e.severity === sev).map(lineFor),
    }));

    if (alertsData.alerts.length > 0) {
      bySeverity.push({
        label: "STATE RESPONSE",
        color: "#d4a02c",
        lines: alertsData.alerts.map((a) => a.body || a.title),
      });
    }

    return bySeverity;
  }, [snapshot?.events, alertsData.alerts]);

  const [step, setStep] = useState(0);
  // Reset the reveal to step 0 whenever a new tick's resolution begins.
  // Adjusting state during render (React's endorsed alternative to an
  // effect keyed on a single prop) rather than useEffect(() => ..., [tick]).
  const [lastTickSeen, setLastTickSeen] = useState(tick);
  if (tick !== lastTickSeen) {
    setLastTickSeen(tick);
    setStep(0);
  }

  useEffect(() => {
    if (step >= steps.length - 1) return;
    const t = setTimeout(() => setStep((s) => s + 1), STEP_DELAY_MS);
    return () => clearTimeout(t);
  }, [step, steps.length]);

  const handleContinue = () => navigate(`/games/${gameId}`);
  const handleSkip = () => navigate(`/games/${gameId}`);

  const isDone = steps.length === 0 || step >= steps.length - 1;

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-void p-6 text-bone">
      <div className="mb-5 flex items-center justify-between">
        <button
          onClick={handleSkip}
          className="rounded border border-wet-concrete px-3.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-fog"
        >
          ← Skip
        </button>
        <div className="font-mono text-[11px] uppercase tracking-[0.3em] text-spire">
          ▸ Resolving Tick {String(prevTick).padStart(4, "0")} → {String(tick).padStart(4, "0")}
        </div>
        <div className="font-mono text-[10px] text-ash">
          {steps.length > 0 ? `${step + 1} / ${steps.length}` : "0 / 0"}
        </div>
      </div>

      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col">
        {steps.length > 0 && (
          <div className="mb-6 flex gap-1">
            {steps.map((s, i) => (
              <div
                key={s.label}
                className="h-[3px] flex-1 rounded-full transition-colors"
                style={{ background: i <= step ? s.color : "#1a1f2a" }}
              />
            ))}
          </div>
        )}

        {steps.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-sm text-ash">
            No changes recorded this tick.
          </div>
        ) : (
          steps.slice(0, step + 1).map((s, i) => (
            <div key={s.label} className="mb-5" style={{ opacity: i === step ? 1 : 0.45 }}>
              <div
                className="mb-2 flex items-center gap-2 font-mono text-[12px] font-bold uppercase tracking-[0.3em]"
                style={{ color: s.color }}
              >
                <BblBadge color={s.color}>{s.label}</BblBadge>
              </div>
              {s.lines.map((line, j) => (
                <div
                  key={j}
                  className="ml-2 border-l py-1 pl-4 font-mono text-[12px] text-bone/85"
                  style={{ borderColor: s.color }}
                >
                  <span className="text-shroud">›</span> {line}
                </div>
              ))}
            </div>
          ))
        )}

        {isDone && (
          <button
            onClick={handleContinue}
            className="mx-auto mt-auto rounded bg-spire px-8 py-3 font-mono text-[11px] font-bold uppercase tracking-[0.22em] text-void"
          >
            ▸ Continue · Tick {String(tick).padStart(4, "0")}
          </button>
        )}
      </div>
    </div>
  );
}
