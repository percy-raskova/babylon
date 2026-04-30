import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import { get } from "@/api/client";
import { OrgDashboard } from "@/components/OrgDashboard";
import { TopBar } from "@/components/layout/TopBar";
import { useGameState } from "@/hooks/useGameState";
import type { OrgState } from "@/types/game";

export function OrganizationsPage({
  username,
  onLogout,
}: {
  username: string;
  onLogout: () => void;
}) {
  const { id: gameId = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [orgs, setOrgs] = useState<OrgState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // We can fetch the snapshot for the TopBar, but we fetch the orgs separately from the new endpoint.
  // Actually, we might just use the TopBar from the snapshot or we can just fetch the orgs alone.
  // The instructions specify its own API endpoint and contract.
  const { snapshot, resolveTick, loading: resolving } = useGameState(gameId);

  useEffect(() => {
    async function fetchOrgs() {
      try {
        const res = await get<{ organizations: OrgState[] }>(
          `/api/games/${gameId}/organizations/?player_only=true`,
        );
        if (res.status === "ok") {
          setOrgs(res.data.organizations);
        } else {
          setError(res.message ?? "Failed to fetch organizations");
        }
      } catch {
        setError("Error fetching organizations");
      } finally {
        setLoading(false);
      }
    }
    void fetchOrgs();
  }, [gameId]);

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
        {loading ? (
          <p className="text-silver">Loading organizations...</p>
        ) : (
          <div className="flex-1 overflow-auto rounded-lg border border-wet-concrete bg-dark-metal p-4">
            {snapshot ? (
              <OrgDashboard snapshot={{ ...snapshot, organizations: orgs }} />
            ) : (
              <p className="text-silver">Loading game data...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
