// GameList.jsx — Babylon Web App UI Kit · Cold Collapse v8

const SCENARIOS = [
  { key: "wayne_county", name: "Wayne County Organizer", description: "Organize in Wayne County, Michigan.", territory_count: 81 },
  { key: "us_nationwide", name: "United States — Nationwide", description: "Full CONUS simulation.", territory_count: 1100 },
];

const MOCK_GAMES = [
  { id: "wayne-county-001", scenario: "wayne_county", current_tick: 14, status: "active", created_at: "2026-03-01" },
  { id: "us-nationwide-003", scenario: "us_nationwide", current_tick: 3, status: "active", created_at: "2026-04-12" },
];

const GameList = ({ auth, onSelectGame, onLogout }) => {
  const [games, setGames] = React.useState(MOCK_GAMES);
  const [selectedScenario, setSelectedScenario] = React.useState("wayne_county");
  const [creating, setCreating] = React.useState(false);
  const selectedInfo = SCENARIOS.find(s => s.key === selectedScenario);

  function handleCreate() {
    setCreating(true);
    setTimeout(() => {
      const newId = selectedScenario + "-" + Math.random().toString(36).slice(2, 6);
      setGames(prev => [{ id: newId, scenario: selectedScenario, current_tick: 0, status: "active", created_at: new Date().toISOString().slice(0,10) }, ...prev]);
      setCreating(false);
    }, 600);
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--void)", fontFamily: "var(--font-sans)" }}>
      <nav style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        borderBottom: "1px solid var(--rebar)", background: "var(--void)",
        padding: "10px 24px", flexShrink: 0
      }}>
        <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: "0.32em", color: "var(--bone)", textTransform: "uppercase" }}>
          BAB<span style={{color:"var(--spire)",textShadow:"0 0 10px rgba(77,217,230,.5)"}}>Y</span>LON
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fog)" }}>{auth?.username}</span>
          <button onClick={onLogout} style={{
            background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4,
            padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer",
            letterSpacing: ".14em", textTransform: "uppercase"
          }}>Logout</button>
        </div>
      </nav>

      <div style={{ maxWidth: 760, width: "100%", margin: "0 auto", padding: "32px 24px", flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: "var(--bone)" }}>Your Games</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <select
              value={selectedScenario} onChange={e => setSelectedScenario(e.target.value)}
              style={{
                background: "var(--void)", border: "1px solid var(--wet-steel)", borderRadius: 4,
                padding: "8px 10px", fontSize: 12, color: "var(--bone)", outline: "none", cursor: "pointer"
              }}
            >
              {SCENARIOS.map(s => <option key={s.key} value={s.key}>{s.name}</option>)}
            </select>
            <button onClick={handleCreate} disabled={creating} style={{
              background: creating ? "rgba(77,217,230,.4)" : "var(--spire)",
              color: "var(--void)", border: "none", borderRadius: 4,
              padding: "8px 18px", fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
              letterSpacing: ".16em", textTransform: "uppercase",
              cursor: creating ? "not-allowed" : "pointer",
              boxShadow: creating ? "none" : "0 0 16px rgba(77,217,230,.2)"
            }}>
              {creating ? "Creating..." : "+ New Game"}
            </button>
          </div>
        </div>

        {selectedInfo && (
          <p style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ash)", marginBottom: 16, letterSpacing: ".05em" }}>
            {selectedInfo.description} ({selectedInfo.territory_count} territories)
          </p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {games.map(game => (
            <button key={game.id} onClick={() => onSelectGame(game.id)} style={{
              width: "100%", background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6,
              padding: "16px 20px", textAlign: "left", cursor: "pointer", transition: "border-color .2s, background .2s",
              fontFamily: "var(--font-sans)"
            }}
              onMouseOver={e => { e.currentTarget.style.borderColor="var(--spire)"; e.currentTarget.style.background="rgba(77,217,230,.03)"; }}
              onMouseOut={e => { e.currentTarget.style.borderColor="var(--rebar)"; e.currentTarget.style.background="var(--concrete)"; }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "var(--bone)" }}>{game.scenario}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, textTransform: "uppercase", letterSpacing: ".18em", color: game.status === "active" ? "var(--solidarity)" : "var(--ash)" }}>
                  ● {game.status}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fog)" }}>
                <span>Tick {String(game.current_tick).padStart(4,"0")}</span>
                <span>{game.id.slice(0, 12)}...</span>
              </div>
            </button>
          ))}
        </div>

        {games.length === 0 && (
          <p style={{ textAlign: "center", color: "var(--ash)", padding: "48px 0", fontFamily: "var(--font-mono)", fontSize: 12, letterSpacing: ".1em" }}>
            NO GAMES YET. CREATE ONE TO BEGIN.
          </p>
        )}
      </div>
    </div>
  );
};

Object.assign(window, { GameList });
