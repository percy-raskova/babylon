// Topology.jsx — full-screen network view
const Topology = ({ onBack }) => {
  const nodes = [
    { id: "WCLF", x: 280, y: 140, r: 28, c: "var(--spire)",      label: "WCLF" },
    { id: "DTC",  x: 440, y: 100, r: 22, c: "var(--solidarity)", label: "DTC" },
    { id: "DFB",  x: 480, y: 220, r: 18, c: "var(--solidarity)", label: "DFB" },
    { id: "DEAR", x: 160, y: 240, r: 16, c: "var(--solidarity)", label: "DEAR" },
    { id: "UAW",  x: 140, y: 100, r: 24, c: "var(--rupture)",    label: "UAW" },
    { id: "WCSD", x: 580, y: 320, r: 26, c: "var(--heat)",       label: "WCSD" },
    { id: "FORD", x: 700, y: 160, r: 32, c: "var(--laser)",      label: "FORD" },
    { id: "FCA",  x: 660, y: 280, r: 28, c: "var(--laser)",      label: "FCA" },
    { id: "PROL", x: 320, y: 360, r: 36, c: "var(--cadre)",      label: "PROLETARIAT" },
    { id: "LUMP", x: 480, y: 400, r: 24, c: "var(--population)", label: "LUMPEN" },
  ];
  const edges = [
    { a: "WCLF", b: "DTC",  type: "SOLIDARITY",   c: "var(--solidarity)" },
    { a: "WCLF", b: "DFB",  type: "SOLIDARITY",   c: "var(--solidarity)" },
    { a: "WCLF", b: "DEAR", type: "SOLIDARITY",   c: "var(--solidarity)" },
    { a: "WCLF", b: "UAW",  type: "TENSION",      c: "var(--heat)" },
    { a: "WCLF", b: "PROL", type: "REPRESENTS",   c: "var(--cadre)" },
    { a: "FORD", b: "PROL", type: "EXPLOITATION", c: "var(--laser)" },
    { a: "FCA",  b: "PROL", type: "EXPLOITATION", c: "var(--laser)" },
    { a: "FORD", b: "LUMP", type: "EXPLOITATION", c: "var(--laser)" },
    { a: "WCSD", b: "WCLF", type: "REPRESSION",   c: "var(--heat)" },
    { a: "WCSD", b: "PROL", type: "REPRESSION",   c: "var(--heat)" },
    { a: "FORD", b: "WCSD", type: "TRIBUTE",      c: "var(--rupture)" },
    { a: "PROL", b: "LUMP", type: "ADJACENCY",    c: "var(--shroud)" },
  ];
  const map = Object.fromEntries(nodes.map(n => [n.id, n]));
  return (
    <div style={{ height: "100vh", background: "var(--void)", color: "var(--bone)", display: "flex", flexDirection: "column", fontFamily: "var(--font-sans)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 20px", borderBottom: "1px solid var(--rebar)" }}>
        <button onClick={onBack} style={{ background: "transparent", border: "1px solid var(--wet-steel)", borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>← Cockpit</button>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: ".22em", color: "var(--spire)", textTransform: "uppercase" }}>▸ Topology · Wayne County</div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: ".1em" }}>{nodes.length} nodes · {edges.length} edges</div>
      </div>
      <div style={{ flex: 1, padding: 20, position: "relative" }}>
        <svg width="100%" height="100%" viewBox="0 0 840 480" style={{ display: "block" }}>
          {edges.map((e, i) => {
            const A = map[e.a], B = map[e.b];
            return <line key={i} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={e.c} strokeWidth={1.4} strokeOpacity={.55} strokeDasharray={e.type === "ADJACENCY" ? "3 4" : "0"}/>;
          })}
          {nodes.map(n => (
            <g key={n.id}>
              <circle cx={n.x} cy={n.y} r={n.r} fill={n.c} fillOpacity={.18} stroke={n.c} strokeWidth={1.5}/>
              <text x={n.x} y={n.y+4} textAnchor="middle" fill={n.c} fontSize={9} fontFamily="var(--font-mono)" letterSpacing=".1em">{n.label}</text>
            </g>
          ))}
        </svg>
        <div style={{ position: "absolute", top: 24, right: 28, background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 12, minWidth: 180 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase", marginBottom: 8 }}>Edge Types</div>
          {[
            ["SOLIDARITY","var(--solidarity)"],["EXPLOITATION","var(--laser)"],
            ["REPRESSION","var(--heat)"],["TENSION","var(--heat)"],
            ["TRIBUTE","var(--rupture)"],["REPRESENTS","var(--cadre)"],
            ["ADJACENCY","var(--shroud)"],
          ].map(([k, c]) => (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)", padding: "3px 0" }}>
              <span style={{ width: 16, height: 1.5, background: c }}/>{k}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
window.Topology = Topology;
