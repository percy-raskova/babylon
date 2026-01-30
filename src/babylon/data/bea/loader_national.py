"""BEA national industry data loader for 3NF schema.

Loads BEA GDP-by-industry data from XLSX files directly into the normalized
3NF schema (marxist-data-3NF.duckdb). This loader populates:
- dim_bea_industry: Industry dimension with hierarchy
- fact_bea_national_industry: Annual gross output, value added, intermediate inputs

The data forms the foundation for Marxian value analysis by providing:
- Constant capital ratios (c) via intermediate inputs
- Value added (v + s) for decomposition
- Industry classification for sectoral analysis

Usage:
    from babylon.data.bea import BEANationalLoader
    from babylon.data.reference.database import get_normalized_session_factory

    loader = BEANationalLoader()
    session_factory = get_normalized_session_factory()
    with session_factory() as session:
        stats = loader.load(session)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm

from babylon.data.bea.parser import BEAIndustry, BEAIndustryParser, BEAParseResult
from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.reference.schema import (
    BridgeNAICSBEA,
    DimBEAIndustry,
    DimDataSource,
    FactBEACountyGDP,
    FactBEANationalIndustry,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default data directory relative to project root
DEFAULT_DATA_DIR = Path("data")


class BEANationalLoader(DataLoader):
    """Loader for BEA national industry data into 3NF schema.

    Parses XLSX files from BEA GDP-by-industry tables and loads industry
    dimensions and fact values into the normalized schema.

    Attributes:
        config: LoaderConfig controlling operational settings.
        data_dir: Path to data directory containing gdp-by-industry/.

    Example:
        loader = BEANationalLoader()
        stats = loader.load(session, reset=True)
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """Initialize BEA national loader.

        Args:
            config: LoaderConfig for operational settings.
            data_dir: Path to data directory. Defaults to "data" in project root.
        """
        super().__init__(config)
        self.data_dir = data_dir if data_dir is not None else DEFAULT_DATA_DIR
        self._parser = BEAIndustryParser(self.data_dir)
        self._source_id: int | None = None
        self._industry_cache: dict[int, int] = {}  # line_number -> bea_industry_id

    def get_dimension_tables(self) -> list[type]:
        """Return dimension table models this loader populates."""
        return [DimDataSource, DimBEAIndustry]

    def get_fact_tables(self) -> list[type]:
        """Return fact table models this loader populates."""
        return [FactBEANationalIndustry]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **_kwargs: object,
    ) -> LoadStats:
        """Load BEA national industry data into 3NF schema.

        Parses all three BEA XLSX files (GrossOutput, ValueAdded, IntermediateInputs)
        and merges them into a unified fact table with one row per industry-year
        containing all three value types.

        Args:
            session: SQLAlchemy session for the normalized database.
            reset: If True, delete existing BEA data before loading.
            verbose: If True, print progress information.
            **_kwargs: Additional parameters (unused).

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        stats = LoadStats(source="bea_national")

        if verbose:
            print("Loading BEA national industry data...")

        try:
            # Clear existing data if reset
            if reset:
                if verbose:
                    print("Clearing existing BEA data...")
                self._clear_bea_tables(session)
                session.flush()

            # Parse all three XLSX files
            if verbose:
                print("Parsing BEA XLSX files...")

            gross_output = self._parser.parse_gross_output()
            stats.files_processed += 1

            value_added = self._parser.parse_value_added()
            stats.files_processed += 1

            intermediate_inputs = self._parser.parse_intermediate_inputs()
            stats.files_processed += 1

            # Determine year range from parsed data
            all_years = (
                set(gross_output.years) | set(value_added.years) | set(intermediate_inputs.years)
            )
            min_year = min(all_years)
            max_year = max(all_years)

            # Load data source
            self._load_data_source(session, min_year, max_year)
            stats.dimensions_loaded["dim_data_source"] = 1

            # Load industry dimension (use gross_output as canonical source)
            industry_count = self._load_industry_dimension(session, gross_output, verbose)
            stats.dimensions_loaded["dim_bea_industry"] = industry_count

            session.flush()

            # Load fact table by merging all three value types
            fact_count = self._load_fact_table(
                session,
                gross_output,
                value_added,
                intermediate_inputs,
                verbose,
            )
            stats.facts_loaded["fact_bea_national_industry"] = fact_count
            stats.record_ingest(
                f"bea:{min_year}-{max_year}:fact_bea_national_industry",
                fact_count,
            )

            session.commit()

            if verbose:
                print(f"\n{stats}")
                self._validate_accounting_identity(session)

        except Exception as e:
            stats.errors.append(str(e))
            session.rollback()
            raise

        return stats

    def _clear_bea_tables(self, session: Session) -> None:
        """Clear BEA-specific tables (facts first to respect FK constraints)."""
        # Must delete facts and bridges before dimensions due to FK constraints
        # DuckDB requires commit between FK-related deletes
        session.query(FactBEANationalIndustry).delete()
        session.commit()
        session.query(FactBEACountyGDP).delete()
        session.commit()
        session.query(BridgeNAICSBEA).delete()
        session.commit()
        session.query(DimBEAIndustry).delete()
        session.commit()

    def _load_data_source(self, session: Session, start_year: int, end_year: int) -> None:
        """Load data source dimension."""
        source_code = f"BEA_GDP_INDUSTRY_{start_year}_{end_year}"
        self._source_id = self._get_or_create_data_source(
            session,
            source_code=source_code,
            source_name=f"BEA GDP-by-Industry Accounts {start_year}-{end_year}",
            source_url="https://apps.bea.gov/iTable/?reqid=150",
            source_year=end_year,
            source_agency="Bureau of Economic Analysis",
            coverage_start_year=start_year,
            coverage_end_year=end_year,
        )

    def _load_industry_dimension(
        self,
        session: Session,
        parse_result: BEAParseResult,
        verbose: bool,
    ) -> int:
        """Load BEA industry dimension from parsed data."""
        count = 0

        industries = sorted(parse_result.industries, key=lambda x: x.line_number)
        industry_iter = tqdm(industries, desc="Industries", disable=not verbose)

        for bea_industry in industry_iter:
            dim_industry = DimBEAIndustry(
                bea_code=bea_industry.code,
                industry_name=bea_industry.name,
                bea_level=bea_industry.level,
                parent_bea_code=self._find_parent_code(bea_industry, industries),
                line_number=bea_industry.line_number,
            )
            session.add(dim_industry)
            session.flush()

            self._industry_cache[bea_industry.line_number] = dim_industry.bea_industry_id
            count += 1

        return count

    def _find_parent_code(
        self,
        industry: BEAIndustry,
        all_industries: list[BEAIndustry],
    ) -> str | None:
        """Find parent industry code based on hierarchy level."""

        if industry.level == 1:
            return None  # Top-level has no parent

        # Find the closest preceding industry with a lower level
        parent_level = industry.level - 1
        for prev_industry in reversed(all_industries):
            if prev_industry.line_number >= industry.line_number:
                continue
            if prev_industry.level == parent_level:
                return prev_industry.code
            if prev_industry.level < parent_level:
                # We've gone past potential parents
                return prev_industry.code

        return None

    def _load_fact_table(
        self,
        session: Session,
        gross_output: BEAParseResult,
        value_added: BEAParseResult,
        intermediate_inputs: BEAParseResult,
        verbose: bool,
    ) -> int:
        """Load fact table by merging all three value types.

        Creates one fact row per industry-year with gross_output, value_added,
        and intermediate_inputs columns populated from the respective sources.
        """
        count = 0

        # Build lookup dictionaries for fast access
        go_lookup: dict[tuple[int, int], Decimal | None] = {}
        for v in gross_output.values:
            go_lookup[(v.line_number, v.year)] = v.value_millions

        va_lookup: dict[tuple[int, int], Decimal | None] = {}
        for v in value_added.values:
            va_lookup[(v.line_number, v.year)] = v.value_millions

        ii_lookup: dict[tuple[int, int], Decimal | None] = {}
        for v in intermediate_inputs.values:
            ii_lookup[(v.line_number, v.year)] = v.value_millions

        # Get all unique (industry, year) combinations
        all_keys: set[tuple[int, int]] = set()
        all_keys.update(go_lookup.keys())
        all_keys.update(va_lookup.keys())
        all_keys.update(ii_lookup.keys())

        keys_list = sorted(all_keys)
        keys_iter = tqdm(keys_list, desc="Fact rows", disable=not verbose)

        for line_number, year in keys_iter:
            industry_id = self._industry_cache.get(line_number)
            if not industry_id:
                continue

            time_id = self._get_or_create_time(session, year)

            fact = FactBEANationalIndustry(
                bea_industry_id=industry_id,
                time_id=time_id,
                gross_output_millions=go_lookup.get((line_number, year)),
                value_added_millions=va_lookup.get((line_number, year)),
                intermediate_inputs_millions=ii_lookup.get((line_number, year)),
            )
            session.add(fact)
            count += 1

            # Periodic flush to avoid memory issues
            if count % 5000 == 0:
                session.flush()

        session.flush()
        return count

    def _validate_accounting_identity(self, session: Session) -> None:
        """Validate that gross_output = intermediate_inputs + value_added.

        The accounting identity should hold within a small tolerance (rounding).
        This is a sanity check on data quality.
        """
        # Query to check accounting identity
        # Note: Using raw SQL for aggregation
        from sqlalchemy import text

        result = session.execute(
            text("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(CASE
                        WHEN gross_output_millions IS NOT NULL
                        AND intermediate_inputs_millions IS NOT NULL
                        AND value_added_millions IS NOT NULL
                        THEN 1
                    END) as complete_rows,
                    AVG(CASE
                        WHEN gross_output_millions IS NOT NULL
                        AND intermediate_inputs_millions IS NOT NULL
                        AND value_added_millions IS NOT NULL
                        THEN ABS(gross_output_millions - (intermediate_inputs_millions + value_added_millions))
                        ELSE NULL
                    END) as avg_discrepancy
                FROM fact_bea_national_industry
            """)
        ).fetchone()

        if result:
            total_rows, complete_rows, avg_discrepancy = result
            print("\nAccounting Identity Validation:")
            print(f"  Total rows: {total_rows:,}")
            print(f"  Complete rows (all 3 values): {complete_rows:,}")
            if avg_discrepancy is not None:
                print(f"  Avg discrepancy: ${avg_discrepancy:,.2f}M")
                if avg_discrepancy > 1.0:
                    logger.warning(
                        f"Accounting identity discrepancy exceeds $1M average: ${avg_discrepancy:,.2f}M"
                    )


__all__ = [
    "BEANationalLoader",
]
