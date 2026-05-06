// ============================================================================
// Babylon Frontend v2 — Verb Pages (9) + Analysis
// /games/:id/actions/<verb> — one route per verb, target-type-gated
// /games/:id/analysis — full-size charts + UpSet plot
// ============================================================================

// Resolve the gated target list per verb's declared target_type.
// CRITICAL: never one big dropdown. Per Constitution Article IV (dual graph),
// hyperedges and dyadic nodes are NEVER conflated.
function resolveTargets(verb) {
  const tt = verb.target_type;
  if (tt === "community") {
    return COMMUNITIES.map(c => ({
      id: c.id, type: "community", label: c.name,
      sub: `${c.composition.join(" · ")} · ${c.members.toLocaleString()} ppl`,
      color: CLASS_COLORS[c.dominant_class],
      meta: c, telemetry: { CON: c.con, SOL: c.sol }
    }));
  }
  if (tt === "territory") {
    return TERRITORIES.map(t => ({
      id: t.id, type: "territory", label: t.name,
      sub: `${t.county} County · pop ${t.pop.toLocaleString()}`,
      color: "#80b0e0",
      meta: t, telemetry: { HEAT: t.heat, RENT: t.rent }
    }));
  }
  if (tt === "org") {
    return ORGS.map(o => ({
      id: o.id, type: "org", label: o.short,
      sub: `${o.name}${o.player_controlled ? " · ALLIED" : " · ENEMY"}`,
      color: CLASS_COLORS[o.class_character],
      meta: o, telemetry: { COH: o.cohesion, OPC: o.opacity }
    }));
  }
  if (tt === "org_or_territory") {
    return [
      ...ORGS.filter(o => !o.player_controlled).map(o => ({
        id: o.id, type: "org", label: o.short, sub: `${o.name} · ENEMY`,
        color: CLASS_COLORS[o.class_character], meta: o,
        telemetry: { COH: o.cohesion, OPC: o.opacity }
      })),
      ...TERRITORIES.map(t => ({
        id: t.id, type: "territory", label: t.name,
        sub: `${t.county} County · pop ${t.pop.toLocaleString()}`,
        color: "#80b0e0", meta: t, telemetry: { HEAT: t.heat, RENT: t.rent }
      })),
    ];
  }
  if (tt === "territory_or_community") {
    return [
      ...TERRITORIES.map(t => ({
        id: t.id, type: "territory", label: t.name,
        sub: `${t.county} County`, color: "#80b0e0", meta: t,
        telemetry: { HEAT: t.heat, RENT: t.rent }
      })),
      ...COMMUNITIES.map(c => ({
        id: c.id, type: "community", label: c.name,
        sub: c.composition.join(" · "),
        color: CLASS_COLORS[c.dominant_class], meta: c,
        telemetry: { CON: c.con, SOL: c.sol }
      })),
    ];
  }
  if (tt === "any") {
    return [
      ...ORGS.filter(o => !o.player_controlled).map(o => ({
        id: o.id, type: "org", label: o.short, sub: `${o.name} · ENEMY`,
        color: CLASS_COLORS[o.class_character], meta: o,
        telemetry: { OPC: o.opacity }
      })),
      ...EDGES.map(e => ({
        id: e.id, type: "edge", label: e.type,
        sub: `${e.source} → ${e.target} · ${(e.intensity*100).toFixed(0)}%`,
        color: EDGE_COLORS[e.type], meta: e,
        telemetry: { INT: e.intensity }
      })),
      ...TERRITORIES.map(t => ({
        id: t.id, type: "territory", label: t.name,
        sub: `${t.county} County`, color: "#80b0e0", meta: t,
        telemetry: { HEAT: t.heat }
      })),
      ...COMMUNITIES.map(c => ({
        id: c.id, type: "community", label: c.name,
        sub: c.composition.join(" · "),
        color: CLASS_COLORS[c.dominant_class], meta: c,
        telemetry: { CON: c.con }
      })),
    ];
  }
  return [];
}

// Per-verb form schema — verb-specific params shown in the right panel.
function getVerbParams(verb) {
  switch (verb.verb) {
    case "educate":  return [
      { key: "method", label: "Method", kind: "radio", options: ["Study Circle", "Mass Line", "Agitation"] },
      { key: "intensity", label: "Cadre commitment", kind: "slider", min: 1, max: 8, default: 3, unit: "CL" },
    ];
    case "mobilize": return [
      { key: "vehicle", label: "Vehicle", kind: "radio", options: ["Mass Action", "General Strike", "Block Org"] },
      { key: "intensity", label: "Sympathizer draw", kind: "slider", min: 1, max: 12, default: 5, unit: "SL" },
    ];
    case "aid":      return [
      { key: "kind", label: "Aid kind", kind: "radio", options: ["Material", "Legal", "Medical", "Financial"] },
      { key: "amount", label: "Amount", kind: "slider", min: 10, max: 200, default: 50, unit: "$" },
    ];
    case "attack":   return [
      { key: "method", label: "Method", kind: "radio", options: ["Sabotage", "Disruption", "Direct Action"] },
      { key: "force", label: "Force", kind: "slider", min: 2, max: 12, default: 6, unit: "CL" },
      { key: "expose", label: "Accept exposure (+heat)", kind: "toggle", default: false },
    ];
    case "campaign": return [
      { key: "frame", label: "Framing", kind: "radio", options: ["Class", "Anti-Imperialist", "Communal"] },
      { key: "duration", label: "Sustained ticks", kind: "slider", min: 1, max: 6, default: 2, unit: "ticks" },
    ];
    case "move":     return [
      { key: "what", label: "Move", kind: "radio", options: ["HQ", "Cadre Cell", "Sympathizer Network"] },
    ];
    case "investigate": return [
      { key: "depth", label: "Depth", kind: "radio", options: ["Surveil", "Penetrate", "Forensic"] },
      { key: "intensity", label: "Cadre commitment", kind: "slider", min: 1, max: 6, default: 2, unit: "CL" },
    ];
    case "reproduce":   return [
      { key: "track", label: "Track", kind: "radio", options: ["Convert SL→CL", "Train Successor", "Found Cell"] },
      { key: "intensity", label: "Resources", kind: "slider", min: 5, max: 20, default: 10, unit: "CL" },
    ];
    case "negotiate":   return [
      { key: "stance", label: "Stance", kind: "radio", options: ["Coalition", "Cease-Fire", "Tactical Alliance"] },
      { key: "concede", label: "Willing to concede", kind: "toggle", default: false },
    ];
    default: return [];
  }
}

// ============================================================================
// VerbPage — single template, gated by verb.target_type
// ============================================================================
const VerbPage = ({ verb, onNavigate, currentOrgId, onSelectOrg }) => {
  const playerOrgs = ORGS.filter(o => o.player_controlled);
  const [activeOrg, setActiveOrg] = React.useState(currentOrgId || playerOrgs[0].id);
  const targets = resolveTargets(verb);
  const [filter, setFilter] = React.useState("all");
  const filtered = filter === "all" ? targets : targets.filter(t => t.type === filter);
  const [selectedId, setSelectedId] = React.useState(filtered[0]?.id);
  const selected = targets.find(t => t.id === selectedId) || filtered[0];
  const params = getVerbParams(verb);
  const [paramVals, setParamVals] = React.useState(() =>
    Object.fromEntries(params.map(p => [p.key, p.default ?? (p.options ? p.options[0] : 0)]))
  );
  const targetTypes = [...new Set(targets.map(t => t.type))];

  const org = ORGS.find(o => o.id === activeOrg);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <PageHeader title={`Action · ${verb.label}`}
        subtitle={verb.desc}
        breadcrumbs={["Operation", "Actions", verb.label]}
        right={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <BblBadge color="#c8a860">target type · {verb.target_type.replace(/_/g, " ")}</BblBadge>
            <BblBadge color="#80b0e0">cost · {verb.cost_label}</BblBadge>
          </div>
        }/>
      <div style={{ flex: 1, display: "grid",
                     gridTemplateColumns: "240px 1fr 320px",
                     gap: 12, padding: 12, minHeight: 0 }}>
        {/* 1. Actor (player org) selection */}
        <BblPanel title="Acting Org" right={<BblLabel>required</BblLabel>}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {playerOrgs.map(o => {
              const active = o.id === activeOrg;
              const v = o.vanguard;
              return (
                <button key={o.id} onClick={() => { setActiveOrg(o.id); onSelectOrg && onSelectOrg(o.id); }} style={{
                  textAlign: "left", padding: "10px 12px",
                  background: active ? "rgba(200,168,96,.1)" : "#0a0a0f",
                  border: active ? "1px solid #c8a860" : "1px solid #1a1a2a",
                  borderRadius: 6, color: "#e0e0e0", cursor: "pointer",
                  fontFamily: "var(--font-sans)"
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600 }}>{o.short}</div>
                  <div style={{ fontSize: 9, color: "#787878", marginTop: 2 }}>{o.ooda_phase} · COH {(o.cohesion*100).toFixed(0)}%</div>
                  <div style={{ display: "flex", gap: 8, marginTop: 6, fontFamily: "var(--font-mono)", fontSize: 9 }}>
                    <span style={{ color: "#80b0e0" }}>{v.cl} CL</span>
                    <span style={{ color: "#40c040" }}>{v.sl} SL</span>
                    <span style={{ color: "#c8a860" }}>${v.budget}</span>
                  </div>
                </button>
              );
            })}
          </div>
          <div style={{ marginTop: 16 }}>
            <BblLabel>Other Verbs</BblLabel>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 4, marginTop: 6 }}>
              {VERBS.map(v => {
                const active = v.verb === verb.verb;
                return (
                  <BblTooltip key={v.verb} text={`${v.label} → ${v.target_type.replace(/_/g, " ")}`}>
                    <button onClick={() => onNavigate(verbRouteKey(v.verb))} style={{
                      aspectRatio: "1", background: active ? "rgba(200,168,96,.15)" : "#0a0a0f",
                      border: active ? "1px solid #c8a860" : "1px solid #1a1a2a",
                      color: active ? "#c8a860" : "#787878",
                      fontSize: 14, fontFamily: "var(--font-mono)", cursor: "pointer",
                      borderRadius: 4, width: "100%"
                    }}>{v.glyph}</button>
                  </BblTooltip>
                );
              })}
            </div>
          </div>
        </BblPanel>

        {/* 2. Target selection — GATED list */}
        <BblPanel title={`Eligible Targets (${filtered.length})`}
          right={
            targetTypes.length > 1 ? (
              <div style={{ display: "flex", gap: 4 }}>
                <FilterChip active={filter === "all"} onClick={() => setFilter("all")}>all</FilterChip>
                {targetTypes.map(t => (
                  <FilterChip key={t} active={filter === t} onClick={() => setFilter(t)}>{t}</FilterChip>
                ))}
              </div>
            ) : (
              <BblBadge color="#787878">{verb.target_type.replace(/_/g," ")}</BblBadge>
            )
          }
          style={{ minHeight: 0 }}>
          <div style={{ height: "100%", overflow: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
            {filtered.map(t => {
              const isSel = t.id === selected?.id;
              return (
                <button key={t.id} onClick={() => setSelectedId(t.id)} style={{
                  display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 12,
                  alignItems: "center", padding: "10px 12px",
                  background: isSel ? "rgba(200,168,96,.08)" : "#0a0a0f",
                  border: isSel ? "1px solid #c8a860" : "1px solid #1a1a2a",
                  borderRadius: 6, color: "#e0e0e0", cursor: "pointer",
                  textAlign: "left", fontFamily: "var(--font-sans)"
                }}>
                  <div style={{ width: 4, height: 36, background: t.color, borderRadius: 2 }}/>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{t.label}</span>
                      <BblBadge color={t.color}>{t.type}</BblBadge>
                    </div>
                    <div style={{ fontSize: 10, color: "#787878", marginTop: 2 }}>{t.sub}</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 2 }}>
                    {Object.entries(t.telemetry).map(([k, v]) => (
                      <div key={k} style={{ display: "flex", gap: 4, fontFamily: "var(--font-mono)", fontSize: 9 }}>
                        <span style={{ color: "#404040" }}>{k}</span>
                        <span style={{ color: t.color }}>{(v*100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </button>
              );
            })}
            {!filtered.length && (
              <div style={{ padding: 20, textAlign: "center", color: "#787878", fontSize: 11 }}>
                No eligible targets of that type.
              </div>
            )}
          </div>
        </BblPanel>

        {/* 3. Compose & Submit */}
        <BblPanel title="Compose Action" accent="#c8a860">
          <div style={{ display: "flex", flexDirection: "column", gap: 14, height: "100%" }}>
            <div style={{ padding: 10, background: "#0a0a0f", border: "1px solid #1a1a2a",
                           borderRadius: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <BblLabel>Selected target</BblLabel>
                {selected && <BblBadge color={selected.color}>{selected.type}</BblBadge>}
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#e0e0e0", marginTop: 4 }}>
                {selected?.label || "—"}
              </div>
              <div style={{ fontSize: 10, color: "#787878", marginTop: 2 }}>{selected?.sub}</div>
            </div>

            {params.map(p => (
              <div key={p.key}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                  <BblLabel>{p.label}</BblLabel>
                  {p.kind === "slider" && <BblData color="#c8a860" size={11}>{paramVals[p.key]} {p.unit}</BblData>}
                </div>
                {p.kind === "radio" && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {p.options.map(opt => (
                      <button key={opt}
                        onClick={() => setParamVals(v => ({ ...v, [p.key]: opt }))}
                        style={{
                          padding: "6px 10px", fontSize: 10,
                          background: paramVals[p.key] === opt ? "rgba(200,168,96,.15)" : "transparent",
                          border: paramVals[p.key] === opt ? "1px solid #c8a860" : "1px solid #2a2a3a",
                          color: paramVals[p.key] === opt ? "#c8a860" : "#787878",
                          borderRadius: 4, cursor: "pointer", fontFamily: "var(--font-sans)"
                        }}>{opt}</button>
                    ))}
                  </div>
                )}
                {p.kind === "slider" && (
                  <input type="range" min={p.min} max={p.max} value={paramVals[p.key]}
                    onChange={e => setParamVals(v => ({ ...v, [p.key]: Number(e.target.value) }))}
                    style={{ width: "100%", accentColor: "#c8a860" }}/>
                )}
                {p.kind === "toggle" && (
                  <button onClick={() => setParamVals(v => ({ ...v, [p.key]: !v[p.key] }))}
                    style={{
                      padding: "6px 12px", fontSize: 10,
                      background: paramVals[p.key] ? "rgba(224,64,64,.15)" : "transparent",
                      border: paramVals[p.key] ? "1px solid #e04040" : "1px solid #2a2a3a",
                      color: paramVals[p.key] ? "#e04040" : "#787878",
                      borderRadius: 4, cursor: "pointer", fontFamily: "var(--font-sans)"
                    }}>{paramVals[p.key] ? "ENABLED" : "OFF"}</button>
                )}
              </div>
            ))}

            <div style={{ marginTop: 6, padding: 10, background: "rgba(200,168,96,.05)",
                           border: "1px dashed #c8a86055", borderRadius: 4 }}>
              <BblLabel color="#c8a860">Predicted Outcome</BblLabel>
              <PredictionLines verb={verb} target={selected} org={org}/>
            </div>

            <div style={{ flex: 1 }}/>

            <button style={{
              padding: "12px 14px", background: "#c8a860", color: "#0a0a0f",
              border: "none", borderRadius: 6, fontWeight: 700, letterSpacing: ".2em",
              fontSize: 11, textTransform: "uppercase", cursor: "pointer",
              fontFamily: "var(--font-sans)"
            }}>Queue {verb.label} ▸</button>
            <div style={{ fontSize: 9, color: "#404040", textAlign: "center", lineHeight: 1.5 }}>
              POST /api/games/{`{id}`}/actions/<br/>
              {`{verb: "${verb.verb}", target_id: "${selected?.id || "..."}", params: {...}}`}
            </div>
          </div>
        </BblPanel>
      </div>
    </div>
  );
};

const FilterChip = ({ active, onClick, children }) => (
  <button onClick={onClick} style={{
    background: active ? "rgba(200,168,96,.15)" : "transparent",
    border: active ? "1px solid #c8a860" : "1px solid #2a2a3a",
    color: active ? "#c8a860" : "#787878",
    fontSize: 9, padding: "3px 8px", letterSpacing: ".15em",
    textTransform: "uppercase", borderRadius: 4, cursor: "pointer",
    fontFamily: "var(--font-sans)"
  }}>{children}</button>
);

const PredictionLines = ({ verb, target, org }) => {
  // Mocked predictions — production would call /api/predict
  const preds = {
    educate:  [["+0.04 CON",  "#80b0e0"], ["+0.02 SOL",  "#40c040"], ["−3 CL",   "#404040"]],
    mobilize: [["+0.07 SOL",  "#40c040"], ["+0.04 HEAT", "#e04040"], ["−5 SL",   "#404040"]],
    aid:      [["+0.05 LEG",  "#40c040"], ["+0.03 CRED", "#c8a860"], ["−$50",    "#404040"]],
    attack:   [["−0.08 OPC (target)", "#a070d0"], ["+0.12 HEAT", "#e04040"], ["−8 CL",   "#404040"]],
    campaign: [["+0.06 CON",  "#80b0e0"], ["+0.04 LEG",  "#40c040"], ["−4 CL/tick","#404040"]],
    move:     [["HQ relocates", "#80b0e0"], ["−0.05 OPC", "#a070d0"], ["−1 CL",   "#404040"]],
    investigate: [["−0.18 OPC (target)", "#a070d0"], ["+0.05 INTEL", "#c8a860"], ["−2 CL",  "#404040"]],
    reproduce:[["+1 CL", "#80b0e0"], ["+2 SL", "#40c040"], ["−10 CL upfront", "#404040"]],
    negotiate:[["edge formed", "#40c040"], ["−0.04 LEG (risk)", "#e04040"], ["−1 CL", "#404040"]],
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 6 }}>
      {(preds[verb.verb] || []).map(([txt, c], i) => (
        <div key={i} style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: c }}>{txt}</div>
      ))}
    </div>
  );
};

// ============================================================================
// /games/:id/analysis — full-size charts + UpSet plot + scrubber
// ============================================================================
const AnalysisPage = ({ tick }) => {
  const series = [
    ["Imperial Rent",   TIMESERIES.imperial_rent,   "#a070d0"],
    ["Consciousness",   TIMESERIES.consciousness,   "#80b0e0"],
    ["Solidarity",      TIMESERIES.solidarity,      "#40c040"],
    ["Heat",            TIMESERIES.heat,            "#e04040"],
    ["Wealth",          TIMESERIES.wealth,          "#c8a860"],
    ["Biocapacity",     TIMESERIES.biocapacity,     "#7ab038"],
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <PageHeader title="Analysis"
        subtitle="Full-bleed time series, UpSet intersection plot, tick scrubber. Read-only — no action composer."
        breadcrumbs={["Operation", "Analysis"]}
        right={<BblBadge color="#787878">read-only</BblBadge>}/>
      <div style={{ flex: 1, padding: 12, display: "grid",
                     gridTemplateColumns: "1fr 1fr", gridTemplateRows: "auto 1fr auto",
                     gap: 12, minHeight: 0, overflow: "auto" }}>
        {series.map(([label, data, color], i) => (
          <BblPanel key={label} title={label} style={{ minHeight: 200,
              gridColumn: i < 2 ? "auto" : "auto" }}
            right={<BblData color={color} size={14}>{data[data.length-1].toFixed(3)}</BblData>}>
            <FullChart data={data} color={color} />
          </BblPanel>
        ))}
        <BblPanel title="Community Intersection · UpSet Plot"
          style={{ gridColumn: "1 / span 2", gridRow: "3" }}>
          <UpSetPlot/>
        </BblPanel>
      </div>
      <Scrubber tick={tick}/>
    </div>
  );
};

const FullChart = ({ data, color }) => {
  const w = 480, h = 140, pad = 22;
  const min = Math.min(...data, 0), max = Math.max(...data, 1);
  const span = max - min || 1;
  const step = (w - pad*2) / (data.length - 1);
  const pts = data.map((v, i) => `${pad + i * step},${h - pad - ((v - min) / span) * (h - pad*2)}`).join(" ");
  // Area
  const area = `${pad},${h - pad} ${pts} ${pad + (data.length-1)*step},${h - pad}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" style={{ display: "block" }}>
      {/* gridlines */}
      {[0.25, 0.5, 0.75].map(g => (
        <line key={g} x1={pad} y1={pad + g*(h - pad*2)} x2={w-pad} y2={pad + g*(h - pad*2)}
          stroke="#1a1a2a" strokeWidth="1" strokeDasharray="2 3"/>
      ))}
      <polygon points={area} fill={color} fillOpacity={.08}/>
      <polyline points={pts} stroke={color} strokeWidth="1.6" fill="none"/>
      {data.map((v, i) => (
        <circle key={i} cx={pad + i*step} cy={h - pad - ((v - min) / span) * (h - pad*2)}
                r="1.5" fill={color}/>
      ))}
      {/* axis labels */}
      <text x={pad} y={h - 4} fontSize="8" fill="#404040" fontFamily="var(--font-mono)">T-{data.length}</text>
      <text x={w-pad} y={h - 4} textAnchor="end" fontSize="8" fill="#404040" fontFamily="var(--font-mono)">T-0</text>
      <text x={pad - 4} y={pad + 4} textAnchor="end" fontSize="8" fill="#404040" fontFamily="var(--font-mono)">{max.toFixed(2)}</text>
      <text x={pad - 4} y={h - pad} textAnchor="end" fontSize="8" fill="#404040" fontFamily="var(--font-mono)">{min.toFixed(2)}</text>
    </svg>
  );
};

const UpSetPlot = () => {
  const groups = ["NEW_AFRIKAN","SETTLER","WOMEN","INCARCERATED","WORKING_CLASS","HOMEOWNERS"];
  const intersections = [
    { sets: ["NEW_AFRIKAN","WORKING_CLASS"], n: 8400 },
    { sets: ["NEW_AFRIKAN","INCARCERATED","WORKING_CLASS"], n: 11200 },
    { sets: ["WOMEN","WORKING_CLASS"], n: 22100 },
    { sets: ["SETTLER","HOMEOWNERS"], n: 14800 },
    { sets: ["NEW_AFRIKAN","WOMEN","WORKING_CLASS"], n: 6300 },
  ];
  const max = Math.max(...intersections.map(i => i.n));
  const cellW = 80, rowH = 22, leftPad = 140;
  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={leftPad + intersections.length * cellW + 20} height={groups.length * rowH + 130}>
        {/* group labels */}
        {groups.map((g, i) => (
          <text key={g} x={leftPad - 10} y={130 + i * rowH + rowH/2 + 3}
                fontSize="10" textAnchor="end" fill="#a0a0a0" fontFamily="var(--font-sans)">{g}</text>
        ))}
        {/* bars */}
        {intersections.map((it, i) => {
          const x = leftPad + i * cellW + cellW/2;
          const barH = (it.n / max) * 80;
          return (
            <g key={i}>
              <rect x={x - 14} y={104 - barH} width={28} height={barH}
                    fill="#c8a860" fillOpacity={.85}/>
              <text x={x} y={100 - barH} textAnchor="middle" fontSize="9"
                    fill="#c8a860" fontFamily="var(--font-mono)">{(it.n/1000).toFixed(1)}k</text>
              {/* dots */}
              {groups.map((g, gi) => {
                const inSet = it.sets.includes(g);
                return (
                  <circle key={g} cx={x} cy={130 + gi * rowH + rowH/2}
                          r="5" fill={inSet ? "#c8a860" : "#1a1a2a"}
                          stroke="#1a1a2a" strokeWidth="1"/>
                );
              })}
              {/* connector line through dots in this intersection */}
              {it.sets.length > 1 && (() => {
                const idxs = it.sets.map(s => groups.indexOf(s)).sort((a,b)=>a-b);
                return (
                  <line x1={x} y1={130 + idxs[0]*rowH + rowH/2}
                        x2={x} y2={130 + idxs[idxs.length-1]*rowH + rowH/2}
                        stroke="#c8a860" strokeWidth="1.4"/>
                );
              })()}
            </g>
          );
        })}
        <text x={10} y={20} fontSize="9" fill="#787878" fontFamily="var(--font-sans)" letterSpacing=".15em">INTERSECTION SIZE</text>
        <text x={10} y={120} fontSize="9" fill="#787878" fontFamily="var(--font-sans)" letterSpacing=".15em">MEMBERSHIP</text>
      </svg>
    </div>
  );
};

const Scrubber = ({ tick }) => {
  const [val, setVal] = React.useState(tick);
  return (
    <div style={{ padding: "10px 16px", borderTop: "1px solid #1a1a2a",
                   display: "flex", alignItems: "center", gap: 14,
                   background: "#0a0a0f", flexShrink: 0 }}>
      <BblLabel>Tick scrubber</BblLabel>
      <input type="range" min={0} max={tick} value={val} onChange={e => setVal(Number(e.target.value))}
        style={{ flex: 1, accentColor: "#c8a860" }}/>
      <BblData color="#c8a860">T-{val}</BblData>
      <BblBadge color="#787878">replay-only</BblBadge>
    </div>
  );
};

Object.assign(window, { VerbPage, AnalysisPage, resolveTargets, getVerbParams });
