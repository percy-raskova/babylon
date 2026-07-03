// view-educate.jsx — /games/:id/actions/educate
// Verb page: the target picker is GATED to community hyperedges only.
// Article IV: hyperedges are first-class targets for Educate/Mobilize/Campaign.
// This artboard demonstrates that gating in UI form.

function EducateView() {
  const [selected, setSelected] = React.useState(0);
  const t = EDUCATE_TARGETS[selected];
  const c = COMM_BY_ID[t.community_id];

  return (
    <div style={{
      width: "100%", height: "100%", display: "flex", flexDirection: "column",
      background: "var(--void)", color: "var(--bone)", overflow: "hidden",
    }}>
      <TopBar route={["Game · DET-070", "Action", "Educate"]} orgShort="DRA"/>
      <SubTabs active="educate" tabs={[
        { id: "educate",  label: "Educate" },
        { id: "mobilize", label: "Mobilize" },
        { id: "campaign", label: "Campaign" },
        { id: "more",     label: "+6 verbs" },
      ]}/>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "420px 1fr",
        gap: 12, padding: 16, minHeight: 0 }}>

        {/* LEFT: target picker — gated to community hyperedges */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          <ConstitutionBanner>
            Target type: <em style={{ color: "var(--bone)", fontStyle: "normal" }}>community hyperedge</em>.
            <span style={{ color: "var(--shroud)" }}> Orgs and territories excluded by Article IV.</span>
          </ConstitutionBanner>

          <Pane label="Targets · Community Hyperedges" badge={`${EDUCATE_TARGETS.length} candidates · ROI desc`}
            style={{ flex: 1, minHeight: 0 }}>
            <div style={{ padding: "8px 8px", display: "flex", flexDirection: "column", gap: 6,
              overflow: "auto" }}>
              {EDUCATE_TARGETS.map((target, i) => (
                <TargetRow key={target.community_id} target={target}
                  isSelected={i === selected}
                  onClick={() => setSelected(i)}/>
              ))}
            </div>
          </Pane>
        </div>

        {/* RIGHT: action composer */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, minHeight: 0 }}>
          {/* Header — selected target */}
          <div style={{
            padding: "14px 18px",
            background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 5,
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
                letterSpacing: ".22em" }}>VERB · TARGET</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 14, marginTop: 4 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 700,
                  color: "var(--bone)", letterSpacing: ".18em", textTransform: "uppercase" }}>
                  EDUCATE
                </span>
                <span style={{ color: "var(--ash)", fontFamily: "var(--font-mono)", fontSize: 14 }}>→</span>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                  <span style={{ width: 12, height: 12, background: c.color,
                    boxShadow: `0 0 10px ${c.color}` }}/>
                  <span style={{ fontFamily: "var(--font-sans)", fontSize: 18, fontWeight: 600,
                    color: "var(--bone)", letterSpacing: "-.01em" }}>
                    {c.label}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11,
                    color: "var(--shroud)", letterSpacing: ".18em" }}>HYPEREDGE · {c.short}</span>
                </span>
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)",
                marginTop: 4, letterSpacing: ".04em" }}>
                {c.desc}
              </div>
            </div>
            {t.warning && (
              <div style={{
                padding: "6px 10px",
                background: "rgba(255,51,68,.08)",
                border: "1px solid rgba(255,51,68,.32)",
                borderRadius: 3,
                fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--laser)",
                letterSpacing: ".18em", textTransform: "uppercase", maxWidth: 240, textAlign: "right",
              }}>
                <div style={{ fontWeight: 700, marginBottom: 2 }}>NEGATIVE SHIFT</div>
                <div style={{ color: "var(--fog)", letterSpacing: ".02em", textTransform: "none",
                  fontSize: 9 }}>{t.warning}</div>
              </div>
            )}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12,
            flex: 1, minHeight: 0 }}>

            {/* Predicted outcome */}
            <Pane label="Predicted Δ Consciousness" badge="server preview">
              <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12 }}>
                <div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)",
                    letterSpacing: ".22em", marginBottom: 6 }}>BASELINE → AFTER</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                    <ConsciousnessNumber value={t.baseline_consciousness} tone="baseline"/>
                    <span style={{ color: "var(--ash)", fontSize: 18,
                      fontFamily: "var(--font-mono)" }}>→</span>
                    <ConsciousnessNumber value={t.predicted_after} tone="after"/>
                    <span style={{ marginLeft: "auto",
                      fontFamily: "var(--font-mono)", fontSize: 16, fontWeight: 700,
                      color: t.predicted_consciousness_shift >= 0 ? "var(--solidarity)" : "var(--laser)",
                      letterSpacing: "-.01em" }}>
                      {fmtSigned(t.predicted_consciousness_shift, 3)}
                    </span>
                  </div>
                </div>

                {/* Linear "consciousness rail" */}
                <div>
                  <div style={{ height: 8, background: "var(--tar)", borderRadius: 2,
                    position: "relative", overflow: "visible" }}>
                    <div style={{ position: "absolute", left: 0, top: 0, bottom: 0,
                      width: `${t.baseline_consciousness*100}%`,
                      background: "var(--ash)", opacity: 0.6 }}/>
                    <div style={{ position: "absolute",
                      left: `${Math.min(t.baseline_consciousness, t.predicted_after)*100}%`,
                      top: 0, bottom: 0,
                      width: `${Math.abs(t.predicted_consciousness_shift)*100}%`,
                      background: t.predicted_consciousness_shift >= 0
                        ? "var(--solidarity)" : "var(--laser)",
                      boxShadow: t.predicted_consciousness_shift >= 0
                        ? "0 0 8px var(--solidarity)" : "0 0 8px var(--laser)" }}/>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4,
                    fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--shroud)",
                    letterSpacing: ".18em" }}>
                    <span>0 · REACTIONARY</span>
                    <span>0.5 · DUAL</span>
                    <span>1.0 · REVOLUTIONARY</span>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <Stat label="Members reached" value={fmtCount(t.members_reached)} sub="of community"/>
                  <Stat label="Cost · CL" value={String(t.cost)} sub={`org budget ${PLAYER_ORG.budget}`}/>
                </div>

                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10,
                  color: "var(--fog)", lineHeight: 1.5, letterSpacing: ".02em" }}>
                  {t.notes}
                </div>
              </div>
            </Pane>

            {/* Membership overlap */}
            <Pane label="Membership Overlap" badge="DRA reach map">
              <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)",
                  letterSpacing: ".22em" }}>YOUR ORG · COMMUNITY REACH</div>

                {COMMUNITIES.filter(c => PLAYER_ORG.reach[c.id] !== undefined)
                  .sort((a, b) => (PLAYER_ORG.reach[b.id]||0) - (PLAYER_ORG.reach[a.id]||0))
                  .map(comm => {
                    const reach = PLAYER_ORG.reach[comm.id] || 0;
                    const isTarget = comm.id === t.community_id;
                    return (
                      <div key={comm.id} style={{ display: "grid",
                        gridTemplateColumns: "10px 110px 1fr 44px",
                        gap: 10, alignItems: "center" }}>
                        <span style={{ width: 8, height: 8, background: comm.color,
                          boxShadow: `0 0 6px ${comm.color}` }}/>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10,
                          color: isTarget ? "var(--spire)" : "var(--bone)",
                          letterSpacing: ".08em", textTransform: "uppercase",
                          fontWeight: isTarget ? 700 : 500 }}>
                          {comm.label} {isTarget && <span style={{ color: "var(--spire)" }}>·</span>}
                        </span>
                        <div style={{ height: 6, background: "var(--tar)", borderRadius: 1 }}>
                          <div style={{ width: `${reach*100}%`, height: "100%",
                            background: comm.color, opacity: isTarget ? 1 : 0.7,
                            boxShadow: isTarget ? `0 0 8px ${comm.color}` : "none" }}/>
                        </div>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10,
                          color: "var(--bone)", textAlign: "right", letterSpacing: ".02em",
                          fontWeight: isTarget ? 700 : 400 }}>
                          {fmtPct(reach, 0)}
                        </span>
                      </div>
                    );
                  })}

                <div style={{ marginTop: 4, padding: "8px 10px",
                  background: "var(--tar)", border: "1px solid var(--rebar)", borderRadius: 3,
                  fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)",
                  letterSpacing: ".04em", lineHeight: 1.5 }}>
                  Higher overlap → lower cadre-labor cost. Educate is more efficient where
                  the org already has organic reach.
                </div>
              </div>
            </Pane>
          </div>

          {/* Footer: submit */}
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "12px 16px",
            background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 5,
          }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)",
              letterSpacing: ".06em" }}>
              <span style={{ color: "var(--ash)", letterSpacing: ".22em" }}>ENDPOINT </span>
              <span style={{ color: "var(--spire)" }}>POST /api/games/DET-070/actions/</span>
              <span style={{ color: "var(--ash)" }}>  payload </span>
              <span style={{ color: "var(--bone)" }}>{`{verb:"educate", target_id:"${t.community_id}"}`}</span>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button style={{
                padding: "8px 14px", background: "var(--tar)",
                border: "1px solid var(--rebar)", borderRadius: 3,
                fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)",
                letterSpacing: ".22em", textTransform: "uppercase", cursor: "pointer",
              }}>Discard</button>
              <button style={{
                padding: "8px 20px",
                background: t.warning ? "rgba(255,51,68,.12)" : "var(--solidarity)",
                border: `1px solid ${t.warning ? "var(--laser)" : "var(--solidarity)"}`,
                color: t.warning ? "var(--laser)" : "var(--void)",
                borderRadius: 3,
                fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
                letterSpacing: ".22em", textTransform: "uppercase", cursor: "pointer",
                boxShadow: t.warning ? "none" : "0 0 14px rgba(95,191,122,.4)",
              }}>{t.warning ? "Confirm Anyway →" : "Submit Action →"}</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// TargetRow — one row in the target picker
// ────────────────────────────────────────────────────────────
function TargetRow({ target, isSelected, onClick }) {
  const c = COMM_BY_ID[target.community_id];
  const isWarn = !!target.warning;
  const isPositive = target.predicted_consciousness_shift > 0;
  return (
    <div onClick={onClick} style={{
      display: "grid", gridTemplateColumns: "14px 1fr 80px",
      gap: 10, alignItems: "center",
      padding: "10px 12px",
      background: isSelected ? "rgba(77,217,230,.06)" : "var(--tar)",
      border: `1px solid ${isSelected ? "var(--spire)" : isWarn ? "rgba(255,51,68,.22)" : "var(--rebar)"}`,
      borderRadius: 3, cursor: "pointer",
    }}>
      <span style={{ width: 10, height: 10, background: c.color,
        boxShadow: `0 0 10px ${c.color}` }}/>
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600,
            color: isSelected ? "var(--spire)" : "var(--bone)",
            letterSpacing: ".08em", textTransform: "uppercase" }}>
            {c.label}
          </span>
          {isWarn && <span style={{
            padding: "1px 6px",
            background: "rgba(255,51,68,.1)", border: "1px solid rgba(255,51,68,.3)",
            borderRadius: 2,
            fontFamily: "var(--font-mono)", fontSize: 8, fontWeight: 700,
            color: "var(--laser)", letterSpacing: ".22em" }}>HOSTILE</span>}
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 4,
          fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--shroud)",
          letterSpacing: ".06em" }}>
          <span>reach <span style={{ color: "var(--fog)" }}>{fmtPct(target.overlap, 0)}</span></span>
          <span>cost <span style={{ color: "var(--fog)" }}>{target.cost} CL</span></span>
          <span>cons <span style={{ color: "var(--fog)" }}>{target.baseline_consciousness.toFixed(2)}</span></span>
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700,
          color: isPositive ? "var(--solidarity)" :
                 target.predicted_consciousness_shift < 0 ? "var(--laser)" : "var(--bone)",
          letterSpacing: "-.01em" }}>
          {fmtSigned(target.predicted_consciousness_shift, 3)}
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--shroud)",
          letterSpacing: ".18em" }}>Δ CONS</div>
      </div>
    </div>
  );
}

function ConsciousnessNumber({ value, tone }) {
  const color = tone === "after" ? "var(--solidarity)" : "var(--bone)";
  return (
    <div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700,
        color, letterSpacing: "-.02em" }}>
        {value.toFixed(3)}
      </div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--shroud)",
        letterSpacing: ".22em" }}>{tone === "after" ? "AFTER TICK" : "BASELINE"}</div>
    </div>
  );
}
