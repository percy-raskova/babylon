# 04 — Babylon's current state, costs and boundaries

**Status: source investigation, with proposed changes labeled.** Source identity:
`99f998e3dffb301a218a8a4e0ed809f440dafef2`. This analysis reads implementation and preserved reports; it does not
claim a new benchmark, playable qualification or an approved replacement architecture. The Director's
entertainment-first ruling governs the proposed reset. See [the data contract](05-data-and-model-contract.md),
[runtime proposal](06-target-runtime-and-sqlite.md) and [history proposal](07-history-replay-and-archive.md).

## What actually happens

Babylon already judges its world in Rust memory. PostgreSQL supplies durability, historical projections and
database-enforced reader permissions. The next period is not computed by issuing economic SQL updates. Replacing
PostgreSQL while preserving the current reconstruction and evidence contracts would preserve substantial CPU, memory
and history growth.

The national source capture supplies county identities, industry cohorts, resident workforce, households, transport,
trade, world population, authored policies and rules. `NationalSources::admit` reconstructs a typed opening from
captured bytes; `EconomicOpening::compile` makes the engine rows. Opening admission also regenerates and checks
graph and material identity. See [national admission, lines
24–118](../../rust/crates/babylon-persistence/src/economic_catalog/national.rs) and [opening compiler, lines
30–42](../../rust/crates/babylon-persistence/src/economic_catalog/compile.rs). This is useful provenance and
reproducibility, but cold loading currently pays for expensive source interpretation and repeated admission.

`MaterialCircuitState` contains both immutable definitions and changing quantities: commodity and recipe
definitions, logistics topology, inventory, orders, backlog, freight, capacity, labor, commitments and monetary
accounts. A detached candidate closes the material period, applies staffing and graph rules, and derives the
successor register and evidence. See [state, lines
451–479](../../rust/crates/babylon-material-circuit/src/model.rs), [in-memory close, lines
175–230](../../rust/crates/babylon-tick/src/material_replay.rs), and [advance, lines
694–727](../../rust/crates/babylon-persistence/src/material_runtime.rs).

Only after candidate preparation does the writer enter its transaction. It writes graph and semantic rows, the
ordered action batch, choice receipts, events, checkpoint references, material state/receipt frames, organizer
projections and an Archive dirty receipt. The durable marker and acknowledged commit publish the result together.
Failure must leave the old world authoritative. This atomic behavior is valuable and survives the proposed backend
change. See [pre-marker writes, lines 726–767](../../rust/crates/babylon-persistence/src/runtime.rs) and [commit
path, lines 729–840](../../rust/crates/babylon-persistence/src/material_runtime.rs).

Three different consumers then add work. Runtime reopening captures foundation, current/prior state, lookup history
and organizer witnesses; it finishes its read transaction before expensive admission. A cold full observer
reconstructs material periods from opening through the requested tick to establish lifecycle history, then
authenticates endpoints and builds a large production projection. Archive independently captures disclosed facts and
creates immutable dossiers. These are not interchangeable timings. See [runtime open, lines
54–105](../../rust/crates/babylon-persistence/src/material_runtime/open.rs), [checkpoint capture, lines
21–110](../../rust/crates/babylon-persistence/src/material_runtime/runtime_checkpoint.rs), [observer history, lines
616–675](../../rust/crates/babylon-persistence/src/observer_material.rs), and [Archive worker, lines
32–77](../../rust/crates/babylon-persistence/src/archive_revision/worker.rs).

## The database is not a giant JSON document

The two current DDL files declare **66 tables**, enumerated mechanically and assigned dispositions in [the table
inventory](evidence/storage-table-disposition.tsv). Neither declares JSON/JSONB columns. `material_tick_v3` stores
typed binary identity, register, receipt and lookup frames in `bytea`. Other tables encode relational graph state,
packed arrays, reference data and publication evidence. See [material table, lines
1073–1080](../../rust/crates/babylon-persistence/migrations/current_schema.sql).

The giant object is more visible at the observation boundary. `ProductionSnapshot` includes sites, routes, freight,
capacity accounts, order definitions, events, household/service/price/labor/staffing accounts, observed contexts and
provenance. A complete national export asks for all of these together. Ordinary gameplay must instead ask a bounded
decision question. The proposed owner therefore serves county/subject/relationship queries and small map summaries.
Exhaustive exports remain explicit engineering work. See [production projection, lines
19–60](../../rust/crates/babylon-persistence/src/production_observation.rs).

## Improvements already present

The reset must not rediscover these as unimplemented optimizations:

- Unchanged material sections reuse opening content; changed sections have typed identity normalization and
  compression.
- State and receipts share typed identity tables; period-local lookup ownership avoids retaining every retired
  identity in live maps.
- Graph/event arrays and string/key lookups reduce repeated row identity.
- Checkpoint references reuse existing admitted source components rather than physically copying them again.
- zstd level 9 has bounded exact decoding and canonical hash checks.
- Archive membership uses complete bases plus exact additions; provenance and graph memberships have additional
  reuse mechanisms.

See [state section encoding, lines 409–438](../../rust/crates/babylon-persistence/src/state_storage.rs),
[compression, lines 16–54](../../rust/crates/babylon-persistence/src/storage_compression.rs), [checkpoint
references, lines 31–51](../../rust/crates/babylon-persistence/src/checkpoint_reference.rs), and [live
architecture](../concepts/architecture.rst). Opening-based elision is not a general previous-period row delta: a
changed section can still be stored as a complete compressed section. These mechanisms reduce disk bytes without
necessarily reducing typed state or hydration cost.

## Remaining amplification

`MaterialWorldRegister` holds the full typed state and a shared canonical byte vector. Sharing avoids several copies
but does not remove the simultaneous typed and serialized representations. Its builder encodes state, drops it, and
decodes that encoding back into typed state. The opening compiler does the same. `canonical_state` clones all state,
sorts it and validates it; the close uses it at entry and completion. Splitting definitions from working quantities
and admitting a typed candidate once is a more direct memory intervention than adding another compression setting.
See [register, lines 98–160](../../rust/crates/babylon-tick/src/material_world.rs) and [canonicalization, lines
442–460, 792–802 and 1555–1557](../../rust/crates/babylon-material-circuit/src/transition.rs).

Cold restore still scans historical lookup metadata from period one. Cold full-observer reads additionally decode
all prior material periods. Warm cursors already avoid redundant full admission and must not be described as absent.
Their existence does not solve first open or long-history access. The proposed independent current root and small
causal indexes remove this dependency deliberately; merely substituting SQLite for the SQL calls does not. See
[lookup history, lines 1670–1715](../../rust/crates/babylon-persistence/src/material_runtime.rs).

Organizer history needs special attention. Current state contains complete receipts, observations, products and
consumed-product IDs; validators cross-reference them, and current household-time receipts constrain actions. Those
are presently connected consumers, not dead audit bytes. The replacement splits compact causal authority from a
permanent journal and preserves the cross-references. It does not erase history or weaken double-use checks. The
field inventory in chapter 05 makes that split explicit.

## Evidence and its limits

An older complete two-period run preserved in the canonical architecture is smoke008; it did not establish play
acceptance. [Chapter 01](01-evidence-and-failed-approaches.md) separately examines later smoke021 chat evidence.
[Architecture lines 396–458](../concepts/architecture.rst) record:

| Measure | Preserved observation |
| --- | ---: |
| Opening database | 284,456,627 bytes |
| Period retained growth | 37,707,776 / 29,401,088 bytes |
| Committed advances | 69.28 / 63.54 seconds |
| Archive completion | 177.39 / 99.42 seconds |
| Complete production reads | 120.11 / 120.80 seconds |
| Cold reopens | 85.22 / 105.45 seconds |
| Whole smoke | 972.20 seconds; failed its 900-second limit |
| Sampled native peak | 10,166,202,368 bytes, excluding PostgreSQL |
| Later production evidence body | 809,432,538 bytes |

A later cold production read took roughly 145 seconds and peaked near 6 GB. Allocator work reduced retained heap
after release; a separate control still peaked around 5.2 GB. These observations do not isolate the engine, storage
and export costs, and they are not current-head measurements. The ignored raw report directory was unavailable in
this checkout; this chapter attributes the numbers to the canonical documented evidence.

The current v6 policy allows 40 MB period growth, targets 23 MB, allows 10 GB at 325 periods and 10 GB combined
running-game memory. Its latency limits include 120-second advance p95 and 180-second cold open. The proposed reset
sets a much smaller **gameplay objective: a 16 GB host, at most 4,000,000,000 bytes whole-game memory, ordinary
committed turns at most 30 seconds, and a 10 MB-per-period storage ambition**. These are proposed acceptance
targets, not a claim that swapping storage reaches them. Complete physical accounting and checkpoint rotation are
specified in chapter 07.

## What H3 and algebra do here

The national opening already uses cohorts rather than individual decision agents. Current household keys retain
earning and ownership distinctions; the graph preserves public relations. BSL rejects invalid aggregation such as
summing intensive quantities. These are substantive modeling tools, not a proof that detailed state can always be
recreated from a total.

H3 identifies spatial cells and supports deterministic hierarchy. Current Rust uses `h3o`; the SQL schema stores
integer H3 IDs and checked parents rather than relying on PostGIS or an H3 extension. Arbitrary per-cell economic
values cannot be recovered from an H3 index. The documented national run had no H3-related recurring growth. The
proposed uneven-detail model therefore keeps national coverage, material distinctions and significant flows while
removing unnecessary detailed objects; it does not use mathematical terminology as a substitute for an explicit
aggregation policy.

The Lawvere-inspired unified algebra and sheaf language describe historical formalism proposals; they do not
establish a deployed general-purpose runtime compression algorithm. The [July 22 formalism review, line
75](../superpowers/specs/2026-07-22-mirror-typed-core-spec.md) itself distinguishes conservation over disjoint
partitions from a sheaf gluing law, and a proportional allocation section from an adjunction. The live mechanisms
verified here are typed extensive/intensive folds ([typechecker, lines
224–240](../../rust/crates/babylon-bsl/src/typecheck.rs)), H3 spatial identity and hierarchy, and finite transition
kernels with exact ticket allocation ([kernel representation, lines 189–210; allocation, lines
2259–2276](../../rust/crates/babylon-bsl/src/probability.rs)). No general runtime sheaf reduction is established by
this source trace.

Category laws can help specify which aggregates preserve selected relationships, but they do not automatically
identify a smaller sufficient state for every later action. Nor do abstract laws guarantee byte-identical
floating-point evaluation after regrouping or equivalent gameplay after deleting distinctions. A proposed fold must
name the conserved quantities, the retained decision differences, the rounding/ordering rule and the downstream
action it still permits. A lossy reduction is an authored game-model decision with a causal signature to qualify,
not a consequence of calling the representation a sheaf.
