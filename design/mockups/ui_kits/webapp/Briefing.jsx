// Briefing.jsx — Pre-game scenario briefing
const Briefing = ({ onStart, onBack }) => {
  const s = window.MOCK.scenario;
  return (
    <div style={{ minHeight: "100vh", background: "var(--void)", fontFamily: "var(--font-sans)", color: "var(--bone)", padding: 32, position: "relative", overflow: "auto" }}>
      <div style={{ position:"absolute", inset:0, background:"repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0, rgba(0,0,0,.18) 1px, transparent 1px, transparent 4px)", pointerEvents:"none"}}/>
      <div style={{ maxWidth: 760, margin: "0 auto", position: "relative" }}>
        <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Games</button>
        <div style={{ marginTop: 24, marginBottom: 28 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: ".3em", color: "var(--spire)", textTransform: "uppercase", marginBottom: 8 }}>▸ Scenario Briefing</div>
          <h1 style={{ fontSize: 36, fontWeight: 700, letterSpacing: "0.04em", color: "var(--bone)", marginBottom: 6 }}>{s.name}</h1>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fog)", letterSpacing: ".06em" }}>{s.region} · {s.territories} territories · t={s.year}.W{s.week}</div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {[
            { label: "Population", value: "742K", color: "var(--cadre)" },
            { label: "Imperial Rent", value: "0.43", color: "var(--rent)" },
            { label: "Avg. Consciousness", value: "0.39", color: "var(--cadre)" },
            { label: "State Heat", value: "0.51", color: "var(--heat)" },
          ].map(s => (
            <div key={s.label} style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "16px 18px" }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase", marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700, color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
        <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 20, marginBottom: 14, lineHeight: 1.6 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase", marginBottom: 10 }}>Conditions</div>
          <p style={{ fontSize: 13, color: "var(--bone)", marginBottom: 10 }}>The American empire is in its terminal phase. In Wayne County, fifty years of deindustrialization have produced an irregular topology: depleted proletarian neighborhoods, a fortified labor aristocracy, an enclave bourgeoisie in Grosse Pointe, and a vast lumpen periphery in the East side.</p>
          <p style={{ fontSize: 13, color: "var(--fog)" }}>You play the <span style={{color:"var(--spire)"}}>Wayne County Labor Federation</span> — a small civil-society org with 8 cadre and 24 sympathizers. Your survival depends on consciousness work, mass-line organizing, and avoiding state attention until you have rupture-grade infrastructure.</p>
        </div>
        <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 20, marginBottom: 18 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: ".22em", color: "var(--rupture)", textTransform: "uppercase", marginBottom: 10 }}>Victory Conditions</div>
          <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              "Achieve regional consciousness ≥ 0.65 average",
              "Form 5+ active solidarity edges to mass orgs",
              "Survive 60 ticks without organizational collapse",
              "Trigger one rupture event without total state response",
            ].map((t, i) => (
              <li key={i} style={{ display: "flex", gap: 10, alignItems: "baseline", fontSize: 13, color: "var(--bone)" }}>
                <span style={{ color: "var(--rupture)", fontFamily: "var(--font-mono)", fontSize: 11 }}>0{i+1}</span>{t}
              </li>
            ))}
          </ul>
        </div>
        <button onClick={onStart} style={{ width: "100%", background: "var(--spire)", color: "var(--void)", border: "none", borderRadius: 4, padding: "14px", fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700, letterSpacing: ".22em", textTransform: "uppercase", cursor: "pointer", boxShadow: "0 0 24px rgba(77,217,230,.3)" }}>▸ Begin Operation · Tick 0042</button>
      </div>
    </div>
  );
};
window.Briefing = Briefing;
