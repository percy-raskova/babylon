# Game delivery audit — 2026-10-29

**Historical decision, October 29:** Repair the national launcher check and finish a bounded player
session before starting the next scene. The repository has a material circuit,
Archive and an organizer loop. The late-empire plan and an autonomous opponent
remain undelivered. The current source does not show whether players understand
or enjoy the loop. This audit adds no mechanics.

This review uses [`9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65`](https://github.com/percy-raskova/babylon/commit/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65),
the remote `dev` head inspected on October 29. Source links below use that
revision. Linear status is a snapshot, not a substitute for acceptance evidence.

## November 4 follow-up

The initial findings below describe the October 29 revision. Subsequent work
connected the first City PD opponent and the native Wayne map, evidence,
action and restart path. The [approved closeout plan](../docs/superpowers/plans/2026-11-04-first-opponent-wayne-closeout.md)
addresses acceptance gaps; the earlier Goal-complete wording was too broad.
The remaining sections retain the October 29 findings at their stated revision.

| Area | Delivered behavior | Current acceptance |
| --- | --- | --- |
| First City PD | Committed funding, finite paid visits, private cases and actor-scoped public encounters | Matched PD/no-PD PostgreSQL, post-hidden-change selection and source-input order controls passed. Scoped review passed; integrated multi-case, actor-order and topology variants remain unqualified. |
| Wayne map and action | Places/Relationships selection, evidence, captured targets, committed P7 and restart | Review text and cramped reading areas were repaired. Real-font layout and keyboard consumer regressions passed; the final client run passed 580 tests. Static native evidence is linked below. Complete choice comparison, physical input, Director comprehension and enjoyment remain unaccepted. |
| Performance | Retained native traces and four new disposable PostgreSQL advance timings | No demonstrated causal defect justified a repair. Slow reopen attribution, Archive attribution, complete storage charge, combined-game memory and sustained national qualification remain open. |
| Wider opponent | First PD foundations are reusable | Full PER-355 agency delivery remains open; observation alone does not establish interesting opposition. |

Current development qualification retains ADR280 and the selected v6 policy:
40,000,000 bytes per period, a separate 23,000,000-byte optimization target,
and a 120-second advance p95 requiring 52 samples. The North Star retains its
10,000,000-byte ambition. Neither the retained single-period net growth nor the
short disposable fixture qualifies those sustained limits. PostgreSQL remains
authoritative; older SQLite instructions are historical.

The closeout also reran the current controller component contracts: nine passed,
including case order, owner/provenance, reconstructed graph identities and honest
no-case/no-funds outcomes. These component checks complement the bounded
integrated witness; they do not establish a multi-agency playtest or every
integrated hidden-topology variation. The November 4 acceptance repairs add no
mechanic or public API.

The matched [PostgreSQL funding control](../rust/crates/babylon-persistence/tests/national_city_pd_live.rs)
produced one disclosed encounter with PD enabled and none without it. Other
Wayne claims were fully funded in both arms; the control does not demonstrate a
shortage. The [controller contracts](../rust/crates/babylon-tick/tests/state_opponent.rs)
remain distinct from the wider integrated matrix.

The retained P7 capture at source
[`956119a8`](https://github.com/percy-raskova/babylon/commit/956119a8ee011bb1bf34e8562e6ad9028adb7ba0)
shows the review and map at 1366x768 and 1920x1080. The
[1366 capture](gameplay-delivery-audit-2026-10-29-assets/wayne-review-1366.png)
is included here. The larger original remains in the retained run evidence
with SHA-256 `477c62a2d23893aa7dc5f6111765bd2b47d829cd33e477b54303cdca04bf85d8`.
The situation is readable; the initial choice area remains partly clipped by
its outer viewport. Computed geometry shows that scrolling can expose a larger
reading area, but the capture did not exercise that input. Review terms also
require scrolling at the smaller size.

The [loaded workplace Archive](gameplay-delivery-audit-2026-10-29-assets/wayne-pd-archive-1366.png)
visibly reports a period-2 public City PD check-in and explicitly withholds an
inference that the organizer attended. This is a disclosed signal; the capture
did not open its underlying citation or expose the agency's private case.
Full P7 marker metadata matched before and after, and the original personal
draft was restored. No commitment or advance was submitted.

The later [keyboard repair](https://github.com/percy-raskova/babylon/commit/6397a5f0602fd5b89a107be2008c5df33c0609ab)
changes only the focus router and its tests. It lets paging continue to an
outer panel when the inner panel cannot move and permits paging from focused
choice buttons. Actual keyboard-consumer regressions cover those paths;
injected geometry also checks that Tab starts nested focus reveal without
activation. The organizer layout file is unchanged, so the static captures
above remain rendering evidence, not native verification of the new key path.
Wheel code is unchanged and physical keyboard/wheel acceptance remains open.

## Scope and status

[PER-350](https://linear.app/percy-raskova/issue/PER-350),
[PER-354](https://linear.app/percy-raskova/issue/PER-354), and
[PER-362](https://linear.app/percy-raskova/issue/PER-362) have status `Done`.
[PER-355](https://linear.app/percy-raskova/issue/PER-355) has status `Backlog`,
[PER-336](https://linear.app/percy-raskova/issue/PER-336) has status `In Progress`, and
[PER-292](https://linear.app/percy-raskova/issue/PER-292) has status `Todo`. PER-336's
latest clarification describes preparation, not completed player acceptance.
PER-354's architecture phases P0–P9 are not the game plan's W1–W5.

[ADR289](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/ai/decisions/ADR289_retain_postgresql_campaign_owner_and_retire_sqlite_experiment.yaml)
retains Postgres as the sole campaign owner and supersedes the SQLite owner
decision. Commit [`239ff7c04`](https://github.com/percy-raskova/babylon/commit/239ff7c04)
removed the SQLite experiment. It neither implemented nor reverted the later
game waves.

The [October 25 plan](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/docs/superpowers/plans/2026-10-25-babylon-gameplay-and-late-empire-plan.md#L1-L16)
still assumes ADR287, SQLite, Constitution 4.3 and a DeepSeek mandate. Those
assumptions do not describe current authority or this audit's requested model.
Its wave overview also numbers tasks differently from its nine task headings.
Read it as historical design input, not current implementation evidence.

## Current delivery and campaign path

| Area | Designed | Implemented component | Connected to play | Verified |
| --- | --- | --- | --- | --- |
| Catalog and opening | National captured economy and organizer content | Immutable captured catalog and foundation admission | National New selects and creates the foundation | Source trace. Reused scoped Postgres smoke, not a fresh national acceptance |
| Material circuit | Bounded production and distribution | Material-cycle and durable material replay | National capture includes the cycle | Reused scoped 15-tick/restart evidence. No fresh DB run |
| Organizer | Bounded commitment, time and partner response | Typed organizer state, command admission and receipts | Organizer workspace submits commitments for later periods | Source trace and reused session smoke. Human comprehension and enjoyment unverified |
| Archive | Grant-filtered, receipt-bound knowledge | County dossier projection and organizer archive | Restricted views expose earned facts and practice receipts | Source trace. No fresh player-facing acceptance |
| Enemy foundations | Belief, exposure and finite capacity utilities | Graph modules and internal tests | No production opponent caller found | Fresh 121 graph tests and direct probe. The probe exposed pre-activation hazards |
| Multi-agency opponents | Planned police, intelligence, military and reactionary actors | No current campaign controllers found | No construction-to-receipt chain found | Source search only. No autonomous opponent play session |

The normal national path begins when the title's [New Game action](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-client/src/observer_title.rs#L323-L335)
emits `NewNationalCampaign`. The client [maps it](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-client/src/observer_io/runtime.rs#L975-L997)
to `RuntimeSessionPreset::NationalWorld`. The [backend](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/runtime_session/backend.rs#L214-L237)
captures the national catalog and creates its foundation. Its [campaign capture](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/economic_catalog/capture.rs#L118-L154)
includes organizer authority and the [material and organizer rules](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/economic_catalog/preset.rs#L40-L46).

The runtime [accepts organizer submissions and advances](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/runtime_session/backend.rs#L47-L77),
loads the pending commitment for the resolving period and [prepares a detached tick](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/material_runtime/runtime.rs#L762-L786).
The [Postgres transaction](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/material_runtime/runtime.rs#L859-L919)
writes tick and organizer rows before the [durable marker](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/material_runtime/runtime.rs#L945-L970),
then publishes. Reopening [restores the captured foundation and checkpoint](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/material_runtime/runtime.rs#L591-L631).
The organizer presents [actor-scoped practice receipts](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-client/src/organizer/presentation.rs#L462-L470).
Archive [filters county facts by grants](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/county_producer/dossier.rs#L531-L548).
This is a source trace supported by the scoped prior smoke below, not a fresh
native play session or acceptance of a national session.

## Delivery against the nine game tasks

“Design only” means the current path does not show the named behavior.
Related foundations also exist.

| Plan task | Delivery assessment | Present evidence and boundary |
| --- | --- | --- |
| 1. Empirical extractors | Design only | Generic reference-data tools exist. The search did not find the proposed wealth, trade and exhaustion tables. |
| 2. Seven wealth and imperial-rent equations | Design only | The older [imperial-rent rules](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-tick/content/rules/imperial-rent.bsl#L1-L33) and [household time](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-material-circuit/src/household_time.rs#L57-L94) are real, distinct work, not evidence for these seven equations. |
| 3. Two-stroke veil, deceptive dossiers and narrators | Design only | The [county Archive grants](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-persistence/src/county_producer/dossier.rs#L87-L99) filter facts at the receipt tick. They do not show the proposed veil, deception or narrator systems. |
| 4. Police and intelligence cells | Design only, with graph foundations | Dossier, capacity, exposure, backfire and induced modules exist. The search found no autonomous campaign opponent chain. See below. |
| 5. Military meta-cell | Design only | The search found no current military controller or decision-to-receipt path. |
| 6. Reactionary, warlord and opportunist actors | Design only | Existing graph utilities do not show the described actor dynamics and transitions. |
| 7. Prison pipeline and prison organizing | Design only | An older [penal-suppression rule](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-tick/content/rules/territory.bsl#L209-L219) zeros organization in penal colonies. The [organizer time consumer](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-tick/src/material_world/organizer_time.rs#L31-L102) is separate from the proposed prison pipeline. |
| 8. Party clock, dual power and endgames | Design only | [Practice identifiers](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-practice-contract/src/intent.rs#L88-L101) do not show executable verbs or these endgames. A bounded organizer transition does exist. |
| 9. Six screens and decision ceremony | Design only | The [five current surface IDs](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-client/src/decision_surface.rs#L13-L31) include an [OrganizerWorkspace](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-client/src/decision_surface.rs#L313-L325). The county Investigate action remains [sealed](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-client/src/decision_surface.rs#L276-L283). These are not the proposed six-screen ceremony. |

The national [material](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/content/scenarios/national/material-cycle.bsl)
and [organizer](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/content/scenarios/national/organizer-cycle.bsl)
cycles are actual campaign content. National organizer values are inquiry 2,
contact 2, contributor cap 8. [Michigan](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/content/scenarios/michigan/defines.toml#L8-L15)
has player 16, inquiry 12 and contact 8 hours. The
[national defines](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/content/scenarios/national/defines.toml#L367-L380)
use the `Designed` evidence class. They are not empirical claims.

## Enemy AI and pre-activation hazards

The graph exports opponent-relevant utilities, but current source searches found
no production construction, decision, commit/restart and visible-receipt chain
for an opponent. The search found no `AgencyCellKind`, `NsaSignals`, `CiaClandestine` or
`EdgeMedium` controller. The [OODA slot](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-tick/src/phase_order.rs#L128-L132)
is a schedule location, not an agent. The older
[`struggle/spark` rule](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-tick/content/rules/struggle-spark.bsl#L1-L24)
uses scalar repression in conformance/diagnostic context. The national capture
does not use it as an autonomous enemy. Useful player work can continue before
the team builds every proposed cell.

A disposable probe using the actual public Rust `APIs` found three behaviors to
resolve before connecting these components to an opponent:

A `Dossier` with two resolved nodes but no resolved edge reports the edge
unknown. After adding that edge to the underlying graph, `components(graph,
dossier.scope(), "coordination")` changes from two components to one.
[`scope`](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-graph/src/dossier.rs#L187-L196)
supplies node IDs, while [exposure](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-graph/src/exposure.rs#L84-L93)
traverses graph neighbors. If the intended belief boundary includes unknown
ties, a caller or representation must enforce it.

With one micro-unit available, a candidate costing one with expected yield
`-0.1` gets funding: `funded=1`, `declined=0`, remaining `0`. A fresh capacity
accepts replenishment of `-1` micro-unit and reports `-1` available.
[Yield admission and funding](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-graph/src/capacity.rs#L302-L338)
and [replenishment](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-graph/src/capacity.rs#L210-L219)
show why. Decide the permitted policy before wiring. This audit does not
assert that negative values are universally forbidden.

The allocator already checks the budget owner, positive representable costs and finite yields, uses checked
arithmetic and deterministic ordering. Candidate scoring, eligibility and
owner-node validation remain caller obligations. The search found no current production callers of these graph components in
the inspected Rust, BSL and captures. These are pre-activation hazards, not
shown live player information leaks. The probe used `rustc` with the
current graph and kernel `rlib` files. The observations above are its exact results.

## Immediate launch-check blocker

The [launcher](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/tools/run_observer_session.py#L674-L713)
requires `economy-status` schema 1, while the
[client producer](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/rust/crates/babylon-client/src/economy_status.rs#L117)
emits schema 2. The [test fixture](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/tests/unit/tools/test_run_observer_session.py#L1090)
mirrors version 1.

A database-free probe invoked the real
`_national_economy_status` with a mocked successful process response. It used
the same complete identity and scope fields for each version. The launcher
accepted version 1 and refused version 2 with `national economic snapshot has incomplete scope or
mismatched identity`.

Thus the green launcher tests do not cover producer/consumer
drift. This blocks the national **installation check**. It does not prove that
an ordinary windowed launch fails. This review made no repair.

## Verification and next work

Fresh checks in this session: `BLAS=1 mise exec -- cargo test -p babylon-graph
--locked --lib` passed 121 tests. `BLAS=1 mise run test:q --
tests/unit/tools/test_governance_mass.py tests/unit/tools/test_run_observer_session.py`
passed 151. `BLAS=1 mise run check:governance-mass` passed. This session did
not generate documentation. These checks do not qualify the GUI or national play.

The following hosted CI passed earlier. This audit did not rerun it:
[PR 1027](https://github.com/percy-raskova/babylon/pull/1027) head
`fd22ef661bc1c737edb56891686934e3862d59ea`,
[run 40130065614](https://github.com/percy-raskova/babylon/actions/runs/40130065614),
merge `26ab3d459`.

[PR 1037](https://github.com/percy-raskova/babylon/pull/1037)
head `c4afd4bde69ff63f4ab8d2577c6a5d282e129f32`,
[run 40615934193](https://github.com/percy-raskova/babylon/actions/runs/40615934193),
merge `473e4bcba`.

[PR 1042](https://github.com/percy-raskova/babylon/pull/1042)
head `68cb203c8478aec068f4505e8ea79f0f0c8eb4f1`,
[run 40811849095](https://github.com/percy-raskova/babylon/actions/runs/40811849095),
merge `69c6ea80f`.

Each cited run succeeded for its head. The inspected head
adds a dependency merge after `69c6ea80f`. PR 1042 reports a scoped Postgres
15-tick, restart and session smoke. This session did not run the database.
Those results are not current national or human-play acceptance.

**First:** Repair the launcher/client schema contract and add a producer-consumer
check. Run the finite national installation check. Complete PER-336 with an
observed player session and concrete usability findings.

**Next:** Use that evidence to scope a bounded [PER-292](https://linear.app/percy-raskova/issue/PER-292)
scene that gives the player a legible choice and consequence. Let a player
experience the loop before another broad architecture audit.

**Separately:** Treat [PER-355](https://linear.app/percy-raskova/issue/PER-355)
opponent activation as separate work. Decide belief and budget semantics. Trace
one opponent from construction through decision, restart and an intelligible
receipt. Include the probe findings in that admission.

**Later debt:** Track sustained national budgets in [PER-360](https://linear.app/percy-raskova/issue/PER-360)
and [PER-344](https://linear.app/percy-raskova/issue/PER-344) as open debt.
Bounded smoke does not prove sustained national performance.

Before implementing historical designs that prescribe a founding arrest or
terminal result, assess them against the live [Constitution 4.2](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/CONSTITUTION.md#L41-L47)
and its [non-predetermination rule](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/CONSTITUTION.md#L75-L78).
For example, the [porch design](https://github.com/percy-raskova/babylon/blob/9e49ff5dd88cbcfe7664baa5d1c1092c7cbf2e65/docs/gameplay/2026-10-25-porch-02.md#L362-L363)
prescribes an arrest after founding. Preserve the historical document, resolve
any conflict in the scoped governance process, and do not treat all fixed
Designed values as prohibited.
