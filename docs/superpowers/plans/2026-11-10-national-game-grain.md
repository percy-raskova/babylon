# National game grain implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` task by task. Track steps
  with Markdown checkboxes.

**Goal:** Reduce the national economy before expansion and complete Wayne's report-to-funded-commitment loop.

**Architecture:** Assign captured county/source contributions to Designed representatives before constructing economic
sites, accounts and relationships. Preserve additive source quantities and explicit ownership of money and time. Use the
ordinary compiler, detached material tick, authenticated persistence and actor disclosures. This game resolution does
not reproduce the old fine trajectories exactly.

**Tech Stack:** Locked Rust workspace, `babylon-persistence/material-circuit/tick/client`, Bevy 0.20, captured national
TOML and typed canonical encoding.

**Spec:** `docs/superpowers/specs/2026-11-03-wayne-map-and-relationships-design.md`, “National game grain”.
`ai/decisions/ADR296_national_game_grain.yaml` records the decision.
`.superpowers/sdd/2026-11-09-native-qualification-split/task-4-bounded-delivery-goal.md` carries the same combined goal.
Both national reduction and Wayne play must pass before completing the goal. The retained 10 November candidate design
and baseline supply evidence, without separate live authority.

## Director amendment: 11 November 2026

The ordinary national warm-turn limit is now thirty seconds, replacing the earlier ten-second limit.
Keep the complete endpoint: Advance input through a useful dated report or pending brief, rendered evidence and usable next controls.
Each of the first three samples at 1366×768 Standard must meet thirty seconds. Three samples do not prove p95.

Keep earlier measurements and their source/workload boundaries unchanged. This decision changes acceptance, without claiming a speed improvement.
Every other performance, memory, storage, correctness limit and period horizon stays the same.
After the final source meets the agreed limits, continue game play qualification. Defer optional performance work.
The proposed statistics experiment on three system catalogs remains deferred without execution.

## Global Constraints

- Include all 3,144 captured county contributions exactly once.
- Keep twelve foreign groups, six separate dependencies, international gateways and finite shared freight.
- Keep all Wayne `26163` and Cook `17031` opening principals detailed.
- Assign sources and prepare aid before folding. Never construct a fine `EconomicOpening` first.
- Background principals are new Designed representatives.

Preserve distinct positions, budgets, source ownership, protected needs, receiving/reporting/participation consent and
current class margins. Do not claim old/new transition or hash equivalence.

Use checked integers and per-source floors before sums. Preserve unknown versus zero, eight source classes, exact
currency micros and independent stock/time owners. Keep canonical order, atomic publication and restart admission.

Author national numbers in `content/scenarios/national/defines.toml`. Treasury starts at $1. The contribution target
spans $1–$1,450 and starts at $280. Food spans 0–4 units and starts at 1. Cash spans $0–$1,450 and starts at 0.

Refuse zero food with zero cash. Keep 2-hour collection, 2-hour food fulfillment and coordination costs.

Captured county transport and original hub/regional/trunk/gateway pools govern membership. Apply the settled
deterministic capacity subdivision before fixing the candidate. Add no capacity multiplier, fictitious geography or
primitive.

Allow one initial measured candidate and ONE corrective iteration after a measured acceptance failure. Allow at most one
targeted diagnostic per demonstrated blocker. Do not repeat unchanged full runs or the completed sole baseline profile.

The Director approved one further repair pass on 10 November. Tasks 5 and 6 carry that extension. Repair the known
qualification blockers, then make one measured retry. Keep the economic candidate and qualification limits fixed.
The only guard change permitted here synchronizes SQL and Python with the existing native receipt format.

Ordinary P1–P3 Advance must each reach a dated actionable or legitimate pending brief, with usable next controls, within
30 seconds. Measure at 1366×768 Standard. Three samples do not prove p95. Measure startup and recovery separately.

Both normal AND full-memory national smoke/walk members remain required. Complete the ten-period decision loop,
restart/lifecycle checks, native input/frame checks and human acceptance. Limits remain: cold <180s, advance ≤120s,
Archive/read ≤180s and normal two-period smoke ≤900s. Total memory must stay ≤10,000,000,000B. Sample gaps must stay
≤5s. Keep existing storage/custody limits.

Use `/media/user/data/worktrees/per364-wayne-solidarity-loop/babylon`. Do not edit protected 0c51, add
compatibility/migrations, delete broadly, add unrelated feature/AI work, merge or close umbrella scope. Run heavy checks
serially with BLAS=1, pinned tools and installed v13 worktree controls. Generate no documentation.

## Review Focus

- Keep pre-existing county scarcity explicit. Distinguish it from consolidation-induced shortage with Task 1's
  finite-lane fixture.
- Test same-hub reserve positions through real compile/tick. Keep their household cash, pantry and public budgets
  independent.
- Preserve protected child/parent, payee, membership and receiving identities exactly once.
- Keep aid settlement at most once and later purchasing at P+2. Run existing aid/restart regressions.
- Keep hub outcomes distinct from observed county outcomes. Protect undisclosed principals in Tasks 1/2.
- Measure the usable visible brief and controls in Tasks 3/4. An internal receipt alone cannot prove readiness.

---

### Task 1: Build and execute the real coarse national opening

**Ownership:** One fresh implementer owns related source writes and scoped checks. Other agents can inspect read-only.
No parallel writers or subagent dispatch.

**Files:**

- Create `rust/crates/babylon-persistence/src/national_economy/grain.rs`.
- Add tests beneath `national_economy/grain/` only when cohesion warrants separation.
- Change `national_economy.rs`, `national_economy/identity.rs`, `policy/{game,admission}.rs` and
  `opening/{build,actors,financial,household_time,markets,equipment,routes,detail}.rs`.
- Change `content/scenarios/national/defines.toml`.
- Expose only necessary helpers in `national_resident_allocation/{allocation,households}.rs`. Preserve source allocation
  and validation.
- Wire capture/witness through `economic_catalog/{national,model,compile}.rs` and affected current-source
  encoding/consumers. Add no compatibility branch.
- Update coupled opening/runtime/replay/knowledge tests. Change canonical expected values only through the required
  ceremony.

Do not change qualification operators or run a campaign.

**Interfaces:** Consume `allocate_home_county` output, household/time controls, exact `aid::prepare` remapping, admitted
counties/transport and captured `NationalGamePolicy`.

Produce `NationalGrainPolicy`, `CapturedNationalMembership`, `NationalGenerationWitness`, `NationalOpeningRoster` and
representative identity/domain keys. Expose one current `coarsen_source_allocation(...) -> Result<NationalOpeningRoster,
NationalGrainError>` operation.

`capture_membership(counties, transport, source_allocation, households, aid, policy) ->
Result<CapturedNationalMembership, NationalGrainError>` owns deterministic partition/refinement. Reuse strong
identifiers and allocation types. These authoring types add no mathematical primitive.

Builder consumes `NationalOpeningRoster` to construct the ordinary compiler's `EconomicOpening`, without first
constructing fine background principals. The roster supplies workplaces/members, explicit households/time eligibility,
per-source endowment sums, financial-domain joins and witness. Capture and authenticate the witness once. Reproduce it
on restart without copying incidence into every state/receipt.

- [ ] **Step 1:** Read the canonical requirements and current consumers.

Read the specification, ADR296, Constitution II/VI, Rust style and gotchas. Record the exact task base and settled
deterministic refinement. Stop only for an architectural contradiction that the implementer/controller cannot resolve.
The implementer/controller owns ordinary technical choices.

- [ ] **Step 2:** Run focused failing fixtures and record actual RED.

Cover complete membership and insertion-order identity. Cover unique subdivisions, the two-county 28-billion-gram versus
20-billion-gram counterexample and a pre-existing oversized singleton. Cover same-hub reserve/budget distinctions,
nondivisible per-source production floors and exact protected child/parent joins.

- [ ] **Step 3:** Build typed captured policy and one membership/refinement operation.

Derive reserve positions after subdivision. Refuse malformed/incomplete transport joins, overflow, protected overlap and
unsupported generation with specific errors. Record the finite screening witness, deterministic membership digest and
source totals. Run no new baseline profile.

- [ ] **Step 4:** Fold sources after `aid::prepare`, before `actors::domestic`.

Fold one temporary productive source seed at a time. Never hold a vector of fine sites. Remap counted household/member
identities. Sum same-unit endowments, household/person/class/eligibility/time quantities while preserving source floors.
Pass exact Wayne/Cook rows through.

- [ ] **Step 5:** Connect the roster to actors, finance, equipment, markets and routes.

Preserve source ownership for Designed sites. Join public/owner budgets by domain identity, not hub location. Use
explicit household eligibility overrides rather than hub population. Preserve finite stock, merchant labor and shared
transport authority. Remove obsolete generation and misleading late classification-as-consolidation claims.

- [ ] **Step 6:** Complete admission, capture, regeneration and ordinary consumers.

Add real compile/tick tests for independent balances/pantries, staffing-payee/time joins, transport contention, island
refusal and source conservation. Check protected opening identities/endowments exactly. Allow changed national trading
trajectories. Run existing funded contribution/food/cash/partner/refusal/timing/replay/atomic-failure tests serially.

- [ ] **Step 7:** Run GREEN and the applicable scoped gates serially.

Start with the smallest tests from `rust/`, using locked Cargo and current worktree controls. Follow with scoped
conformance/replay. Run `cargo fmt --all -- --check`, scoped strict Clippy and BSL sentinel separately. Generate no
docs. Record commands, exit statuses, counts, skipped cases and unresolved risks. Unit tests cannot prove
native/performance acceptance.

- [ ] **Step 8:** Review the complete path, commit and report.

Use `mise run commit -- "feat(economy): generate national game-grain principals"` with required `Part of PER-364` and
coauthor conventions. Root dispatches independent review. The worker does not dispatch a reviewer.

### Task 2: Keep organizer questions scoped and county evidence truthful

**Files:** Keep ordinary organizer runtime/session routes, `organizer_runtime/{snapshot,material_preview}.rs`,
`observer_material/snapshot.rs` and `production_projection/projection.rs` unchanged after the read audit. Change World
scope text in `babylon-client/src/map_economy_lens.rs` and `observer_ui.rs`, plus production inspection in
`production/readings.rs` and coupled tests. Add the remote representative regression to
`babylon-persistence/tests/national_partner_reports.rs`. County source and Archive labels already keep observed values
separate. Add no generic projection framework.

**Interfaces:** Consume Task 1 identities/witness and authenticated organizer disclosure. Keep the current typed
snapshot/preview. The read audit confirms that ordinary `KnownPreview` and material previews avoid a full national
`ProductionSnapshot`. Keep that route and full observer inspection.

Explain regional accounts in World and inspection readings. Keep county observations separate. Never accept wider client
scope or claim a scoped hash covers the nation.

- [ ] **Step 1:** Trace Advance through authenticated read to the dated brief.

Use the existing audit. Separate required full decode/hash work from avoidable national DTO allocation.

- [ ] **Step 2:** Run only missing failing knowledge/provenance tests.

Test unchanged local disclosure after undisclosed remote mutation. Distinguish hub results from observed county values
and actual dates from pending dates. If the path already satisfies the boundary, record evidence and omit speculative
changes.

- [ ] **Step 3:** Make the smallest repair and run scoped checks.

Run GREEN, format, Clippy and contracts serially. Commit through the governed runner. Independent review must confirm
full national inspection and evidence/hash authority.

### Task 3: Measure the one candidate and admit the next native run

**Files:** Change qualification operators/tests only for current identity or required measurements. Use task-private
bounded operators and evidence. Root owns the sole heavy/runtime slot and final release grant. Do not reuse stale
namespace, source or binary pins.

**Interfaces:** Consume the reviewed Task 1/2 head, captured source/input digests, normal final binary manifest and
retained baseline. Produce authenticated candidate counts, P0/P1/P2 states/receipts, normal warm observations and
separate memory evidence.

- [ ] **Step 1:** Reuse the completed sole baseline and recorded decisions.

Baseline head: `52e789859bcc55f8109c3c88a547acf0746cd3f5`. Input:
`f74b00861c74b2a92cadbcf0925c4e5b88accf72c0274c7c78957a2921cbddd5`. Keep qualification14 headers. Do not rerun the
baseline: 60,634 sites, 15,696 households, 100,302 terms and 2,169,757 relation-row occurrences.

- [ ] **Step 2:** Build ordinary binaries and prepare a fresh disposable national fixture.

Use installed exclusive controls. Independently check source, inputs and final bytes. Keep prior failed fixtures, unique
evidence and source. Add no legacy save conversion or failed-state backup program.

- [ ] **Step 3:** Measure the opening and first two closes at comparable boundaries.

The candidate must reduce live actors/sites, economic relations, P0/P1/P2 canonical states and P1/P2 receipts. Report
packed bytes and RSS separately. Retained baseline bytes follow.

| Boundary | State | Receipts | Packed pair |
| --- | ---: | ---: | ---: |
| P0 | 187,831,389 | — | — |
| P1 | 218,047,972 | 386,683,376 | 30,578,680 |
| P2 | 231,323,308 | 341,793,923 | 31,990,935 |

- [ ] **Step 4:** Measure ordinary native P1–P3 at 1366×768 Standard.

Measure input to useful dated/pending brief with usable next controls. Each must take ≤30s. Report all three without
claiming p95. Internal ticks and typed drivers cannot prove visible readiness.

Use a separate ordinary companion through the existing installed callback. Close three periods without interruption,
using the first three `WALK_FIXED_DECISIONS`. Then accept P4 Pause without closing P4. Remove all four qualification
audit variables from companion environment copies. Keep the qualified normal and full-memory smoke and ten-period
walk members unchanged.

For each close, capture the first strict ready status, exact rendered frame and next accepted original. Report the
intervals from input to ready status and from input to capture. Use the later completion of capture or next acceptance
for the usable endpoint, including all overhead. Keep raw pixels and incomplete evidence.

This prefix does not prove a full ten-period walk, recovery, storage or qualification. Use `qualification-26` as the
fresh disposable namespace. Keep `qualification-15` and its artifacts.

Invoke `tools/run_rust_postgres.sh --wayne-ordinary-prefix` for the separate normal-only `ordinary-01` profile.
Its independent evidence path is `qualification-26/ordinary-01/normal_play/evidence`. The source horizon stays at ten
periods. Existing source, capacity, binary, ownership and role checks apply.

After the prefix, stop and keep the exact container, primary data and evidence. Record late or incomplete measurements
without claiming qualification or backup. Release only the matching lease after checked shutdown. A refused stop keeps
the lease. The stopped campaign keeps its connection flag closed.

This uses the existing disposable campaign fence, not continuous exclusion of all SQL clients.

The next try uses the single corrective iteration. The checker accepts default report selection with a closed inspector.
An open inspector still causes refusal. If the measured conditions still fail, report evidence and options without
another candidate.

- [ ] **Step 5:** Apply the measured-failure bound.

Allow at most one targeted diagnostic per demonstrated blocker and ONE corrective iteration. Separate pre-measurement
review/unit repairs from changes to the measured candidate. If both candidates miss, return evidence/options and leave
the active goal incomplete. Do not expand scope or raise limits.

### Task 4: Complete the funded loop and reviewable delivery

**Files:** Use existing qualification members, native comparison evidence, canonical Wayne design, exact-head
publishing/PR records and authorized narrow Linear updates. Keep old ADRs/reports unchanged. Claim no broader milestone
completion.

**Interfaces:** Consume Task 3's structural/performance result and playable build. Produce normal/full-memory smoke AND
ten-period walk evidence, native frame/input evidence and a session without coaching. Deliver an exact-head green
follow-up PR targeting `dev`.

- [ ] **Step 1:** Exercise the national ten-period funded loop.

Follow collect → local food-only → remote mixed → explicitly manage routine during arrival → cash-only → later ordinary
purchasing. Use actual finite route timing. Check reports/permissions, exact settlements and one response through
restart. Separate normal timing from required full-memory members without weakening either.

- [ ] **Step 2:** Inspect original native frames and physical input.

Inspect 1366×768 and 1920×1080 Standard/Larger frames. Check pointer/keyboard amount entry,
comparison/review/confirm/advance, cited report/Archive return and overlay exclusion. Typed drivers do not prove
physical input. Record remaining human checks honestly.

- [ ] **Step 3:** Prepare the authorized fresh play session without coaching after automated readiness.

The player must explain cost/timing and actual/pending response, then choose a follow-up without coaching.

Record comprehension, hesitation, follow-up choice and willingness to continue. Fix blocking failures within the
correction bound and secure Director acceptance. Do not coach initial decisions.

- [ ] **Step 4:** Complete publishing checks and independent review.

Run scoped regressions first, then applicable Python, Rust format/Clippy/conformance/replay/contracts/BSL and hosted
exact-head CI. Run serially without documentation generation or baseline relaxation. Secure broad independent branch
review and resolve load-bearing findings.

- [ ] **Step 5:** Publish the reviewable follow-up PR, playable build and comparison evidence.

Target `dev`. Update authorized Linear issues with verified delivery and remaining acceptance. Preserve PR1052 and
broader issue scope. Do not merge or close umbrella scope.


### Task 5: Synchronize receipt guards and current dossier tests

**Ownership:** One fresh implementer owns source edits and scoped checks in the existing task worktree. Window tracing
can run read-only. Keep heavy checks serial and return ownership before native work.

**Files:** `rust/crates/babylon-persistence/migrations/current_schema.sql`,
`tools/devtools/national_storage_qualification.py`, their directly affected boundary tests, and
`rust/crates/babylon-client/tests/dossier_card.rs`. Include this approved plan extension in the source commit.

**Interfaces:** The existing v20 native format allows seven aid receipts per material-row allowance. Preserve its
65,536-row allowance, 387-byte aid row and all mechanics. Synchronize canonical admission from 874,709,881 to
925,434,745 bytes, and stored admission from 874,712,176 to 925,437,040 bytes. This raises old SQL/Python guards by
50,724,864 bytes. It changes no Designed qualification-policy ceiling.

- [ ] **Step 1:** Use the saved full-gate failures as RED for unchanged source.

Add a focused Python admission boundary regression before changing its guard. Keep exact acceptance and rejection boundaries.

- [ ] **Step 2:** Update every directly coupled SQL/Python consumer.

Keep independent complete-family arithmetic, collection's one-row increment, framing, format refusal and checked overflow.
Add no native row allowance or format.

- [ ] **Step 3:** Correct the dossier integration flows.

Assert readable evidence first, then use the real Technical evidence control for exact Source/Locator/Field.
Identify the footer through its unique history control and current displayed caption. Keep all geometry, history, pending-state, citation and
reading-region assertions. Change no production presentation for these tests.

- [ ] **Step 4:** Run focused GREEN, applicable lint/type/format checks and normal commit hooks.

Report exact commands, results and remaining concerns. Do not rerun the full workspace or launch a game in this task.

Keep `contracts/national_storage_qualification_v6.json`, game costs and money/time resources unchanged. Do not
change native format bounds, weaken equality checks, add compatibility or bless a baseline. The source diagnosis files
in the current SDD workspace explain the inherited mismatches.

### Task 6: Repair window acknowledgement and exercise the approved retry

**Ownership:** A separate implementer owns window/render/control work after Task 5 returns source ownership. Root owns
all real runtime work and the serial build slot.

- [ ] **Step 1:** Trace the window size change from application to OS observation and render acknowledgement.

If the saved evidence cannot identify the actual missing condition, gather one startup-to-resize diagnostic through the
existing admitted launcher and control path. Submit no game commitment or Advance. Keep the observations and exact fixture.

- [ ] **Step 2:** Repair the demonstrated cause.

Preserve real physical dimensions, window identity, source context and capture verification at 1366×768 and 1920×1080.
Keep presentation and game time limits unchanged. Add no launcher.

- [ ] **Step 3:** Complete focused RED/GREEN and independent reviews, then freeze the repaired source and normal build.

Use a fresh disposable namespace and preserve earlier fixtures, binaries and evidence.

- [ ] **Step 4:** Make one measured retry of the ordinary three-close path.

Report all endpoints and raw frames. If it passes, continue the original required normal/full-memory smoke, full funded
walk, input, human and publishing checks at that frozen candidate. If it misses, return evidence/options before another candidate.

This extension permits the three known repair areas only. Nationwide coverage, foreign trade, existing economic
mechanics and the original completion conditions remain required. The Director has not authorized a merge or umbrella closure.


### Task 7: Complete the receipt guard's trusted schema consumers

This task completes the approved receipt-limit synchronization after namespace19 refused schema initialization.
It precedes the remaining Task 6 window observation. It introduces no economic candidate or qualification exception.

**Ownership:** One fresh implementer owns source and focused checks. Root owns every real database operation.
Run heavy work serially. Preserve earlier fixtures and all original evidence.

**Files:** The four current schema census fixtures, the existing schema provenance tests, and the native runner's
bootstrap failure evidence with its directly affected Python tests. Roll current disposable references to qualification20.
Include this plan clarification in the commit.
Do not change schema authentication, numeric limits, roles, grants, game rules or supported formats.

- [ ] **Step 1:** Run the existing current census provenance test as RED before changing any fixture.

- [ ] **Step 2:** Reuse the preserved four-role catalog capture process against the exact current SQL and pinned image.

Root creates one fresh isolated schema-only database. Capture actual catalog rows for every role configuration.
Compare every row with its corresponding trusted fixture. Allow only the receipt table's changed constraint signature.

The existing test enforces four SQL headers. Refresh existing provenance headers from the exact captured source bytes,
including the informational Rust headers. Keep the header roster fixed.

Refuse other catalog drift. Keep raw rows, actual source hashes and capture evidence.
Do not guess or edit a digest without that evidence.

- [ ] **Step 3:** Install only the authenticated captured fixture changes and preserve detailed bootstrap failures.

Use the existing private evidence mechanism for bounded command status and output before a generic initialization
refusal. Preserve the original failure if evidence publication also fails. Expose no credentials in public output.
Add no general tracing framework or launcher.

The governed baseline estate is `tests/baselines/`. These schema contracts lie outside that estate. Record the real
capture and normal ceremony check. Do not invent a generated baseline blessing or unrelated baseline change.

- [ ] **Step 4:** Run focused GREEN, strict source checks and an independent task review.

Root then runs the existing live reference-integrity checks. Check fresh and repeated installs, all four role
configurations and unchanged drift refusals. Only then resume the still-unperformed window observation in Task 6.
The original measured retry and all completion conditions remain unchanged.


### 11 November extension: one measured ordinary Advance repair

The Director approved one instrumented three-turn diagnostic, one checkpoint/publication repair supported by its
measurements, and one acceptance retry. This extension takes precedence over earlier limits for this pass.
Stop and report if the cause remains unclear or the retry fails. If the retry passes, continue the original qualification.
Keep every numerical limit, economic candidate, schema check, durability guarantee and proof checks unchanged.

### Task 9: Instrument ordinary Advance and run the single diagnostic

**Ownership:** One implementer owns instrumentation, the current namespace and scoped checks. Root owns independent
review, the normal build, release custody and the one real diagnostic. Source completion means a clean reviewed commit.
It does not mean the diagnostic ran or native acceptance passed.

- [ ] Extend existing opt-in `BABYLON_TIMINGS` records with fixed private nested phase observations.

Measure full checkpoint capture, report and envelope preparation, the second checkpoint source and row composition,
and material register/receipt encoding. Split schema settings/owner/sentinels, the complete census SQL query and received rows,
local decode, fixture matching and source identity checks.

Measure typed/checkpoint writes, material writes,
organizer/catalog/marker publication and actual COMMIT acknowledgement. Include campaign and period identity.
Keep clocks out of canonical bytes and errors. Preserve all work and its ordering, fresh complete per-write schema
admission, marker-last writes and authenticated ambiguous-commit reconciliation. Add no optimization or SQL change.

- [ ] Move current storage and public ordinary references from qualification18 to fresh qualification21.

Refuse retained qualification17/18/19/20 and reserved qualification22 through the existing admission contracts.
Preserve those earlier runs, binaries and evidence. Use the existing normal ten-horizon `--wayne-ordinary-prefix`
entry. Change no launcher, workload, endpoint, clock, capture, authentication or presentation guard.

- [ ] Complete meaningful namespace RED/GREEN, scoped persistence contracts, strict source checks and review.

Run heavy work serially through installed v13 Main controls. Generate no documentation. Do not run full Python or
workspace Rust gates here. Both passed at the accepted base, and final gates follow the measured repair.

- [ ] Root builds and releases the reviewed source, then runs qualification21 once.

Keep normal four confirmations and three closes: P1 Collect1450, P2 local food1/cash0 and P3 remote food2/cash280.
Then accept P4 Pause at P3, followed by the existing driver-owned Quit. Earlier qualification21 used ten-second endpoint checks.
Current qualification uses the thirty-second limit above. Keep every context check.

Clear the window diagnostic selector and strip NativeAudit variables as before. Add no sampler. A timing miss remains
failure or incomplete evidence. It cannot become diagnostic success by relaxing a guard.

### Task 10: Apply the measured repair and make one acceptance retry

Task 10 starts only after Root reports the actual cause and selects a checkpoint/publication repair supported by
qualification21 evidence. Do not assume checkpoint reuse or a schema optimization before those measurements.

- [ ] Apply the one supported repair, preserve byte and authority contracts, and complete focused checks and review.
- [ ] Root freezes the normal build and release, then uses fresh qualification22 for the one acceptance retry.

Preserve qualification21 and all earlier evidence. Stop and report if the cause is unclear or this retry fails.
Review and unit corrections do not allow a second diagnostic or acceptance loop. If the retry passes, continue full Goal A qualification.
Keep saved-byte, normal and full-memory smoke/walk, and ten-period decision-loop checks.
Complete restart/lifecycle, render, input, human, final CI and PR work.

Keep existing storage and custody limits. This source task proves none of those outcomes.

## 11 November continuation: keep native window context

The Director approved the logging change and one further normal three-turn diagnostic. The Director also gave standing
direction to proceed with investigations, supported repairs and necessary checks without routine permission questions.
Return for steering if the evidence stops narrowing the problem or work repeats with little progress. This direction
supersedes earlier permission stops for routine work. Every numerical limit, nationwide and international coverage,
accounting authority, durability rule and original delivery obligation stays fixed.

### Task 12: Keep bounded window context and diagnose the real run

**Ownership:** One implementer owns native context, safe refusal codes, current namespace and focused source checks.
Root owns independent review, build custody and the real diagnostic. Keep the current economic candidate unchanged.

- [x] Keep four bounded window snapshots in the ordinary native control path.

Capture before mutation, immediately after the resize call, at the first after-Last boundary, and at terminal
acknowledgement or refusal. Reuse private diagnostic facts. Include the branch, base/effective scale and override,
copied pending maximize flag, component/native identity and geometry. Include target and observed extent, predicates,
event counts, last event, elapsed time, and exact action/sequence.

Keep the detailed stream opt-in. Keep the compact record on both success and failure. Use private compact format
version 1 in the existing observer log target. Preserve the detailed stream's phase contract. Do not add per-frame
native probes, a shadow cache or dependency patches.

Keep clocks and observations out of decisions and canonical bytes. Preserve the three-second timeout, existing verified
no-op and fresh-observation conditions, authentication, camera behavior and error ordering. No functional resize change
belongs in this task. Private Bevy cache and actual native submission remain unobserved unless directly proved.
Record sampled facts without claiming window-manager or surface causes.

- [x] Carry allowlisted native window refusal codes into the combined failure record.

Keep raw peer, transport, SQL and arbitrary exception text private. Unknown reasons get safe generic codes.
Capture any private evidence format change explicitly, without compatibility layers.

- [x] Use fresh qualification23 for the normal diagnostic and preserve qualification22 for acceptance.

Refuse retained qualification17 through21 and reserved22 through the existing admission tests. Preserve earlier campaigns,
binaries and evidence. Keep the public ten-horizon ordinary entry, its four confirmations and three closes.
Keep P1 Collect1450, P2 local food1/cash0, P3 remote food2/cash280, then P4 Pause without advancing P4.
Change no launcher, workload, endpoint or numerical guard. Use no window-only selector, NativeAudit or memory sampler.

- [x] Run meaningful focused RED/GREEN, applicable source checks and independent review.

Use installed v13 Main storage controls, serial heavy work, no documentation generation and no speculative full reruns.
Test context preservation, refusal privacy and unchanged successful/refused native behavior. Then Root freezes the normal
build and runs the one combined observation. Keep all source, logs, frames, database and shutdown evidence.

If the native boundary fails, inspect its actual retained predicates before choosing a repair. If it succeeds, use the same
run's P1–P3 phase observations to select the supported checkpoint/publication repair. Continue the original qualification
when evidence supports it.

Stop for steering if the cause remains ambiguous or further attempts would repeat without useful progress. A passing window resize is not game acceptance. Task10 and every original Goal A and Wayne obligation
remain required. Keep qualification22 for its acceptance retry.


### Task 13: Refresh first-publication statistics and finish grain law contracts

**Authority:** Continue the Director-approved delivery without routine approval stops.
Return for direction if useful progress stops. Keep the current limits and both original outcomes.
The dated amendment above owns the warm limit.

**Evidence:** Actual23 published three national periods. Its unchanged usable endpoints took
10.703, 12.345 and 10.594 seconds. Second-checkpoint work averaged 8.343 milliseconds, so reject that repair hypothesis.

The copied database had no statistics for all eleven measured graph/event tables.
Default column statistics changed the fifteen original validation SELECTs from 1,264.081 to 776.235 milliseconds on the committed copy.
All 155 census rows kept the same bytes. These separate statements do not prove native commit performance or qualify the game.

Keep both plans, statistics, source identity and clean shutdown evidence in the working evidence folder.
Do not ship the column grouping draft. Its inner data sets were empty in the measured case.

In a cold Michigan test, this SQL refresh took 2.009935 seconds. Its retry spent 0.006352 seconds.
Both values include the client round trip. They do not measure national play.

**Ownership:** One implementer owns the persistence changes and focused checks in Main.
Root owns native lifecycle, qualification and independent review. Run heavy checks one at a time.

- [x] Refresh the eleven approved graph/event column statistics after the first positive publication inserts its typed rows.

Run this refresh after the marker insert and before its deferred checks. Follow the existing Archive statistics pattern.
Use only the measured tables, columns and first-period identity.
Do not add persistent markers, policy thresholds, planner settings or caches.

Keep the refresh cost inside the unchanged first-turn endpoint.
Keep schema admission, every deferred check, atomic publication, locks, command identity, restart and all material and canonical bytes.

- [x] Add independent household composition and complete opening contracts for reversed input order.

Read source budgets, time and actual live consumer output. Add each protected child back once.
The two successive groupings must each merge positive contributions.
Compare the full typed witness and use the existing production material byte format.

Keep this exact accounting claim separate from the Designed grouping of live owners.
Do not add a witness byte format, new primitive, production grouping helper or claim that transitions stay the same.

- [ ] Show RED/GREEN with real SQL publication and actual contribution and order faults.

Restore temporary faults exactly. Run scoped tests, formatting, strict Clippy and BSL checks one at a time.
Build no documentation. Complete independent source review.
Keep normal23 programs before checks can replace them.

- [x] Route all current qualification profiles to the reserved fresh `qualification-22` folder.

Keep earlier `qualification-23` artifacts unchanged. Refuse them as current input.
Do not add compatibility by profile or new overrides. Do not release or run a game during this source change.

- [ ] Measure native results with fresh authenticated programs under the reserved qualification22 acceptance folder.

Root owns this step. Keep the matched byte comparison, both smoke and ten-period play tests in normal and memory modes.
Keep restart, rendered/input variants, the player session, final gates and reviewable PR open.
Defer optional census work. Continue game play once the agreed limits pass. This task claims no census speed gain.


### Task 16: Make the current decision readable

The Director's 11 November handoff requires these focused presentation fixes. The warm limit is 30 seconds.
Keep the current rules, permissions, personal draft and all other limits. Do not start more performance work.

One client owner handles these changes and scoped checks. Root owns independent review and native qualification.
The inspected Native23 frames identify defects. They do not qualify the new source.

- [x] Name collection work as shared material hours. Keep organizer pledges separate. Test with different quantities.
- [x] Give successful updates a short dated acknowledgement. Keep full facts in the dispatch, reports and exact receipt reading.
- [x] Keep errors, saving feedback and police interruptions visible.
- [x] Give each original aid commitment one heading and clear stage names. Lead with the actual response when present.
- [x] Keep separate commitments separate. Keep every exact receipt in history and Archive.
- [x] Keep a pending route's amounts in the personal draft. State why Review cannot proceed.
- [x] Distinguish saved drafts, changes awaiting save and saving failures. A draft alone submits nothing.
- [x] Put the existing Direction / routine action in the fixed deck toolbar.
- [x] Keep the local alternative, authenticated Review, separate Confirm and Advance, and every consent and time check.
- [x] Never choose for the player.
- [x] Run meaningful scoped client regressions and applicable format, Clippy and BSL checks serially. No docs builds.
- [ ] Inspect the final native screen at both sizes and interface scales, then exercise its input and return paths.

Keep overlapping county labels as follow-up polish unless the final play evidence shows a blocking problem.
No new art, map system, report store, practice or game rule belongs in this repair.


### Task 19: Repair the withdrawn executor dependency

Hosted run 43077137687 passed its 3,809 selected Rust tests, then rejected the withdrawn
`async-executor` 1.14.0 dependency. The other eight jobs passed. CI remains open.

The [crate registry](https://index.crates.io/as/yn/async-executor) marks 1.14.0 withdrawn
and 1.14.1 available. The [upstream release notes](https://github.com/smol-rs/async-executor/blob/master/CHANGELOG.md)
identify a use-after-free fix during executor destruction. Use the smallest compatible patch.

- [x] Reproduce the withdrawal refusal after refreshing registry metadata.
- [x] Update only `async-executor` to 1.14.1 and its checksum in `rust/Cargo.lock`.
- [x] Keep Bevy 0.20.0, all other dependency pins and all four policy checks.
- [x] Run the complete dependency policy check and compile its direct Bevy consumer.
- [ ] Complete independent review and exact-head hosted CI.

Local dependency checks use installed cargo-deny 0.19.0. Hosted CI uses 0.20.2.
The retained final22 programs describe the earlier source. Native qualification remains open.
Preserve those programs and earlier evidence. Root owns the later final gates and native qualification.


### Task 20: Isolate the native resize failure

The controlled probe at `03c4ac65` began at actual 1080x768, outer position (0, 0), on portrait DP-3.
The component request to 1366x768, including unmaximize, failed its three-second acknowledgement.
A direct native request without unmaximize also failed there. Moving the same owned window to
(1112, 1112) on the landscape primary and repeating the direct request produced a fresh resize,
matching native and component extents, and acknowledgement in 51,937 microseconds.

This is placement-dependent intervention evidence. Q22's exact server and visibility were not
recorded. The probe does not establish a universal window-manager policy or cache cause, and it
is not campaign qualification. Retain the probe and earlier qualification evidence unchanged.

### Task 21: Place the initial window on primary and qualify fresh source

- [x] Center the durable window's initial position on the primary monitor. Keep its title,
  1366x768 extent, Bevy 0.20, input, resize acknowledgement, camera behavior and deadlines.
- [x] Route current qualification consumers to fresh `qualification-24`, including Task 3's
  ordinary prefix. Task 16's completed `qualification-22` routing is historical and superseded.
  Preserve every earlier namespace and artifact.
- [ ] Demonstrate a true native 1080-to-1366 component transition after primary centering.
- [ ] Complete independent review, final gates and real campaign qualification at the new source.

The recorded primary is 1920x1080 and fits the requested extent plus its observed 43-pixel frame.
Missing or undersized primary monitors remain unguaranteed. This candidate adds no monitor recovery,
native bypass, retry or timing change. Existing storage, privacy, integrity, durability, nationwide
and international-trade behavior and default allocations remain unchanged.

Binding limits remain warm P1–P3 complete usable endpoints at most 30 seconds each, cold below
180 seconds, advance at most 120 seconds, Archive at most 180 seconds, and normal two-period smoke
at most 900 seconds. Aggregate memory stays at most 10,000,000,000 bytes with sample gaps at most
five seconds; save limits stay 10 GB and 40 MB per tick. Warm acceptance is not a p95 statistic.


### Task 22: stopped-source archive oracle

The source at `1c84ad59e6166c83ab441e1f4690c81dbb879f64` completed the ordinary three-period
prefix in namespace 24. Its full smoke reached both authenticated reopens and Archive, then
retirement refused a shared-catalog VM member absent from the running witness. A confined
read of the stopped original confirmed that file and the shortened catalog heap matched
the retained tar. This proves a phase mismatch. The maintenance process remains unproven.

Keep that failed source, stopped campaign and partial archive unchanged. The repair retains
running SQL, checkpoint, game-main extents, occupancy and stable-file authority. A separate
confined reader inventories and hashes every stopped original file. Both archive passes
must match that exact stopped source, and recovery admission verifies the sealed receipt.

This repair routed consumers to namespace 25. Its scoped checks proved only the operator
contract. Fresh native smoke, memory capture, release adaptation and human acceptance
remained pending. Old namespace 24 evidence cannot qualify the changed source.


### Task 25: Keep one storage model identity at CLI entry

The actual `python -m tools.devtools.wayne_qualification_storage` memory reservation
created `__main__.Reference` while the paired consumer imported the canonical storage
module. Their identical path, length and digest could not satisfy strict typed equality.
Canonical-import probes missed this entry behavior. Namespace 25's completed normal
member and failed memory admissions remain historical evidence, not a qualified pair.

- [x] Reproduce the unchanged-reference refusal through the actual module-as-main entry.
- [x] Delegate that entry to the canonical module before defining any storage models.
  Keep the strict typed comparison and all source, custody and admission guards.
- [x] Route current storage, ordinary-prefix consumers and coupled tests to fresh
  `qualification-26`. Preserve every earlier namespace and its measurements and failures.
- [ ] Complete independent review, final gates and fresh final-source qualification in
  namespace 26. No earlier normal member or failed memory admission qualifies this source.

The public command stays unchanged. The regression crosses the real reservation and paired
consumer without SQL, Docker or native programs; a changed reference must still refuse
before creating its memory member. Scoped GREEN does not establish campaign qualification.

Keep the full 30-second endpoint from Advance to a useful dated report or pending brief,
real rendered pixels and accepted next controls. Cold stays below 180 seconds, advance at most 120 seconds,
Archive at most 180 seconds and normal smoke at most 900 seconds. Aggregate RSS and saves
stay at most 10 GB, sample gaps at most five seconds and save growth at most 40 MB per tick.
No optional performance work or qualification bypass belongs to this repair.


### Task 28: Reduce physical-metadata transport overhead without relaxing capture

Namespace 26's current source passed 4,112 Python cases and fresh ordinary complete endpoints
of 10.330461090, 11.095155439 and 9.875502505 seconds. Its normal smoke completed two closes,
two authenticated reopens and verified retirement. The paired memory member failed opening:
qualified samples 13 and 14 had a 6.065988612-second gap. Charged RSS was 1,574,518,784 bytes.
An intervening foundation-publication crossing was correctly retained as unassigned evidence.
This is an unqualified pair; the normal member cannot qualify later source.

Retained timing locates roughly one second in each full physical-owner reconstruction.
A read-only prototype combined the six fixed container metadata reads into one nonce-framed
reply while running the existing complete validators. Three observed prototype checks took
0.563–0.583 seconds versus 0.867–0.934 seconds through the current supervisor. All complete
owner values matched. These diagnostic samples are not native qualification or a p95 result.

- Implement one fresh, bounded, strictly decoded reply for PGDATA stat, PID1 status, postgres
  UID, postgres GID, lineage and PG_VERSION. Reuse the existing physical/credential validators.
  Retire the six separate metadata execs. Keep the physical evidence schema unchanged.
- Keep the current supervisor transport and its 30-second operation timeout. Keep every
  fresh daemon/image/container/mount/port/role/SQL/ancestry/frozen-file/ownership check, both
  physical checks around native restoration, and all native/PostgreSQL barriers.
- Keep unassigned captures excluded. Do not reset the qualified-sample clock, add a cache,
  skip verification, change charge accounting, or count a crossing as a qualified sample.
- Show RED/GREEN for the framed producer/consumer and failure cases; retain all metadata
  mismatch controls. Run the affected storage, backup, memory and public-entry contracts.
- Route current storage, public ordinary consumers and coupled tests to fresh namespace 27.
  No source bridge, old-format adapter or earlier member may qualify the new source.
- Obtain independent source review, then run final-source gates and one fresh ordinary and
  paired-smoke acceptance retry. If the same sampling cadence still fails, stop further
  infrastructure changes and report measured options for Director steering.

All numerical limits remain: warm full endpoints at most 30 seconds; cold below 180 seconds;
advance at most 120 seconds; Archive at most 180 seconds; normal smoke at most 900 seconds;
combined charged RSS at most 10,000,000,000 bytes; qualified gaps at most five seconds;
saves at most 10 GB and growth at most 40 MB/tick. Optional game/SQL tuning remains deferred.

Current retention follows the Director's latest instruction: retire inactive disposable-test
backup bodies instead of maintaining or compressing them. Preserve source, required build
artifacts, small historical result records and evidence actively used for qualification.
The first cleanup reclaimed 10,116,096,000 allocated bytes. Earlier preservation notes record
past actions; they do not require retaining inactive backup payloads indefinitely. Failed
memory26 is normally stopped with its original files and exact owner record retained; no new
backup was made and no completed memory/paired qualification is claimed.

Task 28 implementation candidate:

- [x] Replace the six metadata executions with one fresh reply. Keep its six typed fields,
  nonce frames, strict base64, bounded reads and complete physical validation.
- [x] Route current storage and public ordinary consumers to namespace 27. Admission tests
  refuse namespaces 01 through 26. Earlier evidence remains unchanged.
- [x] Show RED (18 missing-transport failures) and GREEN (759 scoped operator cases, followed
  by 119 storage cases after a test-fixture refactor). Scoped Ruff, format, type, pinned
  environment and shell syntax checks pass. The existing AnyIO pytest deprecation warning
  and mypy unused-configuration note remain recorded.
- [ ] Complete independent review, final-source gates and the fresh ordinary and paired-smoke
  retry. No game, Docker, SQL or native qualification ran for this implementation candidate.
