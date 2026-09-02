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
     - Make sure the required epoch 8/9 predecessor exists. Then run the
       dedicated epoch 10 preparation and epoch 11 V2 authority cutover.
   * - ``bootstrap``
     - Idempotently activate the same Rust persistence boundary.
   * - ``run --ticks N``
     - Activate, open or create the Michigan durable campaign, and commit
       ``N`` Rust ticks.
   * - ``probe``
     - Show the authority ledger, selected campaign tail when configured, and
       separately labeled database-wide totals.
   * - ``archive``
     - Install the client-owned semantic Archive schema or check its marker and
       relations. Then report durable receipts, grants, consumptions, and pages.
       This command does not change campaign material state.
   * - ``michigan-smoke``
     - Commit and restart the Michigan campaign across the 60-tick proof.

The corresponding repository tasks are ``db:bootstrap``,
``sim:e2e-michigan``, ``sim:probe``, ``sim:archive``, and
``qa:michigan-rollover-smoke``.

Authority Activation
--------------------

``activate_rust_persistence_v2`` is the sole current authority transition. It
establishes the exact H3 reader and epoch 8/9 predecessor, then runs a dedicated
two-step V2 activation. Epoch 10 installs the additive receipt and event schema,
records ``babylon_meta.committed_tick_v2_incompatible_inventory``, and refuses
any incompatible campaign or tick rows. Epoch 11 removes the obsolete empty V1
event relations, constrains the live commit marker to envelope layout 2, and
commits the V2-active authority row last.

The current ledger relation is
``babylon_meta.committed_tick_v2_authority_ledger``. Its only legal history is:

#. ``Prepared`` at epoch 10. It binds the epoch 9 predecessor, V2 cutover
   contract, and epoch 11 reader migration digests.
#. ``Active`` at activation epoch 11. It binds the same contract and reader
   digests, plus the exact prepared-row digest.

The active contract pins the epoch 10 and epoch 11 migration digests. The
ledger's contract digest binds the complete V2 activation law and the exact
epoch 9 predecessor migration. Its reader contract digest directly binds the
migration that removes the V1 reader surface.

Epoch 9 is one ``READ COMMITTED`` transaction. It takes ``ACCESS EXCLUSIVE``
locks on each present legacy relation and on the closed opaque predecessor set
before counting from a fresh post-wait snapshot. It retains those locks through
the empty disposition, deletion, active predecessor row, and commit. The census
sees a concurrent writer that commits while a lock is pending. The resulting
nonzero count rolls back the complete activation and preserves the relation and
its rows.

Epoch 11 remains ``SERIALIZABLE``. Its top-level ``ACCESS EXCLUSIVE`` lock runs
before any query or data modification. The runtime acquires the inventory
snapshot only after a pending lock succeeds.

The transition cannot skip preparation, update or delete a ledger row, return
to Python authority, or construct a second migrator command. Re-running
activation after a durable active row is an idempotent authority reacquisition.
The predecessor ``babylon_meta.persistence_authority_ledger`` and its epoch 8/9
rows remain historical cutover evidence. They are not the live V2 writer gate.

Durable Runtime
---------------

``DurableReplayRuntimeV2`` owns adjudication and commit as one closed
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

- the exact action-batch source.
- the six ordered ``CommittedTickEnvelopeV2`` families: graph, material state,
  event, choice receipt, checkpoint, and Archive dirty receipt.
- one ``babylon_state.tick_commit`` marker with envelope layout 2, written last.

``ChoiceReceiptV1`` rows record the ordered carrier, exact Mass values, ticket
intervals, draw ticket, selected outcome, and allocation and instance digests.
Committed V2 event metadata retains the emitting rule and, for a finite
projection, its engine-derived choice-receipt ordinal. Authored event payloads
never contain probability. The transaction writes choice receipts and projected
events before checkpoint and Archive rows. The runtime writes no durable row
after the commit marker.

The receipt family uses ``tick_choice_receipt_v1``,
``tick_choice_receipt_branch_v1``, and
``tick_choice_receipt_carrier_element_v1``. The event family uses
``tick_event_v2`` and ``tick_event_field_v2``. All five relations are in
``babylon_state``.

All ordered collections use explicit positions or primary-key byte order.
Floating-point codecs reject non-finite values and normalize negative zero.
Retry reads typed rows, reconstructs the complete V2 envelope, and requires
exact byte identity. The runtime never infers durability from ``MAX`` over a
state table. The V2-only reader refuses any marker whose
``envelope_layout_version`` is not 2.

Foundation and Restart
----------------------

``CampaignFoundationV1`` stores the exact stable graph, world registers,
resolver manifest, prepared environment, replay identity, seed, content and
reference digests, and content bundle. Reference artifacts resolve only through
their exact database key and SHA-256 digest; ambient paths, network fetches,
latest-version lookup, and digest fallback are refused.

A full checkpoint has nine ordered sections. Only a complete full-tag manifest
is a restart root. Delta checkpoints cannot act as roots.

Restart reconstructs the latest full checkpoint's six-family V2 envelope from
typed rows. It compares the digest with the marker and then restores the nine
checkpoint sections. Next, it re-executes every later marker-backed tick in
contiguous order. Each newly prepared envelope must match the stored envelope
exactly. Restart resumes at the last acknowledged tick plus one.

The Archive dirty receipt participates in the envelope comparison. Restart does
not use historical semantic Archive pages, grants, consumptions, or citations
as reconstruction input. Thus restart makes no claim about their historical
integrity.

H3 and Schema Boundary
----------------------

Epoch 7 preserves the exact parity evidence for the retired Python reader
estate. Epoch 9 removed the Python game-state reader and compatibility view.
Dedicated epoch 10 prepared the V2-only committed-tick schema, and epoch 11
activated it. Rust reads the typed ``babylon_ref`` and ``babylon_state``
relations directly.

The authoritative schemas are:

``babylon_ref``
   H3 cells, county/place overlaps, immutable cohorts, and exact reference
   artifacts.

``babylon_state``
   Campaign foundation, typed semantic state, V2 events, choice receipts,
   checkpoints, commit markers, and Archive dirty receipts.

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

   uv run --frozen python tools/verify_rust_persistence_cutover_v2.py
   cd rust && cargo test -p babylon-persistence --locked
   mise run rust:check-no-docs
   BABYLON_LEGACY_ADOPTER_LIVE_FOCUS=pr tools/run_rust_legacy_adopter_pg.sh

The live adopter command creates a disposable pinned Postgres 17/PostGIS 3.5
runtime. It verifies clean activation, restart, rollback, ambiguous-commit
reconciliation, installed mutations, and residue-free cleanup.

Contracts
---------

The active contract and these two tests pin the live V2 boundary:

- ``contracts/rust_persistence_cutover_v2.yaml``
- ``rust/crates/babylon-persistence/tests/committed_tick_envelope_v2_contract.rs``
- ``rust/crates/babylon-persistence/tests/committed_tick_v2_postgres_activation_contract.rs``

``tools/verify_rust_persistence_cutover_v1.py`` is an offline historical
verifier only. These older contracts keep their V1 names for predecessor and
unchanged inner-codec evidence:

- ``contracts/rust_persistence_cutover_v1.yaml``
- ``contracts/h3_reader_cutover_v1.yaml``
- ``contracts/committed_tick_envelope_v1.yaml``
- ``contracts/michigan_dynamic_hex_foundation_v1.yaml``

See Also
--------

- :doc:`/concepts/architecture`
- :doc:`/concepts/persistence-architecture`
- :doc:`/reference/determinism-contract`
