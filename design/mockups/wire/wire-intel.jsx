// wire-intel.jsx — CABLE 1847-A · SIGINT cable column
// Hybrid: classification bar + structured field grid + redacted prose + chunk refs

const IntelColumn = ({ citationDensity, focused }) => {
  const story = window.WIRE_DATA.story;
  const i = story.intel;
  const meta = window.WIRE_DATA.meta;

  // render either text or {redact: "..."} bars
  const r = (s) => {
    // detect ▮▮▮ runs already in strings; render them with .redact-dark class
    const parts = s.split(/(▮+)/g);
    return parts.map((p, idx) =>
      /^▮+$/.test(p)
        ? <span key={idx} className="redact-dark">{p}</span>
        : <span key={idx}>{p}</span>
    );
  };

  return (
    <div className="col-wrap col-intel">
      <div className="col-head">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="pill" style={{ color: "var(--rupture)", borderColor: "rgba(212,160,44,0.35)" }}>
            <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--rupture)" }}></span>
            CHANNEL · INTEL
          </span>
          <span className="kicker" style={{ color: "var(--ash)" }}>FOG-OF-WAR PARTIAL</span>
        </div>
        <span className="kicker" style={{ color: "var(--ash)" }}>CABLE {i.cable_id}</span>
      </div>

      {/* Top classification bar — laser red, dominant */}
      <div className="cls-bar">{i.classification}</div>

      <div className="col-body">
        {/* Cable head */}
        <div className="cable-head">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
            <span className="cable-id">CABLE {i.cable_id}</span>
            <span className="mono" style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.18em" }}>
              PAGE {meta.page_of}
            </span>
          </div>

          <div className="field-row">
            <span className="k">SUBJ</span>
            <span className="v" style={{ color: "var(--bone)", fontWeight: 600, letterSpacing: "0.06em" }}>{i.subj}</span>
          </div>
          <div className="field-row">
            <span className="k">ORIGIN</span>
            <span className="v">{r(i.origin)}</span>
          </div>
          <div className="field-row">
            <span className="k">ROUTING</span>
            <span className="v" style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {i.routing.map((rr, idx) => (
                <span key={idx} style={{
                  display: "inline-block",
                  padding: "1px 6px",
                  border: "1px solid var(--rebar)",
                  borderRadius: 2,
                  fontSize: 10,
                  color: "var(--fog)",
                  background: "rgba(255,255,255,0.02)",
                }}>{r(rr)}</span>
              ))}
            </span>
          </div>
          <div className="field-row">
            <span className="k">CAVEAT</span>
            <span className="v" style={{ color: "var(--laser)", fontWeight: 600 }}>{i.caveat}</span>
          </div>
        </div>

        {/* Structured fields */}
        <div style={{ padding: "14px 22px", borderBottom: "1px solid var(--rebar)" }}>
          <div className="label" style={{ marginBottom: 8, color: "var(--rupture)" }}>▸ Structured fields</div>
          {i.fields.map(([k, v]) => (
            <div key={k} className="field-row">
              <span className="k">{k}</span>
              <span className="v">{r(v)}</span>
            </div>
          ))}

          {/* Confidence bar (the one explicitly numeric) */}
          <div style={{ marginTop: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
              <span className="label">Aggregate confidence</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--spire)", fontWeight: 600 }}>0.84 · HIGH</span>
            </div>
            <div className="confidence-bar"><div style={{ width: "84%" }}></div></div>
          </div>
        </div>

        {/* Assessment prose */}
        <div style={{ padding: "14px 22px", borderBottom: "1px solid var(--rebar)" }}>
          <div className="label" style={{ marginBottom: 10, color: "var(--rupture)" }}>▸ Assessment</div>
          {i.assessment.map((a, idx) => (
            <p key={idx} className="assess">
              <span style={{ color: "var(--ash)", marginRight: 6 }}>§{idx + 1}.</span>
              {r(a)}
            </p>
          ))}
        </div>

        {/* RAG refs */}
        {citationDensity !== "off" && (
          <div style={{ padding: "14px 22px", borderBottom: "1px solid var(--rebar)" }}>
            <div className="label" style={{ marginBottom: 10, color: "var(--rupture)" }}>▸ Corpus references</div>
            {i.refs.map((ref, idx) => (
              <div key={idx} style={{
                display: "grid",
                gridTemplateColumns: "auto 1fr auto",
                gap: 10,
                alignItems: "baseline",
                padding: "5px 0",
                borderBottom: "1px dotted var(--rebar)",
              }}>
                <span className="mono" style={{ fontSize: 10, color: "var(--rupture)", letterSpacing: "0.16em" }}>{ref.tag}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--bone)" }}>
                  {ref.id}<span style={{ color: "var(--ash)" }}> · {ref.src}</span>
                </span>
                <span className="mono" style={{ fontSize: 10, color: "var(--spire)" }}>sim {ref.sim.toFixed(2)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Distribution / retain */}
        <div style={{ padding: "12px 22px" }}>
          <div className="field-row">
            <span className="k">DIST</span>
            <span className="v" style={{ color: "var(--fog)" }}>{r(i.distribution)}</span>
          </div>
        </div>
      </div>

      <div className="cls-bar" style={{ marginTop: "auto" }}>{i.classification}</div>
    </div>
  );
};

window.IntelColumn = IntelColumn;
