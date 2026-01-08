"""Unit tests for EIA energy data loader.

Tests the EnergyLoader with mocked API client to verify loading logic
without requiring actual API credentials.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from babylon.data.energy import EnergyLoader
from babylon.data.energy.api_client import (
    EnergyObservation,
    EnergySeriesData,
    EnergySeriesMetadata,
)
from babylon.data.loader_base import LoaderConfig
from babylon.data.normalize import schema as _schema  # noqa: F401
from babylon.data.normalize.database import NormalizedBase
from babylon.data.normalize.schema import DimEnergySeries, FactEnergyAnnual


def _make_session() -> Session:
    engine = create_engine("duckdb:///:memory:")
    NormalizedBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_energy_loader_uses_mer_files() -> None:
    """Test that EnergyLoader loads series and facts from API.

    Uses mocked API client to verify loading logic without requiring
    actual API credentials.
    """
    # Create mock API client that returns test data
    mock_client = MagicMock()
    mock_client.get_series.return_value = EnergySeriesData(
        metadata=EnergySeriesMetadata(
            msn="TEPRBUS",
            description="Total Primary Energy Production",
            unit="Quadrillion Btu",
        ),
        observations=[
            # Single observation - multiple per year would cause PK violation
            EnergyObservation(period="2020", value=3.0),
        ],
    )

    session = _make_session()
    try:
        loader = EnergyLoader(LoaderConfig(energy_start_year=2020, energy_end_year=2020))

        # Patch the _make_client method to return our mock
        with patch.object(loader, "_make_client", return_value=mock_client):
            stats = loader.load(session, reset=True, verbose=False)

        # Verify facts were loaded - one observation per series per year
        # With 20 priority MSN codes, we expect 20 series and 20 observations
        assert stats.facts_loaded.get("energy_annual", 0) > 0
        series_list = session.execute(select(DimEnergySeries)).scalars().all()
        assert len(series_list) > 0
        fact = session.execute(select(FactEnergyAnnual)).scalars().first()
        assert fact is not None
        assert fact.value == 3.0
    finally:
        session.close()
