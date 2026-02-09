"""Integration tests for BEA-NAICS concordance loader.

Tests against actual concordance file and database.
Requires:
- The concordance file to exist
- DimBEAIndustry to be populated (from BEANationalLoader)
- DimIndustry to be populated (from CensusLoader or similar)

Extracted from tests/unit/data/test_bea/test_loader_concordance.py
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from babylon.data.bea.loader_concordance import BEAConcordanceLoader

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@pytest.mark.integration
class TestActualFileLoading:
    """Integration tests against actual concordance file.

    These tests require:
    - The concordance file to exist
    - DimBEAIndustry to be populated (from BEANationalLoader)
    - DimIndustry to be populated (from CensusLoader or similar)
    """

    @pytest.fixture
    def session(self) -> Session:
        """Get a database session."""
        from babylon.data.reference.database import get_normalized_session_factory

        session_factory = get_normalized_session_factory()
        return session_factory()

    @pytest.fixture
    def loader(self) -> BEAConcordanceLoader:
        """Create loader with actual data directory."""
        return BEAConcordanceLoader(data_dir=Path("data"))

    def test_concordance_file_exists(self, loader: BEAConcordanceLoader) -> None:
        """Concordance file should exist."""
        filepath = (
            loader.data_dir
            / "concordance/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx"
        )
        assert filepath.exists()

    def test_load_creates_bridge_records(
        self, session: Session, loader: BEAConcordanceLoader
    ) -> None:
        """Should create bridge records if dependencies exist."""
        from sqlalchemy import text

        # Check if prerequisites exist
        bea_count = session.execute(text("SELECT COUNT(*) FROM dim_bea_industry")).scalar()
        naics_count = session.execute(text("SELECT COUNT(*) FROM dim_industry")).scalar()

        if bea_count == 0 or naics_count == 0:
            pytest.skip("Prerequisites (DimBEAIndustry, DimIndustry) not loaded")

        stats = loader.load(session, reset=True, verbose=False)

        # Should have created some mappings
        bridge_count = session.execute(text("SELECT COUNT(*) FROM bridge_naics_bea")).scalar()
        assert bridge_count > 0
        assert stats.facts_loaded.get("bridge_naics_bea", 0) == bridge_count
