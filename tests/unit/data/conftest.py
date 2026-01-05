"""Shared fixtures for data loader tests.

Provides mock API responses and database connections for isolated unit testing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a mock database session for loader tests.

    Returns:
        MagicMock with spec=Session and configured methods.
    """
    session = MagicMock(spec=Session)
    session.execute = MagicMock(return_value=MagicMock())
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.flush = MagicMock()
    session.add = MagicMock()
    session.query = MagicMock(return_value=MagicMock())
    return session


@pytest.fixture
def in_memory_db() -> Engine:
    """Create an in-memory SQLite database for integration-style unit tests.

    Returns:
        SQLAlchemy engine connected to in-memory SQLite.
    """
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def mock_http_response() -> MagicMock:
    """Create a mock HTTP response for API client tests.

    Returns:
        MagicMock with status_code=200 and raise_for_status configured.
    """
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_httpx_client() -> MagicMock:
    """Create a mock httpx.Client for API client tests.

    Returns:
        MagicMock with get method configured.
    """
    client = MagicMock()
    client.get = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture
def sample_fred_observation() -> dict[str, Any]:
    """Sample FRED API observation response.

    Returns:
        Dict matching FRED API observation format.
    """
    return {
        "date": "2020-01-01",
        "value": "100.5",
    }


@pytest.fixture
def sample_fred_observations() -> list[dict[str, Any]]:
    """Sample list of FRED API observations.

    Returns:
        List of dicts matching FRED API observation format.
    """
    return [
        {"date": "2020-01-01", "value": "100.0"},
        {"date": "2020-02-01", "value": "101.5"},
        {"date": "2020-03-01", "value": "."},  # Missing value marker
        {"date": "2020-04-01", "value": "102.0"},
    ]


@pytest.fixture
def sample_census_row() -> dict[str, str]:
    """Sample Census API response row.

    Returns:
        Dict matching Census API row format.
    """
    return {
        "NAME": "Los Angeles County, California",
        "state": "06",
        "county": "037",
        "B19001_001E": "3000000",
        "B19001_002E": "500000",
    }


@pytest.fixture
def sample_eia_observation() -> dict[str, Any]:
    """Sample EIA API observation response.

    Returns:
        Dict matching EIA API observation format.
    """
    return {
        "period": "2020",
        "value": "1234.5",
        "seriesDescription": "Total Primary Energy Production",
        "unit": "Quadrillion Btu",
    }


@pytest.fixture
def sample_qcew_row() -> dict[str, str]:
    """Sample QCEW CSV row.

    Returns:
        Dict matching QCEW CSV column structure.
    """
    return {
        "area_fips": "01001",
        "area_title": "Autauga County, Alabama",
        "agglvl_code": "70",
        "industry_code": "10",
        "industry_title": "Total, All Industries",
        "own_code": "0",
        "own_title": "Total Covered",
        "year": "2023",
        "annual_avg_estabs_count": "1234",
        "annual_avg_emplvl": "15678",
        "total_annual_wages": "650000000",
        "annual_avg_wkly_wage": "800",
        "avg_annual_pay": "41500",
        "lq_annual_avg_emplvl": "0.95",
        "lq_avg_annual_pay": "0.88",
        "oty_annual_avg_emplvl_chg": "100",
        "oty_annual_avg_emplvl_pct_chg": "0.6",
        "disclosure_code": "",
    }


@pytest.fixture
def sample_trade_row() -> dict[str, Any]:
    """Sample trade data row.

    Returns:
        Dict matching trade Excel row format.
    """
    return {
        "year": 2023,
        "CTY_CODE": "5700",
        "CTYNAME": "China",
        "IJAN": 1000000.0,
        "IFEB": 1100000.0,
        "IMAR": 1200000.0,
        "IAPR": None,
        "IMAY": None,
        "IJUN": None,
        "IJUL": None,
        "IAUG": None,
        "ISEP": None,
        "IOCT": None,
        "INOV": None,
        "IDEC": None,
        "IYR": 12000000.0,
        "EJAN": 500000.0,
        "EFEB": 550000.0,
        "EMAR": 600000.0,
        "EAPR": None,
        "EMAY": None,
        "EJUN": None,
        "EJUL": None,
        "EAUG": None,
        "ESEP": None,
        "EOCT": None,
        "ENOV": None,
        "EDEC": None,
        "EYR": 6000000.0,
    }


@pytest.fixture
def sample_materials_row() -> dict[str, str]:
    """Sample materials/commodity CSV row.

    Returns:
        Dict matching USGS MCS CSV row format.
    """
    return {
        "DataSource": "MCS2025",
        "Commodity": "Lithium",
        "Year": "2023",
        "USprod_Primary_kt": "920",
        "NIR_pct": ">50",
        "Import_kt": "W",
    }
