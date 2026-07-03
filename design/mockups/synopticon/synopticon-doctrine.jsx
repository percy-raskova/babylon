// synopticon-doctrine.jsx — The algorithm rendered as a state document.
//
// Reads like a leaked SOP. Two specs: LAVENDER-V1 (risk scoring) and THE GOSPEL
// (targeting). Each formula sits beside a "footnote" — the human cost translated
// from the mathematical definition.

const DoctrineTab = () => {
  const { DOCTRINE, THRESHOLDS, META } = window.SYN_DATA;

  return (
    <div style={{ height: "100%", overflow: "auto" }}>
      <div className="doc-page">

        {/* Cover page styling */}
        <div className="doc-head" style={{ position: "relative" }}>
          <div className="syn-cls-small" style={{ display: "inline-block", padding: "3px 12px", marginBottom: 18, letterSpacing: "0.32em" }}>
            {DOCTRINE.lavender.classification} · OPERATING DOCTRINE · NOT FOR EXTERNAL DISTRIBUTION
          </div>
          <div className="doc-h1">DOCTRINE · ALGORITHMIC TARGETING</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: 14 }}>
            <div>
              <span className="num" style={{ fontSize: 11, color: "var(--fog)", letterSpacing: "0.18em" }}>
                F2T2EA · FIND · FIX · TRACK · TARGET · ENGAGE · ASSESS
              </span>
            </div>
            <div className="doc-stamp" style={{ transform: "rotate(2deg)" }}>VERSION 3.13</div>
          </div>

          {/* Watermark */}
          <div style={{
            position: "absolute", right: -10, top: 80,
            fontFamily: "var(--font-mono)", fontSize: 96,
            color: "rgba(255,51,68,0.04)",
            fontWeight: 700, letterSpacing: "0.06em",
            pointerEvents: "none", userSelect: "none",
            transform: "rotate(-8deg)",
          }}>
            LAVENDER
          </div>
        </div>

        {/* Epigraph */}
        <div style={{
          margin: "24px 0 32px",
          padding: "14px 18px",
          borderLeft: "3px solid var(--laser)",
          background: "rgba(255,51,68,0.04)",
        }}>
          <div className="num" style={{ fontSize: 13, color: "var(--bone)", letterSpacing: "0.04em", lineHeight: 1.7, fontStyle: "italic" }}>
            "The State does not hate you. The State processes you."
          </div>
          <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.28em", marginTop: 8 }}>
            ▸ SYNOPTICON SPEC · EPIGRAPH · CLEARED FOR INTERNAL CIRCULATION
          </div>
        </div>

        {/* Theory of operation */}
        <div className="doc-h2">▸ Theory of operation</div>
        <p className="doc-body">
          The State AI does not see the True World State. It sees a <em>Legible Projection</em> derived from
          metadata: topology, resource flow, geolocation, communication burst patterns. From this projection,
          it constructs a <em>DigitalDossier</em> for every node in the LegibleGraph.
        </p>
        <p className="doc-body">
          Targets are not guilty. Targets are <em>statistically anomalous</em>. The two are not the same. The
          system is designed to forget that they are not the same.
        </p>

        {/* Three thresholds visual */}
        <div style={{ margin: "24px 0", padding: "20px 24px", background: "var(--tar)", border: "1px solid var(--rebar)" }}>
          <div className="doc-h3" style={{ marginTop: 0 }}>RISK THRESHOLDS · LAVENDER-V1</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginTop: 14 }}>
            {[
              ["MONITOR",   THRESHOLDS.monitor,   "var(--cadre)",  "Passive observation. Increased cadence. Edge cases promoted upward."],
              ["SUPPRESS",  THRESHOLDS.suppress,  "var(--heat)",   "Targeted disruption. Movement restriction. Resource interdiction."],
              ["ELIMINATE", THRESHOLDS.eliminate, "var(--laser)",  "Promoted to Gospel queue. Engaged subject to CDE policy and thread budget."],
            ].map(([lbl, v, c, desc]) => (
              <div key={lbl} style={{ borderTop: `2px solid ${c}`, padding: "10px 12px", background: "var(--void)" }}>
                <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.28em", marginBottom: 4 }}>{lbl} ≥</div>
                <div className="num" style={{ fontSize: 36, fontWeight: 700, color: c, letterSpacing: "0.04em", lineHeight: 1 }}>{v.toFixed(1)}</div>
                <div className="num" style={{ fontSize: 10, color: "var(--fog)", letterSpacing: "0.04em", marginTop: 10, lineHeight: 1.5, fontStyle: "italic" }}>
                  {desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* LAVENDER FEATURES */}
        <div className="doc-h2">▸ Lavender · features</div>
        <p className="doc-body" style={{ marginBottom: 14 }}>
          Four features compose the per-tick risk score. Each is bounded. The sum is clamped to [0, 1]. The
          coefficients are not exposed to operators and are not subject to review.
        </p>

        <div className="doc-formula" style={{ marginBottom: 18 }}>
          RISK(node, t) = clamp( f₁ + f₂ + f₃ + f₄ , 0, 1 )
        </div>

        {DOCTRINE.lavender.features.map((f, i) => (
          <div key={f.key} style={{
            margin: "20px 0",
            padding: "18px 22px",
            background: "var(--concrete)",
            border: "1px solid var(--rebar)",
            borderLeft: `3px solid var(--${f.key === "centrality" ? "cadre" : f.key === "association" ? "rent" : f.key === "velocity" ? "heat" : "laser"})`,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
              <div>
                <span className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.28em" }}>FEATURE f{["₁","₂","₃","₄"][i]}</span>
                <div className="num" style={{ fontSize: 16, color: "var(--bone)", fontWeight: 700, letterSpacing: "0.14em", marginTop: 4 }}>
                  {f.label}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.22em" }}>CAP</div>
                <div className="num" style={{ fontSize: 18, color: "var(--bone)", fontWeight: 700 }}>+{f.cap.toFixed(2)}</div>
              </div>
            </div>

            <div className="doc-formula" style={{ marginTop: 8, marginBottom: 12 }}>{f.formula}</div>

            <div className="doc-body" style={{ marginBottom: 0 }}>{f.logic}</div>

            <div className="doc-note" style={{ marginTop: 12 }}>
              <span className="num" style={{ color: "var(--laser)", letterSpacing: "0.24em", marginRight: 6 }}>◆ FOOTNOTE</span>
              <span style={{ color: "var(--bone)" }}>{f.note}</span>
            </div>
          </div>
        ))}

        {/* GOSPEL */}
        <div className="doc-h2" style={{ marginTop: 48 }}>▸ The Gospel · targeting logic</div>
        <p className="doc-body">
          Gospel sorts the post-Lavender entity space into a strike queue. It does not assess motive. It does
          not produce evidence. It produces priorities, and then it produces engagements.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, margin: "20px 0" }}>
          {/* Sort */}
          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", padding: "16px 20px" }}>
            <div className="doc-h3" style={{ marginTop: 0 }}>SORT LOGIC</div>
            {DOCTRINE.gospel.sort.map((s, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "92px 1fr", gap: 12, padding: "6px 0", borderBottom: "1px dotted var(--rebar)" }}>
                <span className="num" style={{ fontSize: 10, color: "var(--laser)", letterSpacing: "0.22em" }}>{s.key}</span>
                <span style={{ fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--bone)" }}>{s.label}</span>
              </div>
            ))}
          </div>

          {/* Constraints */}
          <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", padding: "16px 20px" }}>
            <div className="doc-h3" style={{ marginTop: 0 }}>CONSTRAINTS</div>
            {DOCTRINE.gospel.constraints.map((s, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "92px 1fr", gap: 12, padding: "6px 0", borderBottom: "1px dotted var(--rebar)" }}>
                <span className="num" style={{ fontSize: 10, color: "var(--heat)", letterSpacing: "0.22em" }}>{s.key}</span>
                <span style={{ fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--bone)" }}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Execution pseudo-code */}
        <div style={{ background: "var(--void)", border: "1px solid var(--rebar)", padding: "16px 20px", margin: "20px 0" }}>
          <div className="doc-h3" style={{ marginTop: 0 }}>EXECUTION · PSEUDO-CODE</div>
          <pre style={{
            fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--solidarity)",
            margin: 0, lineHeight: 1.6, letterSpacing: "0.02em", whiteSpace: "pre-wrap",
          }}>
{`for each tick t:
    G ← LavenderScore(WorldState.LegibleGraph, t)
    Q ← sort(G, by=risk desc, then=opportunity desc, then=cde asc)
    Q ← filter(Q, where cde ≤ POLICY)         # CDE_HOLD if exceeded
    B ← THREAD_BUDGET
    for entity in Q:
        if B < entity.threads:  break
        Engage(entity)                         # produces ATTRITION or BLOWBACK
        B -= entity.threads
    Assess(prior_agitation, post_agitation)    # may misattribute`}
          </pre>
        </div>

        {/* Notes section — the indictment */}
        <div className="doc-h2">▸ Footnotes · operational caveats</div>
        {DOCTRINE.gospel.notes.map((n, i) => (
          <div key={i} className="doc-note" style={{ marginTop: 10 }}>
            <span className="num" style={{ color: "var(--laser)", letterSpacing: "0.2em", marginRight: 6 }}>◆ §{i + 1}</span>
            <span style={{ color: "var(--bone)" }}>{n}</span>
          </div>
        ))}

        {/* Counter-measures (player advisory) */}
        <div className="doc-h2" style={{ marginTop: 48 }}>▸ Adversary counter-measures · advisory only</div>
        <p className="doc-body" style={{ marginBottom: 14 }}>
          The following adversary behaviors degrade Lavender accuracy. They are catalogued for operator
          awareness. They are not actionable from this terminal.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 18 }}>
          {[
            ["TOPOLOGICAL HYGIENE", "ACT_ORGANIZE_CELLS",
              "Adversary severs edges to reduce its own Betweenness Centrality. Efficiency cost ↓. Lavender score ↓.",
              "Detectable via cluster fragmentation over time. Risk: false-negative on remaining nodes."],
            ["PATTERN MIMICRY", "ACT_GO_DARK",
              "Adversary halts resource flow. Velocity anomaly → 0. Risk decays geometrically over n ticks.",
              "Detectable via prolonged dwell at zero velocity. Risk: starvation in own ranks."],
            ["DATA POISONING", "ACT_CREATE_DECOY",
              "Adversary spawns a node with high centrality, high velocity, zero revolutionary value. Strike → BLOWBACK.",
              "Detectable post-hoc via legitimacy delta. Risk: catastrophic."],
            ["HUMAN SHIELDING", "ACT_EMBED_POPULATION",
              "Adversary relocates high-value cadre to high-density territory. CDE rises. Policy may filter.",
              "The Gospel does not block. The Gospel holds. Held targets accumulate."],
          ].map(([name, act, desc, note]) => (
            <div key={name} style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", padding: "14px 16px" }}>
              <div className="num" style={{ fontSize: 10, color: "var(--rupture)", letterSpacing: "0.28em", fontWeight: 700 }}>{name}</div>
              <div className="num" style={{ fontSize: 11, color: "var(--bone)", letterSpacing: "0.14em", marginTop: 4 }}>{act}</div>
              <div style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--bone)", marginTop: 10, lineHeight: 1.55 }}>{desc}</div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--ash)", marginTop: 8, lineHeight: 1.5, letterSpacing: "0.04em", fontStyle: "italic" }}>
                {note}
              </div>
            </div>
          ))}
        </div>

        {/* Sign-off block */}
        <div style={{ marginTop: 56, paddingTop: 22, borderTop: "1px solid var(--rebar)", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.28em" }}>RELEASED BY</div>
            <div className="num" style={{ fontSize: 13, color: "var(--bone)", letterSpacing: "0.16em", fontWeight: 700, marginTop: 4 }}>{META.operator}</div>
            <div className="num" style={{ fontSize: 10, color: "var(--ash)", letterSpacing: "0.18em", marginTop: 2 }}>OPERATOR · ALGORITHMIC TARGETING CELL</div>
          </div>
          <div className="doc-stamp" style={{ transform: "rotate(-3deg)" }}>STATE EYES ONLY</div>
          <div style={{ textAlign: "right" }}>
            <div className="num" style={{ fontSize: 9, color: "var(--ash)", letterSpacing: "0.28em" }}>DECLASSIFY ON</div>
            <div className="num" style={{ fontSize: 13, color: "var(--laser)", letterSpacing: "0.18em", fontWeight: 700, marginTop: 4 }}>NEVER</div>
          </div>
        </div>
      </div>
    </div>
  );
};

window.DoctrineTab = DoctrineTab;
