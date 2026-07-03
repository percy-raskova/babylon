// wire-corporate.jsx — CONTINENTAL · Corporate Feed column
// Sterile sans, generous tracking, passive voice, sources-first, numbered superscript citations,
// footer bibliography. Euphemism flags are subtle (dotted underline); they go red when hovered
// and broadcast their `data-euph` id to the Liberated column to sync-glow the honest equivalent.

const ContinentalColumn = ({ activeEuph, setActiveEuph, activeSup, setActiveSup, euphAlways, citationDensity, focused }) => {
  const story = window.WIRE_DATA.story;
  const c = story.continental;

  const renderRun = (run, idx, isFirstPara) => {
    if (typeof run === "string") return run;
    if (run.sup != null) {
      const showSup = citationDensity !== "off";
      if (!showSup) return null;
      return (
        <sup
          key={"sup" + idx}
          className={"sup" + (activeSup === run.sup ? " active" : "")}
          onClick={() => setActiveSup(activeSup === run.sup ? null : run.sup)}
        >{run.sup}</sup>
      );
    }
    if (run.euph) {
      return (
        <span
          key={"e" + idx}
          className={"euph" + (activeEuph === run.euph ? " active" : "")}
          data-euph={run.euph}
          onMouseEnter={() => setActiveEuph(run.euph)}
          onMouseLeave={() => !euphAlways && setActiveEuph(null)}
          onClick={() => setActiveEuph(activeEuph === run.euph ? null : run.euph)}
        >{run.text}</span>
      );
    }
    return null;
  };

  return (
    <div className="col-wrap col-continental">
      <div className="col-head">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="pill" style={{ color: "var(--cadre)", borderColor: "rgba(107,143,181,0.35)" }}>
            <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--cadre)" }}></span>
            CHANNEL · CORPORATE
          </span>
          <span className="kicker" style={{ color: "var(--ash)" }}>HEGEMONIC FRAME</span>
        </div>
        <span className="kicker" style={{ color: "var(--ash)" }}>{c.kicker}</span>
      </div>

      <div className="col-body">
        {/* Masthead */}
        <div className="masthead" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="monogram">{c.monogram}</div>
            <div>
              <div className="nameplate">CONTINENTAL</div>
              <div className="est">Est. 1851 · Trusted Since · {window.WIRE_DATA.meta.timestamp_utc.slice(0,10)}</div>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 2 }}>
            <span className="label" style={{ color: "var(--fog)" }}>Vol. CLXXIV · No. 24,883</span>
            <span className="label" style={{ color: "var(--ash)" }}>Edition Final · 5h ago</span>
          </div>
        </div>

        {/* Top strip (markets, weather) — chrome that establishes 'normal newspaper' */}
        <div className="chrome-strip">
          {[
            ["DJIA",   "41,824.30", "+0.24%", "var(--solidarity)"],
            ["S&P",    "5,712.18",  "+0.11%", "var(--solidarity)"],
            ["DXY",    "104.92",    "−0.08%", "var(--heat)"],
            ["WTI",    "$72.14",    "+1.20%", "var(--solidarity)"],
            ["DET",    "62°F · CLR", "",       "var(--fog)"],
          ].map(([k,v,d,col]) => (
            <div key={k} style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".2em", color: "var(--ash)" }}>{k}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--bone)" }}>{v}</span>
              {d && <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: col }}>{d}</span>}
            </div>
          ))}
        </div>

        {/* Story body */}
        <div style={{ padding: "22px 28px 8px", maxWidth: focused ? 720 : "none", margin: focused ? "0 auto" : "0" }}>
          <div className="kicker" style={{ color: "var(--cadre)", marginBottom: 10 }}>
            {c.kicker}
          </div>
          <h1 className="hed" style={{ margin: "0 0 12px" }}>{c.hed}</h1>
          <p className="dek" style={{ margin: "0 0 14px" }}>{c.dek}</p>
          <div className="byline" style={{ marginBottom: 22, paddingBottom: 12, borderBottom: "1px solid var(--rebar)" }}>
            {c.byline}
          </div>

          {c.paragraphs.map((para, pi) => (
            <p key={pi} className={pi === 0 ? "firstpara" : ""}>
              {para.map((run, ri) => renderRun(run, pi + "-" + ri, pi === 0))}
            </p>
          ))}

          <div style={{ marginTop: 14, padding: "10px 14px", background: "rgba(255,255,255,0.02)", border: "1px solid var(--rebar)", borderRadius: 4 }}>
            <div className="label" style={{ marginBottom: 4 }}>Editor&rsquo;s note</div>
            <div style={{ fontSize: 12, color: "var(--fog)", lineHeight: 1.55 }}>
              Continental adheres to strict sourcing standards. Names of detainees are withheld pending family notification. This story will be updated as the situation develops.
            </div>
          </div>
        </div>

        {/* Bibliography */}
        {citationDensity !== "off" && (
          <div className="note-drawer">
            <div className="label" style={{ marginBottom: 8 }}>References · Retrieved from corpus</div>
            {c.bibliography.map(b => (
              <div
                key={b.n}
                style={{
                  display: "flex", gap: 8, padding: "4px 0",
                  alignItems: "baseline",
                  background: activeSup === b.n ? "rgba(77,217,230,0.05)" : "transparent",
                  borderLeft: activeSup === b.n ? "2px solid var(--spire)" : "2px solid transparent",
                  paddingLeft: 6,
                  transition: "background 120ms, border-left-color 120ms",
                }}
              >
                <span className="n">{b.n}.</span>
                <span style={{ flex: 1 }}>
                  <span style={{ color: "var(--bone)" }}>{b.src}</span>
                  <span style={{ color: "var(--ash)" }}> · {b.kind} · </span>
                  <span style={{ color: "var(--fog)" }}>{b.id}</span>
                  <span className="sim">[chunk {b.chunk} · sim {b.sim.toFixed(2)}]</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

window.ContinentalColumn = ContinentalColumn;
