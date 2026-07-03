// synopticon-gospel.jsx — The Gospel · automated strike queue
//
// Layout:
//   ┌── Controls ────────────────────────────────────┐
//   │ CDE policy slider │ Sort │ Filter │ Threads bar │
//   ├──── Queue (sorted, color-banded) ──────────────┤
//   │ rank │ entity │ alias │ risk │ CDE pip │ OPP │ status │ ENGAGE │
//   ├── Bottom: strike audit log + post-event log ───┤
//   └────────────────────────────────────────────────┘
//
// On ENGAGE click → confirm modal → resolution screen with:
//   - if decoy_probability >= 0.4: BLOWBACK animation (laser flicker, legitimacy crash)
//   - otherwise: ATTRITION (clean)
// In either case, the row stays in the queue, struck through, with the result.

const GospelTab = () => {
  const { GOSPEL, META, TERRITORIES } = window.SYN_DATA;

  const [cdePolicy, setCdePolicy] = React.useState(META.cde_policy);
  const [sortKey, setSortKey] = React.useState("risk");
  const [filterDecoy, setFilterDecoy] = React.useState(false);
  const [pendingStrike, setPendingStrike] = React.useState(null);
  const [resolution, setResolution] = React.useState(null); // {target, blowback, legit_delta, agit_delta}
  const [strikeLog, setStrikeLog] = React.useState([]);
  const [struckIds, setStruckIds] = React.useState(new Set());

  // ─── Queue derivation ──────────────────────────────────────────────────
  const computed = GOSPEL.map(g => {
    const cdeOk = g.cde <= cdePolicy;
    const struck = struckIds.has(g.entity);
    let status = g.status;
    if (struck) status = "STRUCK";
    else if (!cdeOk) status = "CDE_HOLD";
    else if (status === "MONITOR") status = "MONITOR"; // unchanged
    return { ...g, _status: status, _cdeOk: cdeOk, _struck: struck };
  });

  const sorted = [...computed].sort((a, b) => {
    if (a._struck && !b._struck) return 1;
    if (!a._struck && b._struck) return -1;
    if (sortKey === "risk") return b.risk - a.risk;
    if (sortKey === "opp")  return b.opp - a.opp;
    if (sortKey === "cde")  return a.cde - b.cde;
    return 0;
  });

  const filtered = filterDecoy ? sorted.filter(g => g.decoy < 0.2 || g._struck) : sorted;

  // ─── Strike resolution ─────────────────────────────────────────────────
  const executeStrike = (target) => {
    const isDecoy = target.decoy >= 0.3 && Math.random() < target.decoy + 0.2;
    const ts = Date.now();
    setResolution({
      target,
      blowback: isDecoy,
      legit_delta: isDecoy ? -0.30 : -0.04,
      agit_delta:  isDecoy ?  0.50 :  0.08,
      ts,
    });
    setStruckIds(s => new Set([...s, target.entity]));
    setStrikeLog(log => [{
      ts, target, blowback: isDecoy,
    }, ...log].slice(0, 12));
    setPendingStrike(null);
  };

  // ─── CDE pip indicator ─────────────────────────────────────────────────
  const CdePip = ({ cde, policy }) => {
    const pips = 12;
    return (
      <div className="cde-pip" title={`CDE ${cde} · policy ${policy}`}>
        {Array.from({ length: pips }).map((_, i) => {
          const filled = i < cde;
          const overPolicy = i >= policy && i < cde;
          return <i key={i} className={filled ? (overPolicy ? "over" : "on") : ""}></i>;
        })}
        <span className="num" style={{ fontSize: 10, color: cde > policy ? "var(--laser)" : "var(--heat)", marginLeft: 6, fontWeight: 600 }}>
          {cde}
        </span>
      </div>
    );
  };

  // ─── Queue row ─────────────────────────────────────────────────────────
  const Row = ({ g }) => {
    const held = !g._cdeOk;
    const struck = g._struck;
    const blowbackOnRecord = strikeLog.find(l => l.target.entity === g.entity)?.blowback;
    const decoyWarn = g.decoy >= 0.3;

    return (
      <div className={`q-row ${held ? "held" : ""}`}
           style={struck ? { opacity: 0.5, background: "rgba(255,51,68,0.04)" } : {}}>
        <span className="q-rank">{g.rank.toString().padStart(2, "0")}</span>

        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
            <span className="num" style={{
              fontSize: 12, color: "var(--bone)", letterSpacing: "0.08em",
              textDecoration: struck ? "line-through" : "none",
            }}>{g.entity}</span>
            {decoyWarn && !struck && (
              <span className="num" title={`Decoy probability ${g.decoy.toFixed(2)}`}
                    style={{ fontSize: 8, color: "var(--rupture)", letterSpacing: "0.2em", border: "1px solid var(--rupture)", padding: "0 4px" }}>
                ◆DECOY P{g.decoy.toFixed(2)}
              </span>
            )}
          </div>
          <div className="num" style={{ fontSize: 9, color: "var(--laser)", letterSpacing: "0.2em", marginTop: 2 }}>
            ◆ {g.alias} · {g.terr} {TERRITORIES[g.terr] && `· heat ${TERRITORIES[g.terr].heat.toFixed(2)}`}
          </div>
        </div>

        {/* risk + bar */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
            <span className="label">RISK</span>
            <span className="num" style={{ fontSize: 12, fontWeight: 700, color: g.risk >= 0.9 ? "var(--laser)" : g.risk >= 0.7 ? "var(--heat)" : "var(--cadre)" }}>
              {g.risk.toFixed(2)}
            </span>
          </div>
          <div style={{ height: 4, background: "var(--rebar)" }}>
            <div style={{
              width: `${g.risk * 100}%`, height: "100%",
              background: g.risk >= 0.9 ? "var(--laser)" : g.risk >= 0.7 ? "var(--heat)" : "var(--cadre)",
              boxShadow: g.risk >= 0.9 ? "0 0 6px rgba(255,51,68,0.5)" : "none",
            }}></div>
          </div>
        </div>

        {/* CDE pip */}
        <CdePip cde={g.cde} policy={cdePolicy} />

        {/* opportunity */}
        <div style={{ textAlign: "right" }}>
          <div className="num" style={{ fontSize: 12, color: "var(--solidarity)", fontWeight: 600 }}>{g.opp.toFixed(2)}</div>
          <div className="label">OPP</div>
        </div>

        {/* status */}
        <div>
          {struck ? (
            <span className={`badge-status ${blowbackOnRecord ? "s-BLOWBACK" : "s-ELIMINATED"}`}>
              <span className="dot"></span>{blowbackOnRecord ? "BLOWBACK" : "ATTRITION"}
            </span>
          ) : held ? (
            <span className="badge-status s-CDE_HOLD"><span className="dot"></span>CDE HOLD</span>
          ) : g._status === "MONITOR" ? (
            <span className="badge-status s-MONITOR"><span className="dot"></span>BELOW QUEUE</span>
          ) : (
            <span className="badge-status s-QUEUED">
              <span className="dot" style={{ animation: g.rank <= 3 ? "blink-laser 1.2s ease-in-out infinite" : "none" }}></span>
              QUEUED · {g.eta}
            </span>
          )}
        </div>

        {/* action button */}
        <div style={{ textAlign: "right" }}>
          {struck ? (
            <span className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.22em" }}>RESOLVED</span>
          ) : (
            <button className="btn-strike"
                    disabled={held || g._status === "MONITOR"}
                    onClick={() => setPendingStrike(g)}>
              ◆ ENGAGE
            </button>
          )}
        </div>
      </div>
    );
  };

  // ─── Confirmation modal ────────────────────────────────────────────────
  const Confirm = ({ g }) => (
    <div style={{
      position: "absolute", inset: 0, background: "rgba(6,7,11,0.85)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50,
      backdropFilter: "blur(2px)",
    }}>
      <div style={{
        background: "var(--concrete)", border: "1px solid var(--laser)",
        boxShadow: "0 0 30px rgba(255,51,68,0.35)",
        minWidth: 460, maxWidth: 520,
      }}>
        <div className="syn-cls-small" style={{ letterSpacing: "0.36em" }}>STRIKE AUTHORIZATION REQUIRED</div>
        <div style={{ padding: "22px 26px" }}>
          <div className="num" style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.26em", marginBottom: 4 }}>
            TARGET
          </div>
          <div className="num" style={{ fontSize: 22, fontWeight: 700, color: "var(--bone)", letterSpacing: "0.08em" }}>
            {g.entity}
          </div>
          <div className="num" style={{ fontSize: 11, color: "var(--laser)", letterSpacing: "0.22em", marginTop: 3 }}>
            ◆ {g.alias}
          </div>

          <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div>
              <div className="label">RISK</div>
              <div className="num" style={{ fontSize: 18, color: "var(--laser)", fontWeight: 700 }}>{g.risk.toFixed(2)}</div>
            </div>
            <div>
              <div className="label">OPPORTUNITY</div>
              <div className="num" style={{ fontSize: 18, color: "var(--solidarity)", fontWeight: 700 }}>{g.opp.toFixed(2)}</div>
            </div>
            <div>
              <div className="label">PROJ. COLLATERAL</div>
              <div className="num" style={{ fontSize: 18, color: "var(--rupture)", fontWeight: 700 }}>
                {g.cde} civ. <span style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.16em" }}>/ {cdePolicy}</span>
              </div>
            </div>
            <div>
              <div className="label">THREAD COST</div>
              <div className="num" style={{ fontSize: 18, color: "var(--bone)", fontWeight: 700 }}>{g.threads}</div>
            </div>
          </div>

          {g.decoy >= 0.3 && (
            <div className="doc-note" style={{ marginTop: 18 }}>
              <span className="num" style={{ color: "var(--rupture)", letterSpacing: "0.2em" }}>◆ ADVISORY · </span>
              Honeypot signature detected. Decoy probability <strong style={{ color: "var(--rupture)" }}>{g.decoy.toFixed(2)}</strong>.
              The Gospel does not block on this signal. Engagement may produce BLOWBACK.
            </div>
          )}

          <div style={{ marginTop: 22, display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn-ghost" onClick={() => setPendingStrike(null)}>CANCEL</button>
            <button className="btn-strike" onClick={() => executeStrike(g)}>◆ AUTHORIZE STRIKE</button>
          </div>
        </div>
      </div>
    </div>
  );

  // ─── Resolution overlay (Engage + Assess) ──────────────────────────────
  const Resolution = ({ r }) => {
    const isBlowback = r.blowback;
    React.useEffect(() => {
      const t = setTimeout(() => setResolution(null), isBlowback ? 4200 : 2400);
      return () => clearTimeout(t);
    }, []);

    return (
      <div className={`flick-red`} style={{
        position: "absolute", inset: 0, zIndex: 60,
        background: isBlowback ? "rgba(255,51,68,0.10)" : "rgba(6,7,11,0.6)",
        display: "flex", alignItems: "center", justifyContent: "center",
        pointerEvents: "none",
      }}>
        {isBlowback && <div className="scan-line"></div>}
        <div style={{
          minWidth: 540, maxWidth: 640,
          background: "var(--void)",
          border: `2px solid ${isBlowback ? "var(--rupture)" : "var(--laser)"}`,
          boxShadow: isBlowback ? "0 0 40px rgba(212,160,44,0.4)" : "0 0 20px rgba(255,51,68,0.3)",
        }}>
          <div className="syn-cls-small" style={{ background: isBlowback ? "var(--rupture)" : "var(--laser)", color: "var(--void)" }}>
            {isBlowback ? "◆ BLOWBACK EVENT · ASSESS PHASE ◆" : "◆ ATTRITION EVENT · ASSESS PHASE ◆"}
          </div>

          <div style={{ padding: "24px 30px" }}>
            <div className="num blink-laser" style={{ fontSize: 11, color: isBlowback ? "var(--rupture)" : "var(--laser)", letterSpacing: "0.32em", marginBottom: 6 }}>
              ▸ STRIKE EXECUTED · T-{META.tick}
            </div>
            <div className="num" style={{ fontSize: 26, fontWeight: 700, color: "var(--bone)", letterSpacing: "0.08em" }}>
              {r.target.entity}
            </div>
            <div className="num" style={{ fontSize: 12, color: isBlowback ? "var(--rupture)" : "var(--laser)", letterSpacing: "0.24em", marginTop: 4 }}>
              ◆ {r.target.alias}
            </div>

            {isBlowback ? (
              <div style={{ marginTop: 18 }}>
                <div className="num" style={{ fontSize: 13, color: "var(--rupture)", fontWeight: 700, letterSpacing: "0.16em", marginBottom: 10 }}>
                  TARGET WAS DECOY · STATE LEGIBLE PROJECTION COMPROMISED
                </div>
                <div className="doc-body" style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, lineHeight: 1.6, color: "var(--bone)" }}>
                  Post-strike forensics indicate the targeted node was a fabricated network artifact —
                  high centrality, high velocity, zero revolutionary value. The strike has been
                  attributed to the state by all observable channels.
                </div>
                <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div style={{ border: "1px solid var(--rupture)", padding: "10px 12px", background: "rgba(212,160,44,0.05)" }}>
                    <div className="label">LEGITIMACY</div>
                    <div className="num" style={{ fontSize: 18, fontWeight: 700, color: "var(--rupture)" }}>
                      {r.legit_delta.toFixed(2)}
                    </div>
                  </div>
                  <div style={{ border: "1px solid var(--rupture)", padding: "10px 12px", background: "rgba(212,160,44,0.05)" }}>
                    <div className="label">AGITATION</div>
                    <div className="num" style={{ fontSize: 18, fontWeight: 700, color: "var(--rupture)" }}>
                      +{r.agit_delta.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="num" style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.18em", marginTop: 14, lineHeight: 1.6, fontStyle: "italic" }}>
                  ASSESS_MODULE will attribute the rise in agitation to insurgent activity, not to this strike.<br/>
                  The Lavender score of nearby nodes will rise as a result. The system will recommend more strikes.
                </div>
              </div>
            ) : (
              <div style={{ marginTop: 18 }}>
                <div className="num" style={{ fontSize: 13, color: "var(--laser)", fontWeight: 700, letterSpacing: "0.16em", marginBottom: 10 }}>
                  TARGET ELIMINATED · CADRE ATTRITION CONFIRMED
                </div>
                <div className="doc-body" style={{ fontFamily: "var(--font-mono)", fontSize: 11.5, lineHeight: 1.6, color: "var(--bone)" }}>
                  Topology updated. Adjacent neighbor-risk averages will be recomputed at next tick.
                  Local cluster centrality redistributed.
                </div>
                <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                  <div style={{ border: "1px solid var(--laser)", padding: "10px 12px" }}>
                    <div className="label">COLLATERAL</div>
                    <div className="num" style={{ fontSize: 18, fontWeight: 700, color: "var(--rupture)" }}>{r.target.cde} civ.</div>
                  </div>
                  <div style={{ border: "1px solid var(--laser)", padding: "10px 12px" }}>
                    <div className="label">LEGITIMACY</div>
                    <div className="num" style={{ fontSize: 18, fontWeight: 700, color: "var(--cadre)" }}>{r.legit_delta.toFixed(2)}</div>
                  </div>
                  <div style={{ border: "1px solid var(--laser)", padding: "10px 12px" }}>
                    <div className="label">AGITATION</div>
                    <div className="num" style={{ fontSize: 18, fontWeight: 700, color: "var(--heat)" }}>+{r.agit_delta.toFixed(2)}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ─── Render ────────────────────────────────────────────────────────────
  const queuedCount  = computed.filter(g => g._status === "QUEUED" && !g._struck).length;
  const heldCount    = computed.filter(g => !g._cdeOk && !g._struck).length;
  const struckCount  = computed.filter(g => g._struck).length;
  const blowbackCount = strikeLog.filter(l => l.blowback).length;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", position: "relative" }}>

      {/* Controls strip */}
      <div style={{
        flexShrink: 0,
        background: "rgba(255,51,68,0.03)",
        borderBottom: "1px solid var(--rebar)",
        padding: "12px 18px",
        display: "grid",
        gridTemplateColumns: "1.4fr 1fr 1fr 1fr",
        gap: 24, alignItems: "center",
      }}>
        {/* CDE policy slider — the only humane lever */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span className="label">▸ CDE POLICY CEILING</span>
            <span className="num" style={{ fontSize: 14, color: "var(--rupture)", fontWeight: 700, letterSpacing: "0.06em" }}>
              ≤ {cdePolicy} <span style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.18em" }}>civilians</span>
            </span>
          </div>
          <input type="range" min="0" max="40" value={cdePolicy}
                 onChange={e => setCdePolicy(+e.target.value)}
                 style={{ width: "100%", accentColor: "var(--rupture)" }}/>
          <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.16em", marginTop: 4, fontStyle: "italic" }}>
            Filters queue items where projected collateral exceeds policy. The Gospel does not skip — it holds.
          </div>
        </div>

        {/* Sort */}
        <div>
          <div className="label" style={{ marginBottom: 6 }}>▸ SORT</div>
          <div style={{ display: "flex", gap: 4 }}>
            {[["risk", "RISK ↓"], ["opp", "OPP ↓"], ["cde", "CDE ↑"]].map(([k, lbl]) => (
              <button key={k} className={`btn-ghost ${sortKey === k ? "active" : ""}`}
                      onClick={() => setSortKey(k)}>
                {lbl}
              </button>
            ))}
          </div>
        </div>

        {/* Filter */}
        <div>
          <div className="label" style={{ marginBottom: 6 }}>▸ FILTERS</div>
          <button className={`btn-ghost ${filterDecoy ? "active" : ""}`}
                  onClick={() => setFilterDecoy(!filterDecoy)}>
            {filterDecoy ? "HIDING DECOYS" : "SHOW ALL"}
          </button>
        </div>

        {/* Threads gauge */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span className="label">▸ THREADS BUDGET</span>
            <span className="num" style={{ fontSize: 12, color: "var(--bone)", fontWeight: 700 }}>
              {META.threads_used} / {META.threads_total}
            </span>
          </div>
          <div style={{ height: 8, background: "var(--rebar)", border: "1px solid var(--rebar)" }}>
            <div style={{
              width: `${(META.threads_used / META.threads_total) * 100}%`, height: "100%",
              background: "linear-gradient(90deg, var(--cadre), var(--laser))",
            }}></div>
          </div>
          <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.16em", marginTop: 4 }}>
            REMAINING {META.threads_available} · ENOUGH FOR {Math.floor(META.threads_available / 14)} ENGAGEMENTS
          </div>
        </div>
      </div>

      {/* Summary row */}
      <div style={{
        flexShrink: 0,
        display: "flex", gap: 28,
        padding: "10px 18px",
        borderBottom: "1px solid var(--rebar)",
        background: "var(--tar)",
      }}>
        <div>
          <span className="num" style={{ fontSize: 20, color: "var(--laser)", fontWeight: 700, letterSpacing: "0.04em" }}>{queuedCount}</span>
          <span className="label" style={{ marginLeft: 8 }}>QUEUED</span>
        </div>
        <div>
          <span className="num" style={{ fontSize: 20, color: "var(--rupture)", fontWeight: 700 }}>{heldCount}</span>
          <span className="label" style={{ marginLeft: 8 }}>CDE HOLD</span>
        </div>
        <div>
          <span className="num" style={{ fontSize: 20, color: "var(--ash)", fontWeight: 700 }}>{struckCount}</span>
          <span className="label" style={{ marginLeft: 8 }}>RESOLVED THIS SESSION</span>
        </div>
        <div>
          <span className="num" style={{ fontSize: 20, color: "var(--rupture)", fontWeight: 700, textShadow: blowbackCount ? "0 0 8px rgba(212,160,44,0.5)" : "none" }}>{blowbackCount}</span>
          <span className="label" style={{ marginLeft: 8 }}>BLOWBACK</span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <span className="num blink-laser" style={{ fontSize: 9, color: "var(--laser)", letterSpacing: "0.28em", fontWeight: 700 }}>
            ◆ ACTIVE FEED · T-{META.tick}
          </span>
        </div>
      </div>

      {/* Column headers */}
      <div className="q-row" style={{
        background: "rgba(0,0,0,0.3)",
        borderBottom: "1px solid var(--wet-steel)",
        cursor: "default",
        padding: "6px 14px",
      }}>
        <span className="label">RANK</span>
        <span className="label">ENTITY · ALIAS · TERRITORY</span>
        <span className="label" style={{ textAlign: "right" }}>RISK</span>
        <span className="label">CDE</span>
        <span className="label" style={{ textAlign: "right" }}>OPP</span>
        <span className="label">STATUS</span>
        <span className="label" style={{ textAlign: "right" }}>ACTION</span>
      </div>

      {/* Queue body */}
      <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
        {filtered.map(g => <Row key={g.entity} g={g} />)}
        <div style={{ padding: 20, fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--shroud)", letterSpacing: "0.24em", textAlign: "center" }}>
          ─ END OF QUEUE · {filtered.length} ENTRIES ─
        </div>
      </div>

      {/* Bottom strike audit log */}
      <div style={{
        flexShrink: 0,
        borderTop: "1px solid var(--rebar)",
        background: "var(--tar)",
        maxHeight: 140,
        overflow: "hidden",
        display: "flex", flexDirection: "column",
      }}>
        <div style={{ padding: "6px 18px", borderBottom: "1px solid var(--rebar)", display: "flex", justifyContent: "space-between" }}>
          <span className="label">▸ STRIKE LOG · SESSION</span>
          <span className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.18em" }}>{strikeLog.length} EVENTS</span>
        </div>
        <div style={{ overflowY: "auto", flex: 1, padding: "4px 0" }}>
          {strikeLog.length === 0 ? (
            <div style={{ padding: "12px 18px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: "0.2em" }}>
              NO STRIKES THIS SESSION · QUEUE IDLE
            </div>
          ) : strikeLog.map((l, i) => (
            <div key={i} style={{
              padding: "5px 18px",
              borderBottom: "1px dotted var(--rebar)",
              display: "grid", gridTemplateColumns: "80px 60px 1fr auto",
              gap: 12, alignItems: "baseline",
              fontFamily: "var(--font-mono)", fontSize: 11,
            }}>
              <span className="num" style={{ color: "var(--ash)", letterSpacing: "0.14em" }}>
                T-{META.tick}.{strikeLog.length - i}
              </span>
              <span className={`num ${l.blowback ? "" : ""}`} style={{ color: l.blowback ? "var(--rupture)" : "var(--laser)", fontWeight: 700, letterSpacing: "0.18em" }}>
                {l.blowback ? "BLOWBACK" : "ATTRITION"}
              </span>
              <span style={{ color: "var(--bone)" }}>
                <span className="num">{l.target.entity}</span>
                <span className="num" style={{ color: "var(--ash)", marginLeft: 8, letterSpacing: "0.16em" }}>◆ {l.target.alias}</span>
              </span>
              <span className="num" style={{ color: l.blowback ? "var(--rupture)" : "var(--ash)", fontSize: 10, letterSpacing: "0.14em" }}>
                {l.blowback ? `LEGIT -0.30 · AGIT +0.50` : `LEGIT -0.04 · AGIT +0.08`}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Overlays */}
      {pendingStrike && <Confirm g={pendingStrike} />}
      {resolution && <Resolution r={resolution} />}
    </div>
  );
};

window.GospelTab = GospelTab;
