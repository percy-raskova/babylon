Persistence Reference
=====================

Babylon has one authoritative game-state persistence path: the Rust
``babylon-persistence`` crate composed by ``babylon-runtime``. Python
persistence is non-authoritative periphery.

Rust Composition Root
---------------------

The binary accepts these commands:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Command
     - Behavior
   * - ``preflight``
     - Validate the target and inspect the current schema epoch without
       mutation.
   * - ``activate``
     - Run the forward-only epoch 8 preparation and epoch 9 authority cutover.
   * - ``bootstrap``
     - Idempotently activate the same Rust persistence boundary.
   * - ``run --ticks N``
     - Activate, open or create the Michigan durable campaign, and commit
       ``N`` Rust ticks.
   * - ``probe``
     - Show the authority ledger and durable campaign tail.
   * - ``archive``
     - Inspect durable Archive dirty receipts without mutating campaigns.
   * - ``michigan-smoke``
     - Commit and restart the Michigan campaign across the 60-tick proof.

The corresponding repository tasks are ``db:bootstrap``,
``sim:e2e-michigan``, ``sim:probe``, ``sim:archive``, and
``qa:michigan-rollover-smoke``.

Authority Activation
--------------------

``activate_rust_persistence_v1`` is the sole authority transition. It installs
the exact H3 reference cohort, prepares epoch 8, proves the legacy reader and
relation dispositions, performs the epoch 9 destructive migration, and commits
the ``rust_active`` authority-ledger row last.

The ledger relation is ``babylon_meta.persistence_authority_ledger``. Its only
legal history is:

#. ``prepared`` at schema epoch 8.
#. ``rust_active`` at schema epoch 9, bound to the exact prepared-row digest.

The transition cannot skip preparation, update or delete a ledger row, return
to Python authority, or construct a second migrator command. Re-running
activation after a durable active row is an idempotent authority reacquisition.

Durable Runtime
---------------

``DurableReplayRuntimeV1`` owns adjudication and commit as one closed
composition. Its primary operations are:

``create``
   Capture a new ``CampaignFoundationV1`` from an exact replay session and
   content bundle.

``open``
   Hydrate a campaign foundation or complete full checkpoint and replay its
   contiguous committed tail.

``advance_and_commit``
   Judge the next tick into a private runtime-owned buffer, prepare typed rows,
   write the marker-last transaction, and publish the receipt only after
   acknowledgement.

The caller-provided sink is post-acknowledgement only. It remains byte-identical
after refusal, rollback, or unresolved commit ambiguity. A caller cannot commit
an externally prepared report.

Transaction Boundary
--------------------

One tick transaction contains:

- typed graph rows;
- typed material-state rows;
- successful events;
- the required checkpoint sections;
- exactly one ``archive_dirty_receipt_v1`` row; and
- one ``tick_commit_v1`` marker, written last.

All ordered collections use explicit positions or primary-key byte order.
Floating-point codecs reject non-finite values and normalize negative zero.
Retry reads typed rows, reconstructs the complete envelope, and requires exact
byte identity. The runtime never infers durability from ``MAX`` over a state
table.

Foundation and Restart
----------------------

``CampaignFoundationV1`` stores the exact stable graph, world registers,
resolver manifest, prepared environment, replay identity, seed, content and
reference digests, and content bundle. Reference artifacts resolve only through
their exact database key and SHA-256 digest; ambient paths, network fetches,
latest-version lookup, and digest fallback are refused.

A full checkpoint has nine ordered sections. Only a complete full-tag manifest
is a restart root. Delta checkpoints cannot act as roots. Restart refuses any
missing, duplicate, out-of-order, or digest-mismatched section, then replays a
contiguous marker tail and resumes at the last acknowledged tick plus one.

H3 and Schema Boundary
----------------------

Epoch 7 preserves the exact parity evidence for the retired Python reader
estate. Epoch 9 exposes no Python game-state reader and no compatibility view.
Rust reads the typed ``babylon_ref`` and ``babylon_state`` relations directly.

The authoritative schemas are:

``babylon_ref``
   H3 cells, county/place overlaps, immutable cohorts, and exact reference
   artifacts.

``babylon_state``
   Campaign foundation, typed semantic state, checkpoints, commit markers, and
   Archive dirty receipts.

``babylon_meta``
   Authority, campaign catalog, watchlist, jumplist, and breadcrumb metadata.

Python Persistence Periphery
----------------------------

The ``babylon.persistence`` Python package exports only non-authoritative
surfaces:

``RuntimeDatabase``
   Mutable SQLite for frozen local reference runs and tests.

``RuntimePersistence``
   The frozen local SQLite protocol.

``PgVectorStore`` and ``VectorStoreProtocol``
   Semantic document storage in a dedicated periphery estate.

``ReadOnlyPostgres``
   A read-only periphery boundary. It is not a transition game-state reader.

``RUNTIME_SCHEMA_DDL``
   SQLite reference schema only.

The retired ``babylon.persistence.postgres_runtime`` namespace exports nothing.
Python has no authoritative game-state PostgreSQL writer, migration runner,
compatibility adapter, or fallback.

Verification
------------

Use the narrow contract first, then the serialized repository gates:

.. code-block:: bash

   uv run python tools/verify_rust_persistence_cutover_v1.py
   cd rust && cargo test -p babylon-persistence --locked
   mise run rust:check-no-docs
   BABYLON_LEGACY_ADOPTER_LIVE_FOCUS=pr tools/run_rust_legacy_adopter_pg.sh

The live adopter command creates a disposable pinned PostgreSQL/H3 runtime and
verifies clean activation, restart, rollback, ambiguous-commit reconciliation,
installed mutations, and residue-free cleanup.

Contracts
---------

- ``contracts/rust_persistence_cutover_v1.yaml``
- ``contracts/h3_reader_cutover_v1.yaml``
- ``contracts/committed_tick_envelope_v1.yaml``
- ``contracts/michigan_dynamic_hex_foundation_v1.yaml``

See Also
--------

- :doc:`/concepts/architecture`
- :doc:`/concepts/persistence-architecture`
- :doc:`/reference/determinism-contract`
