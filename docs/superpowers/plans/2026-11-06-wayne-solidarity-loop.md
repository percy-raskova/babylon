# Wayne local needs versus wider solidarity implementation plan

> For agentic workers: use superpowers:subagent-driven-development. Execute the tasks below with independent task reviews and one whole-branch review.

**Goal:** A national Wayne player reads reported conditions, chooses contribution and independent food/cash amounts, receives one independent partner response, sees actual consequences, and chooses again.

**Architecture:** Extend the existing national material economy, organizer intent/admission/journal, restricted reports and native workspace. Keep one authoritative accounting/time/receipt path and explicit food/cash legs. No parallel scheduler or alternative economy.

**Tech stack:** Locked Rust/Bevy workspace, governed content, authoritative PostgreSQL and restricted Archive, existing Python operator/qualification tools.

**Spec:** Director-approved plan in this chat (6 November 2026); update the existing canonical Wayne design at `docs/superpowers/specs/2026-11-03-wayne-map-and-relationships-design.md` with the approved loop. This plan is its implementation breakdown, not a competing design authority.

**Linear:** PER-364, child of PER-9. Existing capability owners PER-58 (aid) and PER-345 (contributions). PR1052 remains a separate open UI delivery.

## Global Constraints

- Use national Wayne, not the Michigan fixed-time fixture, for this loop and native acceptance. Preserve P7 and the original Michigan P3 campaign, personal draft, old owner/evidence and normal binaries. Never query or operate P7/shared services or send gameplay input to the human campaign.
- Preserve existing household endowments and the $1 organization opening treasury. No extra cash, goods, consent, membership, loyalty, report agreements, political pledges or actual time are manufactured.
- Designed contribution target: whole-dollar input $1 through $1,450, initial draft $280. Independent aid food quantity: whole person-period packages 0 through 4, initial draft 1. Independent cash amount: whole-dollar input $0 through $1,450, initial draft $0. Internal monetary values remain exact signed i128 micros with checked nonnegative bounds and existing decimal-string wire representation. Actual partial results keep their exact precision.
- Collection costs existing 2 hours. Food fulfillment costs existing 2 real household hours per dispatched unit. Preserve captured organizer/partner coordination costs. Pledged political time and real household time are distinct constraints; fulfillment must not debit the political pledge twice.
- One practice per organization per 28-day period. A specific accepted practice substitutes for routine once. Paused routine remains paused until explicit Resume. Failed admission leaves routine intact.
- One up-to funding/dispatch attempt per original commitment. Unfulfilled remainder is terminal with a reason; no automatic retry. Only actual dispatched food can remain in transit. Never substitute cash for an unfulfilled food leg or vice versa.
- Cash transfers at existing support close: accepted in P, transferred in P+1 after ordinary household order admission, potentially spent by ordinary purchasing in P+2. Do not reorder phases or rerun purchases. Food alone follows physical freight, delay and loss.
- The first positive cash settlement OR actually consumed food permits one independently adjudicated coordination response, regardless of another leg failing. Record that attempt identity; later arrivals never reroll or repeat it. Existing receiving and independent political authority, actual household time and political pledges still constrain outcomes. If all requested legs end without qualifying support, record terminal NoQualifyingSupport without coordination time.
- Reporting authority is separate from giving/receiving and participation. Report only opted-in facts for already-known partners. Hidden facts cannot affect visible counts, nodes, geometry, picking or refusal detail. Historical access and retained-evidence/Archive rules remain binding.
- Keep transfer/delivery, purchase/payment, consumption, need change, actual time and participation distinct. No gift attribution for later fungible purchases; no housing-to-extra-time rule (current food-only unmet burden remains unchanged).
- Follow Constitution4.2.0, current governed vocabulary, strict immutable typed state, deterministic canonical bytes/hashes, detached atomic close and replay. No new primitive or weaker constitutional prohibition. Read constitution and relevant Rust style/gotchas before mechanics changes.
- No compatibility shims, missing-field defaults or migrations for replaced formats. Preserve old artifacts separately and reject unsupported inputs before writes. Retire replaced linked-cash implementation and coupled tests while retaining independent conservation/byte/behavior contracts.
- All task worktrees and bulky data stay under /media/user/data/worktrees or approved media storage, outside babylon-data. Use exclusive existing build-storage controls, BLAS=1 and serial heavy jobs. Never touch another worktree target or run broad cleanup/signals.
- Source/CI, native behavior/rendering and human acceptance are separate evidence. No merge is authorized. Use required mise commit workflow and coauthor trailer, Part of PER-364/PER-58/PER-345 as applicable. No doc-generating aggregate, Sphinx or cargo doc.
- Test meaningful regressions through RED/GREEN, smallest first. Run applicable conformance/replay/format/strict Clippy/BSL/publishing gates serially, once per relevant final change. Do not weaken baselines or budgets; intentional byte/content baselines require the existing ceremony and trailer.

For each recipient, good, unit and close, original commitment identity sets the
order of food consumption credit. Each original draws at most its actual grant
from the remaining household consumption. The household total stays separate.
This convention does not trace parcels or claim marginal effects.

## Review Focus

- Food/cash ownership and permissions, exact expense/income matching, partial outcomes and no duplicate charges.
- Mixed-arrival response identity across restart, all-no-support terminal state and independent political refusal.
- Actual shared household time versus pledged political hours; routine/pending collisions remain genuine constraints.
- Amounts bound to authentication, nonce, original request and future history, not reconstructed from a new cap.
- New report topics/grants/subjects retain lawful dates, opening basis and no private balance or hidden-layout leak.

## Task 1: Authenticated allocations and independent material support

**Ownership:** Core Rust organizer/practice contract, material-circuit aid/collection and money integration, tick material adapter and support bridge, persistence admission/capture/codecs/runtime protocol, national policy, directly coupled consuming fixtures/tests. Also the minimal client draft/command-construction changes needed to produce the new required type (no allocation UI/layout work yet). Own the approved numeric-authoring clarification, allocation ADR and canonical design update. Do not alter qualification operators or operate any campaign/service. You are not alone; preserve unrelated work.

**Read first:** Global Constraints and Review Focus above, the relevant current organizer types/transition/material replay/aid/collection/snapshot/draft paths, and current canonical Wayne design. Constitution and Rust style/gotchas govern changed mechanics.

### Interfaces

- Retain practice kind as OrganizerChoice. Add REQUIRED typed OrganizerAllocation to OrganizerCommand: None for ordinary practices; Collection { target_cash_micros: i128 }; Aid { food_quantity: u64, cash_micros: i128 }. Validate variant against choice, positive target, captured caps, checked integer bounds and zero/zero. Add no legacy default/deserializer fallback.
- Exact allocation must flow draft -> authenticated preview -> confirmed command -> original commitment identity -> material input -> result/pending/history/checkpoint. Same nonce plus same command is idempotent; changed amount under same nonce conflicts; another nonce cannot authorize another period practice.
- Replace mandatory linked cash_per_food with independent captured maximum_cash_micros and receiving authority for positive cash; food retains its own cap/receiving authority. A zero unselected leg is not unwired behavior and must not require irrelevant resources/permissions.
- Preserve original requested allocation separately from actual dispatch/grant. Give food and cash independently typed outcomes and dates, plus a separately retained at-most-once response state/receipt. Keep authorization until both requested material legs AND response are terminal.
- Existing status/snapshot surfaces must expose actual selected target, requests, per-leg progress, cash/food postings and response identity sufficiently for Tasks2/3. Do not reconstruct requested values from current config.

### Implementation and tests

- [ ] Clarify AGENTS numeric authoring to selected scenario's existing defines.toml. National is already a separately admitted policy source; author national caps there only. Keep instructions under200lines. Record authority clarification and allocation/leg/response semantics in a scoped new ADR; old ADRs remain immutable. Update canonical Wayne design, not a second design document.
- [ ] Add focused failing contracts for allocation validation, amount-bound command/nonce identity and selected collection targets. Record actual RED before implementation. Follow existing canonical/codec and scenario evidence practices.
- [ ] Carry the selected collection ceiling through the real protected contribution close and matching expense/income/receipt path. Preserve full/partial/refused outcomes and exact actual time. Never collect more than requested or lawful available funds.
- [ ] Add failing food-only/cash-only/mixed material tests. Independently execute food using existing stock/protection/fulfillment/freight/arrival/consumption. Execute cash using BOTH MonetaryBook::transfer_cash(..., MutualAid) and CostClose::cash_gift(sender, recipient, amount). Cash is one grant at dispatch close for local/remote; no synthetic food or reverse collection.
- [ ] Apply one-time partial grant/dispatch, terminal shortfall, exact separately authorized receiving terms, and independent results. Granted cash is not revoked by food loss/political refusal. Granted food is not erased by cash refusal. Retire obsolete per-food gift cash escrow/refund after checking consumers; keep unrelated ordinary payment/freight escrow.
- [ ] Prove response eligibility when either actual positive received leg qualifies, with exactly one actual response attempt and existing pledge/time/partner checks. Retain failed/refused response; no later arrival retry. All material legs terminal with no qualifying support yields explicit terminal no-support and zero coordination charge.
- [ ] Prove cash-at-P+1 cannot finance earlier admitted P+1 purchases, but is available to ordinary P+2 purchasing. Transfers alone cannot claim food, consumption or released time. Preserve real household endowments/treasury and current unmet-food burden rules.
- [ ] Test command-only collection/no-collection and varying amount controls, food-only/cash-only independence, both leg orders, partial/no funds, receiving refusal, route/loss, protected needs/time, ordinary/pending pledge collisions, duplicate original command and restart/failed publication. Extend existing consuming controls instead of cloning implementations.
- [ ] Update affected current schema/protocol/canonical versions and required fixtures faithfully. Use necessary baseline ceremony for intentional governed byte/content changes; never change expected values merely to bless a fault. Minimal client draft current schema and make_command must carry explicit initial/selected amounts; Task3 owns the editor.
- [ ] Run scoped changed-crate tests, applicable mechanical conformance/replay contracts, format and scoped strict Clippy/BSL as appropriate, serially. No full publishing/native/source push yet. Self-review exact money/time joins and public consumer wiring. Commit through mise with Part of PER-364, PER-58, PER-345 and required coauthor.

**Deliverable:** Compiling current contracts and real independently allocated material settlement/response, producer-to-consumer tested. Report exact public interfaces, changed versions/ceremony, RED/GREEN commands/results/logs, files, commits and concerns in Task1 report. No missing-leg placeholder, permissive fallback or untested cap increase.

## Task 2: Lawful partner reports, evidence and retained consequences

**Ownership:** Report/need-sharing domain types as needed against Task1's settled interfaces; material-receipt report producer; organizer journal/status/snapshot history; restricted report grant/Archive paths and stable aid-partner subject. Direct consuming tests and minimal compile updates. No allocation renderer or operators. You are not alone; preserve Task1 and unrelated work.

### Interfaces and semantics

- Add typed partner report with stable report identity, known partner/source, exact topic values/units, observed/acquired period, evidence class and scoped citation/grant. Topics are FoodProvision, EssentialServices, ParticipationTime; granting/receiving/participating never implies sharing.
- Food uses HouseholdConsumptionReceipt required/consumed/unmet/closing. Services use HouseholdServiceReceipt and ServicePerformanceReceipt; actual settled/refunded cash joins exact MoneyTransferReceipt by service order/period/buyer, never balance differences. Time uses actual household_time plus same-period contribution debits exactly once.
- Scope EssentialServices to food-related provisioning, housing and existing essential service requirements actually named in the opted-in grant; omit unrelated purchases/accounts/providers. ParticipationTime sharing is separate; reported completed residual is not future promised capacity.
- P0 opening report is explicitly OpeningAssessment from captured initial stock/current required food (and clearly marked dated requested/quoted support), not completed unmet consumption/purchase/time. The funding brief uses actual own resources. Completed reports begin after first real close. No opening service-stock invention.
- Known aid-partner subject represents disclosed partner identity, not hidden private household incidence. Refactor hard-coded workplace report filters through explicit typed subject/knowledge checks across dispatch, World, inspection and Archive. An exact report grant does not grant the whole private dossier.
- Retain bounded aid history by original commitment using existing history window and Archive for older exact evidence; requested amount, each leg and response have original dates. Missing retained evidence routes to Archive. History cannot show future reports/actions.

### Implementation and tests

- [ ] Add focused RED for opted-in reports from actual committed food/service/payment/time receipts; withheld topics or reports cannot change visible counts/geometry/hit targets or leak private cash balances.
- [ ] Wire report producer/journal/atomic persistence, authenticated snapshot, exact evidence grants and Archive subjects end-to-end, including P0 opening basis and independent observed/acquired dates.
- [ ] Wire full requested/actual support history, pending and completed cold reopen, exact original grant/response joins and current-versus-historical restrictions.
- [ ] Test cash received versus next-close purchases/services/food separately; housing satisfaction can change with no time gain. Compare only actually acquired prior reports, otherwise prior unknown. No gift-specific causal attribution from fungible money.
- [ ] Run scoped tests/conformance/replay/format/strict Clippy/BSL applicable to changed source, serially; record RED/GREEN and actual results. Update canonical design with final implemented evidence semantics. Commit scoped Part of PER-364/PER-58 as appropriate.

**Deliverable:** New lawful partner reports and retained consequences actually reachable through the admitted runtime and Archive, with exact typed interfaces for Task3. Report commands/logs/commits/limitations; no source or CI proof claimed as human acceptance.

## Task 3: Native allocation decisions and consequence dispatch

**Ownership:** Bevy organizer draft/editor/action/review/dispatch/report views, public subject consumers, shared HUD/layout/camera fitting/input exclusion together, qualification-control actions/fields needed to exercise the same ordinary handlers, and directly coupled client/control tests. No engine/persistence semantic changes without controller coordination. You are not alone; preserve earlier task changes.

### Player behavior

- Resource header shows actual treasury, pledged organizer-hours and clearly dated shared household time. Show donor food ownership/protected availability, fulfillment hours and market/route uncertainty in allocation details; never call donor pantry organization-owned stock.
- Editable contribution dollars and independent food/cash aid amounts use the accepted bounds/defaults. Preserve saved values/notes/references through inspection, return and local/remote comparison. Same shared aid basket enables fair local/remote comparison; changes invalidate authenticated review. Invalid inputs show specific errors; do not round/clamp silently.
- Contribution mode compares Collect with routine. Aid mode compares local and remote for the same chosen amounts, with routine always discoverable and displaced work explicit. Keep all other practices accessible.
- Report action prepares cited ordinary draft only. Review freezes actual amounts/parties/costs/receiving terms and separate cash/food/purchase/response timing before separate Confirm and Advance. No report click or editor action executes gameplay.
- Pending and result dispatch separates requested, granted/dispatched, in-transit/arrived/lost/refused, recipient consumption/services/time and one partner response. Later food cannot repeat an already completed response. Historic receipt cannot pose as current result.
- Pause Play once for new own support dispatch/settlement/arrival/loss/refusal/partial, one partner response, and first/changed disclosed unmet food or essential-service shortfall. Deduplicate by stable original/leg/transition/report identities and current period; unchanged pending stages or historical reports do not repeatedly interrupt. Arrival-window warning exposes possible routine/time collision and offers explicit Pause, never silently cancels routine.
- Respect existing keyboard/focus/a11y, one readable region/fixed Return, audio/reduced-motion and overlay gesture exclusion. Fit1366x768 Standard1/Larger1.15 and1920x1080 Standard1.25/Larger1.4375; selected group/resources/two choices/essential consequences together. Do not enlarge existing oversized UI modules just to absorb the editor; extract coherent owned components if needed.

### Implementation and tests

- [ ] RED/GREEN client contracts for parsing/bounds/defaults, draft persistence and amount edit review invalidation, exact confirmed command, report->draft provenance/return, amount-scaled visible cost and independent timelines.
- [ ] Implement current native UI through ordinary OrganizerAction handlers and stable subjects, including keyboard numeric entry and map input exclusion while editing. Private presentation models may format admitted data, never judge mechanics or hidden eligibility.
- [ ] Test current result/history selection, partial/mixed/no-support/refused outcomes, response dedup and Play pause triggers across replayed reports/unchanged pending/current reopen.
- [ ] Expose test-only controls through the SAME ordinary actions, including actual editor input/focus and authenticated preview fields; extend producer-faithful consuming fixtures, never reconstruct unsupported state in test helpers.
- [ ] Run scoped client/control/real-font layout/decision-surface tests first, then format/scoped strict Clippy/BSL serially. Update canonical design and record independent rendered acceptance still pending Task4. Commit scoped Part of PER-364.

**Deliverable:** Playable adjustable resource decisions and meaningful report/response/result navigation in the existing workspace. Report exact ordinary input/control path, tests, versions, commits and remaining native/human evidence.

## Task 4: National qualification, reviewable delivery and human handoff

**Ownership:** Necessary current qualification-control consumers/operator tests, task-owned disposable national admission/run/backup/recovery artifacts, public report/unaltered screenshots and final canonical evidence update. Root owns overall publishing/Linear/PR and final live releases. No protected-campaign or shared-service operation. You are not alone; keep source frozen while native binaries are qualified.

### Runtime qualification

<!-- Vale: these are qualification constraints, not procedural steps. -->
<!-- vale ste.ProcedureLength = NO -->

- Use the ADR294 pair for each named workload: `normal_play` then `memory_capture`, serially under the common lease. Use `bash tools/run_rust_postgres.sh --wayne-native-pair smoke-01` for two periods and `walk-01` for ten. No anonymous single-run native certificate.
- Give each member a disposable owned database/container/port and separate XDG state, with explicit source/binary/owner/canary/lock/current-input admission. Source declares one fresh shared UUID4 only for these two empty databases and authenticates each actual P0. No inherited/shared target or default protected DSN. Wait for the original human game's normal closure before admission. Never close it automatically or use its save.
- Release exactly three external inputs: cached `BABYLON_POSTGRES_IMAGE_ID`, actual `BABYLON_WAYNE_HOST_CONTEXT_SHA256`, and serialized per-workload `BABYLON_WAYNE_NATIVE_EXPECTATION_REF` Reference JSON. Have `PostgreSQL` 17+ `pg_restore` on PATH for offline custom-dump list/read validation. Do not invent a release generator or copy historical P0 hashes.
- Before any live run, prepare concrete bounded operator/admission/recovery plan for independent review and controller release. Reuse existing controls, no new general lifecycle framework. Retain failures; no hidden reset or enlarged budget.
- Actual ordinary national sequence: inspect opening, adjustable Collect, local food-only, remote mixed, explicit routine management through disclosed arrival, cash-only, then following ordinary purchasing close. Actual national route defines waits. Exercise pending and completed restart, and verify real installed actor/observation/durable state, not process readiness alone.
- Real normal binaries, four fitted native variants, actual allocation editor/review/confirm/advance/report/evidence/return path, distinct per-leg dates/results and exactly one response. Root personally inspects images. Retain raw unmodified captures, source capsule, input and binary hashes and exact authoritative snapshots.
- Keep numeric policy v6 unchanged byte for byte. Normal play constructs no sampler. Enforce advance <=120s and cold open/reopen <180s. Archive and production reads take <=180s each, focused controls <=60s and the existing two-period smoke <=900s. Time the longer walk separately. Keep the required 52 samples for p95 and 52/325-period acceptance separate.
- The required memory member repeats the same workload, including all three process-cold walk segments. Keep full creation/period coverage, source/actual-role admission, process/backend identity, authority and restoration. Keep RSS plus `hugetlb` <=10,000,000,000 bytes and largest gap between samples <=5s. Raw phase durations remain diagnostic under the existing 900s operation watchdog and existing control/cleanup watchdogs. Never subtract freezes or invent zero-memory evidence.
- Authenticate exact command/commitment/receipt/marker joins and restart state within each member. Compare equal source closure, actual role-to-binary digests, inputs, policy, workload, horizon, foundations and ordered actual decision semantics across members, allowing legitimate different `nonces`. Matching decisions must also match the named schedule.
- Restore each full backup into its own verification database. Compare actual terminal state, check logical/physical custody and exact retirement. Reread both bundles for final report v8.

  Preserve PGDATA/XDG/source/input capsules/raw images/full backup/logs/unique evidence. The canonical namespace is `qualification-10/<workload>/<mode>/`. `sql-01` stays unpaired. Leave earlier namespaces unchanged. A missing/failed member cannot qualify.

<!-- vale ste.ProcedureLength = YES -->

### Verification and delivery

- [ ] Extend meaningful producer/consumer operator tests RED/GREEN only where the new real path requires them; no implementation-mirroring suite or default-filled new mandatory state.
- [ ] Complete actual native witnesses and independent image/source review. Record genuine refusals/partial outcomes and original failure history. Do not script success or inflate resources to pass.
- [ ] Publish concise factual report and unmodified size-compliant screenshots, privacy check, meaningful exact citations/links; update canonical design. No credentials, owner manifests, dumps or personal drafts in Git.
- [ ] Prepare exact review package and root whole-branch review. Run appropriate scoped checks first and applicable final Python/Rust formatting/Clippy/conformance/replay/decision/BSL checks serially without documentation generation. Required normal hooked publishing and exact-head remote CI/verifier remain root-controlled. No merge.
- [ ] Separate human session after agent walkthrough: record comprehension, hesitation, chosen follow-up and desire to continue. Source/native success does not fill these fields. Prepare a reviewed human campaign/build handoff without touching existing campaigns; keep pending human acceptance explicit if external input is still needed.

**Deliverable:** Reviewable follow-up PR targeting dev, playable qualified national build and comparison screenshots, with actual tested behavior and explicit remaining human/broader acceptance. Keep PR1052 and old worktrees/evidence unchanged. Root updates PER-364 and capability owners from evidence without closing umbrellas from CI.
