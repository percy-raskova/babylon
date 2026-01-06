QCEW Employment Data
====================

The QCEW (Quarterly Census of Employment and Wages) module provides access to
employment and wage data from the Bureau of Labor Statistics for Babylon's
simulation systems.

Overview
--------

QCEW is integrated into Babylon to provide:

- **County-level employment**: Detailed establishment and worker counts by NAICS industry
- **State-level aggregates**: Broader geographic patterns for macro analysis
- **Metro area data**: MSA, Micropolitan, and CSA aggregates for urban economic analysis
- **Location quotients**: Industry concentration metrics for comparative analysis
- **Class composition**: NAICS industry mapping to Marxian class categories

All data is stored in ``data/sqlite/marxist-data-3NF.sqlite`` using a normalized
star schema.

Setup
-----

**No setup required for API loading.** QCEW uses a hybrid loading strategy:

- **API (2021-2025)**: Fetches directly from BLS QCEW Open Data API
- **Files (2013-2020)**: Reads from local CSV files (optional, for historical data)

For file-based loading of historical years, download CSV files from:
https://www.bls.gov/cew/downloadable-data-files.htm

Loading Data
------------

Command Line
^^^^^^^^^^^^

.. code-block:: bash

    # Default hybrid loading (API for 2021+, files for historical)
    mise run data:qcew

    # Specific year range
    mise run data:qcew -- --years 2020-2023

    # Force API for all years (may fail for old years not in API)
    mise run data:qcew -- --force-api

    # Force file-based loading (requires downloaded CSVs)
    mise run data:qcew -- --force-files --data-path data/qcew

    # Reset tables before loading
    mise run data:qcew -- --reset

Python API
^^^^^^^^^^

.. code-block:: python

    from babylon.data.qcew import QcewLoader, QcewAPIClient
    from babylon.data.loader_base import LoaderConfig
    from babylon.data.normalize.database import get_normalized_session

    # Hybrid loading (default)
    config = LoaderConfig(qcew_years=list(range(2013, 2026)))
    loader = QcewLoader(config)

    with get_normalized_session() as session:
        stats = loader.load(session, reset=True)
        print(f"County: {stats.facts_loaded.get('qcew_county', 0):,}")
        print(f"State: {stats.facts_loaded.get('qcew_state', 0):,}")
        print(f"Metro: {stats.facts_loaded.get('qcew_metro', 0):,}")

    # Direct API access
    with QcewAPIClient() as client:
        # Fetch California state-level data for 2023
        for record in client.get_area_annual_data(2023, "06000"):
            print(f"{record.industry_code}: {record.annual_avg_emplvl:,} workers")

Geographic Levels
-----------------

QCEW data is loaded at three geographic levels based on aggregation level codes:

.. list-table::
   :header-rows: 1
   :widths: 20 20 30 30

   * - Level
     - agglvl_code
     - Fact Table
     - Description
   * - County
     - 70-78
     - ``fact_qcew_annual``
     - 3,200+ US counties
   * - State
     - 20-28
     - ``fact_qcew_state_annual``
     - 52 states/territories
   * - MSA
     - 30-38
     - ``fact_qcew_metro_annual``
     - Metropolitan Statistical Areas
   * - Micropolitan
     - 40-48
     - ``fact_qcew_metro_annual``
     - Micropolitan Statistical Areas
   * - CSA
     - 50-58
     - ``fact_qcew_metro_annual``
     - Combined Statistical Areas

Database Schema
---------------

Fact Tables
^^^^^^^^^^^

**fact_qcew_annual** (County Level)

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Column
     - Type
     - Description
   * - county_id
     - FK
     - Reference to dim_county
   * - industry_id
     - FK
     - Reference to dim_industry
   * - ownership_id
     - FK
     - Reference to dim_ownership
   * - time_id
     - FK
     - Reference to dim_time
   * - establishments
     - INT
     - Number of business establishments
   * - employment
     - INT
     - Annual average employment
   * - total_wages_usd
     - DECIMAL
     - Total annual wages paid
   * - avg_weekly_wage_usd
     - INT
     - Average weekly wage per worker
   * - avg_annual_pay_usd
     - INT
     - Average annual pay per worker
   * - lq_employment
     - DECIMAL
     - Location quotient for employment
   * - lq_annual_pay
     - DECIMAL
     - Location quotient for pay
   * - disclosure_code
     - VARCHAR
     - Data suppression indicator

**fact_qcew_state_annual** and **fact_qcew_metro_annual** follow the same
structure, with FK references to ``dim_state`` and ``dim_metro_area`` respectively.

SQL Queries
-----------

**Employment by Class Composition**

.. code-block:: sql

    SELECT
        sec.class_composition,
        SUM(q.employment) as total_employment,
        ROUND(SUM(q.total_wages_usd) / 1e9, 2) as wages_billions
    FROM fact_qcew_annual q
    JOIN dim_industry i ON q.industry_id = i.industry_id
    JOIN dim_sector sec ON i.sector_code = sec.sector_code
    JOIN dim_time t ON q.time_id = t.time_id
    WHERE t.year = 2023 AND sec.class_composition IS NOT NULL
    GROUP BY sec.class_composition
    ORDER BY total_employment DESC;

**State-Level Industry Concentration**

.. code-block:: sql

    SELECT
        s.state_name,
        i.naics_title,
        q.lq_employment as concentration,
        q.employment
    FROM fact_qcew_state_annual q
    JOIN dim_state s ON q.state_id = s.state_id
    JOIN dim_industry i ON q.industry_id = i.industry_id
    JOIN dim_time t ON q.time_id = t.time_id
    WHERE t.year = 2023
      AND q.lq_employment > 2.0  -- Highly concentrated
    ORDER BY q.lq_employment DESC
    LIMIT 20;

**Metro Area Manufacturing Employment**

.. code-block:: sql

    SELECT
        m.metro_name,
        q.area_type,
        SUM(q.employment) as manufacturing_jobs,
        ROUND(AVG(q.avg_annual_pay_usd), 0) as avg_pay
    FROM fact_qcew_metro_annual q
    JOIN dim_metro_area m ON q.metro_area_id = m.metro_area_id
    JOIN dim_industry i ON q.industry_id = i.industry_id
    JOIN dim_time t ON q.time_id = t.time_id
    WHERE i.naics_code LIKE '31%'
       OR i.naics_code LIKE '32%'
       OR i.naics_code LIKE '33%'
    AND t.year = 2023
    GROUP BY m.metro_name, q.area_type
    ORDER BY manufacturing_jobs DESC
    LIMIT 20;

API Client
----------

The ``QcewAPIClient`` class provides direct access to the BLS QCEW Open Data API:

.. code-block:: python

    from babylon.data.qcew import QcewAPIClient, QcewAPIError

    with QcewAPIClient() as client:
        try:
            # Fetch by area (state/county FIPS code)
            records = list(client.get_area_annual_data(2023, "01001"))  # Autauga County, AL

            # Fetch by industry (NAICS code)
            records = list(client.get_industry_annual_data(2023, "31-33"))  # Manufacturing

        except QcewAPIError as e:
            print(f"API error {e.status_code}: {e.message}")

API Features:

- **Rate limiting**: 0.5s delay between requests (polite to BLS servers)
- **Retry logic**: Exponential backoff on 429/5xx errors
- **CSV parsing**: Automatic parsing of BLS CSV responses
- **Error handling**: Distinguishes 404 (missing data) from server errors

Marxian Analysis
----------------

QCEW data supports Marxian class analysis through:

**Class Composition by Sector**

Industries are mapped to class composition categories in ``dim_sector``:

- ``goods_producing`` - Manufacturing, construction (productive labor)
- ``service_producing`` - Services, retail (mixed productive/unproductive)
- ``circulation`` - Finance, real estate (unproductive, surplus redistribution)
- ``government`` - Public administration (social reproduction)
- ``extraction`` - Mining, resources (ground rent extraction)

**Location Quotients for Labor Market Analysis**

Location quotients (LQ) reveal industry concentration:

- LQ > 1.25: Industry concentrated (potential labor aristocracy formation)
- LQ < 0.75: Industry underrepresented (labor mobility constraints)

**Wage Differentials**

Cross-geographic wage comparisons reveal unequal exchange dynamics:

- Core metro areas: Higher wages, higher productivity
- Periphery counties: Lower wages, extraction patterns

See Also
--------

- :doc:`fred-data` - FRED macroeconomic data
- :doc:`census-analysis` - Census ACS demographics
- :mod:`babylon.data.qcew` - API reference
- `BLS QCEW Open Data <https://www.bls.gov/cew/additional-resources/open-data/>`_
