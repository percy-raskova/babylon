"""Federal Reserve Economic Data (FRED) access module.

Provides ingestion for FRED economic indicators:
- GDP, unemployment, CPI, interest rates
- Federal debt and money supply
- Median household income

See brainstorm/data-requirements.md for data collection specifications.
See ai-docs/game-data.yaml for API documentation and variable mappings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from babylon.data.external.base import DataIngester, IngestResult, parse_float, validate_year
from babylon.data.schema import FredIndicator

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FredIndicatorIngester(DataIngester[FredIndicator]):
    """Ingester for FRED economic indicator data.

    Expected CSV format:
        year,quarter,gdp_billions,unemployment_pct,cpi,fed_funds_rate,federal_debt_millions,m2_money_supply,median_income
        2023,4,27610.3,3.7,306.746,5.33,34001493,20866,74580
        ...

    Note: quarter can be empty for annual data.
    """

    @property
    def model_class(self) -> type[FredIndicator]:
        """Return the FredIndicator model class."""
        return FredIndicator

    def validate_row(self, row: dict[str, str]) -> list[str]:
        """Validate a FRED indicator row.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = validate_year(row.get("year"))

        # Validate quarter if provided
        quarter_str = row.get("quarter", "").strip()
        if quarter_str:
            try:
                quarter = int(quarter_str)
                if quarter < 1 or quarter > 4:
                    errors.append(f"Quarter must be 1-4, got: {quarter}")
            except ValueError:
                errors.append(f"Invalid quarter: {quarter_str}")

        return errors

    def parse_row(self, row: dict[str, str]) -> FredIndicator | None:
        """Parse a CSV row into a FredIndicator model.

        Args:
            row: Dictionary of column name -> value from CSV

        Returns:
            FredIndicator model instance
        """
        quarter_str = row.get("quarter", "").strip()

        return FredIndicator(
            year=int(row["year"]),
            quarter=int(quarter_str) if quarter_str else None,
            gdp_billions=parse_float(row.get("gdp_billions")),
            unemployment_pct=parse_float(row.get("unemployment_pct")),
            cpi=parse_float(row.get("cpi")),
            fed_funds_rate=parse_float(row.get("fed_funds_rate")),
            federal_debt_millions=parse_float(row.get("federal_debt_millions")),
            m2_money_supply=parse_float(row.get("m2_money_supply")),
            median_income=parse_float(row.get("median_income")),
        )


def ingest_fred_data(
    session: Session,
    csv_path: Path | str,
) -> IngestResult:
    """Ingest FRED economic indicator data.

    Args:
        session: SQLAlchemy session
        csv_path: Path to the CSV file

    Returns:
        IngestResult with statistics about the operation
    """
    ingester = FredIndicatorIngester()
    return ingester.ingest_csv(session, csv_path)


__all__ = [
    "FredIndicatorIngester",
    "ingest_fred_data",
]
