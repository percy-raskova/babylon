// synopticon-panopticon.jsx — Operations HUD
//
// Layout:
//   ┌────────── Stats strip (6 boxes) ─────────────┐
//   │ Histogram │  Sparrow heatmap   │ Gospel top-5 │
//   │  + dist   │  (the network)     │              │
//   └─── Time-series sparklines ──────────────────────┘

const PanopticonTab = ({ onOpenGospel, onOpenDossier }) => {
  const { META, GOSPEL, NETWORK, RISK_HISTOGRAM, TIMESERIES, THRESHOLDS, TERRITORIES } = window.SYN_DATA;
  const [hoverNode, setHoverNode] = React.useState(null);

  // ─── Top stats strip ───────────────────────────────────────────────────
  const StatBox = ({ label, value, sub, color, delta }) => (
    <div className="syn-panel" style={{ padding: "10px 14px", flex: 1, minWidth: 0, borderRadius: 0 }}>
      <div className="stat-l" style={{ marginBottom: 6 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span className="stat-v num" style={{ color: color || "var(--bone)" }}>{value}</span>
        {sub && <span className="num" style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.12em" }}>{sub}</span>}
      </div>
      {delta && (
        <div className="stat-delta num" style={{ marginTop: 4, color: delta.color || "var(--ash)" }}>
          {delta.text}
        </div>
      )}
    </div>
  );

  // ─── Histogram of risk distribution ────────────────────────────────────
  const maxCount = Math.max(...RISK_HISTOGRAM.map(b => b[2]));
  const Histogram = () => (
    <div className="syn-panel" style={{ height: "100%" }}>
      <div className="syn-panel-head">
        <span className="ttl">▸ RISK DISTRIBUTION</span>
        <span className="sub">N = {RISK_HISTOGRAM.reduce((s,b)=>s+b[2],0).toLocaleString()}</span>
      </div>
      <div className="syn-panel-body" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ flex: 1, display: "flex", alignItems: "flex-end", gap: 4, minHeight: 160, position: "relative" }}>
          {/* Y-axis label */}
          <div style={{
            position: "absolute", left: -2, top: 0,
            writingMode: "vertical-rl", transform: "rotate(180deg)",
            fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: "0.22em",
            color: "var(--ash)", textTransform: "uppercase",
          }}>NODES (log scale clipped)</div>
          {RISK_HISTOGRAM.map((b, i) => {
            const [lo, hi, count, lbl] = b;
            const h = Math.pow(count / maxCount, 0.5) * 100; // softened
            const isElim = lo >= 0.9;
            const isSup  = lo >= 0.7 && lo < 0.9;
            const isMon  = lo >= 0.4 && lo < 0.7;
            const cls = isElim ? "eliminate" : isSup ? "suppress" : isMon ? "monitor" : "";
            return (
              <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "stretch", height: "100%", justifyContent: "flex-end", marginLeft: 8 }}>
                <div className="num" style={{ fontSize: 9, color: cls ? "var(--bone)" : "var(--ash)", textAlign: "center", marginBottom: 2 }}>{count}</div>
                <div className={`hist-bar ${cls}`} style={{ height: `${h}%`, minHeight: 3, borderRadius: "1px 1px 0 0" }}></div>
              </div>
            );
          })}
        </div>
        {/* X axis with threshold tick markers */}
        <div style={{ position: "relative", height: 32 }}>
          {/* tick row */}
          <div style={{ display: "flex", gap: 4 }}>
            {RISK_HISTOGRAM.map((b, i) => (
              <div key={i} style={{ flex: 1, marginLeft: 8 }}>
                <div className="num" style={{ fontSize: 8, color: "var(--ash)", textAlign: "center" }}>
                  {b[0].toFixed(1)}
                </div>
              </div>
            ))}
          </div>
          {/* threshold legend below */}
          <div style={{ display: "flex", justifyContent: "space-around", marginTop: 8, gap: 8 }}>
            <span className="num" style={{ fontSize: 8.5, color: "var(--heat)", letterSpacing: "0.2em" }}>
              ◆ MON {THRESHOLDS.monitor}
            </span>
            <span className="num" style={{ fontSize: 8.5, color: "var(--laser)", letterSpacing: "0.2em" }}>
              ◆ SUP {THRESHOLDS.suppress}
            </span>
            <span className="num" style={{ fontSize: 8.5, color: "var(--laser)", letterSpacing: "0.2em", textShadow: "0 0 6px rgba(255,51,68,0.5)" }}>
              ◆ KILL {THRESHOLDS.eliminate}
            </span>
          </div>
        </div>

        {/* threshold summary */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6, marginTop: 4 }}>
          <div style={{ borderLeft: "2px solid var(--heat)", paddingLeft: 8 }}>
            <div className="num" style={{ fontSize: 22, fontWeight: 700, color: "var(--heat)", letterSpacing: "0.04em" }}>{META.flagged}</div>
            <div className="label">flagged</div>
          </div>
          <div style={{ borderLeft: "2px solid var(--laser)", paddingLeft: 8 }}>
            <div className="num" style={{ fontSize: 22, fontWeight: 700, color: "var(--laser)", letterSpacing: "0.04em" }}>{META.on_suppress}</div>
            <div className="label">suppress</div>
          </div>
          <div style={{ borderLeft: "2px solid var(--laser)", paddingLeft: 8 }}>
            <div className="num" style={{ fontSize: 22, fontWeight: 700, color: "var(--laser)", letterSpacing: "0.04em", textShadow: "0 0 8px rgba(255,51,68,0.4)" }}>{META.on_kill_list}</div>
            <div className="label">kill list</div>
          </div>
        </div>

        <div style={{ borderTop: "1px solid var(--rebar)", paddingTop: 10 }}>
          <div className="label" style={{ marginBottom: 6 }}>▸ Coverage</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
            <span className="num" style={{ fontSize: 11, color: "var(--bone)" }}>Legible projection</span>
            <span className="num" style={{ fontSize: 12, color: "var(--spire)", fontWeight: 700 }}>{(META.coverage_pct * 100).toFixed(0)}%</span>
          </div>
          <div style={{ height: 4, background: "var(--rebar)" }}>
            <div style={{ width: `${META.coverage_pct * 100}%`, height: "100%", background: "linear-gradient(90deg, var(--cadre), var(--spire))" }}></div>
          </div>
          <div className="num" style={{ fontSize: 10, color: "var(--ash)", marginTop: 4 }}>
            Signal loss: {(META.signal_loss_pct * 100).toFixed(0)}% — fog estimate
          </div>
        </div>
      </div>
    </div>
  );

  // ─── Sparrow heatmap — the network ─────────────────────────────────────
  const Heatmap = () => {
    const W = 900, H = 700;
    const nodeColor = (r) => {
      if (r == null) return "var(--shroud)";
      if (r >= 0.9)  return "var(--laser)";
      if (r >= 0.7)  return "var(--heat)";
      if (r >= 0.4)  return "var(--cadre)";
      return "var(--ash)";
    };
    const nodeR = (c) => 5 + c * 14;

    return (
      <div className="syn-panel crt-overlay" style={{ height: "100%", position: "relative", overflow: "hidden" }}>
        <div className="syn-panel-head" style={{ position: "relative", zIndex: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="ttl">▸ SPARROW · CENTRALITY HEATMAP</span>
            <span className="badge-status s-TARGET" style={{ fontSize: 8 }}>
              <span className="dot"></span>LEGIBLE PROJECTION
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span className="sub">N {NETWORK.nodes.length}</span>
            <span className="sub">E {NETWORK.edges.length}</span>
            <span className="sub" style={{ color: "var(--ash)" }}>SCAN T-{META.tick}</span>
          </div>
        </div>

        <div style={{ position: "relative", flex: 1, minHeight: 0 }}>
          <div className="scan-line"></div>

          {/* Floating annotation overlay — top-left "what they see" caption */}
          <div style={{
            position: "absolute", top: 12, left: 14, zIndex: 8,
            maxWidth: 260, pointerEvents: "none",
          }}>
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: 9,
              letterSpacing: "0.28em", color: "var(--laser)",
              textTransform: "uppercase", fontWeight: 700,
            }}>
              ◆ This is what they see of you.
            </div>
            <div className="num" style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.14em", marginTop: 4, lineHeight: 1.5 }}>
              Ghost nodes (□) = clusters inferred from signal-edge<br/>
              residuals. Identity unresolved. Risk unscored.
            </div>
          </div>

          {/* Hover panel — top-right */}
          {hoverNode && (
            <div style={{
              position: "absolute", top: 12, right: 14, zIndex: 8,
              background: "var(--tar)", border: "1px solid var(--laser)",
              padding: "10px 14px", minWidth: 240,
              boxShadow: "0 0 14px rgba(255,51,68,0.25)",
            }}>
              <div className="num" style={{ fontSize: 9, color: "var(--laser)", letterSpacing: "0.24em", marginBottom: 4 }}>
                ◆ NODE SELECTED
              </div>
              <div className="num" style={{ fontSize: 13, color: "var(--bone)", fontWeight: 700, letterSpacing: "0.08em" }}>
                {hoverNode.entity}
              </div>
              <div className="num" style={{ fontSize: 10, color: "var(--laser)", letterSpacing: "0.18em", marginTop: 2 }}>
                ◆ {hoverNode.a}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 12px", marginTop: 10, fontFamily: "var(--font-mono)", fontSize: 10.5 }}>
                <span className="label">RISK</span>
                <span style={{ color: hoverNode.r >= 0.9 ? "var(--laser)" : hoverNode.r >= 0.7 ? "var(--heat)" : "var(--bone)", fontWeight: 700 }}>
                  {hoverNode.r != null ? hoverNode.r.toFixed(2) : "—"}
                </span>
                <span className="label">CENT</span>
                <span style={{ color: "var(--cadre)" }}>{hoverNode.c.toFixed(2)}</span>
                <span className="label">STATUS</span>
                <span style={{ color: "var(--bone)" }}>{hoverNode.s}</span>
              </div>
            </div>
          )}

          {/* Bottom legend */}
          <div style={{
            position: "absolute", bottom: 10, left: 14, zIndex: 8,
            display: "flex", gap: 18, alignItems: "center",
            fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.2em", color: "var(--ash)",
          }}>
            <span>● = entity</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--laser)", boxShadow: "0 0 5px var(--laser)" }}></span>
              KILL ≥0.9
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--heat)" }}></span>
              SUPRESS ≥0.7
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--cadre)" }}></span>
              MON ≥0.4
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 2, border: "1px solid var(--shroud)", borderStyle: "dashed" }}></span>
              GHOST
            </span>
          </div>

          <svg className="spw-svg" viewBox={`0 100 ${W} ${H - 100}`} preserveAspectRatio="xMidYMid meet">
            {/* light grid */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--rebar)" strokeWidth="0.3" opacity="0.6"/>
              </pattern>
            </defs>
            <rect x="0" y="100" width={W} height={H - 100} fill="url(#grid)" />

            {/* concentric panopticon rings */}
            <g className="spw-rings">
              {[100, 180, 260, 340, 420].map(r => (
                <circle key={r} cx={W/2} cy={400} r={r} />
              ))}
            </g>

            {/* edges */}
            <g>
              {NETWORK.edges.map(([from, to, w], i) => {
                const a = NETWORK.nodes.find(n => n.id === from);
                const b = NETWORK.nodes.find(n => n.id === to);
                if (!a || !b) return null;
                const isGhost = from.startsWith("g") || to.startsWith("g");
                const isHigh = !isGhost && (a.r || 0) >= 0.7 && (b.r || 0) >= 0.7;
                return (
                  <line key={i}
                    x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                    className={`spw-edge ${isGhost ? "ghost" : isHigh ? "high" : ""}`}
                  />
                );
              })}
            </g>

            {/* halos for TARGETs */}
            {NETWORK.nodes.filter(n => n.s === "TARGET").map(n => (
              <g key={`h-${n.id}`}>
                <circle cx={n.x} cy={n.y} r={nodeR(n.c) + 7} className="spw-node-halo" />
                <circle cx={n.x} cy={n.y} r={nodeR(n.c)} className="spw-pulse" />
              </g>
            ))}

            {/* nodes */}
            {NETWORK.nodes.map(n => {
              const isGhost = n.s === "GHOST";
              const isElim = n.s === "ELIMINATED";
              if (isGhost) {
                return (
                  <g key={n.id}
                     className="spw-node"
                     style={{ color: "var(--shroud)" }}
                     onMouseEnter={() => setHoverNode(n)}
                     onMouseLeave={() => setHoverNode(null)}
                  >
                    <rect x={n.x - 6} y={n.y - 6} width="12" height="12"
                          fill="transparent" stroke="var(--shroud)" strokeWidth="0.8" strokeDasharray="2 2"/>
                    <text x={n.x + 12} y={n.y + 3} className="spw-node-label ghost">{n.a}</text>
                  </g>
                );
              }
              return (
                <g key={n.id}
                   className="spw-node"
                   style={{ color: nodeColor(n.r) }}
                   onMouseEnter={() => setHoverNode(n)}
                   onMouseLeave={() => setHoverNode(null)}
                   onClick={() => onOpenDossier && onOpenDossier(n.entity)}
                >
                  <circle cx={n.x} cy={n.y} r={nodeR(n.c)}
                          fill={nodeColor(n.r)}
                          stroke={isElim ? "var(--shroud)" : "var(--void)"}
                          strokeWidth="1.5"
                          opacity={isElim ? 0.4 : 1}
                  />
                  {/* crosshair on TARGETs */}
                  {n.s === "TARGET" && (
                    <g className="spw-crosshair">
                      <line x1={n.x - 18} y1={n.y} x2={n.x + 18} y2={n.y}/>
                      <line x1={n.x} y1={n.y - 18} x2={n.x} y2={n.y + 18}/>
                    </g>
                  )}
                  <text x={n.x + nodeR(n.c) + 4} y={n.y + 3}
                        className={`spw-node-label ${n.s === "TARGET" ? "t" : ""} ${isElim ? "elim" : ""}`}>
                    {n.a}
                  </text>
                </g>
              );
            })}

            {/* compass / scale */}
            <g transform={`translate(${W - 100}, ${H - 30})`}>
              <line x1="0" y1="0" x2="60" y2="0" stroke="var(--fog)" strokeWidth="1"/>
              <line x1="0" y1="-3" x2="0" y2="3" stroke="var(--fog)" strokeWidth="1"/>
              <line x1="60" y1="-3" x2="60" y2="3" stroke="var(--fog)" strokeWidth="1"/>
              <text x="30" y="-6" textAnchor="middle" className="spw-node-label" style={{ fill: "var(--fog)" }}>
                ≈ 1 hop
              </text>
            </g>
          </svg>
        </div>
      </div>
    );
  };

  // ─── Gospel preview (top 5) ────────────────────────────────────────────
  const GospelPreview = () => (
    <div className="syn-panel" style={{ height: "100%" }}>
      <div className="syn-panel-head">
        <span className="ttl" style={{ color: "var(--laser)" }}>◆ GOSPEL · KILL LIST</span>
        <span className="sub">QUEUED {GOSPEL.filter(g => g.status === "QUEUED").length} / {GOSPEL.length}</span>
      </div>
      <div className="syn-panel-body">
        <div style={{ padding: "8px 12px", borderBottom: "1px solid var(--rebar)", background: "rgba(255,51,68,0.03)" }}>
          <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: 4 }}>
            CDE policy ceiling
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <span className="num" style={{ fontSize: 18, color: "var(--rupture)", fontWeight: 700 }}>{META.cde_policy}</span>
            <span className="num" style={{ fontSize: 10, color: "var(--ash)" }}>civilians max</span>
          </div>
        </div>

        {GOSPEL.slice(0, 6).map(g => {
          const held = g.status === "CDE_HOLD" || g.status === "MONITOR";
          const decoyWarn = g.decoy > 0.2;
          return (
            <div key={g.entity}
                 onClick={onOpenGospel}
                 style={{
                   padding: "9px 12px",
                   borderBottom: "1px solid var(--rebar)",
                   display: "grid",
                   gridTemplateColumns: "20px 1fr auto",
                   gap: 10,
                   alignItems: "center",
                   cursor: "pointer",
                   opacity: held ? 0.55 : 1,
                   transition: "background 120ms",
                 }}
                 onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,51,68,0.05)"}
                 onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
            >
              <span className="q-rank" style={{ color: held ? "var(--ash)" : "var(--laser)" }}>{g.rank}</span>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                  <span className="num" style={{ fontSize: 11, color: "var(--bone)", letterSpacing: "0.08em" }}>{g.entity}</span>
                  {decoyWarn && (
                    <span className="num" title="High decoy probability"
                          style={{ fontSize: 8, color: "var(--rupture)", letterSpacing: "0.2em", border: "1px solid var(--rupture)", padding: "0 4px" }}>
                      ◆DECOY?
                    </span>
                  )}
                </div>
                <div className="num" style={{ fontSize: 9, color: held ? "var(--ash)" : "var(--laser)", letterSpacing: "0.18em", marginTop: 1 }}>
                  ◆ {g.alias} · CDE {g.cde}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="num" style={{ fontSize: 14, color: held ? "var(--ash)" : "var(--laser)", fontWeight: 700 }}>
                  {g.risk.toFixed(2)}
                </div>
                <div className="num" style={{ fontSize: 8, color: "var(--ash)", letterSpacing: "0.18em" }}>
                  {g.status}
                </div>
              </div>
            </div>
          );
        })}

        <div style={{ padding: "12px 14px", borderTop: "1px solid var(--rebar)" }}>
          <button className="btn-strike" onClick={onOpenGospel} style={{ width: "100%", justifyContent: "center" }}>
            ▸ OPEN FULL QUEUE
          </button>
          <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.18em", marginTop: 8, textAlign: "center" }}>
            THREADS {META.threads_used} / {META.threads_total} ALLOCATED
          </div>
          <div style={{ height: 4, background: "var(--rebar)", marginTop: 4 }}>
            <div style={{ width: `${(META.threads_used / META.threads_total) * 100}%`, height: "100%", background: "var(--laser)" }}></div>
          </div>
        </div>
      </div>
    </div>
  );

  // ─── Sparklines strip ──────────────────────────────────────────────────
  const Sparkline = ({ data, color, label, value, unit }) => {
    const max = Math.max(...data, 1);
    const w = 220, h = 36;
    const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / max) * h}`).join(" ");
    return (
      <div style={{ flex: 1, padding: "10px 14px", borderRight: "1px solid var(--rebar)", minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
          <span className="label">{label}</span>
          <span className="num" style={{ fontSize: 13, color, fontWeight: 700, letterSpacing: "0.04em" }}>
            {value}<span style={{ fontSize: 9, color: "var(--ash)", marginLeft: 4, letterSpacing: "0.16em" }}>{unit}</span>
          </span>
        </div>
        <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ width: "100%", height: 36 }}>
          <polyline points={points} fill="none" stroke={color} strokeWidth="1.5"/>
          <polyline points={`0,${h} ${points} ${w},${h}`} fill={color} opacity="0.12"/>
        </svg>
      </div>
    );
  };

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 8, padding: 8 }}>
      {/* TOP STATS STRIP */}
      <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
        <StatBox
          label="POPULATION OBSERVED"
          value={(META.population_observed / 1e6).toFixed(2) + "M"}
          sub="souls"
          delta={{ text: "Δ +0.4% / 30 ticks", color: "var(--solidarity)" }}
        />
        <StatBox
          label="LEGIBLE NODES"
          value={META.legible_nodes.toLocaleString()}
          sub={`${(META.coverage_pct*100).toFixed(0)}% cov.`}
          color="var(--spire)"
        />
        <StatBox
          label="FLAGGED · RISK ≥ 0.4"
          value={META.flagged}
          color="var(--heat)"
          delta={{ text: "Δ +27 / 30 ticks", color: "var(--heat)" }}
        />
        <StatBox
          label="◆ KILL LIST · RISK ≥ 0.9"
          value={META.on_kill_list}
          color="var(--laser)"
          delta={{ text: "Δ +5 / 30 ticks", color: "var(--laser)" }}
        />
        <StatBox
          label="THREADS AVAIL."
          value={META.threads_available}
          sub={`of ${META.threads_total}`}
          color="var(--bone)"
        />
        <StatBox
          label="CDE POLICY"
          value={META.cde_policy}
          sub="max civ."
          color="var(--rupture)"
        />
        <StatBox
          label="DECOY STRIKES · T-30"
          value={META.decoy_strikes_t_minus_30}
          color="var(--rupture)"
          delta={{ text: "BLOWBACK pending", color: "var(--rupture)" }}
        />
      </div>

      {/* MAIN GRID */}
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr 360px", gap: 8, flex: 1, minHeight: 0 }}>
        <Histogram />
        <Heatmap />
        <GospelPreview />
      </div>

      {/* SPARKLINE STRIP */}
      <div className="syn-panel" style={{ flexShrink: 0 }}>
        <div className="syn-panel-head">
          <span className="ttl">▸ TIME SERIES · LAST 30 TICKS</span>
          <span className="sub">RESOLUTION 1 TICK</span>
        </div>
        <div style={{ display: "flex" }}>
          <Sparkline data={TIMESERIES.flagged}  color="var(--heat)"    label="FLAGGED"        value={META.flagged}     unit="nodes" />
          <Sparkline data={TIMESERIES.on_kill}  color="var(--laser)"   label="KILL LIST"      value={META.on_kill_list} unit="targets" />
          <Sparkline data={TIMESERIES.strikes}  color="var(--bone)"    label="STRIKES EXEC."  value={TIMESERIES.strikes.reduce((s,v)=>s+v,0)} unit="t-30" />
          <Sparkline data={TIMESERIES.blowback} color="var(--rupture)" label="BLOWBACK EVT."  value={TIMESERIES.blowback.reduce((s,v)=>s+v,0)} unit="confirmed" />
        </div>
      </div>
    </div>
  );
};

window.PanopticonTab = PanopticonTab;
