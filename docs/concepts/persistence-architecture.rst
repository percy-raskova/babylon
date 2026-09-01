Persistence Architecture
========================

Persistence begins only after the Rust tick judge succeeds. The engine crates
stay database-free, while ``babylon-persistence`` owns the one authoritative
game-managed PostgreSQL composition.

Why One Authoritative Backend?
------------------------------

The old Python design placed SQLite and PostgreSQL behind one runtime protocol.
That made authority depend on the selected adapter and allowed two game-state
storage paths to survive. Gate 3 replaces that model with an explicit split:

**Rust PostgreSQL authority**
   Owns campaign foundation, typed state, commit markers, restart, and Archive
   dirty receipts. It is the only production game-state writer.

**Python SQLite reference**
   ``RuntimeDatabase`` supports frozen behavioral tests and local reference
   work. It is not a deployment alternative and cannot acquire PostgreSQL
   authority.

**Dedicated periphery stores**
   Data, AI, documents, and vector search may use their own stores and
   credentials. Those credentials cannot mutate the governed game schemas.

This is a source-of-truth boundary, not a backend abstraction. There is no
adapter, fallback, compatibility view, or dual-write phase between Python and
Rust.

Judgment and Commit
-------------------

The sequence for one durable tick is:

#. ``ReplayTickSession`` judges the next tick on detached in-memory state.
#. The runtime prepares exact typed semantic rows and envelope bytes.
#. One PostgreSQL transaction writes graph, material state, events, checkpoint
   rows, and one Archive dirty receipt.
#. ``tick_commit_v1`` is inserted last.
#. Only an acknowledged ``COMMIT`` or exact ambiguity reconciliation publishes
   the receipt and caller sink.

A rollback leaves no commit marker. An unresolved commit ambiguity leaves the
caller sink unchanged. Retry must reconstruct byte-identical rows and envelope
identity.

Authority State Machine
-----------------------

The append-only authority ledger admits exactly two rows: ``prepared`` at
schema epoch 8 and ``rust_active`` at epoch 9. The active row binds the prepared
row digest and commits last during activation. Once active, only
``babylon-runtime`` can reacquire writer authority.

Epoch 9 retires the Python-managed relations only after their data is migrated
with ordered count and semantic hash parity or proved unreachable and empty.
The terminal reader boundary contains no Python game-state edge and no
compatibility projection.

Restart Model
-------------

The runtime captures immutable foundation bytes for each campaign. A complete
full checkpoint contains the nine required state and identity sections. Restart
loads the foundation or latest full checkpoint, validates every section, then
replays a contiguous marker tail.

Delta checkpoints reduce write volume but never act as restart roots. A gap,
duplicate, digest mismatch, or incomplete manifest refuses recovery rather than
guessing.

Reference Data and H3
---------------------

``babylon_ref`` owns fixed geography, H3 cohorts, and exact reference artifacts.
Artifact lookup uses the full digest-qualified database key. The runtime does
not fetch from ambient paths, the network, a latest-version alias, or a fallback
digest.

Rust installs and reads the canonical H3 products directly. Python continues to
build deterministic data artifacts, but it cannot write the authoritative
campaign estate.

Archive Boundary
----------------

Every committed tick writes exactly one Archive dirty receipt carrying the
tick-content identity. The receipt is durable evidence that semantic material
must refresh. ``sim:archive`` installs the additive client-owned Archive schema
exactly once. Later calls check its marker and relations. The command reports
receipts, knowledge grants, consumptions, and materialized pages.

The first semantic worker slice binds an exact dirty batch to each marker-backed
receipt. It applies subject and field knowledge grants in SQL. It renders pages
with the pinned strict MiniJinja template and searches only granted pages. Later
Gate 3 work adds broader dirty-subject producers, dossier coverage, and the
playable retrieval loop. This slice alone does not pass a game milestone.

Operational Consequences
------------------------

- ``db:bootstrap`` performs the idempotent Rust activation.
- ``sim:e2e-michigan`` runs a fresh Rust-owned durable campaign.
- ``sim:probe`` reports the selected worktree campaign tail and labels
  database-wide totals separately.
- ``sim:archive`` installs the additive semantic Archive schema or checks its
  marker and relations. It reports the Archive estate.
- ``qa:michigan-rollover-smoke`` proves a 60-tick restart boundary.
- The live adopter suite verifies rollback, lock refusal, ambiguous commit,
  installed mutations, and cleanup against a disposable pinned database.

See Also
--------

- :doc:`/reference/persistence` — Commands, types, and contract references
- :doc:`/concepts/architecture` — Whole-system live boundary
- :doc:`/reference/determinism-contract` — Hash and replay identity contracts
