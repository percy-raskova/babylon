/**
 * GameRouteShell — persistent chrome for all in-game routes.
 *
 * Mounts once per :id. Never re-mounts on sub-route navigation.
 * Renders TopBar + NavRail + <Outlet/>.
 */

import { Outlet, useParams, useNavigate } from "react-router";
import { NavRail } from "./NavRail";
import { TopBarV2 } from "./TopBarV2";

interface GameRouteShellProps {
  username: string;
  onLogout: () => void;
}

export function GameRouteShell({ username, onLogout }: GameRouteShellProps) {
  const { id: gameId = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-void">
      {/* Top bar — persistent across all in-game routes */}
      <TopBarV2 username={username} onBack={() => navigate("/games")} onLogout={onLogout} />

      {/* Body: NavRail + Page content */}
      <div className="flex min-h-0 flex-1">
        <NavRail gameId={gameId} />
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
