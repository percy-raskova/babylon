# spec-113 integration ledger (orchestrator-owned wiring between waves)

Cross-lane seams deliberately left to the orchestrator so concurrent lanes stay
file-disjoint. Checked off as done; anything unchecked at program end becomes an
owner item.

## After Wave 2

- [x] Lane C unwraps the explain envelope — ExplainResponse types mirror
      `_explain_result_to_dict` + MSW fixtures; live payload confirmed 2026-07-11 vs
      session 5ad0c6ae (exploitation_rate 0.0 @ tick 0, recursive
      value_extraction_ratio ref).
- [x] `narrationPanel` registered (TAKEOVER_PANEL_KEYS + PanelsSlice) + `useNarration`
      hook + EventTray narrator strip — commit `0cc2f38a`.
- [~] `NarrationBlock` mounts: EventTray ✓; chronicle/endgame + wire strip → Wave 3
      SKIN-MENUS; county InspectionCard section → deferred (needs fips↔beat adapter,
      queue for Phase D/owner).
- [ ] Three-channel critical events (bible §5.2): map-anchored cue for criticals —
      post-Wave-3 polish (event→geo ref data exists; cue layer is map-side).
- [x] `inspectSlice` tick refetch: C used `api.subscribe` from its own slice file;
      unit-tested.
- [x] mapSlice default-framing flip residue: MapStage test fixed by orchestrator in
      the wave-2 commit; C decoupled mapSlice.test from B's DEFAULT_LENS.
- [~] `region-dock` / `region-bottomstrip` placements → Lane G rewriting real-loop
      assertions in Wave 3; live validation in Phase V.
- [~] TopBar StatChip metric props → Wave 3 SKIN-CHROME (chips click-ready).
- [ ] `lib/inspectorMapping.ts` absorb → Wave 3 Lane G.

NOTE: the "Juice Pass" inventory below predates DESIGN_BIBLE §9b (The Installer,
owner ruling) — §9b's re-aim SUPERSEDES the gradient/glow items; the performance
budget remains binding law.

## Phase D (design/reskin) queue

### The Juice Pass (owner directive 2026-07-11: "really fancy Tailwind + effects,
### as long as they don't bog down performance — make it feel like a **game**")

Effects inventory (Tailwind v4 + custom keyframes; extend the takeovers'
phosphor/scanline language into all chrome):
- Panel chrome: gradient hairline borders (conic accents at corners), layered
  box-shadow glow tokens (cyan ambient + red urgency), backdrop-blur + saturate
  on floating panels, subtle noise texture via data-URI background.
- Text: phosphor bloom (text-shadow token) on display-register numerals; wire
  headlines get a one-shot CRT-reveal on arrival.
- Motion (@keyframes): tick pulse on the time cluster (every resolve);
  toast slam-in + settle; critical-alert throb (border/glow only); claim-redraw
  shimmer along the new border path (≥600ms, cause-named per bible §2.2);
  legend flash on domain change; endgame takeover iris/fade.
- Map chrome: vignette + scanline mask on takeover overlays only (never the
  live map canvas); selection halo pulse; hover glow signifiers (Norman).

PERFORMANCE BUDGET (hard rules):
- Compositor-only animation: transform + opacity ONLY on persistent/looping
  animations; no animated filter/backdrop-filter/box-shadow loops on large
  surfaces; one-shot entrance effects may animate shadow/filter.
- backdrop-blur is expensive over a live WebGL canvas: small panels only
  (≤ ~25% viewport each), never full-screen scrims while unpaused.
- `prefers-reduced-motion` honored globally (all loops off, one-shots reduced
  to fades) + a settings kill-switch.
- Nothing animates on the deck.gl render path itself except deck-native layer
  transitions; DeckGLMap.stability render-count test must stay green.
- Verify: Chrome DevTools performance profile on the wayne_county session —
  no long tasks from CSS, 60fps pan/zoom preserved with all effects on.

- [ ] Extend takeover diegetic language into shell chrome (audit: two visual
      languages; reskin = extend the first into the second).
- [ ] OrgSelect + faction `<select>` restyle in-register (bible §9.6).
- [ ] TimeseriesChart de-chart-ification toward BblData idiom (bible §9.7).
- [ ] BottomDrawer bottom-right toggle per bible layout (Lane A shipped full-width
      footer as structure-now placeholder).
- [ ] Contested-claim TRUE striping (FillStyleExtension pattern) if Lane B shipped
      dash-only.
- [ ] Empty-state copy sweep — every surface in-register (Lanes E/F purge their own;
      sweep the rest).
- [ ] ds-sync: new chrome components → barrel + componentSrcMap; re-sync to
      "Babylon Cockpit" project; grade renders.

## Owner items raised en route

- bridge_county_h3 res-5/res-7 vs Constitution II.13 res-8 (Program 11 flag) —
  recorded in charter.
- BLS LAUS county file needs re-fetch (data survey).
- profit_rate/occ have no live engine source (Lane D honest nulls) — engine-side
  wiring is an engine-team item, not frontend.
