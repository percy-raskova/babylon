// synopticon-window.jsx — Algorithmic State Apparatus shell
// The Wire's chrome with the state mask on: laser dominant, classification banners,
// system-clinical typography. This is the operator's terminal at a black site.

const SynopticonWindow = ({ tabs, activeId, onTab, badge, classification, children }) => {
  return (
    <div style={{
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      background: "var(--void)",
      overflow: "hidden",
    }}>
      {/* TOP CLASSIFICATION BAR — laser red strip */}
      <div className="syn-cls-bar">
        <span style={{ flexShrink: 0 }}>◆ {classification}</span>
        <span style={{ flex: 1, textAlign: "center", letterSpacing: "0.22em", opacity: 0.85 }}>
          UNAUTHORIZED DISCLOSURE SUBJECT TO CRIMINAL SANCTION · HANDLE VIA SAP CHANNELS
        </span>
        <span style={{ flexShrink: 0, opacity: 0.9 }}>SAP · LAVENDER ◆</span>
      </div>

      {/* TITLE BAR — traffic lights + app title + tick badge */}
      <div style={{
        flexShrink: 0,
        display: "flex", alignItems: "center", gap: 14,
        padding: "8px 14px",
        background: "linear-gradient(180deg, #0b0e15 0%, #07090d 100%)",
        borderBottom: "1px solid var(--rebar)",
        position: "relative",
      }}>
        {/* Traffic lights — Babylon palette */}
        <div style={{ display: "flex", gap: 7 }}>
          <span title="close"    style={{ width: 11, height: 11, borderRadius: 9999, background: "var(--laser)",     boxShadow: "0 0 4px rgba(255,51,68,0.5)" }}></span>
          <span title="minimize" style={{ width: 11, height: 11, borderRadius: 9999, background: "var(--heat)",      boxShadow: "0 0 4px rgba(217,122,44,0.4)" }}></span>
          <span title="maximize" style={{ width: 11, height: 11, borderRadius: 9999, background: "var(--solidarity)", boxShadow: "0 0 4px rgba(95,191,122,0.45)" }}></span>
        </div>

        {/* App title — absolutely centered */}
        <div style={{
          position: "absolute",
          left: "50%", top: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex", alignItems: "baseline", gap: 10,
          pointerEvents: "none",
        }}>
          <span style={{
            fontFamily: "var(--font-sans)", fontWeight: 700,
            fontSize: 13, letterSpacing: "0.42em",
            color: "var(--fog)",
          }}>BABYLON</span>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 10,
            letterSpacing: "0.32em", color: "var(--ash)",
          }}>·</span>
          <span style={{
            fontFamily: "var(--font-sans)", fontWeight: 700,
            fontSize: 13, letterSpacing: "0.42em",
            color: "var(--laser)",
            textShadow: "0 0 10px rgba(255,51,68,0.55)",
          }}>THE SYNOPTICON</span>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 9.5,
            letterSpacing: "0.28em", color: "var(--ash)",
            marginLeft: 4,
          }}>v3.13-rc</span>
        </div>

        {/* Right side — tick badge */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {badge}
        </div>
      </div>

      {/* TAB BAR */}
      <div style={{
        flexShrink: 0,
        display: "flex", alignItems: "stretch",
        background: "#0a0d13",
        borderBottom: "1px solid var(--rebar)",
        paddingLeft: 8,
      }}>
        {tabs.map(t => {
          const active = t.id === activeId;
          const accent = t.accent || "var(--laser)";
          return (
            <button
              key={t.id}
              onClick={() => onTab(t.id)}
              style={{
                position: "relative",
                background: active ? "var(--void)" : "transparent",
                color: active ? accent : "var(--fog)",
                border: "none",
                borderRight: "1px solid var(--rebar)",
                padding: "9px 18px 8px",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                letterSpacing: "0.24em",
                textTransform: "uppercase",
                fontWeight: active ? 700 : 500,
                cursor: "pointer",
                display: "flex", alignItems: "center", gap: 8,
                borderTop: active ? `2px solid ${accent}` : "2px solid transparent",
                transition: "color 120ms, background 120ms",
              }}
              onMouseOver={e => { if (!active) e.currentTarget.style.color = "var(--bone)"; }}
              onMouseOut={e => { if (!active) e.currentTarget.style.color = "var(--fog)"; }}
            >
              <span style={{
                width: 6, height: 6, borderRadius: 9999,
                background: active ? accent : "var(--wet-steel)",
                boxShadow: active ? `0 0 6px ${accent}` : "none",
              }}></span>
              {t.label}
              {t.count != null && (
                <span style={{
                  fontFamily: "var(--font-mono)", fontSize: 9,
                  padding: "1px 6px", borderRadius: 9999,
                  background: active ? "rgba(255,51,68,0.12)" : "var(--rebar)",
                  color: active ? accent : "var(--ash)",
                  letterSpacing: "0.1em",
                  fontWeight: 600,
                }}>{t.count}</span>
              )}
            </button>
          );
        })}
        <div style={{ flex: 1, borderBottom: "1px solid var(--rebar)" }}></div>

        {/* nav back to cockpit */}
        <a href="../wire/The Wire.html" className="btn-ghost" style={{
          alignSelf: "center", marginRight: 8, textDecoration: "none",
        }}>← The Wire</a>
        <a href="../ui_kits/webapp/index.html" className="btn-ghost" style={{
          alignSelf: "center", marginRight: 12, textDecoration: "none",
        }}>← Cockpit</a>
      </div>

      {/* CONTENT */}
      <div style={{ flex: 1, minHeight: 0, position: "relative", overflow: "hidden" }}>
        {children}
      </div>

      {/* BOTTOM CLASSIFICATION BAR */}
      <div className="syn-cls-bar bottom">
        <span style={{ flexShrink: 0 }}>◆ {classification}</span>
        <span style={{ flex: 1, textAlign: "center", letterSpacing: "0.22em", opacity: 0.85 }}>
          DERIVED FROM: LAVENDER-V1, GOSPEL · DECLASSIFY ON: NEVER · DISTRIBUTION: STATE-EYES-ONLY
        </span>
        <span style={{ flexShrink: 0, opacity: 0.9 }}>◆ {window.SYN_DATA.META.caveat}</span>
      </div>
    </div>
  );
};

window.SynopticonWindow = SynopticonWindow;
