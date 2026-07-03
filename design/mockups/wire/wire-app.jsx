// wire-app.jsx — The Wire main shell (tabbed window)
//
// Window chrome (WireWindow) wraps four tabs:
//   WIRE     — triptych comparative reading view (the main feature)
//   INDEX    — story archive (formerly the left rail)
//   PATTERNS — Manufacturing Consent dashboard (formerly the right rail, full-page)
//   CORPUS   — RAG retrieval browser
// A slim hover-translation footer below the triptych shows the active euphemism's
// translation in-context so the right rail can move to its own tab without losing
// the sync-highlight feedback.

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "tab": "wire",
  "layout": "triptych",
  "focus_channel": "liberated",
  "euph_always_on": false,
  "citation_density": "normal",
  "show_intel": true
}/*EDITMODE-END*/;

const WireApp = () => {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [activeId, setActiveId] = React.useState("WC-RAID-0042");
  const [activeEuph, setActiveEuph] = React.useState(null);
  const [activeSup, setActiveSup] = React.useState(null);

  const meta = window.WIRE_DATA.meta;
  const euphs = window.WIRE_DATA.euphemisms;

  // tab switch helper — used by IndexPage onOpen to jump to the WIRE tab
  const goToWire = (storyId) => {
    setActiveId(storyId);
    setTweak("tab", "wire");
  };

  // Tabs metadata
  const tabs = [
    { id: "wire",     label: "The Wire", count: 3, dot: "var(--spire)" },
    { id: "index",    label: "Wire Index", count: window.WIRE_DATA.index.length },
    { id: "patterns", label: "Patterns", count: Object.keys(euphs).length, dot: "var(--laser)" },
    { id: "corpus",   label: "Corpus" },
  ];

  // Tick badge for the title bar
  const badge = (
    <>
      <span className="label">TICK</span>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700,
        color: "var(--spire)", textShadow: "0 0 10px rgba(77,217,230,0.4)",
        letterSpacing: "0.04em",
      }}>{String(meta.tick).padStart(4, "0")}</span>
      <span style={{ width: 1, height: 18, background: "var(--rebar)", margin: "0 8px" }}></span>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--fog)", letterSpacing: "0.18em" }}>
        OP · {meta.operator}
      </span>
      <a href="../ui_kits/webapp/index.html" className="btn-ghost" style={{ marginLeft: 10, textDecoration: "none" }}>← Cockpit</a>
    </>
  );

  // === WIRE TAB (triptych) ===
  const wireTab = (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }} className={t.euph_always_on ? "euph-always" : ""}>
      {/* Story chrome — current story header */}
      <div style={{
        flexShrink: 0,
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "10px 18px",
        background: "rgba(255,255,255,0.012)",
        borderBottom: "1px solid var(--rebar)",
        gap: 14,
      }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 14, minWidth: 0 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ash)", letterSpacing: "0.22em" }}>
            STORY
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--spire)", letterSpacing: "0.14em" }}>
            {activeId}
          </span>
          <span style={{ width: 1, height: 14, background: "var(--rebar)" }}></span>
          <span style={{
            fontFamily: "var(--font-sans)", fontSize: 12, fontWeight: 600,
            letterSpacing: "0.22em", textTransform: "uppercase",
            color: "var(--bone)",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {window.WIRE_DATA.index.find(s => s.id === activeId)?.slug || ""}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 14, flexShrink: 0 }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--fog)", letterSpacing: "0.2em", textTransform: "uppercase" }}>
            neutrality is hegemony
          </span>
          <span style={{ width: 1, height: 14, background: "var(--rebar)" }}></span>
          {/* Layout switcher */}
          <div style={{ display: "flex", gap: 4 }}>
            {[
              ["triptych", "Triptych"],
              ["two_up",   "2-Up"],
              ["focus",    "Focus"],
            ].map(([k, l]) => (
              <button
                key={k}
                className={"btn-ghost" + (t.layout === k ? " active" : "")}
                onClick={() => setTweak("layout", k)}
              >{l}</button>
            ))}
          </div>
          {t.layout === "focus" && (
            <div style={{ display: "flex", gap: 4, paddingLeft: 6, borderLeft: "1px solid var(--rebar)" }}>
              {[
                ["continental", "Cont", "var(--cadre)"],
                ["liberated",   "Free", "var(--solidarity)"],
                ["intel",       "Cable", "var(--rupture)"],
              ].map(([k, l, c]) => (
                <button
                  key={k}
                  className={"btn-ghost" + (t.focus_channel === k ? " active" : "")}
                  onClick={() => setTweak("focus_channel", k)}
                  style={t.focus_channel === k ? { borderColor: c, color: c, background: "rgba(255,255,255,0.03)" } : {}}
                >{l}</button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Triptych */}
      <div style={{ flex: 1, display: "flex", minHeight: 0, overflow: "hidden" }}>
        {(t.layout === "triptych" || t.layout === "two_up" || (t.layout === "focus" && t.focus_channel === "continental")) && (
          <ContinentalColumn
            activeEuph={activeEuph}
            setActiveEuph={setActiveEuph}
            activeSup={activeSup}
            setActiveSup={setActiveSup}
            euphAlways={t.euph_always_on}
            citationDensity={t.citation_density}
            focused={t.layout === "focus"}
          />
        )}
        {(t.layout === "triptych" || t.layout === "two_up" || (t.layout === "focus" && t.focus_channel === "liberated")) && (
          <>
            {t.layout !== "focus" && <div className="drift" />}
            <LiberatedColumn
              activeEuph={activeEuph}
              setActiveEuph={setActiveEuph}
              euphAlways={t.euph_always_on}
              citationDensity={t.citation_density}
              focused={t.layout === "focus"}
            />
          </>
        )}
        {t.show_intel && (t.layout === "triptych" || (t.layout === "focus" && t.focus_channel === "intel")) && (
          <>
            {t.layout !== "focus" && <div className="drift" />}
            <IntelColumn citationDensity={t.citation_density} focused={t.layout === "focus"} />
          </>
        )}
      </div>

      {/* Slim translation footer — the right-rail Pattern chip in a single horizontal strip */}
      <TranslationFooter
        activeEuph={activeEuph}
        setActiveEuph={setActiveEuph}
        euphAlways={t.euph_always_on}
        setEuphAlways={(v) => setTweak("euph_always_on", v)}
        onOpenPatterns={() => setTweak("tab", "patterns")}
      />
    </div>
  );

  return (
    <WireWindow
      tabs={tabs}
      activeId={t.tab}
      onTab={(id) => setTweak("tab", id)}
      badge={badge}
    >
      {t.tab === "wire"     && wireTab}
      {t.tab === "index"    && <IndexPage activeId={activeId} setActiveId={setActiveId} onOpen={goToWire} />}
      {t.tab === "patterns" && <PatternsPage />}
      {t.tab === "corpus"   && <CorpusPage />}

      <TweaksPanel title="Tweaks">
        <TweakSection label="Tab">
          <TweakRadio
            label="View"
            value={t.tab}
            onChange={v => setTweak("tab", v)}
            options={[
              { value: "wire",     label: "Wire" },
              { value: "index",    label: "Index" },
              { value: "patterns", label: "Pat." },
              { value: "corpus",   label: "Corp." },
            ]}
          />
        </TweakSection>

        <TweakSection label="Triptych layout">
          <TweakRadio
            label="Mode"
            value={t.layout}
            onChange={v => setTweak("layout", v)}
            options={[
              { value: "triptych", label: "Triptych" },
              { value: "two_up",   label: "2-Up" },
              { value: "focus",    label: "Focus" },
            ]}
          />
          {t.layout === "focus" && (
            <TweakSelect
              label="Focus channel"
              value={t.focus_channel}
              onChange={v => setTweak("focus_channel", v)}
              options={[
                { value: "continental", label: "Continental (Corporate)" },
                { value: "liberated",   label: "Free Signal (Liberated)" },
                { value: "intel",       label: "Cable / Intel" },
              ]}
            />
          )}
        </TweakSection>

        <TweakSection label="Euphemism overlay">
          <TweakToggle
            label="Always-on (strikethrough + glow)"
            value={t.euph_always_on}
            onChange={v => setTweak("euph_always_on", v)}
          />
        </TweakSection>

        <TweakSection label="Citations (RAG)">
          <TweakRadio
            label="Density"
            value={t.citation_density}
            onChange={v => setTweak("citation_density", v)}
            options={[
              { value: "off",    label: "Off" },
              { value: "normal", label: "Normal" },
              { value: "dense",  label: "Dense" },
            ]}
          />
        </TweakSection>

        <TweakSection label="Fog of War">
          <TweakToggle
            label="Intel channel unlocked"
            value={t.show_intel}
            onChange={v => setTweak("show_intel", v)}
          />
        </TweakSection>
      </TweaksPanel>
    </WireWindow>
  );
};


// ============================================================================
// TranslationFooter — slim bottom strip below the triptych. Shows the live
// translation chip when a euphemism is hovered; otherwise shows status counts
// and a CTA to open the Patterns tab.
// ============================================================================
const TranslationFooter = ({ activeEuph, setActiveEuph, euphAlways, setEuphAlways, onOpenPatterns }) => {
  const euphs = window.WIRE_DATA.euphemisms;
  const filters = window.WIRE_DATA.filters;
  const active = activeEuph ? euphs[activeEuph] : null;
  const total = Object.keys(euphs).length;
  const filterTotal = filters.reduce((s, f) => s + f.hits, 0);

  return (
    <div style={{
      flexShrink: 0,
      borderTop: "1px solid var(--rebar)",
      background: "linear-gradient(180deg, #0a0d13 0%, var(--void) 100%)",
      padding: "10px 18px",
      display: "flex", alignItems: "center", gap: 18,
      minHeight: 54,
    }}>
      <span className="label" style={{ color: active ? "var(--laser)" : "var(--ash)", flexShrink: 0 }}>
        ▸ Euphemism map
      </span>

      {active ? (
        <div style={{ display: "flex", alignItems: "center", gap: 14, flex: 1, minWidth: 0 }}>
          <span style={{
            fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--bone)",
            textDecoration: "line-through", textDecorationColor: "var(--laser)", textDecorationThickness: 1,
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            maxWidth: "32%",
          }}>
            &ldquo;{active.c}&rdquo;
          </span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--laser)", flexShrink: 0 }}>→</span>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600,
            color: "#b4ffd1", letterSpacing: "0.02em",
            textShadow: "0 0 6px rgba(95,191,122,0.4)",
            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            maxWidth: "32%",
          }}>
            {active.l}
          </span>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 9.5,
            color: "var(--rupture)", letterSpacing: "0.2em", textTransform: "uppercase",
            padding: "3px 8px", border: "1px solid rgba(212,160,44,0.4)", borderRadius: 3,
            flexShrink: 0,
          }}>
            FILTER · {active.filter}
          </span>
          <span style={{
            fontSize: 12, color: "var(--fog)", lineHeight: 1.4,
            flex: 1, minWidth: 0,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {active.note}
          </span>
        </div>
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: 14, flex: 1, minWidth: 0 }}>
          <span style={{ fontSize: 12, color: "var(--fog)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            Hover a flagged term to see how the same fact is rendered across registers.
          </span>
          <div style={{ display: "flex", gap: 14, flexShrink: 0, marginLeft: "auto" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: "0.16em" }}>
              EUPHEMISMS <span style={{ color: "var(--laser)", fontWeight: 700 }}>{total}</span>
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: "0.16em" }}>
              FILTER HITS <span style={{ color: "var(--heat)", fontWeight: 700 }}>{filterTotal}</span>
            </span>
          </div>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 9, color: "var(--fog)", letterSpacing: "0.18em" }}>ALWAYS ON</span>
          <span style={{
            width: 22, height: 12, borderRadius: 9999,
            background: euphAlways ? "var(--spire)" : "var(--rebar)",
            position: "relative", transition: "background 120ms",
          }}>
            <span style={{
              position: "absolute", top: 1, left: euphAlways ? 11 : 1,
              width: 10, height: 10, borderRadius: 9999,
              background: euphAlways ? "var(--void)" : "var(--fog)",
              transition: "left 120ms",
            }}></span>
          </span>
          <input type="checkbox" checked={euphAlways} onChange={e => setEuphAlways(e.target.checked)} style={{ display: "none" }} />
        </label>
        <button className="btn-ghost" onClick={onOpenPatterns}>Open Patterns ▸</button>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<WireApp />);
