// synopticon-dossiers.jsx — Digital Dossier browser
//
// Left: filterable list of all 18 dossiers (rank, entity-id, alias, risk, status)
// Right: full case file
//   - Top: ID block + alias + status + classification stamp
//   - Risk anatomy: 4 contribution bars + threshold ladder
//   - Pattern of Life: 3-axis radar (movement / spending / communication)
//   - POL Log: timestamped surveillance events
//   - Collateral / territory / neighbors / strike recommendation

const DossiersTab = ({ selectedId, setSelectedId }) => {
  const { DOSSIERS, THRESHOLDS, TERRITORIES, META } = window.SYN_DATA;
  const [filter, setFilter] = React.useState("ALL");
  const [sort, setSort] = React.useState("risk");

  const filtered = DOSSIERS
    .filter(d => filter === "ALL" ? true : d.status === filter)
    .sort((a, b) => {
      if (sort === "risk") return b.risk_score - a.risk_score;
      if (sort === "age") return b.dossier_age - a.dossier_age;
      if (sort === "cde") return a.collateral_estimate - b.collateral_estimate;
      return 0;
    });

  const active = DOSSIERS.find(d => d.id === selectedId) || filtered[0];

  // ─── List row ──────────────────────────────────────────────────────────
  const ListRow = ({ d }) => {
    const isActive = d.id === active?.id;
    const riskColor = d.risk_score >= 0.9 ? "var(--laser)"
                    : d.risk_score >= 0.7 ? "var(--heat)"
                    : d.risk_score >= 0.4 ? "var(--cadre)"
                    : "var(--ash)";
    return (
      <div className={`dl-row ${isActive ? "active" : ""}`}
           onClick={() => setSelectedId(d.id)}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 2 }}>
            <span className="num" style={{ fontSize: 11, color: "var(--bone)", letterSpacing: "0.08em" }}>{d.id}</span>
            {d.decoy_probability > 0.2 && (
              <span title="High decoy probability" className="num"
                    style={{ fontSize: 8, color: "var(--rupture)", letterSpacing: "0.18em" }}>◆DECOY?</span>
            )}
          </div>
          <div className="num" style={{ fontSize: 9, color: "var(--laser)", letterSpacing: "0.2em", marginBottom: 4 }}>
            {d.alias}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span className={`badge-status s-${d.status}`} style={{ fontSize: 8 }}>{d.status}</span>
            <span className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.14em" }}>{d.territory.split("·")[0].trim()}</span>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="num" style={{ fontSize: 18, fontWeight: 700, color: riskColor, lineHeight: 1, letterSpacing: "0.02em" }}>
            {d.risk_score.toFixed(2)}
          </div>
          <div className="num" style={{ fontSize: 8, color: "var(--ash)", letterSpacing: "0.18em", marginTop: 2 }}>
            RISK
          </div>
        </div>
      </div>
    );
  };

  // ─── Dossier card (right side) ─────────────────────────────────────────
  const DossierCard = ({ d }) => {
    if (!d) return <div style={{ padding: 30, color: "var(--ash)", fontFamily: "var(--font-mono)" }}>NO DOSSIER SELECTED</div>;

    const terr = TERRITORIES[d.territory.split("·")[0].trim()] || { heat: 0, defense: 0 };
    const riskColor = d.risk_score >= 0.9 ? "var(--laser)"
                    : d.risk_score >= 0.7 ? "var(--heat)"
                    : d.risk_score >= 0.4 ? "var(--cadre)"
                    : "var(--ash)";

    // Recommendation logic
    let recom, recomColor;
    if (d.status === "ELIMINATED") { recom = "TARGET CLOSED · ARCHIVED"; recomColor = "var(--shroud)"; }
    else if (d.risk_score >= THRESHOLDS.eliminate) { recom = "ENGAGE — promote to Gospel queue"; recomColor = "var(--laser)"; }
    else if (d.risk_score >= THRESHOLDS.suppress)  { recom = "SUPPRESS — restrict movement, sever edges"; recomColor = "var(--heat)"; }
    else if (d.risk_score >= THRESHOLDS.monitor)   { recom = "MONITOR — increase observation cadence"; recomColor = "var(--cadre)"; }
    else { recom = "PASSIVE — within tolerance"; recomColor = "var(--ash)"; }

    return (
      <div className="dossier-card" style={{ flex: 1 }}>
        {/* Top classification strip */}
        <div className="syn-cls-small">TOP SECRET // SAP-LAVENDER // DOSSIER · DO NOT EXPORT</div>

        {/* Header — id block, alias, status, stamp */}
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--rebar)", display: "flex", gap: 22 }}>
          <div className="id-block">
            {d.id.split("-")[1].slice(0, 2)}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.28em", marginBottom: 6 }}>
              ENTITY DOSSIER · {d.id}
            </div>
            <div className="dossier-id">{d.id}</div>
            <div className="dossier-alias">◆ {d.alias}</div>
            <div style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "center" }}>
              <span className={`badge-status s-${d.status}`}>
                <span className="dot"></span>{d.status}
              </span>
              {d.decoy_probability > 0.2 && (
                <span className="badge-status" style={{ color: "var(--rupture)", borderColor: "var(--rupture)" }}>
                  ◆ DECOY P={d.decoy_probability.toFixed(2)}
                </span>
              )}
              <span className="num" style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.18em" }}>
                FIRST {d.first_seen} · LAST {d.last_observed} · AGE {d.dossier_age}t
              </span>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
            <div className="doc-stamp">
              {d.status === "TARGET" ? "FOR ENGAGE" :
               d.status === "SUSPECT" ? "FOR REVIEW" :
               d.status === "ELIMINATED" ? "CLOSED" : "MONITOR"}
            </div>
            <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.22em", textAlign: "right" }}>
              CASE · T{META.tick}-{d.id.split("-")[1]}
            </div>
          </div>
        </div>

        {/* Body — scrollable */}
        <div style={{ flex: 1, minHeight: 0, overflow: "auto" }}>

          {/* ── Risk anatomy ── */}
          <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--rebar)" }}>
            <div className="label" style={{ marginBottom: 10 }}>▸ Risk anatomy · Lavender-V1</div>

            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: "8px 14px", alignItems: "center" }}>
              {/* Total */}
              <span className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.2em" }}>TOTAL</span>
              <div style={{ position: "relative", height: 22, background: "var(--rebar)", borderRadius: 2, overflow: "hidden" }}>
                {/* threshold markers behind the bar */}
                {[THRESHOLDS.monitor, THRESHOLDS.suppress, THRESHOLDS.eliminate].map((t, i) => (
                  <div key={i} style={{
                    position: "absolute", left: `${t * 100}%`, top: 0, bottom: 0,
                    width: 1, background: i === 2 ? "var(--laser)" : i === 1 ? "var(--heat)" : "var(--ash)",
                    opacity: 0.6,
                  }}></div>
                ))}
                {/* stacked segments */}
                <div className="risk-stack" style={{ position: "absolute", inset: 0, height: 22, border: "none", background: "transparent" }}>
                  {["centrality","association","velocity","geo"].map((k) => (
                    <div key={k} className={`risk-seg ${k}`} style={{ width: `${d.contributions[k] * 100}%` }}></div>
                  ))}
                </div>
              </div>
              <span className="num" style={{ fontSize: 24, fontWeight: 700, color: riskColor, letterSpacing: "0.02em", lineHeight: 1, textShadow: d.risk_score >= 0.9 ? "0 0 10px rgba(255,51,68,0.5)" : "none" }}>
                {d.risk_score.toFixed(2)}
              </span>
            </div>

            {/* Threshold legend below */}
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: "0.18em", paddingLeft: 56, paddingRight: 60 }}>
              <span>0.00</span>
              <span style={{ color: "var(--cadre)" }}>MON 0.40</span>
              <span style={{ color: "var(--heat)" }}>SUP 0.70</span>
              <span style={{ color: "var(--laser)" }}>KILL 0.90</span>
              <span>1.00</span>
            </div>

            {/* 4 features ledger */}
            <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8 }}>
              {[
                ["centrality",  "BETWEENNESS",    "courier / bridge",   "var(--cadre)",  0.40],
                ["association", "NEIGHBOR-RISK",  "guilt by topology",  "var(--rent)",   0.20],
                ["velocity",    "SPEND VS INCOME", "illicit funding",   "var(--heat)",   0.30],
                ["geo",         "HEAT-ZONE DWELL", "wrong territory",   "var(--laser)",  0.20],
              ].map(([k, lbl, desc, c, cap]) => {
                const v = d.contributions[k];
                return (
                  <div key={k} style={{ background: "var(--tar)", border: "1px solid var(--rebar)", padding: "10px 12px", borderTop: `2px solid ${c}` }}>
                    <div className="num" style={{ fontSize: 8.5, color: "var(--ash)", letterSpacing: "0.22em", marginBottom: 2 }}>{lbl}</div>
                    <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 6 }}>
                      <span className="num" style={{ fontSize: 20, fontWeight: 700, color: c }}>
                        +{v.toFixed(2)}
                      </span>
                      <span className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.12em" }}>
                        / {cap.toFixed(2)}
                      </span>
                    </div>
                    <div style={{ height: 3, background: "var(--rebar)" }}>
                      <div style={{ width: `${(v / cap) * 100}%`, height: "100%", background: c }}></div>
                    </div>
                    <div className="num" style={{ fontSize: 9, color: "var(--fog)", letterSpacing: "0.06em", marginTop: 6, fontStyle: "italic" }}>
                      {desc}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── Pattern of life + territory ── */}
          <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--rebar)", display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: 18 }}>
            {/* POL Radar */}
            <div>
              <div className="label" style={{ marginBottom: 10 }}>▸ Pattern of life · POL vector</div>
              <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                <PolRadar v={d.pol_vector} />
                <div style={{ flex: 1, fontFamily: "var(--font-mono)", fontSize: 10 }}>
                  {Object.entries(d.pol_vector).map(([k, v]) => (
                    <div key={k} style={{ display: "grid", gridTemplateColumns: "100px 1fr 40px", gap: 8, alignItems: "center", padding: "3px 0" }}>
                      <span className="label" style={{ textAlign: "left" }}>{k}</span>
                      <div style={{ height: 4, background: "var(--rebar)" }}>
                        <div style={{ width: `${v * 100}%`, height: "100%", background: "var(--spire)" }}></div>
                      </div>
                      <span className="num" style={{ color: "var(--spire)", fontWeight: 600, textAlign: "right", fontSize: 11 }}>{v.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Territory card */}
            <div>
              <div className="label" style={{ marginBottom: 10 }}>▸ Territory</div>
              <div className="num" style={{ fontSize: 13, color: "var(--bone)", letterSpacing: "0.08em", fontWeight: 700 }}>
                {d.territory}
              </div>
              <div style={{ marginTop: 10, fontFamily: "var(--font-mono)", fontSize: 10 }}>
                {[
                  ["INSURGENCY INDEX", terr.heat,    "var(--laser)"],
                  ["STATE DEFENSE",     terr.defense, "var(--cadre)"],
                  ["CONTROL",            terr.control, "var(--solidarity)"],
                ].map(([lbl, v, c]) => (
                  <div key={lbl} style={{ display: "grid", gridTemplateColumns: "100px 1fr 40px", gap: 8, alignItems: "center", padding: "3px 0" }}>
                    <span className="label" style={{ textAlign: "left" }}>{lbl}</span>
                    <div style={{ height: 4, background: "var(--rebar)" }}>
                      <div style={{ width: `${(v || 0) * 100}%`, height: "100%", background: c }}></div>
                    </div>
                    <span className="num" style={{ color: c, fontWeight: 600, textAlign: "right", fontSize: 11 }}>{(v||0).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Operational params */}
            <div>
              <div className="label" style={{ marginBottom: 10 }}>▸ Operational</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>
                <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 12px" }}>
                  <span className="label">NEIGHBORS</span>
                  <span style={{ color: "var(--bone)" }} className="num">{d.neighbors}</span>
                  <span className="label">COLL. EST.</span>
                  <span className="num" style={{ color: d.collateral_estimate > META.cde_policy ? "var(--laser)" : "var(--rupture)", fontWeight: 700 }}>
                    {d.collateral_estimate} {d.collateral_estimate > META.cde_policy && <span style={{ fontSize: 9, color: "var(--laser)", marginLeft: 6, letterSpacing: "0.18em" }}>◆ EXCEEDS POLICY</span>}
                  </span>
                  <span className="label">DOSSIER AGE</span>
                  <span className="num" style={{ color: "var(--bone)" }}>{d.dossier_age} ticks</span>
                  <span className="label">DECOY P.</span>
                  <span className="num" style={{ color: d.decoy_probability > 0.2 ? "var(--rupture)" : "var(--ash)" }}>
                    {d.decoy_probability.toFixed(2)}
                    {d.decoy_probability > 0.2 && " ◆ELEVATED"}
                  </span>
                </div>

                {/* Recommendation */}
                <div style={{
                  marginTop: 14, padding: "10px 12px",
                  background: "var(--tar)", border: `1px solid ${recomColor}`,
                  borderLeft: `3px solid ${recomColor}`,
                }}>
                  <div className="num" style={{ fontSize: 8.5, color: "var(--ash)", letterSpacing: "0.24em", marginBottom: 4 }}>▸ GOSPEL RECOMMENDATION</div>
                  <div className="num" style={{ fontSize: 11, color: recomColor, fontWeight: 700, letterSpacing: "0.08em" }}>
                    {recom}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── POL Log ── */}
          <div style={{ padding: "18px 24px" }}>
            <div className="label" style={{ marginBottom: 10 }}>▸ Pattern-of-life log · last {d.history.length} events</div>
            <div style={{ border: "1px solid var(--rebar)", background: "var(--tar)" }}>
              {d.history.length === 0 ? (
                <div style={{ padding: 14, fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ash)", letterSpacing: "0.14em" }}>
                  NO EVENTS · BELOW MONITOR THRESHOLD
                </div>
              ) : d.history.map((h, i) => (
                <div key={i} className="pol-row">
                  <span className="tt num">T-{h.t}</span>
                  <span className={`ss num ${h.sev}`}>◆{h.sev}</span>
                  <span className="tg">{h.tag}</span>
                  <span className="nt">{h.note}</span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Footer · provenance ── */}
          <div style={{ padding: "14px 24px", borderTop: "1px solid var(--rebar)", background: "rgba(255,51,68,0.03)" }}>
            <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.18em", lineHeight: 1.7 }}>
              ▸ PROVENANCE · LegibleGraph snapshot T-{META.tick} · LAVENDER-V1 weights · scan time 0.13s<br/>
              ▸ This dossier is generated. Underlying observations are derived. Confidence is not provenance.
            </div>
          </div>
        </div>
      </div>
    );
  };

  // ─── POL Radar SVG ─────────────────────────────────────────────────────
  const PolRadar = ({ v }) => {
    const cx = 70, cy = 70, R = 50;
    const axes = ["movement", "spending", "communication"];
    const angle = (i) => -Math.PI / 2 + (i / 3) * 2 * Math.PI;
    const pt = (i, val) => [cx + Math.cos(angle(i)) * R * val, cy + Math.sin(angle(i)) * R * val];
    const polygon = axes.map((k, i) => pt(i, v[k]).join(",")).join(" ");

    return (
      <svg viewBox="0 0 140 140" width="140" height="140">
        {[0.25, 0.5, 0.75, 1].map(s => (
          <polygon key={s}
                   points={axes.map((_, i) => pt(i, s).join(",")).join(" ")}
                   fill="none" stroke="var(--rebar)" strokeWidth="0.5"/>
        ))}
        {axes.map((k, i) => {
          const [x, y] = pt(i, 1.18);
          return (
            <g key={k}>
              <line x1={cx} y1={cy} x2={pt(i,1)[0]} y2={pt(i,1)[1]} stroke="var(--rebar)" strokeWidth="0.5"/>
              <text x={x} y={y} textAnchor="middle" dominantBaseline="middle"
                    style={{ fontFamily: "var(--font-mono)", fontSize: 7.5, fill: "var(--ash)", letterSpacing: "0.16em" }}>
                {k.slice(0, 3).toUpperCase()}
              </text>
            </g>
          );
        })}
        <polygon points={polygon} fill="rgba(77,217,230,0.18)" stroke="var(--spire)" strokeWidth="1"/>
        {axes.map((k, i) => {
          const [x, y] = pt(i, v[k]);
          return <circle key={k} cx={x} cy={y} r="2.5" fill="var(--spire)"/>;
        })}
      </svg>
    );
  };

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <div style={{ height: "100%", display: "flex" }}>
      {/* LEFT — list */}
      <div style={{ width: 320, borderRight: "1px solid var(--rebar)", display: "flex", flexDirection: "column", flexShrink: 0 }}>
        <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--rebar)", background: "rgba(255,51,68,0.03)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
            <span className="ttl" style={{ fontSize: 10, color: "var(--bone)", letterSpacing: "0.26em", fontFamily: "var(--font-mono)", fontWeight: 700 }}>▸ DIGITAL DOSSIERS</span>
            <span className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.18em" }}>{filtered.length}/{DOSSIERS.length}</span>
          </div>

          {/* Filter pills */}
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 8 }}>
            {["ALL", "TARGET", "SUSPECT", "UNKNOWN", "ELIMINATED"].map(f => (
              <button key={f}
                      className={`btn-ghost ${filter === f ? "active" : ""}`}
                      onClick={() => setFilter(f)}
                      style={{ fontSize: 9, padding: "3px 7px", letterSpacing: "0.16em" }}>
                {f}
              </button>
            ))}
          </div>

          {/* Sort */}
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="label">SORT</span>
            <select value={sort} onChange={e => setSort(e.target.value)}
                    style={{
                      background: "var(--void)", border: "1px solid var(--wet-steel)",
                      color: "var(--bone)", fontFamily: "var(--font-mono)", fontSize: 10,
                      padding: "3px 6px", letterSpacing: "0.14em",
                    }}>
              <option value="risk">RISK ↓</option>
              <option value="age">AGE ↓</option>
              <option value="cde">CDE ↑</option>
            </select>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto" }}>
          {filtered.map(d => <ListRow key={d.id} d={d} />)}
        </div>
      </div>

      {/* RIGHT — dossier card */}
      <div style={{ flex: 1, padding: 10, display: "flex", minWidth: 0 }}>
        <DossierCard d={active} />
      </div>
    </div>
  );
};

window.DossiersTab = DossiersTab;
