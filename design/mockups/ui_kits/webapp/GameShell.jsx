// GameShell.jsx — Babylon Web App UI Kit · Cold Collapse v8
// Spire-primary, semantic accents per metric, cooled substrate, sharper radii

const LENSES = [
  { id: "economic", name: "Economic", icon: "▦" },
  { id: "political", name: "Political", icon: "◈" },
  { id: "social", name: "Social", icon: "◎" },
  { id: "strategic", name: "Strategic", icon: "◆" },
];

const BOTTOM_TABS = ["timeseries", "events", "notifications"];

const MOCK_SNAPSHOT = {
  tick: 42,
  session_id: "wayne-county-001",
  organizations: [{
    id: "ORG001", name: "Wayne County Labor Federation",
    org_type: "civil_society_org", class_character: "proletarian",
    budget: 142, cadre_level: 0.7, heat: 0.71,
    vanguard: { cadre_labor: 8.4, max_cadre_labor: 12, sympathizer_labor: 24.1, max_sympathizer_labor: 44, reputation: 0.63, budget: 142, heat: 0.71 }
  }],
  events: [
    { id: "e1", type: "EXTRACTION", severity: "warning", tick: 41, description: "Imperial rent increased by 0.042 in Dearborn territory" },
    { id: "e2", type: "CONSCIOUSNESS", severity: "info", tick: 42, description: "Class consciousness rising in Wayne County periphery" },
    { id: "e3", type: "HEAT_SPIKE", severity: "critical", tick: 42, description: "State heat elevated — informant detected in organizing network" },
  ],
};

const METRICS = [
  { id: "heat", label: "HEAT", value: "71%", color: "var(--heat)" },
  { id: "rent", label: "RENT", value: "0.34", color: "var(--rent)" },
  { id: "con",  label: "CON",  value: "0.22", color: "var(--cadre)" },
  { id: "sol",  label: "SOL",  value: "0.56", color: "var(--solidarity)" },
];

const AVAILABLE_ACTIONS = [
  { verb: "educate",  label: "Educate",  cost: "3 CL",  desc: "Raise consciousness in target community" },
  { verb: "mobilize", label: "Mobilize", cost: "5 SL",  desc: "Activate sympathizers for direct action" },
  { verb: "attack",   label: "Attack",   cost: "8 CL",  desc: "Targeted sabotage of bourgeois institution" },
  { verb: "aid",      label: "Aid",      cost: "$50",   desc: "Transfer material resources to allied org" },
];

const TS_DATA = [
  { label: "Imperial Rent", value: 0.342, color: "var(--rent)" },
  { label: "Consciousness", value: 0.218, color: "var(--cadre)" },
  { label: "Solidarity",    value: 0.561, color: "var(--solidarity)" },
  { label: "Heat",          value: 0.714, color: "var(--heat)" },
  { label: "Wealth",        value: 0.431, color: "var(--rupture)" },
];

const SEV_COLOR = { critical: "var(--laser)", warning: "var(--heat)", info: "var(--solidarity)" };

const GameShell = ({ auth, gameId, onBack, onLogout, onAction }) => {
  const [activeLens, setActiveLens] = React.useState("economic");
  const [bottomTab, setBottomTab] = React.useState("timeseries");
  const [bottomOpen, setBottomOpen] = React.useState(true);
  const [rightOpen, setRightOpen] = React.useState(true);
  const [graphOpen, setGraphOpen] = React.useState(false);
  const [resolving, setResolving] = React.useState(false);
  const [tick, setTick] = React.useState(42);
  const [notifCount, setNotifCount] = React.useState(3);

  const v = MOCK_SNAPSHOT.organizations[0].vanguard;

  function handleResolve() {
    setResolving(true);
    setTimeout(() => { setTick(t => t + 1); setResolving(false); }, 1200);
  }

  const labelStyle = { fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.22em", textTransform: "uppercase", color: "var(--ash)" };
  const chipStyle = { background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 4, padding: "4px 10px", display: "flex", gap: 6, alignItems: "center" };
  const ghostBtn = { background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "5px 12px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--void)", fontFamily: "var(--font-sans)" }}>

      {/* TOP BAR */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        borderBottom: "1px solid var(--rebar)", background: "var(--void)",
        padding: "9px 16px", flexShrink: 0, gap: 12
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={onBack} style={ghostBtn}>← Games</button>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ash)" }}>{gameId?.slice(0,12)}...</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, padding: "0 12px", borderLeft: "1px solid var(--rebar)", borderRight: "1px solid var(--rebar)" }}>
            <span style={labelStyle}>Tick</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 700, color: "var(--spire)", textShadow: "0 0 12px rgba(77,217,230,.4)" }}>{String(tick).padStart(4,"0")}</span>
          </div>
          <div style={{ display: "flex", gap: 5 }}>
            {METRICS.map(m => (
              <div key={m.id} style={chipStyle}>
                <span style={labelStyle}>{m.label}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: m.color }}>{m.value}</span>
              </div>
            ))}
          </div>
          {notifCount > 0 && (
            <div onClick={() => { setBottomTab("notifications"); setBottomOpen(true); setNotifCount(0); }}
              style={{ background: "var(--laser)", color: "var(--void)", borderRadius: 9999, minWidth: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700, padding: "0 5px", cursor: "pointer", boxShadow: "0 0 10px rgba(255,51,68,.4)" }}>{notifCount}</div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={handleResolve} disabled={resolving} style={{
            background: resolving ? "rgba(77,217,230,.4)" : "var(--spire)", color: "var(--void)", border: "none",
            borderRadius: 4, padding: "6px 16px", fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700,
            letterSpacing: "0.18em", textTransform: "uppercase",
            cursor: resolving ? "not-allowed" : "pointer",
            boxShadow: resolving ? "none" : "0 0 16px rgba(77,217,230,.25)"
          }}>
            {resolving ? "Resolving..." : "▸ Resolve Tick"}
          </button>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fog)" }}>{auth?.username}</span>
          <button onClick={onLogout} style={ghostBtn}>Logout</button>
        </div>
      </div>

      {/* RESOURCE BAR */}
      <div style={{ flexShrink: 0, padding: "8px 12px" }}>
        <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "12px 16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, paddingBottom: 8, borderBottom: "1px solid var(--rebar)" }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--bone)" }}>Wayne County Labor Federation</span>
            <span style={labelStyle}>civil_society_org</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 14 }}>
            {[
              { label: "CL", value: v.cadre_labor.toFixed(1), max: v.max_cadre_labor, color: "var(--cadre)", gauge: true },
              { label: "SL", value: v.sympathizer_labor.toFixed(1), max: v.max_sympathizer_labor, color: "var(--solidarity)", gauge: true },
              { label: "REP", value: `${(v.reputation*100).toFixed(0)}%`, color: "var(--solidarity)" },
              { label: "$$$", value: `$${v.budget.toFixed(0)}`, color: "var(--rupture)" },
              { label: "HEAT", value: `${(v.heat*100).toFixed(0)}%`, color: "var(--heat)" },
            ].map((r, i) => r.gauge ? (
              <div key={i}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={labelStyle}>{r.label}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: r.color }}>{r.value}</span>
                </div>
                <div style={{ height: 4, background: "var(--void)", borderRadius: 9999, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(parseFloat(r.value)/r.max)*100}%`, background: r.color, borderRadius: 9999 }}></div>
                </div>
              </div>
            ) : (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, padding: "4px 6px", background: "var(--void)", borderRadius: 4, border: "1px solid var(--rebar)" }}>
                <span style={labelStyle}>{r.label}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, color: r.color }}>{r.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* MAIN AREA */}
      <div style={{ display: "flex", minHeight: 0, flex: 1, overflow: "hidden" }}>
        {/* Graph panel */}
        {!graphOpen && (
          <button onClick={() => setGraphOpen(true)} style={{ width: 22, flexShrink: 0, background: "var(--void)", color: "var(--ash)", border: "none", borderRight: "1px solid var(--rebar)", cursor: "pointer", fontSize: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>▶</button>
        )}
        {graphOpen && (
          <div style={{ width: 220, flexShrink: 0, borderRight: "1px solid var(--rebar)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--rebar)", padding: "6px 10px", background: "var(--void)" }}>
              <span style={labelStyle}>Topology</span>
              <button onClick={() => setGraphOpen(false)} style={{ fontSize: 10, color: "var(--ash)", background: "none", border: "none", cursor: "pointer" }}>◀</button>
            </div>
            <div style={{ flex: 1, background: "var(--void)", padding: 12, overflow: "hidden", position: "relative" }}>
              <svg width="100%" height="100%" viewBox="0 0 196 300">
                {[
                  {x:98,y:30,label:"Proletariat",c:"#6b8fb5"},
                  {x:160,y:110,label:"Bourgeoisie",c:"#ff3344"},
                  {x:36,y:110,label:"L.Aristocracy",c:"#d4a02c"},
                  {x:98,y:200,label:"State",c:"#d97a2c"},
                  {x:50,y:260,label:"Precariat",c:"#7a6db8"}
                ].map((n,i) => (
                  <g key={i}>
                    <circle cx={n.x} cy={n.y} r={18} fill={n.c} fillOpacity={.15} stroke={n.c} strokeWidth={1.5}/>
                    <text x={n.x} y={n.y+4} textAnchor="middle" fill={n.c} fontSize={6.5} fontFamily="var(--font-mono)">{n.label}</text>
                  </g>
                ))}
                <line x1={98} y1={48} x2={160} y2={94} stroke="#ff3344" strokeWidth={1} strokeOpacity={.5}/>
                <line x1={98} y1={48} x2={36} y2={94} stroke="#5fbf7a" strokeWidth={1.5} strokeOpacity={.7}/>
                <line x1={36} y1={128} x2={98} y2={184} stroke="#d4a02c" strokeWidth={1} strokeOpacity={.4}/>
                <line x1={160} y1={128} x2={98} y2={184} stroke="#ff3344" strokeWidth={1} strokeOpacity={.5}/>
                <line x1={98} y1={218} x2={50} y2={244} stroke="#7a6db8" strokeWidth={1} strokeOpacity={.6}/>
                <text x={130} y={76} fill="#ff3344" fontSize={6} fontFamily="var(--font-mono)" opacity={.8}>EXPLOIT</text>
                <text x={52} y={76} fill="#5fbf7a" fontSize={6} fontFamily="var(--font-mono)" opacity={.8}>SOLIDARITY</text>
              </svg>
            </div>
          </div>
        )}

        {/* Center: map + bottom */}
        <div style={{ display: "flex", minWidth: 0, flex: 1, flexDirection: "column", overflow: "hidden" }}>
          <div style={{ flex: 1, padding: 10, overflow: "hidden" }}>
            <div style={{ height: "100%", borderRadius: 6, border: "1px solid var(--rebar)", background: "var(--concrete)", position: "relative", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: .7 }} viewBox="0 0 400 260" preserveAspectRatio="xMidYMid slice">
                {Array.from({length: 60}).map((_, i) => {
                  const cols = 10; const r = 18;
                  const col = i % cols; const row = Math.floor(i/cols);
                  const x = col * r * 1.75 + (row % 2 ? r * 0.875 : 0) + r;
                  const y = row * r * 1.52 + r;
                  // Heat ramp: tar → heat → laser (luminance-monotonic)
                  const ramp = ["#0d1016","#1a1f2a","#3a3530","#6b3318","#a04822","#d97a2c","#ff3344"];
                  const fill = ramp[Math.floor(Math.random()*ramp.length)];
                  const pts = Array.from({length:6}).map((_,j) => {
                    const a = Math.PI/180*(60*j-30);
                    return `${(x+r*.85*Math.cos(a)).toFixed(1)},${(y+r*.85*Math.sin(a)).toFixed(1)}`;
                  }).join(" ");
                  return <polygon key={i} points={pts} fill={fill} fillOpacity={.75} stroke="var(--void)" strokeWidth={.8}/>;
                })}
              </svg>
              <div style={{ position: "relative", textAlign: "center", zIndex: 2 }}>
                <div style={{ ...labelStyle, fontSize: 11, marginBottom: 4, color: "var(--fog)" }}>Wayne County · Hex Map</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--shroud)", letterSpacing: ".1em" }}>deck.gl · {activeLens.toUpperCase()} LENS</div>
              </div>
              <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, rgba(0,0,0,.06) 0, rgba(0,0,0,.06) 1px, transparent 1px, transparent 4px)", pointerEvents: "none" }}/>
              <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 70% 70% at center, transparent 40%, rgba(0,0,0,.7) 100%)", pointerEvents: "none" }}/>
            </div>
          </div>

          {/* Lens bar */}
          <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 4, borderTop: "1px solid var(--rebar)", background: "var(--void)", padding: "5px 12px" }}>
            <span style={{ ...labelStyle, marginRight: 8 }}>Lens</span>
            {LENSES.map(l => (
              <button key={l.id} onClick={() => setActiveLens(l.id)} style={{
                display: "flex", alignItems: "center", gap: 5,
                borderRadius: 3, padding: "5px 12px", fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 500, border: "none", cursor: "pointer",
                letterSpacing: ".14em", textTransform: "uppercase",
                background: activeLens === l.id ? "rgba(77,217,230,.08)" : "transparent",
                color: activeLens === l.id ? "var(--spire)" : "var(--ash)",
                borderBottom: activeLens === l.id ? "1px solid var(--spire)" : "1px solid transparent"
              }}>
                <span>{l.icon}</span>{l.name}
              </button>
            ))}
          </div>

          {/* Bottom panel */}
          <div style={{ flexShrink: 0, borderTop: "1px solid var(--rebar)", background: "var(--void)", height: bottomOpen ? 168 : 36, transition: "height .2s", overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "6px 12px", background: "var(--concrete)", borderBottom: bottomOpen ? "1px solid var(--rebar)" : "none" }}>
              <button onClick={() => setBottomOpen(o => !o)} style={{ width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "1px solid var(--rebar)", borderRadius: 3, color: "var(--fog)", cursor: "pointer", fontSize: 10 }}>
                {bottomOpen ? "▼" : "▲"}
              </button>
              {BOTTOM_TABS.map(tab => (
                <button key={tab} onClick={() => { setBottomTab(tab); setBottomOpen(true); }} style={{
                  position: "relative", borderRadius: 3, padding: "5px 12px", fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 500, border: "none", cursor: "pointer",
                  letterSpacing: ".14em", textTransform: "uppercase",
                  background: bottomTab === tab ? "rgba(77,217,230,.08)" : "transparent",
                  color: bottomTab === tab ? "var(--spire)" : "var(--ash)",
                  borderBottom: bottomTab === tab ? "1px solid var(--spire)" : "1px solid transparent"
                }}>
                  {tab === "timeseries" ? "Time Series" : tab === "events" ? "Events" : "Notifications"}
                  {tab === "notifications" && notifCount > 0 && (
                    <div style={{ position: "absolute", top: -3, right: -5, width: 14, height: 14, borderRadius: 9999, background: "var(--laser)", fontFamily: "var(--font-mono)", fontSize: 8, fontWeight: 700, color: "var(--void)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 0 8px rgba(255,51,68,.4)" }}>{notifCount}</div>
                  )}
                </button>
              ))}
            </div>
            {bottomOpen && (
              <div style={{ padding: "12px" }}>
                {bottomTab === "timeseries" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {TS_DATA.map(d => (
                      <div key={d.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ ...labelStyle, minWidth: 100 }}>{d.label}</span>
                        <div style={{ flex: 1, height: 3, background: "var(--rebar)", borderRadius: 9999, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${d.value*100}%`, background: d.color, borderRadius: 9999 }}></div>
                        </div>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: d.color, minWidth: 48, textAlign: "right" }}>{d.value.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                )}
                {bottomTab === "events" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                    {MOCK_SNAPSHOT.events.map(e => (
                      <div key={e.id} style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: SEV_COLOR[e.severity], minWidth: 12 }}>●</span>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", minWidth: 92, letterSpacing: ".1em" }}>{e.type}</span>
                        <span style={{ fontSize: 12, color: "var(--bone)" }}>{e.description}</span>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--shroud)", marginLeft: "auto" }}>t={e.tick}</span>
                      </div>
                    ))}
                  </div>
                )}
                {bottomTab === "notifications" && (
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ash)", letterSpacing: ".1em" }}>NO UNREAD NOTIFICATIONS.</div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right panel */}
        <div style={{ width: rightOpen ? 280 : 36, flexShrink: 0, borderLeft: "1px solid var(--rebar)", background: "var(--void)", transition: "width .2s", position: "relative", overflow: "hidden" }}>
          <button onClick={() => setRightOpen(o => !o)} style={{ position: "absolute", left: -12, top: 12, zIndex: 10, width: 24, height: 24, borderRadius: 9999, border: "1px solid var(--wet-steel)", background: "var(--concrete)", color: "var(--fog)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12 }}>
            {rightOpen ? "›" : "‹"}
          </button>
          {rightOpen && (
            <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10, height: "100%", overflowY: "auto" }}>
              <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 12 }}>
                <div style={{ ...labelStyle, marginBottom: 10, color: "var(--spire)" }}>▸ Action Composer</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {AVAILABLE_ACTIONS.map(a => (
                    <button key={a.verb} onClick={() => onAction(a.verb)} style={{
                      background: "transparent", border: "1px solid var(--rebar)",
                      borderRadius: 4, padding: "9px 11px", textAlign: "left", cursor: "pointer",
                      fontFamily: "var(--font-sans)", transition: "all .15s"
                    }}
                      onMouseOver={e => { e.currentTarget.style.borderColor="var(--spire)"; e.currentTarget.style.background="rgba(77,217,230,.04)"; }}
                      onMouseOut={e => { e.currentTarget.style.borderColor="var(--rebar)"; e.currentTarget.style.background="transparent"; }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 3 }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: "var(--bone)", textTransform: "uppercase", letterSpacing: "0.14em" }}>{a.label}</span>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--rupture)", fontWeight: 600 }}>{a.cost}</span>
                      </div>
                      <div style={{ fontSize: 11, color: "var(--fog)", lineHeight: 1.4 }}>{a.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 12 }}>
                <div style={{ ...labelStyle, marginBottom: 8 }}>Last Tick Results</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ash)", letterSpacing: ".05em" }}>RESOLVE A TICK TO SEE RESULTS.</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { GameShell });
