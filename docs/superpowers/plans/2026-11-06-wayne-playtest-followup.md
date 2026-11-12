# Wayne play test follow-up implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development. Execute the three implementation tasks sequentially, with independent task reviews and a final connected review.

**Goal:** Make Wayne's resources, commitments, reports and time controls understandable through normal play.

**Architecture:** Extend the existing native client and admitted projections. Preserve engine authority, exact report identities, campaign knowledge and material units. Repair continuous playback through the existing committed-period/status lifecycle. Do not introduce a second simulation clock.

**Tech stack:** Locked Bevy 0.20, current Rust client, existing embedded fonts/art and native qualification infrastructure.

**Spec:** `docs/superpowers/specs/2026-11-03-wayne-map-and-relationships-design.md`, the approved November 5 direction and the Director's November 6 play test corrections.

## Global constraints

- Reuse the clean task worktree `/media/user/data/worktrees/0c51/babylon` and its existing PR #1052.
- Starting head is `a96a1881f71a8270bf33e37b1dc716948fd19714`.
- Target remains `dev`.
- Local `dev` has unrelated unpublished work.
- Do not adopt or change it.
- One source implementer and one heavy local job at a time.
- Use BLAS=1, the installed host/build controls and persistent TTYs.
- No documentation generation.
- Preserve P7, the separate P3 human campaign, its draft and all unique evidence.
- Native/runtime testing uses exact owned resources.
- Do not use default shared database commands.
- Only authoritative disclosed values can appear.
- Missing is not zero.
- Current balances cannot populate historical or stale/perspective-changed views.
- Captured commitments supply organizer-hours.
- Shared household time is a dated observation, not a new freely spendable volunteer pool.
- Do not add repeated projections of one budget.
- Format money with `$` and grouped digits, retaining exact amounts below one cent micros.
- This is presentation of the existing common currency, with no USD conversion or mechanics change.
- Group physical quantities.
- Do not group identifiers, periods or hashes.
- Keep authenticated Review, Confirm and Advance separate.
- Flavor describes intended work, not invented outcomes, people, dialog or guaranteed participation.
- Player knowledge cannot gain the full observer economy network.
- Route to supported Observer campaigns explicitly.
- Preserve the current saved world.
- Commit through `mise run commit`, with Part of PER-292, PER-331 and PER-302 where applicable.
- Update the canonical design, not a competing design authority.
- No merge.

## Review focus

- Large or negative balances, one-micro values and i128 limits keep exact meaning.
- History, pending status, changed generation/perspective and duplicated household budgets cannot disclose or double-count resources.
- Continuous Play waits for both exact current status and observation.
- Manual Pause remains available while status is pending, and one-off commitments execute once.
- A delayed inquiry and a current automatic report remain distinct, including observed/received dates and exact typed destinations.
- At 1366×768 and 1920×1080, plus supported enlarged settings, resource values and the selected report's answer are readable.
- Report changes reset the appropriate reading position.
- Later evidence remains reachable.

### Task 1: Visible resources, human quantities and ruling flavor

Ownership: `organizer/workspace.rs`, `workspace_copy.rs`, `presentation.rs`, `board.rs`, `ui.rs`, the shared `observer_ui.rs` header, relevant `production/readings.rs` money/quantity copy, and a small shared client formatter only if existing helpers cannot serve these consumers. Update the canonical spec with the accepted corrections.

Interfaces: consume admitted `OrganizerClient`, `ObserverSession`, collection and aid/time previews. Produce a private typed resource summary and a shared presentation entry usable by both organizer and World headers. Document exact helper signatures for Task 3 in the task report.

- [ ] Add RED regressions for cash ownership, duplicate household supply, real zero versus unavailable, and historical/context gating.
- [ ] Test exact grouped money, including i128 limits and one-micro amounts.
- [ ] Reuse existing geometry fixtures for a three-resource masthead with long values at supported sizes.
- [ ] Show collective cash, organizer-hours and dated shared/voluntary time prominently throughout the organizer campaign's workspace and World/evidence views.
- [ ] Keep an honest unavailable state for a scenario without a disclosed treasury or time budget.
- [ ] Do not manufacture a personal wallet or future capacity.
- [ ] Share one number-formatting policy.
- [ ] Use `$1,234.56`, `-$1.20` and `$0.000001` as examples of exact human money.
- [ ] Group labor, output, inventory and `request` quantities in the changed Wayne/World readings.
- [ ] Preserve units and keep IDs/dates unchanged.
- [ ] Add one short atmospheric intent sentence to cards, All practices and authenticated review through a shared choice helper.
- [ ] Keep actual cost, displacement, prerequisites and conditional benefit readable.
- [ ] Handle paused Hold and opening inquiries honestly.
- [ ] Leave actual receipt language factual.
- [ ] Run scoped client tests first, then format, applicable Clippy, eight decision-surface contracts and BSL sentinels serially.
- [ ] Reach GREEN and commit.
- [ ] Do not create literal-copy snapshot tests for prose alone.

### Task 2: Continuous Play and honest economy-network access

Ownership: `observer_io/runtime.rs`, `organizer/client.rs`, `observer_controls.rs`, relevant shared Time/menu UI and economy-network unavailable/navigation presentation. Accommodate Task 1's header changes.

Interfaces: preserve `ObserverSession` scheduling/admission and existing OrganizerAction/ObserverCommand handlers. Use the existing observer campaign chooser. No reader, engine, schema or permission expansion.

- [ ] Add RED regressions that drive two successive organizer commit/status/observation cycles.
- [ ] Assert no second advance while status or observation is missing.
- [ ] Assert no duplicate outstanding `request` or resubmission of a consumed one-off commitment.
- [ ] Assert manual Pause during pending status and unchanged one-period Step.
- [ ] Keep playing through a successful organizer commit and its automatic Status refresh.
- [ ] Keep explicit organizer interactions, history, failures, completion and other existing pause conditions.
- [ ] Keep the actual pacing clock and its meaning as delay between ready committed periods.
- [ ] Make Play/Pause/Speed labels and explanatory copy agree with that behavior.
- [ ] Speed changes pace.
- [ ] It does not independently submit or confirm a ruling.
- [ ] Replace the bare unavailable network dead end with readable explanation and an actionable route to existing Observer campaigns.
- [ ] Explain the separate saved world and preserve organizer return/load behavior.
- [ ] Keep all FullObserver and frame freshness gates.
- [ ] Run scoped lifecycle/control/navigation tests RED/GREEN, format, applicable Clippy and BSL.
- [ ] Commit and report exact behavior.

### Task 3: Report answers first and readable World evidence

Ownership: report/evidence presentation and inspector layout/navigation in `organizer/{presentation,workspace_copy,board,ui,evidence}.rs`, World `ui/dossier_compose.rs`, `ui/dossier_card.rs`, and `observer_ui.rs::county_developments`. Reuse Task 1's formatting helpers and preserve Task 2's controls.

Interfaces: exact observation IDs and disclosed report types/dates remain authoritative. Consume current admitted production events and existing economic brief helpers for factual World developments.

- [ ] Add real-font RED tests for initial visibility of the report title and numerical answer.
- [ ] Include long names and enlarged text.
- [ ] Drive report changes and check a fresh reading position, reachable final evidence and reliable Return preserving subject/draft.
- [ ] Put report kind, answer, named source and observed/received dates before notebook/provenance help.
- [ ] Make report choices distinguish a requested delayed inquiry from an automatic current report.
- [ ] Keep explicit dispatch links bound to their exact report ID.
- [ ] Do not silently substitute newer facts.
- [ ] Make the dispatch's actual acquired answer and Read action easy to find.
- [ ] Keep cost, participation, report acquisition and material outcomes separate.
- [ ] Preserve opening/missing/evicted/historical report rules and Archive fallback.
- [ ] Remove Field/Locator, raw grant keys, hashes and publication dumps from ordinary World evidence reading.
- [ ] Keep readable source/date citations and exact citation accessibility in a separate technical evidence control where required by existing contracts.
- [ ] Replace the county's generic committed-record count with bounded factual developments from the admitted frame/production descriptions and quantities.
- [ ] Reuse existing summaries.
- [ ] Do not infer causes from closing stock, merge unlike goods, expose hidden actors or call zero event count no change.
- [ ] Run the connected report/Archive/history/World tests, full scoped client suite, format, applicable Clippy, decision-surface contracts and BSL serially.
- [ ] Reach GREEN and commit.

### Task 4: Native evidence and delivery

Ownership: native/operator evidence, rendered defects, final review, report and PR update. Do not alter the preserved human owner/admission records to make a new source look qualified before this work.

- [ ] Review each implementation task independently for spec and quality, then the full follow-up diff.
- [ ] Resolve material findings without repeating unrelated reviews or already-passed tests.
- [ ] Inspect real native resource/header, ruling, exact report and World evidence frames at the supported normal sizes.
- [ ] Exercise continuous Play across at least two real installed periods, Pause and manual Step in an owned disposable campaign.
- [ ] Check the supported observer network/Flow route separately.
- [ ] Preserve actual limits where data is unavailable.
- [ ] Reuse current native capture/lifecycle infrastructure and existing presets.
- [ ] Do not repeat national performance qualification as a UI witness or invent a resource-enabled scenario.
- [ ] Keep current human campaign/draft and P7 intact.
- [ ] Record the Director's feedback and rendered result in a follow-up evidence report linked from the canonical design.
- [ ] Explain unavailable versus modeled resources.
- [ ] Record the next mechanical gap: reported conditions need consequential organizing choices and visible material and social follow-up.
- [ ] This authorizes no new primitive or AI system.
- [ ] Run required publishing checks once the final source/evidence is ready, through the normal hooked push.
- [ ] Pin PR checks and read-only verification to the exact new head, keep review threads honestly, and update PR #1052.
- [ ] No merge.
- [ ] Prepare the updated playable build with an honest new source/binary admission.
- [ ] Preserve old save/draft evidence.
- [ ] Report code, rendered behavior and outstanding human acceptance distinctly.
