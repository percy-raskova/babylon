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

Ordinary P1–P3 Advance must each reach a dated actionable or legitimate pending brief, with usable next controls, within
10 seconds. Measure at 1366×768 Standard. Three samples do not prove p95. Measure startup and recovery separately.

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

Measure input to useful dated/pending brief with usable next controls. Each must take ≤10s. Report all three without
claiming p95. Internal ticks and typed drivers cannot prove visible readiness.

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
