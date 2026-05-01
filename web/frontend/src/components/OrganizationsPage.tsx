import { useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import { OrgDashboard } from "@/components/OrgDashboard";
import { TopBar } from "@/components/layout/TopBar";
import { useGameState } from "@/hooks/useGameState";
import { useGameStore } from "@/stores/gameStore";

export function OrganizationsPage({
  username,
  onLogout,
}: {
  username: string;
  onLogout: () => void;
}) {
  const { id: gameId = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { snapshot, resolveTick, loading: resolving } = useGameState(gameId);

  const playerOrgs = useGameStore((s) => s.playerOrgs);
  const playerOrgsLoaded = useGameStore((s) => s.playerOrgsLoaded);
  const fetchPlayerOrgs = useGameStore((s) => s.fetchPlayerOrgs);
  const error = useGameStore((s) => s.error);

  useEffect(() => {
    void fetchPlayerOrgs(gameId);
  }, [gameId, fetchPlayerOrgs]);

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
          onBack={() => navigate("/games")}
          onLogout={onLogout}
        />
      )}

      <div className="flex flex-1 flex-col overflow-hidden p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-wider text-gold uppercase">
            Player Organizations
          </h2>
          <button
            onClick={() => navigate(`/games/${gameId}`)}
            className="rounded border border-wet-concrete px-4 py-2 text-sm text-silver hover:border-gold"
          >
            ← Back to Briefing
          </button>
        </div>

        {error && <p className="text-crimson mb-4">{error}</p>}
        {!playerOrgsLoaded ? (
          <p className="text-silver">Loading organizations...</p>
        ) : (
          <div className="flex-1 overflow-auto rounded-lg border border-wet-concrete bg-dark-metal p-4">
            {snapshot ? (
              <OrgDashboard snapshot={{ ...snapshot, organizations: playerOrgs }} />
            ) : (
              <p className="text-silver">Loading game data...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
