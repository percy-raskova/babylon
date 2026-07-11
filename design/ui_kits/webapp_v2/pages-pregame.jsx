// ============================================================================
// Babylon Frontend v2 — Pre-Game Routes
// /login, /games (lobby)
// No game chrome, no viz libs loaded. Fast and minimal.
// ============================================================================

const LoginPage = ({ onLogin }) => (
  <div style={{
    height: "100%", width: "100%", display: "flex", alignItems: "center",
    justifyContent: "center", background: "#0a0a0f",
    backgroundImage: "radial-gradient(ellipse at 30% 40%, rgba(110,16,32,.18), transparent 60%), radial-gradient(ellipse at 70% 80%, rgba(200,168,96,.06), transparent 60%)",
    fontFamily: "var(--font-sans)", color: "#e0e0e0"
  }}>
    <div style={{ width: 360, padding: 32, background: "#141420",
                   border: "1px solid #2a2a3a", borderRadius: 8 }}>
      <div style={{ textAlign: "center", marginBottom: 28 }}>
        <div style={{ display: "inline-block", padding: "4px 12px", marginBottom: 12,
                       border: "1px solid #c8a860", borderRadius: 9999 }}>
          <BblLabel color="#c8a860">Field Operations Console</BblLabel>
        </div>
        <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: ".5em",
                      color: "#c8a860", margin: 0,
                      textShadow: "0 0 20px rgba(200,168,96,.3)" }}>BABYLON</h1>
        <div style={{ fontSize: 11, color: "#787878", letterSpacing: ".25em",
                       textTransform: "uppercase", marginTop: 6 }}>v0.42 · build 2026.04</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <FieldInput label="Operative ID" placeholder="percy" />
        <FieldInput label="Pass Phrase" placeholder="••••••••" type="password" />
        <button onClick={onLogin} style={{
          background: "#c8a860", color: "#0a0a0f", border: "none", borderRadius: 6,
          padding: "10px 14px", fontSize: 12, fontWeight: 700, letterSpacing: ".2em",
          textTransform: "uppercase", cursor: "pointer",
          fontFamily: "var(--font-sans)", marginTop: 6
        }}>Authenticate ▸</button>
      </div>
      <div style={{ marginTop: 22, paddingTop: 14, borderTop: "1px solid #2a2a3a",
                     fontSize: 10, color: "#404040", textAlign: "center", lineHeight: 1.6 }}>
        Wayne County Test Bed · Validated against QCEW, BEA, Census, FRED<br/>
        <span style={{ color: "#c8a860" }}>“Without revolutionary theory there can be no revolutionary movement.”</span>
      </div>
    </div>
  </div>
);

const FieldInput = ({ label, placeholder, type = "text" }) => (
  <div>
    <BblLabel>{label}</BblLabel>
    <input type={type} placeholder={placeholder} style={{
      width: "100%", marginTop: 4, padding: "8px 10px",
      background: "#0a0a0f", border: "1px solid #2a2a3a", borderRadius: 4,
      color: "#e0e0e0", fontSize: 13, fontFamily: "var(--font-mono)",
      outline: "none"
    }}/>
  </div>
);

// ----------------------------------------------------------------------------
const GAME_LIST = [
  { id: "wayne-county-2026-001", scenario: "Wayne County Organizer", tick: 42,
    status: "active", players: 1, last_played: "2 min ago", briefing: "Informant detected in WCLF — heat elevated.",
    threat: "high" },
  { id: "wayne-county-2026-002", scenario: "Wayne County Organizer", tick: 17,
    status: "active", players: 1, last_played: "1 day ago", briefing: "Solidarity edge formed: WCLF ↔ Detroit Tenants Coalition.",
    threat: "low" },
  { id: "metro-detroit-2025-007", scenario: "Metro Detroit Calibration", tick: 134,
    status: "paused", players: 1, last_played: "1 week ago", briefing: "Settler militia consolidated Downriver. Three orgs lost.",
    threat: "lost" },
  { id: "wayne-county-2026-test", scenario: "Wayne County (Tutorial)", tick: 4,
    status: "completed", players: 1, last_played: "2 weeks ago", briefing: "Tutorial completed.",
    threat: "tutorial" },
];

const GamesLobbyPage = ({ onOpenGame, onLogout, username }) => {
  const [filter, setFilter] = React.useState("all");
  const filtered = filter === "all" ? GAME_LIST : GAME_LIST.filter(g => g.status === filter);
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column",
                   background: "#0a0a0f", color: "#e0e0e0",
                   fontFamily: "var(--font-sans)" }}>
      {/* Lobby topbar — minimal, no in-game chrome */}
      <div style={{ display: "flex", alignItems: "center", padding: "0 24px",
                     borderBottom: "1px solid #1a1a2a", height: 52, gap: 18 }}>
        <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: ".4em",
                        color: "#c8a860" }}>BABYLON</span>
        <span style={{ fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase",
                        color: "#787878" }}>Lobby</span>
        <span style={{ flex: 1 }}/>
        <span style={{ fontSize: 11, color: "#787878" }}>op. <span style={{ color: "#e0e0e0" }}>{username}</span></span>
        <button onClick={onLogout} style={{ background: "transparent", border: "1px solid #2a2a3a",
          color: "#787878", padding: "4px 10px", fontSize: 10, letterSpacing: ".15em",
          textTransform: "uppercase", borderRadius: 4, cursor: "pointer",
          fontFamily: "var(--font-sans)" }}>Sign Out</button>
      </div>
      {/* Body */}
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "320px 1fr",
                     gap: 0, minHeight: 0 }}>
        {/* Left: new game */}
        <div style={{ borderRight: "1px solid #1a1a2a", padding: 24,
                       display: "flex", flexDirection: "column", gap: 16 }}>
          <PageHeader title="New Operation" breadcrumbs={["Lobby", "New"]}/>
          <div style={{ marginTop: 4 }}>
            <BblLabel>Scenario</BblLabel>
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
              {["Wayne County Organizer", "Metro Detroit Calibration", "Custom (load .yml)"].map((s, i) => (
                <button key={s} style={{
                  textAlign: "left", padding: "12px 14px", background: i === 0 ? "rgba(200,168,96,.08)" : "transparent",
                  border: i === 0 ? "1px solid #c8a860" : "1px solid #2a2a3a",
                  borderRadius: 6, color: "#e0e0e0", cursor: "pointer",
                  fontFamily: "var(--font-sans)"
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{s}</div>
                  <div style={{ fontSize: 10, color: "#787878", marginTop: 4 }}>
                    {i === 0 && "5 territories · 5 communities · 2 player orgs"}
                    {i === 1 && "247 territories · validated against QCEW"}
                    {i === 2 && "Upload your own scenario file"}
                  </div>
                </button>
              ))}
            </div>
            <button style={{
              width: "100%", marginTop: 16, padding: "10px 14px", background: "#c8a860",
              color: "#0a0a0f", border: "none", borderRadius: 6, fontWeight: 700,
              letterSpacing: ".2em", fontSize: 11, textTransform: "uppercase",
              cursor: "pointer", fontFamily: "var(--font-sans)"
            }}>Begin Operation ▸</button>
          </div>
        </div>
        {/* Right: existing games */}
        <div style={{ padding: 24, overflow: "auto" }}>
          <PageHeader title="Active Operations" breadcrumbs={["Lobby"]}
            right={
              <div style={{ display: "flex", gap: 6 }}>
                {["all", "active", "paused", "completed"].map(f => (
                  <button key={f} onClick={() => setFilter(f)} style={{
                    background: filter === f ? "rgba(200,168,96,.15)" : "transparent",
                    border: filter === f ? "1px solid #c8a860" : "1px solid #2a2a3a",
                    color: filter === f ? "#c8a860" : "#787878",
                    fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase",
                    padding: "4px 10px", borderRadius: 4, cursor: "pointer",
                    fontFamily: "var(--font-sans)"
                  }}>{f}</button>
                ))}
              </div>
            }/>
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 8, marginTop: 16 }}>
            {filtered.map(g => {
              const tcolor = g.threat === "high" ? "#e04040" : g.threat === "lost" ? "#404040"
                            : g.threat === "tutorial" ? "#80b0e0" : "#40c040";
              return (
                <button key={g.id} onClick={() => onOpenGame(g.id)} style={{
                  display: "grid", gridTemplateColumns: "auto 1fr auto auto auto",
                  gap: 14, alignItems: "center", padding: "12px 14px",
                  background: "#141420", border: "1px solid #2a2a3a", borderRadius: 6,
                  color: "#e0e0e0", cursor: "pointer", textAlign: "left",
                  fontFamily: "var(--font-sans)"
                }}>
                  <div style={{ width: 4, height: 36, background: tcolor, borderRadius: 2 }}/>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{g.scenario}</div>
                    <div style={{ fontSize: 11, color: "#787878", marginTop: 2 }}>{g.briefing}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <BblLabel>Tick</BblLabel>
                    <BblData color="#c8a860">{g.tick}</BblData>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <BblLabel>Status</BblLabel>
                    <BblData color={g.status === "active" ? "#40c040" : "#787878"} size={11}>{g.status}</BblData>
                  </div>
                  <span style={{ fontSize: 16, color: "#787878" }}>›</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { LoginPage, GamesLobbyPage });
