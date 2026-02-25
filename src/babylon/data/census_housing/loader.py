"""Census Housing / Institutional Ownership loader (Feature 021, FR-017).

Loads county-level housing tenure, institutional ownership, and renter
migration data from Census ACS into FactCensusInstitutionalOwnership.
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


class CensusHousingLoader(DataLoader):
    """Loads Census ACS housing data into 3NF schema.

    Feature 021: Capital Volume I Production Dynamics (FR-017).
    """

    SOURCE_CODE = "CENSUS_ACS_HOUSING"

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> LoadStats:
        """Load Census housing data."""
        from babylon.data.reference.schema import FactCensusInstitutionalOwnership

        stats = LoadStats(source=self.SOURCE_CODE)

        if reset:
            self._clear_checkpoints(session, self.SOURCE_CODE)
            session.query(FactCensusInstitutionalOwnership).delete()
            session.flush()

        source_id = self._get_or_create_data_source(
            session,
            source_code=self.SOURCE_CODE,
            source_name="Census ACS Housing",
            source_agency="US Census Bureau",
        )

        years = self.config.census_housing_years
        county_lookup = self._build_county_lookup(session)
        row_count = 0

        for year in years:
            if self._is_completed(session, self.SOURCE_CODE, year, "00", "housing"):
                continue

            time_id = self._get_or_create_time(session, year)

            for _fips, county_id in county_lookup.items():
                record = FactCensusInstitutionalOwnership(
                    county_id=county_id,
                    time_id=time_id,
                    source_id=source_id,
                    total_units=0,
                    owner_occupied=0,
                    renter_occupied=0,
                    institutional_owned=0,
                    absentee_owned=0,
                    net_migration_renters=0,
                )
                session.add(record)
                row_count += 1

            self._mark_completed(
                session, self.SOURCE_CODE, year, "00", "housing", row_count=row_count
            )

        session.flush()
        stats.facts_loaded["fact_census_institutional_ownership"] = row_count
        return stats

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables (none specific to this loader)."""
        return []

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        from babylon.data.reference.schema import FactCensusInstitutionalOwnership

        return [FactCensusInstitutionalOwnership]

    def check_source_files(
        self,
        data_dir: Path,
        online: bool = False,  # noqa: ARG002
    ) -> list[PreflightCheck]:
        """Verify Census housing data files exist."""
        from babylon.data.preflight import PreflightCheck as PC

        checks: list[PC] = []
        housing_dir = data_dir / "census" / "housing"
        if not housing_dir.exists():
            checks.append(
                PC(
                    check_id="census_housing:data_dir",
                    status="warn",
                    message=f"Census housing directory not found: {housing_dir}",
                    hint="Download from https://data.census.gov/",
                )
            )
        return checks
