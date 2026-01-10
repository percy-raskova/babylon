"""Employment industry loader for 3NF schema population."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.loaders.dimension_loader import DimensionLoader
from babylon.data.normalize.classifications import classify_class_composition
from babylon.data.normalize.schema import (
    DimCounty,
    DimDataSource,
    DimEmploymentArea,
    DimIndustry,
    DimOwnership,
    DimState,
    DimTime,
    FactEmploymentIndustryAnnual,
)
from babylon.data.qcew.parser import determine_area_type, determine_naics_level
from babylon.data.utils import BatchWriter, normalize_numeric_fips
from babylon.data.utils.field_parsers import parse_decimal, parse_float, parse_int, parse_str

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_EMPLOYMENT_PATH = Path("data/employment_industry")


def _normalize_area_code(raw_value: str) -> str:
    raw = raw_value.strip()
    if raw.isdigit():
        normalized = normalize_numeric_fips(raw, 5, min_length=4)
        return normalized or raw
    return raw


def _extract_state_fips(area_code: str) -> str | None:
    if not area_code:
        return None
    if area_code.startswith(("US", "CS", "C")):
        return None
    if area_code.isdigit() and len(area_code) >= 2:
        return area_code[:2]
    return None


def _determine_employment_area_type(area_code: str, agglvl_code: int | None) -> str:
    if area_code.startswith("US"):
        return "national"
    if area_code.startswith("CS"):
        return "csa"
    if area_code.startswith("C"):
        return "msa"
    if agglvl_code is None:
        return "other"
    area_type = determine_area_type(agglvl_code, area_code)
    if area_type == "msa" and 20 <= agglvl_code < 30:
        return "state"
    return area_type


def _discover_area_files(base_path: Path) -> list[Path]:
    if base_path.is_file():
        return [base_path]
    files: list[Path] = []
    for directory in sorted(base_path.glob("*.annual.by_area")):
        if not directory.is_dir():
            continue
        files.extend(sorted(directory.glob("*.csv")))
    return files


def _build_fact_row(
    row: dict[str, str | None],
    area_id: int,
    industry_id: int,
    ownership_id: int,
    time_id: int,
    agglvl_code: int | None,
) -> dict[str, Any]:
    """Build a fact row dictionary from CSV data.

    Extracts and parses all fact fields from the CSV row.
    """
    return {
        "area_id": area_id,
        "industry_id": industry_id,
        "ownership_id": ownership_id,
        "time_id": time_id,
        "agglvl_code": agglvl_code,
        "size_code": parse_str(row.get("size_code")),
        "qtr": parse_str(row.get("qtr")),
        "disclosure_code": parse_str(row.get("disclosure_code")),
        "annual_avg_estabs_count": parse_int(row.get("annual_avg_estabs_count")),
        "annual_avg_emplvl": parse_int(row.get("annual_avg_emplvl")),
        "total_annual_wages": parse_decimal(row.get("total_annual_wages")),
        "taxable_annual_wages": parse_decimal(row.get("taxable_annual_wages")),
        "annual_contributions": parse_decimal(row.get("annual_contributions")),
        "annual_avg_wkly_wage": parse_int(row.get("annual_avg_wkly_wage")),
        "avg_annual_pay": parse_int(row.get("avg_annual_pay")),
        "lq_disclosure_code": parse_str(row.get("lq_disclosure_code")),
        "lq_annual_avg_estabs_count": parse_float(row.get("lq_annual_avg_estabs_count")),
        "lq_annual_avg_emplvl": parse_float(row.get("lq_annual_avg_emplvl")),
        "lq_total_annual_wages": parse_float(row.get("lq_total_annual_wages")),
        "lq_taxable_annual_wages": parse_float(row.get("lq_taxable_annual_wages")),
        "lq_annual_contributions": parse_float(row.get("lq_annual_contributions")),
        "lq_annual_avg_wkly_wage": parse_float(row.get("lq_annual_avg_wkly_wage")),
        "lq_avg_annual_pay": parse_float(row.get("lq_avg_annual_pay")),
        "oty_disclosure_code": parse_str(row.get("oty_disclosure_code")),
        "oty_annual_avg_estabs_count_chg": parse_decimal(
            row.get("oty_annual_avg_estabs_count_chg")
        ),
        "oty_annual_avg_estabs_count_pct_chg": parse_float(
            row.get("oty_annual_avg_estabs_count_pct_chg")
        ),
        "oty_annual_avg_emplvl_chg": parse_decimal(row.get("oty_annual_avg_emplvl_chg")),
        "oty_annual_avg_emplvl_pct_chg": parse_float(row.get("oty_annual_avg_emplvl_pct_chg")),
        "oty_total_annual_wages_chg": parse_decimal(row.get("oty_total_annual_wages_chg")),
        "oty_total_annual_wages_pct_chg": parse_float(row.get("oty_total_annual_wages_pct_chg")),
        "oty_taxable_annual_wages_chg": parse_decimal(row.get("oty_taxable_annual_wages_chg")),
        "oty_taxable_annual_wages_pct_chg": parse_float(
            row.get("oty_taxable_annual_wages_pct_chg")
        ),
        "oty_annual_contributions_chg": parse_decimal(row.get("oty_annual_contributions_chg")),
        "oty_annual_contributions_pct_chg": parse_float(
            row.get("oty_annual_contributions_pct_chg")
        ),
        "oty_annual_avg_wkly_wage_chg": parse_decimal(row.get("oty_annual_avg_wkly_wage_chg")),
        "oty_annual_avg_wkly_wage_pct_chg": parse_float(
            row.get("oty_annual_avg_wkly_wage_pct_chg")
        ),
        "oty_avg_annual_pay_chg": parse_decimal(row.get("oty_avg_annual_pay_chg")),
        "oty_avg_annual_pay_pct_chg": parse_float(row.get("oty_avg_annual_pay_pct_chg")),
    }


class EmploymentIndustryLoader(DataLoader):
    """Loader for BLS QCEW employment industry data (by area)."""

    def get_dimension_tables(self) -> list[type]:
        return [DimDataSource, DimEmploymentArea, DimIndustry, DimOwnership, DimTime]

    def get_fact_tables(self) -> list[type]:
        return [FactEmploymentIndustryAnnual]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        stats = LoadStats(source="employment_industry")
        base_path = self._resolve_data_path(kwargs)

        if not base_path.exists():
            stats.errors.append(f"Employment industry data path not found: {base_path}")
            logger.error("Employment industry data path not found: %s", base_path)
            return stats

        files = _discover_area_files(base_path)
        if not files:
            stats.errors.append(f"No employment industry CSV files found in {base_path}")
            logger.error("No employment industry CSV files found in %s", base_path)
            return stats

        stats.files_processed = len(files)

        if reset:
            self._clear_existing_data(session, verbose)

        self._get_or_create_data_source(
            session,
            source_code="BLS_QCEW_AREA",
            source_name="BLS QCEW Employment by Area",
            source_url="https://www.bls.gov/cew/",
            source_agency="Bureau of Labor Statistics",
        )

        lookups = self._initialize_lookups(session)
        loaded = self._process_all_files(session, files, lookups)

        session.commit()
        self._record_stats(stats, lookups, loaded, verbose)
        return stats

    def _resolve_data_path(self, kwargs: dict[str, object]) -> Path:
        """Resolve the employment data path from kwargs or default."""
        data_path = kwargs.get("data_path")
        if isinstance(data_path, (str, Path)):
            return Path(data_path)
        return DEFAULT_EMPLOYMENT_PATH

    def _clear_existing_data(self, session: Session, verbose: bool) -> None:
        """Clear existing employment industry data."""
        if verbose:
            logger.info("Clearing existing employment industry data...")
        session.execute(delete(FactEmploymentIndustryAnnual))
        session.execute(delete(DimEmploymentArea))
        session.flush()

    def _initialize_lookups(self, session: Session) -> dict[str, Any]:
        """Initialize all dimension lookup dictionaries and loaders."""
        # Create DimensionLoaders for get-or-create pattern
        area_loader = DimensionLoader(session, DimEmploymentArea, "area_code")
        area_loader.initialize_from_db()

        industry_loader = DimensionLoader(session, DimIndustry, "naics_code")
        industry_loader.initialize_from_db()

        ownership_loader = DimensionLoader(session, DimOwnership, "own_code")
        ownership_loader.initialize_from_db()

        return {
            "state": {s.state_fips: s.state_id for s in session.query(DimState).all()},
            "county": {c.fips: c.county_id for c in session.query(DimCounty).all()},
            "state_filter": set(self.config.state_fips_list or []),
            "area_loader": area_loader,
            "industry_loader": industry_loader,
            "ownership_loader": ownership_loader,
        }

    def _process_all_files(
        self,
        session: Session,
        files: list[Path],
        lookups: dict[str, Any],
    ) -> int:
        """Process all CSV files and load facts with per-file commits."""
        writer = BatchWriter(session, self.config.batch_size)
        loaded = 0
        total_files = len(files)

        for i, csv_path in enumerate(files, 1):
            logger.info("Processing file %d/%d: %s", i, total_files, csv_path.name)
            file_loaded = self._process_csv_file(session, csv_path, lookups, writer)
            loaded += file_loaded
            # Commit after each file for resumability
            session.commit()
            logger.info("File %d/%d complete: %d facts loaded", i, total_files, file_loaded)

        return loaded

    def _process_csv_file(
        self,
        session: Session,
        csv_path: Path,
        lookups: dict[str, Any],
        writer: BatchWriter,
    ) -> int:
        """Process a single CSV file with per-file idempotency.

        For idempotent loading, this method:
        1. Reads all rows from the file
        2. Extracts unique area_codes
        3. Deletes existing facts for those areas (enables resume without duplicates)
        4. Inserts new facts
        """
        # Read all rows from file
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        if not rows:
            return 0

        # Extract unique area_codes from this file for idempotent delete
        area_codes: set[str] = set()
        for row in rows:
            raw_area = parse_str(row.get("area_fips"))
            if raw_area:
                area_codes.add(_normalize_area_code(raw_area))

        # Delete existing facts for these areas (idempotent per-file)
        if area_codes:
            area_ids_subq = (
                select(DimEmploymentArea.area_id)
                .where(DimEmploymentArea.area_code.in_(area_codes))
                .scalar_subquery()
            )
            session.execute(
                delete(FactEmploymentIndustryAnnual).where(
                    FactEmploymentIndustryAnnual.area_id.in_(area_ids_subq)
                )
            )
            session.flush()

        # Process and insert rows
        loaded = 0
        batch: list[dict[str, Any]] = []
        for row in rows:
            fact_row = self._process_csv_row(session, row, lookups)
            if fact_row is None:
                continue
            batch.append(fact_row)
            if len(batch) >= self.config.batch_size:
                loaded += writer.write(FactEmploymentIndustryAnnual, batch)
                batch.clear()

        # Flush remaining batch
        if batch:
            loaded += writer.write(FactEmploymentIndustryAnnual, batch)

        return loaded

    def _process_csv_row(
        self,
        session: Session,
        row: dict[str, str | None],
        lookups: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Process a single CSV row and return fact dictionary or None."""
        raw_area = parse_str(row.get("area_fips"))
        if not raw_area:
            return None

        area_code = _normalize_area_code(raw_area)
        agglvl_code = parse_int(row.get("agglvl_code"))
        area_type = _determine_employment_area_type(area_code, agglvl_code)

        state_fips = _extract_state_fips(area_code)
        state_filter = lookups["state_filter"]
        if state_filter and (not state_fips or state_fips not in state_filter):
            return None

        year = parse_int(row.get("year"))
        if year is None:
            return None

        county_id = self._resolve_county_id(area_code, area_type, lookups["county"])
        state_id = lookups["state"].get(state_fips) if state_fips else None
        area_id = self._get_or_create_area(
            area_code,
            parse_str(row.get("area_title")) or area_code,
            area_type,
            state_id,
            county_id,
            lookups["area_loader"],
        )

        industry_id = self._get_or_create_industry(
            session,
            parse_str(row.get("industry_code")) or "10",
            parse_str(row.get("industry_title")) or "Total, all industries",
            lookups["industry_loader"],
        )

        ownership_id = self._get_or_create_ownership(
            parse_str(row.get("own_code")) or "0",
            parse_str(row.get("own_title")) or "Total Covered",
            lookups["ownership_loader"],
        )

        time_id = self._get_or_create_time(session, year)

        return _build_fact_row(row, area_id, industry_id, ownership_id, time_id, agglvl_code)

    def _resolve_county_id(
        self, area_code: str, area_type: str, county_lookup: dict[str, int]
    ) -> int | None:
        """Resolve county_id for county-level areas."""
        if area_type == "county" and area_code.isdigit() and len(area_code) == 5:
            return county_lookup.get(area_code)
        return None

    def _record_stats(
        self,
        stats: LoadStats,
        lookups: dict[str, Any],
        loaded: int,
        verbose: bool,
    ) -> None:
        """Record loading statistics."""
        area_loader: DimensionLoader[DimEmploymentArea] = lookups["area_loader"]
        industry_loader: DimensionLoader[DimIndustry] = lookups["industry_loader"]
        ownership_loader: DimensionLoader[DimOwnership] = lookups["ownership_loader"]

        stats.dimensions_loaded["employment_areas"] = len(area_loader)
        stats.dimensions_loaded["industries"] = len(industry_loader)
        stats.dimensions_loaded["ownership"] = len(ownership_loader)
        stats.facts_loaded["employment_industry_annual"] = loaded
        stats.record_ingest("employment:areas", len(area_loader))
        stats.record_ingest("employment:industries", len(industry_loader))
        stats.record_ingest("employment:ownership", len(ownership_loader))
        stats.record_ingest("employment:employment_industry_annual", loaded)

        if verbose:
            logger.info(
                "Employment industry loading complete: %s areas, %s facts.",
                len(area_loader),
                loaded,
            )

    def _get_or_create_area(
        self,
        area_code: str,
        area_name: str,
        area_type: str,
        state_id: int | None,
        county_id: int | None,
        area_loader: DimensionLoader[DimEmploymentArea],
    ) -> int:
        """Get or create employment area dimension using DimensionLoader."""
        # Derive CBSA/CSA codes from area_code
        cbsa_code, csa_code = self._derive_area_codes(area_code, area_type)

        return area_loader.get_or_create(
            area_code=area_code,
            area_name=area_name,
            area_type=area_type,
            state_id=state_id,
            county_id=county_id,
            cbsa_code=cbsa_code,
            csa_code=csa_code,
        )

    def _derive_area_codes(self, area_code: str, area_type: str) -> tuple[str | None, str | None]:
        """Extract CBSA and CSA codes from area_code."""
        cbsa_code = None
        csa_code = None
        if area_code.startswith("CS"):
            csa_code = area_code[2:]
        elif area_code.startswith("C"):
            cbsa_code = area_code[1:]
        elif area_type == "msa":
            cbsa_code = area_code if area_code.isdigit() else None
        return cbsa_code, csa_code

    def _get_or_create_industry(
        self,
        session: Session,
        naics_code: str,
        industry_title: str,
        industry_loader: DimensionLoader[DimIndustry],
    ) -> int:
        """Get or create industry dimension, marking has_qcew_data=True.

        Uses DimensionLoader.get() for lookup, then handles the has_qcew_data
        flag update for existing records separately.
        """
        # Check if industry already exists (cache + DB lookup)
        existing_id = industry_loader.get(naics_code)
        if existing_id is not None:
            # Update has_qcew_data flag if needed
            existing = session.get(DimIndustry, existing_id)
            if existing and not existing.has_qcew_data:
                existing.has_qcew_data = True
            return existing_id

        # Create new industry with derived fields
        naics_level = determine_naics_level(naics_code)
        sector_code = naics_code[:2] if len(naics_code) >= 2 else None
        parent_code = naics_code[:-1] if len(naics_code) > 2 else None
        class_comp = classify_class_composition(naics_code, industry_title)

        return industry_loader.get_or_create(
            naics_code=naics_code,
            industry_title=industry_title,
            naics_level=naics_level,
            parent_naics_code=parent_code,
            sector_code=sector_code,
            class_composition=class_comp,
            has_qcew_data=True,
            has_productivity_data=False,
            has_fred_data=False,
        )

    def _get_or_create_ownership(
        self,
        own_code: str,
        own_title: str,
        ownership_loader: DimensionLoader[DimOwnership],
    ) -> int:
        """Get or create ownership dimension using DimensionLoader."""
        is_government = own_code in ("1", "2", "3", "4")
        is_private = own_code == "5"

        return ownership_loader.get_or_create(
            own_code=own_code,
            own_title=own_title,
            is_government=is_government,
            is_private=is_private,
        )
