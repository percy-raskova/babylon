/**
 * ActionDock — chrome stub, bottom-center dock hosting `ActionComposer`
 * verbatim (architecture §1.2's `RightDock` disperse row, Actions tab →
 * "bottom-center verb bar; clicking a verb opens `ActionComposer` in a
 * `FloatingPanel`"). v1 keeps the composer open by default
 * (`ui.chrome.composerOpen`) so verb submission stays a one-step flow for
 * existing e2e coverage (`verb-submit.spec.ts`); Lane F owns building the
 * ≤3-verb bar + click-to-open behavior (Design Bible §5.1) on top of this
 * same `FloatingPanel` + `composerOpen` toggle.
 *
 * Keeps `region-dock` (architecture §6 testid-contract risk — real-loop.
 * spec.ts, owned by Lane G, still asserts it) — RightDock's Actions tab
 * was its default view, and this is its direct successor container.
 */

import { useStore } from "@/store";
import { FloatingPanel } from "./FloatingPanel";
import { ActionComposer } from "@/components/action/ActionComposer";

interface ActionDockProps {
  gameId: string;
}

export function ActionDock({ gameId }: ActionDockProps): React.JSX.Element {
  const composerOpen = useStore((s) => s.ui.chrome.composerOpen);
  const toggleComposer = useStore((s) => s.ui.toggleComposer);

  return (
    <FloatingPanel
      anchor="free"
      title="Actions"
      collapsed={!composerOpen}
      onToggle={toggleComposer}
      testId="region-dock"
    >
      <ActionComposer gameId={gameId} />
    </FloatingPanel>
  );
}
