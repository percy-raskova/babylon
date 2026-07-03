// wire-liberated.jsx — FREE SIGNAL · pirate-radio phosphor terminal with handwritten marginalia
// JetBrains Mono in green phosphor on a CRT, scanlines + paper-grain handled by wire.css.
// Citations live in the gutter as Caveat-font margin notes (tilted, hand-scrawled).
// Euphemism spans get a phosphor glow when their `data-euph` id matches activeEuph.

const LiberatedColumn = ({ activeEuph, setActiveEuph, euphAlways, citationDensity, focused }) => {
  const story = window.WIRE_DATA.story;
  const l = story.liberated;
  const meta = window.WIRE_DATA.meta;

  const renderRun = (run, idx) => {
    if (typeof run === "string") return run;
    if (run.euph) {
      return (
        <span
          key={"e" + idx}
          className={"euph phos" + (activeEuph === run.euph ? " active" : "")}
          data-euph={run.euph}
          onMouseEnter={() => setActiveEuph(run.euph)}
          onMouseLeave={() => !euphAlways && setActiveEuph(null)}
          onClick={() => setActiveEuph(activeEuph === run.euph ? null : run.euph)}
        >{run.text}</span>
      );
    }
    return null;
  };

  // chunky pirate-radio dial readout
  const SignalMeter = () => {
    const bars = 24;
    return (
      <div style={{ display: "flex", gap: 2, alignItems: "flex-end", height: 14 }}>
        {Array.from({ length: bars }).map((_, i) => {
          const h = 3 + (Math.sin(i * 0.8) * 0.5 + 0.5) * 10 + (i > 16 ? 2 : 0);
          const dim = i > 19;
          return (
            <div key={i} style={{
              width: 2, height: h,
              background: dim ? "rgba(95,191,122,0.18)" : "rgba(127,224,161,0.85)",
              boxShadow: dim ? "none" : "0 0 4px rgba(95,191,122,0.6)"
            }}></div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="col-wrap col-liberated">
      <div className="col-head" style={{ background: "rgba(95,191,122,0.04)", borderBottomColor: "rgba(127,224,161,0.18)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="pill" style={{ color: "#7fe0a1", borderColor: "rgba(127,224,161,0.35)", background: "rgba(95,191,122,0.05)" }}>
            <span style={{ width: 6, height: 6, borderRadius: 9999, background: "#7fe0a1", boxShadow: "0 0 6px rgba(95,191,122,0.7)" }}></span>
            CHANNEL · LIBERATED
          </span>
          <span className="kicker" style={{ color: "rgba(127,224,161,0.6)" }}>COUNTER-HEGEMONIC</span>
        </div>
        <span className="kicker" style={{ color: "rgba(127,224,161,0.6)" }}>OP // {l.operator} · QTH {meta.qth.split(" / ")[0]}</span>
      </div>

      <div className="col-body" style={{ padding: 0 }}>
        {/* Callsign / frequency block */}
        <div className="signal-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 14 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div className="callsign">▸ {l.brand} · {l.callsign}</div>
            <div className="freq phos">{meta.freq}</div>
            <div className="mono" style={{ fontSize: 10, color: "rgba(127,224,161,0.65)", letterSpacing: "0.18em" }}>
              QTH {meta.qth} · UTC {meta.timestamp_utc.slice(11,19)} · TX +12.4 dB
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
            <SignalMeter />
            <div className="mono" style={{ fontSize: 10, color: "rgba(127,224,161,0.65)", letterSpacing: "0.18em" }}>
              S9+20 · CLEAR
            </div>
          </div>
        </div>

        <div className="tx-marker">{l.pre}</div>

        {/* Hed */}
        <div style={{ padding: "16px 22px 4px" }}>
          <h1 className="hed">{l.hed}</h1>
        </div>

        {/* Story body — TWO COLUMNS inside the column: prose | margin */}
        <div style={{ padding: "12px 0 16px" }}>
          {l.paragraphs.map((para, pi) => (
            <div
              key={pi}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 180px",
                gap: 14,
                padding: "8px 22px 10px",
                borderBottom: pi < l.paragraphs.length - 1 ? "1px dashed rgba(127,224,161,0.10)" : "none",
              }}
            >
              <p>
                <span className="phos">{para.body.map((run, ri) => renderRun(run, pi + "-" + ri))}</span>
                {pi === l.paragraphs.length - 1 && <span className="cursor"></span>}
              </p>

              {citationDensity !== "off" && para.margin && (
                <div className={"lib-margin tilt-" + ((pi % 6) + 1)}>
                  <span style={{ display: "inline-block", marginRight: 4 }}>↳</span>{para.margin.note}
                  <span className="ref">— {para.margin.ref}</span>
                  {citationDensity === "dense" && (
                    <span className="mono" style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "rgba(217,160,44,0.7)", display: "block", letterSpacing: "0.14em", marginTop: 2 }}>
                      [{para.margin.chunk}]
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="tx-marker">{l.post}</div>

        {/* Sign-off block */}
        <div style={{ padding: "10px 22px 20px", display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div className="mono" style={{ fontSize: 10, color: "rgba(127,224,161,0.7)", letterSpacing: "0.2em" }}>
            73 · OP // {l.operator} · NEXT TX +60M
          </div>
          <div className="hand" style={{ fontSize: 18, color: "#ffd76b", transform: "rotate(-1.5deg)" }}>
            — pass it on, comrades
          </div>
        </div>
      </div>
    </div>
  );
};

window.LiberatedColumn = LiberatedColumn;
