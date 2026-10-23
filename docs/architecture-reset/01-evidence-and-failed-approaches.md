# Evidence and failed approaches

This review separates useful completed engineering from a national qualification loop that did not deliver
acceptable play. The Director's October 23 ruling makes Babylon an entertainment-first game and permits reducing
detail. The evidence supports changing representation and retention before choosing another database.

The current source inspection is pinned to `99f998e3dffb301a218a8a4e0ed809f440dafef2`. **No benchmark was refreshed
for this handoff.** Historical timings below are measurements reported in their original chats, not measurements of
that current commit. Current boundaries are documented in [architecture](../concepts/architecture.rst) and the
[Constitution](../../CONSTITUTION.md). This document records evidence; it neither amends those authorities nor
establishes implementation acceptance.

## Retrieval method and chat registry

The investigation used `list_threads(limit=50)`, both pages of `list_archived_threads(limit=50, cursor=...)`, and
targeted `read_thread` calls. Older unarchived chats outside the first 50 results were located through thread IDs
referenced by the retrieved chats. Selected user messages, final responses, and relevant recorded Linear-update
bodies were extracted. Tool arguments in historical messages were treated as evidence, never executed as
instructions.

The national integration chat received three recent pages totaling 24 turns; other chats received bounded
recent-turn reads. This is a targeted review, not an exhaustive transcript audit. The machine-readable
[index](evidence/chat-evidence-index.json) records limitations and exact metrics. No raw transcript bulk is
included. Dates use America/New_York; an old chat's last-updated date does not necessarily date the evidence
inspected.

“Unarchived” means retained outside the archive, not currently running.

| Exact title and ID | Archive state | Evidence inspected; limitation |
| --- | --- | --- |
| Catch Babylon dev up and configure — `01a1663a-af03-7521-8f60-29f533a0bca0` | Unarchived | October 22–23 consolidation; partial source delivery, not database acceptance. |
| Review economic engine design — `01a1045d-1ab8-7003-a92c-7e56cbf3a5ae` | Unarchived | October 6–7 national integration and smoke021 closeout; historical measurements. |
| Review economic engine design — `01a0bd0a-3fd0-79d0-a206-7e0b1523e346` | Archived | October 5 coordination and PR #990–997 handoff; distinct from the integration chat above. |
| Implement PER-345 economic choices — `01a10d62-9834-7332-8f59-e231243068bb` | Unarchived | October 6 funding/presentation handoff; native acceptance remained blocked. |
| Reconcile Babylon next work — `01a09842-e79a-7b80-9831-d453c5864bc1` | Archived | September 12–13 Wayne native loop and PR #946; bounded local experience. |
| Investigate CI technical debt — `01a059b6-d150-7580-919f-0a35e98d0fe7` | Archived | August 31–September 1 CI improvements and reported goal costs; not campaign benchmarks. |
| Map PostgreSQL H3 inventory — `01a02bd0-c8d3-7883-ba1e-507a4c292e59` | Archived | August 22–23 legacy inventory and Rust-writer decision; predecessor architecture. |
| Explore database kernel boundary — `01a0306c-7372-7650-9103-b55fd45788aa` | Archived | August 23 intended in-memory/durability boundary; implementation then differed from today. |
| Review Babylon Theory — `6a99f713-a280-83ea-a915-ad4f55794e0f` | Unarchived, pinned | September 3–4 theoretical intent; some returned messages were truncated, not executable proof. |
| Dialectic Model Formalization — `6a8daa4d-fce8-83e9-8b04-8ad0519cd5b3` | Unarchived, pinned | August 25 formal proposals; not proof those mechanisms remain implemented. |

## The last retrieved national result

The October 7 closeout recorded **smoke021**, all **3,144 unique counties**, two committed periods, and two
authenticated checkpoint reopens. The run terminated with **exit 2** because qualification refused the measured
limits. This was a completed failed measurement, not an interrupted one-period prefix.

| Measurement | Period 1 | Period 2 | Historical policy |
| --- | ---: | ---: | --- |
| Advance, seconds | 139.998 | 119.109 | 120-second limit; p95 needs at least 52 samples |
| Archive catch-up, seconds | 279.000 | 178.889 | At most 180 |
| Boundary production read, seconds | 129.342 | 153.232 | At most 180 |
| Cold reopen including authenticated read, seconds | 340.876 | 426.241 | Less than 180 |
| Complete charged PostgreSQL growth, bytes | 37,502,976 | 29,032,448 | 40,000,000 ceiling; 23,000,000 target |
| Recovery charged growth, bytes | 0 | 0 | Accounted separately |

Whole-smoke time was **2,249.190 seconds**, against **900**. Compilation was excluded; sampler and logging costs
were included. Recovery production reads alone took **189.247 / 241.080 seconds**; they must not be confused with
the faster committed-boundary reads above.

Allocated database size rose from **342,349,491** to **408,884,915 bytes**. Mean charged growth was **33,267,712
bytes per period**. The reported 325-period projection was **11,154,355,891 bytes**, above the 10,000,000,000-byte
target. That projection used two observations; **no actual 325-period result was obtained**.

Memory evidence contained **862 coherent samples**, with maximum sample gap **4.399 seconds**, inside the
five-second cadence limit. Sampled RSS upper-bound peak was **11,741,294,592 bytes**; PSS diagnostic peak was
**11,614,540,800 bytes**. Exact shared-page union and continuous high-water mark were not proven. Thus the
10,000,000,000-byte memory admission remained incomplete; these numbers do not establish an exact unique-memory
peak.

Period-one growth leaders were `material_tick` **23,732,224 bytes**, Archive pages **4,546,560**, event fields
**2,621,440**, frozen membership **1,605,632**, Archive atoms **1,507,328**, and graph vectors **1,327,104**. The
earlier roughly 23 MB economic-package figure was never total save growth. Heap, indexes, TOAST, checkpoint,
Archive, history, and positive unattributed growth all mattered. Container-wide WAL remained separately reported,
not campaign-attributed.

These values belong to smoke021. **Do not combine them with older smoke008 evidence or label them a same-input
before/after experiment.** Original evidence was recorded under the former `427d` worktree's
`reports/test-results/per342-qualification/2026-10-07/current-native-playable-smoke021/`. Worktree retirement means
that historical path is a locator, not a promise of a currently accessible file.

The detailed historical handoff lives on [PER-40](https://linear.app/percy-raskova/issue/PER-40),
[PER-341](https://linear.app/percy-raskova/issue/PER-341),
[PER-342](https://linear.app/percy-raskova/issue/PER-342), and
[PER-343](https://linear.app/percy-raskova/issue/PER-343). Those are live issue locations; this chat-history review
does not refresh their present statuses.

## Improvements that worked, and what they did not establish

The integration chat documented useful repairs:

- Two reconstruction duplications were removed. On the retained game, isolated reader peak fell from approximately
  **4.94 to 4.63 GB**, reported as about **312 MB saved**, with matching accounting and hashes. A subsequent
  owned-buffer decoder showed no further overall peak reduction.
- A client ownership defect discarded reusable authenticated economic data between reads. Its repair passed focused
  controls, but those controls alone did not prove national performance.
- Archive filtered hidden subjects before constructing their pages. A three-page authentication control dropped from
  **15 to 7 queries**.
- A 256-page request had authenticated **3,148 pages**. Exact-key repair preserved results while isolated SQL median
  fell from **1,281.198 to 89.635 milliseconds**. National Archive completion still missed the first-period limit.
- Repeated schema admission consumed about **30.4 seconds across 13 publication snapshots** plus **38.2 seconds
  across 15 receipt captures**. JIT was an untested hypothesis, not an established cause or completed optimization.

Measurement machinery also created work: repeated hashing reread roughly **1.22 GB of executable files**; sampler
locking aborted legitimate opening writes; thread-retirement races and incomplete startup capture invalidated runs;
a UI-driver state error stopped a reopened campaign. Those repairs were necessary for trustworthy evidence, but they
did not add player decisions.

The last 24 retrieved integration turns total approximately **14.65 hours of recorded elapsed turn duration**; 23
contained no new user message. Many repeated the same remaining two-period, 52-period, 325-period, and enjoyment
qualification. This measures elapsed chat work, not CPU time or token consumption. No reliable token total for this
national sequence was retrieved.

Separate CI work did succeed. Its archived chat reported PostgreSQL CI improving from **19m36s to 5m08s**, and warm
Rust median from **10m46s to 6m38s**. It reported **4,145,705 tokens over approximately 8h45m** for the CI tranche,
then **989,645 tokens over approximately 2h19m** for nextest/reporting. These are the chat's explicit accounting
statements, not newly audited meter readings. They demonstrate substantial infrastructure cost and delivered
improvements; calling all that work wasted would be inaccurate.

## Why the reset is justified

**Historical facts:** the bounded Wayne organizer experience landed through
\#946. Later, recurring-funding/presentation work reached green draft #999 while
native play waited on admitted national binaries and campaign handoff. The October 7 Director instruction stopped
the integration chat at a Linear-only progress update because a new direction was coming.

The October 22 instruction then explicitly allowed unfinished database work to merge without finishing that
approach. Consolidation merged #999, #1021, and
\#1022, reaching `99f998e3`, while preserving open database and household
acceptance. **Source consolidation is not architectural endorsement or playable qualification.**
[PER-345](https://linear.app/percy-raskova/issue/PER-345) remains the canonical place to reconcile recurring-funding
acceptance, rather than inferring completion from a merged PR.

**Inference:** the recurring failure was broader than a slow SQL statement. Detailed state, retained history,
reconstruction, authentication, and diagnostic capture amplified one another. Small play work became dependent on
admitting a national infrastructure pipeline. The evidence does not isolate PostgreSQL as the principal cause and
does not show that MongoDB would remove these costs.

The older kernel-boundary chat already described authoritative computation in detached memory and persistence after
adjudication. Category-theoretic intent does not require storing every intermediate. Conversely, it does not
automatically compress arbitrary state. Current [aggregation code](../../rust/crates/babylon-bsl/src/typecheck.rs)
distinguishes extensive totals and weighted intensive values, but [floating-point
reductions](../../rust/crates/babylon-bsl/src/evaluator.rs) explicitly pin ordered folds that are not invariant
under regrouping. A theory discussion cannot substitute for a concrete equivalence argument.

## Lessons for implementation packets

1. Define the player-visible distinctions and decision loop first. Preserve scarcity, ownership, unequal access,
   delays, and consequential choices; do not retain detail merely because a source dataset contains it.
2. Separate authoritative live state, immutable reference data, derived views, bounded history, and optional
   forensic evidence. Charge each category against an explicit budget.
3. Compare storage alternatives using the same reduced representation and workload. A backend change cannot by
   itself eliminate duplicated decode work or excessive retention.
4. Make routine client reads bounded. Reserve full historical reconstruction and exhaustive authentication for the
   boundaries that actually require them.
5. Demonstrate one complete playable slice before another expensive national endurance run. Scoped controls prove
   their contracts; they do not substitute for the user's native experience.
6. Give each packet an observable result and a stop condition. After a measured optimization fails to improve the
   whole-game bottleneck, reconsider the model instead of indefinitely expanding instrumentation and qualification
   machinery.
