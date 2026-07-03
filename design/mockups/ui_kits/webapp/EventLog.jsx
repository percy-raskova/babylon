// EventLog.jsx — tick-by-tick replay
const EventLog = ({ onBack }) => {
  const [filter, setFilter] = React.useState("all");
  const events = window.MOCK.events;
  const filtered = filter === "all" ? events : events.filter(e => e.severity === filter);
  return (
    <div style={{ minHeight: "100vh", background: "var(--void)", color: "var(--bone)", fontFamily: "var(--font-sans)", padding: "16px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
        <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Cockpit</button>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase" }}>▸ Event Log</div>
        <div style={{ display: "flex", gap: 4 }}>
          {["all","info","warning","critical","rupture"].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{ background: filter === f ? "rgba(77,217,230,.08)" : "transparent", color: filter === f ? "var(--spire)" : "var(--ash)", border: "1px solid", borderColor: filter === f ? "var(--spire)" : "var(--rebar)", borderRadius: 3, padding: "5px 10px", fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".14em", textTransform: "uppercase", cursor: "pointer" }}>{f}</button>
          ))}
        </div>
      </div>
      <div style={{ maxWidth: 880, margin: "0 auto" }}>
        {filtered.map(e => (
          <div key={e.id} style={{ display: "flex", gap: 14, alignItems: "baseline", padding: "12px 14px", marginBottom: 6, background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 4, borderLeftColor: e.severity === "critical" ? "var(--laser)" : e.severity === "warning" ? "var(--heat)" : e.severity === "rupture" ? "var(--rupture)" : "var(--solidarity)", borderLeftWidth: 2 }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--shroud)", minWidth: 50, letterSpacing: ".1em" }}>t={e.tick}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", minWidth: 110, letterSpacing: ".14em", textTransform: "uppercase" }}>{e.type}</span>
            <span style={{ fontSize: 13, color: "var(--bone)", flex: 1 }}>{e.text}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: e.severity === "critical" ? "var(--laser)" : e.severity === "warning" ? "var(--heat)" : e.severity === "rupture" ? "var(--rupture)" : "var(--solidarity)", letterSpacing: ".18em", textTransform: "uppercase" }}>● {e.severity}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
window.EventLog = EventLog;
