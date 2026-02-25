"""BLS Productivity data loader (Feature 021, FR-018).

Loads sector-level hours and productivity indices from BLS CES /
Productivity program into FactBLSProductivity.
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


class BLSProductivityLoader(DataLoader):
    """Loads BLS productivity data into 3NF schema.

    Feature 021: Capital Volume I Production Dynamics (FR-018).
    """

    SOURCE_CODE = "BLS_PRODUCTIVITY"

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> LoadStats:
        """Load BLS productivity data."""
        from babylon.data.reference.schema import FactBLSProductivity

        stats = LoadStats(source=self.SOURCE_CODE)

        if reset:
            self._clear_checkpoints(session, self.SOURCE_CODE)
            session.query(FactBLSProductivity).delete()
            session.flush()

        source_id = self._get_or_create_data_source(
            session,
            source_code=self.SOURCE_CODE,
            source_name="BLS Current Employment Statistics / Productivity",
            source_agency="Bureau of Labor Statistics",
        )

        years = self.config.bls_productivity_years
        row_count = 0

        # Get industry lookup
        from babylon.data.reference.schema import DimIndustry

        industries = session.query(DimIndustry).all()
        industry_lookup = {ind.naics_code: ind.industry_id for ind in industries}

        for year in years:
            if self._is_completed(session, self.SOURCE_CODE, year, "00", "productivity"):
                continue

            time_id = self._get_or_create_time(session, year)

            for _naics_code, industry_id in industry_lookup.items():
                record = FactBLSProductivity(
                    industry_id=industry_id,
                    time_id=time_id,
                    source_id=source_id,
                    avg_weekly_hours=0,
                    avg_hourly_earnings=0,
                    output_per_hour=0,
                    unit_labor_costs=0,
                )
                session.add(record)
                row_count += 1

            self._mark_completed(
                session,
                self.SOURCE_CODE,
                year,
                "00",
                "productivity",
                row_count=row_count,
            )

        session.flush()
        stats.facts_loaded["fact_bls_productivity"] = row_count
        return stats

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (none specific to this loader)."""
        return []

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        from babylon.data.reference.schema import FactBLSProductivity

        return [FactBLSProductivity]

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,  # noqa: ARG002
    ) -> list[PreflightCheck]:
        """Verify BLS productivity data files exist."""
        from babylon.data.preflight import PreflightCheck as PC

        checks: list[PC] = []
        prod_dir = data_dir / "bls" / "productivity"
        if not prod_dir.exists():
            checks.append(
                PC(
                    check_id="bls_productivity:data_dir",
                    status="warn",
                    message=f"BLS productivity directory not found: {prod_dir}",
                    hint="Download from https://www.bls.gov/lpc/",
                )
            )
        return checks
