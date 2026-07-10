/**
 * Right Dock — three tabs: Action Composer / Inspector / Objectives
 * (spec-110 B5 adds the third tab).
 */

import { useStore } from "@/store";
import { ActionComposer } from "@/components/action/ActionComposer";
import { InspectorPanel } from "@/components/inspector/InspectorPanel";
import { ObjectivesTracker } from "@/components/objectives/ObjectivesTracker";

interface RightDockProps {
  gameId: string;
}

export function RightDock({ gameId }: RightDockProps): React.JSX.Element {
  const activeTab = useStore((s) => s.ui.rightDockTab);
  const setActiveTab = useStore((s) => s.ui.setRightDockTab);

  return (
    <aside
      data-testid="region-dock"
      aria-label="Dock"
      className="row-start-2 flex flex-col overflow-hidden border-l border-rebar"
    >
      <div className="flex border-b border-rebar">
        <TabButton active={activeTab === "actions"} onClick={() => setActiveTab("actions")}>
          Actions
        </TabButton>
        <TabButton active={activeTab === "inspector"} onClick={() => setActiveTab("inspector")}>
          Inspector
        </TabButton>
        <TabButton active={activeTab === "objectives"} onClick={() => setActiveTab("objectives")}>
          Objectives
        </TabButton>
      </div>
      <div className="flex-1 overflow-y-auto">
        {activeTab === "actions" && <ActionComposer gameId={gameId} />}
        {activeTab === "inspector" && <InspectorPanel />}
        {activeTab === "objectives" && <ObjectivesTracker gameId={gameId} />}
      </div>
    </aside>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`flex-1 py-2 text-[10px] font-semibold uppercase tracking-widest ${
        active ? "border-b-2 border-spire text-spire" : "text-ash hover:text-fog"
      }`}
    >
      {children}
    </button>
  );
}
