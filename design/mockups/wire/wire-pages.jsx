// wire-pages.jsx — Full-page tab content for INDEX, PATTERNS, CORPUS.
// The triptych stays its own tab in wire-app.jsx; these three give the
// supporting data room to breathe instead of crowding the main reading view.

// ============================================================================
// INDEX PAGE — story archive
// ============================================================================
const IndexPage = ({ activeId, setActiveId, onOpen }) => {
  const idx = window.WIRE_DATA.index;
  const [filter, setFilter] = React.useState("all");
  const filters = [
    ["all",      "All",      idx.length],
    ["critical", "Critical", idx.filter(s => s.severity === "critical").length],
    ["warning",  "Warning",  idx.filter(s => s.severity === "warning").length],
    ["info",     "Info",     idx.filter(s => s.severity === "info").length],
  ];
  const shown = filter === "all" ? idx : idx.filter(s => s.severity === filter);

  const sevColor = (s) =>
    s === "critical" ? "var(--laser)" :
    s === "warning"  ? "var(--heat)"  : "var(--solidarity)";

  return (
    <div style={{ padding: "20px 28px", height: "100%", overflowY: "auto", background: "var(--void)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 18 }}>
        <div>
          <div className="label" style={{ marginBottom: 4 }}>▸ Wire Index</div>
          <div style={{ fontFamily: "var(--font-sans)", fontSize: 22, fontWeight: 700, letterSpacing: "0.04em", color: "var(--bone)" }}>
            Recent dispatches · Wayne County
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fog)", letterSpacing: "0.16em", marginTop: 4 }}>
            T={window.WIRE_DATA.meta.tick} · {idx.length} STORIES · NEXT REFRESH T+1
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {filters.map(([f, l, n]) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={"btn-ghost" + (filter === f ? " active" : "")}
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              {l}
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)" }}>×{n}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gap: 10 }}>
        {shown.map(s => {
          const isActive = s.id === activeId;
          return (
            <div
              key={s.id}
              onClick={() => onOpen(s.id)}
              style={{
                background: "var(--concrete)",
                border: "1px solid " + (isActive ? "var(--spire)" : "var(--rebar)"),
                borderLeft: "3px solid " + sevColor(s.severity),
                borderRadius: 6,
                padding: "14px 18px",
                cursor: "pointer",
                transition: "border-color 120ms, background 120ms",
                display: "grid",
                gridTemplateColumns: "84px 1fr auto",
                gap: 18,
                alignItems: "stretch",
              }}
              onMouseOver={e => { if (!isActive) e.currentTarget.style.borderColor = "var(--wet-steel)"; }}
              onMouseOut ={e => { if (!isActive) e.currentTarget.style.borderColor = "var(--rebar)"; }}
            >
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 4 }}>
                <span className="label">TICK</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700, color: "var(--spire)", lineHeight: 1, textShadow: "0 0 8px rgba(77,217,230,0.35)" }}>
                  {String(s.tick).padStart(4,"0")}
                </span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: sevColor(s.severity), letterSpacing: "0.18em", textTransform: "uppercase" }}>
                  ● {s.severity}
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontFamily: "var(--font-sans)", fontSize: 11, fontWeight: 600, letterSpacing: "0.22em", textTransform: "uppercase", color: "var(--ash)" }}>
                  {s.slug} · <span style={{ color: "var(--fog)" }}>{s.id}</span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
                  {/* Continental */}
                  <div style={{ borderLeft: "2px solid var(--cadre)", paddingLeft: 10 }}>
                    <div className="label" style={{ color: "var(--cadre)", marginBottom: 3 }}>Continental</div>
                    <div style={{ fontFamily: "var(--font-sans)", fontSize: 13, lineHeight: 1.35, color: s.coverage.includes("c") ? "var(--bone)" : "var(--ash)", fontWeight: 500 }}>
                      {s.hed.c}
                    </div>
                  </div>
                  {/* Free Signal */}
                  <div style={{ borderLeft: "2px solid var(--solidarity)", paddingLeft: 10 }}>
                    <div className="label" style={{ color: "var(--solidarity)", marginBottom: 3 }}>Free Signal</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.35, color: s.coverage.includes("l") ? "#b4ffd1" : "var(--ash)", letterSpacing: "0.01em", textShadow: s.coverage.includes("l") ? "0 0 6px rgba(95,191,122,0.3)" : "none" }}>
                      {s.hed.l}
                    </div>
                  </div>
                  {/* Cable */}
                  <div style={{ borderLeft: "2px solid var(--rupture)", paddingLeft: 10 }}>
                    <div className="label" style={{ color: "var(--rupture)", marginBottom: 3 }}>Cable / Intel</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.35, color: s.coverage.includes("i") ? "var(--bone)" : "var(--ash)", letterSpacing: "0.04em" }}>
                      {s.hed.i}
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", justifyContent: "space-between", gap: 8 }}>
                <div style={{ display: "flex", gap: 4 }}>
                  {["c", "l", "i"].map(k => (
                    <span key={k} style={{
                      fontFamily: "var(--font-mono)", fontSize: 9, letterSpacing: "0.18em",
                      padding: "2px 6px", borderRadius: 3,
                      border: "1px solid " + (s.coverage.includes(k) ? "var(--wet-steel)" : "var(--rebar)"),
                      background: s.coverage.includes(k) ? "var(--rebar)" : "transparent",
                      color: s.coverage.includes(k) ? "var(--fog)" : "var(--shroud)",
                    }}>
                      {k.toUpperCase()}{s.coverage.includes(k) ? "" : "·"}
                    </span>
                  ))}
                </div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: "0.18em" }}>
                  OPEN ▸
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
window.IndexPage = IndexPage;


// ============================================================================
// PATTERNS PAGE — Manufacturing Consent dashboard
// ============================================================================
const PatternsPage = () => {
  const euphs = window.WIRE_DATA.euphemisms;
  const filters = window.WIRE_DATA.filters;
  const story = window.WIRE_DATA.story;
  const totalHits = filters.reduce((s, f) => s + f.hits, 0);
  const consentScore = Math.min(100, Math.round((totalHits / 20) * 100));

  return (
    <div style={{ padding: "20px 28px", height: "100%", overflowY: "auto", background: "var(--void)" }}>
      <div style={{ marginBottom: 18 }}>
        <div className="label" style={{ marginBottom: 4 }}>▸ Pattern Analysis</div>
        <div style={{ fontFamily: "var(--font-sans)", fontSize: 22, fontWeight: 700, letterSpacing: "0.04em", color: "var(--bone)" }}>
          Manufacturing Consent · live audit
        </div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fog)", letterSpacing: "0.16em", marginTop: 4 }}>
          STORY {story.id} · {totalHits} FILTER HITS · {Object.keys(euphs).length} EUPHEMISMS DETECTED
        </div>
      </div>

      {/* Headline score panel */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 320px",
        gap: 14,
        marginBottom: 18,
      }}>
        <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "18px 22px" }}>
          <div className="label" style={{ marginBottom: 6 }}>Manufactured-consent score · this story</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 56, fontWeight: 700, color: "var(--laser)", lineHeight: 1, textShadow: "0 0 18px rgba(255,51,68,0.4)" }}>
              {consentScore}
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--fog)", letterSpacing: "0.18em" }}>/ 100</span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--heat)", letterSpacing: "0.22em", textTransform: "uppercase", padding: "3px 8px", border: "1px solid var(--heat)", borderRadius: 3, marginLeft: "auto" }}>
              HIGH MEDIATION
            </span>
          </div>
          <div style={{ marginTop: 12, fontSize: 12.5, color: "var(--fog)", lineHeight: 1.55 }}>
            All five Herman/Chomsky filters are firing on this story. Source distribution is state-dominant
            ({filters.find(f => f.id === "sourcing").hits}/5 named sources). Ownership and advertiser exposure to the
            implicated industries is non-trivial. The Continental piece is, technically, accurate; the editing is
            where consent is manufactured.
          </div>
        </div>

        <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, padding: "14px 18px" }}>
          <div className="label" style={{ marginBottom: 8, color: "var(--rupture)" }}>The thesis</div>
          <div style={{ fontSize: 12, color: "var(--fog)", lineHeight: 1.6, fontStyle: "italic" }}>
            &ldquo;The mass media serve as a system for communicating messages and symbols to the general populace.
            It is their function to amuse, entertain, and inform, and to inculcate individuals with the values, beliefs,
            and codes of behavior that will integrate them into the institutional structures of the larger society.&rdquo;
          </div>
          <div style={{ marginTop: 8, fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: "0.18em" }}>
            — HERMAN &amp; CHOMSKY · 1988
          </div>
        </div>
      </div>

      {/* Five filters */}
      <div style={{ marginBottom: 22 }}>
        <div className="label" style={{ marginBottom: 10 }}>▸ Five filters · this story</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 10 }}>
          {filters.map(f => (
            <div key={f.id} className="filter-card" style={{ padding: 14, marginBottom: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
                <span style={{ fontFamily: "var(--font-sans)", fontSize: 14, fontWeight: 600, color: "var(--bone)" }}>
                  {f.label}
                </span>
                <span className="mono" style={{ fontSize: 13, color: f.color, fontWeight: 700, letterSpacing: "0.04em" }}>
                  ×{f.hits}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--fog)", lineHeight: 1.5, marginBottom: 10 }}>
                {f.desc}
              </div>
              <div style={{ height: 4, background: "var(--rebar)", borderRadius: 9999, overflow: "hidden" }}>
                <div style={{ width: (Math.min(f.hits, 5) / 5 * 100) + "%", height: "100%", background: f.color, boxShadow: `0 0 8px ${f.color}` }}></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Euphemism table — all flagged terms with their honest equivalents */}
      <div>
        <div className="label" style={{ marginBottom: 10 }}>▸ Euphemism map · {Object.keys(euphs).length} detected</div>
        <div style={{ background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 6, overflow: "hidden" }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1.2fr 130px",
            gap: 14,
            padding: "10px 18px",
            background: "rgba(255,255,255,0.02)",
            borderBottom: "1px solid var(--rebar)",
          }}>
            <span className="label" style={{ color: "var(--cadre)" }}>Continental said</span>
            <span className="label" style={{ color: "var(--solidarity)" }}>Free Signal said</span>
            <span className="label">Editorial intervention</span>
            <span className="label" style={{ color: "var(--ash)" }}>Filter</span>
          </div>
          {Object.entries(euphs).map(([id, e], idx) => (
            <div
              key={id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1.2fr 130px",
                gap: 14,
                padding: "10px 18px",
                borderBottom: idx < Object.keys(euphs).length - 1 ? "1px solid var(--rebar)" : "none",
                alignItems: "baseline",
              }}
            >
              <span style={{ fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--bone)", textDecoration: "line-through", textDecorationColor: "var(--laser)", textDecorationThickness: 1 }}>
                &ldquo;{e.c}&rdquo;
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#b4ffd1", fontWeight: 600, letterSpacing: "0.02em", textShadow: "0 0 4px rgba(95,191,122,0.35)" }}>
                {e.l}
              </span>
              <span style={{ fontSize: 12, color: "var(--fog)", lineHeight: 1.5 }}>
                {e.note}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: "var(--ash)", letterSpacing: "0.16em", textTransform: "uppercase" }}>
                {e.filter}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
window.PatternsPage = PatternsPage;


// ============================================================================
// CORPUS PAGE — RAG retrieval browser
// ============================================================================
const CorpusPage = () => {
  const story = window.WIRE_DATA.story;

  // Gather all chunks referenced across channels
  const chunks = [];
  story.continental.bibliography.forEach(b => chunks.push({
    chunk: b.chunk, sim: b.sim, src: b.src, kind: b.kind, id: b.id, channel: "continental",
  }));
  story.liberated.paragraphs.forEach(p => p.margin && chunks.push({
    chunk: p.margin.chunk, sim: 0.85, src: p.margin.ref, kind: "field witness", id: p.margin.ref, channel: "liberated", note: p.margin.note,
  }));
  story.intel.refs.forEach(r => chunks.push({
    chunk: r.id, sim: r.sim, src: r.src, kind: r.tag, id: r.id, channel: "intel",
  }));

  const [channelFilter, setChannelFilter] = React.useState("all");
  const shown = channelFilter === "all" ? chunks : chunks.filter(c => c.channel === channelFilter);

  const channelColor = (c) =>
    c === "continental" ? "var(--cadre)" :
    c === "liberated"   ? "var(--solidarity)" :
    c === "intel"       ? "var(--rupture)" : "var(--fog)";

  return (
    <div style={{ padding: "20px 28px", height: "100%", overflowY: "auto", background: "var(--void)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 18 }}>
        <div>
          <div className="label" style={{ marginBottom: 4 }}>▸ Corpus retrieval</div>
          <div style={{ fontFamily: "var(--font-sans)", fontSize: 22, fontWeight: 700, letterSpacing: "0.04em", color: "var(--bone)" }}>
            ChromaDB · The Archive
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fog)", letterSpacing: "0.16em", marginTop: 4 }}>
            {chunks.length} CHUNKS RETRIEVED FOR {story.id} · MODEL: bge-large-en-v1.5
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {[
            ["all",         "All",         chunks.length],
            ["continental", "Continental", chunks.filter(c => c.channel === "continental").length],
            ["liberated",   "Free Signal", chunks.filter(c => c.channel === "liberated").length],
            ["intel",       "Cable",       chunks.filter(c => c.channel === "intel").length],
          ].map(([k, l, n]) => (
            <button
              key={k}
              onClick={() => setChannelFilter(k)}
              className={"btn-ghost" + (channelFilter === k ? " active" : "")}
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              {l} <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--ash)" }}>×{n}</span>
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        {shown.map((c, idx) => (
          <div
            key={c.chunk + "-" + idx}
            style={{
              background: "var(--concrete)",
              border: "1px solid var(--rebar)",
              borderLeft: "3px solid " + channelColor(c.channel),
              borderRadius: 6,
              padding: "12px 18px",
              display: "grid",
              gridTemplateColumns: "auto 1fr auto",
              gap: 18,
              alignItems: "center",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 120 }}>
              <span className="label" style={{ color: channelColor(c.channel) }}>{c.channel}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--bone)", letterSpacing: "0.06em" }}>
                {c.chunk}
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
              <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--bone)", fontWeight: 500 }}>
                {c.src}
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: "0.14em", textTransform: "uppercase" }}>
                {c.kind} · {c.id}
              </span>
              {c.note && (
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fog)", marginTop: 4, lineHeight: 1.4 }}>
                  &ldquo;{c.note}&rdquo;
                </span>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, minWidth: 90 }}>
              <span className="label" style={{ color: "var(--ash)" }}>similarity</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 700, color: c.sim > 0.85 ? "var(--spire)" : c.sim > 0.75 ? "var(--cadre)" : "var(--ash)" }}>
                {c.sim.toFixed(2)}
              </span>
              <div style={{ width: 70, height: 3, background: "var(--rebar)", borderRadius: 9999, overflow: "hidden" }}>
                <div style={{ width: (c.sim * 100) + "%", height: "100%", background: c.sim > 0.85 ? "var(--spire)" : c.sim > 0.75 ? "var(--cadre)" : "var(--ash)" }}></div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 22, padding: "12px 16px", border: "1px dashed var(--rebar)", borderRadius: 6 }}>
        <div className="label" style={{ marginBottom: 6, color: "var(--rupture)" }}>Note · Archive is observer-only</div>
        <div style={{ fontSize: 12, color: "var(--fog)", lineHeight: 1.55 }}>
          Per Constitution VIII, The Archive (ChromaDB) provides semantic history for narrative
          but never controls simulation state. Retrieval here is read-only; the corpus is appended
          tick-by-tick from Ledger events.
        </div>
      </div>
    </div>
  );
};
window.CorpusPage = CorpusPage;
