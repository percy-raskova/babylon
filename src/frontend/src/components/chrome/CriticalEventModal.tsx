/**
 * CriticalEventModal — Paradox-style modal for `time.status === "autopaused"`
 * (architecture §4.2). Gives the existing autopause machinery its missing
 * face: lists the critical events that fired the autopause
 * (`time.autopauseEventIds`, resolved against the current tick's events via
 * `classifyEvents` — the same id scheme `worldSlice` used to pick them),
 * with "Open Wire" (`ui.openTakeover("wire")`) and "Resume" CTAs. `Resume`
 * is the bounded default action (CK3: "an ignored popup never stalls the
 * game") — it's also reachable via `time.resume()` directly from
 * `TimeControls`.
 */

import { useStore } from "@/store";
import { classifyEvents } from "@/lib/eventClassifier";
import type { ClassifiedEvent } from "@/types/game";

interface CriticalEventModalProps {
  gameId: string;
}

export function CriticalEventModal(_props: CriticalEventModalProps): React.JSX.Element | null {
  const status = useStore((s) => s.time.status);
  const autopauseEventIds = useStore((s) => s.time.autopauseEventIds);
  const events = useStore((s) => s.world.snapshot?.events);
  const resume = useStore((s) => s.time.resume);
  const openTakeover = useStore((s) => s.ui.openTakeover);

  if (status !== "autopaused") return null;

  const firing: ClassifiedEvent[] = classifyEvents(events ?? []).filter((e) =>
    autopauseEventIds.includes(e.id),
  );

  return (
    <div
      data-testid="critical-event-modal"
      role="alertdialog"
      aria-label="Autopaused"
      className="pointer-events-auto absolute inset-0 flex items-center justify-center bg-void/60"
    >
      <div className="w-96 rounded border border-heat bg-concrete p-4 text-bone">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-heat">
          The game has stopped itself — this cannot pass unread.
        </p>
        <div className="mb-3 flex flex-col gap-1.5">
          {firing.length === 0 ? (
            <p className="text-[11px] italic text-shroud">
              The firing events are no longer on this tick's record.
            </p>
          ) : (
            firing.map((e) => (
              <div key={e.id} data-testid={`autopause-event-${e.id}`} className="text-[11px]">
                <span className="text-bone">{e.event.title || e.event.type}</span>
                <span className="text-ash"> — tick {e.tick}</span>
                {e.event.body && <p className="text-[10px] text-ash">{e.event.body}</p>}
              </div>
            ))
          )}
        </div>
        <div className="flex items-center justify-end gap-2">
          <button
            onClick={() => openTakeover("wire")}
            data-testid="autopause-open-wire"
            className="rounded border border-rebar px-2.5 py-1 text-[10px] uppercase tracking-widest text-fog hover:border-spire hover:text-spire"
          >
            Open Wire
          </button>
          <button
            onClick={resume}
            data-testid="autopause-resume"
            className="rounded border border-heat px-2.5 py-1 text-[10px] uppercase tracking-widest text-heat hover:bg-heat hover:text-void"
          >
            Resume
          </button>
        </div>
      </div>
    </div>
  );
}
