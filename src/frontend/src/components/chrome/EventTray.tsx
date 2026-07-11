/**
 * EventTray — chrome stub, persistent right rail hosting `EventsFeed`
 * verbatim (architecture §1.2's `BottomStrip` disperse row; §4.2). Lane A
 * hands this file to Lane E after merge (badge counts mirroring
 * `summary.event_counts`, TopBar alert-badge deep-link, are Lane E's
 * territory — architecture §4.3).
 *
 * `anchor="free"` — `AppShell` composes the shared right-column wrapper
 * (stacked with `ObjectivesTray` per the §1.1 layout diagram); this
 * component doesn't self-position a full-height right edge.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { EventsFeed } from "@/components/events/EventsFeed";

interface EventTrayProps {
  gameId: string;
}

export function EventTray(_props: EventTrayProps): React.JSX.Element {
  const eventTrayOpen = useStore((s) => s.ui.chrome.eventTrayOpen);
  const toggleEventTray = useStore((s) => s.ui.toggleEventTray);

  return (
    <FloatingPanel
      anchor="free"
      title="Events"
      collapsed={!eventTrayOpen}
      onToggle={toggleEventTray}
      width={280}
      testId="event-tray"
    >
      <EventsFeed />
    </FloatingPanel>
  );
}
