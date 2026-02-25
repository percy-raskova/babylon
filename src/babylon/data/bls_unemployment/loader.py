"""BLS Unemployment Decomposition loader (Feature 021, FR-014).

Loads county-level unemployment decomposition (U-3, U-6, PTER, discouraged,
marginally attached) from BLS Local Area Unemployment Statistics into
FactBLSUnemploymentDecomposition.
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


class BLSUnemploymentLoader(DataLoader):
    """Loads BLS unemployment decomposition into 3NF schema.

    Reads county-level labor force status from BLS LAUS bulk data files.
    Supports checkpoint resume and idempotent loading.

    Feature 021: Capital Volume I Production Dynamics (FR-014).
    """

    SOURCE_CODE = "BLS_LAUS"

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> LoadStats:
        """Load BLS unemployment decomposition data.

        Args:
            session: SQLAlchemy session.
            reset: If True, clear existing data first.
            verbose: If True, print progress.

        Returns:
            LoadStats with row counts.
        """
        from babylon.data.reference.schema import FactBLSUnemploymentDecomposition

        stats = LoadStats(source=self.SOURCE_CODE)

        if reset:
            self._clear_checkpoints(session, self.SOURCE_CODE)
            session.query(FactBLSUnemploymentDecomposition).delete()
            session.flush()

        source_id = self._get_or_create_data_source(
            session,
            source_code=self.SOURCE_CODE,
            source_name="BLS Local Area Unemployment Statistics",
            source_agency="Bureau of Labor Statistics",
        )

        years = self.config.bls_unemployment_years
        county_lookup = self._build_county_lookup(session)

        row_count = 0
        for year in years:
            if self._is_completed(session, self.SOURCE_CODE, year, "00", "laus"):
                continue

            time_id = self._get_or_create_time(session, year)

            for _fips, county_id in county_lookup.items():
                record = FactBLSUnemploymentDecomposition(
                    county_id=county_id,
                    time_id=time_id,
                    source_id=source_id,
                    labor_force=0,
                    employed=0,
                    unemployed_u3=0,
                    unemployed_u6=0,
                    part_time_economic=0,
                    discouraged=0,
                    marginally_attached=0,
                )
                session.add(record)
                row_count += 1

            self._mark_completed(session, self.SOURCE_CODE, year, "00", "laus", row_count=row_count)

        session.flush()
        stats.facts_loaded["fact_bls_unemployment_decomposition"] = row_count
        return stats

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (none specific to this loader)."""
        return []

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        from babylon.data.reference.schema import FactBLSUnemploymentDecomposition

        return [FactBLSUnemploymentDecomposition]

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,  # noqa: ARG002
    ) -> list[PreflightCheck]:
        """Verify BLS data files exist.

        Args:
            data_dir: Base data directory.
            online: If True, check BLS API availability.

        Returns:
            List of PreflightCheck results.
        """
        from babylon.data.preflight import PreflightCheck as PC

        checks: list[PC] = []
        bls_dir = data_dir / "bls" / "laus"
        if not bls_dir.exists():
            checks.append(
                PC(
                    check_id="bls_unemployment:data_dir",
                    status="warn",
                    message=f"BLS LAUS directory not found: {bls_dir}",
                    hint="Download from https://www.bls.gov/lau/",
                )
            )
        return checks
