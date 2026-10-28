# Implementation packets

**Proposed execution plan.** This file turns the decisions in the dossier into finite tasks. It does not authorize
implementation or merging independently of the Director's current request. The documentation author did not run
these future implementation checks.

Read [acceptance and governance](09-acceptance-and-governance.md) before starting. Current-code entry points are
indexed in [04](04-babylon-current-architecture.md); collection dispositions are in
[05](05-data-and-model-contract.md). The SQLite schema and recovery contract in
[06](06-target-runtime-and-sqlite.md) are normative within this proposal. Do not infer new tables or semantics from
a packet's shorthand.

## Sequence and resource rules

```text
P0 Baseline and authority
  -> P1 Bounded persistence witness
  -> P2 Content/causal-state separation
  -> P3 SQLite owner and durable current state
  -> P4 Compact causal memory and bounded history
  -> P5 Scoped player reads and Archive
  -> P6 Authored national detail
  -> P7 External BSL/BSCN/TOML content
  -> P8 Connected play and measured qualification
  -> P9 One-way cutover and retirement
```

The sequence is intentionally conservative. P7's documentation and parser analysis can proceed independently after
P2, but its end-to-end evidence depends on P3 and P5. Do not create parallel writers to the same modules or fixture.
Separate worktrees for concurrent source edits; acquire the existing national fixture lease and native-launch slot
before using them.

Use the existing [national lifecycle](../../tools/postgres_national_lifecycle.sh) and [native
runner](../../tools/devtools/national_native_runner.py) ownership rules during the PostgreSQL comparison. Do not
start or reset a shared service to get a fresh database. The current native runner checks an exact ownership record
against the shared lease.

A packet is done when its behavior and listed checks pass. Do not add speculative abstractions, exhaustive new tests
that mirror implementation, a new benchmark framework, or a new task wrapper without demonstrated need. At a
repeated failure, classify the cause and stop expanding scope. A transient failure may be retried once with an
explanation; further attempts require a changed input or a concrete fix.

## P0 — Establish the exact starting point and authority

**Outcome:** one source/ownership record and an explicit storage-law disposition.

1. Read current `AGENTS.md`, the relevant Linear issues and this dossier. Record branch, HEAD, working-tree changes,
   current `origin/dev`, active writer and fixture/native ownership. The dossier baseline is
   `99f998e3dffb301a218a8a4e0ed809f440dafef2`; do not reset newer work to it.
2. Inspect only relevant changes to the paths in chapter 04 and the package's source manifest. Preserve unrelated
   changes. Create an authorized implementation lane from current `dev`; never commit to `dev` or `main`.
3. Prepare the narrowly scoped amendment described in chapter 09. Current [Constitution Article
   V](../../CONSTITUTION.md) explicitly requires Postgres and forbids mutable campaign SQLite. Mark proposed edits
   as proposed until the Director ratifies them.
4. Locate retained captures or a disposable small fixture for P1. Record path, digest, format, engine/content
   identity and ownership. Do not consume a historical database as a mutable test fixture.

**Check:** inspect source/fixture manifests and the proposed amendment diff. No engine build is required for this
packet.

**Stop:** unrelated ownership, missing recoverable fixture, or a source change that invalidates the selected
architecture. Report the specific conflict. Pending amendment approval does not prevent an isolated P1 witness; it
prevents authoritative SQLite activation.

## P1 — Test the SQLite persistence direction cheaply

**Outcome:** a two-period persistence witness with equivalent required behavior in both stores.

Use the existing canonical frames before redesigning them. Include captured content, one pending/consumed organizer
intent, a knowledge acquisition, an unresolved shipment or obligation crossing the period boundary, and a choice
receipt if the scenario exercises a finite kernel. A fixture with no choices must not claim choice-round-trip
coverage; cover the type separately.

Implement only the smallest isolated SQLite witness in the persistence crate's test/experiment boundary. It is not a
production backend interface. Store the same semantic payloads; do not compare an SQLite three-BLOB toy to
PostgreSQL's full Archive pipeline and report the difference as database speedup.

Exercise:

- write/read the captured content and two complete current states;
- commit an intent before acknowledgement and consume it exactly once at tick commit;
- read one authorized subject/period and refuse an undisclosed one;
- cold restore and compare logical canonical state/receipt identities;
- interrupt before commit, after commit but before acknowledgement, and during export;
- refuse malformed/truncated payloads, missing references and wrong versions.

Record allocated database bytes, indexes, WAL, export bytes, temporary disk, wall time and process memory
separately. Start with a small control. A retained national capture may be measured once after the control passes,
under the existing lease. Missing national evidence limits the claim; it does not justify launching a new 325-period
run.

**Decision rule:** continue only when correctness passes and the witness establishes a viable
single-writer/scoped-read/recovery path. The witness need not meet the final game's budgets with the old
representation. Report whether it isolates a database cost or leaves the dominant cost in
representation/reconstruction. If SQLite cannot support a required semantic behavior, stop and report it; do not
select another backend autonomously.

**Cleanup:** retain the witness result and a useful narrow contract; retire throwaway comparison code after the
production path subsumes it. Never retain two production stores to preserve the experiment.

## P2 — Separate immutable content from changing state

**Outcome:** one admitted catalog shared by runtime state, with compact instance references.

Entry points: [MaterialCircuitState](../../rust/crates/babylon-material-circuit/src/model.rs), [canonical
transition](../../rust/crates/babylon-material-circuit/src/transition.rs),
[MaterialWorldRegister](../../rust/crates/babylon-tick/src/material_world.rs), and [opening
compiler](../../rust/crates/babylon-persistence/src/economic_catalog/compile.rs).

Move definitions and static route/recipe/source descriptions to the typed immutable catalog identified in chapter
05. Keep a detached mutable candidate for tick atomicity. Stop constructing a typed state by encoding it, dropping
it and decoding it merely to admit already-validated internal data. Preserve external-byte validation and canonical
ordering; stream hashes/encoding rather than keeping avoidable complete copies.

Introduce a new canonical format only through the existing required ceremony. A changed representation does not
authorize changed quantities or tie-breaking. Keep current BSL phase order, checked arithmetic, role attribution and
event ordering.

**Checks:** content sharing across instances; external decode rejection; failed tick leaves the published state
unchanged; current scenario accounting parity; restart gives the same next tick. Use a regression for each removed
amplification path where an observable contract exists. Do not assert allocator addresses or incidental object
layouts.

**Stop:** a moved field has an unidentified consumer or a change affects gameplay rather than representation.
Classify it under P6 instead of hiding it in a codec refactor.

## P3 — Implement the SQLite campaign owner

**Outcome:** a complete current campaign can commit, close and reopen through the proposed store.

Prerequisites: P1/P2 and ratified authoritative-storage change. Implement [06](06-target-runtime-and-sqlite.md),
including its exact schema, transactions, chunk references, integrity checks, pending intent idempotency and current
snapshot root. Current state must restore without replaying old receipt or lookup chains.

The owner alone opens the mutable campaign database. UI/AI-facing code receives typed commands and scoped reads.
Replace PostgreSQL advisory/row locks with owner serialization and short SQLite transactions; do not emulate a
distributed lock service. Replace `LISTEN/NOTIFY` with post-commit wake hints plus durable pending work discovered
on startup.

Keep money and wide counters in the specified exact representation. Preserve source/content hashes, explicit
versions and specific error types. Implement portable export with SQLite's supported backup mechanism; copying a
live main file while ignoring WAL is not a save operation.

**Checks:** P1 failures plus wrong schema/build/content, duplicate command nonce, command retry, corrupt chunks,
foreign-key/reference failure, transaction rollback, disk-write error and export reopen. Check a real consumer
obtains a committed acknowledgement and reads the same period.

**Stop:** any path exposes partly committed state, acknowledges before durability, leaks hidden state to a reader,
or falls back to PostgreSQL on failure.

## P4 — Bound history without deleting causal memory

**Outcome:** restoration independent of historical state-chain length and permanent decision history, with a bounded
technical-detail window. Restore work remains proportional to current state and required causal indexes.

Entry points: [organizer contract](../../rust/crates/babylon-practice-contract/src/organizer/contract.rs),
[organizer time](../../rust/crates/babylon-tick/src/material_world/organizer_time.rs), [production
history](../../rust/crates/babylon-persistence/src/production_projection/history.rs), and [current checkpoint
readers](../../rust/crates/babylon-persistence/src/material_runtime/runtime_checkpoint.rs).

Implement chapter 07's retention rules: opening plus current state, two rolling historical checkpoints at
thirteen-period boundaries, thirteen periods of detailed engineering receipts, permanent accepted
inputs/choices/player journal/earned observations. Keep exact current anti-double-use, active knowledge and
obligation indexes in causal state. Do not drop organizer receipts until their causal consumers have moved to the
declared compact state.

Delete a chunk only when no retained snapshot references it, inside the same owner transaction that replaces those
references. Rebuildable caches may be evicted; earned reports and cited observations are not caches. Historical
replay uses retained input/content identity and the matching engine; unsupported old builds fail explicitly.

**Checks:** periods 12/13/14 and 25/26/27, old report access, expired contact product, consumed-product replay,
accepted intent after failed tick, shipment crossing a checkpoint, and interrupted retention cleanup. Verify current
restore does not scan every old period. Account for checkpoint rotation costs without masking them by deletions.

## P5 — Connect scoped player reads and Archive

**Outcome:** selecting a subject and advancing the player loop no longer requires a national production export.

Entry points: [observer material reader](../../rust/crates/babylon-persistence/src/observer_material.rs),
[production observation](../../rust/crates/babylon-persistence/src/production_observation.rs), [restricted
reader](../../rust/crates/babylon-persistence/src/reader.rs), and [Archive
worker](../../rust/crates/babylon-persistence/src/archive_revision/worker.rs).

Replace broad caller requests with the chapter 06 scoped interfaces. Use the same committed period and disclosure
snapshot throughout one response. Prepare the next-turn briefing and required earned report before marking the
player loop ready. Unrelated administrative dossiers can be generated on request or from queued dirty work; their
absence must never masquerade as a completed earned report.

Keep Archive citations and acquisition periods. Do not generate undisclosed pages before filtering, authenticate
thousands of pages for a small request, or refresh broad projections from frame/tooltip updates. Complete production
exports remain explicit diagnostic operations, outside normal navigation.

**Checks:** one workplace/organization selection, paginated history, cross-period refusal, future-grant
non-disclosure, delayed Archive work/restart, no hidden ledger fields, and a visible briefing tied to the durable
tick. Measure bounded response work rather than only SQL time.

## P6 — Author national detail that earns its cost

**Outcome:** all counties participate without a uniform dense cross-product of economic entities.

Entry points: [national opening](../../rust/crates/babylon-persistence/src/national_economy/opening.rs), [national
cohorts](../../rust/crates/babylon-persistence/src/national_cohorts/model.rs), [household
allocation](../../rust/crates/babylon-persistence/src/national_household_allocation/model.rs), and [household
refinement](../../rust/crates/babylon-persistence/src/national_household_refinement.rs).

Apply chapter 05's authored reduction policy. Keep a sparse national background and explicit distinctions for the
organizer area, relevant counterparties and bottlenecks. Use a stable content-authored layout for the whole
campaign; do not materialize actors because the camera moved. Preserve county identity and explicit cross-boundary
flows.

First remove duplicate/unused representation without changing mechanics. A further gameplay simplification must be
an explicit Designed content/model change with its own rationale and acceptance, not a claim of lossless
compression. Preserve wealth/access distributions where thresholds matter. Do not pool rich and poor households to
make a purchase feasible.

**Checks:** county coverage; conserved population, workforce, time, stock and money; poverty/ownership
counterexample; shared capacity and delayed freight; local versus remote aid; independently authorized
organizational costs; source evidence classes. Current f64 folds are order-sensitive: do not claim byte parity after
regrouping unless the test establishes it.

**Stop:** the proposed merge has no demonstrated equivalence or declared, approved approximation, or it erases a
required player distinction. Do not add dynamic refinement or a universal category-theory framework to rescue it.

## P7 — Admit external BSL/BSCN/TOML content

**Outcome:** the same content path supports first-party files and a small external mod without rebuilding the game
executable.

Implement chapter 03's exact package contract, not a second one. P7 has two required substeps:

1. **P7a, numeric campaign:** admit the external complete Michigan defines replacement through the existing economic
   foundation, then advance, save, reopen and replay it in the ordinary campaign path.
2. **P7b, authored scenario and rule campaign:** connect the worked BSCN/BSL examples to the existing authored
   foundation and replay session through chapter 03's explicit adapter contract. Capture sources, graph, registers
   and resolver identity; use the same SQLite owner and publication protocol; expose the permitted public fixture
   fields in the graph view; advance, save, reopen and replay the changed rule. Route supported embedded first-party
   declarations and rules through that same content admission boundary. A parser-only or unsaved fixture is not P7b
   completion. The bounded authored campaign does not qualify the national economy.

Preserve explicit native calls such as `material-cycle`; mod content does not become arbitrary Rust code or direct
database access. Do not introduce a second simulation engine or save service for the authored example.

Resolve package identities/replacements deterministically, compile once, capture the resolved source once, and
retain the resulting content identity in the campaign. Keep engine phase/rule ordering separate from package
discovery. Existing saves use their captured content after the installed package changes.

**Checks:** the three worked examples reach real consumers; shuffled file discovery; duplicate IDs and replacement
conflicts; missing/cyclic dependencies; unknown fields; invalid units/effects; wrong native-host invocation;
modified installed content after save; invalid content cannot publish a campaign. Distinguish parser success from
complete playable-scenario admission.

**Stop:** a change needs new primitives or new restricted causal authority. Report that specific requirement.
Launcher/workshop integration and hot reload are not prerequisites.

## P8 — Qualify connected play and actual costs

**Outcome:** a reproducible playable loop with measurements against the new policy.

Run the small accounting/organizer controls first, then two real national advances with close/reopen and a scoped
player action sequence. Freeze the exact engine, content, policy, county roster and fixture identity before
measuring. Readiness time ends only after the briefing and action-critical report are available. Record optional
background work separately.

After the smoke passes, run one actual 52-period window for sustained behavior and p95 timing. Run the separate
325-period storage/aging qualification only after the shorter window passes. Do not substitute a multiplication of
two periods for either run. Do not rerun the entire window for a changed report formatter when the retained inputs
and outputs can be re-evaluated honestly.

Measure all game roles together, plus allocated retained save, WAL and temporary disk. Preserve incomplete output on
interruption. Play acceptance includes an actual understandable local-versus-remote organizer choice and its later
consequence; aggregate throughput and green tests cannot establish enjoyment.

**Stop:** first failed admission with its phase and measurement. Apply only a bounded root-cause fix to the
identified component, then rerun the smallest invalidated evidence. No repeated hours-long loop without a changed
hypothesis and source.

## P9 — Retire the obsolete path and publish the result

**Outcome:** one production path, accurate live documentation, preserved recovery evidence.

After the new path and consumer coverage pass, remove the old mutable campaign PostgreSQL runtime, SQL-only
readers/roles, service packaging, duplicate serializers and implementation-coupled tests that have no remaining
consumer. Retain independently required reference-data and operator consumers. Inspect every deletion's consumers;
do not assume a filename containing `postgres` is obsolete.

Preserve old databases/saves and unique evidence unchanged. No migration or broad filesystem cleanup is part of this
packet. Update the live architecture, North Star, AGENTS and current executable policy under the approved governance
change; keep historical ADRs/reports unchanged.

Run the required final scoped/static and no-documentation gates once at the final exact head. Create/merge only as
currently authorized, using repository commit conventions and `mise run pr:merge -- N` for an authorized merge. No
direct merge to `main`.

**Stop:** an old production writer remains reachable, a consumer still depends on a removed path, acceptance
evidence is from an earlier head without a justified unchanged boundary, or review threads remain unresolved.

## Existing check commands

Run from the implementation worktree. The first two examples are real current tasks; the crate selection must match
the packet's edits.

```bash
mise run rust:test:q -- -p babylon-persistence
mise run check:bsl-sentinels
```

From `rust/`:

```bash
cargo fmt --all -- --check
cargo test -p babylon-material-circuit --locked
cargo clippy -p babylon-persistence --all-targets --locked -- -D warnings -D clippy::cognitive_complexity
```

Use focused test-name/filter arguments before the full crate where a specific contract is under test. Run retained
Python `mise run check` only when its gate is applicable. The final `mise run rust:check-no-docs` gate includes
doctest execution but does not generate documentation. Never substitute `mise run ci:rust`, `cargo doc`, or Sphinx.
Do not run `bsl:grammar-test` as an incidental prose check: it regenerates parser artifacts.

## Packet completion record

Record this in the current authorized work/PR report, not by editing a historical dossier measurement:

```text
Packet:
Source HEAD and branch:
Fixture/content/policy identities:
Authority/ownership disposition:
Behavior changed and connected consumer:
Retired code/data obligations:
Checks run, exit status and evidence paths:
Actual time/memory/storage measurements (or not measured):
Known limits and remaining blocker:
Next eligible packet:
```

A completion record is enough. Do not launch a new review swarm, rebuild a whole evidence infrastructure, or rewrite
this dossier after every packet.
