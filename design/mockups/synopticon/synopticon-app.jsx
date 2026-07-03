// synopticon-app.jsx — Algorithmic State Apparatus main shell

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "tab": "panopticon",
  "selected_dossier": "ENT-7741-A",
  "show_ghosts": true,
  "show_pulses": true,
  "tick_pulse": true
}/*EDITMODE-END*/;

const SynopticonApp = () => {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const M = window.SYN_DATA.META;

  // Tick badge — laser red instead of spire cyan; matches the surveillance role
  const badge = (
    <>
      <span className="label">TICK</span>
      <span className={t.tick_pulse ? "blink-laser" : ""} style={{
        fontFamily: "var(--font-mono)", fontSize: 18, fontWeight: 700,
        color: "var(--laser)", textShadow: "0 0 10px rgba(255,51,68,0.5)",
        letterSpacing: "0.04em",
      }}>{String(M.tick).padStart(4, "0")}</span>
      <span style={{ width: 1, height: 18, background: "var(--rebar)", margin: "0 8px" }}></span>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--ash)", letterSpacing: "0.18em" }}>
        OP · {M.operator}
      </span>
    </>
  );

  // Tabs metadata
  const tabs = [
    { id: "panopticon", label: "Panopticon", count: M.flagged,    accent: "var(--laser)" },
    { id: "dossiers",   label: "Dossiers",   count: window.SYN_DATA.DOSSIERS.length, accent: "var(--laser)" },
    { id: "gospel",     label: "Gospel",     count: M.on_kill_list, accent: "var(--laser)" },
    { id: "doctrine",   label: "Doctrine",                          accent: "var(--rupture)" },
  ];

  const goToDossier = (entityId) => {
    setTweak("selected_dossier", entityId);
    setTweak("tab", "dossiers");
  };
  const goToGospel = () => setTweak("tab", "gospel");

  return (
    <SynopticonWindow
      tabs={tabs}
      activeId={t.tab}
      onTab={(id) => setTweak("tab", id)}
      badge={badge}
      classification={M.classification}
    >
      {t.tab === "panopticon" && (
        <PanopticonTab onOpenGospel={goToGospel} onOpenDossier={goToDossier} />
      )}
      {t.tab === "dossiers" && (
        <DossiersTab
          selectedId={t.selected_dossier}
          setSelectedId={(id) => setTweak("selected_dossier", id)}
        />
      )}
      {t.tab === "gospel" && <GospelTab />}
      {t.tab === "doctrine" && <DoctrineTab />}

      <TweaksPanel title="Tweaks">
        <TweakSection label="View">
          <TweakRadio
            label="Tab"
            value={t.tab}
            onChange={v => setTweak("tab", v)}
            options={[
              { value: "panopticon", label: "Panopt." },
              { value: "dossiers",   label: "Doss." },
              { value: "gospel",     label: "Gospel" },
              { value: "doctrine",   label: "Doct." },
            ]}
          />
        </TweakSection>

        <TweakSection label="Heatmap">
          <TweakToggle
            label="Show ghost nodes (signal-loss inferences)"
            value={t.show_ghosts}
            onChange={v => setTweak("show_ghosts", v)}
          />
          <TweakToggle
            label="Target pulses"
            value={t.show_pulses}
            onChange={v => setTweak("show_pulses", v)}
          />
        </TweakSection>

        <TweakSection label="Chrome">
          <TweakToggle
            label="Tick counter blinks"
            value={t.tick_pulse}
            onChange={v => setTweak("tick_pulse", v)}
          />
        </TweakSection>

        <TweakSection label="Jump to dossier">
          <TweakSelect
            label="Entity"
            value={t.selected_dossier}
            onChange={v => { setTweak("selected_dossier", v); setTweak("tab", "dossiers"); }}
            options={window.SYN_DATA.DOSSIERS.map(d => ({
              value: d.id, label: `${d.id} · ${d.alias} · r=${d.risk_score}`,
            }))}
          />
        </TweakSection>
      </TweaksPanel>
    </SynopticonWindow>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<SynopticonApp />);
