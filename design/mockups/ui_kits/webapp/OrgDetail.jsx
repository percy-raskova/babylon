// OrgDetail.jsx — full vanguard breakdown for player org
const OrgDetail = ({ onBack }) => {
  const o = window.MOCK.player_org;
  const v = o.vanguard;
  const Spark = ({ data, color, label, value }) => {
    const min = Math.min(...data), max = Math.max(...data), span = (max - min) || 1;
    const w = 200, h = 36, step = w / (data.length - 1);
    const pts = data.map((d, i) => `${(i*step).toFixed(1)},${(h - ((d-min)/span)*h).toFixed(1)}`).join(" ");
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--rebar)" }}>
        <div style={{ minWidth: 90 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase" }}>{label}</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 700, color }}>{value}</div>
        </div>
        <svg width={w} height={h}><polyline fill="none" stroke={color} strokeWidth="1.5" points={pts}/></svg>
      </div>
    );
  };
  return (
    <div style={{ minHeight: "100vh", background: "var(--void)", color: "var(--bone)", fontFamily: "var(--font-sans)", padding: "16px 24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
        <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Cockpit</button>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase" }}>▸ Organization · {o.short}</div>
      </div>
      <div style={{ maxWidth: 880, margin: "0 auto" }}>
        <div style={{ paddingBottom: 14, borderBottom: "1px solid var(--rebar)", marginBottom: 18 }}>
          <h1 style={{ fontSize: 28, fontWeight: 700 }}>{o.name}</h1>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fog)", letterSpacing: ".06em", marginTop: 6 }}>{o.org_type} · {o.class_character} · {o.members.toLocaleString()} members · OODA: <span style={{color:"var(--spire)"}}>{o.ooda_phase}</span></div>
        </div>
        <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 18, marginBottom: 14 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase", marginBottom: 6 }}>Vanguard Economy</div>
          <Spark data={o.history_cl}   color="var(--cadre)"      label="Cadre Labor"       value={`${v.cl.toFixed(1)} / ${v.cl_max}`}/>
          <Spark data={o.history_sl}   color="var(--solidarity)" label="Sympathizer Labor" value={`${v.sl.toFixed(1)} / ${v.sl_max}`}/>
          <Spark data={o.history_rep}  color="var(--solidarity)" label="Reputation"        value={`${(v.rep*100).toFixed(0)}%`}/>
          <Spark data={o.history_heat} color="var(--heat)"       label="Heat"              value={`${(v.heat*100).toFixed(0)}%`}/>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 16 }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase", marginBottom: 10 }}>Relations</div>
            {window.MOCK.orgs_other.map(x => (
              <div key={x.id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--rebar)", fontSize: 12 }}>
                <span style={{ color: "var(--bone)" }}>{x.short || x.name}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: x.rel === "ally" ? "var(--solidarity)" : x.rel === "hostile" ? "var(--laser)" : x.rel === "exploiter" ? "var(--rent)" : "var(--fog)", letterSpacing: ".14em", textTransform: "uppercase" }}>{x.rel}</span>
              </div>
            ))}
          </div>
          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 16 }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase", marginBottom: 10 }}>Org History</div>
            {window.MOCK.events.slice(0, 6).map(e => (
              <div key={e.id} style={{ display: "flex", gap: 8, fontSize: 11, padding: "5px 0", borderBottom: "1px solid var(--rebar)" }}>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--shroud)", minWidth: 40 }}>t={e.tick}</span>
                <span style={{ color: "var(--fog)" }}>{e.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
window.OrgDetail = OrgDetail;
