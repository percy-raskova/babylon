// map-shell.jsx — Cockpit shell wrapping The Map.
// Adapted from ui_kits/webapp/GameShell.jsx (Cold Collapse v8 aesthetic).
// One self-contained shell per artboard; each variation passes initial lens/faction/state.

// ─────────────────────────────────────────────────────────────
// SUBCOMPONENTS
// ─────────────────────────────────────────────────────────────

function LensTab({ active, onClick, icon, children }) {
  return (
    <button onClick={onClick} style={{
      display: "flex", alignItems: "center", gap: 5,
      borderRadius: 3, padding: "5px 11px",
      fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 500,
      border: "none", cursor: "pointer",
      letterSpacing: ".14em", textTransform: "uppercase",
      background: active ? "rgba(77,217,230,.08)" : "transparent",
      color: active ? "var(--spire)" : "var(--ash)",
      borderBottom: active ? "1px solid var(--spire)" : "1px solid transparent",
    }}>
      <span style={{ fontSize: 11 }}>{icon}</span>{children}
    </button>
  );
}

function GhostButton({ children, onClick, active }) {
  return (
    <button onClick={onClick} style={{
      background: active ? "rgba(77,217,230,.06)" : "transparent",
      border: `1px solid ${active ? "var(--spire)" : "var(--wet-steel)"}`,
      borderRadius: 4, padding: "5px 11px",
      fontFamily: "var(--font-mono)", fontSize: 10,
      color: active ? "var(--spire)" : "var(--fog)",
      cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase",
    }}>{children}</button>
  );
}

// Sovereign roster — replaces the org "Resource Bar" with a faction-power readout
function SovereignRoster({ onSelectFaction, selectedFaction }) {
  // Count hexes per sovereign
  const counts = React.useMemo(() => {
    const c = { SOV_RESTORATIONIST: 0, SOV_WORKERS_CONGRESS: 0, SOV_DECOLONIAL: 0, NONE: 0 };
    HEXES.forEach(h => { c[h.sovereign_id || "NONE"]++; });
    return c;
  }, []);
  const total = HEXES.length;

  return (
    <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "10px 14px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 9, paddingBottom: 7, borderBottom: "1px solid var(--rebar)" }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--bone)", letterSpacing: ".02em" }}>Sovereign Roster · Post-Collapse Claims</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase" }}>{HEXES.length} TERRITORIES</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 16 }}>
        {SOVEREIGNS.map(s => {
          const fac = FAC_BY_ID[s.ruling_faction_id];
          const stance = STANCE[fac.stance];
          const c = counts[s.id];
          const isSelected = selectedFaction === fac.id;
          return (
            <button key={s.id} onClick={() => onSelectFaction && onSelectFaction(isSelected ? null : fac.id)}
              style={{
                background: isSelected ? "rgba(77,217,230,.04)" : "var(--void)",
                border: `1px solid ${isSelected ? "var(--spire)" : "var(--rebar)"}`,
                borderRadius: 4, padding: "8px 10px", textAlign: "left", cursor: "pointer",
                transition: "border-color .15s",
              }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
                <span style={{ width: 8, height: 8, background: s.color, borderRadius: 9999, boxShadow: `0 0 6px ${stance.glow}`, flexShrink: 0 }}/>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)", fontWeight: 600, letterSpacing: ".06em" }}>{s.short_name}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 8.5, color: stance.color, letterSpacing: ".18em", marginLeft: "auto" }}>{stance.label.toUpperCase()}</span>
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", marginBottom: 6, letterSpacing: ".02em" }}>{fac.name}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                <div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase" }}>Claims</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, color: s.color }}>{c}<span style={{ fontSize: 9, color: "var(--shroud)", fontWeight: 400 }}>/{total}</span></div>
                </div>
                <div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase" }}>Leg.</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--bone)" }}>{s.legitimacy.toFixed(2)}</div>
                </div>
                <div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase" }}>ΔHab</div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: s.metabolic_impact > 0 ? "#5fbf7a" : "#ff3344" }}>
                    {s.metabolic_impact > 0 ? "+" : ""}{s.metabolic_impact.toFixed(3)}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
        {/* Ungoverned counter */}
        <div style={{ background: "var(--void)", border: "1px dashed var(--rebar)", borderRadius: 4, padding: "8px 10px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minWidth: 80 }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase", marginBottom: 3 }}>Ungoverned</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700, color: "#d4a02c" }}>{counts.NONE}</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".14em" }}>contested zones</div>
        </div>
      </div>
    </div>
  );
}

// Right panel content — Hex Detail
function HexDetailCard({ hex }) {
  if (!hex) {
    return (
      <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 14 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--ash)", textTransform: "uppercase", marginBottom: 10 }}>▸ Territory Detail</div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ash)", lineHeight: 1.5, letterSpacing: ".05em" }}>SELECT A HEX TO INSPECT.<br/><br/>HOVER FOR INFLUENCE BREAKDOWN.</div>
      </div>
    );
  }
  const sortedFactions = Object.entries(hex.influences).sort((a, b) => b[1] - a[1]);
  const sov = hex.sovereign_id ? SOV_BY_ID[hex.sovereign_id] : null;

  return (
    <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, color: "var(--spire)", letterSpacing: ".1em" }}>▸ {hex.id}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase" }}>{hex.region_name}</span>
      </div>

      <div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", letterSpacing: ".22em", textTransform: "uppercase", marginBottom: 6 }}>Faction Influence</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          {sortedFactions.map(([fid, val], i) => {
            const f = FAC_BY_ID[fid];
            const s = STANCE[f.stance];
            return (
              <div key={fid}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                  <span style={{ width: 8, height: 8, background: s.color, borderRadius: 9999, boxShadow: `0 0 4px ${s.glow}` }}/>
                  <span style={{ fontFamily: "var(--font-sans)", fontSize: 10.5, color: "var(--bone)", flex: 1 }}>{f.name}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, color: s.color }}>{val.toFixed(3)}</span>
                </div>
                <div style={{ height: 3, background: "var(--void)", borderRadius: 9999, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${val * 100}%`, background: s.color, boxShadow: `0 0 4px ${s.glow}` }}/>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {hex.contested && (
        <div style={{ background: "rgba(212,160,44,.08)", border: "1px solid rgba(212,160,44,.4)", borderRadius: 4, padding: "7px 9px" }}>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "#d4a02c", letterSpacing: ".22em", marginBottom: 3 }}>⚠ CONTESTED</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)" }}>Δ {(hex.dominant_share - hex.second_share).toFixed(3)} between top two factions.</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", marginTop: 4, fontStyle: "italic" }}>Next collapse_transition tick: this hex flips.</div>
        </div>
      )}

      <div style={{ borderTop: "1px solid var(--rebar)", paddingTop: 9 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", letterSpacing: ".22em", textTransform: "uppercase", marginBottom: 6 }}>Claims & Metrics</div>
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", rowGap: 5, columnGap: 12 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".18em", textTransform: "uppercase" }}>Sovereign</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: sov ? sov.color : "#d4a02c", fontWeight: 600 }}>{sov ? sov.name : "— Ungoverned —"}</span>

          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".18em", textTransform: "uppercase" }}>Extr. Policy</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: sov ? sov.color : "var(--shroud)" }}>
            {sov ? sov.extraction_policy : "—"}
          </span>

          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".18em", textTransform: "uppercase" }}>Habitability</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ flex: 1, height: 3, background: "var(--void)", borderRadius: 9999, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${hex.habitability * 100}%`, background: hex.habitability > 0.5 ? "#5fbf7a" : hex.habitability > 0.3 ? "#d97a2c" : "#ff3344" }}/>
            </div>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: hex.habitability > 0.5 ? "#5fbf7a" : "#ff3344", minWidth: 40, textAlign: "right" }}>{hex.habitability.toFixed(3)}</span>
          </div>

          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".18em", textTransform: "uppercase" }}>Heat</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ flex: 1, height: 3, background: "var(--void)", borderRadius: 9999, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${hex.heat * 100}%`, background: "#d97a2c" }}/>
            </div>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "#d97a2c", minWidth: 40, textAlign: "right" }}>{hex.heat.toFixed(3)}</span>
          </div>

          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".18em", textTransform: "uppercase" }}>Population</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ flex: 1, height: 3, background: "var(--void)", borderRadius: 9999, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${hex.population * 100}%`, background: "#7a6db8" }}/>
            </div>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--bone)", minWidth: 40, textAlign: "right" }}>{hex.population.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function FactionDetailCard({ factionId, onClear }) {
  if (!factionId) return null;
  const f = FAC_BY_ID[factionId];
  const s = STANCE[f.stance];
  // Compute total influence held by this faction
  let totalInf = 0, dominantCount = 0;
  HEXES.forEach(h => {
    totalInf += h.influences[factionId];
    if (h.dominant_faction_id === factionId) dominantCount++;
  });

  return (
    <div style={{ background: "var(--concrete)", border: `1px solid ${s.color}`, borderRadius: 6, padding: 14, display: "flex", flexDirection: "column", gap: 10, boxShadow: `0 0 18px ${s.glow}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ width: 14, height: 14, background: s.color, borderRadius: 9999, boxShadow: `0 0 10px ${s.glow}`, flexShrink: 0 }}/>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 700, color: "var(--bone)", lineHeight: 1.1 }}>{f.name}</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: s.color, letterSpacing: ".22em", textTransform: "uppercase" }}>{f.ideology}</div>
        </div>
        {onClear && (
          <button onClick={onClear} style={{ background: "transparent", border: "1px solid var(--rebar)", borderRadius: 3, padding: "2px 7px", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", cursor: "pointer", letterSpacing: ".14em" }}>CLEAR</button>
        )}
      </div>

      <div style={{ background: "var(--void)", borderRadius: 4, padding: "8px 10px" }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase", marginBottom: 3 }}>Colonial Stance</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 700, color: s.color, letterSpacing: ".06em" }}>{s.label.toUpperCase()}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", letterSpacing: ".05em", fontStyle: "italic" }}>
            extraction_policy: {f.stance === "UPHOLD" ? "INTENSIFY" : f.stance === "IGNORE" ? "CONTINUE" : "CEASE"}
          </span>
        </div>
      </div>

      <div style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--fog)", lineHeight: 1.5, letterSpacing: ".01em" }}>{f.blurb}</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {[
          { lbl: "Extr. Mod", val: f.extraction_modifier.toFixed(2) + "×", col: f.extraction_modifier > 1 ? "#ff3344" : f.extraction_modifier > 0.1 ? "#d97a2c" : "#5fbf7a" },
          { lbl: "Viol. Mod", val: f.violence_modifier.toFixed(2) + "×", col: f.violence_modifier > 1 ? "#ff3344" : "#d97a2c" },
          { lbl: "Class Δ",  val: f.class_reduction.toFixed(2), col: "#6b8fb5" },
          { lbl: "Metab. Δ", val: (f.metabolic_reduction > 0 ? "+" : "") + f.metabolic_reduction.toFixed(2), col: f.metabolic_reduction > 0 ? "#5fbf7a" : "#ff3344" },
        ].map((m, i) => (
          <div key={i} style={{ background: "var(--void)", border: "1px solid var(--rebar)", borderRadius: 3, padding: "6px 8px" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase" }}>{m.lbl}</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700, color: m.col }}>{m.val}</div>
          </div>
        ))}
      </div>

      <div style={{ borderTop: "1px solid var(--rebar)", paddingTop: 9 }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase", marginBottom: 5 }}>Map Presence</div>
        <div style={{ display: "flex", gap: 12 }}>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".18em" }}>DOM. HEX</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 700, color: s.color }}>{dominantCount}<span style={{ fontSize: 9, color: "var(--shroud)", fontWeight: 400 }}>/{HEXES.length}</span></div>
          </div>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".18em" }}>TOTAL INF.</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 700, color: s.color }}>{totalInf.toFixed(1)}</div>
          </div>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)", letterSpacing: ".18em" }}>BASE</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--bone)", marginTop: 4, lineHeight: 1.3 }}>{f.base}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// THE COCKPIT SHELL — accepts initial state per artboard
// ─────────────────────────────────────────────────────────────
function MapShell({
  variant = "stance",       // "stance" | "heat" | "faction" | "collapse"
  initialLens,
  initialFactionFilter = null,
  initialSelectedHex = null,
  showStateLines = true,
  showRings = true,
  showBoundaries = true,
  showContested = true,
}) {
  const [lens, setLens] = React.useState(initialLens || (variant === "faction" ? "faction" : variant));
  const [factionFilter, setFactionFilter] = React.useState(initialFactionFilter);
  const [hoveredHex, setHoveredHex] = React.useState(null);
  const [selectedHex, setSelectedHex] = React.useState(initialSelectedHex);
  const [bottomOpen, setBottomOpen] = React.useState(true);
  const [tick, setTick] = React.useState(variant === "collapse" ? 288 : 287);
  const isCollapse = variant === "collapse";

  // Pulse loop for collapse lens
  const [pulse, setPulse] = React.useState(0);
  React.useEffect(() => {
    if (!isCollapse) return;
    let raf;
    const start = performance.now();
    const tick = (t) => {
      setPulse(((t - start) / 1800) % 1);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [isCollapse]);

  // Global metrics derived from current state
  const globalMetrics = React.useMemo(() => {
    let hab = 0, heat = 0, popControl = { UPHOLD: 0, IGNORE: 0, ABOLISH: 0 };
    HEXES.forEach(h => {
      hab += h.habitability * h.population;
      heat += h.heat * h.population;
      const stance = FAC_BY_ID[h.dominant_faction_id].stance;
      popControl[stance] += h.population;
    });
    const popSum = HEXES.reduce((a, h) => a + h.population, 0);
    return {
      hab: (hab / popSum),
      heat: (heat / popSum),
      uphold: popControl.UPHOLD / popSum,
      ignore: popControl.IGNORE / popSum,
      abolish: popControl.ABOLISH / popSum,
      contested: HEXES.filter(h => h.contested).length,
    };
  }, []);

  const labelStyle = { fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", textTransform: "uppercase", color: "var(--ash)" };
  const chipStyle = { background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 4, padding: "4px 10px", display: "flex", gap: 6, alignItems: "center" };

  // Variant: which faction is foregrounded in detail panel
  const variantPanelFaction = (variant === "faction" || factionFilter) ? (factionFilter || "FAC_DECOLONIAL") : null;

  return (
    <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--void)", fontFamily: "var(--font-sans)", color: "var(--bone)", position: "relative" }}>

      {/* TOP BAR */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        borderBottom: "1px solid var(--rebar)", background: "var(--void)",
        padding: "9px 16px", flexShrink: 0, gap: 12
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase" }}>babylon · the cockpit</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--shroud)" }}>·</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--spire)", letterSpacing: ".18em", textTransform: "uppercase" }}>▸ the map</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)", marginLeft: 6 }}>epoch 3 · the collapse</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, padding: "0 12px", borderLeft: "1px solid var(--rebar)", borderRight: "1px solid var(--rebar)" }}>
            <span style={labelStyle}>Tick</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 700, color: "var(--spire)", textShadow: "0 0 12px rgba(77,217,230,.4)" }}>{String(tick).padStart(4, "0")}</span>
          </div>
          <div style={{ display: "flex", gap: 5 }}>
            {[
              { lbl: "HAB",  val: globalMetrics.hab.toFixed(3),  col: globalMetrics.hab > 0.5 ? "#5fbf7a" : "#ff3344" },
              { lbl: "HEAT", val: globalMetrics.heat.toFixed(3), col: "#d97a2c" },
              { lbl: "CONT", val: globalMetrics.contested.toString(), col: "#d4a02c" },
              { lbl: "DOM·U", val: (globalMetrics.uphold * 100).toFixed(0) + "%", col: "#ff3344" },
              { lbl: "DOM·I", val: (globalMetrics.ignore * 100).toFixed(0) + "%", col: "#6b8fb5" },
              { lbl: "DOM·A", val: (globalMetrics.abolish * 100).toFixed(0) + "%", col: "#5fbf7a" },
            ].map(m => (
              <div key={m.lbl} style={chipStyle}>
                <span style={labelStyle}>{m.lbl}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: m.col }}>{m.val}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <GhostButton>Log</GhostButton>
          <GhostButton>Dialectic</GhostButton>
          <button onClick={() => setTick(t => t + 1)} style={{
            background: "var(--spire)", color: "var(--void)", border: "none",
            borderRadius: 4, padding: "6px 14px", fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700,
            letterSpacing: ".18em", textTransform: "uppercase",
            cursor: "pointer", boxShadow: "0 0 14px rgba(77,217,230,.25)"
          }}>▸ Resolve Tick</button>
        </div>
      </div>

      {/* SOVEREIGN ROSTER BAR */}
      <div style={{ flexShrink: 0, padding: "8px 12px" }}>
        <SovereignRoster selectedFaction={factionFilter}
          onSelectFaction={f => { setFactionFilter(f); if (f) setLens("faction"); else if (lens === "faction") setLens("stance"); }} />
      </div>

      {/* MAIN AREA */}
      <div style={{ display: "flex", minHeight: 0, flex: 1, overflow: "hidden" }}>

        {/* Center: map + lens bar + bottom panel */}
        <div style={{ display: "flex", minWidth: 0, flex: 1, flexDirection: "column", overflow: "hidden" }}>
          {/* MAP */}
          <div style={{ flex: 1, padding: 10, overflow: "hidden", minHeight: 0 }}>
            <div style={{ height: "100%", borderRadius: 6, border: "1px solid var(--rebar)", background: "#0a0d13", position: "relative", overflow: "hidden" }}>
              <HexMap lens={lens} factionFilter={lens === "faction" ? factionFilter : null}
                showBoundaries={showBoundaries && lens !== "heat" && lens !== "habitability"}
                showRings={showRings}
                showContested={showContested}
                showStateLines={showStateLines}
                hoveredId={hoveredHex?.id} selectedId={selectedHex?.id}
                onHexHover={setHoveredHex} onHexClick={setSelectedHex}
                collapseFrame={pulse}
              />

              {/* Hover tooltip */}
              {hoveredHex && (
                <HexTooltip hex={hoveredHex}
                  anchorX={(hoveredHex.cx / 940) * 100}
                  anchorY={(hoveredHex.cy / 500) * 100}/>
              )}

              {/* Legend - bottom right */}
              <div style={{ position: "absolute", bottom: 12, right: 12, zIndex: 5 }}>
                <MapLegend lens={lens} factionFilter={factionFilter}/>
              </div>

              {/* Title label - top left */}
              <div style={{ position: "absolute", top: 12, left: 14, zIndex: 5 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: ".22em", textTransform: "uppercase", marginBottom: 2 }}>Continental US · post-fracture</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)", letterSpacing: ".05em", fontStyle: "italic" }}>
                  {lens === "stance" && "Lens: colonial_stance + influence"}
                  {lens === "heat" && "Lens: heat — state attention pressure"}
                  {lens === "habitability" && "Lens: habitability — the metabolic rift"}
                  {lens === "faction" && factionFilter && `Lens: filtered to ${FAC_BY_ID[factionFilter].name}`}
                  {lens === "collapse" && `Event: SOVEREIGN_COLLAPSE · tick ${tick}`}
                </div>
              </div>

              {/* Collapse-lens overlay banner */}
              {isCollapse && (
                <div style={{ position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)", background: "rgba(255,51,68,.12)", border: "1px solid #ff3344", borderRadius: 4, padding: "5px 12px", zIndex: 5, backdropFilter: "blur(4px)" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#ff3344", letterSpacing: ".22em", textTransform: "uppercase", fontWeight: 700 }}>● collapse_transition · tick {tick}</span>
                </div>
              )}

              {/* Scanlines overlay */}
              <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(0deg, rgba(0,0,0,.10) 0, rgba(0,0,0,.10) 1px, transparent 1px, transparent 3px)", pointerEvents: "none" }}/>
              {/* Vignette */}
              <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 80% 80% at center, transparent 50%, rgba(0,0,0,.65) 100%)", pointerEvents: "none" }}/>
            </div>
          </div>

          {/* LENS BAR */}
          <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 4, borderTop: "1px solid var(--rebar)", background: "var(--void)", padding: "5px 12px" }}>
            <span style={{ ...labelStyle, marginRight: 8 }}>Lens</span>
            <LensTab active={lens === "stance"} onClick={() => { setLens("stance"); setFactionFilter(null); }} icon="◆">Stance</LensTab>
            <LensTab active={lens === "heat"} onClick={() => setLens("heat")} icon="◉">Heat</LensTab>
            <LensTab active={lens === "habitability"} onClick={() => setLens("habitability")} icon="❋">Habitability</LensTab>
            <LensTab active={lens === "faction"} onClick={() => { setLens("faction"); if (!factionFilter) setFactionFilter("FAC_DECOLONIAL"); }} icon="◎">Faction Filter</LensTab>
            <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
              <span style={labelStyle}>Show</span>
              <button style={{ background: "transparent", border: "1px solid var(--rebar)", borderRadius: 3, padding: "3px 8px", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>Boundaries</button>
              <button style={{ background: "transparent", border: "1px solid var(--rebar)", borderRadius: 3, padding: "3px 8px", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>Rings</button>
              <button style={{ background: "transparent", border: "1px solid var(--rebar)", borderRadius: 3, padding: "3px 8px", fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", cursor: "pointer", letterSpacing: ".14em", textTransform: "uppercase" }}>Cities</button>
            </div>
          </div>

          {/* BOTTOM PANEL - Event log */}
          <div style={{ flexShrink: 0, borderTop: "1px solid var(--rebar)", background: "var(--void)", height: bottomOpen ? 138 : 36, transition: "height .2s", overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 12px", background: "var(--concrete)", borderBottom: bottomOpen ? "1px solid var(--rebar)" : "none" }}>
              <button onClick={() => setBottomOpen(o => !o)} style={{ width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "1px solid var(--rebar)", borderRadius: 3, color: "var(--fog)", cursor: "pointer", fontSize: 9 }}>{bottomOpen ? "▼" : "▲"}</button>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 500, color: "var(--spire)", borderBottom: "1px solid var(--spire)", padding: "3px 10px", letterSpacing: ".14em", textTransform: "uppercase" }}>Event Log</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", padding: "3px 10px", letterSpacing: ".14em", textTransform: "uppercase" }}>Topology</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", padding: "3px 10px", letterSpacing: ".14em", textTransform: "uppercase" }}>Notifications</span>
              {isCollapse && <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 9, color: "#ff3344", letterSpacing: ".22em", textTransform: "uppercase", fontWeight: 700 }}>● live</span>}
            </div>
            {bottomOpen && (
              <div style={{ padding: "8px 14px", overflowY: "auto", height: 100 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  {(isCollapse ? COLLAPSE_EVENTS : COLLAPSE_EVENTS.slice(0, 4)).map((e, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: e.severity === "critical" ? "#ff3344" : e.severity === "warning" ? "#d97a2c" : "#5fbf7a", minWidth: 12 }}>●</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: "var(--ash)", minWidth: 130, letterSpacing: ".12em" }}>{e.type}</span>
                      <span style={{ fontFamily: "var(--font-sans)", fontSize: 11, color: "var(--bone)", flex: 1 }}>{e.msg}</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)", marginLeft: "auto" }}>t={e.tick}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT PANEL: Hex or Faction Detail */}
        <div style={{ width: 312, flexShrink: 0, borderLeft: "1px solid var(--rebar)", background: "var(--void)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10, overflowY: "auto", flex: 1 }}>
            {variantPanelFaction && (
              <FactionDetailCard factionId={variantPanelFaction} onClear={() => { setFactionFilter(null); if (lens === "faction") setLens("stance"); }}/>
            )}
            <HexDetailCard hex={selectedHex || hoveredHex}/>
            {!variantPanelFaction && (
              <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: 12 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: ".22em", color: "var(--ash)", textTransform: "uppercase", marginBottom: 7 }}>▸ Theory note</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", lineHeight: 1.55, fontStyle: "italic" }}>
                  Influence ≠ legitimacy. Influence is what a faction <em style={{ color: "#d4a02c", fontStyle: "normal" }}>can</em> claim on collapse. Legitimacy is what they <em style={{ color: "#d4a02c", fontStyle: "normal" }}>can hold</em>.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { MapShell, SovereignRoster, HexDetailCard, FactionDetailCard });
