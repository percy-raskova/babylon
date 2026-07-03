// map-canvas.jsx — The HexMap component
// Renders the political-topology overlay over a stylized continental US.
//
// Modes (lens):
//   "stance"        - hexes filled by dominant ColonialStance, concentric rings for influence
//   "heat"          - heat overlay dominant, stance reduced to thin outline
//   "habitability"  - metabolic-rift state (low = crimson, high = phosphor green)
//   "faction"       - single-faction filter (factionFilter prop); non-influence hexes desaturated
//   "collapse"      - contested hexes pulse gold; transition arrows where dominant shifted
//
// Layers (toggleable):
//   showBoundaries  - sovereign CLAIMS convex hulls
//   showRings       - concentric influence rings inside each hex
//   showContested   - flicker on contested
//   showStateLines  - state-cluster polygon outlines

// Concentric ring scales: outer (1.0) = dominant, middle (0.62) = secondary, inner (0.30) = third
const RING_SCALES = [1.0, 0.62, 0.30];

function lerp(a, b, t) { return a + (b - a) * t; }

// Habitability color scale (crimson → amber → phosphor)
function habColor(v) {
  if (v < 0.33) return `rgba(255,51,68,${0.18 + v * 1.2})`;            // laser
  if (v < 0.66) return `rgba(217,122,44,${0.30 + (v - 0.33) * 0.6})`;  // heat
  return `rgba(95,191,122,${0.40 + (v - 0.66) * 1.2})`;                 // solidarity
}

// Heat color scale (tar → heat → laser)
function heatColor(v) {
  if (v < 0.40) return `rgba(58,53,48,${0.30 + v})`;
  if (v < 0.70) return `rgba(217,122,44,${0.45 + (v - 0.4) * 1.1})`;
  return `rgba(255,51,68,${0.55 + (v - 0.7) * 1.5})`;
}

function HexMap({
  lens = "stance",
  factionFilter = null,
  showBoundaries = true,
  showRings = true,
  showContested = true,
  showStateLines = true,
  showHeatGloom = true,     // dim heatmap underlay even in stance mode
  scanlines = true,
  hoveredId = null, selectedId = null,
  onHexHover, onHexClick,
  collapseFrame = 0,        // 0..1, used by "collapse" lens to drive pulse
  className,
  style,
}) {

  // Pre-compute sovereign hull polygons (memoized once)
  const hulls = React.useMemo(() => SOVEREIGNS.map(s => ({
    id: s.id, color: s.color,
    points: sovereignClaimsPath(s.id),
  })).filter(h => h.points), []);

  // For "collapse" lens: derive a "previous" sovereign assignment
  // (some hexes "switch" — we just mark contested hexes as transitioning)
  return (
    <svg viewBox="0 0 940 500" preserveAspectRatio="xMidYMid meet"
      width="100%" height="100%" className={className}
      style={{ display: "block", background: "transparent", ...style }}>

      {/* Defs: filters, patterns */}
      <defs>
        <filter id="glow-soft" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.8" />
        </filter>
        <filter id="glow-hard" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3.5" />
        </filter>
        <radialGradient id="rg-decay" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(255,51,68,.0)"/>
          <stop offset="100%" stopColor="rgba(255,51,68,.35)"/>
        </radialGradient>
        <pattern id="hatch-contested" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="6" stroke="#d4a02c" strokeWidth="1.2" strokeOpacity=".55"/>
        </pattern>
        <pattern id="grid-bg" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1a1f2a" strokeWidth=".5"/>
        </pattern>
      </defs>

      {/* Background: faint void grid + film of dust */}
      <rect width="940" height="500" fill="#0a0d13"/>
      <rect width="940" height="500" fill="url(#grid-bg)" opacity=".5"/>

      {/* State-cluster outlines (the abstracted US) — drawn under hexes */}
      {showStateLines && (
        <g>
          {US_REGIONS.map(r => (
            <polygon key={r.id} points={r.poly}
              fill="#11141c"
              stroke="#1a1f2a" strokeWidth="0.6"
              fillOpacity=".55"/>
          ))}
        </g>
      )}

      {/* HEXES — main layer */}
      <g>
        {HEXES.map(h => {
          const isHovered = hoveredId === h.id;
          const isSelected = selectedId === h.id;

          // Sort factions by influence to assign ring order (descending)
          const sortedFactions = Object.entries(h.influences)
            .sort((a, b) => b[1] - a[1]);
          const dominantFaction = FAC_BY_ID[sortedFactions[0][0]];
          const dominantStance = STANCE[dominantFaction.stance];

          // === Decide fill strategy by lens ===
          let primaryFill, primaryOpacity;
          let dimmed = false;

          if (lens === "stance") {
            primaryFill = dominantStance.color;
            primaryOpacity = lerp(0.18, 0.78, h.dominant_share); // stronger fill where more dominant
          } else if (lens === "heat") {
            primaryFill = heatColor(h.heat);
            primaryOpacity = 1;
          } else if (lens === "habitability") {
            primaryFill = habColor(h.habitability);
            primaryOpacity = 1;
          } else if (lens === "faction" && factionFilter) {
            const f = FAC_BY_ID[factionFilter];
            const fStance = STANCE[f.stance];
            const fInf = h.influences[factionFilter];
            if (fInf < 0.20) {
              // Below threshold: desaturate completely
              primaryFill = "#1a1f2a";
              primaryOpacity = 0.55;
              dimmed = true;
            } else {
              primaryFill = fStance.color;
              primaryOpacity = lerp(0.18, 0.85, fInf);
            }
          } else if (lens === "collapse") {
            primaryFill = dominantStance.color;
            primaryOpacity = lerp(0.18, 0.65, h.dominant_share);
          }

          // Outer hex
          const outer = hexPoints(h.cx, h.cy, HEX_RADIUS);

          return (
            <g key={h.id}
              onMouseEnter={() => onHexHover && onHexHover(h)}
              onMouseLeave={() => onHexHover && onHexHover(null)}
              onClick={() => onHexClick && onHexClick(h)}
              style={{ cursor: "pointer" }}>
              {/* Base hex */}
              <polygon points={outer}
                fill={primaryFill}
                fillOpacity={primaryOpacity}
                stroke={isSelected ? "#4dd9e6" : isHovered ? "#d8dce0" : "#06070b"}
                strokeWidth={isSelected ? 1.6 : isHovered ? 1.0 : 0.5}
              />

              {/* Concentric influence rings (only in stance + collapse lenses, and not dimmed) */}
              {showRings && !dimmed && (lens === "stance" || lens === "collapse") && (
                <>
                  {/* Middle ring: secondary faction */}
                  <polygon
                    points={hexPoints(h.cx, h.cy, HEX_RADIUS * RING_SCALES[1])}
                    fill={STANCE[FAC_BY_ID[sortedFactions[1][0]].stance].color}
                    fillOpacity={lerp(0.05, 0.55, sortedFactions[1][1])}
                    stroke="none"
                    pointerEvents="none"/>
                  {/* Inner ring: third faction */}
                  <polygon
                    points={hexPoints(h.cx, h.cy, HEX_RADIUS * RING_SCALES[2])}
                    fill={STANCE[FAC_BY_ID[sortedFactions[2][0]].stance].color}
                    fillOpacity={lerp(0.05, 0.65, sortedFactions[2][1])}
                    stroke="none"
                    pointerEvents="none"/>
                </>
              )}

              {/* Heat gloom — subtle red wash on high-heat hexes when in stance/faction lens */}
              {showHeatGloom && (lens === "stance" || lens === "faction") && h.heat > 0.55 && !dimmed && (
                <polygon points={outer}
                  fill="url(#rg-decay)"
                  fillOpacity={lerp(0, 0.55, (h.heat - 0.55) / 0.45)}
                  pointerEvents="none"/>
              )}

              {/* Contested indication */}
              {showContested && h.contested && lens !== "heat" && lens !== "habitability" && !dimmed && (
                <polygon points={hexPoints(h.cx, h.cy, HEX_RADIUS * 0.94)}
                  fill="none"
                  stroke="#d4a02c"
                  strokeWidth={lens === "collapse" ? 1.4 + Math.sin(collapseFrame * Math.PI * 2) * 0.6 : 1.2}
                  strokeOpacity={lens === "collapse" ? 0.6 + Math.sin(collapseFrame * Math.PI * 2 + h.cx * 0.02) * 0.4 : 0.85}
                  strokeDasharray="2 2.5"
                  pointerEvents="none"/>
              )}
            </g>
          );
        })}
      </g>

      {/* SOVEREIGN CLAIMS BOUNDARIES — convex hulls of controlled hex clusters */}
      {showBoundaries && (
        <g>
          {hulls.map(h => (
            <g key={h.id}>
              <polygon points={h.points}
                fill="none"
                stroke={h.color}
                strokeWidth="1.6"
                strokeOpacity=".85"
                strokeDasharray="6 3"
                filter="url(#glow-soft)"/>
              <polygon points={h.points}
                fill="none"
                stroke={h.color}
                strokeWidth=".7"
                strokeOpacity=".95"/>
            </g>
          ))}
        </g>
      )}

      {/* MAJOR CITY LABELS — small caps under each city dot */}
      <g>
        {CITIES.map(c => (
          <g key={c.name}>
            <circle cx={c.x} cy={c.y} r={1.4} fill="#d8dce0" opacity=".75"/>
            <text x={c.x + 4} y={c.y + 3}
              fontSize="7.5"
              fontFamily="var(--font-mono)"
              fill="#8a93a0"
              letterSpacing=".05em"
              style={{ pointerEvents: "none", textShadow: "0 0 4px #06070b" }}>{c.name}</text>
          </g>
        ))}
      </g>

      {/* CRT scanlines overlay */}
      {scanlines && (
        <rect width="940" height="500" fill="url(#grid-bg)" opacity="0" pointerEvents="none"/>
      )}
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────
// LEGEND — small overlay shown in the corner of the map
// ─────────────────────────────────────────────────────────────
function MapLegend({ lens, factionFilter, theory = true }) {
  const lblStyle = { fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--fog)", textTransform: "uppercase" };
  const noteStyle = { fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", fontStyle: "italic" };
  const valStyle = { fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)", letterSpacing: ".06em" };

  if (lens === "heat") {
    return (
      <div style={{ background: "rgba(17,20,28,.92)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "10px 12px", minWidth: 200, backdropFilter: "blur(4px)" }}>
        <div style={{ ...lblStyle, marginBottom: 8 }}>Heat · State Attention</div>
        <div style={{ height: 6, background: "linear-gradient(to right, #3a3530, #d97a2c, #ff3344)", borderRadius: 9999, marginBottom: 4 }}/>
        <div style={{ display: "flex", justifyContent: "space-between", ...valStyle }}>
          <span>0.0 · QUIET</span><span>1.0 · MAXIMUM</span>
        </div>
        {theory && <div style={{ ...noteStyle, marginTop: 8 }}>"Surveillance pressure" — empire watching back.</div>}
      </div>
    );
  }

  if (lens === "habitability") {
    return (
      <div style={{ background: "rgba(17,20,28,.92)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "10px 12px", minWidth: 200, backdropFilter: "blur(4px)" }}>
        <div style={{ ...lblStyle, marginBottom: 8 }}>Habitability · Metabolic Rift</div>
        <div style={{ height: 6, background: "linear-gradient(to right, #ff3344, #d97a2c, #5fbf7a)", borderRadius: 9999, marginBottom: 4 }}/>
        <div style={{ display: "flex", justifyContent: "space-between", ...valStyle }}>
          <span>0.0 · DEAD</span><span>1.0 · LIVING</span>
        </div>
        {theory && <div style={{ ...noteStyle, marginTop: 8 }}>Only CEASE-policy sovereigns recover habitability.</div>}
      </div>
    );
  }

  if (lens === "faction" && factionFilter) {
    const f = FAC_BY_ID[factionFilter];
    const s = STANCE[f.stance];
    return (
      <div style={{ background: "rgba(17,20,28,.92)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "10px 12px", minWidth: 230, backdropFilter: "blur(4px)" }}>
        <div style={{ ...lblStyle, marginBottom: 8 }}>Faction Filter · {s.label}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ width: 12, height: 12, background: s.color, borderRadius: 9999, boxShadow: `0 0 8px ${s.glow}` }}/>
          <span style={{ ...valStyle, color: "var(--bone)", fontWeight: 600 }}>{f.name}</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {["LOW · 0.20", "MID · 0.45", "HIGH · 0.75"].map((t, i) => (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 14, height: 10, background: s.color, opacity: [0.25, 0.55, 0.85][i], display: "inline-block" }}/>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)" }}>{t}</span>
            </div>
          ))}
        </div>
        {theory && <div style={{ ...noteStyle, marginTop: 8, lineHeight: 1.4 }}>{f.blurb}</div>}
      </div>
    );
  }

  // Default: stance legend (3 colors + influence rings)
  return (
    <div style={{ background: "rgba(17,20,28,.92)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "10px 12px", minWidth: 230, backdropFilter: "blur(4px)" }}>
      <div style={{ ...lblStyle, marginBottom: 8 }}>Colonial Stance · Influence</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5, marginBottom: 8 }}>
        {Object.values(STANCE).map(s => (
          <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ width: 12, height: 12, background: s.color, borderRadius: 2, boxShadow: `0 0 6px ${s.glow}` }}/>
            <span style={{ ...valStyle }}>{s.label.toUpperCase()}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", marginLeft: "auto" }}>
              {s.id === "UPHOLD" ? "extract +1.5" : s.id === "IGNORE" ? "extract ×0.8" : "extract = 0"}
            </span>
          </div>
        ))}
      </div>
      <div style={{ borderTop: "1px solid var(--rebar)", paddingTop: 7, marginTop: 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <svg width="20" height="20" viewBox="-10 -10 20 20">
            <polygon points={hexPoints(0, 0, 9)} fill="#ff3344" fillOpacity=".65"/>
            <polygon points={hexPoints(0, 0, 5.6)} fill="#6b8fb5" fillOpacity=".60"/>
            <polygon points={hexPoints(0, 0, 2.7)} fill="#5fbf7a" fillOpacity=".70"/>
          </svg>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--bone)", letterSpacing: ".06em" }}>concentric = influence</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)" }}>outer · mid · inner</div>
          </div>
        </div>
      </div>
      <div style={{ borderTop: "1px solid var(--rebar)", paddingTop: 7, marginTop: 7, display: "flex", alignItems: "center", gap: 8 }}>
        <svg width="20" height="20" viewBox="-10 -10 20 20">
          <polygon points={hexPoints(0, 0, 9)} fill="none" stroke="#d4a02c" strokeDasharray="2 2" strokeWidth="1"/>
        </svg>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--bone)", letterSpacing: ".06em" }}>contested · Δ &lt; 0.12</div>
      </div>
      {theory && <div style={{ ...noteStyle, marginTop: 10, lineHeight: 1.4 }}>You cannot build socialism on stolen land.</div>}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// HEX TOOLTIP — floating panel shown on hover
// ─────────────────────────────────────────────────────────────
function HexTooltip({ hex, anchorX, anchorY }) {
  if (!hex) return null;
  const sortedFactions = Object.entries(hex.influences).sort((a, b) => b[1] - a[1]);
  const sov = hex.sovereign_id ? SOV_BY_ID[hex.sovereign_id] : null;

  return (
    <div style={{
      position: "absolute",
      left: `calc(${anchorX}% + 12px)`,
      top: `calc(${anchorY}% - 60px)`,
      background: "rgba(6,7,11,.96)",
      border: "1px solid var(--wet-steel)",
      borderRadius: 6,
      padding: "9px 11px",
      minWidth: 220,
      pointerEvents: "none",
      backdropFilter: "blur(6px)",
      boxShadow: "0 6px 22px rgba(0,0,0,.6)",
      zIndex: 50,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)", letterSpacing: ".1em", fontWeight: 600 }}>{hex.id}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".1em", textTransform: "uppercase" }}>{hex.region_name}</span>
      </div>

      {/* Influence breakdown */}
      <div style={{ display: "flex", flexDirection: "column", gap: 3, marginBottom: 7 }}>
        {sortedFactions.map(([fid, val]) => {
          const f = FAC_BY_ID[fid];
          const s = STANCE[f.stance];
          return (
            <div key={fid} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 7, height: 7, background: s.color, borderRadius: 9999, boxShadow: `0 0 4px ${s.glow}`, flexShrink: 0 }}/>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: "var(--bone)", flex: 1, letterSpacing: ".02em" }}>{f.name}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: s.color, fontWeight: 600 }}>{val.toFixed(2)}</span>
            </div>
          );
        })}
      </div>

      {hex.contested && (
        <div style={{ background: "rgba(212,160,44,.10)", border: "1px solid rgba(212,160,44,.35)", padding: "3px 7px", borderRadius: 3, fontFamily: "var(--font-mono)", fontSize: 9, color: "#d4a02c", letterSpacing: ".14em", marginBottom: 7 }}>
          CONTESTED · Δ {(hex.dominant_share - hex.second_share).toFixed(3)}
        </div>
      )}

      {/* Sovereign + metrics */}
      <div style={{ borderTop: "1px solid var(--rebar)", paddingTop: 6, display: "grid", gridTemplateColumns: "auto 1fr", rowGap: 3, columnGap: 8 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".15em" }}>SOV</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: sov ? sov.color : "var(--shroud)" }}>{sov ? sov.short_name : "— ungoverned —"}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".15em" }}>HAB</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: hex.habitability > 0.5 ? "#5fbf7a" : hex.habitability > 0.3 ? "#d97a2c" : "#ff3344" }}>{hex.habitability.toFixed(3)}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".15em" }}>HEAT</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: hex.heat > 0.6 ? "#ff3344" : "#d97a2c" }}>{hex.heat.toFixed(3)}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".15em" }}>POP</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: "var(--bone)" }}>{hex.population.toFixed(2)}</span>
      </div>
    </div>
  );
}

Object.assign(window, { HexMap, MapLegend, HexTooltip });
