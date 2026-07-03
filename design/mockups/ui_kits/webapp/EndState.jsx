// EndState.jsx — Rupture (victory) or Defeat
const EndState = ({ outcome = "rupture", onRestart }) => {
  const isRupture = outcome === "rupture";
  return (
    <div style={{ minHeight: "100vh", background: isRupture ? "radial-gradient(ellipse at center, #1a1408 0%, #06070b 75%)" : "radial-gradient(ellipse at center, #1a0606 0%, #06070b 75%)", color: "var(--bone)", fontFamily: "var(--font-sans)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 32, position: "relative", overflow: "hidden" }}>
      <div style={{ position:"absolute", inset:0, background:"repeating-linear-gradient(0deg, rgba(0,0,0,.22) 0, rgba(0,0,0,.22) 1px, transparent 1px, transparent 4px)", pointerEvents:"none"}}/>
      <div style={{ position: "relative", textAlign: "center", maxWidth: 640 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".4em", color: isRupture ? "var(--rupture)" : "var(--laser)", textTransform: "uppercase", marginBottom: 20, textShadow: isRupture ? "0 0 16px rgba(212,160,44,.5)" : "0 0 16px rgba(255,51,68,.5)" }}>{isRupture ? "▸ Rupture Achieved" : "✕ Organizational Collapse"}</div>
        <h1 style={{ fontSize: 56, fontWeight: 700, letterSpacing: "0.06em", marginBottom: 24, color: isRupture ? "var(--rupture)" : "var(--laser)" }}>{isRupture ? "BABYLON FALLS" : "THE BUNKER FAILS"}</h1>
        <p style={{ fontSize: 16, color: "var(--fog)", lineHeight: 1.7, marginBottom: 36 }}>
          {isRupture
            ? "On Tick 0067 the Wayne County General Strike spread beyond the simulation's containment. Imperial rent collapsed by 40% across the region. The vanguard transitioned from civil-society organization to dual-power formation. The empire could not hold what it could not extract."
            : "On Tick 0048 state heat exceeded 0.92. WCSD raids dispersed the organizing core. Surviving cadre dispersed into the lumpen periphery. The conditions remain — but this formation will not see them ripen."}
        </p>
        <div style={{ display: "flex", gap: 14, justifyContent: "center", marginBottom: 36 }}>
          {[
            { label: "Final Tick", value: isRupture ? "0067" : "0048", c: "var(--spire)" },
            { label: "Consciousness", value: isRupture ? "0.71" : "0.34", c: "var(--cadre)" },
            { label: "Solidarity Edges", value: isRupture ? "12" : "3",  c: "var(--solidarity)" },
            { label: "Heat at End",   value: isRupture ? "0.58" : "0.94", c: "var(--heat)" },
          ].map(s => (
            <div key={s.label} style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "12px 18px", minWidth: 110 }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase", marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 700, color: s.c }}>{s.value}</div>
            </div>
          ))}
        </div>
        <button onClick={onRestart} style={{ background: "var(--spire)", color: "var(--void)", border: "none", borderRadius: 4, padding: "12px 32px", fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: ".22em", textTransform: "uppercase", cursor: "pointer", boxShadow: "0 0 24px rgba(77,217,230,.3)" }}>▸ New Operation</button>
      </div>
    </div>
  );
};
window.EndState = EndState;
