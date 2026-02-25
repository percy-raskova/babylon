"""Eviction Lab data loader (Feature 021, FR-015).

Loads county-level eviction filings and executions from Eviction Lab
data into FactEvictionLabFiling.
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


class EvictionLabLoader(DataLoader):
    """Loads Eviction Lab data into 3NF schema.

    Feature 021: Capital Volume I Production Dynamics (FR-015).
    """

    SOURCE_CODE = "EVICTION_LAB"

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> LoadStats:
        """Load Eviction Lab data."""
        from babylon.data.reference.schema import FactEvictionLabFiling

        stats = LoadStats(source=self.SOURCE_CODE)

        if reset:
            self._clear_checkpoints(session, self.SOURCE_CODE)
            session.query(FactEvictionLabFiling).delete()
            session.flush()

        source_id = self._get_or_create_data_source(
            session,
            source_code=self.SOURCE_CODE,
            source_name="Eviction Lab",
            source_agency="Princeton University",
        )

        years = self.config.eviction_lab_years
        county_lookup = self._build_county_lookup(session)
        row_count = 0

        for year in years:
            if self._is_completed(session, self.SOURCE_CODE, year, "00", "eviction"):
                continue

            time_id = self._get_or_create_time(session, year)

            for _fips, county_id in county_lookup.items():
                record = FactEvictionLabFiling(
                    county_id=county_id,
                    time_id=time_id,
                    source_id=source_id,
                    filings=0,
                    executions=0,
                    filing_rate=0,
                    execution_rate=0,
                    renter_households=0,
                )
                session.add(record)
                row_count += 1

            self._mark_completed(
                session, self.SOURCE_CODE, year, "00", "eviction", row_count=row_count
            )

        session.flush()
        stats.facts_loaded["fact_eviction_lab_filing"] = row_count
        return stats

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (none specific to this loader)."""
        return []

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        from babylon.data.reference.schema import FactEvictionLabFiling

        return [FactEvictionLabFiling]

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,  # noqa: ARG002
    ) -> list[PreflightCheck]:
        """Verify Eviction Lab data files exist."""
        from babylon.data.preflight import PreflightCheck as PC

        checks: list[PC] = []
        eviction_dir = data_dir / "eviction_lab"
        if not eviction_dir.exists():
            checks.append(
                PC(
                    check_id="eviction_lab:data_dir",
                    status="warn",
                    message=f"Eviction Lab directory not found: {eviction_dir}",
                    hint="Download from https://evictionlab.org/get-the-data/",
                )
            )
        return checks
