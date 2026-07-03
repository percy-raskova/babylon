// TerritoryDetail.jsx — drill into a single hex
const TerritoryDetail = ({ territoryId, onBack }) => {
  const t = window.MOCK.territories.find(x => x.id === territoryId) || window.MOCK.territories[0];
  const Stat = ({ label, value, color }) => (
    <div style={{ background: "var(--void)", border: "1px solid var(--rebar)", borderRadius: 4, padding: "10px 12px" }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700, color }}>{value}</div>
    </div>
  );
  return (
    <div style={{ minHeight: "100vh", background: "var(--void)", color: "var(--bone)", fontFamily: "var(--font-sans)", padding: "16px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
        <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Cockpit</button>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase" }}>▸ Territory · {t.id}</div>
      </div>
      <div style={{ maxWidth: 880, margin: "0 auto" }}>
        <div style={{ display: "flex", gap: 16, alignItems: "baseline", marginBottom: 18, paddingBottom: 14, borderBottom: "1px solid var(--rebar)" }}>
          <h1 style={{ fontSize: 32, fontWeight: 700, color: "var(--bone)" }}>{t.name}</h1>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, padding: "3px 10px", border: "1px solid var(--rebar)", borderRadius: 9999, color: "var(--fog)", letterSpacing: ".14em", textTransform: "uppercase" }}>{t.class}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ash)", marginLeft: "auto" }}>pop. {t.pop.toLocaleString()}</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 10, marginBottom: 18 }}>
          <Stat label="Heat"          value={t.heat.toFixed(2)}          color="var(--heat)"/>
          <Stat label="Rent"          value={t.rent.toFixed(2)}          color="var(--rent)"/>
          <Stat label="Consciousness" value={t.consciousness.toFixed(2)} color="var(--cadre)"/>
          <Stat label="Wealth"        value={t.wealth.toFixed(2)}        color="var(--rupture)"/>
          <Stat label="Biocap"        value={t.biocap.toFixed(2)}        color="var(--solidarity)"/>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 16 }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase", marginBottom: 10 }}>Active Organizations</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {window.MOCK.orgs_other.slice(0, 3).map(o => (
                <div key={o.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--rebar)" }}>
                  <div>
                    <div style={{ fontSize: 13, color: "var(--bone)" }}>{o.name}</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: ".06em" }}>{o.class}</div>
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: o.rel === "ally" ? "var(--solidarity)" : o.rel === "hostile" ? "var(--laser)" : "var(--fog)", letterSpacing: ".14em", textTransform: "uppercase" }}>{o.rel}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 16 }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase", marginBottom: 10 }}>Recent Events</div>
            {window.MOCK.events.filter(e => Math.random() > .4).slice(0, 4).map(e => (
              <div key={e.id} style={{ display: "flex", gap: 8, fontSize: 12, padding: "5px 0", borderBottom: "1px solid var(--rebar)" }}>
                <span style={{ fontFamily: "var(--font-mono)", color: e.severity === "critical" ? "var(--laser)" : e.severity === "warning" ? "var(--heat)" : "var(--solidarity)" }}>●</span>
                <span style={{ color: "var(--fog)", flex: 1 }}>{e.text}</span>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--shroud)", fontSize: 10 }}>t={e.tick}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
window.TerritoryDetail = TerritoryDetail;
