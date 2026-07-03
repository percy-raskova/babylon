// wire-window.jsx — Babylon-styled application window chrome with tabs.
// The "cockpit in a stairwell" aesthetic — traffic lights re-cast in Cold Collapse
// tokens (laser/heat/spire), CRT scanlines on the frame, JetBrains Mono tab labels.

const WireWindow = ({ tabs, activeId, onTab, badge, children }) => {
  return (
    <div style={{
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      background: "var(--void)",
      overflow: "hidden",
    }}>
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
          <span title="close"    style={{ width: 11, height: 11, borderRadius: 9999, background: "var(--laser)",   boxShadow: "0 0 4px rgba(255,51,68,0.5)" }}></span>
          <span title="minimize" style={{ width: 11, height: 11, borderRadius: 9999, background: "var(--heat)",    boxShadow: "0 0 4px rgba(217,122,44,0.4)" }}></span>
          <span title="maximize" style={{ width: 11, height: 11, borderRadius: 9999, background: "var(--solidarity)", boxShadow: "0 0 4px rgba(95,191,122,0.45)" }}></span>
        </div>

        {/* App title — centered absolutely so tabs/content don't shift it */}
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
            color: "var(--spire)",
            textShadow: "0 0 8px rgba(77,217,230,0.45)",
          }}>THE WIRE</span>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 9.5,
            letterSpacing: "0.28em", color: "var(--ash)",
            marginLeft: 4,
          }}>v0.4.2-dev</span>
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
          return (
            <button
              key={t.id}
              onClick={() => onTab(t.id)}
              style={{
                position: "relative",
                background: active ? "var(--void)" : "transparent",
                color: active ? "var(--spire)" : "var(--fog)",
                border: "none",
                borderRight: "1px solid var(--rebar)",
                padding: "9px 18px 8px",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                letterSpacing: "0.22em",
                textTransform: "uppercase",
                fontWeight: active ? 700 : 500,
                cursor: "pointer",
                display: "flex", alignItems: "center", gap: 8,
                borderTop: active ? "2px solid var(--spire)" : "2px solid transparent",
                marginTop: active ? 0 : 0,
                boxShadow: active ? "inset 0 -1px 0 var(--void)" : "none",
                transition: "color 120ms, background 120ms",
              }}
              onMouseOver={e => { if (!active) e.currentTarget.style.color = "var(--bone)"; }}
              onMouseOut={e => { if (!active) e.currentTarget.style.color = "var(--fog)"; }}
            >
              <span style={{
                width: 6, height: 6, borderRadius: 9999,
                background: active ? "var(--spire)" : "var(--wet-steel)",
                boxShadow: active ? "0 0 6px rgba(77,217,230,0.7)" : "none",
              }}></span>
              {t.label}
              {t.count != null && (
                <span style={{
                  fontFamily: "var(--font-mono)", fontSize: 9,
                  padding: "1px 6px", borderRadius: 9999,
                  background: active ? "rgba(77,217,230,0.12)" : "var(--rebar)",
                  color: active ? "var(--spire)" : "var(--ash)",
                  letterSpacing: "0.1em",
                  fontWeight: 600,
                }}>{t.count}</span>
              )}
              {t.dot && (
                <span style={{
                  width: 5, height: 5, borderRadius: 9999,
                  background: t.dot,
                  boxShadow: `0 0 5px ${t.dot}`,
                }}></span>
              )}
            </button>
          );
        })}
        <div style={{ flex: 1, borderBottom: "1px solid var(--rebar)" }}></div>
      </div>

      {/* CONTENT */}
      <div style={{ flex: 1, minHeight: 0, position: "relative", overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
};

window.WireWindow = WireWindow;
