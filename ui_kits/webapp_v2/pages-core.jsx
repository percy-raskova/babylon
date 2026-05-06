// ============================================================================
// Babylon Frontend v2 — Core In-Game Routes
// /games/:id (Briefing), /games/:id/orgs, /games/:id/intel/:type/:id, /results
// ============================================================================

// ----------------------------------------------------------------------------
// /games/:id — BRIEFING
// "Newspaper" landing page for the tick.
// Strict scope: ONE map (one framing selector), sparkline strip (3 small),
// tick narrative, end-turn nav. NO org dashboard, NO full-size charts,
// NO verb accordion.
// ----------------------------------------------------------------------------
const BriefingPage = ({ tick, onNavigate }) => {
  const sevColor = (s) => s === "critical" ? "#e04040" : s === "warning" ? "#e0a030"
                    : s === "good" ? "#40c040" : "#80b0e0";
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <PageHeader title={`Tick ${tick} Briefing`}
        subtitle="Field Dispatch · Wayne County Operation 001"
        breadcrumbs={["Operation", `Tick ${tick}`, "Briefing"]}
        right={
          <button onClick={() => onNavigate("orgs")} style={{
            background: "transparent", border: "1px solid #c8a860", color: "#c8a860",
            padding: "8px 14px", fontSize: 11, fontWeight: 700, letterSpacing: ".15em",
            textTransform: "uppercase", borderRadius: 6, cursor: "pointer",
            fontFamily: "var(--font-sans)"
          }}>Take Actions ▸</button>
        }/>
      <div style={{ flex: 1, display: "grid",
                     gridTemplateColumns: "1.4fr 1fr",
                     gridTemplateRows: "minmax(0, 1fr) auto",
                     gap: 12, padding: 12, minHeight: 0, overflow: "hidden" }}>
        {/* Map (persistent component) — single framing selector */}
        <BblPanel title="Wayne County · Layer: Heat" style={{ minHeight: 0, overflow: "hidden" }}
          right={<BblLabel color="#787878">deck.gl + MapLibre · placeholder</BblLabel>}>
          <div style={{ height: "100%", minHeight: 0 }}>
            <HexMap layer="heat" lens="economic" height="100%" />
          </div>
        </BblPanel>
        {/* Right column: tick narrative + next steps */}
        <BblPanel title="Tick Narrative" style={{ minHeight: 0, overflow: "hidden" }}>
          <div style={{ height: "100%", overflow: "auto", display: "flex",
                         flexDirection: "column", gap: 14 }}>
            <div style={{ padding: 12, background: "rgba(110,16,32,.18)",
                           border: "1px solid #6e1020", borderRadius: 6 }}>
              <BblLabel color="#e04040">Lead Dispatch</BblLabel>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#e0e0e0",
                             marginTop: 4, lineHeight: 1.4 }}>
                Informant detected in Wayne County Labor Federation
              </div>
              <div style={{ fontSize: 12, color: "#a0a0a0", marginTop: 6, lineHeight: 1.6 }}>
                Pattern-of-life analysis flagged a 6-tick anomaly in cadre meeting attendance.
                Heat elevated +0.12. Recommend immediate Investigate of the suspected edge,
                then Reproduce to harden remaining cadre. Repression edge from WCSD intensified
                to 0.71 — see Intel for the full pattern.
              </div>
              <div style={{ marginTop: 10, display: "flex", gap: 6 }}>
                <button onClick={() => onNavigate("v_invest")} style={pillBtn("#c8a860")}>
                  ▸ Investigate
                </button>
                <button onClick={() => onNavigate("v_reproduce")} style={pillBtn("#c8a860")}>
                  ▸ Reproduce
                </button>
                <button onClick={() => onNavigate("intel")} style={pillBtn("#787878")}>
                  ▸ Open Intel
                </button>
              </div>
            </div>
            <div>
              <BblLabel>Other Events This Tick</BblLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                {EVENTS.map(ev => (
                  <div key={ev.id} style={{
                    display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 10,
                    padding: "8px 10px", background: "#0a0a0f",
                    border: "1px solid #1a1a2a", borderRadius: 4
                  }}>
                    <div style={{ width: 3, alignSelf: "stretch", background: sevColor(ev.severity),
                                   borderRadius: 2 }}/>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "#e0e0e0" }}>{ev.title}</div>
                      <div style={{ fontSize: 10, color: "#787878", marginTop: 2 }}>{ev.body}</div>
                    </div>
                    <BblData color="#404040" size={9}>T{ev.tick}</BblData>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </BblPanel>
        {/* Bottom: sparklines (NOT full-size — those go to /analysis) */}
        <BblPanel title="Vital Signs · Last 24 Ticks"
          right={
            <button onClick={() => onNavigate("analysis")} style={{
              background: "transparent", border: "none", color: "#787878",
              fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase",
              cursor: "pointer", fontFamily: "var(--font-sans)"
            }}>Open Analysis ▸</button>
          }
          style={{ gridColumn: "1 / span 2" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 16 }}>
            <BblTooltip breakdown={[
              {label:"Base extraction", value:.18},
              {label:"Tribute (DFB)", value:.12},
              {label:"Rent burden", value:.04},
              {label:"Educate offset", value:-.03}
            ]} total={TIMESERIES.imperial_rent[TIMESERIES.imperial_rent.length-1]}>
              <Sparkline label="Imperial Rent" data={TIMESERIES.imperial_rent} color="#a070d0" w={130}/>
            </BblTooltip>
            <BblTooltip breakdown={Scope.getScriptValueBreakdown("consciousness")}
              total={TIMESERIES.consciousness[TIMESERIES.consciousness.length-1]}>
              <Sparkline label="Consciousness" data={TIMESERIES.consciousness} color="#80b0e0" w={130}/>
            </BblTooltip>
            <Sparkline label="Solidarity"   data={TIMESERIES.solidarity}   color="#40c040" w={130}/>
            <BblTooltip breakdown={Scope.getScriptValueBreakdown("heat")}
              total={TIMESERIES.heat[TIMESERIES.heat.length-1]}>
              <Sparkline label="Heat"      data={TIMESERIES.heat}        color="#e04040" w={130}/>
            </BblTooltip>
            <Sparkline label="Wealth"      data={TIMESERIES.wealth}      color="#c8a860" w={130}/>
            <Sparkline label="Biocapacity" data={TIMESERIES.biocapacity} color="#7ab038" w={130}/>
          </div>
        </BblPanel>
      </div>
    </div>
  );
};

const pillBtn = (color) => ({
  background: "transparent", border: `1px solid ${color}`, color,
  padding: "4px 10px", fontSize: 9, fontWeight: 700, letterSpacing: ".15em",
  textTransform: "uppercase", borderRadius: 4, cursor: "pointer",
  fontFamily: "var(--font-sans)"
});

// ----------------------------------------------------------------------------
// /games/:id/orgs — ORGANIZATIONS
// Player-controlled orgs ONLY. Enemy orgs go in INTEL.
// 3×3 verb grid as nav links to verb pages.
// ----------------------------------------------------------------------------
const OrgsPage = ({ onNavigate, currentOrgId, onSelectOrg }) => {
  const playerOrgs = ORGS.filter(o => o.player_controlled);
  const org = playerOrgs.find(o => o.id === currentOrgId) || playerOrgs[0];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <PageHeader title="Organizations"
        subtitle={`${playerOrgs.length} player orgs · ${ORGS.filter(o => !o.player_controlled).length} known enemy orgs in Intel`}
        breadcrumbs={["Operation", "Orgs"]}/>
      <div style={{ flex: 1, display: "grid",
                     gridTemplateColumns: "300px 1fr",
                     gap: 12, padding: 12, minHeight: 0 }}>
        {/* Org roster (player-only) */}
        <BblPanel title="Player Roster">
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {playerOrgs.map(o => {
              const active = o.id === org.id;
              return (
                <button key={o.id} onClick={() => onSelectOrg(o.id)} style={{
                  textAlign: "left", padding: "10px 12px",
                  background: active ? "rgba(200,168,96,.1)" : "#0a0a0f",
                  border: active ? "1px solid #c8a860" : "1px solid #1a1a2a",
                  borderRadius: 6, color: "#e0e0e0", cursor: "pointer",
                  fontFamily: "var(--font-sans)"
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{o.short}</span>
                    <BblBadge color={CLASS_COLORS[o.class_character]}>{o.ooda_phase}</BblBadge>
                  </div>
                  <div style={{ fontSize: 10, color: "#787878", marginTop: 2 }}>{o.name}</div>
                  <div style={{ display: "flex", gap: 10, marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 10 }}>
                    <span><span style={{color:"#404040"}}>CL </span><span style={{color:"#80b0e0"}}>{o.vanguard.cl}</span></span>
                    <span><span style={{color:"#404040"}}>SL </span><span style={{color:"#40c040"}}>{o.vanguard.sl}</span></span>
                    <span><span style={{color:"#404040"}}>♥ </span><span style={{color:"#c8a860"}}>{(o.cohesion*100).toFixed(0)}%</span></span>
                  </div>
                </button>
              );
            })}
          </div>
          <div style={{ marginTop: 12, padding: 8, background: "rgba(64,192,64,.05)",
                         border: "1px dashed #40c04055", borderRadius: 4,
                         fontSize: 10, color: "#787878", lineHeight: 1.5 }}>
            <BblLabel color="#40c040">Note</BblLabel>
            <div style={{ marginTop: 4 }}>
              Enemy orgs (WCSD, DFB, S3) appear in <span style={{ color: "#c8a860", cursor: "pointer" }}
              onClick={() => onNavigate("intel")}>Intel</span>, not here.
              The action surface only shows actor-orgs you control.
            </div>
          </div>
        </BblPanel>
        {/* Org detail — verb grid + status */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <OrgDetailHeader org={org}/>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, flex: 1, minHeight: 0 }}>
            <BblPanel title={`Action · ${org.short}`}
              right={<BblData color="#c8a860" size={10}>{org.vanguard.cl}/{org.vanguard.cl_max} CL · {org.vanguard.sl}/{org.vanguard.sl_max} SL</BblData>}>
              <VerbGrid onNavigate={onNavigate} org={org}/>
            </BblPanel>
            <BblPanel title="Org Composition · Hyperedge View">
              <div style={{ marginBottom: 10, fontSize: 10, color: "#787878", lineHeight: 1.5 }}>
                Members are communities (XGI hyperedges), not individuals.
                Listing membership — not pairwise edges.
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {org.members.map(cid => {
                  const c = Scope.getCommunity(cid);
                  if (!c) return null;
                  return (
                    <div key={cid} style={{
                      padding: "8px 10px", background: "#0a0a0f",
                      border: "1px solid #1a1a2a", borderRadius: 4
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 11, fontWeight: 600 }}>{c.name}</span>
                        <BblData color={CLASS_COLORS[c.dominant_class]} size={10}>
                          {c.members.toLocaleString()} ppl
                        </BblData>
                      </div>
                      <div style={{ display: "flex", gap: 4, marginTop: 6, flexWrap: "wrap" }}>
                        {c.composition.map(tag => (
                          <BblBadge key={tag} color="#c8a860" bg="rgba(200,168,96,.06)">{tag}</BblBadge>
                        ))}
                      </div>
                      <div style={{ display: "flex", gap: 12, marginTop: 6, fontFamily: "var(--font-mono)", fontSize: 9 }}>
                        <span><span style={{color:"#404040"}}>CON </span>{(c.con*100).toFixed(0)}%</span>
                        <span><span style={{color:"#404040"}}>SOL </span>{(c.sol*100).toFixed(0)}%</span>
                        <span><span style={{color:"#404040"}}>CRED→{org.short} </span><span style={{color:"#c8a860"}}>{(c.credibility_to[org.id]*100).toFixed(0)}%</span></span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </BblPanel>
          </div>
        </div>
      </div>
    </div>
  );
};

const OrgDetailHeader = ({ org }) => {
  const v = org.vanguard;
  return (
    <BblPanel title={org.name} right={<BblBadge color={CLASS_COLORS[org.class_character]}>{org.class_character}</BblBadge>}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 16 }}>
        <Stat label="OODA" value={org.ooda_phase} color="#80b0e0"
          tooltip="Observe → Orient → Decide → Act. Each org cycles per tick. Action availability gates by phase."/>
        <BblTooltip breakdown={Scope.getScriptValueBreakdown("cohesion")} total={org.cohesion}>
          <Stat label="Cohesion"   value={`${(org.cohesion*100).toFixed(0)}%`} color="#c8a860" wrap={false}/>
        </BblTooltip>
        <Stat label="Legitimacy" value={`${(org.legitimacy*100).toFixed(0)}%`} color="#40c040"
          tooltip="External legitimacy. Rises with successful campaigns; falls with failed Negotiate / aggressive Attacks."/>
        <Stat label="Opacity"    value={`${(org.opacity*100).toFixed(0)}%`}    color="#a070d0"
          tooltip="Visibility to repressive apparatuses. Lower opacity → easier to repress."/>
        <Stat label="Heat"       value={`${(v.heat*100).toFixed(0)}%`}
          color={v.heat > 0.6 ? "#e04040" : "#c8a860"}
          tooltip="Repression pressure. >70% triggers raid risk."/>
        <Stat label="HQ"         value={Scope.getTerritory(org.hq_territory)?.name || "—"} color="#e0e0e0"/>
      </div>
      <div style={{ display: "flex", gap: 6, marginTop: 14, flexWrap: "wrap" }}>
        {org.badges.map(b => (
          <BblBadge key={b} color="#c8a860" bg="rgba(200,168,96,.08)">{b}</BblBadge>
        ))}
        <span style={{ flex: 1 }}/>
        <BblLabel>Last action — T{org.last_action.tick}</BblLabel>
        <BblBadge color="#80b0e0">{org.last_action.verb} · {org.last_action.outcome}</BblBadge>
      </div>
    </BblPanel>
  );
};

const VerbGrid = ({ onNavigate, org }) => (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
    {VERBS.map(v => (
      <BblTooltip key={v.verb}
        breakdown={[
          { label: "Cost", value: 0 },
          { label: "Target type", value: 0 },
        ]}
        text={`${v.label} — ${v.desc} · Cost: ${v.cost_label} · Targets: ${v.target_type.replace("_", " or ")}`}>
        <button onClick={() => onNavigate("v_" + v.verb.slice(0,3) + (v.verb === "investigate" ? "est" : v.verb === "negotiate" ? "otiate" : v.verb === "reproduce" ? "roduce" : v.verb === "campaign" ? "paign" : v.verb === "mobilize" ? "ilize" : v.verb === "educate" ? "cate" : v.verb === "attack" ? "ack" : v.verb === "move" ? "e" : v.verb === "aid" ? "" : ""))} style={{
          padding: 14, background: "#0a0a0f", border: "1px solid #2a2a3a",
          borderRadius: 6, color: "#e0e0e0", cursor: "pointer", textAlign: "left",
          width: "100%", fontFamily: "var(--font-sans)"
        }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#c8a860"; e.currentTarget.style.background = "rgba(200,168,96,.05)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#2a2a3a"; e.currentTarget.style.background = "#0a0a0f"; }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 18, color: "#c8a860", fontFamily: "var(--font-mono)" }}>{v.glyph}</span>
            <BblData color="#787878" size={9}>{v.cost_label}</BblData>
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, marginTop: 6 }}>{v.label}</div>
          <div style={{ fontSize: 9, color: "#787878", marginTop: 2,
                          letterSpacing: ".1em", textTransform: "uppercase" }}>
            → {v.target_type.replace(/_/g, " ")}
          </div>
        </button>
      </BblTooltip>
    ))}
  </div>
);

// Verb→route key resolver (corrects clumsy slicing in onNavigate above)
function verbRouteKey(verb) {
  const map = {
    educate: "v_educate", aid: "v_aid", attack: "v_attack",
    mobilize: "v_mobilize", campaign: "v_campaign", move: "v_move",
    investigate: "v_invest", reproduce: "v_reproduce", negotiate: "v_negotiate",
  };
  return map[verb];
}

// ----------------------------------------------------------------------------
// /games/:id/intel/:type/:id — INTEL / INSPECTOR
// Where enemy orgs, edges, territories, communities show up.
// ----------------------------------------------------------------------------
const IntelPage = ({ onNavigate, intelTarget, onSelectIntel }) => {
  const target = intelTarget || { type: "org", id: "ORG-NPC-002" };
  const tabs = [
    { type: "territory", label: "Territories", count: TERRITORIES.length },
    { type: "org",       label: "Orgs (Enemy)", count: ORGS.filter(o => !o.player_controlled).length },
    { type: "edge",      label: "Edges",      count: EDGES.length },
    { type: "community", label: "Communities", count: COMMUNITIES.length },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <PageHeader title="Intel"
        subtitle="Inspector for enemy orgs, edges, territories, and communities. Click a tab on the map to deep-link."
        breadcrumbs={["Operation", "Intel", target.type, target.id]}/>
      <div style={{ flex: 1, display: "grid",
                     gridTemplateColumns: "260px 1fr",
                     gap: 12, padding: 12, minHeight: 0 }}>
        {/* Tabs + list */}
        <BblPanel title="Surveillance Index">
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 10 }}>
            {tabs.map(t => (
              <button key={t.type} onClick={() => onSelectIntel({ type: t.type, id: defaultIntelId(t.type) })} style={{
                background: target.type === t.type ? "rgba(200,168,96,.1)" : "transparent",
                border: target.type === t.type ? "1px solid #c8a860" : "1px solid #2a2a3a",
                color: target.type === t.type ? "#c8a860" : "#787878",
                fontSize: 9, padding: "3px 8px", letterSpacing: ".15em",
                textTransform: "uppercase", borderRadius: 4, cursor: "pointer",
                fontFamily: "var(--font-sans)"
              }}>{t.label} <span style={{ color: "#404040" }}>{t.count}</span></button>
            ))}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {intelList(target.type).map(item => (
              <button key={item.id} onClick={() => onSelectIntel({ type: target.type, id: item.id })} style={{
                textAlign: "left", padding: "8px 10px",
                background: item.id === target.id ? "rgba(200,168,96,.08)" : "#0a0a0f",
                border: item.id === target.id ? "1px solid #c8a860" : "1px solid #1a1a2a",
                borderRadius: 4, color: "#e0e0e0", cursor: "pointer",
                fontFamily: "var(--font-sans)"
              }}>
                <div style={{ fontSize: 11, fontWeight: 600 }}>{item.label}</div>
                <div style={{ fontSize: 9, color: "#787878", marginTop: 2 }}>{item.sub}</div>
              </button>
            ))}
          </div>
        </BblPanel>
        <IntelDetail target={target} onNavigate={onNavigate}/>
      </div>
    </div>
  );
};

function defaultIntelId(type) {
  if (type === "territory") return TERRITORIES[0].id;
  if (type === "org")       return "ORG-NPC-001";
  if (type === "edge")      return EDGES[0].id;
  if (type === "community") return COMMUNITIES[0].id;
}
function intelList(type) {
  if (type === "territory") return TERRITORIES.map(t => ({ id: t.id, label: t.name, sub: `pop ${t.pop.toLocaleString()} · heat ${(t.heat*100).toFixed(0)}%` }));
  if (type === "org")       return ORGS.filter(o => !o.player_controlled).map(o => ({ id: o.id, label: o.short, sub: `${o.name} · ${o.threat_level}` }));
  if (type === "edge")      return EDGES.map(e => ({ id: e.id, label: e.type, sub: `${e.source} → ${e.target}` }));
  if (type === "community") return COMMUNITIES.map(c => ({ id: c.id, label: c.name, sub: c.composition.join(" · ") }));
  return [];
}

const IntelDetail = ({ target, onNavigate }) => {
  if (target.type === "org") {
    const o = Scope.getOrg(target.id);
    if (!o) return null;
    return (
      <BblPanel title={`Intel · ${o.short}`} accent="#e04040"
        right={<BblBadge color="#e04040">THREAT · {o.threat_level || "—"}</BblBadge>}>
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16, height: "100%" }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#e04040", marginBottom: 4 }}>{o.name}</div>
            <BblBadge color={CLASS_COLORS[o.class_character]}>{o.class_character.replace(/_/g," ")}</BblBadge>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
              <Stat label="Cohesion"   value={`${(o.cohesion*100).toFixed(0)}%`} color="#c8a860"/>
              <Stat label="Legitimacy" value={`${(o.legitimacy*100).toFixed(0)}%`} color="#40c040"/>
              <Stat label="Opacity"    value={`${(o.opacity*100).toFixed(0)}%`}    color="#a070d0"/>
              <Stat label="OODA"       value={o.ooda_phase}                          color="#80b0e0"/>
              <Stat label="HQ"         value={Scope.getTerritory(o.hq_territory)?.name || "—"} color="#e0e0e0"/>
              <Stat label="Last Obs."  value={`T${o.last_observed_tick}`}            color="#787878"/>
            </div>
            <div style={{ marginTop: 16, padding: 10, background: "rgba(110,16,32,.18)",
                           border: "1px solid #6e1020", borderRadius: 4,
                           fontSize: 11, color: "#a0a0a0", lineHeight: 1.5 }}>
              <BblLabel color="#e04040">Surveillance Note</BblLabel>
              <div style={{ marginTop: 4 }}>
                Opacity {(o.opacity*100).toFixed(0)}% — {o.opacity > 0.5 ? "intel is partial; further Investigate recommended."
                : "intel is reliable enough to plan against."}
              </div>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 6 }}>
              <button onClick={() => onNavigate("v_invest")} style={pillBtn("#c8a860")}>▸ Investigate</button>
              <button onClick={() => onNavigate("v_attack")} style={pillBtn("#e04040")}>▸ Attack</button>
              <button onClick={() => onNavigate("v_negotiate")} style={pillBtn("#80b0e0")}>▸ Negotiate</button>
            </div>
          </div>
          <div>
            <BblLabel>Edge Topology</BblLabel>
            <div style={{ marginTop: 4, background: "#0a0a0f", border: "1px solid #1a1a2a",
                            borderRadius: 4, height: 240 }}>
              <TopologyGraph height={240} mode="dyadic"/>
            </div>
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
              {Scope.getEdgesOf(o.id).map(e => (
                <div key={e.id} style={{ display: "flex", justifyContent: "space-between",
                                           padding: "5px 8px", background: "#0a0a0f",
                                           border: "1px solid #1a1a2a", borderRadius: 3,
                                           fontSize: 10 }}>
                  <BblBadge color={EDGE_COLORS[e.type]}>{e.type}</BblBadge>
                  <span style={{ color: "#787878", fontFamily: "var(--font-mono)" }}>
                    {e.source === o.id ? "→" : "←"} {(e.source === o.id ? e.target : e.source)}
                  </span>
                  <BblData color="#c8a860" size={10}>{(e.intensity*100).toFixed(0)}%</BblData>
                </div>
              ))}
            </div>
          </div>
        </div>
      </BblPanel>
    );
  }
  if (target.type === "territory") {
    const t = Scope.getTerritory(target.id);
    if (!t) return null;
    const inhab = Scope.getCommunitiesIn(t.id);
    return (
      <BblPanel title={`Territory · ${t.name}`}
        right={<BblBadge color="#80b0e0">{t.county} County</BblBadge>}>
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
              <Stat label="Population"   value={t.pop.toLocaleString()}          color="#e0e0e0"/>
              <Stat label="Imperial Rent" value={(t.rent*100).toFixed(0)+"%"}    color="#a070d0"/>
              <Stat label="Consciousness" value={(t.con*100).toFixed(0)+"%"}     color="#80b0e0"/>
              <Stat label="Solidarity"   value={(t.sol*100).toFixed(0)+"%"}      color="#40c040"/>
              <Stat label="Heat"         value={(t.heat*100).toFixed(0)+"%"}     color={t.heat>.6 ? "#e04040":"#c8a860"}/>
              <Stat label="Wealth"       value={(t.wealth*100).toFixed(0)+"%"}   color="#c8a860"/>
              <Stat label="Biocapacity"  value={(t.biocap*100).toFixed(0)+"%"}   color="#7ab038"/>
              <Stat label="Dom. Class"   value={t.dominant_community}            color="#e04040"/>
            </div>
            <div style={{ marginTop: 16 }}>
              <BblLabel>Communities In Territory · Hyperedge Choropleth</BblLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}>
                {inhab.length ? inhab.map(c => (
                  <button key={c.id} onClick={() => {}} style={{
                    textAlign: "left", padding: "6px 10px", background: "#0a0a0f",
                    border: "1px solid #1a1a2a", borderRadius: 3, color: "#e0e0e0",
                    cursor: "pointer", fontSize: 11, fontFamily: "var(--font-sans)"
                  }}>
                    <span>{c.name}</span>
                    <span style={{ color: "#787878", fontFamily: "var(--font-mono)", float: "right" }}>
                      {c.members.toLocaleString()} ppl · {c.dominant_class}
                    </span>
                  </button>
                )) : <span style={{ fontSize: 10, color: "#787878" }}>No communities indexed.</span>}
              </div>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 6 }}>
              <button onClick={() => onNavigate("v_move")}     style={pillBtn("#80b0e0")}>▸ Move</button>
              <button onClick={() => onNavigate("v_aid")}      style={pillBtn("#40c040")}>▸ Aid</button>
              <button onClick={() => onNavigate("v_campaign")} style={pillBtn("#c8a860")}>▸ Campaign</button>
            </div>
          </div>
          <div>
            <BblLabel>Map Detail</BblLabel>
            <div style={{ marginTop: 4, height: 240 }}>
              <HexMap layer="rent" lens="economic" height="100%"/>
            </div>
          </div>
        </div>
      </BblPanel>
    );
  }
  if (target.type === "edge") {
    const e = Scope.getEdge(target.id);
    if (!e) return null;
    return (
      <BblPanel title={`Edge · ${e.type}`} accent={EDGE_COLORS[e.type]}>
        <div style={{ display: "flex", justifyContent: "space-around", alignItems: "center", marginBottom: 22 }}>
          <NodeChip id={e.source}/>
          <div style={{ flex: 1, position: "relative", height: 24, margin: "0 14px" }}>
            <div style={{ position: "absolute", inset: 0, borderTop: `2px solid ${EDGE_COLORS[e.type]}` }}/>
            <div style={{ position: "absolute", left: "50%", top: "-6px", transform: "translateX(-50%)",
                           background: "#0a0a0f", padding: "0 8px" }}>
              <BblBadge color={EDGE_COLORS[e.type]}>{e.type}</BblBadge>
            </div>
            <div style={{ position: "absolute", right: -2, top: -4 }}>
              <span style={{ color: EDGE_COLORS[e.type], fontSize: 16 }}>▶</span>
            </div>
          </div>
          <NodeChip id={e.target}/>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          <Stat label="Intensity" value={(e.intensity*100).toFixed(0)+"%"} color={EDGE_COLORS[e.type]}/>
          {e.rate_of_profit !== undefined && <Stat label="Rate of Profit" value={(e.rate_of_profit*100).toFixed(0)+"%"} color="#a070d0"/>}
          {e.rent_burden     !== undefined && <Stat label="Rent Burden"   value={(e.rent_burden*100).toFixed(0)+"%"}   color="#a070d0"/>}
          {e.value_flow_per_tick !== undefined && <Stat label="Value Flow / Tick" value={`${e.value_flow_per_tick}`}    color="#c8a860"/>}
          {e.last_event !== undefined && <Stat label="Last Event" value={e.last_event} color="#e04040"/>}
          {e.age_ticks !== undefined && <Stat label="Edge Age" value={`${e.age_ticks} ticks`} color="#787878"/>}
        </div>
      </BblPanel>
    );
  }
  if (target.type === "community") {
    const c = Scope.getCommunity(target.id);
    if (!c) return null;
    return (
      <BblPanel title={`Community · ${c.name}`} accent={CLASS_COLORS[c.dominant_class]}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <BblLabel>Composition (Hyperedge Membership)</BblLabel>
            <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
              {c.composition.map(tag => (
                <BblBadge key={tag} color="#c8a860" bg="rgba(200,168,96,.08)" style={{ fontSize: 11, padding: "4px 12px" }}>{tag}</BblBadge>
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginTop: 16 }}>
              <Stat label="Members"        value={c.members.toLocaleString()}                color="#e0e0e0"/>
              <Stat label="Dominant Class" value={c.dominant_class}                          color={CLASS_COLORS[c.dominant_class]}/>
              <Stat label="Consciousness"  value={(c.con*100).toFixed(0)+"%"}                color="#80b0e0"/>
              <Stat label="Solidarity"     value={(c.sol*100).toFixed(0)+"%"}                color="#40c040"/>
            </div>
            <div style={{ marginTop: 16, display: "flex", gap: 6 }}>
              <button onClick={() => onNavigate("v_educate")}  style={pillBtn("#c8a860")}>▸ Educate</button>
              <button onClick={() => onNavigate("v_mobilize")} style={pillBtn("#40c040")}>▸ Mobilize</button>
              <button onClick={() => onNavigate("v_campaign")} style={pillBtn("#c8a860")}>▸ Campaign</button>
            </div>
          </div>
          <div>
            <BblLabel>Credibility To Player Orgs</BblLabel>
            <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
              {Object.entries(c.credibility_to).map(([oid, val]) => {
                const o = Scope.getOrg(oid);
                return (
                  <div key={oid} style={{ display: "grid", gridTemplateColumns: "1fr auto",
                                            gap: 8, alignItems: "center", padding: "6px 10px",
                                            background: "#0a0a0f", border: "1px solid #1a1a2a",
                                            borderRadius: 3 }}>
                    <span style={{ fontSize: 11 }}>{o?.short || oid}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 80, height: 4, background: "#1a1a2a", borderRadius: 9999,
                                     overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${val*100}%`,
                                       background: val > 0.6 ? "#40c040" : val > 0.4 ? "#c8a860" : "#e04040" }}/>
                      </div>
                      <BblData color="#c8a860" size={10}>{(val*100).toFixed(0)}%</BblData>
                    </div>
                  </div>
                );
              })}
            </div>
            <div style={{ marginTop: 16, padding: 10, background: "#0a0a0f",
                           border: "1px dashed #2a2a3a", borderRadius: 4 }}>
              <BblLabel>Topological View · BubbleSets Hull</BblLabel>
              <div style={{ marginTop: 4 }}>
                <TopologyGraph height={120} mode="topological"/>
              </div>
              <div style={{ fontSize: 9, color: "#787878", marginTop: 6, lineHeight: 1.5 }}>
                Hyperedge community rendered as containment hull (Article VIII.9)
                — never as pairwise edges between an org and every member.
              </div>
            </div>
          </div>
        </div>
      </BblPanel>
    );
  }
  return null;
};

const NodeChip = ({ id }) => {
  let label = id, color = "#888";
  if (id.startsWith("ORG")) {
    const o = Scope.getOrg(id);
    label = o?.short || id;
    color = CLASS_COLORS[o?.class_character] || "#888";
  } else if (id.startsWith("T-")) {
    label = Scope.getTerritory(id)?.name || id;
    color = "#80b0e0";
  } else if (id.startsWith("C-")) {
    label = Scope.getCommunity(id)?.name || id;
    color = "#a070d0";
  }
  return (
    <div style={{ padding: "8px 14px", border: `1px solid ${color}`,
                   borderRadius: 6, background: `${color}11`, textAlign: "center", minWidth: 140 }}>
      <BblLabel color={color}>{id.startsWith("ORG") ? "ORG" : id.startsWith("T-") ? "Territory" : "Community"}</BblLabel>
      <div style={{ fontSize: 12, fontWeight: 600, color, marginTop: 2 }}>{label}</div>
    </div>
  );
};

// ----------------------------------------------------------------------------
// /games/:id/results — RESULTS (mechanical)
// ----------------------------------------------------------------------------
const ResultsPage = ({ tick }) => (
  <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
    <PageHeader title={`Tick ${tick} Results`}
      subtitle="Mechanical resolution — distinct from Briefing's narrative framing."
      breadcrumbs={["Operation", `Tick ${tick}`, "Results"]}/>
    <div style={{ flex: 1, padding: 12, display: "grid",
                   gridTemplateColumns: "1fr 1fr", gap: 12, minHeight: 0,
                   overflow: "auto" }}>
      <BblPanel title="Player Actions Submitted">
        <table style={{ width: "100%", borderCollapse: "collapse",
                         fontFamily: "var(--font-mono)", fontSize: 11 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #2a2a3a" }}>
              {["Org", "Verb", "Target", "ΔState", "Outcome"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: 6, color: "#787878", fontWeight: 400,
                                       textTransform: "uppercase", letterSpacing: ".15em", fontSize: 9 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["WCLF", "educate",  "C-DEARBORN-PROLE", "+0.04 CON", "success"],
              ["DTC",  "mobilize", "C-DETROIT-C-PROLE","+0.07 SOL", "success"],
              ["WCLF", "investigate","E003 (REPRESSION)","-0.18 OPACITY","critical"],
            ].map((r, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #1a1a2a" }}>
                {r.map((c, j) => (
                  <td key={j} style={{ padding: 8,
                    color: j === 4 ? (c === "critical" ? "#e04040" : c === "success" ? "#40c040" : "#787878")
                          : j === 1 ? "#c8a860" : "#e0e0e0" }}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </BblPanel>
      <BblPanel title="NPC Actions Resolved">
        <table style={{ width: "100%", borderCollapse: "collapse",
                         fontFamily: "var(--font-mono)", fontSize: 11 }}>
          <thead><tr style={{ borderBottom: "1px solid #2a2a3a" }}>
            {["Org", "Verb", "Target", "ΔState"].map(h => (
              <th key={h} style={{ textAlign: "left", padding: 6, color: "#787878", fontWeight: 400,
                                     textTransform: "uppercase", letterSpacing: ".15em", fontSize: 9 }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {[
              ["WCSD", "investigate", "ORG001 (WCLF)", "+0.12 HEAT"],
              ["DFB",  "campaign",  "T-DEARBORN-E", "+0.04 RENT"],
              ["S3",   "move",      "T-DOWNRIVER",  "—"],
            ].map((r, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #1a1a2a" }}>
                {r.map((c, j) => (
                  <td key={j} style={{ padding: 8, color: j === 1 ? "#e0a030" : "#a0a0a0" }}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </BblPanel>
      <BblPanel title="Tensor Diff (Δ from T-1)" style={{ gridColumn: "1 / span 2" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 16 }}>
          {[
            ["Imperial Rent",   0.34, +0.012, "#a070d0"],
            ["Consciousness",   0.30, +0.008, "#80b0e0"],
            ["Solidarity",      0.42, +0.014, "#40c040"],
            ["Heat",            0.55, +0.024, "#e04040"],
            ["Wealth",          0.32, -0.003, "#c8a860"],
            ["Biocapacity",     0.51, -0.001, "#7ab038"],
          ].map(([l, v, d, c]) => (
            <div key={l}>
              <BblLabel>{l}</BblLabel>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 2 }}>
                <BblData color={c} size={20}>{v.toFixed(3)}</BblData>
                <BblData color={d > 0 ? "#40c040" : "#e06060"} size={11}>
                  {d > 0 ? "▲" : "▼"} {Math.abs(d).toFixed(3)}
                </BblData>
              </div>
            </div>
          ))}
        </div>
      </BblPanel>
    </div>
  </div>
);

Object.assign(window, {
  BriefingPage, OrgsPage, IntelPage, ResultsPage, OrgDetailHeader, VerbGrid,
  pillBtn, verbRouteKey, NodeChip
});
