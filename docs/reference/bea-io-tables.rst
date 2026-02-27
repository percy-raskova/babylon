.. _bea-io-tables:

=====================================
BEA Input-Output Tables
=====================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Reference for the Bureau of Economic Analysis (BEA) Input-Output data files
used in Feature 025, including file inventory, XLSX structure, the coefficient
computation formula, and the ``BEAIOLoader`` API.

For the theoretical background, see :ref:`leontief-analysis`.
For the schema tables these populate, see :ref:`tensor-hierarchy-schema`.

----

Data Overview
=============

The BEA publishes annual Input-Output accounts at three levels of industry
detail: Detail (~400 industries), Summary (~70 industries), and Sector (~15).
Babylon uses the **Summary level** because it aligns with the four-Marxian-
department aggregation (see :ref:`bea-department-mapping`).

Files are downloaded from the BEA I-O Accounts data page and stored in
``data/input-output/`` relative to the project root. The files are large
multi-sheet XLSX workbooks, one sheet per year.

----

File Inventory
==============

.. list-table:: BEA I-O Data Files in ``data/input-output/``
   :header-rows: 1
   :widths: 45 55

   * - File path
     - Contents
   * - ``make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx``
     - **Primary source** for BEAIOLoader. Use table at Producers' prices,
       Summary level. Multi-sheet XLSX, one sheet per year (1997–2024).
       Contains commodity-by-industry intermediate use data.
   * - ``make-use/IOUse_Before_Redefinitions_PUR_Summary.xlsx``
     - Use table at Purchasers' prices, Summary level. Not used by default.
   * - ``make-use/IOMake_Before_Redefinitions_PRO_Summary.xlsx``
     - Make table, Summary level (industry-by-commodity output structure).
   * - ``make-use/IOUse_Before_Redefinitions_PRO_Sector.xlsx``
     - Use table at Producers' prices, Sector level (~15 industries).
   * - ``make-use/IOMake_Before_Redefinitions_PRO_Sector.xlsx``
     - Make table, Sector level.
   * - ``supply-use/Supply_Summary.xlsx``
     - Supply table, Summary level.
   * - ``supply-use/Use_Summary.xlsx``
     - Use table (supply-use framework), Summary level.
   * - ``total-domestic-requirements/IxI_TR_Summary.xlsx``
     - Industry-by-industry total requirements (Leontief inverse as published
       by BEA). Useful for validation against ``DefaultLeontiefComputer``.
   * - ``total-domestic-requirements/CxC_TR_Summary.xlsx``
     - Commodity-by-commodity total requirements, Summary level.
   * - ``total-domestic-requirements/IxI_Domestic_Summary.xlsx``
     - Domestic-only total requirements (excludes imports), Summary level.

**Loader default:** ``BEAIOLoader`` reads only
``make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx``.

----

XLSX Row Structure
==================

Each sheet in the Use table XLSX (one sheet per year) follows this fixed
row layout (0-indexed):

.. list-table:: BEA I-O XLSX Row Structure
   :header-rows: 1
   :widths: 10 30 60

   * - Row
     - Content
     - Example
   * - 0
     - Title string
     - ``"Use of Commodities by Industries Before Redefinitions..."``
   * - 1
     - Units
     - ``"(Millions of dollars)"``
   * - 2
     - Source
     - ``"Bureau of Economic Analysis"``
   * - 3
     - Year
     - ``"2021"``
   * - 4
     - Empty
     - (blank row)
   * - 5
     - Column codes
     - ``None, "Commodities/Industries", "1100A1", "1130A1", ..., "T001", ...``
   * - 6
     - Column names
     - ``"IOCode", "Description", "Farms", "Forestry...", ...``
   * - 7+
     - Data rows
     - ``"1100A1", "Farms", 12.3, 0.0, ..., 156.7, ...``

**Column extraction:** Industry columns start at column index 2 of row 5.
Final-demand columns (prefixed ``F``) are excluded. The parser identifies
industry columns as those whose row-5 code does not start with ``F``.

**Row codes:** Each data row's first cell (column 0) is the IOCode. Special
rows are excluded from the industry list:

- ``T001``–``T020``: Total/subtotal rows (intermediate totals, final demand
  totals, gross output total T019)
- ``V001``–``V006``: Value-added rows (compensation, gross operating surplus, etc.)

Only rows whose IOCode is not in the ``_SKIP_CODES`` set are treated as
industry rows.

Missing Data
------------

BEA uses the string ``'...'`` to indicate suppressed or unavailable data.
The loader converts ``'...'`` to ``0.0``. This understates inter-industry
linkages in sectors with incomplete survey coverage but is the conservative
default.

----

Coefficient Computation
========================

The Use table contains raw dollar values: Use[i,j] = millions USD of commodity
*i* used by industry *j* as intermediate input.

The direct requirements coefficient is:

.. math::

   A[i, j] = \frac{\text{Use}[i, j]}{\text{GrossOutput}[j]}

**Gross output source:** Row T019 (``"T019"`` IOCode) contains gross output by
industry, if present. The loader reads this row into a ``gross_output`` dict
mapping industry code → gross output value (minimum 1.0 to avoid division by
zero).

**Fallback when T019 is absent:** If T019 is not found, gross output is
approximated as column sum: total intermediate use plus value-added rows:

.. math::

   \text{GrossOutput}[j] \approx \sum_i \text{Use}[i, j] + \text{ValueAdded}[j]

This fallback is less accurate but produces valid (if slightly off) coefficients.

----

BEAIOLoader API
================

.. class:: BEAIOLoader

   Loader for BEA I-O coefficients into the 3NF SQLite schema.

   Reads ``IOUse_Before_Redefinitions_PRO_Summary.xlsx`` from
   ``data/input-output/make-use/``. Each sheet (named by year, e.g., ``'1997'``,
   ``'2021'``) is parsed and loaded independently.

   Prerequisite: ``dim_bea_industry`` must be pre-populated by
   ``BEANationalLoader`` before BEAIOLoader can run. The industry lookup maps
   BEA codes to ``bea_industry_id`` values.

   .. method:: __init__(config=None, data_dir=None)

      :param config: ``LoaderConfig`` for batch size and operational settings.
         Default: ``LoaderConfig()`` with ``batch_size=1000``.
      :param data_dir: Base data directory. Default: ``Path("data")`` relative
         to project working directory.

   .. method:: load(session, reset=True, verbose=True, **kwargs) -> LoadStats

      Load BEA I-O coefficients into 3NF schema.

      :param session: SQLAlchemy ``Session`` connected to the normalized DB.
      :param reset: If ``True``, delete existing records in
         ``fact_bea_io_coefficient`` and ``dim_bea_io_table_type`` before
         loading. Default: ``True``.
      :param verbose: If ``True``, log progress per sheet. Default: ``True``.
      :param kwargs: Ignored (present for interface compatibility).
      :returns: ``LoadStats`` with fields:

         - ``dimensions_loaded["dim_bea_io_table_type"]``: 1 (USE record)
         - ``facts_loaded["fact_bea_io_coefficient"]``: total coefficient rows
         - ``files_processed``: number of year sheets successfully parsed
         - ``errors``: list of error strings (empty on success)

      :raises: Does not raise; errors are appended to ``LoadStats.errors``.

   **Tables populated:**

   - ``dim_bea_io_table_type``: Creates/retrieves the ``USE`` record.
   - ``fact_bea_io_coefficient``: Inserts non-zero coefficient rows for each
     year via upsert (conflict key: ``uq_bea_io_coeff``).

   **Year range:** Sheets named with valid years (1990–2030) are processed.
   Sheet names that do not parse as integers in this range are skipped.

   **Example:**

   .. code-block:: python

      from babylon.data.bea.io_loader import BEAIOLoader
      from babylon.data.reference.database import get_session_factory

      loader = BEAIOLoader()
      session_factory = get_session_factory()
      with session_factory() as session:
          stats = loader.load(session)
      print(f"Loaded {stats.facts_loaded['fact_bea_io_coefficient']} coefficients")
      print(f"Sheets processed: {stats.files_processed}")

IOMatrixParser API
-------------------

.. class:: IOMatrixParser

   Internal parser for BEA I-O XLSX row data. Used by ``BEAIOLoader``; can be
   used independently for custom XLSX processing.

   .. method:: parse_rows(rows) -> tuple[list[str], np.ndarray]

      Parse a list of row tuples (from ``openpyxl iter_rows(values_only=True)``)
      into industry codes and coefficient matrix.

      :param rows: List of row tuples. Expected format: 7 header rows then data.
      :returns: Tuple of ``(industries, matrix)`` where:

         - ``industries``: Ordered list of BEA industry codes (columns).
         - ``matrix``: Direct requirements matrix A, shape ``(n, n)``,
           ``float64``. Zero if insufficient data.

How to Obtain the Data
======================

BEA I-O data files are **already included** in the repository under
``data/input-output/``. No manual download is required.

If refreshing to a newer BEA release:

1. Go to `<https://www.bea.gov/industry/input-output-accounts-data>`_
2. Download "Use Tables/Before Redefinitions/Producers' Prices/Summary" XLSX
3. Replace ``data/input-output/make-use/IOUse_Before_Redefinitions_PRO_Summary.xlsx``
4. Re-run ``BEAIOLoader.load()``

----

Related Documentation
=====================

- :ref:`leontief-analysis` — Theory behind the direct requirements coefficient
- :ref:`tensor-hierarchy-schema` — ``dim_bea_io_table_type`` and
  ``fact_bea_io_coefficient`` table definitions
- :ref:`bea-department-mapping` — BEA industry to Marxian department mapping
- :ref:`tensor-hierarchy-reference` — ``InterIndustryFlow`` and ``LeontiefInverse``
  tensor types
- :mod:`babylon.data.bea.io_loader` — BEAIOLoader implementation
