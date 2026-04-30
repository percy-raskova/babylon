import { useParams, useNavigate } from "react-router";
import { TopBar } from "@/components/layout/TopBar";
import { useGameState } from "@/hooks/useGameState";
import { NodeInspector } from "@/components/inspector/NodeInspector";
import { HexInspector } from "@/components/inspector/HexInspector";

export function IntelPage({ username, onLogout }: { username: string; onLogout: () => void }) {
  const {
    id: gameId = "",
    target_type,
    target_id,
  } = useParams<{ id: string; target_type: string; target_id: string }>();
  const navigate = useNavigate();
  const { snapshot, resolveTick, loading: resolving } = useGameState(gameId);

  function renderContent() {
    if (!snapshot) return <p className="text-silver">Loading snapshot...</p>;
    if (!target_id) return <p className="text-silver">Invalid target ID</p>;

    if (target_type === "territory") {
      return (
        <div className="flex-1 overflow-auto">
          <HexInspector snapshot={snapshot} hexId={target_id} />
        </div>
      );
    }
    if (target_type === "organization" || target_type === "institution") {
      return (
        <div className="flex-1 overflow-auto">
          <NodeInspector snapshot={snapshot} nodeId={target_id} />
        </div>
      );
    }
    return <p className="text-silver">Invalid target type or ID</p>;
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-void">
      {snapshot && (
        <TopBar
          snapshot={snapshot}
          gameId={gameId}
          username={username}
          resolving={resolving}
          onResolve={async () => {
            await resolveTick();
          }}
          onBack={() => navigate(`/games/${gameId}`)}
          onLogout={onLogout}
        />
      )}

      <div className="flex flex-1 flex-col overflow-hidden p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-wider text-gold uppercase">
            Intel: {target_type}
          </h2>
          <button
            onClick={() => navigate(`/games/${gameId}`)}
            className="rounded border border-wet-concrete px-4 py-2 text-sm text-silver hover:border-gold"
          >
            ← Back to Briefing
          </button>
        </div>

        <div className="mx-auto mt-4 flex w-full max-w-4xl flex-1 flex-col overflow-hidden rounded-lg border border-wet-concrete bg-dark-metal p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
