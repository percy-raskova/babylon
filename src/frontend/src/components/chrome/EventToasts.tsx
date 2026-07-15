/**
 * EventToasts — the toast queue (architecture §4.2, DESIGN_BIBLE §5.2).
 *
 * Renders `events.toasts` (urgent-stream only — see `eventsSlice`'s
 * docstring for why the ambient stream never toasts). Two lifetimes:
 * `persistent` (critical, one event per toast) never auto-dismisses — the
 * player must act (Dismiss, or "Open Wire" for more context); `ephemeral`
 * (a same-tick batch of notable events) auto-dismisses after a generous
 * window and is expandable to list its member events. Dismissing either
 * kind moves it into `events.tray`, never deletes it (HOI4's recoverable
 * dismissal — `EventTray` is where a missed toast is retrieved).
 */

import { useEffect, useState } from "react";
import { useStore } from "@/store";
import type { ToastEntry } from "@/store/slices/eventsSlice";
import type { EventCategory, StreamEvent } from "@/lib/eventClassifier";
import { keyButtonClass } from "./installerKit";
import { maoScore } from "@/components/map/layers/stormMarkers";

interface EventToastsProps {
  gameId: string;
}

/** Generous ephemeral timeout (DESIGN_BIBLE §5.2: "ephemeral-with-generous-timing"). */
const EPHEMERAL_TIMEOUT_MS = 12000;

const SEVERITY_BORDER: Record<StreamEvent["severity"], string> = {
  critical: "border-accent-crimson",
  notable: "border-heat",
  ambient: "border-ksbc-muted-1",
};

/** Critical toasts throb (compositor-safe pseudo-layer opacity loop, see index.css). */
const SEVERITY_THROB: Record<StreamEvent["severity"], string> = {
  critical: "alert-throb-frame",
  notable: "",
  ambient: "",
};

function toastCategories(toast: ToastEntry): EventCategory[] {
  return Array.from(new Set(toast.events.map((e) => e.category)));
}

/**
 * RUPTURE is global (no node/territory anchor — `contradiction.py`'s payload
 * is `{opposition, gap, rate}`), so it never gets a map glyph
 * (`stormMarkers.ts`'s module docstring). This is the "ride the existing
 * global channel minimally" half of that split (Wave 3 R2a brief): every
 * RUPTURE toast already flows through here (its severity is "critical" in
 * `EVENT_SEVERITY_MAP`) — grade its copy with the real Mao score when both
 * `gap`/`rate` are served, never fabricate one when they aren't.
 */
function ruptureScoreCopy(event: StreamEvent): string | null {
  if (event.event.type !== "rupture") return null;
  const { gap, rate } = event.event.data;
  if (typeof gap !== "number" || typeof rate !== "number") return null;
  return `Principal-contradiction score ≈ ${maoScore(gap, rate).toFixed(2)}`;
}

function EventLine({ event }: { event: StreamEvent }): React.JSX.Element {
  // "Headlines lead with actor + action + tick" (DESIGN_BIBLE §7).
  const headline = event.event.title || event.event.type;
  const scoreCopy = ruptureScoreCopy(event);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] text-ink">
        {headline} <span className="text-ksbc-muted-2">— tick {event.tick}</span>
      </span>
      {event.event.body && (
        <span className="text-[10px] text-ksbc-muted-2">{event.event.body}</span>
      )}
      {scoreCopy && (
        <span data-testid={`toast-rupture-score-${event.id}`} className="text-[10px] text-rupture">
          {scoreCopy}
        </span>
      )}
    </div>
  );
}

function ToastCard({
  toast,
  onDismiss,
  onOpenWire,
  onToggleMute,
}: {
  toast: ToastEntry;
  onDismiss: () => void;
  onOpenWire: () => void;
  onToggleMute: (category: EventCategory) => void;
}): React.JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const isBatch = toast.events.length > 1;
  const categories = toastCategories(toast);

  useEffect(() => {
    if (toast.lifetime !== "ephemeral") return;
    const timer = setTimeout(onDismiss, EPHEMERAL_TIMEOUT_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- fires once per toast id
  }, [toast.id]);

  return (
    <div
      data-testid={`toast-${toast.id}`}
      className={`toast-slam pointer-events-auto w-72 border-2 bg-plate/90 p-2 shadow-[4px_4px_0_#000] backdrop-blur-sm ${SEVERITY_BORDER[toast.severity]} ${SEVERITY_THROB[toast.severity]}`}
    >
      {isBatch && !expanded ? (
        <button
          data-testid={`toast-expand-${toast.id}`}
          onClick={() => setExpanded(true)}
          className="w-full text-left"
        >
          <span className="text-[11px] text-ink">{toast.events.length} developments this tick</span>
          <span className="ml-1 text-[10px] text-ksbc-muted-2">— expand</span>
        </button>
      ) : (
        <div className="flex flex-col gap-1.5">
          {toast.events.map((e) => (
            <EventLine key={e.id} event={e} />
          ))}
        </div>
      )}

      <div className="mt-1.5 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          {toast.lifetime === "persistent" && (
            <button
              onClick={onOpenWire}
              data-testid={`toast-open-wire-${toast.id}`}
              className={keyButtonClass(false, "px-1.5 py-0.5 text-[9px]")}
            >
              Open Wire
            </button>
          )}
          <button
            onClick={onDismiss}
            data-testid={`toast-dismiss-${toast.id}`}
            className={keyButtonClass(false, "px-1.5 py-0.5 text-[9px]")}
          >
            Dismiss
          </button>
        </div>
        <div className="flex items-center gap-1">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => onToggleMute(category)}
              title={`Mute ${category}`}
              data-testid={`toast-mute-${toast.id}-${category}`}
              className="border border-ksbc-muted-3 bg-plate px-1 py-0.5 font-mono text-[8px] uppercase tracking-widest text-ksbc-muted-2 hover:border-heat hover:text-heat"
            >
              mute {category}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function EventToasts({ gameId: _gameId }: EventToastsProps): React.JSX.Element {
  const toasts = useStore((s) => s.events.toasts);
  const dismissToast = useStore((s) => s.events.dismissToast);
  const toggleMuteCategory = useStore((s) => s.events.toggleMuteCategory);
  const openTakeover = useStore((s) => s.ui.openTakeover);

  return (
    <div
      data-testid="event-toasts"
      className="pointer-events-none absolute right-3 top-14 flex flex-col gap-2"
    >
      {toasts.map((toast) => (
        <ToastCard
          key={toast.id}
          toast={toast}
          onDismiss={() => dismissToast(toast.id)}
          onOpenWire={() => openTakeover("wire")}
          onToggleMute={toggleMuteCategory}
        />
      ))}
    </div>
  );
}
