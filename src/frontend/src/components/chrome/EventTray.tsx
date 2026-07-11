/**
 * EventTray — persistent right rail hosting `EventsFeed` verbatim
 * (architecture §1.2's `BottomStrip` disperse row; §4.2; DESIGN_BIBLE
 * §5.2). Adds the badge counts (`summary.event_counts` — the same data
 * TopBar's alert badges already mirror, architecture §4.3), per-category
 * mute toggles, and the recoverable tray of dismissed toasts
 * (`events.tray` / `events.restoreToast`).
 *
 * `anchor="free"` — `AppShell` composes the shared right-column wrapper
 * (stacked with `ObjectivesTray` per the §1.1 layout diagram); this
 * component doesn't self-position a full-height right edge.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { RAIL_RIGHT_W } from "./layout";
import { EventsFeed } from "@/components/events/EventsFeed";
import { EVENT_CATEGORIES } from "@/lib/eventClassifier";
import { NarrationBlock } from "@/components/narration/NarrationBlock";
import { useNarration } from "@/hooks/useNarration";
import { keyButtonClass } from "./installerKit";

interface EventTrayProps {
  gameId: string;
}

export function EventTray({ gameId }: EventTrayProps): React.JSX.Element {
  const eventTrayOpen = useStore((s) => s.ui.chrome.eventTrayOpen);
  const toggleEventTray = useStore((s) => s.ui.toggleEventTray);
  const eventCounts = useStore((s) => s.panels.summary.data?.event_counts);
  const mutedCategories = useStore((s) => s.events.mutedCategories);
  const toggleMuteCategory = useStore((s) => s.events.toggleMuteCategory);
  const tray = useStore((s) => s.events.tray);
  const restoreToast = useStore((s) => s.events.restoreToast);
  // The tray is the narration panel's canonical always-mounted host (spec-113
  // integration ledger): mounting here keeps the cumulative beat feed warm for
  // every other slot (toasts, inspection cards, chronicle).
  const narration = useNarration(gameId);

  return (
    <FloatingPanel
      anchor="free"
      title="Events"
      collapsed={!eventTrayOpen}
      onToggle={toggleEventTray}
      width={RAIL_RIGHT_W}
      testId="event-tray"
    >
      <div className="flex h-full flex-col">
        {eventCounts !== undefined && (
          <div
            data-testid="event-tray-counts"
            className="flex items-center gap-1.5 border-b-2 border-ksbc-muted-1 px-2 py-1.5"
          >
            <CountBadge
              label="critical"
              count={eventCounts.critical}
              colorClassName="bg-accent-crimson text-ink"
            />
            <CountBadge
              label="warning"
              count={eventCounts.warning}
              colorClassName="bg-heat text-void"
            />
            <CountBadge
              label="informational"
              count={eventCounts.informational}
              colorClassName="bg-solidarity text-void"
            />
          </div>
        )}

        <div className="installer-well m-2 px-2 py-1.5" data-testid="event-tray-narration">
          <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">Narrator</p>
          <NarrationBlock beat={narration.latest} state={narration.status} />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <EventsFeed />
        </div>

        <div className="border-t-2 border-ksbc-muted-1 p-2">
          <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">Mute</p>
          <div className="flex flex-wrap gap-1" data-testid="event-tray-mutes">
            {EVENT_CATEGORIES.map((category) => {
              const muted = mutedCategories.includes(category);
              return (
                <button
                  key={category}
                  onClick={() => toggleMuteCategory(category)}
                  aria-pressed={muted}
                  data-testid={`mute-toggle-${category}`}
                  className={keyButtonClass(muted, "px-1.5 py-0.5 text-[9px]")}
                >
                  {category}
                </button>
              );
            })}
          </div>
        </div>

        {tray.length > 0 && (
          <div className="border-t-2 border-ksbc-muted-1 p-2" data-testid="event-tray-dismissed">
            <p className="mb-1 text-[9px] uppercase tracking-widest text-ksbc-muted-2">
              Missed ({tray.length})
            </p>
            <div className="flex flex-col gap-1">
              {tray.map((toast) => (
                <button
                  key={toast.id}
                  onClick={() => restoreToast(toast.id)}
                  data-testid={`tray-restore-${toast.id}`}
                  className="flex items-center justify-between border border-ksbc-muted-3 bg-plate px-1 py-0.5 text-left text-[10px] text-ink hover:border-accent-gold hover:text-accent-gold"
                >
                  <span className="truncate">
                    {toast.events.length > 1
                      ? `${toast.events.length} developments — tick ${toast.tick}`
                      : (toast.events[0]?.event.title ?? toast.events[0]?.event.type)}
                  </span>
                  <span className="text-ksbc-muted-2">restore</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </FloatingPanel>
  );
}

function CountBadge({
  label,
  count,
  colorClassName,
}: {
  label: string;
  count: number;
  colorClassName: string;
}): React.JSX.Element | null {
  if (count <= 0) return null;
  return (
    <span
      title={`${count} ${label}`}
      data-testid={`event-tray-count-${label}`}
      className={`border-2 border-key-shadow px-1.5 py-0.5 font-mono text-[9px] font-bold ${colorClassName}`}
    >
      {count}
    </span>
  );
}
