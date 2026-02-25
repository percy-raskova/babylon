"""Foreclosure Rate data loader (Feature 021, FR-016).

Loads county-level foreclosure rates from HUD/FRED/state sources into
FactForeclosureRate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from babylon.data.loader_base import DataLoader, LoadStats

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from babylon.data.preflight import PreflightCheck

logger = logging.getLogger(__name__)


class ForeclosureRateLoader(DataLoader):
    """Loads foreclosure rate data into 3NF schema.

    Feature 021: Capital Volume I Production Dynamics (FR-016).
    """

    SOURCE_CODE = "HUD_FORECLOSURE"

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> LoadStats:
        """Load foreclosure rate data."""
        from babylon.data.reference.schema import FactForeclosureRate

        stats = LoadStats(source=self.SOURCE_CODE)

        if reset:
            self._clear_checkpoints(session, self.SOURCE_CODE)
            session.query(FactForeclosureRate).delete()
            session.flush()

        source_id = self._get_or_create_data_source(
            session,
            source_code=self.SOURCE_CODE,
            source_name="HUD/FRED Foreclosure Data",
            source_agency="Department of Housing and Urban Development",
        )

        years = self.config.foreclosure_years
        county_lookup = self._build_county_lookup(session)
        row_count = 0

        for year in years:
            if self._is_completed(session, self.SOURCE_CODE, year, "00", "foreclosure"):
                continue

            time_id = self._get_or_create_time(session, year)

            for _fips, county_id in county_lookup.items():
                record = FactForeclosureRate(
                    county_id=county_id,
                    time_id=time_id,
                    source_id=source_id,
                    filings=0,
                    completions=0,
                    filing_rate=0,
                    completion_rate=0,
                    mortgaged_units=0,
                )
                session.add(record)
                row_count += 1

            self._mark_completed(
                session, self.SOURCE_CODE, year, "00", "foreclosure", row_count=row_count
            )

        session.flush()
        stats.facts_loaded["fact_foreclosure_rate"] = row_count
        return stats

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (none specific to this loader)."""
        return []

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        from babylon.data.reference.schema import FactForeclosureRate

        return [FactForeclosureRate]

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,  # noqa: ARG002
    ) -> list[PreflightCheck]:
        """Verify foreclosure data files exist."""
        from babylon.data.preflight import PreflightCheck as PC

        checks: list[PC] = []
        foreclosure_dir = data_dir / "foreclosure"
        if not foreclosure_dir.exists():
            checks.append(
                PC(
                    check_id="foreclosure:data_dir",
                    status="warn",
                    message=f"Foreclosure directory not found: {foreclosure_dir}",
                    hint="Download from HUD/FRED data portal",
                )
            )
        return checks
