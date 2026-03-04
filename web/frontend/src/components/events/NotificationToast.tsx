/**
 * NotificationToast — fixed-position overlay for critical events.
 *
 * Renders critical ClassifiedEvents with CRIMSON border, acknowledge button,
 * and navigate button to jump to the linked entity.
 */

import { useUIStore } from "@/stores/uiStore";
import type { ClassifiedEvent } from "@/types/game";

interface NotificationToastProps {
  events: ClassifiedEvent[];
}

export function NotificationToast({ events }: NotificationToastProps) {
  const markEventRead = useUIStore((s) => s.markEventRead);
  const setSelectedHex = useUIStore((s) => s.setSelectedHex);
  const setSelectedNode = useUIStore((s) => s.setSelectedNode);

  if (events.length === 0) return null;

  return (
    <div className="pointer-events-auto absolute left-1/2 top-4 z-50 flex -translate-x-1/2 flex-col gap-2">
      {events.map((evt) => (
        <div
          key={evt.id}
          className="flex min-w-[320px] flex-col gap-2 rounded-lg border-2 border-crimson bg-dark-metal/95 p-3 shadow-lg shadow-crimson/20"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-widest text-crimson">
              Critical Event
            </span>
            <span className="font-mono text-[10px] text-ash">T{evt.event.tick}</span>
          </div>

          <div className="text-[12px] font-semibold text-bone">
            {evt.event.type.replace(/_/g, " ")}
          </div>

          {evt.linkedEntityId && (
            <span className="text-[11px] text-silver">
              {evt.linkedEntityType}: {evt.linkedEntityId}
            </span>
          )}

          <div className="flex gap-2">
            {evt.linkedEntityId && (
              <button
                onClick={() => {
                  if (evt.linkedEntityType === "territory") {
                    setSelectedHex(evt.linkedEntityId);
                  } else if (evt.linkedEntityId) {
                    setSelectedNode(evt.linkedEntityId);
                  }
                  markEventRead(evt.id);
                }}
                className="rounded bg-crimson/20 px-3 py-1 text-[10px] font-semibold text-crimson transition-colors hover:bg-crimson/30"
              >
                Navigate
              </button>
            )}
            <button
              onClick={() => markEventRead(evt.id)}
              className="rounded border border-wet-concrete px-3 py-1 text-[10px] text-ash transition-colors hover:text-silver"
            >
              Dismiss
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
