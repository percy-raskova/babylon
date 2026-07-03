// DialecticSpread.jsx — novel surface: contradictions as cards
const DialecticSpread = ({ onBack }) => {
  const cards = [
    { thesis: "Labor Aristocracy", antithesis: "Lumpen", resolution: "Mass Line", tension: 0.71, color: "var(--cadre)" },
    { thesis: "Civil Society",     antithesis: "Dual Power", resolution: "Rupture", tension: 0.42, color: "var(--rupture)" },
    { thesis: "Reproduction",      antithesis: "Survival",   resolution: "Mutual Aid", tension: 0.58, color: "var(--solidarity)" },
    { thesis: "State Repression",  antithesis: "Counter-Power", resolution: "Defense", tension: 0.84, color: "var(--laser)" },
  ];
  return (
    <div style={{ minHeight: "100vh", background: "var(--void)", color: "var(--bone)", fontFamily: "var(--font-sans)", padding: "16px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 18 }}>
        <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Cockpit</button>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase" }}>▸ Active Contradictions</div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)" }}>{cards.length} active</div>
      </div>
      <div style={{ maxWidth: 1080, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 14 }}>
        {cards.map((c, i) => (
          <div key={i} style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 20, position: "relative", overflow: "hidden" }}>
            <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at top right, ${c.color}, transparent 60%)`, opacity: .06, pointerEvents: "none" }}/>
            <div style={{ position: "relative" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: c.color, textTransform: "uppercase", marginBottom: 14 }}>● Contradiction {String(i+1).padStart(2,"0")}</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: 12, marginBottom: 16 }}>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase", marginBottom: 4 }}>Thesis</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "var(--bone)" }}>{c.thesis}</div>
                </div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, color: c.color }}>↮</div>
                <div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase", marginBottom: 4 }}>Antithesis</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "var(--bone)" }}>{c.antithesis}</div>
                </div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase" }}>Tension</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: c.color }}>{c.tension.toFixed(2)}</span>
                </div>
                <div style={{ height: 4, background: "var(--void)", borderRadius: 9999, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${c.tension*100}%`, background: c.color, boxShadow: `0 0 8px ${c.color}` }}/>
                </div>
              </div>
              <div style={{ paddingTop: 12, borderTop: "1px solid var(--rebar)", display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase" }}>Synthesis</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: c.color, letterSpacing: ".14em", textTransform: "uppercase" }}>▸ {c.resolution}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
window.DialecticSpread = DialecticSpread;
