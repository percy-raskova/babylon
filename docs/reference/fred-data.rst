FRED Economic Data
==================

The FRED (Federal Reserve Economic Data) module provides access to macroeconomic
time series from the Federal Reserve Bank of St. Louis for Babylon's simulation
systems.

Overview
--------

FRED is integrated into Babylon to provide:

- **Real wage calculations**: CPI and nominal hourly earnings
- **Reserve army metrics**: National, state, and industry unemployment rates
- **Fiscal indicators**: Federal debt and M2 money supply
- **Imperial bribe data**: PPP-adjusted GDP per capita

All data is stored in ``data/sqlite/research.sqlite`` alongside Census, QCEW,
Trade, and Productivity data.

Setup
-----

1. Register for a FRED API key at https://fredaccount.stlouisfed.org/apikeys

2. Set the environment variable::

    export FRED_API_KEY=your_key_here

3. Load the data::

    mise run data:fred-load

Series Catalog
--------------

National Series (8)
^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Series ID
     - Description
     - Marxian Use
   * - CPIAUCSL
     - Consumer Price Index
     - Real wage calculation (adjusts nominal wages for inflation)
   * - AHETPI
     - Average Hourly Earnings
     - Nominal wage input for variable capital (v)
   * - UNRATE
     - Unemployment Rate
     - Reserve army of labor proxy
   * - GFDEBTN
     - Federal Debt
     - Fiscal trilemma modeling
   * - GINIALLRF
     - Gini Index
     - Class tension initialization
   * - M2SL
     - M2 Money Stock
     - Fictitious capital proxy
   * - PPPTTLUSA618NUPN
     - PPP over GDP (lags 2-3 years)
     - Unequal exchange calculation
   * - RGDPCHUSA625NUPN
     - PPP GDP/Capita (lags 2-3 years)
     - Imperial bribe / superwages

State Unemployment (51)
^^^^^^^^^^^^^^^^^^^^^^^

State-level unemployment rates for all 50 states plus DC using the LAUST
series pattern: ``LAUST{FIPS}0000000000003A``

Example: ``LAUST120000000000003A`` for Florida (FIPS 12)

Industry Unemployment (8)
^^^^^^^^^^^^^^^^^^^^^^^^^

Major sector unemployment rates that join with QCEW NAICS codes:

- Construction (NAICS 23)
- Manufacturing (NAICS 31-33)
- Transportation & Utilities (NAICS 48-49)
- Information (NAICS 51)
- Financial Activities (NAICS 52-53)
- Professional & Business Services (NAICS 54-56)
- Education & Health Services (NAICS 61-62)
- Leisure & Hospitality (NAICS 71-72)

Usage
-----

Command Line
^^^^^^^^^^^^

.. code-block:: bash

    # Load all FRED data for 2022 (default)
    mise run data:fred-load

    # Reset and reload
    mise run data:fred-reset

    # National series only (faster)
    mise run data:fred-national

Python API
^^^^^^^^^^

.. code-block:: python

    from babylon.data.fred import load_fred_data, FredNational, FredSeries
    from babylon.data.census import get_census_db

    # Load data
    stats = load_fred_data(year=2022, reset=True)
    print(f"Loaded {stats.national_records} national records")

    # Query CPI data
    db = next(get_census_db())
    cpi = db.query(FredNational).join(FredSeries).filter(
        FredSeries.series_id == "CPIAUCSL"
    ).all()

    for obs in cpi:
        print(f"{obs.date}: {obs.value}")

SQL Queries
^^^^^^^^^^^

**Calculate Real Wages**

.. code-block:: sql

    SELECT
        f_wage.value / (f_cpi.value / 100) as real_hourly_wage,
        f_wage.date
    FROM fred_national f_wage
    JOIN fred_series s_wage ON f_wage.series_id = s_wage.id
    JOIN fred_national f_cpi ON f_wage.date = f_cpi.date
    JOIN fred_series s_cpi ON f_cpi.series_id = s_cpi.id
    WHERE s_wage.series_id = 'AHETPI'
      AND s_cpi.series_id = 'CPIAUCSL'
      AND f_wage.year = 2022;

**Join State Unemployment with QCEW Employment**

.. code-block:: sql

    SELECT
        fs.name as state,
        fu.unemployment_rate,
        SUM(qa.employment) as total_employment
    FROM fred_state_unemployment fu
    JOIN fred_states fs ON fu.state_id = fs.id
    JOIN qcew_areas qa ON qa.area_fips LIKE fs.fips_code || '%'
    WHERE fu.year = 2022
    GROUP BY fs.name;

Database Schema
---------------

Dimension Tables
^^^^^^^^^^^^^^^^

**fred_series**
    Metadata for each time series (series_id, title, units, frequency)

**fred_states**
    US states with FIPS codes for state-level joins

**fred_industries**
    Industry sectors with NAICS codes for QCEW joins

Fact Tables
^^^^^^^^^^^

**fred_national**
    National series observations (value, date, year, month, quarter)

**fred_state_unemployment**
    State-level unemployment rates by month

**fred_industry_unemployment**
    Industry-level unemployment rates by month

See Also
--------

- :doc:`census-analysis` - Census Bureau ACS data
- :mod:`babylon.data.fred` - API reference
- `FRED API Documentation <https://fred.stlouisfed.org/docs/api/fred/>`_
