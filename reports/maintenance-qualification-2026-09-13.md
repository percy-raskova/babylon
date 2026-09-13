# Wayne maintenance qualification — 2026-09-13

<!-- Vale: PostgreSQL is the database project's proper name wherever marked below. -->
This is partial PER-30, PER-32 and PER-293 work. The four maintenance cases pass
the native exercise and real-source <!-- vale Vale.Terms = NO -->PostgreSQL<!-- vale Vale.Terms = YES --> qualification. The implementation
adds one bounded maintenance dependency. It does not complete the productive and
distributive circuit, broader Gate 3 or Gate 4 acceptance, or player actions.

## Admitted source and designed experiment

The provider uses Wayne County's pinned 2024 private repair-industry row.
It has NAICS 811310, ownership 5, aggregation 78, size 0, annual quarter A,
and an empty disclosure flag. The observed row has 122 establishments and 1,480
annual-average jobs. Those observations do not specify the modeled crew.

The source CSV has SHA-256
`1382b5821ac95ca6f344e50f76b6846f76f841b0bc32ebf69ee8fbadc545481a`.
The extraction artifact is
[`wayne_maintenance_industry_2024.json`](../src/babylon/data/reference/economy/wayne_maintenance_industry_2024.json).
Its checked SHA-256 is
`1a6bf597ac4f0a01f6467bb398e71aec06527ece5671286eb900c7d1e03ae38f`.
The extraction was rerun against the pinned CSV during this qualification.

The provider is `owner-26163-81`. Its consumer is
`26163-31-33-metal_parts`. All service coefficients, opening stocks, and modeled
workers use the Designed evidence class. The common consumer stock is 2,560 kg of metal stock,
with 16 batches enabled for the opening period. The four cases vary provider
employed/reserve between 1/0 and 0/1, and opening metal-parts spares between
256 kg and zero.

One whole job uses 1 kg of parts and 10 current labor-hours. At most 16 jobs
complete per period. Each enables one consumer batch in the following period.
Unused opening service expires. New service replaces it.

The finite local replenishment order is 256 kg. Its credits occur after maintenance.

## Retained statewide qualification

This change carries forward the existing road and commodity qualification
through exact dependency equivalence. It does not claim a new road extraction,
new shortest-path calculation, or new supplier selection. The search found no original full
graph, matrix, or temporary matrix-authoring script.

Git commit `41844cf72a29e8b9a588696cc25d24b216b88ea3` retains the original
defines and captured inputs. Their digests matched the old manifest exactly.
After excluding only `SCHEMA_VERSION` and the newly added `maintenance` table,
every preexisting parsed parameter matches. The type-preserving canonical
JSON of those parameters has SHA-256
`61f311790eb37a5b585dd01c87e398c881becac15500fd3d4f607d29953af0c1`.

Only three defines bindings advance: the manifest, commodity qualification,
and physical capture's `terminal_source_pins`. Both compressed artifact hashes
then advance in the manifest. Every other decoded field stays the same. Counts remain at 397
owners, 233 processes, 581 orders, 233 finite final demands, 83 terminals, 7,085
edges, and 1,245 capacity groups. Maintenance adds its provider and local order
after this unchanged statewide selection.

| Input | Previous SHA-256 | Current SHA-256 |
| --- | --- | --- |
| Defines | `bc6a0c80eb1e7781eb36d2e3f14fc7643794e6a0721212d129c18ebd04af3037` | `62108d7ac8ffd9e751e236dd4e20ed428f30a118c152514f9fb7b23e14c5eea4` |
| Qualification `gzip` | `1c7de1b928822062e9919bdc28a3f86967e496f206088f569c62012c3d9e3b28` | `ac8717c1ece373d9a4409e655107eab3791b55d4443f6c9aa6ff5b400583d5bc` |
| Physical `gzip` | `736bb9d368cd05eca93e521b51051e3cfee795409dfa890b55c586581d63b3a7` | `f61560f1ebc9cefcc18118fd0feac030c48be79d360dd9b3b90f382f776c0484` |

The original graph digest remains
`d6ec26e347bfabcd3c86c3f9e784c7d9fbb4d32e8a7cb76ae724e53fdc745550`.
The original matrix digest remains
`66df8effd50e25fdf5d557ae5a1ae8dcfe7ffda786614adf966ff45ea79945c4`.
The amended terminal pin map is explicitly not claimed to reproduce that
unavailable matrix's bytes. Current runtime digest checks remain unchanged.

The task-only [recapture script](test-results/per293-observer/tooling/recapture-maintenance.py)
authenticates the pinned before-state and proves the complete parameter equality.
It checks the roster digest, retains exact before/after bytes, and verifies the
two allowed decoded capture changes. The
[provenance record](test-results/per293-observer/source-recapture/dependency-equivalence.json)
preserves original terminal pins and all output hashes. Direct negative
controls detect a changed transport parameter and a corrupted physical byte.
Local storage retains these linked task artifacts outside the published tree.

## Verification boundary

The four-case synthetic network test has passed through the BSL material cycle,
captured content, checkpoint reconstruction, source removal, and failed commit
retry. It verifies first-period jobs of 16 versus zero, next-period consumer
output of 960 versus zero kg, and later recovery in the shortage cases.
Its extra synthetic buyer means it does not prove an exact 60 kg local
replenishment witness for the real network.

The core checks also cover service expiry, checked whole-job debits, idle-firm
work requests, and rehiring. A late failed close cannot publish computed jobs
or their inventory debits. The replay failure check uses the existing
publication callback. The separate live <!-- vale Vale.Terms = NO -->PostgreSQL<!-- vale Vale.Terms = YES --> check below also exercises a
failed database transaction.

Six maintenance client checks passed for readings, comparison, service
navigation, the new menu family, and restricted disclosure. Evidence and
accounting checks keep maintenance parts and labor separate from production
and merchant handling. Completed zero remains distinct from absent evidence.

## Native maintenance witness

The final observer opened all four separately saved maintenance campaigns at
period 3. The [session log](test-results/per293-observer/logs/native-final-catalog-projection-fixed.log)
records successful baseline reads at 06:27:49 UTC and both constraints at 06:42:41.
Parts-shortage reads succeeded at 06:43:56 and labor-shortage reads at 06:44:40.
The [campaign record](test-results/per293-observer/native-current/campaigns.json)
pins their separate identities. Captures span 1366×768 and 1920×1080.

| Native result | Baseline | Labor shortage | Parts shortage | Both |
| --- | ---: | ---: | ---: | ---: |
| Period 1 completed jobs | 16 | 0 | 0 | 0 |
| Period 2 consumer output | 960 kg | 0 kg | 0 kg | 0 kg |
| Period 3 consumer output | 0 kg | 960 kg | 960 kg | 960 kg |

Either shortage prevents first-period service. All four consumers still use
their seeded opening service in that period. Completed jobs enable the following
period's output. The period-3 reversal follows recovery in the shortage cases
after the baseline used its material buffer. This does not erase lost period-2 output.
The provider receives 60 kg from its finite local replenishment order after
maintenance, so those parts cannot repair the same period's shortage.

Representative captures show [provider inputs and jobs](test-results/per293-observer/native-current/final/1920-maintenance-baseline-provider-p1.png),
[delayed output](test-results/per293-observer/native-current/final/1366-maintenance-base-both-p2-confirmed.png),
[labor recovery](test-results/per293-observer/native-current/final/1920-maintenance-base-labor-p3-recovery-ready.png),
and [parts recovery](test-results/per293-observer/native-current/final/1920-maintenance-parts-consumer-p3-recovery.png).
The provider's Sources reading distinguishes 1,480 observed annual-average jobs
from the Designed crew and service quantities. Restricted preview withholds
material accounts at [1366](test-results/per293-observer/native-current/final/1366-maintenance-known-circuit.png)
and [1920](test-results/per293-observer/native-current/final/1920-maintenance-known-circuit.png).

The native **Wayne maintenance / Both constraints** button created a ninth
campaign, `c81094f6-99c5-41d6-80ba-7cbfc645241e`. Three native Advance
operations produced 960, zero, and 960 kg. The period-2 reading shows 60 kg
available spares, 16 completed jobs, and service enabling period 3. The final
[recovery capture](test-results/per293-observer/native-current/final/1920-native-new-maintenance-both-p3-recovery.png)
shows actual output and Archive verified through period 3. Existing saves remain.

That new campaign also reopened in a separate native process, PID 2389000.
It reached Ready at viewed/durable period 3, with Archive verified through
period 3. The final 1366×768 inspection showed 960 kg of Wayne metal-parts output.
It also showed 6 employed and 6 reserve workers, 16 consumed service batches,
and 44 kg of provider parts.

The prior process, PID 2270950, reported Closed with `failed=false`. The
[fresh-resume record](test-results/per293-observer/native-current/native-created-maintenance-fresh-resume.json),
[log](test-results/per293-observer/logs/native-maintenance-fresh-resume-final.log),
and [capture](test-results/per293-observer/native-current/final/maintenance-fresh-process-output-p3.png)
preserve these readings. The game remains open at the recovered producer.

## Full projection and persisted verification

Native opening originally found a full-observer projection failure: the coverage
check counted every non-production site as a merchant. A maintenance provider
raised that count to 167 against 166 merchant accounts. The repair explicitly
counts Wholesale and Retail, preserving the separate Maintenance role.

The [RED regression](test-results/per293-observer/logs/maintenance-full-projection-red.log)
failed at foundation. The same four-case full-projection regression passed in
15.92 seconds after repair. It checked foundation and three periods, provider
identity, observed jobs, merchant coverage, and zero and positive completed work.
The [GREEN/build log](test-results/per293-observer/logs/catalog-projection-final-green-build.log)
also records scoped client/persistence Clippy and the final native build.

The required `statewide_qualified` [run](test-results/per293-observer/logs/postgres-statewide-final.log)
passed all four original campaigns through 16 persisted periods. Its maintenance
test then refused an invalid failure-injection setup: adding a trigger changed
the schema census before the intended failed tick. This complete invocation
returned 101. This record preserves the failed result.

The repaired test holds a transaction-level SHARE lock on the existing commit
marker table. Schema and tail reads still pass. The final marker INSERT
hits the writer's existing five-second lock timeout after candidate writes.
The test requires SQLSTATE `55P03` and the exact lock-timeout error.
It also requires unchanged live graph/material/hash/tick/tail/sink, no partial
rows in all 26 tick tables, and an unchanged catalog tail. Releasing the lock allows deterministic twin retry.

The focused [maintenance rerun](test-results/per293-observer/logs/postgres-maintenance-marker-lock-final.log)
passed all four real-source cases through three persisted periods in 496.09 seconds.
It also proves current-format reads, held history, restricted preview, captured
source independence, and checkpoint restart. Harness cleanup and the outer
process returned zero. The [task-only harness diff](test-results/per293-observer/tooling/run-maintenance-postgres-focused.patch)
changes only its relocated root path and test filter. Ownership, admission,
deadlines, bootstrap, and cleanup remain the repository's existing harness.
The unchanged original four-case result above remains separate evidence.

The full Rust publication checks passed before the final scoped repairs.
The [observer record](observer-qualification-2026-09-13.md) gives those results,
the later targeted checks, client/Archive integration, and native performance.
The [build provenance](test-results/per293-observer/native-current/build-provenance-catalog-projection-fixed.json)
pins the exact source inventory and executable hashes. All `test-results` links
refer to retained local evidence, which is not included in the public repository.

Payments, household consumption, recurring demand, broader organizational
struggle, and executable political interactions remain outside this delivery.
