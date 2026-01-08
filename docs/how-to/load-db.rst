=======================
How to Load the 3NF DB
=======================

This guide shows how to load the Babylon 3NF DuckDB database using the
existing CLI and task runner. It follows the Diataxis how-to style: short,
goal-oriented steps you can run in your shell.

Overview
========

The data pipeline is driven by:

- ``mise`` tasks (convenient shortcuts)
- ``babylon.data.cli`` (Typer-based CLI)
- A hybrid loader strategy (API for recent years, files for historical)

Key commands you will use:

- ``mise run data:readiness`` for checks (aliases: ``data:preflight``, ``data:schema-check``)
- ``mise run data:load`` for full ingestion
- ``mise run data:qcew`` for QCEW only
- ``mise run data:employment-industry`` for BLS area/industry files
- ``mise run data:dot-hpms`` for DOT HPMS road segments
- ``mise run data:lodes`` for LODES crosswalks

Prerequisites
=============

Environment variables
---------------------

Required:

- ``FRED_API_KEY`` (FRED API)
- ``ENERGY_API_KEY`` (EIA API, optional if using MER Excel files)

Optional but recommended:

- ``CENSUS_API_KEY`` (Census API rate limits)

Required only for FCC downloads:

- ``FCC_USERNAME``
- ``FCC_API_KEY``

Note: QCEW API ingestion does **not** require a BLS API key. The current QCEW
client uses the BLS QCEW Open Data API (no authentication).

Required files
--------------

These files must exist before running full ingestion:

- ``data/census/cbsa_delineation_2023.xlsx``
- ``data/imperial_rent/country.xlsx``
- ``data/raw_mats/commodities/*.csv`` or ``data/raw_mats/minerals/*.csv``
- ``data/fcc/downloads/*/national/*.csv`` (if loading FCC data)
- ``data/qcew/*.csv`` or ``data/qcew/*.xlsx`` (only if loading QCEW for years < 2021)
- ``data/employment_industry/*.annual.by_area/*.csv``
- ``data/dot/HPMS_Spatial*Sections*.csv``
- ``data/lodes/us_xwalk.csv`` (or ``us_xwalk.csv.gz``)
- ``data/energy/Table *.xlsx`` (if ENERGY_API_KEY is not set)

If you do not have historical QCEW CSVs, you can run QCEW API-only years.

Quick Start: Full Load
======================

1) Run ingest readiness checks (with endpoint validation and schema repair):

.. code-block:: bash

   mise run data:readiness -- --online

2) Download FCC national summary (only required if you plan to load FCC data):

.. code-block:: bash

   mise run data:fcc-download -- --national

3) Load everything:

.. code-block:: bash

   mise run data:load

If schema checks fail due to missing DuckDB SQLAlchemy dialect, you can skip
schema checks during load:

.. code-block:: bash

   mise run data:load -- --no-schema-check

To report schema drift without applying repairs, use:

.. code-block:: bash

   mise run data:readiness -- --no-repair

Run QCEW with API-Only Years
============================

If you only want QCEW via API (2021+), use:

.. code-block:: bash

   mise run data:qcew -- --years 2021-2024

This avoids the need for historical CSV/Excel files under ``data/qcew``.

Verify the Load
===============

Recommended checks after a full load:

.. code-block:: bash

   mise run data:readiness -- --no-repair
   mise run test:unit

For the full non-AI test suite:

.. code-block:: bash

   mise run test:all

Common Troubleshooting
======================

Missing CBSA file
-----------------

Ensure the file exists at:

- ``data/census/cbsa_delineation_2023.xlsx``

If it is a Git LFS pointer, run:

.. code-block:: bash

   git lfs pull --include "data/census/cbsa_delineation_2023.xlsx"

Missing FCC downloads
---------------------

Run:

.. code-block:: bash

   mise run data:fcc-download -- --national

Then re-run ``mise run data:fcc`` or ``mise run data:load``.

Missing historical QCEW files
------------------------------

Use API-only years:

.. code-block:: bash

   mise run data:qcew -- --years 2021-2024

Or download historical CSV/Excel files into ``data/qcew`` and run the full loader.

How the Pipeline Works (Short Version)
======================================

- ``data:readiness`` validates environment variables, required files, and schema drift.
- ``data:load`` initializes the normalized schema and loads all sources.
- QCEW uses API for 2021+ and CSVs for earlier years (hybrid loader).
- FCC uses downloaded CSVs (the download step is separate).

Useful References
=================

- CLI entry point: ``src/babylon/data/cli.py``
- QCEW loader: ``src/babylon/data/qcew/loader_3nf.py``
- FCC downloader: ``src/babylon/data/cli.py`` (``fcc_download`` command)
- Readiness checks: ``src/babylon/data/preflight.py``,
  ``src/babylon/data/normalize/schema_check.py``
