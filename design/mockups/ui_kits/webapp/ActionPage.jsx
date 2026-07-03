// ActionPage.jsx — Babylon Web App UI Kit · Cold Collapse v8

const ACTION_TARGETS = {
  educate: [
    { id: "C001", name: "Dearborn — Proletarian", category: "Proletarian", credibility: "0.72" },
    { id: "C002", name: "Detroit East — Lumpen", category: "Lumpenproletariat", credibility: "0.41" },
    { id: "C003", name: "Hamtramck — Immigrant", category: "Proletarian", credibility: "0.68" },
    { id: "C004", name: "Downriver — Labor Aristo", category: "Labor Aristocracy", credibility: "0.55" },
  ],
  attack: [
    { id: "T001", name: "Wayne County Sheriff's Dept", type: "Institution" },
    { id: "T002", name: "Ford Motor Company", type: "Corporation" },
    { id: "T003", name: "Fiat-Chrysler Detroit", type: "Corporation" },
  ],
  aid: [
    { id: "A001", name: "Detroit Food Not Bombs", type: "Community Org" },
    { id: "A002", name: "UAW Local 600", type: "Labor Union" },
    { id: "A003", name: "Dearborn Community Defense", type: "Mutual Aid" },
  ],
  mobilize: [
    { id: "M001", name: "Dearborn Community Assembly" },
    { id: "M002", name: "Detroit East General Strike Committee" },
    { id: "M003", name: "Hamtramck Tenants Union" },
  ],
};

const ACTION_META = {
  educate:  { label: "Educate",  desc: "Raise class consciousness through political education. Targets communities with low consciousness but favorable credibility.", cost: "3 CL" },
  mobilize: { label: "Mobilize", desc: "Convert sympathizer energy into collective action. Commits sympathizer labor to build power in target assembly.", cost: "5 SL" },
  attack:   { label: "Attack",   desc: "Targeted sabotage against a bourgeois institution or corporation. Reduces their capacity and increases Heat.", cost: "8 CL" },
  aid:      { label: "Aid",      desc: "Transfer material resources (budget) to an allied organization to build solidarity infrastructure.", cost: "$50" },
};

const ActionPage = ({ auth, gameId, verb, onBack, onLogout }) => {
  const [selectedTarget, setSelectedTarget] = React.useState("");
  const [slCommitted, setSlCommitted] = React.useState(5);
  const [transferAmount, setTransferAmount] = React.useState(50);
  const [attackMode, setAttackMode] = React.useState("targeted");
  const [submitting, setSubmitting] = React.useState(false);
  const [submitted, setSubmitted] = React.useState(false);
  const [error, setError] = React.useState(null);

  const meta = ACTION_META[verb] || { label: verb, desc: "", cost: "?" };
  const targets = ACTION_TARGETS[verb] || [];

  React.useEffect(() => { if (targets.length > 0) setSelectedTarget(targets[0].id); }, [verb]);

  function handleSubmit(e) {
    e.preventDefault();
    if (!selectedTarget) { setError("Please select a target."); return; }
    setSubmitting(true); setError(null);
    setTimeout(() => { setSubmitting(false); setSubmitted(true); }, 800);
  }

  const labelStyle = { display: "block", fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.22em", textTransform: "uppercase", color: "var(--fog)", marginBottom: 6 };
  const inputStyle = { width: "100%", background: "var(--void)", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "10px 12px", fontSize: 13, color: "var(--bone)", outline: "none" };
  const submitBtn = (text) => ({
    marginTop: 8, background: submitting ? "rgba(77,217,230,.4)" : "var(--spire)",
    color: "var(--void)", border: "none", borderRadius: 4, padding: "12px",
    fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: "0.18em", textTransform: "uppercase",
    cursor: submitting ? "not-allowed" : "pointer",
    boxShadow: submitting ? "none" : "0 0 16px rgba(77,217,230,.25)"
  });

  if (submitted) return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "var(--void)", fontFamily: "var(--font-sans)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--rebar)", padding: "10px 16px", flexShrink: 0 }}>
        <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: "0.32em", color: "var(--bone)" }}>BAB<span style={{color:"var(--spire)"}}>Y</span>LON</span>
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 14 }}>
        <div style={{ fontSize: 36, color: "var(--solidarity)", textShadow: "0 0 16px rgba(95,191,122,.5)" }}>✓</div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".24em", textTransform: "uppercase", color: "var(--spire)" }}>ACTION SUBMITTED</div>
        <div style={{ fontSize: 13, color: "var(--fog)" }}>{meta.label} → {targets.find(t=>t.id===selectedTarget)?.name}</div>
        <button onClick={onBack} style={{ ...submitBtn(), padding: "10px 22px", marginTop: 12 }}>← Back to Briefing</button>
      </div>
    </div>
  );

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--void)", fontFamily: "var(--font-sans)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--rebar)", padding: "10px 16px", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: "0.32em", color: "var(--bone)" }}>BAB<span style={{color:"var(--spire)"}}>Y</span>LON</span>
          <span style={{ fontSize: 12, color: "var(--shroud)" }}>·</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fog)" }}>{gameId?.slice(0,12)}...</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fog)" }}>{auth?.username}</span>
          <button onClick={onLogout} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "5px 12px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>Logout</button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, maxWidth: 520, margin: "0 auto 24px" }}>
          <h2 style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "var(--spire)", textShadow: "0 0 10px rgba(77,217,230,.3)" }}>▸ ACTION · {meta.label}</h2>
          <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Back</button>
        </div>

        <div style={{ maxWidth: 520, margin: "0 auto" }}>
          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "16px 18px", marginBottom: 14 }}>
            <div style={{ fontSize: 13, color: "var(--fog)", marginBottom: 12, lineHeight: 1.5 }}>{meta.desc}</div>
            <div style={{ display: "flex", gap: 20, paddingTop: 10, borderTop: "1px solid var(--rebar)" }}>
              <div><span style={labelStyle}>Cost</span><span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--rupture)", fontWeight: 600 }}>{meta.cost}</span></div>
              <div><span style={labelStyle}>Org</span><span style={{ fontSize: 13, color: "var(--bone)" }}>Wayne County Labor Federation</span></div>
            </div>
          </div>

          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "20px" }}>
            {error && <p style={{ color: "var(--laser)", fontFamily: "var(--font-mono)", fontSize: 11, marginBottom: 12, letterSpacing: ".05em" }}>✕ {error}</p>}
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={labelStyle}>
                  {verb === "educate" ? "Target Community" : verb === "attack" ? "Target Institution / Corporation" : verb === "aid" ? "Target Organization" : "Target Assembly"}
                </label>
                <select value={selectedTarget} onChange={e => setSelectedTarget(e.target.value)} style={inputStyle}>
                  {targets.map(t => (
                    <option key={t.id} value={t.id}>
                      {t.name}{t.category ? ` (${t.category})` : ""}{t.type ? ` — ${t.type}` : ""}{t.credibility ? ` — Credibility: ${t.credibility}` : ""}
                    </option>
                  ))}
                </select>
              </div>

              {verb === "mobilize" && (
                <div>
                  <label style={labelStyle}>Sympathizer Labor Committed</label>
                  <input type="number" min={0} max={44} value={slCommitted} onChange={e => setSlCommitted(Number(e.target.value))} style={{ ...inputStyle, fontFamily: "var(--font-mono)" }}/>
                </div>
              )}
              {verb === "aid" && (
                <div>
                  <label style={labelStyle}>Transfer Amount ($)</label>
                  <input type="number" min={0} value={transferAmount} onChange={e => setTransferAmount(Number(e.target.value))} style={{ ...inputStyle, fontFamily: "var(--font-mono)" }}/>
                </div>
              )}
              {verb === "attack" && (
                <div>
                  <label style={labelStyle}>Attack Mode</label>
                  <select value={attackMode} onChange={e => setAttackMode(e.target.value)} style={inputStyle}>
                    <option value="targeted">Targeted Sabotage</option>
                    <option value="mass">Mass Action</option>
                  </select>
                </div>
              )}

              <button type="submit" disabled={submitting} style={submitBtn()}>
                {submitting ? "Submitting..." : `Submit ${meta.label}`}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { ActionPage });
