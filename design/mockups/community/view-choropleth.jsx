// view-choropleth.jsx — Community lens on the hex map.
// Article VIII.9: choropleth by dominant composition is one of the THREE
// legitimate ways to spatially-render hyperedge data.
// (The other two: inspector badges, UpSet plots — see sibling views.)
// NOT permitted: spatial hulls / convex envelopes around community members.

// Per-hex community composition: project the region archetype onto each hex,
// add deterministic per-hex noise so the map has texture but stays legible.
function buildHexCompositions() {
  // we reuse the existing HEXES global from map-data.jsx
  return HEXES.map((h, i) => {
    const region = REGION_COMPOSITION[h.region_id];
    if (!region) return { ...h, comp: {}, dominant: "WORKING", dominant_share: 0.4 };
    // mild noise — but seeded by hex id so it's stable
    const rng = ((i * 2654435761) % 1000) / 1000;
    const rng2 = ((i * 1597463007) % 1000) / 1000;
    const noise = 0.08;
    const comp = {};
    for (const [id, base] of Object.entries(region.mix)) {
      const shifted = base + (rng - 0.5) * noise + (rng2 - 0.5) * noise * 0.7;
      comp[id] = Math.max(0.005, shifted);
    }
    // determine dominant by highest share among non-cross-cutting communities
    // (Settler/Working/Women cross-cut every region; we use "national identity" as dominant)
    // Allow ALL communities to compete for "dominant" to honor the data.
    const entries = Object.entries(comp).sort((a, b) => b[1] - a[1]);
    return { ...h, comp, dominant: entries[0][0], dominant_share: entries[0][1] };
  });
}

function ChoroplethView() {
  const [lens, setLens] = React.useState("dominant"); // dominant | settler | new_afrikan | working | indigenous
  const [hoveredHex, setHoveredHex] = React.useState(null);
  const hexes = React.useMemo(buildHexCompositions, []);

  const VIEWBOX = "0 0 900 500";

  // Color picker per hex based on lens
  function hexColor(h) {
    if (lens === "dominant") {
      const c = COMM_BY_ID[h.dominant];
      const opacity = 0.35 + (h.dominant_share - 0.2) * 1.5; // luminosity = magnitude
      return { fill: c.color, opacity: Math.max(0.2, Math.min(1, opacity)) };
    } else {
      // Single-community lens: intensity scaled by that community's share
      const share = h.comp[lens.toUpperCase()] ?? 0;
      const c = COMM_BY_ID[lens.toUpperCase()];
      return { fill: c.color, opacity: Math.max(0.06, share) };
    }
  }

  const hovered = hoveredHex && hexes.find(h => h.id === hoveredHex);

  return (
    <div style={{
      width: "100%", height: "100%", display: "flex", flexDirection: "column",
      background: "var(--void)", color: "var(--bone)", overflow: "hidden",
    }}>
      <TopBar route={["Game · DET-070", "Briefing", "Map", "Community Lens"]}/>
      <SubTabs active="comm" tabs={[
        { id: "stance",   label: "Stance" },
        { id: "heat",     label: "Heat" },
        { id: "wealth",   label: "Wealth" },
        { id: "comm",     label: "Community" },
      ]}/>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 320px",
        gap: 12, padding: 16, minHeight: 0 }}>

        {/* MAP */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
          <ConstitutionBanner>
            Dominant <em style={{ color: "var(--bone)", fontStyle: "normal" }}>composition</em> projected
            to hexes. <span style={{ color: "var(--shroud)" }}>Communities are not hulls; this is a marginal projection.</span>
          </ConstitutionBanner>

          <Pane label="Continental US · dominant community per hex" badge={`${hexes.length} hexes · lens: ${lens}`}
            style={{ flex: 1, minHeight: 0 }}>
            <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
              <svg viewBox={VIEWBOX} preserveAspectRatio="xMidYMid meet"
                style={{ display: "block", width: "100%", height: "100%" }}>
                {/* state outlines */}
                {US_REGIONS.map(r => (
                  <polygon key={r.id} points={r.poly}
                    fill="none" stroke="var(--rebar)" strokeWidth="0.6"/>
                ))}
                {/* hex tiles */}
                {hexes.map(h => {
                  const { fill, opacity } = hexColor(h);
                  const isHov = hoveredHex === h.id;
                  return (
                    <polygon key={h.id} points={h.points}
                      fill={fill} opacity={opacity}
                      stroke={isHov ? "var(--bone)" : "var(--void)"}
                      strokeWidth={isHov ? 1.5 : 0.4}
                      onMouseEnter={() => setHoveredHex(h.id)}
                      onMouseLeave={() => setHoveredHex(null)}
                      style={{ cursor: "pointer", transition: "stroke .15s" }}/>
                  );
                })}
                {/* city markers */}
                {CITIES.map(c => (
                  <g key={c.name}>
                    <circle cx={c.x} cy={c.y} r={2.5} fill="var(--void)"
                      stroke="var(--bone)" strokeWidth="0.8"/>
                    <text x={c.x + 5} y={c.y + 3} fill="var(--fog)" fontSize={7.5}
                      fontFamily="var(--font-mono)" letterSpacing=".12em">
                      {c.name.toUpperCase()}
                    </text>
                  </g>
                ))}
              </svg>

              {/* hover detail floating */}
              {hovered && (
                <div style={{
                  position: "absolute", bottom: 12, left: 12,
                  padding: "10px 12px", background: "rgba(13,16,22,.95)",
                  border: "1px solid var(--wet-steel)", borderRadius: 4,
                  fontFamily: "var(--font-mono)", fontSize: 10, minWidth: 220,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ color: "var(--fog)", letterSpacing: ".16em" }}>HEX {hovered.id}</span>
                    <span style={{ color: "var(--ash)" }}>{hovered.region_name || hovered.region_id}</span>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    {Object.entries(hovered.comp)
                      .sort((a,b) => b[1] - a[1])
                      .slice(0, 5)
                      .map(([id, s]) => (
                        <div key={id} style={{ display: "grid", gridTemplateColumns: "10px 1fr 50px 40px",
                          gap: 6, alignItems: "center" }}>
                          <span style={{ width: 8, height: 8, background: COMM_BY_ID[id].color,
                            boxShadow: `0 0 6px ${COMM_BY_ID[id].color}` }}/>
                          <span style={{ color: "var(--bone)", letterSpacing: ".06em" }}>
                            {COMM_BY_ID[id].label}
                          </span>
                          <div style={{ height: 4, background: "var(--tar)", borderRadius: 1 }}>
                            <div style={{ width: `${s*100}%`, height: "100%",
                              background: COMM_BY_ID[id].color, opacity: 0.75 }}/>
                          </div>
                          <span style={{ color: "var(--bone)", textAlign: "right", letterSpacing: ".04em" }}>
                            {fmtPct(s, 0)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </Pane>
        </div>

        {/* RIGHT RAIL */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <Pane label="Lens" badge="single community" style={{ flexShrink: 0 }}>
            <div style={{ padding: "8px 10px", display: "flex", flexDirection: "column", gap: 4 }}>
              <LensRow id="dominant" label="Dominant composition" active={lens} onClick={setLens}
                hint="luminosity = strength of dominance"/>
              {["NEW_AFRIKAN","CHICANO","INDIGENOUS","SETTLER","WORKING","LABOR_ARIST"].map(id => (
                <LensRow key={id} id={id.toLowerCase()} label={COMM_BY_ID[id].label}
                  swatch={COMM_BY_ID[id].color} active={lens} onClick={setLens}
                  hint={`share of ${COMM_BY_ID[id].short}`}/>
              ))}
            </div>
          </Pane>

          <Pane label="Dominant — distribution" badge="hex count">
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
              {(() => {
                const buckets = {};
                hexes.forEach(h => { buckets[h.dominant] = (buckets[h.dominant]||0) + 1; });
                const total = hexes.length;
                return Object.entries(buckets)
                  .sort((a,b) => b[1] - a[1])
                  .map(([id, n]) => (
                    <div key={id} style={{ display: "grid", gridTemplateColumns: "12px 80px 1fr 26px",
                      alignItems: "center", gap: 8, fontFamily: "var(--font-mono)", fontSize: 10 }}>
                      <span style={{ width: 8, height: 8, background: COMM_BY_ID[id].color,
                        boxShadow: `0 0 6px ${COMM_BY_ID[id].color}` }}/>
                      <span style={{ color: "var(--bone)", letterSpacing: ".06em" }}>
                        {COMM_BY_ID[id].label}
                      </span>
                      <div style={{ height: 6, background: "var(--tar)", borderRadius: 1 }}>
                        <div style={{ width: `${n/total*100}%`, height: "100%",
                          background: COMM_BY_ID[id].color, opacity: 0.75 }}/>
                      </div>
                      <span style={{ color: "var(--bone)", textAlign: "right", letterSpacing: ".02em" }}>
                        {n}
                      </span>
                    </div>
                  ));
              })()}
            </div>
          </Pane>

          <Pane label="Why not hulls?" style={{ flex: 1, minHeight: 0 }}>
            <div style={{ padding: "10px 12px", fontFamily: "var(--font-mono)", fontSize: 10,
              color: "var(--fog)", lineHeight: 1.6, letterSpacing: ".02em" }}>
              <p style={{ marginBottom: 8 }}>
                A community is an n-ary set, not a region. Drawing a hull around its members
                conflates <span style={{ color: "var(--bone)" }}>membership</span> with
                <span style={{ color: "var(--bone)" }}> territory</span>.
              </p>
              <p style={{ marginBottom: 8 }}>
                Two members of <span style={{ color: COMM_BY_ID["NEW_AFRIKAN"].color }}>NEW_AFRIKAN</span> in
                Detroit and Atlanta belong to one hyperedge — but the land between them does not.
              </p>
              <p style={{ color: "var(--ash)", fontStyle: "italic" }}>
                — Const. Art. VIII.9
              </p>
            </div>
          </Pane>
        </div>
      </div>
    </div>
  );
}

function LensRow({ id, label, hint, swatch, active, onClick }) {
  const isActive = active === id;
  return (
    <div onClick={() => onClick(id)} style={{
      display: "grid", gridTemplateColumns: "12px 1fr auto",
      alignItems: "center", gap: 8, padding: "7px 8px",
      background: isActive ? "rgba(77,217,230,.07)" : "var(--tar)",
      border: `1px solid ${isActive ? "var(--spire)" : "var(--rebar)"}`,
      borderRadius: 3, cursor: "pointer",
    }}>
      <span style={{ width: 8, height: 8, background: swatch || "var(--bone)",
        boxShadow: swatch ? `0 0 6px ${swatch}` : "none", borderRadius: 1 }}/>
      <div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10,
          color: isActive ? "var(--spire)" : "var(--bone)",
          fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase" }}>
          {label}
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9,
          color: "var(--shroud)", letterSpacing: ".04em" }}>
          {hint}
        </div>
      </div>
      {isActive && <span style={{ color: "var(--spire)",
        fontFamily: "var(--font-mono)", fontSize: 11 }}>●</span>}
    </div>
  );
}
