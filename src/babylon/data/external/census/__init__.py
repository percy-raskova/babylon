"""US Census Bureau data access module.

Provides ingestion for Census ACS (American Community Survey) data:
- State-level population and class proxies
- Metro-level demographics

Data sources:
    - American Community Survey (ACS) 5-Year Estimates
    - Decennial Census

See brainstorm/data-requirements.md for data collection specifications.
See ai-docs/game-data.yaml for API documentation and variable mappings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from babylon.data.external.base import (
    DataIngester,
    IngestResult,
    parse_float,
    parse_int,
    validate_year,
)
from babylon.data.schema import CensusMetro, CensusPopulation, MetroArea, State

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class StateIngester(DataIngester[State]):
    """Ingester for US State reference data.

    Expected CSV format:
        fips,name,abbreviation
        01,Alabama,AL
        02,Alaska,AK
        ...
    """

    @property
    def model_class(self) -> type[State]:
        """Return the State model class."""
        return State

    def validate_row(self, row: dict[str, str]) -> list[str]:
        """Validate a state row.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if not row.get("fips"):
            errors.append("Missing required field: fips")
        elif len(row["fips"]) != 2:
            errors.append(f"FIPS code must be 2 characters, got: {row['fips']}")

        if not row.get("name"):
            errors.append("Missing required field: name")

        if not row.get("abbreviation"):
            errors.append("Missing required field: abbreviation")
        elif len(row.get("abbreviation", "")) != 2:
            errors.append(f"Abbreviation must be 2 characters, got: {row.get('abbreviation')}")

        return errors

    def parse_row(self, row: dict[str, str]) -> State | None:
        """Parse a CSV row into a State model.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            State model instance
        """
        return State(
            fips=row["fips"].strip(),
            name=row["name"].strip(),
            abbreviation=row["abbreviation"].strip().upper(),
        )


class MetroAreaIngester(DataIngester[MetroArea]):
    """Ingester for Metropolitan Statistical Area reference data.

    Expected CSV format:
        cbsa_code,name
        31080,Los Angeles-Long Beach-Anaheim
        16980,Chicago-Naperville-Elgin
        ...
    """

    @property
    def model_class(self) -> type[MetroArea]:
        """Return the MetroArea model class."""
        return MetroArea

    def validate_row(self, row: dict[str, str]) -> list[str]:
        """Validate a metro area row.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        if not row.get("cbsa_code"):
            errors.append("Missing required field: cbsa_code")
        elif len(row["cbsa_code"]) != 5:
            errors.append(f"CBSA code must be 5 characters, got: {row['cbsa_code']}")

        if not row.get("name"):
            errors.append("Missing required field: name")

        return errors

    def parse_row(self, row: dict[str, str]) -> MetroArea | None:
        """Parse a CSV row into a MetroArea model.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            MetroArea model instance
        """
        return MetroArea(
            cbsa_code=row["cbsa_code"].strip(),
            name=row["name"].strip(),
        )


class CensusPopulationIngester(DataIngester[CensusPopulation]):
    """Ingester for Census state population data.

    Expected CSV format:
        state_fips,year,total_pop,employed,unemployed,self_employed,median_income,poverty_pop
        01,2022,5024279,2200000,100000,150000,52035,800000
        ...

    Note: state_fips can be empty for national totals.
    """

    @property
    def model_class(self) -> type[CensusPopulation]:
        """Return the CensusPopulation model class."""
        return CensusPopulation

    def validate_row(self, row: dict[str, str]) -> list[str]:
        """Validate a census population row.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        return validate_year(row.get("year"), min_year=1790)

    def parse_row(self, row: dict[str, str]) -> CensusPopulation | None:
        """Parse a CSV row into a CensusPopulation model.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            CensusPopulation model instance
        """
        state_fips = row.get("state_fips", "").strip()

        return CensusPopulation(
            state_fips=state_fips if state_fips else None,
            year=int(row["year"]),
            total_pop=parse_int(row.get("total_pop")),
            employed=parse_int(row.get("employed")),
            unemployed=parse_int(row.get("unemployed")),
            self_employed=parse_int(row.get("self_employed")),
            median_income=parse_float(row.get("median_income")),
            poverty_pop=parse_int(row.get("poverty_pop")),
        )


class CensusMetroIngester(DataIngester[CensusMetro]):
    """Ingester for Census metro area demographic data.

    Expected CSV format:
        cbsa_code,year,total_pop,median_income,gini_index,median_rent,median_home_value
        31080,2022,13200998,80440,0.49,1750,750000
        ...

    Note: cbsa_code can be empty for national totals.
    """

    @property
    def model_class(self) -> type[CensusMetro]:
        """Return the CensusMetro model class."""
        return CensusMetro

    def validate_row(self, row: dict[str, str]) -> list[str]:
        """Validate a census metro row.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        return validate_year(row.get("year"), min_year=1790)

    def parse_row(self, row: dict[str, str]) -> CensusMetro | None:
        """Parse a CSV row into a CensusMetro model.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            CensusMetro model instance
        """
        cbsa_code = row.get("cbsa_code", "").strip()

        return CensusMetro(
            cbsa_code=cbsa_code if cbsa_code else None,
            year=int(row["year"]),
            total_pop=parse_int(row.get("total_pop")),
            median_income=parse_float(row.get("median_income")),
            gini_index=parse_float(row.get("gini_index")),
            median_rent=parse_float(row.get("median_rent")),
            median_home_value=parse_float(row.get("median_home_value")),
        )


def ingest_all_census_data(
    session: Session,
    data_dir: Path | str,
) -> dict[str, IngestResult]:
    """Ingest all Census data from a directory.

    Expected directory structure:
        data_dir/
            states.csv
            metro_areas.csv
            census_state_population.csv
            census_metro_demographics.csv

    Args:
        session: SQLAlchemy session
        data_dir: Path to directory containing CSV files

    Returns:
        Dictionary of filename -> IngestResult
    """
    data_dir = Path(data_dir)
    results: dict[str, IngestResult] = {}

    # Order matters: reference tables first, then dependent tables
    ingest_files = [
        ("states.csv", StateIngester()),
        ("metro_areas.csv", MetroAreaIngester()),
        ("census_state_population.csv", CensusPopulationIngester()),
        ("census_metro_demographics.csv", CensusMetroIngester()),
    ]

    for filename, ingester in ingest_files:
        csv_path = data_dir / filename
        if csv_path.exists():
            results[filename] = ingester.ingest_csv(session, csv_path)
        else:
            logger.debug(f"Skipping {filename} - file not found")

    return results


__all__ = [
    "StateIngester",
    "MetroAreaIngester",
    "CensusPopulationIngester",
    "CensusMetroIngester",
    "ingest_all_census_data",
]
