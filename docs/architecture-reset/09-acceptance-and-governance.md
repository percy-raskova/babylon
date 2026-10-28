# Acceptance, authority and evidence

**Proposed implementation policy, 23 October 2026.** The Director selected the SQLite direction and game targets in
this conversation. This document does not itself amend the Constitution, change Linear scope, change executable
contracts, or qualify any build. Preserve that distinction in implementation reports.

## Authority changes required

The current [Constitution](../../CONSTITUTION.md), Article V, explicitly says Postgres owns durability and that
SQLite is never mutable campaign state. The live [architecture](../concepts/architecture.rst), [North
Star](../../NORTH_STAR.md) and repository instructions reflect that boundary. A production SQLite cutover therefore
requires a targeted governance change; a new mathematical primitive is neither needed nor authorized.

Propose the following replacement meaning for Article V's storage-specific paragraph:

> Publication of a completed economic period occurs only after detached adjudication. One Rust campaign owner
> commits the current world, required causal registers, accepted-input consumption, choice and player receipts,
> knowledge changes, and durable projection work as one atomic SQLite transaction. The durable tick advances only
> after the transaction acknowledges it. Command acceptance and bounded nonmechanical service operations may commit
> independently under their declared contracts; they cannot advance the tick, adjudicate effects or grant unearned
> knowledge. Pinned reference artifacts remain immutable inputs. Historical engineering detail may be bounded under
> the declared retention contract; current causal state, permanent player history, required choice evidence and
> deterministic replay inputs must remain sufficient for their declared consumers.

This is proposed wording for Director review, not a new amendment number or ratification. The final approved text
may be edited without weakening its behavioral commitments. Keep the current detached working-copy requirement,
next-period intent boundary, native hyperedges, immutable geography, exact choice receipts, deterministic identity
and explicit errors.

The Gate 3 name **“PostgreSQL/H3/Archive decision-loop slice”** also names the old backend. Propose renaming it
**“Durable campaign/H3/Archive decision-loop slice”** wherever its governed identity is repeated. Keep its
decision-loop and Archive requirements; do not close the gate by renaming it. Ratification must cover that exact
naming change and its machine-readable references.

### Live records to update during implementation

| Record | Required disposition |
| --- | --- |
| Constitution Article V and the governed Gate 3 label | Approved narrow amendment; no broader theory rewrite |
| NORTH_STAR.md | New runtime/turn targets, retained-data policy and player-first acceptance |
| docs/concepts/architecture.rst | Replace the live storage/read/Archive description after source proves it |
| AGENTS.md target and ai/mantras.yaml | Concise current authority and orientation, without copying this dossier |
| Current persistence and qualification contracts | New explicit format/policy identity; incompatible inputs refused |
| Linear PER-40, PER-337, PER-341–345 and relevant dependencies | Reconcile with actual scope; keep partial delivery distinct from acceptance |
| Historical ADRs, saved reports and old qualification policies | Preserve unchanged; record scoped supersession in a new ADR if authorized |

Use `mise run adr -- search "<topic>"` and `show` for exact decision lookup. Do not bulk-read the ADR index or mark
old decisions superseded without naming which requirements change. Relevant families include ADR220/221 persistence
authority, ADR248 choice contracts, ADR257 period semantics, ADR261 material invocation, ADR278 save footprint,
ADR280 qualification, and ADR281–284 storage/Archive encodings. A family reference is a lookup guide, not a claim
that every clause in that ADR is superseded.

The official old/new authority mapping belongs in the approved amendment/ADR. This dossier remains the handoff
proposal; it must not become an alternative constitution.

## Targets and defaults

All sizes below use **decimal bytes** unless a codec/chunk limit explicitly says otherwise. The game interval
remains one **28-day tick**, thirteen ticks per model year. No weekly substep simulation is introduced.

| Measure | Redesigned game target | Prior inspected policy / interpretation |
| --- | --- | --- |
| Target computer | 16 GB desktop | User-selected target class; a benchmark must record exact CPU/storage/OS |
| Combined running-game memory | ≤4,000,000,000 bytes | v6 allowed 10,000,000,000; neither is a measured current success |
| Ordinary advance, durable save, required briefing | ≤30 seconds | v6 p95≤120 seconds, aim 60–90; old allowance is not the new target |
| Cold open to actionable player view | ≤30 seconds | **Proposed dossier default**, using the same usability ceiling; v6 allowed 180 |
| Normal subject selection/history page | ≤1 second warm; ≤2 seconds cold | **Proposed dossier defaults** for bounded reads, not a whole-world export |
| Charged retained growth per committed period | ≤10,000,000 bytes | North Star ambition; v6 allowed 40,000,000 and targeted 23,000,000 |
| Thirteen-period charged growth | ≤130,000,000 bytes | Includes checkpoint retention and metadata |
| Fifty-two-period charged growth | ≤520,000,000 bytes | Actual run required; no extrapolation credit |
| 325-period charged growth | ≤3,250,000,000 bytes | Plus opening; retain 10,000,000,000 total as a secondary ceiling |
| Recent technical detail | Latest 13 periods | Proposed retention default, not permission to prune causal state |
| Historical checkpoints | Permanent opening + latest 2 completed 13-period checkpoints | Current snapshot is always complete and separate; not unbounded yearly snapshots |

Opening size must be measured separately and explained by retained content/state. Do not put a corpus into a
campaign merely because it is immutable. Capture only the inputs required to reproduce the selected world and cite
the external research source. Game assets and optional diagnostic archives are separate accounting categories, not
places to hide required save data.

For the two-period smoke, both advances must meet 30 seconds. For the actual 52-period window, report every advance,
maximum, median and p95; an ordinary advance above 30 seconds is a target failure, even if p95 passes. A
deliberately requested historical replay or diagnostic export is not an ordinary advance and has its own measured
latency. Do not move action-critical report preparation into that exception.

The proposed 1/2/30-second defaults can be changed by an explicit design decision before a run. Freeze the chosen
policy in that run's evidence. Changing a limit afterward never relabels an old result.

### Retained storage versus transient work

Retained growth includes current state, referenced chunks, history, earned reports, knowledge metadata, indexes,
checkpoint rotation and allocated database pages. Include required sidecars in retained totals. Charge positive
growth by component/boundary; do not cancel a new checkpoint's cost against deletion of an old one to manufacture a
passing period.

Report WAL generation, peak WAL allocation, temporary files, export copies and database free pages separately. A
routine checkpoint may make WAL reusable; do not report only a freshly vacuumed/exported file as if it were the
actual playing save. Conversely, avoid adding the same bytes twice through nested totals. Provide both physical
allocated bytes and logical retained payload bytes.

The 10 MB target is demanding and unproven. If chunk rewrites or checkpoint rotation exceed it, show the responsible
component. Do not silently switch to average-only accounting, relax the target to 40 MB, or assert that SQLite
solved it because a compressed blob is small.

## Minimum correctness scenarios

| Scenario | Required observation |
| --- | --- |
| Repeat identical admitted inputs | Same canonical state, ordered effects and identity under the new format |
| Fail during judgment | Published state, period, knowledge and durable command consumption unchanged |
| Fail before transaction commit | No partial tick visible; pending accepted work remains retryable |
| Commit succeeds but acknowledgement is lost | Reopen/reconcile returns the committed result; no second execution |
| Duplicate command nonce | Same request/result or a specific conflicting-payload refusal |
| Changed installed BSL/BSCN/TOML | Existing save uses captured content; new campaign captures a new identity |
| Unknown schema/build/codec or corrupt chunk | Specific refusal; no stale fallback or automatic rewrite |
| Current restore at old and aged saves | Reads bounded current roots/pending indexes, not every historical period |
| Shipment/claim crosses checkpoints | Arrival/settlement occurs once at the right period with conserved accounts |
| Household poverty counterexample | Aggregation cannot spend another household's cash or erase unmet needs |
| Shared household/organizational time | Aliases and partners cannot supply the same hours twice |
| Late/backdated knowledge grant | No disclosure before actual acquisition; current grant cannot rewrite past knowledge |
| Expired/consumed contact product | Cannot be reused; historical record remains inspectable |
| Historical report retained past detail eviction | Original observed/acquired periods, source, citation and content remain available |
| Interrupted retention/export | Last durable state remains openable; no dangling referenced chunk |
| Missing or conflicting mod definitions | Rejected before authoritative campaign publication |
| File/package enumeration shuffled | Resolved content and execution order are unchanged for the same admitted selection |

Preserve choice receipts and their selected/unselected alternatives where the Constitution requires them. Retention
of other receipts is governed by actual causal/player consumers, not their name. Validate old and current knowledge
separately; a scoped reader must never obtain provider-private accounts through a diagnostic shortcut.

Tests must assert behaviors, not merely match the new implementation's serialization. Include independent totals and
counterexamples. If regrouping changes floating-point order, exact old-byte parity is not assumed. A purposeful new
representation/model version needs its approved ceremony and explicitly retained behavioral contracts.

## Performance procedure

1. Record exact source commit, executable digest, content/package hashes, seed, county roster, policy hash,
   hardware, build mode and cold/warm condition. Collect executable identities once; do not repeatedly hash gigabyte
   binaries while sampling.
2. Identify every game role: native client, runtime/worker, SQLite cache and any helper actually needed during play.
   Compilation and test harnesses are separate. Do not report engine-only memory as combined game memory.
3. Use the existing measurement tools where applicable, adapting their PostgreSQL-specific role assumptions. Avoid a
   parallel policy/reporting framework. Sample no slower than 250 ms during the short witness and record gaps and
   sampler overhead. Longer runs may use the same interval if measured overhead remains negligible; reduce
   instrumentation work rather than silently weakening evidence.
4. Report sampled concurrent memory and per-process high-water evidence honestly. A sum of RSS is a conservative
   sampled bound that can double-count shared pages; it is not an exact simultaneous peak. Passing the conservative
   bound is sufficient. If it fails, use sound shared-page accounting or reduce usage; do not subtract guessed
   shared memory. Report GPU memory separately.
5. Start the ordinary advance timer when the accepted player advance begins. Stop after commit acknowledgement and
   the required briefing/report are usable. Report judgment, encoding, commit and projection subphases without
   substituting one for total latency.
6. Measure scoped navigation independently from complete exports. Instrument bytes/chunks/entities visited so
   bounded work can be inspected, not just inferred from a fast sample.
7. Capture retained allocation before/after actual commits and checkpoint/retention boundaries. Preserve partial
   results and the exact failing phase on interruption.

Do not run a heavy national benchmark merely to validate documentation. During implementation, small controls
precede the two-period smoke; the smoke precedes 52 periods; actual 325-period qualification follows the shorter
passing window. One failed result produces a bounded diagnosis, not an unattended cycle of slightly different long
runs.

## Player acceptance

Provide a bounded organizer session that exposes:

- a comprehensible local need and the evidence the organization actually has;
- a choice between immediate local work and slower remote solidarity using real goods, money and finite time;
- a visible cost, durable acknowledgement, subsequent consequence and preserved receipt;
- at least one constraint that changes the viable choice, rather than a cosmetic variation;
- understandable county/organization relationships without requiring the player to read a national ledger.

The Director assesses comprehension and enjoyment. Record the tested scenario and observations; do not infer
enjoyment from automation, accounting parity or a screenshot. A useful local loop can be tested before long-run
national qualification, while clearly retaining the national acceptance gap.

## Documentation-only verification and publication

For this dossier, validate file inventory, relative links, JSON/TSV syntax, quoted source identities, packet
dependencies, commands and current/proposed labels. Run only targeted Markdown and Vale checks on these files; do
not generate Sphinx or Rust documentation. The documentation author must report any unavailable checker rather than
substitute a broad build.

Before a future implementation PR claims completion, check exact-head required CI, review threads, source/contract
drift and the relevant acceptance evidence. A partial packet uses `Part of PER-N`; `Fixes PER-N` requires the
issue's full acceptance. Source consolidation alone never proves playability.

This package deliberately does not pick an amendment number, invent a new Linear issue, update historical run
results or grant merge authority. Those records are resolved against live project state at their actual boundary.
