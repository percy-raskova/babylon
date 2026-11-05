# Wayne game workspace implementation plan

> Use Superpowers Subagent-Driven Development. The Director approved the complete design in chat on 2026-11-05 and delegated visual craft.

**Goal.** Build native Wayne as an industrial political strategy game through surveying the map, committing work, and receiving a period dispatch.

**Spec.** `docs/superpowers/specs/2026-11-03-wayne-map-and-relationships-design.md`, extended with the Director's November 5 workspace redesign. The accepted old frames in the October 29 delivery audit are comparison evidence.

**Architecture.** Native Bevy 0.20, existing atlas/camera, embedded art/fonts/audio and authenticated organizer runtime. UI projections consume existing admitted views, previews, receipts and disclosed encounters. The current game mechanics own all effects. The geographic background fills the organizer screen and overlay geometry excludes map input.

## Global constraints

- Work on the task branch from current `dev` in the existing media-drive linked worktree.
- Preserve unrelated work, the retained P7 campaign and its personal draft.
- Use `mise run commit -- "type(scope): description"`, and Part of PER-331, PER-292 and PER-302 where applicable.
- Prepare a PR against `dev`. This plan grants no merge permission.
- Use one implementation worker at a time in this worktree. Read-only investigation and review can run independently.
- Run heavy Cargo/runtime jobs serially with the existing host policy. Keep BLAS=1.
- Preserve stable subjects, captured targets, drafts, visibility, historical read restrictions, independent partner responses, explicit Review/Confirm/Advance and errors.
- Never infer graph facts from art or membership counts from portraits.
- Draw only disclosed relations. Distinguish typed agreement, routine, earned contact and incidence, with dates and source.
- Treat missing evidence as unknown. P0 has no completed-period report. Actual campaign hours and material terms own costs.
- Qualify native 1366x768@1, 1920x1080@1 and @1.25 and existing larger-scale settings.
- Use readable embedded fonts, one detail region that scrolls, visible core decisions and access to every existing practice.
- Generate no documentation. Run scoped Rust tests, format, clippy, decision-surface and BSL gates, then required publishing checks.
- Do not add baselines to hide faults.

## Review focus

Input protection must agree with organizer camera/render geometry. Comparison must not silently change the draft. Current dispatch requires exact period equality. Old PD reports must remain dated history. Historical and pending views must not write or substitute current information.

### Task 1: Decision and period presentation contracts

Ownership: organizer presentation and its consumer-independent tests, plus the canonical Wayne design update. Do not change organizer UI/layout or shared shell yet.

Update canonical design with the full map, compact top controls, illustrated identity and selected group dossier.
Include a bottom two-choice deck, one inspector and a dispatch that leaves the workspace usable.
Cite approved existing artwork and the narrow `V3`/`Stellaris` lessons. Old design examples set no universal hours.

Define private typed choice-comparison projections in presentation, using a new sibling module if needed.
Consume `OrganizerClient`/`OrganizerView` and current choice. Name the captured target and partner, actual hours, displaced routine, possible benefit, resolving period and availability.
Expose common display terms to the UI without parsing formatted strings. Keep all practices reachable.

For a Hold draft, compare Reinforce against Hold when available, without selecting Reinforce. An existing non-Hold draft compares itself against Hold.

Define period-dispatch projections for actor-authorized receipts from the exact viewed period.
Include newly acquired reports with separate observed/acquired dates, and disclosed PD encounters. Keep older rows in dated history.

Direct a missing current receipt window to Archive. Never invent a quiet result.
Links use stable `OrganizerSubject` or existing typed inspector/Archive destinations, without string matching. Navigation preserves viewed context and draft.

Add meaningful regression tests, show RED, reach GREEN and run scoped presentation/client tests.
Cover paused routines, actual differing scenario costs, P0 absence, refusal, pending aid and results from the same period only.
Cover previous PD rows and hidden/history restrictions. Report exact interfaces for Task 3.
Commit the task and write the SDD report with test evidence.

### Task 2: Three group illustrations and integration

Ownership: three new artwork assets and embedded visual asset catalog/loading/manifest/provenance only. Use the `imagegen` skill and built-in image generation tool.

Generate original, mutually recognizable illustrations for the organizing collective, workplace committee and neighborhood contact group.
Use existing industrial ink/paper/rust/bone/brass art as style reference. Personify each group without baked text, faction seals, fictional named people or asserted member counts.
Make final images compact and suitable for cropped small landscape portraits in the screen.

Save final outputs in `assets/visual`. Extend existing typed asset identities and loading/catalog records.
Keep exact prompts and provenance in the existing art records. Do not introduce a parallel asset system.
Inspect images and check catalog/embedded loading consumers. Commit and report final paths and typed accessors to Task 3.

### Task 3: Native game composition and connected flow

Ownership: organizer UI/scene and its real consumer/layout tests, shared organizer-only viewport/camera fitting/input exclusion, theme/font/asset/audio reuse as needed. Use Task 1 types and Task 2 assets.

Use a full geographic background and Wayne focus. Add a compact top strip for the collective, period, actual means, standing work and advance.
Preserve ordinary map/production/Archive destinations. Remove competing old organizer chrome.

Places and Relationships share stable selected subjects. Relationships uses deterministic disclosed endpoints, typed bands/glyphs, genuine partial body incidence and reusable group portraits.
Keep illustration distinct from geographic and relation evidence.

Add the right selected-subject dossier and bottom comparison deck. Keep two meaningful alternatives and concise essential terms visible together at supported normal sizes.
All practices opens a single accessible list. Never lose collection, aid, inquiry or standing controls.
Larger text and long names use stacked rows and a single reading region.
Evidence, notes, history and review route through existing focused inspectors.

Authenticated review has full actual terms and visible confirmation controls. Keep Review, Confirm and Advance distinct.
Keep disabled, pending, refused, failed, historical and completed states honest and usable. Selected navigation cannot change a captured command target.

The exact-period dispatch features actual partner/earned outcome, reports and public encounter citations.
Open known subjects and evidence in the same period, with return. Keep old PD notices in history and quiet turns compact.
Reuse existing audio feedback and selection/commit transitions. Respect reduced motion and settings.

Change organizer camera render rectangles and UI exclusion/hit bounds together. Block map clicks, drags and wheel input beneath overlays, inspector and dispatch.
Use one atlas/camera with organizer-specific geometry. Preserve other primary views.

Show RED/GREEN for meaningful native input/consumer regressions. Use real-font clipped-intersection layout assertions from actual projected text.
Check supported sizes/scales, both modes, different costs, long names, pending/historical/unknown states and access to all practices. Commit and report.

### Task 4: Native qualification and delivery

Ownership: scoped fixes found by qualification, report/screenshots, final evidence and publishing.

Review each preceding task independently for spec and code quality. The final whole-branch review is separate. Resolve material findings.

Inspect the map, selected comparison/review and actual committed dispatch at supported sizes. Use existing qualification/capture infrastructure. Preserve P7.

Use an owned disposable campaign for two decisions, durable advances, evidence return and cold restart.
Record actual outcomes and delay, without scripting success. Inspect mouse/keyboard routes where tooling supports them. Distinguish injected, native and human evidence.

Run scoped `babylon-client` tests first. Run the decision-surface contract and format/clippy/BSL separately.
Run required publishing gates without documentation, serially. Broaden only for changed contracts or failures.

Compare the accepted baseline against native new captures. Record actual resource/pacing observations without claiming sustained national qualification.
Offer a ready visible build for a short human play session. Keep enjoyment/comprehension pending until a human plays.

Commit qualified source/evidence. Prepare a reviewable PR against `dev` with Part of PER-292/PER-331/PER-302 as applicable.
Check exact head checks. Do not merge. Keep valuable source/art/evidence.
Clean only exact task-owned disposable runtime fixtures.
