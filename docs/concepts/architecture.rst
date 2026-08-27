Architecture Boundary
=====================

``CONSTITUTION.md`` v4.0.0 governs the architecture. ``NORTH_STAR.md`` gives
the game direction and the gate order. The page separates live parts from
planned parts.

System boundary
---------------

Babylon has these primary boundaries:

#. A pure Rust engine makes one weekly tick.
#. Live Rust BSL rules control causal changes. No executable shock vocabulary
   or shock content exists.
#. In the planned action slice, BSL will let actions run, charge costs, choose
   targets, and encode political results.
#. The frozen Python path has mutable SQLite and atomic Postgres persistence.
#. Gate 3 will add the full v4 Rust commit and Archive boundary after game
   judgment.
#. Bevy is an administrative viewer.
#. The planned action slice will make Bevy send player intent.

A shock must not write its downstream result. Ordinary BSL rules derive and
write world data through governed causal operations. AI can parse, retrieve, and
narrate. AI does not judge a game rule.

Live Rust path
--------------

The Rust workspace contains the shipping engine path:

``babylon-kernel``
   Deterministic types and contracts.

``babylon-graph``
   Native relations, hyperedges, and canonical hashes.

``babylon-bsl``
   The BSL lexer, parser, checker, loader, and evaluator.

``babylon-tick``
   The weekly tick, atomic ``TickSession``, and in-memory ``TickReport``.

``babylon-client``
   The Bevy administrative viewer.

Each weekly tick runs on a detached graph and buffers its events. The session
publishes graph state, allocator cursors, events, and completed time only after
all rules and hash boundaries succeed. ``GraphStateHash`` identifies graph
bytes only. ``NominalWorldHash`` adds completed time, allocator cursors, and the
governed phase-schedule digest. It is the hash the Bevy viewer shows after a
committed tick.

.. Vale: these paragraphs preserve literal graph and identity terms.
.. vale ste.UnapprovedWords = NO

The database-free ``ReplayTickSession`` adds the canonical replay identity. It
requires ``ReplaySessionIdV1``, ``ReplaySeed``, RNG V2, content and reference
digests, stable element names, and the exact empty accepted-action batch.
``ReplayTickSession`` publishes ``TickContentHashV1`` atomically with the
detached graph, events, completed time, and nested identity evidence. It never
nests ``GraphStateHash`` or ``NominalWorldHash`` inside that replay hash.

.. vale ste.UnapprovedWords = YES

This boundary provides in-memory rollback. ``babylon-persistence`` now defines
the database-free ``CommittedTickEnvelopeV1`` byte contract and complete-payload
retry contract. No tick runtime composes the envelope. No Postgres acknowledgment
of durability exists.

The Bevy client draws the county atlas and moves ticks forward.
It has lenses, events, causal beats, and hash diagnostics. Committed BSL has no
player action. The client remains on ``TickSession`` and does not complete a
game decision cycle.

Frozen Python reference
-----------------------

ADR172 froze the engine in Python. The engine serves as a behavioral reference.
Its scenarios, property tests, traces, and goldens specify frozen behavior and
persisted replay.
Rust ports must keep that behavior or record a replacement decision.

Python also prepares reference data and runs selected periphery. The frozen
engine uses Pydantic and ``rustworkx`` through ``BabylonGraph``. Python is not
the shipping game engine.

Data boundary now
-----------------

.. Vale: these paragraphs preserve literal persistence and schema identifiers.
.. vale ste.UnapprovedWords = NO
.. vale ste.NounClusters = NO

Parquet sources and the deterministic reference SQLite database are build
artifacts. The Python ``RuntimeDatabase`` is a separate, mutable SQLite store
for per-run snapshots and replay.

The Python Postgres path already has ``PerTickTransactionEnvelope`` and
``persist_tick_atomic``. It writes graph state, events, envelope rows, and a
``tick_commit`` marker in one transaction. A partial ``babylon_meta`` schema
stores campaign and navigation state. Python also has an action pipeline. None
of these predecessors is the full v4 Rust BSL-to-Bevy decision loop.

.. vale ste.NounClusters = YES
.. vale ste.UnapprovedWords = YES

Planned Gate 3 boundary
-----------------------

Gate 3 plans the full v4 Rust persistence and Archive boundary with three owned
schemas:

``babylon_ref``
   Fixed geography and taxonomy, with H3 cells and overlap weights.

``babylon_state``
   Campaign data, tick commits, action receipts, events, and the Archive outbox.

``babylon_meta``
   Player knowledge, hidden facts, Archive pages, links, and retrieval chunks.

.. Vale: this paragraph preserves literal Linear IDs and persistence terms.
.. vale ste.UnapprovedWords = NO
.. vale ste.NounClusters = NO

The plan adds one bounded writer. One transaction will write the Rust commit
envelope, campaign data, outbox rows, and ``tick_commit``. The client will
change its durable tick only after a database acknowledgment.

.. Vale: the accepted Linear status uses a passive state label.
.. vale strunk.ActiveVoice = NO
.. vale ste.PassiveVoice = NO

PER-48 is decided.

.. vale ste.PassiveVoice = YES
.. vale strunk.ActiveVoice = YES

Python remains the sole live writer until cutover. After the one-way cutover,
Rust owns authoritative game-managed Postgres connections, migrations, and
writes. Python continues to own data builds, AI, document and wiki transforms,
external API work, and CLI periphery, with read-only transition observers.

.. vale ste.NounClusters = YES
.. vale ste.UnapprovedWords = YES

An Archive worker will read outbox rows in tick order. Each query will include
campaign and knowledge context. SQL will apply fog before retrieval.

.. Vale: this paragraph preserves literal schema and client-boundary terms.
.. vale ste.UnapprovedWords = NO
.. vale ste.NounClusters = NO

The first planned cycle starts with a county or city dossier and a decision. A
new tick produces an effect and an updated dossier. The complete schema split,
Rust commit envelope, Archive outbox worker, BSL-Bevy decision cycle, and Bevy
player actions have not landed.

.. vale ste.NounClusters = YES
.. vale ste.UnapprovedWords = YES

Flow
----

The solid arrows show the live path. Dashed arrows show Gate 3 plans.

.. Vale: the Mermaid block contains literal crate and schema identifiers.
.. vale off

.. mermaid::

   flowchart LR
       REF["Reference data"] --> TICK["Rust weekly tick"]
       BSL["BSL rules"] --> TICK
       TICK --> REPORT["TickReport"]
       REPORT --> VIEW["Bevy viewer"]
       REF --> REPLAY["Rust replay tick"]
       BSL --> REPLAY
       EMPTY["Exact empty action batch"] --> REPLAY
       REPLAY --> IDENTIFIED["IdentifiedTickReportV1"]
       PY["Frozen Python tick"] --> OLDENV["PerTickTransactionEnvelope"]
       OLDENV --> PG["Postgres tick_commit"]
       PY --> SQLITE["RuntimeDatabase SQLite"]
       IDENTIFIED -. "Gate 3" .-> ENV["CommittedTickEnvelope"]
       ENV -.-> STATE["babylon_state"]
       STATE -.-> OUTBOX["Archive outbox"]
       OUTBOX -.-> ARCHIVE["Semantic Archive"]
       ARCHIVE -.-> CHOICE["Player choice"]

.. vale on

Invariants
----------

.. Vale: this invariant preserves literal graph and identity terms.
.. vale ste.UnapprovedWords = NO
.. vale ste.NounClusters = NO
.. vale strunk.ActiveVoice = NO
.. vale ste.PassiveVoice = NO

Tick identity
   Equal inputs produce equal graph, nominal-world, and replay-tick bytes and
   hashes. Replay identity and campaign durability identity are separate typed
   inputs. Gate 3 will persist the accepted replay evidence. It will not
   redefine the bytes.

.. vale ste.PassiveVoice = YES
.. vale strunk.ActiveVoice = YES
.. vale ste.UnapprovedWords = YES
.. vale ste.NounClusters = YES

Pure judgment
   The relation, BSL, and tick crates have no database dependency. Storage starts
   after the tick copy passes its checks.

Native topology
   Hyperedges are first-class public elements. Incidence data is an internal
   storage method.

Source honesty
   Each substantive value is ``Observed``, ``Derived``, ``Calibrated``, or
   ``Designed``.

Knowledge boundary
   Archive and narrative data must not change material truth. Retrieval must
   not show facts that the campaign has not learned.

Player relevance
   Each game display must answer a decision question. An administrative display
   cannot pass a game milestone.

Related pages
-------------

.. Vale: the following roles contain literal Sphinx document paths.
.. vale ste.Ambiguity = NO

- :doc:`/concepts/persistence-architecture`
- :doc:`/reference/persistence`
- :doc:`/concepts/topology`
- :doc:`/reference/bsl-language`

.. vale ste.Ambiguity = YES
