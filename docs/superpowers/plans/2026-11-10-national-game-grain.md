# National game grain implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the live national economy before expansion while completing Wayne's real report-to-funded-commitment loop.

**Architecture:** Push captured county/source contributions into Designed representative principals before economic sites, accounts and relationships are built. Preserve additive source quantities and explicit financial/time ownership; continue using the ordinary compiler, detached material tick, authenticated persistence and actor disclosures. This is a new game resolution, not an exact quotient of the old fine trajectories.

**Tech Stack:** Locked Rust workspace, babylon-persistence/material-circuit/tick/client, Bevy 0.20, existing captured national TOML and typed canonical codecs.

**Spec:** `docs/superpowers/specs/2026-11-03-wayne-map-and-relationships-design.md`, section “National game grain”. The design decisions are recorded in `ai/decisions/ADR296_national_game_grain.yaml`. The active combined-goal contract is mirrored at `.superpowers/sdd/2026-11-09-native-qualification-split/task-4-bounded-delivery-goal.md`; both milestones remain required. The retained 10 November candidate design and baseline are evidence, not separate live authorities.

## Global Constraints

- Nationwide coverage includes all 3,144 captured county contributions exactly once, twelve finite foreign groups, six separate dependencies, international gateways and finite shared freight.
- Full Wayne 26163 and Cook 17031 opening principals remain detailed. Source assignment and aid preparation precede folding; no full fine EconomicOpening is built and then consolidated.
- Background principals are explicitly new Designed representatives. Distinct positions, budgets, source ownership, protected needs, receiving/reporting/participation consent and current class margins remain meaningful. No exact old/new transition or hash equivalence claim.
- Exact source accounting uses checked integers and per-source floors before sums. Preserve unknown versus zero, eight source classes, exact currency micros, independent stock/time owners, canonical ordering, atomic publication and restart admission.
- National numeric terms belong in `content/scenarios/national/defines.toml`: treasury $1; contribution target $1–$1,450 initially $280; food 0–4 initially 1; cash $0–$1,450 initially 0; no zero/zero; existing 2-hour collection, 2-hour food fulfillment and coordination costs.
- Existing county transport mapping and finite original hub/regional/trunk/gateway pools are the membership authority. Resolve capacity-induced basic-needs subdivision deterministically before candidate freeze; no capacity multiplier, fictitious geography or new primitive.
- One coherent initial implementation plus ONE corrective iteration after measured acceptance failure. At most one targeted diagnostic per demonstrated blocker; no unchanged full reruns. The sole baseline profile is completed and cannot be repeated.
- Ordinary P1–P3 Advance-to-dated-actionable-or-legitimate-pending-brief with usable next controls must each be ≤10 seconds at 1366×768 Standard. Three samples are not p95. Startup/recovery are separate.
- Both normal AND full-memory national smoke/walk members, ten-period decision loop, restart/lifecycle, native input/frame and human acceptance remain required. Cold <180s; advance ≤120s; Archive/read ≤180s; normal two-period smoke ≤900s; aggregate memory ≤10,000,000,000B; sample gaps ≤5s. Existing storage/custody limits unchanged.
- Use the isolated `/media/user/data/worktrees/per364-wayne-solidarity-loop/babylon` lane. No protected 0c51 edits, compatibility/migrations, broad deletion, unrelated feature/AI work, merge or umbrella closure. Heavy checks serial; BLAS=1; pinned toolchain and installed v13 worktree build controls; no documentation generation.

## Review Focus

- A county with pre-existing excessive demand stays explicitly scarce; splitting must distinguish that from a shortage newly forced by consolidation (Task 1 finite lane fixture).
- Two reserve positions share a physical hub but cannot spend each other's household cash/pantry or public budgets (Task 1 real compiled/ticked independence fixture).
- Protected child/parent, payee, membership and receiving identities survive the fold exactly once; aid still settles once and later purchases remain P+2 (Task 1 existing aid/restart regressions).
- Hub-level results cannot masquerade as observed individual county outcomes, or expose undisclosed principals (Tasks 1/2 provenance and hidden mutation checks).
- A fast internal receipt is insufficient: the visible brief and next controls must be usable, with actual/pending dates and reliable evidence return (Tasks 3/4 native measurements and human session).

---

### Task 1: Build and execute the real coarse national opening

**Ownership:** One fresh implementer owns all related source writes and scoped verification for this task. Other agents may inspect read-only. Do not create parallel writers or dispatch subagents.

**Files:**
- Create `rust/crates/babylon-persistence/src/national_economy/grain.rs` and focused tests beneath `national_economy/grain/` only if cohesion warrants separation.
- Modify `national_economy.rs`, `national_economy/identity.rs`, `policy/{game,admission}.rs`, `opening/{build,actors,financial,household_time,markets,equipment,routes,detail}.rs` and `content/scenarios/national/defines.toml`.
- Modify only necessary helper visibility in `national_resident_allocation/{allocation,households}.rs`; preserve source county allocation and its source validation.
- Wire admitted capture/witness through `economic_catalog/{national,model,compile}.rs` and directly affected current-source codecs/consumers where needed. Do not add a compatibility branch.
- Update directly coupled opening/runtime/replay/knowledge tests and current canonical expected values only with the required ceremony. Do not touch qualification operators or run a campaign.

**Interfaces:**
- Consumes the existing `allocate_home_county` output, household/time controls, exact `aid::prepare` remapping, admitted counties/transport and captured `NationalGamePolicy`.
- Produces `NationalGrainPolicy`, `CapturedNationalMembership`, `NationalGenerationWitness`, `NationalOpeningRoster`, representative identity/domain keys and one current `coarsen_source_allocation(...) -> Result<NationalOpeningRoster, NationalGrainError>` operation.
- `capture_membership(counties, transport, source_allocation, policy) -> Result<CapturedNationalMembership, NationalGrainError>` owns deterministic partition/refinement; use existing strong identifier and allocation types. New names in this plan are authoring types, not mathematical primitives.
- `NationalOpeningRoster` supplies current workplaces/members, explicit households/time eligibility, per-source-summed productive endowments, financial-domain joins and witness. Only this live roster enters the ordinary compiler. Witness is captured/authenticated once and reproducible on restart; do not copy incidence into each state/receipt.

- [ ] **Step 1:** Read the canonical specification, ADR296, relevant Constitution II/VI, Rust style/gotchas and current source consumers. Record the exact task base and the settled deterministic refinement rule. Stop only for a genuine unresolvable architectural contradiction; ordinary technical choices belong to the implementer/controller.
- [ ] **Step 2:** Add and run focused failing fixtures for complete county membership/insertion-order identity; unique subdivisions and the two-county 28-billion-gram versus 20-billion-gram counterexample; pre-existing oversized singleton; same-hub reserve/budget distinctions; per-source nondivisible production-floor sums; exact protected child/parent joins. Record actual RED, not a retrospective claim.
- [ ] **Step 3:** Implement the typed captured grain policy and one membership/refinement operation. Derive final reserve positions only after subdivision. Refuse malformed or incomplete transport joins, overflow, protected overlap and unsupported generation with specific errors. Record the finite screening witness, deterministic membership digest and source totals. No new baseline profile.
- [ ] **Step 4:** Insert source folding immediately after `aid::prepare` and before `actors::domestic`. Fold one ephemeral productive source seed at a time; no Vec of fine sites. Remap counted household/member identities and sum same-unit endowments, household/person/class/eligibility/time quantities with source floors intact. Pass exact Wayne/Cook rows through.
- [ ] **Step 5:** Consume the actual roster in actors, financial domains, equipment, markets and routes. Preserve explicit source ownership for Designed sites. Public/owner budget joins must use domain identity rather than hub location; household eligibility must use explicit aggregate overrides, not hub population. Preserve finite stock, merchant labor and shared transport authority. Remove misleading late classification-as-consolidation claims and any now obsolete generation path.
- [ ] **Step 6:** Complete admission/capture/regeneration and all ordinary compiler/runtime consumers. Add meaningful real compiled/ticked tests for independent balances/pantries, staffing-payee/time joins, transport contention, island refusal and source conservation. Verify protected opening identities/endowments exactly; permit changed national trading trajectories. Run existing funded contribution/food/cash/partner/refusal/timing/replay/atomic-failure tests serially.
- [ ] **Step 7:** GREEN: run the smallest tests first from `rust/` using locked Cargo and current worktree controls, followed by applicable scoped conformance/replay. `cargo fmt --all -- --check`, applicable scoped strict Clippy and BSL sentinel legs run separately; no docs. Record the actual commands, exit statuses, counts, skipped cases and unresolved risks. No native/performance qualification claim from unit tests.
- [ ] **Step 8:** Self-review the complete real path, commit with `mise run commit -- "feat(economy): generate national game-grain principals"` and required `Part of PER-364`/coauthor conventions, and return a concise report. Root dispatches the independent task reviewer; no worker reviewer.

### Task 2: Keep organizer questions scoped and county evidence truthful

**Files:** Only necessary ordinary organizer runtime/session/client call sites, `organizer_runtime/{snapshot,material_preview}.rs`, `observer_material/snapshot.rs`, `production_projection/projection.rs`, county dossier labels and directly coupled tests. Existing scoped read-only audit determines whether a routing change is warranted; do not add a generic projection framework without a demonstrated missing field.

**Interfaces:** Consume Task 1 current principal identities/witness and existing authenticated organizer disclosure. Produce the same typed organizer snapshot/preview and cited county/catchment provenance. If genuinely needed, use typed server-derived `ProductionReadScope::Actor(ActorDisclosureScope)` before family DTO allocation; never a client-supplied wider scope or a falsely full national hash.

- [ ] **Step 1:** Trace actual ordinary Advance → authenticated read → rendered dated brief. Use the existing audit, do not rediscover it. Record required full decode/hash work separately from avoidable national DTOs.
- [ ] **Step 2:** Add/run only missing failing knowledge/provenance tests: undisclosed remote mutation leaves unchanged local disclosure; coarse hub outcome is not an observed county value; actual and pending result dates remain distinct. If the existing path already satisfies the read boundary, record evidence and omit speculative changes.
- [ ] **Step 3:** Make the smallest needed routing/label fix, run scoped GREEN/format/Clippy/contracts serially and commit with the governed task runner. Independent review must confirm unchanged full national inspection and evidence/hash authority.

### Task 3: Measure the one candidate and admit the next native run

**Files:** Existing qualification operators/tests only where actual current identity or required measurements demand updates; task-private bounded operators and evidence. Root owns the sole heavy/runtime slot and final release grant. No stale namespace/source/binary pins may be reused as current.

**Interfaces:** Consume the reviewed exact Task 1/2 head, captured source/input digests, normal final binary manifest and retained baseline; produce authenticated candidate counts/P0/P1/P2 state/receipts, normal warm observations and separate memory evidence.

- [ ] **Step 1:** Reuse the completed sole baseline profile (`52e789859bcc55f8109c3c88a547acf0746cd3f5`, input `f74b00861c74b2a92cadbcf0925c4e5b88accf72c0274c7c78957a2921cbddd5`), retained qualification14 headers and the same recorded decisions. No baseline rerun. Baseline: 60,634 sites, 15,696 households, 100,302 terms, 2,169,757 relation-row occurrences.
- [ ] **Step 2:** Build current ordinary binaries through installed exclusive controls, independently verify source/inputs/final bytes and prepare a new disposable national fixture. Prior failed fixtures, unique evidence and source remain retained; no legacy save conversion or extra failed-state backup program.
- [ ] **Step 3:** Measure actual opening and first two closes at comparable boundaries. Require fewer live actors/sites and economic relations, smaller P0/P1/P2 canonical state and P1/P2 receipts; report packed bytes/RSS separately. Retained baseline bytes: P0 187,831,389; P1 state 218,047,972/receipts 386,683,376/packed pair 30,578,680; P2 state 231,323,308/receipts 341,793,923/packed pair 31,990,935.
- [ ] **Step 4:** Measure ordinary native P1–P3 at1366×768 Standard from input to useful dated/pending brief plus usable next controls. Each must be ≤10s; report all three, no p95. An internal tick or typed driver alone cannot prove visible readiness.
- [ ] **Step 5:** For a demonstrated failure, permit at most its targeted diagnostic and the ONE measured corrective iteration. Distinguish pre-measurement review/unit repair from changed measured candidate. If both candidates miss, return evidence/options and leave the active goal incomplete; do not expand scope or raise limits.

### Task 4: Complete the funded loop and reviewable delivery

**Files:** Existing qualification member operators, native comparison evidence, canonical Wayne design, exact-head publishing/PR records and authorized narrow Linear updates. Do not modify old ADRs/reports or claim broader milestone completion.

**Interfaces:** Consume Task 3 actual structural/performance outcome and current playable build. Produce normal/full-memory smoke AND ten-period walk evidence, native frame/input evidence, uncoached session and exact-head green reviewable follow-up PR targeting `dev`.

- [ ] **Step 1:** Exercise the national ten-period collect → local food-only → remote mixed → explicitly manage routine during arrival → cash-only → subsequent ordinary purchasing path with actual finite route timing. Verify reports/permissions, exact settlements and one response through restart; separate normal timing from mandatory full-memory members without weakening either.
- [ ] **Step 2:** Inspect original native1366×768 and1920×1080 Standard/Larger frames; verify pointer/keyboard amount entry, comparison/review/confirm/advance, cited report/Archive return and overlay exclusion. Typed action drivers do not establish physical input; record remaining human checks honestly.
- [ ] **Step 3:** Prepare the already-authorized fresh uncoached playtest after automated readiness. Record comprehension, hesitation, follow-up choice and desire to continue; fix blocking failures within the authorized correction bound and obtain Director acceptance. Do not coach the initial decisions.
- [ ] **Step 4:** Run required publishing checks serially without docs generation: scoped regressions first, then applicable Python gate, Rust format/Clippy/conformance/replay/contracts/BSL and hosted exact-head CI. No baseline relaxation. Obtain broad independent branch review and resolve load-bearing findings.
- [ ] **Step 5:** Publish a reviewable follow-up PR to `dev`, current playable build and comparison evidence. Update authorized Linear issues narrowly with verified delivery and explicit remaining acceptance. Preserve PR1052 and broader issue scope. No merge or umbrella closure.
