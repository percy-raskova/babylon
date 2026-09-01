Architecture Boundary
=====================

``CONSTITUTION.md`` v4.0.0 governs the architecture. ``NORTH_STAR.md`` gives
the game direction and gate order. This page describes the live boundary after
the one-way PostgreSQL authority cutover.

System Boundary
---------------

Babylon has these primary boundaries:

#. A pure Rust engine judges one weekly tick.
#. Live Rust BSL rules control causal changes. Executable shocks and player
   actions do not exist yet.
#. ``babylon-persistence`` owns authoritative game-managed PostgreSQL schema,
   writes, restart, and durability.
#. The frozen Python engine remains a behavioral reference. Python also owns
   data, AI, document, external-API, optimization, and local SQLite periphery.
#. Bevy remains an administrative viewer with no player action.

Ordinary BSL rules derive and write world data through governed causal
operations. External shocks must not write downstream results directly.
AI can parse, retrieve, and narrate. AI does not judge a game rule.

Live Rust Path
--------------

The shipping engine path is:

``babylon-kernel``
   Deterministic types and contracts.

``babylon-graph``
   Native relations, hyperedges, and canonical hashes.

``babylon-bsl``
   The BSL lexer, parser, checker, loader, and evaluator.

``babylon-tick``
   The weekly tick, replay identity, material state, and atomic publication.

``babylon-persistence``
   Rust-owned PostgreSQL activation, campaign foundation, checkpoint restart,
   typed semantic rows, commit markers, and Archive dirty receipts.

``babylon-client``
   The Bevy administrative viewer.

Each weekly tick runs on detached state and buffers its events. The tick becomes
observable only after all rule, hash, and persistence boundaries succeed.
``GraphStateHash`` identifies graph bytes only. ``NominalWorldHash`` also binds
completed time, allocator cursors, and the governed phase-schedule digest.
``TickContentHashV1`` binds the identified replay result.
``ReplayTickSession`` publishes ``TickContentHashV1`` atomically. Replay
identity and campaign durability identity are separate typed inputs.

Authoritative Persistence
-------------------------

``babylon-runtime`` is the sole production composition root. It activates the
Rust schema, creates or opens a durable replay runtime, advances a tick, and
commits the prepared ``CommittedTickEnvelopeV1``. Callers cannot submit a
pre-judged report for commit and cannot construct a second writer authority.

The activation ledger is append-only:

.. list-table::
   :header-rows: 1
   :widths: 20 25 55

   * - Ordinal
     - State
     - Meaning
   * - 1
     - ``prepared`` at epoch 8
     - Additive Rust schema and reference preparation completed.
   * - 2
     - ``rust_active`` at epoch 9
     - Legacy Python-managed relations were migrated or proved empty and
       retired; Rust owns game-managed PostgreSQL.

The ``rust_active`` row is the final activation statement before ``COMMIT``.
Activation is forward-only and idempotent. A durable active row permits only
the Rust composition root to reacquire write authority after restart.

.. Vale: these paragraphs preserve literal persistence and schema identifiers.
.. vale ste.UnapprovedWords = NO
.. vale ste.NounClusters = NO

The runtime owns three schemas:

``babylon_ref``
   Immutable geography, H3 cohorts, and exact reference artifacts.

``babylon_state``
   Campaign foundation, typed graph and material rows, events, checkpoints,
   ``tick_commit_v1``, and ``archive_dirty_receipt_v1``.

``babylon_meta``
   The authority ledger plus typed campaign and navigation metadata.

One marker-last transaction writes the complete typed tick estate, a full
checkpoint when required, exactly one Archive dirty receipt, and the commit
marker. The runtime acknowledges the tick only after ``COMMIT`` or exact
ambiguous-commit reconciliation. Retry must reproduce the same envelope bytes.

.. vale ste.NounClusters = YES
.. vale ste.UnapprovedWords = YES

Restart loads the campaign foundation or latest complete full checkpoint, then
replays a contiguous marker tail. A delta checkpoint is never a restore root.
Missing, duplicate, out-of-order, or digest-mismatched sections refuse before
the runtime resumes.

H3 Reader Boundary
------------------

Epoch 7 captured and proved the legacy H3 reader parity corpus. Epoch 9 has no
Python game-state reader edge and no compatibility projection. Rust installs
the exact reference cohort and Michigan dynamic foundation, then reads typed
relations directly.

Frozen Python Reference and Periphery
-------------------------------------

PER-48 is decided. The one-way cutover is complete. Rust owns authoritative
game-managed Postgres. Python continues only in the roles declared below.

ADR172 froze the Python engine. Its scenarios, property tests, traces, and
goldens remain behavioral contracts until a Rust or language-neutral contract
replaces them. ``RuntimeDatabase`` remains a separate mutable SQLite reference
store. The in-memory optimization package remains design-analysis periphery.

Python has no game-managed PostgreSQL DDL, DML, writer credential, migration
runner, compatibility adapter, or fallback after activation. Retained data and
document tooling may use dedicated stores that cannot mutate the governed game
schemas.

Client and Archive Boundary
---------------------------

The Bevy client still reads an administrative world view and displays the
nominal world hash. It does not submit a player intent.

Each committed tick emits an Archive dirty receipt. ``sim:archive`` installs the
client-owned semantic schema or checks its marker and relations. The Rust
Archive store binds each receipt to an exact dirty batch. It applies knowledge
grants in SQL, renders pages with the pinned strict template, and searches only
pages that the player knows. Later work adds broader dossier producers, the
player-facing retrieval surface, and a player decision loop that supports
replay. The persistence cutover and this first Archive slice do not include
those pieces.

Flow
----

Solid arrows are live. Dashed arrows are later gate work.

.. Vale: the Mermaid block contains literal crate and schema identifiers.
.. vale off

.. mermaid::

   flowchart LR
       REF["babylon_ref"] --> TICK["Rust replay tick"]
       BSL["BSL rules"] --> TICK
       EMPTY["Exact empty action batch"] --> TICK
       TICK --> IDENTIFIED["IdentifiedTickReportV1"]
       IDENTIFIED --> RUNTIME["DurableReplayRuntimeV1"]
       RUNTIME --> STATE["babylon_state typed rows"]
       STATE --> MARKER["tick_commit_v1"]
       STATE --> DIRTY["archive_dirty_receipt_v1"]
       MARKER --> VIEW["Bevy administrative viewer"]
       PY["Frozen Python reference"] --> SQLITE["RuntimeDatabase SQLite"]
       DIRTY -.-> ARCHIVE["Semantic Archive worker"]
       ARCHIVE -.-> CHOICE["Player decision"]

.. vale on

Invariants
----------

Tick identity
   Equal inputs produce equal graph, nominal-world, replay-tick, envelope, and
   typed semantic row bytes. Durability is established only by the marker.

Pure judgment
   Relation, BSL, and tick crates have no database dependency. Storage begins
   only after detached judgment succeeds.

Single authority
   No compatibility view, adapter, fallback, dual writer, dual storage, or
   runnable midpoint exists.

Native topology
   Hyperedges remain first-class public elements. Incidence data is an internal
   storage method.

Source honesty
   Each substantive value is ``Observed``, ``Derived``, ``Calibrated``, or
   ``Designed``.

Player relevance
   An administrative display cannot pass a game milestone. The persistence
   cutover is necessary infrastructure, not the playable decision loop.

Related Pages
-------------

- :doc:`/reference/persistence`
- :doc:`/concepts/persistence-architecture`
- :doc:`/concepts/topology`
- :doc:`/reference/bsl-language`
