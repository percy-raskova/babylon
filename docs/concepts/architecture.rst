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
   The weekly tick, ``TickSession``, and in-memory ``TickReport``.

``babylon-client``
   The Bevy administrative viewer.

The Bevy client draws the county atlas and moves ticks forward. It has lenses,
events, causal beats, and hash diagnostics. Committed BSL has no player action.
The client does not complete a game decision cycle.

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
       PY["Frozen Python tick"] --> OLDENV["PerTickTransactionEnvelope"]
       OLDENV --> PG["Postgres tick_commit"]
       PY --> SQLITE["RuntimeDatabase SQLite"]
       REPORT -. "Gate 3" .-> ENV["CommittedTickEnvelope"]
       ENV -.-> STATE["babylon_state"]
       STATE -.-> OUTBOX["Archive outbox"]
       OUTBOX -.-> ARCHIVE["Semantic Archive"]
       ARCHIVE -.-> CHOICE["Player choice"]

.. vale on

Invariants
----------

Tick identity
   Equal inputs and reference digests produce equal bytes and hashes.

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
