// view-inspector.jsx — Territory Intel page with community composition badges.
// Route: /games/:id/intel/territory/:territory_id
// Article VIII.9: badges on inspector panels = the third legitimate rendering.

function InspectorView() {
  // Mock: a single territory in DEEP (Black Belt). The composition is the
  // region archetype rendered at full resolution; this is what you'd see after
  // clicking a hex in the choropleth view.
  const territory = {
    id: "TER_DEEP_S04",
    name: "Lower Mississippi Belt · S04",
    region: "Deep South",
    hexes: 18,
    population: 412000,
    habitability: 0.34,
    heat: 0.71,
    sovereign: "Restorationist Authority",
    contested: true,
  };

  const composition = {
    SETTLER: 0.412, NEW_AFRIKAN: 0.408, WORKING: 0.59, WOMEN: 0.52,
    LABOR_ARIST: 0.08, INCARCERATED: 0.022, QUEER: 0.041,
  };
  const baseline = {
    SETTLER: 0.61, NEW_AFRIKAN: 0.13, WORKING: 0.52, WOMEN: 0.51,
    LABOR_ARIST: 0.21, INCARCERATED: 0.007, QUEER: 0.045,
  };

  // Intersections that include this territory's largest sub-population
  const localIntersections = [
    { ids: ["NEW_AFRIKAN","WORKING","WOMEN"], count: 84000, note: "Reproductive labor + national + class" },
    { ids: ["NEW_AFRIKAN","WORKING"],          count: 68000 },
    { ids: ["NEW_AFRIKAN","INCARCERATED"],     count: 9000,  note: "5.3× national rate." },
    { ids: ["SETTLER","LABOR_ARIST"],          count: 28000 },
  ];

  return (
    <div style={{
      width: "100%", height: "100%", display: "flex", flexDirection: "column",
      background: "var(--void)", color: "var(--bone)", overflow: "hidden",
    }}>
      <TopBar route={["Game · DET-070", "Intel", "Territory", "TER_DEEP_S04"]}/>
      <SubTabs active="composition" tabs={[
        { id: "summary",     label: "Summary" },
        { id: "composition", label: "Composition" },
        { id: "orgs",        label: "Orgs Present" },
        { id: "edges",       label: "Edges" },
      ]}/>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 380px",
        gap: 12, padding: 16, minHeight: 0 }}>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          {/* Identity + status strip */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 16px",
            background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 5,
          }}>
            <div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
                letterSpacing: ".22em" }}>TERRITORY</div>
              <div style={{ fontFamily: "var(--font-sans)", fontSize: 20,
                fontWeight: 600, color: "var(--bone)", marginTop: 2, letterSpacing: "-.01em" }}>
                {territory.name}
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)",
                marginTop: 4, letterSpacing: ".06em" }}>
                {territory.id} · {territory.region} · {territory.hexes} hexes ·
                pop. {fmtCount(territory.population)}
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <StatusChip label="HEAT" value={fmtPct(territory.heat, 0)} color="var(--heat)"/>
              <StatusChip label="HABITABILITY" value={fmtPct(territory.habitability, 0)} color="var(--solidarity)" muted/>
              <StatusChip label="SOVEREIGN" value={territory.sovereign} color="var(--laser)"/>
              {territory.contested && <StatusChip label="STATUS" value="CONTESTED" color="var(--rupture)"/>}
            </div>
          </div>

          <ConstitutionBanner>
            Composition shown as <em style={{ color: "var(--bone)", fontStyle: "normal" }}>badges</em> —
            never as pairwise edges between this territory and individual community members.
          </ConstitutionBanner>

          {/* Stacked composition bar — the dominant rendering */}
          <Pane label="Community Composition" badge="badges + share">
            <div style={{ padding: "14px 16px" }}>
              {/* Stacked bar showing relative weights */}
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
                letterSpacing: ".22em", marginBottom: 6 }}>SHARES (overlapping memberships)</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {Object.entries(composition)
                  .sort((a,b) => b[1] - a[1])
                  .map(([id, share]) => {
                    const c = COMM_BY_ID[id];
                    const base = baseline[id] ?? 0;
                    const delta = share - base;
                    return (
                      <div key={id} style={{
                        display: "grid",
                        gridTemplateColumns: "10px 130px 1fr 60px 70px",
                        gap: 10, alignItems: "center",
                      }}>
                        <span style={{ width: 8, height: 8, background: c.color,
                          boxShadow: `0 0 8px ${c.color}` }}/>
                        <div>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10,
                            color: "var(--bone)", letterSpacing: ".08em",
                            textTransform: "uppercase" }}>{c.label}</div>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: 8,
                            color: "var(--shroud)", letterSpacing: ".18em" }}>{c.id}</div>
                        </div>
                        <div style={{ position: "relative", height: 12,
                          background: "var(--tar)", borderRadius: 2, overflow: "hidden" }}>
                          {/* baseline marker */}
                          <div style={{ position: "absolute", left: `${base*100}%`,
                            top: 0, bottom: 0, width: 1, background: "var(--fog)", opacity: 0.5 }}/>
                          <div style={{ width: `${share*100}%`, height: "100%",
                            background: c.color, opacity: 0.78,
                            boxShadow: `0 0 10px ${c.color}55` }}/>
                        </div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11,
                          fontWeight: 700, color: "var(--bone)", letterSpacing: "-.01em",
                          textAlign: "right" }}>
                          {fmtPct(share, 1)}
                        </div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9,
                          color: delta > 0.05 ? "var(--solidarity)" :
                                 delta < -0.05 ? "var(--laser)" : "var(--ash)",
                          letterSpacing: ".06em", textAlign: "right" }}>
                          {fmtSigned(delta, 2)} vs base
                        </div>
                      </div>
                    );
                  })}
              </div>
              <div style={{ marginTop: 10, fontFamily: "var(--font-mono)", fontSize: 9,
                color: "var(--shroud)", letterSpacing: ".06em" }}>
                Baseline = national average. Vertical tick shows the baseline share for comparison.
              </div>
            </div>
          </Pane>

          {/* Local intersections */}
          <Pane label="Salient Local Intersections" badge="from XGI hyperedge layer">
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
              {localIntersections.map((ix, i) => (
                <div key={i} style={{
                  display: "grid", gridTemplateColumns: "1fr auto",
                  gap: 12, alignItems: "center",
                  padding: "8px 10px",
                  background: "var(--tar)", border: "1px solid var(--rebar)", borderRadius: 3,
                }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {ix.ids.map((id, j) => (
                        <React.Fragment key={id}>
                          <CommBadge id={id} dense/>
                          {j < ix.ids.length-1 && <span style={{ color: "var(--ash)",
                            fontFamily: "var(--font-mono)", alignSelf: "center", fontSize: 11 }}>∩</span>}
                      </React.Fragment>
                      ))}
                    </div>
                    {ix.note && <div style={{ fontFamily: "var(--font-mono)", fontSize: 9,
                      color: "var(--rupture)", letterSpacing: ".06em" }}>{ix.note}</div>}
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 13,
                    color: "var(--bone)", fontWeight: 700, letterSpacing: "-.01em" }}>
                    {fmtCount(ix.count)}
                  </div>
                </div>
              ))}
            </div>
          </Pane>
        </div>

        {/* RIGHT RAIL */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <Pane label="Quick verbs" badge="targetable here" style={{ flexShrink: 0 }}>
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
              <VerbButton verb="Move"      target="territory" recommended/>
              <VerbButton verb="Aid"       target="territory"/>
              <VerbButton verb="Educate"   target="community NEW_AFRIKAN ∩ WORKING"/>
              <VerbButton verb="Campaign"  target="this territory"/>
              <VerbButton verb="Investigate" target="orgs present"/>
            </div>
          </Pane>

          <Pane label="Anti-pattern check" badge="Const. Art. VIII.9">
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
              <AntiPatternRow ok={true}  label="No pairwise edges between territory and members"/>
              <AntiPatternRow ok={true}  label="No spatial hull around community"/>
              <AntiPatternRow ok={true}  label="Composition shown as badges + shares"/>
              <AntiPatternRow ok={true}  label="Intersections sourced from XGI, not NetworkX"/>
            </div>
          </Pane>

          <Pane label="Linked Routes" style={{ flex: 1, minHeight: 0 }}>
            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 4,
              fontFamily: "var(--font-mono)", fontSize: 10 }}>
              <LinkedRoute route="/games/:id" label="Briefing · Map"/>
              <LinkedRoute route="/games/:id/analysis" label="UpSet · Communities"/>
              <LinkedRoute route="/games/:id/actions/educate" label="Educate verb · hyperedge target"/>
              <LinkedRoute route="/games/:id/actions/move" label="Move verb · this territory"/>
              <LinkedRoute route="/games/:id/intel/org/STATE_APP" label="Intel · State Apparatus"/>
              <div style={{ marginTop: 8, color: "var(--shroud)", letterSpacing: ".06em",
                fontStyle: "italic" }}>
                Inspector is its own route — never an inline popup. Each link is its own page.
              </div>
            </div>
          </Pane>
        </div>
      </div>
    </div>
  );
}

function StatusChip({ label, value, color, muted }) {
  return (
    <div style={{
      padding: "6px 12px",
      background: "var(--tar)", border: `1px solid ${muted ? "var(--rebar)" : color + "44"}`,
      borderRadius: 3, minWidth: 80,
    }}>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--ash)",
        letterSpacing: ".22em" }}>{label}</div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700,
        color: muted ? "var(--bone)" : color, marginTop: 1, letterSpacing: ".02em" }}>{value}</div>
    </div>
  );
}

function VerbButton({ verb, target, recommended }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "8px 10px",
      background: recommended ? "rgba(95,191,122,.06)" : "var(--tar)",
      border: `1px solid ${recommended ? "rgba(95,191,122,.32)" : "var(--rebar)"}`,
      borderRadius: 3,
      cursor: "pointer",
    }}>
      <div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700,
          color: recommended ? "var(--solidarity)" : "var(--bone)",
          letterSpacing: ".22em", textTransform: "uppercase" }}>{verb}</div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
          letterSpacing: ".04em" }}>{target}</div>
      </div>
      <span style={{ color: "var(--ash)", fontFamily: "var(--font-mono)" }}>›</span>
    </div>
  );
}

function AntiPatternRow({ ok, label }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "16px 1fr", gap: 8, alignItems: "baseline" }}>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 11,
        color: ok ? "var(--solidarity)" : "var(--laser)" }}>{ok ? "✓" : "×"}</span>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)",
        letterSpacing: ".04em" }}>{label}</span>
    </div>
  );
}

function LinkedRoute({ route, label }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline",
      padding: "3px 0", borderBottom: "1px dashed var(--rebar)" }}>
      <span style={{ color: "var(--spire)", letterSpacing: ".04em" }}>{route}</span>
      <span style={{ color: "var(--ash)", letterSpacing: ".04em" }}>{label}</span>
    </div>
  );
}
