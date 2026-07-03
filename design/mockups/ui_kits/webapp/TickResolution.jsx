// TickResolution.jsx — animated step-through of tick effects
const TickResolution = ({ onComplete, onBack }) => {
  const steps = [
    { phase: "OBSERVE", color: "var(--cadre)",      lines: ["Imperial rent recalculated across 81 territories", "Heat propagated through state edges", "Consciousness drift: +0.018 (Dearborn), +0.024 (Hamtramck)"] },
    { phase: "ORIENT",  color: "var(--population)", lines: ["WCLF OODA: orient phase", "Solidarity edge formed: WCLF ↔ Detroit Tenants Council", "Class character recalculated: 0 reclassifications"] },
    { phase: "DECIDE",  color: "var(--rupture)",    lines: ["Player action committed: EDUCATE → Dearborn", "Cost: 3 CL deducted (8.4 → 5.4)", "Target: 109,976 proletarians"] },
    { phase: "ACT",     color: "var(--solidarity)", lines: ["Educate resolved: +0.024 consciousness in Dearborn", "+1 sympathizer labor next tick (recruitment bonus)", "Reputation: 0.62 → 0.63"] },
    { phase: "RESPOND", color: "var(--laser)",      lines: ["State response: WCSD heat +0.02", "Informant detected — heat threshold approaching", "Bourgeois counter: Ford lobbying budget +$200K"] },
  ];
  const [step, setStep] = React.useState(0);
  const [auto, setAuto] = React.useState(true);
  React.useEffect(() => {
    if (!auto) return;
    if (step >= steps.length - 1) return;
    const t = setTimeout(() => setStep(s => s + 1), 1100);
    return () => clearTimeout(t);
  }, [step, auto]);
  return (
    <div style={{ height: "100vh", background: "var(--void)", color: "var(--bone)", fontFamily: "var(--font-sans)", display: "flex", flexDirection: "column", padding: 24, position: "relative", overflow: "hidden" }}>
      <div style={{ position:"absolute", inset:0, background:"repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0, rgba(0,0,0,.18) 1px, transparent 1px, transparent 4px)", pointerEvents:"none"}}/>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20, position: "relative" }}>
        <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Skip</button>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".3em", color: "var(--spire)", textTransform: "uppercase" }}>▸ Resolving Tick 0042 → 0043</div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)" }}>{step+1} / {steps.length}</div>
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", maxWidth: 720, margin: "0 auto", width: "100%", position: "relative" }}>
        <div style={{ display: "flex", gap: 4, marginBottom: 24 }}>
          {steps.map((s, i) => (
            <div key={i} style={{ flex: 1, height: 3, background: i <= step ? s.color : "var(--rebar)", borderRadius: 9999, transition: "background .3s", boxShadow: i === step ? `0 0 12px ${s.color}` : "none" }}/>
          ))}
        </div>
        {steps.slice(0, step + 1).map((s, i) => (
          <div key={i} style={{ marginBottom: 20, opacity: i === step ? 1 : 0.45, transition: "opacity .3s" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700, letterSpacing: ".3em", color: s.color, marginBottom: 8, textShadow: i === step ? `0 0 10px ${s.color}` : "none" }}>● {s.phase}</div>
            {s.lines.map((line, j) => (
              <div key={j} style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--bone)", padding: "3px 0 3px 16px", borderLeft: `1px solid ${s.color}`, marginLeft: 8, opacity: .85 }}>
                <span style={{ color: "var(--shroud)" }}>›</span> {line}
              </div>
            ))}
          </div>
        ))}
        {step >= steps.length - 1 && (
          <button onClick={onComplete} style={{ marginTop: "auto", alignSelf: "center", background: "var(--spire)", color: "var(--void)", border: "none", borderRadius: 4, padding: "12px 32px", fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: ".22em", textTransform: "uppercase", cursor: "pointer", boxShadow: "0 0 24px rgba(77,217,230,.3)" }}>▸ Continue · Tick 0043</button>
        )}
      </div>
    </div>
  );
};
window.TickResolution = TickResolution;
