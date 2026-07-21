How to add or change reference data (parquet-canonical pipeline)
================================================================

.. note::
   Since the Phase-6 cutover (ADR098, 2026-07-20) the canonical reference
   sources are per-table parquet files plus ``schema.sql``, both registered in
   ``data-artifacts.yaml``. The SQLite file ``data/sqlite/marxist-data-3NF.sqlite``
   is a **build product** — never edit it in place.

Prerequisites
-------------

- The pinned toolchain (the builder hard-gates on SQLite 3.53.1): the repo's
  own vendored flake (ADR102) — run builder commands through
  ``mise run nix -- <cmd>`` or a venv built on the devshell interpreter.
- The data drive mounted (``mise run data:doctor`` green) for drive-sourced
  ingests.

Add a new table
---------------

1. Add the table's DDL to the schema by creating it in a scratch build and
   re-extracting — the canonical DDL is whatever
   ``tools/extract_reference_schema.py`` emits; ``schema.sql`` must be the
   fixed point of build→extract.
2. Add a catalog row in ``data-catalog.yaml`` (the per-table lineage registry;
   the catalog sentinel enforces catalog↔DB bijection).
3. Emit the table's parquet into ``dist/data-artifacts/`` and register it:
   ``mise run data:artifacts`` regenerates the manifest with per-file sha256
   pins.
4. Rebuild and verify::

       mise run data:build-db        # deterministic rebuild from sources
       mise run data:verify-build    # double-build byte identity
       mise run data:verify-roundtrip

5. Run ``mise run qa:regression`` — byte-identical, or STOP.

Change rows in an existing table (ingest)
-----------------------------------------

Loaders produce **sources**; only the builder produces the DB. Run any legacy
DB-writing loader through the wrapper::

    poetry run python tools/loader_to_sources.py \
        --loader <module_name_in_tools> \
        --tables <comma-separated affected tables>

The wrapper copies the build product to a scratch file, runs the loader
against the scratch (``--db-url sqlite:///<scratch>``), re-exports each
affected table as parquet, regenerates the manifest, and deletes the scratch.
The shared DB is never opened for write. A loader that exits nonzero aborts
loudly with nothing changed.

Then rebuild + verify as above, and flip the working DB only after
``qa:regression`` is green (backup first — see the ADR098 flip procedure).
If baselines move, that is a declared ceremony: ``test(baselines):`` commit
with a drift table and a ``Baselines: blessed(<slug>)`` trailer.

Gotchas (hard-won at the cutover)
---------------------------------

- **Never hand-type a sha256** — extract pins programmatically from the
  manifest and compare computed-vs-computed.
- The working copy's container bytes change on first open (WAL) **by
  design** — the container sha pins the *build product*; the working copy's
  guard is the per-table content-hash roundtrip.
- ``ingest_bea_imports`` (and loaders of its era) are one-shot, not
  idempotent: re-running against data that already contains their rows aborts
  on UNIQUE keys. Check the target table first.
- On a tmpfs-``/tmp`` box, VACUUM spills a full DB copy — the builder pins
  its temp dir next to the output; if a "database or disk is full" appears
  anyway, ``df`` the **output path's** filesystem, not ``/``.
- CI note: the nightly rebuild-verify leg runs inside the vendored flake's
  ``dataBuild`` devshell (``nix develop .#dataBuild``) so the runner's sqlite
  is always on-pin (ADR098; devshells vendored in-repo by ADR102).
