# Exact graph lookup schema record — 2026-10-06

Part of PER-343 and PER-342. This repairs a measured reader failure within the approved PostgreSQL storage work. It changes no game mechanism, saved component rows, permission boundary or accounting identity.

Three live reader/recovery runs refused the first delayed delivery period when the complete graph reader hit its 120-second statement timeout. A plan captured immediately before the failing read showed separate campaign-wide name and type scans before membership expansion, with exact node/name conditions applied as a late join filter. Statistics represented earlier campaigns and estimated the newly inserted campaign at one row. The previously captured post-timeout plan was different and was insufficient to establish the cause.

An independent regression analyzes the earlier campaign, holds only test-owned statistics locks that permit normal inserts and reads, then creates and commits another campaign. The original query timed out at its five-second fixture limit; the control finished in 34.65 seconds and preserved the original failure. The revised views returned all 1,696 nodes in 26 milliseconds and all 8,800 binary64 attributes in 60 milliseconds, matching the live graph's exact ordered rows and bits. The GREEN control finished in 30.04 seconds. Both owned fixtures were cleaned up, and selected sources and the national lease remained unchanged during each run.

The node tuple and each referenced string are partial functions of their campaign and exact typed ID, enforced by primary keys. Dependent lateral subqueries with an OFFSET 0 boundary keep those keyed resolutions local instead of permitting a names-by-types Cartesian product before selection. They impose no row limit and preserve inner-join behavior, marker exclusion, duplicates, caller ordering and every value. The public observer wrappers remain unchanged. Full component authentication remains required to refuse missing or altered components.

A fresh PostgreSQL 17.11 transaction captured all four ACL variants using the unchanged bounded catalog query, then rolled back all DDL and temporary grants. Capture took seven seconds; verified owned cleanup completed in twelve seconds. Each variant still has 154 objects: exactly the two private graph views changed, with 152 unchanged objects, no additions or removals, and no changes to immutable fresh-schema fixtures. Published signatures come from this measured capture. Raw state, receipt, session protocol and organizer formats are unchanged by this repair. Only the two graph views and their source provenance signatures change; Archive worker vectors remain unchanged.

Formatting, strict scoped Clippy, all four BSL sentinels and shell syntax checks passed. Targeted Vale found no errors in 201 changed prose lines after repairing the three initial findings; the complete historical document retains unrelated findings. The broader six-control PostgreSQL recovery/corruption gate passed all six tests in 259.20 seconds, with the same source bytes and unchanged absent national lease; the wrapper completed in 336.48 seconds including bootstrap. Uninterrupted and restarted delivery histories preserved the expected distinct downstream onset periods five and seven. Exact fixture, volume and template cleanup was verified. National timing, memory, save growth, sustained activity and actual play remain unqualified; the scoped query measurements cannot substitute for them.

The following payload was produced by tools/generate_ceremony_message.py::build_ceremony_message from the exact captured object changes, without staging or changing Git's index.

test(baselines): pin exact ID graph views after the stale-statistics regression

| file | status | rows (old→new) | changed cells | max \|Δ\| |
| --- | --- | --- | --- | --- |
| rust/crates/babylon-persistence/src/fixtures/current_schema_census.txt | modified | 154→154 | 2 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_reader_census.txt | modified | 154→154 | 2 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_observer_census.txt | modified | 154→154 | 2 | n/a |
| rust/crates/babylon-persistence/src/fixtures/current_schema_reader_observer_census.txt | modified | 154→154 | 2 | n/a |

Baselines: blessed(exact-graph-lookups-2026-10-06)
