# spec-113 integration ledger (orchestrator-owned wiring between waves)

Cross-lane seams deliberately left to the orchestrator so concurrent lanes stay
file-disjoint. Checked off as done; anything unchecked at program end becomes an
owner item.

## After Wave 2

- [ ] VERIFY Lane C unwraps the explain envelope: live payload is
      `{status, data: {metric, scope, value, formula, inputs, constants}, tick, session_id}`
      (verified live 2026-07-11 vs session 5ad0c6ae, tick 0: exploitation_rate 0.0,
      recursive value_extraction_ratio ref present). MSW fixtures must mirror the
      envelope.

- [ ] Register `narrationPanel` in `store/slices/panels/index.ts` + expose via store
      (Lane N ships the file unregistered by design).
- [ ] Mount `NarrationBlock` slots: wire cards (`takeovers/wire`), `EventToasts`,
      county `InspectionCard` (via a narration section), `ChronicleTakeover` endgame.
      Slot is props-driven, so each mount is a small local edit.
- [ ] Three-channel critical events (bible §5.2): map-anchored visual cue for
      critical events — Lane E ships the event→geo ref; the map cue layer belongs
      with Lane B's files; wire in Wave 3/polish.
- [ ] `worldSlice` ↔ `inspectSlice` top-frame refetch on tick: verify Lane C's
      chosen mechanism (subscribe vs fan-out) actually fires under the orchestrator.
- [ ] Confirm Lane C's mapSlice default-framing flip didn't strand Lane B tests
      that assumed 'hex' (both lanes told; verify anyway).
- [ ] `region-dock` / `region-bottomstrip` testid placements (Lane A best-effort)
      re-validated against real-loop.spec.ts on a live backend (Phase V), then Lane G
      rewrites the spec's dispersal-dependent assertions (Events button now opens
      EventTray, not BottomStrip).

## Phase D (design/reskin) queue

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
