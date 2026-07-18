/**
 * CriticalEventModal — Paradox-style modal for `time.status === "autopaused"`
 * (architecture §4.2). Gives the existing autopause machinery its missing
 * face: lists the critical events that fired the autopause, resolved from
 * `time.autopauseEventKeys`, joined by salience key (lib/eventDedup) —
 * tick-independent, so a persisting condition stays listed after the tick
 * advances — with "Open Wire" (`ui.openTakeover("wire")`) and "Resume" CTAs.
 * `Resume` is the bounded default action (CK3: "an ignored popup never
 * stalls the game") — it's also reachable via `time.resume()` directly from
 * `TimeControls`.
 */

import { useStore } from "@/store";
import { classifyEvents } from "@/lib/eventClassifier";
import { dedupKey, dedupeEvents } from "@/lib/eventDedup";
import { keyButtonClass, TITLE_TAB } from "./installerKit";
import { KeyHints } from "./KeyHints";

interface CriticalEventModalProps {
  gameId: string;
}

export function CriticalEventModal(_props: CriticalEventModalProps): React.JSX.Element | null {
  const status = useStore((s) => s.time.status);
  const autopauseEventKeys = useStore((s) => s.time.autopauseEventKeys);
  const events = useStore((s) => s.world.snapshot?.events);
  const resume = useStore((s) => s.time.resume);
  const openTakeover = useStore((s) => s.ui.openTakeover);

  if (status !== "autopaused") return null;

  // Key join is tick-independent: if the tick advanced but the condition
  // persists, the modal still finds it. Same-key repeats collapse into one
  // card with a count (FR-116-2). The zero-match fallback below stays —
  // an honestly empty record is still possible (Constitution III.11).
  const firing = dedupeEvents(
    classifyEvents(events ?? []).filter((e) => autopauseEventKeys.includes(dedupKey(e.event))),
  );

  return (
    <div
      data-testid="critical-event-modal"
      role="alertdialog"
      aria-label="Autopaused"
      className="pointer-events-auto absolute inset-0 flex items-center justify-center bg-field/70"
    >
      <div className="alert-throb-frame w-96 border-2 border-accent-crimson bg-plate pt-2 text-ink shadow-[8px_8px_0_#000]">
        <p className={`installer-blink ${TITLE_TAB}`}>Autopaused</p>
        <div className="p-4">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-accent-crimson">
            The game has stopped itself — this cannot pass unread.
          </p>
          <div className="mb-3 flex flex-col gap-1.5">
            {firing.length === 0 ? (
              <p className="text-[11px] italic text-ksbc-muted-2">
                The firing events are no longer on this tick's record.
              </p>
            ) : (
              firing.map((run) => (
                <div
                  key={run.key}
                  data-testid={`autopause-event-${run.key}`}
                  className="text-[11px]"
                >
                  <span className="text-ink">
                    {run.representative.event.title || run.representative.event.type}
                  </span>
                  {run.count > 1 && <span className="text-accent-gold"> ×{run.count}</span>}
                  <span className="text-ksbc-muted-2">
                    {" "}
                    — tick {run.firstTick}
                    {run.lastTick !== run.firstTick ? `–${run.lastTick}` : ""}
                  </span>
                  {run.representative.event.body && (
                    <p className="text-[10px] text-ksbc-muted-2">{run.representative.event.body}</p>
                  )}
                </div>
              ))
            )}
          </div>
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={() => openTakeover("wire")}
              data-testid="autopause-open-wire"
              className={keyButtonClass(false, "px-2.5 py-1 text-[10px]")}
            >
              Open Wire
            </button>
            <button
              onClick={resume}
              data-testid="autopause-resume"
              className={keyButtonClass(true, "px-2.5 py-1 text-[10px]")}
            >
              Resume
            </button>
          </div>
          <KeyHints />
        </div>
      </div>
    </div>
  );
}
