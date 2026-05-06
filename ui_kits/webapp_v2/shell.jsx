// ============================================================================
// Babylon Frontend v2 — Shell Components
// ----------------------------------------------------------------------------
// Persistent across all in-game routes:
//   - TopBar: tick counter, global resource readouts, RESOLVE TICK, user
//   - NavRail: Paradox-style left icon rail; route entries from ROUTES registry
//   - HUD primitives: BblTooltip (with breakdown), BblScope, BblPanel,
//     BblBadge, BblLabel, BblData, Sparkline, MapPlaceholder, GraphPlaceholder
// ============================================================================

// -------------- Tooltip primitive (Paradox-style breakdown) ----------------
// Mirrors `tooltipwidget = ...` — pass either text or a `breakdown` array of
// {label, value} pairs and we render provenance the way Paradox does.
const BblTooltip = ({ children, text, breakdown, total }) => {
  const [open, setOpen] = React.useState(false);
  const [pos, setPos] = React.useState({ x: 0, y: 0 });
  const ref = React.useRef(null);

  function move(e) {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    setPos({ x: r.left + r.width/2, y: r.top - 6 });
  }

  return (
    <span ref={ref}
      style={{ position: "relative", display: "inline-block", cursor: "help" }}
      onMouseEnter={(e) => { move(e); setOpen(true); }}
      onMouseLeave={() => setOpen(false)}
    >
      {children}
      {open && (
        <div style={{
          position: "fixed", left: pos.x, top: pos.y, transform: "translate(-50%, -100%)",
          zIndex: 9999, background: "#0a0a0f", border: "1px solid #c8a860",
          borderRadius: 6, padding: "8px 10px", minWidth: 200, maxWidth: 280,
          boxShadow: "0 0 24px rgba(0,0,0,.9), 0 0 8px rgba(200,168,96,.2)",
          pointerEvents: "none", fontFamily: "var(--font-sans)"
        }}>
          {text && <div style={{ fontSize: 11, color: "#e0e0e0", lineHeight: 1.4 }}>{text}</div>}
          {breakdown && (
            <div>
              <div style={{ fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase",
                            color: "#787878", marginBottom: 4, paddingBottom: 4,
                            borderBottom: "1px solid #2a2a3a" }}>Breakdown</div>
              {breakdown.map((b, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between",
                                       fontSize: 10, marginBottom: 2 }}>
                  <span style={{ color: "#888" }}>{b.label}</span>
                  <span style={{ fontFamily: "var(--font-mono)",
                                  color: b.value < 0 ? "#e06060" : "#c8a860" }}>
                    {b.value > 0 ? "+" : ""}{b.value.toFixed(3)}
                  </span>
                </div>
              ))}
              {total !== undefined && (
                <div style={{ display: "flex", justifyContent: "space-between",
                              fontSize: 11, marginTop: 4, paddingTop: 4,
                              borderTop: "1px solid #2a2a3a", color: "#c8a860", fontWeight: 600 }}>
                  <span>Total</span>
                  <span style={{ fontFamily: "var(--font-mono)" }}>{total.toFixed(3)}</span>
                </div>
              )}
            </div>
          )}
          {/* tip arrow */}
          <div style={{ position: "absolute", left: "50%", bottom: -6, transform: "translateX(-50%)",
                        width: 0, height: 0, borderLeft: "5px solid transparent",
                        borderRight: "5px solid transparent", borderTop: "6px solid #c8a860" }}/>
        </div>
      )}
    </span>
  );
};

// -------------- Atomic primitives -------------------------------------------
const BblLabel = ({ children, color = "#787878", style = {} }) => (
  <span style={{ fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase",
                  color, fontFamily: "var(--font-sans)", ...style }}>{children}</span>
);

const BblData = ({ children, color = "#c8a860", size = 12, style = {} }) => (
  <span style={{ fontFamily: "var(--font-mono)", fontSize: size, fontWeight: 600,
                  color, ...style }}>{children}</span>
);

const BblPanel = ({ title, right, children, style = {}, accent, bodyStyle = {} }) => (
  <div style={{
    background: "#141420", border: `1px solid ${accent || "#2a2a3a"}`, borderRadius: 8,
    overflow: "hidden", display: "flex", flexDirection: "column", minHeight: 0, ...style
  }}>
    {title && (
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                     padding: "8px 12px", borderBottom: "1px solid #2a2a3a",
                     background: "rgba(0,0,0,.3)", flexShrink: 0 }}>
        <BblLabel color="#c8a860">{title}</BblLabel>
        {right}
      </div>
    )}
    <div style={{ padding: 12, flex: 1, minHeight: 0, overflow: "auto", ...bodyStyle }}>{children}</div>
  </div>
);

const BblBadge = ({ children, color = "#888", bg = "rgba(255,255,255,.04)", style = {} }) => (
  <span style={{
    display: "inline-flex", alignItems: "center", gap: 4,
    fontSize: 9, fontWeight: 600, letterSpacing: ".15em", textTransform: "uppercase",
    color, background: bg, border: `1px solid ${color}33`,
    borderRadius: 9999, padding: "2px 8px", fontFamily: "var(--font-sans)",
    ...style
  }}>{children}</span>
);

// Class character → color (Article VII: color encodes meaning)
const CLASS_COLORS = {
  proletarian: "#e04040",
  bourgeois: "#c8a860",
  comprador_bourgeois: "#e0a030",
  labor_aristocracy: "#80b0e0",
  labor_aristocrat: "#80b0e0",
  lumpen: "#a070d0",
};
const EDGE_COLORS = {
  EXPLOITATION: "#e04040", SOLIDARITY: "#40c040", REPRESSION: "#e0a030",
  TRIBUTE: "#c8a860", TENANCY: "#a070d0", WAGES: "#80b0e0", ADJACENCY: "#404040",
};

// -------------- Sparkline ---------------------------------------------------
const Sparkline = ({ data, color = "#c8a860", w = 100, h = 24, label, value }) => {
  if (!data || !data.length) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const span = max - min || 1;
  const step = w / (data.length - 1);
  const pts = data.map((v, i) => `${i * step},${h - ((v - min) / span) * h}`).join(" ");
  const last = data[data.length - 1];
  const prev = data[data.length - 2] || last;
  const delta = last - prev;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {label && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <BblLabel>{label}</BblLabel>
          <BblData color={color} size={11}>{(value !== undefined ? value : last).toFixed(3)}</BblData>
        </div>
      )}
      <svg width={w} height={h} style={{ display: "block" }}>
        <polyline fill="none" stroke={color} strokeWidth="1.2" points={pts} />
        <circle cx={(data.length - 1) * step} cy={h - ((last - min) / span) * h} r="2" fill={color}/>
        {delta !== 0 && (
          <text x={w - 2} y={10} textAnchor="end" fontSize="8" fill={delta > 0 ? "#40c040" : "#e06060"}
                fontFamily="var(--font-mono)">{delta > 0 ? "▲" : "▼"}</text>
        )}
      </svg>
    </div>
  );
};

// -------------- Hex Map placeholder (deck.gl stand-in) ----------------------
const HexMap = ({ layer = "heat", lens = "economic", height = "100%", showLabels = true,
                  selectedTerritory = null, onTerritoryClick = () => {} }) => {
  const layerColors = {
    heat:           ["#1a0a1a", "#6e1020", "#c82828", "#e0a030", "#c8a860"],
    consciousness:  ["#0a0a0f", "#1e3c5c", "#4682dc", "#5a96e0", "#80b0e0"],
    wealth:         ["#0a0a0f", "#1e3c1e", "#3cb43c", "#a0c860", "#c8a860"],
    rent:           ["#0a0a0f", "#3a1e3a", "#7a3070", "#a070d0", "#e04040"],
    biocapacity:    ["#1a0a0a", "#6e2828", "#c8a860", "#7ab038", "#3cb43c"],
    population:     ["#0a0a0f", "#1e1e3c", "#5050a0", "#8060c0", "#a070d0"],
  };
  const palette = layerColors[layer] || layerColors.heat;
  // Deterministic hex grid w/ value patterns per layer
  const cols = 14, rows = 9;
  const r = 22;
  const tiles = [];
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const x = col * r * 1.75 + (row % 2 ? r * 0.875 : 0) + r;
      const y = row * r * 1.52 + r;
      // Deterministic value
      const v = (Math.sin(col * 1.7 + row * 2.3 + (layer === "heat" ? 0.3 : 0.7)) + 1) / 2;
      const colorIdx = Math.min(palette.length - 1, Math.floor(v * palette.length));
      const fill = palette[colorIdx];
      const pts = Array.from({length: 6}).map((_, j) => {
        const a = Math.PI/180*(60*j-30);
        return `${(x+r*.93*Math.cos(a)).toFixed(1)},${(y+r*.93*Math.sin(a)).toFixed(1)}`;
      }).join(" ");
      tiles.push({ x, y, pts, fill, key: `${col}-${row}` });
    }
  }
  return (
    <div style={{ position: "relative", height, width: "100%", overflow: "hidden",
                   background: "#0a0a0f", borderRadius: 6 }}>
      <svg style={{ display: "block", width: "100%", height: "100%" }}
           viewBox={`0 0 ${cols * r * 1.75 + r} ${rows * r * 1.52 + r}`}
           preserveAspectRatio="xMidYMid meet">
        {tiles.map(t => (
          <polygon key={t.key} points={t.pts} fill={t.fill} fillOpacity={.85}
                   stroke="#0a0a0f" strokeWidth=".8"/>
        ))}
      </svg>
      {/* Layer/Lens chip — exactly ONE framing selector visible */}
      <div style={{ position: "absolute", top: 8, left: 8, display: "flex", gap: 4, alignItems: "center" }}>
        <BblBadge color="#c8a860" bg="rgba(10,10,15,.85)">LAYER · {layer}</BblBadge>
      </div>
      {showLabels && (
        <div style={{ position: "absolute", bottom: 6, right: 8 }}>
          <BblData color="#404040" size={10}>WAYNE COUNTY · {tiles.length} HEXES</BblData>
        </div>
      )}
      {/* CRT overlay */}
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
                     background: "repeating-linear-gradient(0deg, rgba(0,0,0,.06) 0, rgba(0,0,0,.06) 1px, transparent 1px, transparent 4px)" }}/>
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none",
                     background: "radial-gradient(ellipse 90% 90% at center, transparent 50%, rgba(0,0,0,.7) 100%)" }}/>
    </div>
  );
};

// -------------- Topology graph placeholder (Cytoscape stand-in) ------------
const TopologyGraph = ({ height = 260, mode = "dyadic" }) => {
  // Article VIII.9: hyperedges are NOT pairwise. mode="topological" shows
  // BubbleSets-style hulls; mode="dyadic" shows NetworkX-style edges.
  const nodes = [
    { id: "n1", x: 120, y: 40,  label: "WCLF",       c: "#40c040" },
    { id: "n2", x: 260, y: 80,  label: "DTC",        c: "#40c040" },
    { id: "n3", x: 60,  y: 130, label: "WCSD",       c: "#e0a030" },
    { id: "n4", x: 220, y: 180, label: "DFB",        c: "#c8a860" },
    { id: "n5", x: 90,  y: 230, label: "S3",         c: "#a070d0" },
    { id: "n6", x: 320, y: 230, label: "DEARBORN-PROLE", c: "#e04040" },
  ];
  const edges = [
    { from: 0, to: 1, type: "SOLIDARITY",  c: "#40c040" },
    { from: 2, to: 0, type: "REPRESSION",  c: "#e0a030" },
    { from: 3, to: 5, type: "EXPLOITATION", c: "#e04040" },
    { from: 0, to: 5, type: "SOLIDARITY",  c: "#40c040" },
    { from: 1, to: 5, type: "SOLIDARITY",  c: "#40c040" },
    { from: 4, to: 0, type: "REPRESSION",  c: "#e0a030" },
  ];
  return (
    <svg width="100%" height={height} viewBox="0 0 380 280" style={{ display: "block" }}>
      {mode === "topological" && (
        <ellipse cx={205} cy={150} rx={140} ry={65} fill="#e04040" fillOpacity={.06}
                 stroke="#e04040" strokeOpacity={.3} strokeWidth="1" strokeDasharray="3 3"/>
      )}
      {edges.map((e, i) => (
        <line key={i} x1={nodes[e.from].x} y1={nodes[e.from].y}
              x2={nodes[e.to].x} y2={nodes[e.to].y}
              stroke={e.c} strokeOpacity={.55} strokeWidth="1.4"/>
      ))}
      {nodes.map(n => (
        <g key={n.id}>
          <circle cx={n.x} cy={n.y} r={16} fill={n.c} fillOpacity={.18}
                  stroke={n.c} strokeWidth="1.4"/>
          <text x={n.x} y={n.y + 3} textAnchor="middle" fontSize="7" fill={n.c}
                fontFamily="var(--font-mono)" letterSpacing=".05em">{n.label}</text>
        </g>
      ))}
    </svg>
  );
};

// -------------- TopBar (persistent across in-game routes) -------------------
const TopBar = ({ tick, sessionId, currentOrg, onResolve, onLogout, username, route }) => {
  const [resolving, setResolving] = React.useState(false);
  function handleResolve() {
    setResolving(true);
    setTimeout(() => { setResolving(false); onResolve && onResolve(); }, 900);
  }
  const v = currentOrg?.vanguard;
  return (
    <div style={{
      display: "flex", alignItems: "stretch", borderBottom: "1px solid #1a1a2a",
      background: "#0a0a0f", flexShrink: 0
    }}>
      {/* Brand block */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 18px",
                     borderRight: "1px solid #1a1a2a", minWidth: 180 }}>
        <div style={{ width: 8, height: 8, background: "#e04040", borderRadius: 9999,
                       boxShadow: "0 0 8px rgba(224,64,64,.7)" }}/>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: ".4em",
                         color: "#c8a860" }}>BABYLON</div>
          <div style={{ fontSize: 8, letterSpacing: ".2em", textTransform: "uppercase",
                         color: "#404040" }}>The Fall of America</div>
        </div>
      </div>
      {/* Tick block */}
      <BblTooltip text={`Tick ${tick} of session ${sessionId}. Each tick = one quarter-year. Click RESOLVE TICK to advance.`}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "0 18px",
                       borderRight: "1px solid #1a1a2a", height: "100%" }}>
          <div>
            <BblLabel>Tick</BblLabel>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 26, fontWeight: 700,
                           color: "#c8a860", lineHeight: 1, marginTop: 2,
                           textShadow: "0 0 10px rgba(200,168,96,.4)" }}>{tick}</div>
          </div>
          <div style={{ width: 1, height: 32, background: "#1a1a2a" }}/>
          <div>
            <BblLabel>Phase</BblLabel>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "#80b0e0",
                           marginTop: 2 }}>{currentOrg?.ooda_phase || "—"}</div>
          </div>
        </div>
      </BblTooltip>
      {/* Org / vanguard readouts */}
      {v && (
        <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "0 18px",
                       borderRight: "1px solid #1a1a2a", flex: 1 }}>
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <BblLabel>Active Org</BblLabel>
            <div style={{ fontSize: 12, color: "#e0e0e0", fontWeight: 600, marginTop: 1 }}>{currentOrg.short}</div>
          </div>
          <Gauge label="CL" value={v.cl} max={v.cl_max} color="#80b0e0"
            tooltip={`Cadre Labor — committed organizers. ${v.cl}/${v.cl_max} available this tick.`}/>
          <Gauge label="SL" value={v.sl} max={v.sl_max} color="#40c040"
            tooltip={`Sympathizer Labor — uncommitted potential. ${v.sl}/${v.sl_max} this tick.`}/>
          <Stat label="REP" value={`${(v.rep*100).toFixed(0)}%`} color="#40c040"
            tooltip="Reputation in target communities — affects Educate efficacy."/>
          <Stat label="$"    value={`$${v.budget}`} color="#c8a860"
            tooltip="Budget — used by Aid and to maintain infrastructure."/>
          <BblTooltip
            breakdown={Scope.getScriptValueBreakdown("heat")}
            total={v.heat}
          >
            <Stat label="HEAT" value={`${(v.heat*100).toFixed(0)}%`}
              color={v.heat > 0.6 ? "#e04040" : v.heat > 0.4 ? "#e0a030" : "#888"}
              wrap={false}/>
          </BblTooltip>
        </div>
      )}
      {/* Resolve + user */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 18px" }}>
        <button onClick={handleResolve} disabled={resolving} style={{
          background: resolving ? "rgba(200,168,96,.3)" : "#c8a860", color: "#0a0a0f",
          border: "none", borderRadius: 6, padding: "8px 18px", fontSize: 11, fontWeight: 700,
          letterSpacing: ".15em", textTransform: "uppercase", cursor: resolving ? "wait" : "pointer",
          fontFamily: "var(--font-sans)",
          boxShadow: resolving ? "none" : "0 0 12px rgba(200,168,96,.3)"
        }}>{resolving ? "Resolving…" : "Resolve Tick ▸"}</button>
        <span style={{ fontSize: 12, color: "#888" }}>{username}</span>
      </div>
    </div>
  );
};

const Gauge = ({ label, value, max, color, tooltip }) => {
  const pct = Math.min(1, value / max);
  const inner = (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 70 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <BblLabel>{label}</BblLabel>
        <BblData color={color} size={10}>{value.toFixed(1)}<span style={{ color: "#404040" }}>/{max}</span></BblData>
      </div>
      <div style={{ height: 4, background: "#1a1a2a", borderRadius: 9999, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct*100}%`, background: color }}/>
      </div>
    </div>
  );
  return tooltip ? <BblTooltip text={tooltip}>{inner}</BblTooltip> : inner;
};

const Stat = ({ label, value, color, tooltip, wrap = true }) => {
  const inner = (
    <div style={{ display: "flex", flexDirection: "column", gap: 1, alignItems: "flex-start" }}>
      <BblLabel>{label}</BblLabel>
      <BblData color={color} size={12}>{value}</BblData>
    </div>
  );
  if (!wrap) return inner;
  return tooltip ? <BblTooltip text={tooltip}>{inner}</BblTooltip> : inner;
};

// -------------- NavRail (Paradox-style left icon rail) ---------------------
const NavRail = ({ currentRoute, onNavigate, badges = {} }) => {
  const groups = [
    { label: "PLAY", routes: ROUTES.filter(r => r.group === "core") },
    { label: "VERBS", routes: ROUTES.filter(r => r.group === "verb") },
    { label: "ANALYZE", routes: ROUTES.filter(r => r.group === "post") },
  ];
  return (
    <div style={{
      width: 56, flexShrink: 0, background: "#0a0a0f", borderRight: "1px solid #1a1a2a",
      display: "flex", flexDirection: "column", padding: "8px 0", gap: 4,
      overflowY: "auto"
    }}>
      {groups.map((g, gi) => (
        <React.Fragment key={g.label}>
          {gi > 0 && <div style={{ height: 1, background: "#1a1a2a", margin: "8px 12px" }}/>}
          <div style={{ padding: "0 8px", marginBottom: 2 }}>
            <BblLabel style={{ fontSize: 8, letterSpacing: ".25em" }}>{g.label}</BblLabel>
          </div>
          {g.routes.map(r => {
            const active = r.key === currentRoute;
            const badge = badges[r.key];
            return (
              <BblTooltip key={r.key} text={`${r.label} — ${r.path}`}>
                <button onClick={() => onNavigate(r.key)} style={{
                  position: "relative", width: 40, height: 40, margin: "0 auto",
                  background: active ? "rgba(200,168,96,.15)" : "transparent",
                  border: active ? "1px solid #c8a860" : "1px solid transparent",
                  borderRadius: 6, color: active ? "#c8a860" : "#787878",
                  fontSize: 16, cursor: "pointer", display: "flex",
                  alignItems: "center", justifyContent: "center",
                  fontFamily: "var(--font-mono)", transition: "all .12s"
                }}
                  onMouseEnter={e => !active && (e.currentTarget.style.color = "#c8a860")}
                  onMouseLeave={e => !active && (e.currentTarget.style.color = "#787878")}
                >
                  {r.icon}
                  {badge && (
                    <span style={{ position: "absolute", top: 2, right: 2,
                                    background: "#e04040", color: "#0a0a0f",
                                    fontSize: 8, fontWeight: 700, fontFamily: "var(--font-mono)",
                                    minWidth: 14, height: 14, borderRadius: 9999,
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    padding: "0 3px" }}>{badge}</span>
                  )}
                </button>
              </BblTooltip>
            );
          })}
        </React.Fragment>
      ))}
    </div>
  );
};

// -------------- Layout shell ------------------------------------------------
const GameRouteShell = ({ children, currentRoute, onNavigate, badges, tick,
                          sessionId, currentOrg, onResolve, onLogout, username }) => (
  <div style={{ height: "100%", display: "flex", flexDirection: "column",
                 background: "#0a0a0f", fontFamily: "var(--font-sans)",
                 color: "#e0e0e0", overflow: "hidden" }}>
    <TopBar tick={tick} sessionId={sessionId} currentOrg={currentOrg}
            onResolve={onResolve} onLogout={onLogout} username={username}
            route={currentRoute}/>
    <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
      <NavRail currentRoute={currentRoute} onNavigate={onNavigate} badges={badges}/>
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column",
                     overflow: "hidden", position: "relative" }}>
        {children}
      </div>
    </div>
  </div>
);

// -------------- Page header (consistent across routes) ---------------------
const PageHeader = ({ title, subtitle, breadcrumbs, right }) => (
  <div style={{ padding: "16px 24px 8px", borderBottom: "1px solid #1a1a2a",
                 display: "flex", justifyContent: "space-between", alignItems: "flex-end",
                 flexShrink: 0 }}>
    <div>
      {breadcrumbs && (
        <div style={{ display: "flex", gap: 6, marginBottom: 4, alignItems: "center" }}>
          {breadcrumbs.map((b, i) => (
            <React.Fragment key={i}>
              {i > 0 && <span style={{ color: "#404040", fontSize: 10 }}>›</span>}
              <span style={{ fontSize: 10, color: i === breadcrumbs.length-1 ? "#c8a860" : "#787878",
                              letterSpacing: ".15em", textTransform: "uppercase" }}>{b}</span>
            </React.Fragment>
          ))}
        </div>
      )}
      <h1 style={{ fontSize: 22, fontWeight: 700, color: "#e0e0e0",
                    letterSpacing: ".05em", margin: 0 }}>{title}</h1>
      {subtitle && (
        <div style={{ fontSize: 12, color: "#787878", marginTop: 2 }}>{subtitle}</div>
      )}
    </div>
    {right}
  </div>
);

Object.assign(window, {
  BblTooltip, BblLabel, BblData, BblPanel, BblBadge,
  CLASS_COLORS, EDGE_COLORS,
  Sparkline, HexMap, TopologyGraph,
  TopBar, NavRail, GameRouteShell, PageHeader, Gauge, Stat,
});
