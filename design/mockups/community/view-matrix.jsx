// view-matrix.jsx — Pairwise community co-occurrence heatmap.
// Companion to the topology view: instead of seeing the shape of overlap,
// you see the magnitudes. 9×9 grid, diagonal = community totals,
// off-diagonal = number of people in BOTH communities.

function MatrixView() {
  const [hover, setHover] = React.useState(null); // {r, c}

  // Pairwise overlap derived from the n-ary intersections.
  // (Approximation — uses the top-16 intersections; real backend would compute exact.)
  function pairwiseOverlap(idA, idB) {
    if (idA === idB) return COMM_BY_ID[idA].count;
    return INTERSECTIONS
      .filter(ix => ix.ids.includes(idA) && ix.ids.includes(idB))
      .reduce((s, ix) => s + ix.count, 0);
  }

  // Build matrix
  const n = COMMUNITIES.length;
  const matrix = COMMUNITIES.map(a =>
    COMMUNITIES.map(b => pairwiseOverlap(a.id, b.id))
  );
  const maxOff = Math.max(...matrix.flatMap((row, i) =>
    row.map((v, j) => i === j ? 0 : v)));

  // Layout: cell 56px, labels 130px, totals row/col
  const cellW = 56, cellH = 38;
  const labelW = 140;
  const labelH = 80;
  const gridW = labelW + n * cellW + 100;   // + side bar
  const gridH = labelH + n * cellH + 30;    // + bottom

  const hovered = hover ? {
    a: COMMUNITIES[hover.r],
    b: COMMUNITIES[hover.c],
    v: matrix[hover.r][hover.c],
  } : null;

  return (
    <div style={{
      width: "100%", height: "100%", display: "flex", flexDirection: "column",
      background: "var(--void)", color: "var(--bone)", overflow: "hidden",
    }}>
      <TopBar route={["Game · DET-070", "Analysis", "Communities", "Co-occurrence"]}/>
      <SubTabs active="matrix" tabs={[
        { id: "upset",    label: "Intersection · UpSet" },
        { id: "topology", label: "Hyperedge Topology" },
        { id: "matrix",   label: "Co-occurrence Matrix" },
        { id: "incidence",label: "Org Incidence" },
      ]}/>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 360px",
        gap: 12, padding: 16, minHeight: 0 }}>

        {/* CENTER — heatmap */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
          <ConstitutionBanner kind="info">
            Pairwise overlap is the projected 2-section of the hypergraph.
            <span style={{ color: "var(--shroud)" }}> Lossy — use UpSet (artboard A) for true intersection cardinalities.</span>
          </ConstitutionBanner>

          <Pane label="Co-occurrence Heatmap" badge="9 × 9 · pairwise · members in both">
            <div style={{ padding: "20px 24px", display: "flex", justifyContent: "center", alignItems: "center", flex: 1 }}>
              <svg viewBox={`0 0 ${gridW} ${gridH}`}
                preserveAspectRatio="xMidYMid meet"
                style={{ display: "block", width: "100%", maxHeight: 640,
                  fontFamily: "var(--font-mono)" }}>

                {/* COLUMN LABELS (top, rotated) */}
                {COMMUNITIES.map((c, j) => (
                  <g key={`col-${c.id}`} transform={`translate(${labelW + j * cellW + cellW/2}, ${labelH - 8})`}>
                    <g transform="rotate(-50)">
                      <text x={0} y={0} fill={hover?.c === j ? "var(--bone)" : "var(--fog)"}
                        fontSize={10} letterSpacing=".08em" fontWeight={hover?.c === j ? 700 : 500}
                        textAnchor="start">
                        {c.label.toUpperCase()}
                      </text>
                    </g>
                    <rect x={-cellW/2 + 8} y={4} width={cellW - 16} height={4}
                      fill={c.color} opacity={hover?.c === j ? 1 : 0.7}/>
                  </g>
                ))}

                {/* ROW LABELS (left) */}
                {COMMUNITIES.map((c, i) => (
                  <g key={`row-${c.id}`}>
                    <rect x={labelW - 18} y={labelH + i*cellH + cellH/2 - 4} width={10} height={8}
                      fill={c.color} opacity={hover?.r === i ? 1 : 0.7}/>
                    <text x={labelW - 24} y={labelH + i*cellH + cellH/2 + 4}
                      fill={hover?.r === i ? "var(--bone)" : "var(--fog)"}
                      fontSize={10} letterSpacing=".08em"
                      fontWeight={hover?.r === i ? 700 : 500} textAnchor="end">
                      {c.label.toUpperCase()}
                    </text>
                  </g>
                ))}

                {/* CELLS */}
                {matrix.map((row, i) => row.map((v, j) => {
                  const isDiag = i === j;
                  const intensity = isDiag ? 1 : (v / maxOff);
                  const isHover = hover && hover.r === i && hover.c === j;
                  const rowHov = hover && (hover.r === i || hover.c === i);
                  const colHov = hover && (hover.c === j || hover.r === j);
                  const inCross = hover && (hover.r === i || hover.c === j);

                  // Mix-color: blend the two community colors for off-diagonal
                  const cA = COMMUNITIES[i].color, cB = COMMUNITIES[j].color;
                  const fill = isDiag ? cA : "var(--spire)";

                  return (
                    <g key={`${i}-${j}`}
                      onMouseEnter={() => setHover({ r: i, c: j })}
                      onMouseLeave={() => setHover(null)}>
                      <rect x={labelW + j*cellW} y={labelH + i*cellH}
                        width={cellW - 2} height={cellH - 2}
                        rx={2}
                        fill={fill}
                        opacity={isDiag ? 0.85 : Math.max(0.04, intensity * 0.7)}
                        stroke={isHover ? "var(--bone)" :
                                inCross ? "var(--wet-steel)" : "transparent"}
                        strokeWidth={isHover ? 1.5 : 0.5}
                        style={{ cursor: "pointer", transition: "stroke .1s" }}/>
                      {/* numeric label on hot cells */}
                      {(intensity > 0.18 || isDiag) && (
                        <text x={labelW + j*cellW + (cellW-2)/2}
                          y={labelH + i*cellH + cellH/2 + 4}
                          fill={isDiag ? "var(--void)" : "var(--bone)"}
                          fontSize={9} fontWeight={600}
                          textAnchor="middle"
                          letterSpacing=".02em"
                          style={{ pointerEvents: "none" }}>
                          {fmtCount(v)}
                        </text>
                      )}
                    </g>
                  );
                }))}

                {/* Diagonal divider line */}
                <line
                  x1={labelW} y1={labelH}
                  x2={labelW + n*cellW} y2={labelH + n*cellH}
                  stroke="var(--wet-steel)" strokeWidth="0.6" opacity={0.4}/>

                {/* Legend strip — bottom */}
                <g transform={`translate(${labelW}, ${labelH + n*cellH + 14})`}>
                  <text x={0} y={0} fill="var(--ash)" fontSize={9}
                    letterSpacing=".22em">OVERLAP MAGNITUDE</text>
                  {Array.from({length: 10}).map((_, i) => (
                    <rect key={i} x={130 + i*16} y={-9} width={14} height={8}
                      fill="var(--spire)" opacity={0.05 + (i/10) * 0.7}/>
                  ))}
                  <text x={130} y={12} fill="var(--shroud)" fontSize={8} letterSpacing=".18em">0</text>
                  <text x={130 + 10*16 - 14} y={12} fill="var(--shroud)" fontSize={8}
                    letterSpacing=".18em" textAnchor="end">{fmtCount(maxOff)}</text>
                </g>
              </svg>
            </div>
          </Pane>
        </div>

        {/* RIGHT RAIL */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <Pane label="Hovered cell" badge={hover ? `${hovered.a.short} × ${hovered.b.short}` : "—"}
            style={{ flexShrink: 0 }}>
            <div style={{ padding: "14px 14px", display: "flex", flexDirection: "column", gap: 12,
              minHeight: 160 }}>
              {hovered ? (
                <>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
                    <CommBadge id={hovered.a.id}/>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--ash)" }}>∩</span>
                    <CommBadge id={hovered.b.id}/>
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 30, fontWeight: 700,
                    color: "var(--bone)", letterSpacing: "-.02em" }}>
                    {fmtCount(hovered.v)}
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)",
                    letterSpacing: ".04em", lineHeight: 1.5 }}>
                    {hovered.a.id === hovered.b.id
                      ? `Total cardinality of the ${hovered.a.short} hyperedge.`
                      : `Members of ${hovered.a.short} who are ALSO in ${hovered.b.short} (or vice versa).`}
                  </div>
                  {hovered.a.id !== hovered.b.id && hovered.v > 0 && (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      <Stat label={`% of ${hovered.a.short}`}
                        value={fmtPct(hovered.v / hovered.a.count, 1)}/>
                      <Stat label={`% of ${hovered.b.short}`}
                        value={fmtPct(hovered.v / hovered.b.count, 1)}/>
                    </div>
                  )}
                </>
              ) : (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--shroud)",
                  letterSpacing: ".06em", fontStyle: "italic" }}>
                  Hover a cell to see the pairwise overlap.
                </div>
              )}
            </div>
          </Pane>

          <Pane label="Top pairs" badge="rank · overlap desc">
            <div style={{ padding: "8px 10px", display: "flex", flexDirection: "column", gap: 4 }}>
              {(() => {
                const pairs = [];
                for (let i = 0; i < n; i++)
                  for (let j = i+1; j < n; j++)
                    if (matrix[i][j] > 0)
                      pairs.push({ a: COMMUNITIES[i], b: COMMUNITIES[j], v: matrix[i][j] });
                pairs.sort((x,y) => y.v - x.v);
                return pairs.slice(0, 8).map((p, i) => (
                  <div key={i} style={{ display: "grid",
                    gridTemplateColumns: "auto auto auto 1fr auto",
                    alignItems: "center", gap: 6,
                    padding: "4px 6px",
                    fontFamily: "var(--font-mono)", fontSize: 10,
                    background: "var(--tar)", borderRadius: 2,
                    border: "1px solid var(--rebar)" }}>
                    <span style={{ width: 7, height: 7, background: p.a.color,
                      boxShadow: `0 0 5px ${p.a.color}` }}/>
                    <span style={{ color: "var(--bone)", letterSpacing: ".06em" }}>
                      {p.a.short}
                    </span>
                    <span style={{ width: 7, height: 7, background: p.b.color,
                      boxShadow: `0 0 5px ${p.b.color}` }}/>
                    <span style={{ color: "var(--bone)", letterSpacing: ".06em" }}>
                      {p.b.short}
                    </span>
                    <span style={{ color: "var(--bone)", fontWeight: 600,
                      textAlign: "right", letterSpacing: ".02em" }}>
                      {fmtCount(p.v)}
                    </span>
                  </div>
                ));
              })()}
            </div>
          </Pane>

          <Pane label="Reading note" style={{ flex: 1, minHeight: 0 }}>
            <div style={{ padding: "10px 12px", fontFamily: "var(--font-mono)", fontSize: 10,
              color: "var(--fog)", lineHeight: 1.6, letterSpacing: ".02em" }}>
              <p style={{ marginBottom: 8 }}>
                Diagonal cells = total community cardinality.
              </p>
              <p style={{ marginBottom: 8 }}>
                Off-diagonal = pairwise intersection. Symmetric: <span style={{ color: "var(--bone)" }}>M[i][j] = M[j][i]</span>.
              </p>
              <p style={{ marginBottom: 8 }}>
                Matrices lose information about <em>triple</em> intersections — two people in
                <span style={{ color: COMM_BY_ID["WORKING"].color }}> WRK</span>
                <span style={{ color: COMM_BY_ID["WOMEN"].color }}>∩WMN</span> may or may not also be in
                <span style={{ color: COMM_BY_ID["NEW_AFRIKAN"].color }}> NAF</span>. UpSet preserves that.
              </p>
              <p style={{ color: "var(--ash)", fontStyle: "italic" }}>
                Use this view for quick magnitude scans, UpSet for structure.
              </p>
            </div>
          </Pane>
        </div>
      </div>
    </div>
  );
}
