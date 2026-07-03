// view-upset.jsx — UpSet plot for community hyperedge intersection analysis.
// Article VIII.9 prescribes this as the legitimate analytic rendering of
// the hypergraph. Lives at /games/:id/analysis · Communities sub-tab.

function UpsetView() {
  const [selectedIx, setSelectedIx] = React.useState(0); // index into INTERSECTIONS
  const [hoverIx, setHoverIx] = React.useState(null);
  const [hoveredCommunity, setHoveredCommunity] = React.useState(null);

  // Visible intersections (the top 16; data already sorted desc by count)
  const visible = INTERSECTIONS.slice(0, 16);
  const maxIxCount = Math.max(...visible.map(x => x.count));
  const maxCommCount = Math.max(...COMMUNITIES.map(c => c.count));
  const activeIx = hoverIx ?? selectedIx;

  // ── SVG geometry ──────────────────────────────────────────
  const W = 824, H = 520;
  const labelW = 110, totalsW = 96;             // left strip
  const leftPad = 12;
  const matrixX = leftPad + labelW + totalsW;   // 218
  const colW = 36;
  const rowH = 26;
  const matrixW = visible.length * colW;        // 576
  const topBarsY = 18;
  const topBarsH = 152;
  const matrixY = topBarsY + topBarsH + 28;     // 198
  const matrixH = COMMUNITIES.length * rowH;    // 234
  const dotR = 6;

  const xForCol = i => matrixX + i * colW + colW/2;
  const yForRow = r => matrixY + r * rowH + rowH/2;

  return (
    <div style={{
      width: "100%", height: "100%", display: "flex", flexDirection: "column",
      background: "var(--void)", color: "var(--bone)", overflow: "hidden",
    }}>
      <TopBar route={["Game · DET-070", "Analysis", "Communities"]}/>
      <SubTabs active="upset" tabs={[
        { id: "upset",     label: "Intersection Analysis" },
        { id: "roster",    label: "Roster · Totals" },
        { id: "timeseries",label: "Membership Δ · Time" },
        { id: "matrix",    label: "Co-membership Matrix" },
      ]}/>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "240px 1fr 340px",
        gap: 12, padding: 16, minHeight: 0 }}>

        {/* LEFT RAIL — community roster + filter */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <Pane label="Hyperedges" badge={`${COMMUNITIES.length} active`}>
            <div style={{ padding: "8px 10px 10px", display: "flex", flexDirection: "column", gap: 4, overflow: "auto" }}>
              {COMMUNITIES.map(c => (
                <div key={c.id}
                  onMouseEnter={() => setHoveredCommunity(c.id)}
                  onMouseLeave={() => setHoveredCommunity(null)}
                  style={{
                    display: "grid", gridTemplateColumns: "12px 1fr auto",
                    alignItems: "center", gap: 8,
                    padding: "6px 6px",
                    borderRadius: 3,
                    background: hoveredCommunity === c.id ? "var(--tar)" : "transparent",
                    cursor: "default",
                  }}>
                  <span style={{ width: 8, height: 8, background: c.color, borderRadius: 1,
                    boxShadow: `0 0 8px ${c.color}` }}/>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)",
                      letterSpacing: ".06em", textTransform: "uppercase",
                      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {c.label}
                    </div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)", letterSpacing: ".18em" }}>
                      {c.id}
                    </div>
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 10,
                    color: "var(--bone)", fontWeight: 600, letterSpacing: ".02em" }}>
                    {fmtCount(c.count)}
                  </div>
                </div>
              ))}
            </div>
          </Pane>

          <Pane label="Filter" style={{ flexShrink: 0 }}>
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
              <FilterRow label="Min cardinality" value="≥ 4k" />
              <FilterRow label="Show empties" value="off" muted />
              <FilterRow label="Sort" value="size · desc" />
              <FilterRow label="Color by" value="dominant" />
            </div>
          </Pane>
        </div>

        {/* CENTER — UpSet PLOT */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
          <ConstitutionBanner>
            Community membership renders as <em style={{ color: "var(--bone)", fontStyle: "normal" }}>intersection analysis</em>,
            not pairwise edges, not spatial hulls.
          </ConstitutionBanner>

          <Pane label="UpSet · Community Hyperedge Intersections" badge="XGI snapshot · tick 042">
            <div style={{ padding: 8, position: "relative" }}>
              <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block",
                fontFamily: "var(--font-mono)", maxHeight: 540 }}>

                {/* ── TOP: intersection size bars ── */}
                <text x={leftPad} y={topBarsY + 4} fill="var(--ash)"
                  fontSize={9} letterSpacing=".22em">
                  INTERSECTION SIZE
                </text>
                <text x={leftPad} y={topBarsY + 16} fill="var(--shroud)"
                  fontSize={8} letterSpacing=".16em">
                  members in this exact intersection
                </text>

                {/* y-axis ticks for top bars */}
                {[0, 0.25, 0.5, 0.75, 1].map((t, i) => {
                  const v = Math.round(maxIxCount * t);
                  const y = topBarsY + topBarsH - t * topBarsH;
                  return (
                    <g key={i}>
                      <line x1={matrixX - 6} x2={matrixX + matrixW} y1={y} y2={y}
                        stroke="var(--rebar)" strokeWidth="0.5"
                        strokeDasharray={t === 0 ? "0" : "1 3"}/>
                      <text x={matrixX - 8} y={y + 3} fill="var(--ash)"
                        fontSize={8} textAnchor="end" letterSpacing=".06em">
                        {fmtCount(v)}
                      </text>
                    </g>
                  );
                })}

                {/* bars */}
                {visible.map((ix, i) => {
                  const isActive = i === activeIx;
                  const isSelected = i === selectedIx;
                  const h = (ix.count / maxIxCount) * topBarsH;
                  const x = xForCol(i) - 9;
                  const y = topBarsY + topBarsH - h;
                  const fill = isSelected ? "var(--spire)" :
                               isActive ? "var(--bone)" : "var(--fog)";
                  return (
                    <g key={i} onClick={() => setSelectedIx(i)}
                      onMouseEnter={() => setHoverIx(i)}
                      onMouseLeave={() => setHoverIx(null)}
                      style={{ cursor: "pointer" }}>
                      <rect x={xForCol(i)-(colW/2)} y={topBarsY} width={colW} height={topBarsH+matrixH+30}
                        fill={isSelected ? "rgba(77,217,230,.05)" : isActive ? "rgba(255,255,255,.025)" : "transparent"}/>
                      <rect x={x} y={y} width={18} height={h} fill={fill}
                        opacity={isSelected ? 1 : isActive ? 0.95 : 0.78}/>
                      {(isActive || isSelected) && (
                        <text x={xForCol(i)} y={y - 4} fill={fill} fontSize={9}
                          textAnchor="middle" letterSpacing=".04em" fontWeight={600}>
                          {fmtCount(ix.count)}
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* divider between top bars and matrix */}
                <line x1={leftPad} x2={matrixX + matrixW} y1={matrixY - 14} y2={matrixY - 14}
                  stroke="var(--rebar)" strokeWidth="1"/>

                {/* ── LEFT: community labels + total bars ── */}
                <text x={leftPad} y={matrixY - 22} fill="var(--ash)" fontSize={9} letterSpacing=".22em">
                  COMMUNITY · TOTAL CARDINALITY
                </text>
                {COMMUNITIES.map((c, r) => {
                  const isHovered = hoveredCommunity === c.id;
                  const isInActive = visible[activeIx].ids.includes(c.id);
                  const y = yForRow(r);
                  const labelColor = isHovered ? "var(--bone)" :
                                     isInActive ? "var(--bone)" : "var(--fog)";

                  // row band background
                  return (
                    <g key={c.id}
                       onMouseEnter={() => setHoveredCommunity(c.id)}
                       onMouseLeave={() => setHoveredCommunity(null)}>
                      <rect x={0} y={matrixY + r*rowH} width={matrixX + matrixW} height={rowH}
                        fill={r % 2 ? "rgba(255,255,255,.012)" : "transparent"}/>
                      {isHovered && (
                        <rect x={0} y={matrixY + r*rowH} width={matrixX + matrixW} height={rowH}
                          fill={c.color} opacity={0.06}/>
                      )}
                      {/* label */}
                      <rect x={leftPad-2} y={y - 5} width={9} height={9}
                        fill={c.color} opacity={isHovered || isInActive ? 1 : 0.55}/>
                      <text x={leftPad + 14} y={y + 3} fill={labelColor}
                        fontSize={10} letterSpacing=".08em" fontWeight={600}>
                        {c.label.toUpperCase()}
                      </text>
                      {/* total horizontal bar */}
                      <g transform={`translate(${leftPad + labelW}, ${y})`}>
                        <rect x={0} y={-5} width={(c.count / maxCommCount) * (totalsW - 32)} height={10}
                          fill={c.color} opacity={isHovered ? 1 : 0.7}/>
                        <text x={totalsW - 24} y={3} fill="var(--bone)" fontSize={9}
                          letterSpacing=".04em" textAnchor="start" fontWeight={600}>
                          {fmtCount(c.count)}
                        </text>
                      </g>
                    </g>
                  );
                })}

                {/* ── MATRIX: dots & connecting lines ── */}
                {visible.map((ix, i) => {
                  const isActive = i === activeIx;
                  const isSelected = i === selectedIx;
                  const rowsInIx = ix.ids.map(id => COMMUNITIES.findIndex(c => c.id === id));
                  const minR = Math.min(...rowsInIx);
                  const maxR = Math.max(...rowsInIx);
                  const cx = xForCol(i);

                  return (
                    <g key={i}
                      onClick={() => setSelectedIx(i)}
                      onMouseEnter={() => setHoverIx(i)}
                      onMouseLeave={() => setHoverIx(null)}
                      style={{ cursor: "pointer" }}>
                      {/* faint dots for non-participating rows */}
                      {COMMUNITIES.map((c, r) =>
                        !ix.ids.includes(c.id) && (
                          <circle key={r} cx={cx} cy={yForRow(r)} r={3}
                            fill="var(--shroud)" opacity={0.35}/>
                        )
                      )}
                      {/* connecting line through participating rows */}
                      {rowsInIx.length > 1 && (
                        <line x1={cx} x2={cx}
                          y1={yForRow(minR)} y2={yForRow(maxR)}
                          stroke={isSelected ? "var(--spire)" :
                                  isActive ? "var(--bone)" : "var(--fog)"}
                          strokeWidth={isSelected ? 2.5 : isActive ? 2 : 1.5}
                          opacity={isSelected ? 1 : isActive ? 0.95 : 0.7}/>
                      )}
                      {/* solid dots */}
                      {rowsInIx.map((r, idx) => {
                        const comm = ix.ids[idx];
                        const c = COMM_BY_ID[comm];
                        return (
                          <g key={idx}>
                            <circle cx={cx} cy={yForRow(r)} r={dotR}
                              fill={isSelected ? c.color : isActive ? c.color : c.color}
                              opacity={isSelected ? 1 : isActive ? 0.95 : 0.85}
                              stroke={isSelected ? "var(--bone)" : "none"}
                              strokeWidth={1}/>
                            {isSelected && (
                              <circle cx={cx} cy={yForRow(r)} r={dotR + 3}
                                fill="none" stroke={c.color} strokeWidth="0.5" opacity={0.5}/>
                            )}
                          </g>
                        );
                      })}
                    </g>
                  );
                })}

                {/* note marker on salient intersections */}
                {visible.map((ix, i) => ix.note && (
                  <circle key={`note-${i}`} cx={xForCol(i) + 10}
                    cy={topBarsY + topBarsH + 12} r={2.5}
                    fill="var(--rupture)"/>
                ))}

                {/* baseline + x-axis label */}
                <line x1={leftPad + labelW + totalsW - 16} x2={matrixX + matrixW}
                  y1={matrixY + matrixH + 2} y2={matrixY + matrixH + 2}
                  stroke="var(--rebar)" strokeWidth="0.5"/>
                <text x={matrixX + matrixW/2} y={matrixY + matrixH + 22}
                  fill="var(--ash)" fontSize={9} textAnchor="middle"
                  letterSpacing=".22em">
                  16 INTERSECTIONS · SORTED BY CARDINALITY · DESC
                </text>
              </svg>
            </div>
          </Pane>
        </div>

        {/* RIGHT RAIL — selected intersection drill-down */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0, overflow: "hidden" }}>
          <SelectedIntersectionPanel ix={visible[selectedIx]} index={selectedIx}/>
          <EventsPanel/>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// LEFT-RAIL bits
// ────────────────────────────────────────────────────────────
function FilterRow({ label, value, muted }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline",
      padding: "4px 0", borderBottom: "1px dashed var(--rebar)",
      fontFamily: "var(--font-mono)", fontSize: 10 }}>
      <span style={{ color: "var(--ash)", letterSpacing: ".12em", textTransform: "uppercase" }}>{label}</span>
      <span style={{ color: muted ? "var(--shroud)" : "var(--bone)", letterSpacing: ".04em" }}>{value}</span>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// RIGHT-RAIL: detail on the currently selected intersection
// ────────────────────────────────────────────────────────────
function SelectedIntersectionPanel({ ix, index }) {
  const ixLabel = ix.ids.map(id => COMM_BY_ID[id].short).join(" ∩ ");
  const denom = Math.min(...ix.ids.map(id => COMM_BY_ID[id].count));
  const concentration = ix.count / denom;
  return (
    <Pane label="Selected Intersection" badge={`#${String(index+1).padStart(2,"0")}`} style={{ flexShrink: 0 }}>
      <div style={{ padding: "12px 14px", display: "flex", flexDirection: "column", gap: 12 }}>
        {/* hyperedge expression */}
        <div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
            letterSpacing: ".22em", marginBottom: 6 }}>HYPEREDGE</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {ix.ids.map((id, i) => (
              <React.Fragment key={id}>
                <CommBadge id={id}/>
                {i < ix.ids.length-1 && <span style={{
                  fontFamily: "var(--font-mono)", color: "var(--ash)", fontSize: 14,
                  alignSelf: "center", padding: "0 2px" }}>∩</span>}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* members + concentration */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <Stat label="Members" value={fmtCount(ix.count)} sub="people"/>
          <Stat label="Concentration" value={fmtPct(concentration, 1)}
            sub={`of ${COMM_BY_ID[ix.ids[ix.ids.findIndex(id => COMM_BY_ID[id].count === denom)]].short}`}/>
        </div>

        {/* membership-overlap bar */}
        <div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
            letterSpacing: ".22em", marginBottom: 6 }}>OVERLAP DENSITY</div>
          <div style={{ display: "flex", height: 8, background: "var(--tar)", borderRadius: 2, overflow: "hidden" }}>
            {ix.ids.map(id => (
              <div key={id} style={{ flex: 1, background: COMM_BY_ID[id].color, opacity: 0.7 }}/>
            ))}
          </div>
        </div>

        {ix.note && (
          <div style={{
            padding: "8px 10px", background: "rgba(212,160,44,.06)",
            border: "1px solid rgba(212,160,44,.22)", borderRadius: 3,
            fontFamily: "var(--font-mono)", fontSize: 10, lineHeight: 1.5,
            color: "var(--bone)", letterSpacing: ".02em",
          }}>
            <div style={{ color: "var(--rupture)", fontSize: 9, letterSpacing: ".22em", marginBottom: 4 }}>
              SALIENT
            </div>
            {ix.note}
          </div>
        )}

        {/* action buttons */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
          <ActionLink verb="Educate" hint="target → this hyperedge" recommended/>
          <ActionLink verb="Mobilize" hint="target → this hyperedge"/>
          <ActionLink verb="Campaign" hint="target → this hyperedge or a territory"/>
          <div style={{ display: "flex", gap: 6, marginTop: 2 }}>
            <ActionLink verb="Inspect" hint="open intel detail" subtle/>
            <ActionLink verb="Compare" hint="vs. baseline tick 030" subtle/>
          </div>
        </div>
      </div>
    </Pane>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div style={{ background: "var(--tar)", border: "1px solid var(--rebar)",
      borderRadius: 3, padding: "8px 10px" }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)",
        letterSpacing: ".22em" }}>{label.toUpperCase()}</div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, color: "var(--bone)",
        fontWeight: 700, letterSpacing: "-.01em", marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontFamily: "var(--font-mono)", fontSize: 9,
        color: "var(--shroud)", letterSpacing: ".06em" }}>{sub}</div>}
    </div>
  );
}

function ActionLink({ verb, hint, recommended, subtle }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: subtle ? "5px 8px" : "8px 10px",
      flex: subtle ? 1 : "initial",
      background: recommended ? "rgba(95,191,122,.06)" :
                  subtle ? "var(--tar)" : "var(--tar)",
      border: `1px solid ${recommended ? "rgba(95,191,122,.32)" : "var(--rebar)"}`,
      borderRadius: 3,
      cursor: "pointer",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10,
          color: recommended ? "var(--solidarity)" : "var(--bone)", fontWeight: 700,
          letterSpacing: ".22em", textTransform: "uppercase" }}>{verb}</span>
        {!subtle && <span style={{ fontFamily: "var(--font-mono)", fontSize: 9,
          color: "var(--shroud)", letterSpacing: ".04em" }}>{hint}</span>}
      </div>
      <span style={{ color: "var(--ash)", fontFamily: "var(--font-mono)", fontSize: 11 }}>›</span>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Events feed
// ────────────────────────────────────────────────────────────
function EventsPanel() {
  return (
    <Pane label="Membership Flux" badge="last 4 ticks" style={{ flex: 1, minHeight: 0 }}>
      <div style={{ padding: "8px 10px", overflow: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
        {COMMUNITY_EVENTS.map(e => {
          const tone = {
            RUPTURE:      { c: "var(--laser)",      label: "RUPTURE" },
            TRANSMISSION: { c: "var(--solidarity)", label: "TRANSMIT" },
            WARNING:      { c: "var(--rupture)",    label: "WARN" },
            FLUX:         { c: "var(--spire)",      label: "FLUX" },
          }[e.kind];
          return (
            <div key={e.id} style={{
              display: "grid", gridTemplateColumns: "auto 1fr",
              gap: 8, padding: "6px 0",
              borderBottom: "1px dashed var(--rebar)",
            }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 2 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 8,
                  color: tone.c, fontWeight: 700, letterSpacing: ".22em" }}>
                  {tone.label}
                </span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 8,
                  color: "var(--shroud)", letterSpacing: ".08em" }}>
                  {e.t}
                </span>
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 10,
                color: "var(--bone)", lineHeight: 1.5, letterSpacing: ".02em" }}>
                {e.text}
              </div>
            </div>
          );
        })}
      </div>
    </Pane>
  );
}
