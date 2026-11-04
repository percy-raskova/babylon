# Wayne Map and Relationships Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development with GPT-6.1 Terra `xhigh`. Steps use checkboxes for tracking.

**Goal:** Connect a map-first Wayne organizer scene to evidence, reviewed action, and actual committed consequences.

**Architecture:** Extend the committed organizer projection with the controlled collective's authorized partial body. A shared typed selection drives Places, Relationships, detail, and evidence navigation. Existing organizer, Archive, draft, and advance paths remain authoritative. Historical presentation needs authenticated period-valid data. Otherwise, show it as unavailable.

**Tech Stack:** Rust, pinned Bevy 0.20, Postgres-backed material runtime, county atlas, native UI, and Archive.

**Spec:** `docs/superpowers/specs/2026-11-03-wayne-map-and-relationships-design.md`

## Global constraints

Start only after final exact-head qualification of the finite PER-336 Wayne closeout. It includes the national commit repair and queued Archive controls and citation navigation. Recheck interfaces against that head. Use its final schema fingerprint, not a draft fingerprint.

The Director approved “Approve this design and limited disclosure”. This does not prove native P5/P6 contact lifecycle or PER-355 14-cell acceptance. It does not grant Director enjoyment acceptance.

Disclose only the controlled collective's real `ORGANIZATION_BODY` identity and stable structural key. Include only incidence already disclosed by controlled actor positions in the viewed committed period. The part is partial. Partner membership, ledgers, counts, and private state remain unknown.

Use only disclosed inputs for positions, spacing, counts, labels, geometry, and hit targets. Do not infer a census, draw a clique, or invent workplace coordinates.

Distinguish agreement, routine `CONTACT`, earned contact, cooperation, body incidence, notice, report, receipt, and consumption. Keep unknown, pending, known zero, and known absent distinct.

Keep subject identity, action target, draft, and selection across views and Archive return. Historical views cannot write. Add no mechanics, general graph browser, framework, compatibility path, or agency expansion.

Support 1366×768 and 1920×1080. Distinguish focus, hover, selection, unavailable, and pending without color alone. Follow Rust style and run no documentation-generating gates. Set `BLAS=1` and serialize heavy jobs.

Run all commands from the repository root. Each Cargo command below enters `rust/` in its own shell. Each uses pinned `mise exec` and `BLAS=1`. Reuse qualified unchanged evidence.

Use `mise run commit -- -` for each task. Give it a conventional subject and a body containing `Part of PER-292`. Add the required `Co-authored-by: Name <email>` trailer with the executing agent's actual co-author identity. Stage only the task's files.

## Review focus

1. Hidden source changes leave disclosed labels, counts, geometry, and hit targets byte-for-byte equal (Tasks 1 and 2).
2. Changed campaign, actor, perspective, generation, period, or freshness rejects stale installation (Task 1).
3. Historical views exclude later agreements and evidence and cannot write (Tasks 1 and 3).
4. Unavailable bodies and period-zero reports never imply known empty state or a promised result (Tasks 1 and 2).
5. Evidence and subject navigation keep the draft and captured action target (Task 3).

---

## File map and prerequisite

`rust/crates/babylon-persistence/src/organizer_runtime/snapshot.rs` owns the repeatable-read snapshot and tail check. `DurableMaterialRuntime::organizer_snapshot` is the live projection seam. `self.session().graph_session()` supplies the current graph and sealed resolver. `ReplayTickSession::graph()` exposes topology. `StableElementResolver::hyperedge_key` resolves identity. The live consumer test is `rust/crates/babylon-persistence/tests/observer_material_live/organizer.rs`.

`rust/crates/babylon-persistence/src/organizer_runtime.rs` and `runtime_session/protocol.rs` expose the narrow projection. `SessionBackend::organizer_status` and `DurableBackend` own live delivery. `OrganizerView` in `babylon-practice-contract/src/organizer/types.rs` has positions but no hyperedge identity.

`rust/crates/babylon-client/src/organizer/client.rs`, `ui.rs`, and `presentation.rs` own status admission, drafts, actions, and presentation. `ObserverSession::context()` carries campaign, perspective, viewed tick, and generation. Current organizer status uses the durable tick. Do not treat a live snapshot as historical truth.

Create `rust/crates/babylon-client/src/organizer/scene.rs` for typed selection and the disclosed scene. Wire it through the organizer module and existing UI. Reuse `atlas.rs`, `map::SelectedCounty`, `observer_focus.rs`, and existing Archive handlers. Update affected wire fixtures and consumer tests.

Before Task 1, read the final qualified prerequisite evidence and inspect changed interfaces. Stop product work if the prerequisite lacks qualification. Record its exact failure. Keep the historical and privacy contracts if the physical schema changes.

### Task 1: Authenticated partial body projection

**Files:** Change `rust/crates/babylon-persistence/src/organizer_runtime/snapshot.rs`, `organizer_runtime.rs`, and `runtime_session/protocol.rs`. Change `rust/crates/babylon-persistence/tests/observer_material_live/organizer.rs`. Change `rust/crates/babylon-client/src/organizer/client.rs` and its consumer tests in `organizer.rs`. Update `rust/crates/babylon-persistence/src/runtime_session/money_wire_tests.rs` fixtures.

**Interfaces:** Add `body: OrganizerBodyDisclosure` and `body_scope: OrganizerBodyScope` to `OrganizerSnapshot`. Define `OrganizerBodyDisclosure::{Unavailable, KnownAbsent, Partial(OrganizerBodyPart)}`. `KnownAbsent` needs affirmative evidence in that scope. A missing read means unavailable. Keep loading in the existing `PendingRequest` state.

`OrganizerBodyPart` carries `runtime_hyperedge_id: u64`, `scenario: String`, `local_name: String`, `contributors: Vec<u64>`, and `evidence_class: ArchiveEvidenceClass`. Define `OrganizerBodySource::{Foundation { foundation_digest: [u8; 32] }, Committed { tick_content_hash: [u8; 32], world_hash: [u8; 32] }}`. Use actual source attribution. Refuse disclosure if the source lacks attribution.

The scenario and local name encode `StableElementKey::Hyperedge`. Use that key across restarts. The raw handle applies only to its reconstructed graph view and session. Never compare it as a cross-restart identity. Sort and deduplicate contributor IDs. Intersect actual incidence with positions in the same `OrganizerView`.

`OrganizerBodyScope` carries `campaign_id: [u8; 16]`, `actor_id: u64`, `period: u64`, `content_digest: [u8; 32]`, and `source: Option<OrganizerBodySource>`. `Partial` and `KnownAbsent` need a matching `Some(source)`. `Unavailable` can lack a source. Foundation has an explicit identity, not a fabricated tick hash. Check scope against the snapshot and durable tail.

Bind the result to the captured client `StatusContext`. It contains `ObservationContext { campaign, perspective, tick, generation }`, `durable_tick`, and `RuntimeSessionScope { epoch, campaign_id }`. Check context and freshness before installation. Historical reads need their own authenticated viewed-period scope. The scene consumes admitted disclosure and `OrganizerView`, never the raw graph or register.

- [ ] Add `organizer_body_projection_limits_disclosure` at both persistence consumer boundaries.
- [ ] Assert the actual controlled body ID and key and disclosed pair reach the snapshot.
- [ ] Include a hidden contributor, partner-only body, and private partner data in the source.
- [ ] Change hidden inputs and assert the serialized disclosure stays byte-for-byte equal.
- [ ] Distinguish unavailable, affirmatively known absent, and disclosed partial body.
- [ ] Reopen and check stable key identity even if the runtime handle changes.
- [ ] Add `organizer_body_scope_refuses_stale_and_foreign` at client status installation.
- [ ] Vary campaign, actor, perspective, generation, viewed period, and freshness separately.
- [ ] Assert refusal or supersession before installation and preservation of the prior admitted view.
- [ ] Check historical exclusion of later agreements and grants, write refusal, and unavailable missing projection.
- [ ] Run the focused in-process tests. Expect both new assertions to fail.

```bash
(cd rust && BLAS=1 mise exec -- cargo test -p babylon-persistence organizer_body_projection_limits_disclosure --locked)
(cd rust && BLAS=1 mise exec -- cargo test -p babylon-client organizer_body_scope_refuses_stale_and_foreign --locked)
```

The owned Postgres focus in Task 3 exercises the ignored live test. Do not count that test as an ordinary passing test.

- [ ] Extend the snapshot seam after the tail check with the authorized incidence intersection.
- [ ] Resolve real handles and keys through the existing graph and sealed resolver.
- [ ] Return a specific refusal or unavailable state when same-period authentication fails.
- [ ] Use an authenticated period-bound historical read. Never substitute the latest register.
- [ ] Run the two focused commands again. Expect PASS.
- [ ] Run the wire test and focused organizer status tests affected by the change.

```bash
(cd rust && BLAS=1 mise exec -- cargo test -p babylon-persistence runtime_session::money_wire_tests --locked)
```

- [ ] Commit with subject `feat(organizer): project disclosed collective body` and the global commit-body instruction.

### Task 2: Places and disclosed relationship scene

**Files:** Create `rust/crates/babylon-client/src/organizer/scene.rs`. Change `rust/crates/babylon-client/src/organizer.rs`, `organizer/client.rs`, `organizer/ui.rs`, and `organizer/presentation.rs`. Test the scene and actual UI consumer.

**Interfaces:** Define `OrganizerSubject` variants for collective, contributor, workplace committee, neighborhood group, and workplace. Each carries its existing stable ID. Define `OrganizerSceneMode::{Places, Relationships}`. Derive `OrganizerScene` only from admitted `OrganizerView` and `OrganizerBodyDisclosure`.

Store mode and selected subject in `OrganizerClient`. Selection actions use `OrganizerSubject`, not a label. The scene supplies disclosed nodes, labeled relation kinds, and hit targets to rendering and activation.

- [ ] Add `scene_uses_only_disclosed_inputs` and UI consumer test `scene_selection_and_privacy`.
- [ ] Assert deterministic replay and unchanged scene and hit targets when hidden incidence changes.
- [ ] Check distinct agreement, routine contact, earned contact, and real body-incidence labels.
- [ ] Assert unavailable body state makes no empty-body claim.
- [ ] Check the one-member halo, two-member capsule, and three-or-more-member membrane.
- [ ] Assert each shape represents only the disclosed part and implies no total membership.
- [ ] Assert period zero invents no report or receipt.
- [ ] Run the focused tests. Expect failure before the change.

```bash
(cd rust && BLAS=1 mise exec -- cargo test -p babylon-client scene_ --locked)
```

- [ ] Build shared scene and native controls using the admitted projection.
- [ ] Highlight FIPS `26163` with `CountyAtlas` and `SelectedCounty`.
- [ ] Add a county-level subject dock without invented points.
- [ ] Lay out only disclosed identities and permitted relation endpoints in deterministic order.
- [ ] Keep collective and contributor distinct. Use shape and text as well as color for interaction states.
- [ ] Keep focus and hover from changing selection.
- [ ] Run the focused tests again. Expect PASS.
- [ ] Exercise keyboard activation and county synchronization at the actual Bevy consumer boundary.
- [ ] Commit with subject `feat(organizer): add places and relationships scene` and the global commit-body instruction.

### Task 3: Evidence, action, and qualified native path

**Files:** Change `rust/crates/babylon-client/src/organizer/ui.rs`, `organizer/client.rs`, and `organizer/presentation.rs`. Change `organizer/qualification_input.rs` and `tools/devtools/national_windowed_qualification.py` only when native controls need them. Extend existing consumer tests and national qualification evidence. Add no scheduler or runner.

**Interfaces:** Reuse `OrganizerAction::{Review, Confirm, Advance, ArchiveWorkplace, ArchiveOrganization}`. Reuse draft and review state, `OrganizerArchiveRequested`, and `ObserverCommand::Step`. Selection identifies the inspected subject. It cannot change the command's captured `workplace_id` or `workplace_partner_id`. Existing review invalidation applies when observation context changes.

- [ ] Add `scene_navigation_preserves_draft_and_action_target` to native UI consumer tests.
- [ ] Select the committee, switch modes, navigate cited evidence, return, and select the neighborhood group.
- [ ] Assert identity, selection, draft, and captured workplace and committee target remain correct.
- [ ] Assert hover changes neither selection nor command.
- [ ] Assert review and navigation send no submit or advance.
- [ ] Check historical write refusal, unavailable evidence, and absence of period-zero report promises.
- [ ] Run the focused test. Expect failure before the change.

```bash
(cd rust && BLAS=1 mise exec -- cargo test -p babylon-client scene_navigation_preserves_draft_and_action_target --locked)
```

- [ ] Connect scene selection to existing detail, evidence, and review handlers.
- [ ] Show actual 2-hour practice and 2-hour cycle capacity and applicable displaced standing work.
- [ ] Show independent partner response and actual report timing. Distinguish promised from performed time.
- [ ] Open cited Archive evidence within its scope. Return to the same identity and valid draft.
- [ ] Show City PD only after the earned encounter and permitted citation.
- [ ] Add no consumption receipt. Infer no encounter from notice or routine contact.
- [ ] Run the focused test again. Expect PASS.
- [ ] Run format, scoped clippy, and BSL sentinels serially. Expect PASS.

```bash
(cd rust && BLAS=1 mise exec -- cargo fmt --all -- --check)
(cd rust && BLAS=1 mise exec -- cargo clippy -p babylon-client -p babylon-persistence --all-targets --locked -- -D warnings -D clippy::cognitive_complexity)
BLAS=1 mise run check:bsl-sentinels
```

- [ ] Run changed consumer tests and applicable Rust contracts identified from the final diff.
- [ ] Reuse qualified unchanged evidence. Do not default to whole-crate suites.
- [ ] Run the owned, disposable Postgres organizer consumer check serially. Expect PASS.

```bash
BLAS=1 BABYLON_POSTGRES_LIVE_FOCUS=organizer mise run test:rust-postgres
```

- [ ] Make sure the selected test exercises authenticated projection and restart.
- [ ] Extend that focus with the new consumer test if needed.
- [ ] Reuse the final qualified PER-336 native handoff and its reviewed controls.
- [ ] Inspect its exact campaign, schema, source, build, ownership, lock, and admission receipts.
- [ ] Resume only if current code, binaries, schema, and handoff pass those controls.
- [ ] Use the existing guarded fresh-campaign path when physical or schema admission needs fresh data.
- [ ] Use its reviewed capture parameters. Do not migrate or bypass admission.
- [ ] Avoid repeating unrelated national benchmarks. Keep campaign and evidence under existing ownership controls.
- [ ] Exercise Places, committee selection, evidence, return, review, confirm, and separate advance.
- [ ] Inspect the durable receipt and restricted evidence, then restart.
- [ ] Inspect the actual result, including a lawful refusal or unavailable evidence.
- [ ] Inspect both resolutions, keyboard focus, long names, selected state, and pending advance responsiveness.
- [ ] Record exact head, commands, campaign, observations, resource and persistence effects, and artifacts.
- [ ] Compare measured effects with the current North Star budget. Mark insufficient samples unqualified.
- [ ] Add only a bounded control if an existing control cannot drive a step.
- [ ] Rerun its affected qualification. Report native failure or unavailability without claiming acceptance.
- [ ] Commit with subject `feat(organizer): connect map selection to decisions` and the global commit-body instruction.
- [ ] Report actual native evidence separately from Director enjoyment, full national, and gate acceptance.
