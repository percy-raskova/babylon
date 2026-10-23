# 06 — Target runtime and selected embedded SQLite

**Status: PROPOSED, pending governance and the measured witness.** SQLite is the selected desktop direction, not an
established performance result. Do not ship a generic storage-backend framework or a permanent dual-write path. The
unchanged-contract witness must expose material gaps before cutover; a failed witness blocks the affected
implementation packet and returns the concrete defect for correction or an explicit Director decision, rather than
silently selecting another backend.

## Why SQLite, rather than another document store

This comparison records the selected desktop direction; it is not a new backend competition. Product fit below is an
architectural inference from the cited capabilities, checked on 2026-10-23. JSON-shaped authored content does not
require a document database: authoring syntax, canonical runtime objects and durable storage are separate contracts.
Babylon already stores typed binary state in PostgreSQL. Replacing that with nested documents would still require
command atomicity, exact numeric encoding, provenance, retention and scoped disclosure.

| Store | Fit for the selected campaign contract |
| --- | --- |
| **SQLite — selected** | An embedded application file supports transactions, indexed journal projections and binary chunks without another server. Its application-format documentation explicitly describes storing structured collections and BLOBs in one file. This matches a local, single-owner save; the witness still must establish actual cost. [SQLite application format](https://www.sqlite.org/appfileformat.html) |
| **PostgreSQL — baseline to retire after qualification** | Its client/server architecture supports independent clients and database-enforced reader roles, which the current code uses. A local campaign must pay the process, lifecycle and authorization integration costs described above. This reset assigns scoped reading to the trusted Rust owner and does not require a shared database server. [PostgreSQL architecture](https://www.postgresql.org/docs/current/tutorial-arch.html) |
| **MongoDB** | Document organization does not make the campaign a viable single giant document: BSON documents have a 16 MiB maximum, with larger data requiring another representation such as GridFS. It adds no demonstrated solution to Babylon's retained-history or repeated-decoding costs. Community Server uses SSPL; MongoDB's own FAQ says it is not OSI-approved, so it should not be described as a permissively licensed open-source substitute. [Limits](https://www.mongodb.com/docs/manual/reference/limits/), [licensing FAQ](https://www.mongodb.com/legal/licensing/server-side-public-license/faq) |
| **FerretDB** | A credible open-source MongoDB-compatible alternative, but its current architecture translates MongoDB wire requests into SQL using PostgreSQL with the DocumentDB extension. That retains the server dependency this desktop reset removes and introduces another layer. [FerretDB architecture](https://docs.ferretdb.io/) |
| **redb** | A pure Rust embedded ACID key-value store with MIT/Apache licensing is a relevant non-SQL alternative. It could hold typed chunks, but Babylon would own more index/query tooling for its permanent journal. No measured advantage justifies expanding this cutover to a second embedded implementation. [Project documentation](https://github.com/cberner/redb) |

Compression reduces encoded bytes; it does not remove the decoded object graph, cloned state or simultaneously
assembled report. Smaller admitted state, bounded projections and fewer live copies must deliver the memory
reduction independently of the chosen compressor or database.

## One trusted campaign owner

One Rust process owns an open campaign and all mutations. It owns the in-memory graph, immutable content, current
causal quantities, pending commands and scoped knowledge. Bevy, narrative tools and AI receive typed
requests/results; they receive no database path, connection, SQL capability or unrestricted snapshot. A privileged
diagnostic export is a separate explicit owner operation, never an option on the player query surface.

Use one SQLite database per campaign, on a local filesystem. All mutable state, journal, acquired knowledge, recent
detail and references commit in that database. Captured source/content bytes needed to reconstruct the save are
included; an immutable installation cache can accelerate admission but its absence cannot change meaning. A
same-user file owner can inspect their own local save; the security promise is confinement of game components and AI
tools, not secrecy against the computer's owner. Preserve the current distinction between public facts, earned
observations and full engineering inspection.

The concrete Rust boundary is `SqliteCampaignStore`, used by the existing runtime composition root. The following
signatures are design notation, not shipped API:

```rust
fn create(captured: AdmittedContent, opening: AdmittedOpening) -> Result<CampaignHandle, SaveError>;
fn open(path: CampaignPath, expected_build: BuildIdentity) -> Result<CampaignHandle, SaveError>;
fn accept_command(command: PlayerCommand, nonce: [u8; 16]) -> Result<AcceptanceReceipt, CommandError>;
fn commit(candidate: PreparedPeriod) -> Result<CommittedPeriod, SaveError>;
fn query(scope: PlayerScope, query: PlayerQuery) -> Result<PlayerResult, ReadError>;
fn history(scope: PlayerScope, cursor: HistoryCursor, limit: u16) -> Result<HistoryPage, ReadError>;
fn export_save(destination: NewSavePath) -> Result<VerifiedExport, SaveError>;
```

`PlayerQuery` is a closed enum: map summary, county summary, known subject, known relationship, current commitment,
and earned dossier. Every query checks campaign/player/period and acquired-knowledge authority before selecting
fields. Responses carry committed period and source identity, so stale reports are visible. History pages default to
50 records, cap at 200, and use `(period, journal_seq)` cursors. No caller-defined filters, SQL fragments or
arbitrary field paths enter this API.

Accepted command acknowledgement is durable before an advance. A transaction inserts its immutable command/accepted
commitment and 16-byte nonce, then acknowledges. Same nonce plus equal canonical bytes returns the original
acceptance; same nonce plus different bytes refuses. Preserve the existing command contract: only the configured
controlled actor and input authority can submit, and each campaign has one immutable accepted commitment for its
next period. A second distinct commitment for that period refuses even with another nonce. There is no cancellation
or replacement path in this reset; changing that behavior requires a separate gameplay decision. See [current
admission, lines 292–326](../../rust/crates/babylon-persistence/src/organizer_runtime.rs). Standing work remains
separate engine-owned state. Acceptance does not advance time or world hash. A crash reopens indexed pending
commands without replaying the whole journal.

## Nine physical tables

Use `STRICT` tables, explicit `NOT NULL`/length/range constraints, foreign keys enabled on every connection, and
application-owned canonical decoders. No `REAL` column stores money, counts, tickets or canonical binary64 bits.
This is the complete table/column reference; implementation should not invent additional persisted mirrors of the
same state.

| Table | Columns and purpose |
| --- | --- |
| `save_manifest` | `id INTEGER PRIMARY KEY CHECK(id=1)`, `schema_version INTEGER`, `campaign_id BLOB(16)`, `build_hash BLOB(32)`, `content_hash BLOB(32)`, `current_snapshot_id INTEGER FK`, `journal_tail_seq INTEGER`, `journal_tail_hash BLOB(32)`, `knowledge_tail_seq INTEGER`, `knowledge_tail_hash BLOB(32)`. One published save identity and durable tails. |
| `content_entry` | `(kind INTEGER, entry_key BLOB, ordinal INTEGER)` primary key; `codec INTEGER`, `raw_len INTEGER`, `raw_hash BLOB(32)`, `payload BLOB`. Immutable chunked source, compiled definitions, provenance and opening metadata; manifest commits to complete ordered contents. |
| `state_chunk` | `chunk_id INTEGER PRIMARY KEY`, `section INTEGER`, `ordinal INTEGER`, `codec INTEGER`, `raw_len INTEGER`, `raw_hash BLOB(32)`, `payload BLOB`. Ordinary integer-addressed immutable chunks of current/opening/checkpoint state. |
| `snapshot` | `snapshot_id INTEGER PRIMARY KEY`, `role INTEGER`, `period INTEGER`, `world_hash BLOB(32)`, `state_hash BLOB(32)`, `manifest_bytes BLOB`, `committed_journal_seq INTEGER`, `committed_journal_hash BLOB(32)`, `knowledge_seq INTEGER`, `knowledge_hash BLOB(32)`. Role is opening/current/historical; manifest declares every required section, count and ordered chunk hash. |
| `snapshot_chunk` | `(snapshot_id INTEGER FK, section INTEGER, ordinal INTEGER)` primary key; `chunk_id INTEGER FK`. Complete manifest membership; no missing or extra chunks admitted. |
| `permanent_journal` | `journal_seq INTEGER PRIMARY KEY`, `kind INTEGER`, `period INTEGER`, `actor_id BLOB(8) NULL`, `subject_kind INTEGER NULL`, `subject_id BLOB NULL`, `nonce BLOB(16) NULL`, `record_key BLOB NULL`, `codec INTEGER`, `raw_len INTEGER`, `raw_hash BLOB(32)`, `payload BLOB`, `previous_hash BLOB(32)`, `entry_hash BLOB(32)`, `resolved_period INTEGER NULL`, `resolution_seq INTEGER NULL FK`. Immutable typed record plus mutable command-resolution metadata. |
| `knowledge_grant` | `knowledge_seq INTEGER PRIMARY KEY`, `player_id BLOB(8)`, `subject_kind INTEGER`, `subject_id BLOB`, `grant_key INTEGER`, `acquired_period INTEGER`, `source_journal_seq INTEGER FK`, `payload BLOB`, `previous_hash BLOB(32)`, `entry_hash BLOB(32)`. Immutable actually earned authority/fact reference; no future-state lookup substitutes for an observation. |
| `service_state` | `id INTEGER PRIMARY KEY CHECK(id=1)`, `service_seq INTEGER`, `codec INTEGER`, `raw_len INTEGER`, `raw_hash BLOB(32)`, `payload BLOB`. One bounded mutable record for the Archive cursor, pending dossier requests and player navigation; independently writable, excluded from mechanical state/world hashes, included in save integrity and export. |
| `recent_detail` | `(period INTEGER, family INTEGER, ordinal INTEGER)` primary key; `codec INTEGER`, `raw_len INTEGER`, `raw_hash BLOB(32)`, `payload BLOB`. Latest thirteen periods of exhaustive technical receipts and events, never the restart authority. |

Length notation in this reference means a `BLOB` column with `CHECK(length(...) = N)`, not a SQLite `BLOB(N)`
affinity assumption. `role`, `kind`, `section`, `family` and `codec` use closed versioned integer registries
compiled into the reader. Period/sequence/row IDs must fit checked nonnegative i64; exhaustion refuses before
mutation. State and content chunks have at most 4 MiB decoded bytes; recent detail uses the same limit and ordered
fragmentation. Permanent journal records have at most 16 MiB decoded bytes, with one governed choice or action batch
per record, never a complete national report. Unsupported larger records fail preflight without partial publication.
A payload can be literal or one exact zstd frame; codec selection is fixed by format version and hashes cover
decoded canonical bytes.

Required indexes are: one opening and one current snapshot via partial unique indexes; unique historical period;
journal `(period,journal_seq)` and `(subject_kind,subject_id,period,journal_seq)`; unique nonnull command nonce;
partial `UNIQUE(kind,record_key) WHERE record_key IS NOT NULL`; unique accepted-command target `period` filtered to
the accepted-command kind, plus a partial unresolved-command index on `period`; knowledge
`(player_id,subject_kind,subject_id,grant_key,acquired_period,knowledge_seq)` plus unique
`(player_id,subject_kind,subject_id,grant_key,source_journal_seq)` acquisition identity; and
`snapshot_chunk(chunk_id)` for reachability reclamation. The single-campaign file supplies the command uniqueness
scope; journal actor fields do not expand input authority. A private current causal index records active products,
pending obligations and resource consumption; it lives inside current state, not as a second SQL authority.

Do not query opaque payloads using JSON extraction. Indexed columns select a bounded set; typed Rust decoding
produces the explicit projection. Hash indexes are candidate filters, never equality proofs. Reuse a state chunk
only against the preceding current snapshot's same section/ordinal after equal length/hash and exact canonical
bytes. Historical checkpoints share existing chunk IDs. There is no global content-addressable store, unbounded
dedup search, or external object service.

## Exact types and identities

Money remains signed i128 fixed-point micro-units, encoded as 16 bytes in the canonical byte order. General u64
quantities use 8-byte unsigned canonical encoding. Choice interval endpoints/counts that may equal 2^64 use 16-byte
unsigned encoding with the exact governed upper-bound check; ordinary draw tickets remain u64. Binary64 values
retain their exact bits with finite-domain checks. Stable 32-byte identities remain typed; compact local IDs
reference their captured definition. Valid H3 IDs already fit checked signed SQL storage, but arbitrary u64 actor
IDs must not be narrowed.

All arithmetic and economic comparison remain in Rust. No string-to-number coercion or SQL aggregate is allowed to
round a stored amount. Canonical journal hashes include immutable typed fields and payload identity, excluding
mutable command-resolution metadata. A period's commit journal record and snapshot manifest authenticate the exact
consumed command IDs. Open verifies unresolved/resolved metadata against those bounded current witnesses; replay
performs complete historical chain validation.

## Commit, recovery and portable export

Use WAL mode, `synchronous=FULL`, `foreign_keys=ON`, a five-second busy timeout and explicit writer serialization.
The owner holds a task-scoped file lock for its campaign lifetime; a second writer refuses with the owning
process/campaign identity rather than silently opening another runtime. Readers use short consistent transactions.
SQLite library/build identity is pinned through the project's native toolchain; add a pinned `rusqlite` dependency
linked to the admitted SQLite runtime rather than silently introducing another bundled version.

Prepare the typed candidate outside the write transaction. `BEGIN IMMEDIATE` then verifies the expected current
root, inserts new chunks and permanent records, consumes accepted commands, inserts earned knowledge, rotates recent
detail/checkpoints, writes the complete current manifest and updates `save_manifest` last. `COMMIT` precedes
publication to Bevy and the in-process Archive wakeup. A lost acknowledgement is reconciled by exact candidate
period/world/command identity; retry must not perform the command twice. If disk-full, busy, integrity or decoding
errors occur, retain the last committed display and return the specific error. Startup checks pending work from the
durable service record; notifications are only hints.

`service_state` has a decoded limit of 1 MiB, a maximum of 256 pending requests and one current navigation record.
Its typed payload stores monotonically increasing request IDs, subject/source-period/knowledge-prefix identity, and
queued or producing status; queue-full returns a specific error. Enqueue/navigation and completion use separate
serialized owner transactions checking expected `service_seq`. Completion atomically appends or reuses the permanent
dossier journal record, updates journal tails, and removes the pending request/advances the cursor. Dossier identity
includes request ID and exact source/knowledge identity; the unique `(kind,record_key)` projection plus exact
pending/published source-payload comparison makes retry idempotent. For dossier entries, `record_key` is the
canonical concatenation of request ID (u64), source period (u64), knowledge-prefix hash (32 bytes), subject kind
(u32), subject-ID byte length (u32) and exact typed subject-ID bytes, all integers in the format's canonical byte
order. Request IDs never repeat; a retry must match the previously accepted source/knowledge identity. This is an
explicit BLOB projection, not an expression index into the opaque payload. No operation here advances the mechanical
snapshot or world hash. Content/recent/state payload hashes and service-record hash all enter export integrity
validation. Actual new knowledge grants remain part of an admitted period commit; rendering can only publish facts
already earned in its recorded prefix.

Export uses SQLite's online backup mechanism into a new destination while the owner is at a committed boundary, then
opens the resulting independent database read-only, checks integrity, manifests and current state identity,
synchronizes and atomically publishes that destination. Do not copy a live main database file while ignoring
WAL/SHM. Close/checkpoint and export report errors; they never delete the sole good save. Import validates the exact
supported format/content/build before opening a writer. No migration of preserved PostgreSQL campaigns is part of
this cutover.

## The deciding witness

First, use the same admitted opening and two captured current canonical periods in PostgreSQL and SQLite **without
reducing semantics or changing canonical hashes**. SQLite may fragment existing frames physically. Measure storage
including indexes/WAL, writes, cold reconstruction, scoped history and peak whole-game memory. Include a durable
accepted command before the first tick, unresolved freight across the boundary, knowledge earned in period one, and
permanent choice evidence where the selected fixture executes a governed choice. If it executes none, use a separate
bounded canonical choice/ticket control rather than inventing a choice event in that fixture. Crash before
acceptance acknowledgement, before commit, after durable commit/before acknowledgement, and during export; verify
exactly one resulting action and no future knowledge.

After the content/state split, repeat the same fixture through the reduced SQLite contract and compare it with the
recorded unchanged SQLite witness and existing PostgreSQL baseline. This isolates the additional contract reduction
without building a second reduced PostgreSQL implementation. No runtime dual write is permitted: each isolated
fixture receives the same immutable input packet. A tiny SQLite blob demo cannot be compared against a PostgreSQL
run that renders every national dossier. The root implementation packets assign the initial backend witness before
the content/state split; retirement follows integrated qualification.

Full acceptance additionally checks thirteen-period rotation, historical replay, national coverage, the ordinary
play target of at most 30 seconds per ordinary committed turn including its bounded player briefing, cold open at
most 30 seconds, warm scoped query at most one second, cold scoped query at most two seconds, and at most
4,000,000,000 bytes combined game memory on a 16 GB host. The ten-MB period ambition and checkpoint spikes are
charged as [chapter 07](07-history-replay-and-archive.md) specifies. SQLite alone is not credited with meeting any
target.
