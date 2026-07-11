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
import { EventsFeed } from "@/components/events/EventsFeed";
import { EVENT_CATEGORIES } from "@/lib/eventClassifier";

interface EventTrayProps {
  gameId: string;
}

export function EventTray(_props: EventTrayProps): React.JSX.Element {
  const eventTrayOpen = useStore((s) => s.ui.chrome.eventTrayOpen);
  const toggleEventTray = useStore((s) => s.ui.toggleEventTray);
  const eventCounts = useStore((s) => s.panels.summary.data?.event_counts);
  const mutedCategories = useStore((s) => s.events.mutedCategories);
  const toggleMuteCategory = useStore((s) => s.events.toggleMuteCategory);
  const tray = useStore((s) => s.events.tray);
  const restoreToast = useStore((s) => s.events.restoreToast);

  return (
    <FloatingPanel
      anchor="free"
      title="Events"
      collapsed={!eventTrayOpen}
      onToggle={toggleEventTray}
      width={280}
      testId="event-tray"
    >
      <div className="flex h-full flex-col">
        {eventCounts !== undefined && (
          <div
            data-testid="event-tray-counts"
            className="flex items-center gap-1.5 border-b border-rebar px-2 py-1.5"
          >
            <CountBadge label="critical" count={eventCounts.critical} colorClassName="bg-laser" />
            <CountBadge label="warning" count={eventCounts.warning} colorClassName="bg-heat" />
            <CountBadge
              label="informational"
              count={eventCounts.informational}
              colorClassName="bg-solidarity"
            />
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto">
          <EventsFeed />
        </div>

        <div className="border-t border-rebar p-2">
          <p className="mb-1 text-[9px] uppercase tracking-widest text-ash">Mute</p>
          <div className="flex flex-wrap gap-1" data-testid="event-tray-mutes">
            {EVENT_CATEGORIES.map((category) => {
              const muted = mutedCategories.includes(category);
              return (
                <button
                  key={category}
                  onClick={() => toggleMuteCategory(category)}
                  aria-pressed={muted}
                  data-testid={`mute-toggle-${category}`}
                  className={`rounded border px-1.5 py-0.5 text-[9px] uppercase tracking-widest ${
                    muted
                      ? "border-heat text-heat"
                      : "border-rebar text-shroud hover:border-fog hover:text-fog"
                  }`}
                >
                  {category}
                </button>
              );
            })}
          </div>
        </div>

        {tray.length > 0 && (
          <div className="border-t border-rebar p-2" data-testid="event-tray-dismissed">
            <p className="mb-1 text-[9px] uppercase tracking-widest text-ash">
              Missed ({tray.length})
            </p>
            <div className="flex flex-col gap-1">
              {tray.map((toast) => (
                <button
                  key={toast.id}
                  onClick={() => restoreToast(toast.id)}
                  data-testid={`tray-restore-${toast.id}`}
                  className="flex items-center justify-between rounded px-1 py-0.5 text-left text-[10px] text-fog hover:bg-rebar"
                >
                  <span className="truncate">
                    {toast.events.length > 1
                      ? `${toast.events.length} developments — tick ${toast.tick}`
                      : (toast.events[0]?.event.title ?? toast.events[0]?.event.type)}
                  </span>
                  <span className="text-ash">restore</span>
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
      className={`rounded-full px-1.5 py-0.5 font-mono text-[9px] font-bold text-void ${colorClassName}`}
    >
      {count}
    </span>
  );
}
