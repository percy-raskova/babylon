// view-topology.jsx — Topological hypergraph view with BubbleSets-style hulls.
//
// In TOPOLOGICAL mode (positions chosen for legibility, not geography),
// hyperedge hulls ARE legitimate — see the frontend-reset doc:
//   "Cytoscape.js for graph views (dyadic + BubbleSets for hyperedge hulls
//    in topological mode). deck.gl + MapLibre for geographic views. Don't mix."
//
// What Article VIII.9 forbids is hulls on the MAP. Here, positions are chosen
// to make set-structure legible — INCARCERATED appears as TWO disconnected
// blobs precisely to show that hyperedges are NOT spatial.

// ─────────────────────────────────────────────────────────────
// LAYOUT — supercells positioned by hand for legible topology.
// Each supercell represents an intersection-class; n = number of mini-dots
// (each dot ≈ tens of thousands of people).
// ─────────────────────────────────────────────────────────────
const TOPO_CELLS = [
  // Labor-aristocracy cluster (upper-left, separated from labor solidarity)
  { id: "C01", members: ["SETTLER","LABOR_ARIST","WOMEN"],         cx: 220, cy: 110, n: 10, count: 296000, salient: true },
  { id: "C02", members: ["SETTLER","LABOR_ARIST"],                 cx: 140, cy: 175, n:  9, count: 268000 },
  { id: "C03", members: ["SETTLER","LABOR_ARIST","WORKING"],       cx: 270, cy: 195, n:  6, count: 142000 },

  // Settler labor core (left-center)
  { id: "C04", members: ["SETTLER","WORKING","WOMEN"],             cx: 290, cy: 285, n: 14, count: 412000 },
  { id: "C05", members: ["SETTLER","WORKING"],                     cx: 230, cy: 355, n: 12, count: 388000 },
  { id: "C06", members: ["SETTLER","WORKING","QUEER"],             cx: 200, cy: 435, n:  5, count:  46000 },

  // The bridge — WORKING ∩ WOMEN cross-cutting
  { id: "C07", members: ["WORKING","WOMEN"],                       cx: 410, cy: 295, n:  9, count: 174000 },

  // NEW_AFRIKAN cluster (right-of-center)
  { id: "C08", members: ["WORKING","WOMEN","NEW_AFRIKAN"],         cx: 540, cy: 285, n:  9, count: 182000, salient: true },
  { id: "C09", members: ["WORKING","NEW_AFRIKAN"],                 cx: 590, cy: 220, n:  7, count: 108000 },
  { id: "C10", members: ["WORKING","NEW_AFRIKAN","INCARCERATED"],  cx: 670, cy: 165, n:  3, count:  22000, salient: true },
  { id: "C11", members: ["WORKING","NEW_AFRIKAN","QUEER"],         cx: 600, cy: 380, n:  3, count:  17000 },

  // CHICANO cluster (far right)
  { id: "C12", members: ["WORKING","CHICANO"],                     cx: 730, cy: 260, n:  6, count:  92000 },
  { id: "C13", members: ["WORKING","WOMEN","CHICANO"],             cx: 690, cy: 335, n:  7, count: 124000 },

  // QUEER lower band
  { id: "C14", members: ["WORKING","WOMEN","QUEER"],               cx: 470, cy: 435, n:  4, count:  58000 },

  // INDIGENOUS — far left, isolated; INCARCERATED reappears here to
  // demonstrate the hyperedge is NOT spatial (two distant blobs, one set).
  { id: "C15", members: ["WOMEN","INDIGENOUS"],                    cx: 130, cy: 460, n:  4, count:  21000 },
  { id: "C16", members: ["INDIGENOUS","INCARCERATED"],             cx:  72, cy: 515, n:  1, count:   4200, salient: true },
];

// Expand each supercell to its individual member dots (deterministic).
function expandTopoDots() {
  const dots = [];
  TOPO_CELLS.forEach(c => {
    const seed = c.id.charCodeAt(2) * 13;
    for (let i = 0; i < c.n; i++) {
      // Spiral scatter — keeps dots clustered around centroid
      const a = (i * 2.3998) + seed * 0.01;       // golden-angle
      const r = 4 + Math.sqrt(i) * 5.2;
      dots.push({
        cellId: c.id,
        members: c.members,
        x: c.cx + Math.cos(a) * r,
        y: c.cy + Math.sin(a) * r,
      });
    }
  });
  return dots;
}

function TopologyView() {
  const [activeComm, setActiveComm] = React.useState(null);   // hover/select community
  const [activeCell, setActiveCell] = React.useState("C04");  // selected cell
  const dots = React.useMemo(expandTopoDots, []);

  const cellById = Object.fromEntries(TOPO_CELLS.map(c => [c.id, c]));
  const selected = cellById[activeCell];

  // Communities present in this scenario, sorted by count desc
  const commList = COMMUNITIES.slice().sort((a,b) => b.count - a.count);

  const VW = 880, VH = 580;

  return (
    <div style={{
      width: "100%", height: "100%", display: "flex", flexDirection: "column",
      background: "var(--void)", color: "var(--bone)", overflow: "hidden",
    }}>
      <TopBar route={["Game · DET-070", "Analysis", "Communities", "Topology"]}/>
      <SubTabs active="topology" tabs={[
        { id: "upset",    label: "Intersection · UpSet" },
        { id: "topology", label: "Hyperedge Topology" },
        { id: "matrix",   label: "Co-occurrence Matrix" },
        { id: "incidence",label: "Org Incidence" },
      ]}/>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "260px 1fr 320px",
        gap: 12, padding: 16, minHeight: 0 }}>

        {/* LEFT RAIL — hyperedge legend with isolate toggles */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <Pane label="Hyperedges" badge={`${commList.length} · click to isolate`}>
            <div style={{ padding: "8px 8px", display: "flex", flexDirection: "column", gap: 4,
              overflow: "auto" }}>
              {commList.map(c => {
                const isActive = activeComm === c.id;
                const inSelected = selected && selected.members.includes(c.id);
                return (
                  <div key={c.id}
                    onMouseEnter={() => setActiveComm(c.id)}
                    onMouseLeave={() => setActiveComm(null)}
                    style={{
                      display: "grid", gridTemplateColumns: "auto 1fr auto",
                      gap: 8, alignItems: "center",
                      padding: "6px 8px", borderRadius: 3, cursor: "pointer",
                      background: isActive ? `${c.color}18` : "var(--tar)",
                      border: `1px solid ${isActive ? c.color : inSelected ? c.color + "55" : "var(--rebar)"}`,
                    }}>
                    <span style={{
                      width: 14, height: 14, borderRadius: 9999,
                      background: c.color,
                      boxShadow: `0 0 14px ${c.color}, inset 0 0 6px rgba(0,0,0,.3)`,
                    }}/>
                    <div>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10,
                        color: "var(--bone)", letterSpacing: ".08em",
                        textTransform: "uppercase", fontWeight: 600 }}>
                        {c.label}
                      </div>
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 9,
                        color: "var(--shroud)", letterSpacing: ".18em" }}>
                        {fmtCount(c.count)} · {c.id}
                      </div>
                    </div>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 11,
                      color: isActive ? c.color : "var(--shroud)",
                      letterSpacing: ".04em" }}>
                      {(() => {
                        const n = TOPO_CELLS.filter(t => t.members.includes(c.id)).length;
                        return n;
                      })()}
                    </span>
                  </div>
                );
              })}
            </div>
          </Pane>

          <Pane label="Topology · stats" style={{ flexShrink: 0 }}>
            <div style={{ padding: "8px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
              <FilterRow label="Cells (intersection classes)" value={String(TOPO_CELLS.length)}/>
              <FilterRow label="Dots (sub-populations)" value={String(dots.length)}/>
              <FilterRow label="Disconnected components" value="6" />
              <FilterRow label="Layout" value="hand · legibility" />
              <FilterRow label="Method" value="BubbleSets · metaball" muted/>
            </div>
          </Pane>
        </div>

        {/* CENTER — BubbleSets canvas */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
          <ConstitutionBanner kind="info">
            Topological mode: hyperedge hulls are <em style={{ color: "var(--bone)", fontStyle: "normal" }}>permitted</em>.
            <span style={{ color: "var(--shroud)" }}> Positions chosen for set-structure legibility — not geography. INCARCERATED appears twice; the hyperedge is one set.</span>
          </ConstitutionBanner>

          <Pane label="Hypergraph · BubbleSets" badge="XGI · tick 042"
            style={{ flex: 1, minHeight: 0 }}>
            <div style={{ flex: 1, position: "relative", overflow: "hidden",
              background: "radial-gradient(ellipse at 50% 50%, rgba(20,28,38,.5) 0%, var(--void) 80%)" }}>
              <svg viewBox={`0 0 ${VW} ${VH}`} preserveAspectRatio="xMidYMid meet"
                style={{ display: "block", width: "100%", height: "100%" }}>
                <defs>
                  {/* Metaball filter — blurs then thresholds alpha so member dots merge into a smooth hull */}
                  <filter id="goo" x="-10%" y="-10%" width="120%" height="120%">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="11"/>
                    <feColorMatrix values="
                      1 0 0 0 0
                      0 1 0 0 0
                      0 0 1 0 0
                      0 0 0 18 -8"/>
                  </filter>
                  {/* Outline filter — thinner blob outline */}
                  <filter id="goo-outline" x="-10%" y="-10%" width="120%" height="120%">
                    <feGaussianBlur in="SourceGraphic" stdDeviation="11"/>
                    <feColorMatrix values="
                      1 0 0 0 0
                      0 1 0 0 0
                      0 0 1 0 0
                      0 0 0 26 -13"/>
                  </filter>
                  {/* Drop shadow for dots */}
                  <filter id="dot-glow">
                    <feGaussianBlur stdDeviation="1"/>
                  </filter>
                </defs>

                {/* Background grid — subtle, not chartjunk */}
                <g opacity={0.06}>
                  {Array.from({length: 12}).map((_, i) => (
                    <line key={`v${i}`} x1={i*80} x2={i*80} y1={0} y2={VH} stroke="var(--wet-steel)" strokeWidth="0.5"/>
                  ))}
                  {Array.from({length: 8}).map((_, i) => (
                    <line key={`h${i}`} x1={0} x2={VW} y1={i*80} y2={i*80} stroke="var(--wet-steel)" strokeWidth="0.5"/>
                  ))}
                </g>

                {/* HULLS — one per community, metaball over its member dots.
                    Stacked with mix-blend-mode: screen so overlaps brighten. */}
                {commList.map(c => {
                  const memberDots = dots.filter(d => d.members.includes(c.id));
                  const isActive = activeComm === c.id;
                  const isDim = activeComm && activeComm !== c.id;
                  const blobR = 24;
                  return (
                    <g key={`hull-${c.id}`}
                      style={{ mixBlendMode: "screen",
                        opacity: isDim ? 0.16 : 1,
                        transition: "opacity .2s" }}>
                      <g filter="url(#goo)" opacity={isActive ? 0.85 : 0.6}>
                        {memberDots.map((d, i) => (
                          <circle key={i} cx={d.x} cy={d.y} r={blobR} fill={c.color}/>
                        ))}
                      </g>
                    </g>
                  );
                })}

                {/* HULL OUTLINES — thin stroked rings, only for active community, helps identify */}
                {activeComm && (() => {
                  const c = COMM_BY_ID[activeComm];
                  const memberDots = dots.filter(d => d.members.includes(activeComm));
                  return (
                    <g style={{ mixBlendMode: "screen", opacity: 0.9 }}>
                      <g filter="url(#goo-outline)">
                        {memberDots.map((d, i) => (
                          <circle key={i} cx={d.x} cy={d.y} r={24} fill="none"
                            stroke={c.color} strokeWidth="3"/>
                        ))}
                      </g>
                    </g>
                  );
                })()}

                {/* Member dots — each sub-population. Colored by primary (first) membership;
                    multi-membership shown by stacked rings */}
                {dots.map((d, i) => {
                  const isHovered = selected && selected.id === d.cellId;
                  return (
                    <g key={i} style={{ pointerEvents: "none" }}>
                      {/* Outer halo if part of hovered community */}
                      {activeComm && d.members.includes(activeComm) && (
                        <circle cx={d.x} cy={d.y} r={5}
                          fill="none" stroke={COMM_BY_ID[activeComm].color}
                          strokeWidth="1.2" opacity={0.9}/>
                      )}
                      <circle cx={d.x} cy={d.y} r={2.2}
                        fill={isHovered ? "var(--bone)" : "var(--bone)"}
                        opacity={isHovered ? 1 : 0.85}/>
                    </g>
                  );
                })}

                {/* Cell labels — only for salient cells, otherwise too noisy */}
                {TOPO_CELLS.filter(c => c.salient).map(c => {
                  const isSel = c.id === activeCell;
                  return (
                    <g key={`lbl-${c.id}`}>
                      <line x1={c.cx} y1={c.cy} x2={c.cx + 26} y2={c.cy - 36}
                        stroke="var(--fog)" strokeWidth="0.6" opacity={0.6}/>
                      <rect x={c.cx + 22} y={c.cy - 50} width={c.members.length * 22 + 30}
                        height={20} fill="rgba(13,16,22,.92)"
                        stroke={isSel ? "var(--spire)" : "var(--rebar)"} strokeWidth="0.8"
                        rx={2}/>
                      <text x={c.cx + 28} y={c.cy - 36} fill="var(--bone)" fontSize={8.5}
                        fontFamily="var(--font-mono)" letterSpacing=".08em">
                        {c.members.map(m => COMM_BY_ID[m].short).join("∩")}
                      </text>
                      <text x={c.cx + 28} y={c.cy - 24} fill="var(--shroud)" fontSize={7}
                        fontFamily="var(--font-mono)" letterSpacing=".18em">
                        {fmtCount(c.count)}
                      </text>
                    </g>
                  );
                })}

                {/* Clickable cell zones — invisible larger hit area per supercell */}
                {TOPO_CELLS.map(c => (
                  <circle key={`hit-${c.id}`} cx={c.cx} cy={c.cy}
                    r={Math.max(18, 6 + Math.sqrt(c.n) * 6)}
                    fill="transparent"
                    onClick={() => setActiveCell(c.id)}
                    style={{ cursor: "pointer" }}/>
                ))}

                {/* Selected cell ring */}
                {selected && (
                  <circle cx={selected.cx} cy={selected.cy}
                    r={Math.max(20, 8 + Math.sqrt(selected.n) * 6)}
                    fill="none" stroke="var(--spire)" strokeWidth="1.5"
                    strokeDasharray="3 3" opacity={0.85}
                    style={{ pointerEvents: "none" }}/>
                )}

                {/* Two-blob teaching annotation — connects the two INCARCERATED zones
                    to drive home that hyperedges aren't spatial */}
                <g opacity={0.55} style={{ pointerEvents: "none" }}>
                  <line x1={670} y1={165} x2={72} y2={515}
                    stroke={COMM_BY_ID.INCARCERATED.color}
                    strokeWidth="0.8" strokeDasharray="2 6"/>
                  <text x={380} y={345} fill={COMM_BY_ID.INCARCERATED.color}
                    fontSize={9} fontFamily="var(--font-mono)" letterSpacing=".18em"
                    transform="rotate(33 380 345)">
                    one hyperedge, two locations
                  </text>
                </g>
              </svg>
            </div>
          </Pane>
        </div>

        {/* RIGHT RAIL — selected cell + comparison */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <Pane label="Selected Cell" badge={selected?.id ?? "—"} style={{ flexShrink: 0 }}>
            {selected && (
              <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: 12 }}>
                <div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
                    letterSpacing: ".22em", marginBottom: 6 }}>INTERSECTION</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {selected.members.map((id, i) => (
                      <React.Fragment key={id}>
                        <CommBadge id={id} dense/>
                        {i < selected.members.length-1 && (
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12,
                            color: "var(--ash)", alignSelf: "center", padding: "0 2px" }}>∩</span>
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <Stat label="Members" value={fmtCount(selected.count)} sub="cells × pop"/>
                  <Stat label="Arity" value={String(selected.members.length)} sub="n-ary edge"/>
                </div>

                {selected.salient && (
                  <div style={{
                    padding: "8px 10px", background: "rgba(212,160,44,.06)",
                    border: "1px solid rgba(212,160,44,.22)", borderRadius: 3,
                    fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)",
                    lineHeight: 1.5, letterSpacing: ".02em",
                  }}>
                    <div style={{ color: "var(--rupture)", fontSize: 9, letterSpacing: ".22em", marginBottom: 4 }}>
                      SALIENT
                    </div>
                    Politically significant intersection — high cadre yield per member.
                  </div>
                )}
              </div>
            )}
          </Pane>

          <Pane label="Topological vs Geographic" style={{ flexShrink: 0 }}>
            <div style={{ padding: "10px 12px", fontFamily: "var(--font-mono)", fontSize: 10,
              color: "var(--fog)", lineHeight: 1.55, letterSpacing: ".02em" }}>
              <p style={{ marginBottom: 8 }}>
                <span style={{ color: "var(--solidarity)", letterSpacing: ".18em" }}>✓ TOPOLOGICAL </span>
                positions chosen for legibility — hulls allowed.
              </p>
              <p style={{ marginBottom: 8 }}>
                <span style={{ color: "var(--laser)", letterSpacing: ".18em" }}>× GEOGRAPHIC </span>
                positions forced by lat/long — hulls forbidden (Art. VIII.9).
              </p>
              <p style={{ color: "var(--shroud)" }}>
                See artboard B for the geographic rendering: choropleth by dominant composition, never hulls.
              </p>
            </div>
          </Pane>

          <Pane label="Anti-pattern check" style={{ flex: 1, minHeight: 0 }}>
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
              <AntiPatternRow ok={true}  label="No pairwise org→member edges"/>
              <AntiPatternRow ok={true}  label="No spatial hulls (geographic view)"/>
              <AntiPatternRow ok={true}  label="Hulls only in topological mode"/>
              <AntiPatternRow ok={true}  label="Disjoint hyperedge component shown"/>
              <AntiPatternRow ok={true}  label="Hulls drawn via XGI, not collapsed to NetworkX"/>
            </div>
          </Pane>
        </div>
      </div>
    </div>
  );
}
