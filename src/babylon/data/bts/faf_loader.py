"""BTS FAF5 CSV loader for geographic flow tensors.

Feature: 025-tensor-hierarchy
Date: 2026-02-26

Parses BTS Freight Analysis Framework 5 (FAF5) CSV data and loads geographic
commodity flow records into the 3NF schema.

FAF5 CSV Format (BTS standard export):
    - dms_orig: Origin CFS Area code (e.g., "11", "119")
    - dms_dest: Destination CFS Area code
    - sctg2: SCTG 2-digit commodity code (1-43)
    - dms_mode: Transportation mode (1=truck, 2=rail, 3=water, 4=air, 5=pipeline)
    - tons_YYYY: Estimated shipment tonnage (thousands) for year YYYY
    - value_YYYY: Estimated value (millions USD) for year YYYY
    - tmiles_YYYY: Estimated ton-miles (millions) for year YYYY

FAF5 data must be downloaded manually from:
    https://www.bts.gov/faf

The loader looks for FAF5.csv (or FAF5*.csv) at data/freight/faf/.

Usage:
    from babylon.data.bts.faf_loader import FAFLoader
    loader = FAFLoader()
    with session_factory() as session:
        stats = loader.load(session)

See Also:
    :mod:`babylon.data.loader_base`: DataLoader base class.
    :mod:`babylon.data.reference.schema`: DimCFSArea, FactFAFCommodityFlow.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import sqlalchemy as sa

from babylon.data.loader_base import DataLoader, LoaderConfig, LoadStats
from babylon.data.reference.schema import (
    DimCFSArea,
    DimSCTGCommodity,
    FactFAFCommodityFlow,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Default data directory relative to project root
DEFAULT_DATA_DIR = Path("data")

# Year-column prefixes in FAF5 CSV
_VALUE_PREFIX = "value_"
_TONS_PREFIX = "tons_"
_TMILES_PREFIX = "tmiles_"


class FAFCSVParser:
    """Parser for BTS FAF5 CSV row data.

    Extracts origin/destination CFS Area codes, SCTG commodity codes,
    transport modes, and flow values (tons, value, ton-miles) from
    FAF5 CSV rows.

    Example:
        >>> parser = FAFCSVParser()
        >>> headers = ["dms_orig", "dms_dest", "sctg2", "dms_mode", "value_2017"]
        >>> parser.extract_year_columns(headers, 2017)
        {'value': 'value_2017'}
    """

    def extract_year_columns(self, headers: list[str], year: int) -> dict[str, str]:
        """Find year-specific column names in the CSV header.

        Args:
            headers: List of CSV column header strings.
            year: Target year (e.g., 2017).

        Returns:
            Dict mapping 'value', 'tons', 'tmiles' to actual column names
            for each column present in headers.
        """
        header_set = set(headers)
        result: dict[str, str] = {}

        value_col = f"{_VALUE_PREFIX}{year}"
        if value_col in header_set:
            result["value"] = value_col

        tons_col = f"{_TONS_PREFIX}{year}"
        if tons_col in header_set:
            result["tons"] = tons_col

        tmiles_col = f"{_TMILES_PREFIX}{year}"
        if tmiles_col in header_set:
            result["tmiles"] = tmiles_col

        return result

    def parse_row(
        self,
        row: dict[str, str],
        year_cols: dict[str, str],
    ) -> tuple[str, str, int, int, float, float, float] | None:
        """Parse a single CSV row into a flow record.

        Args:
            row: Dict of column name -> value strings.
            year_cols: Year column mapping from :meth:`extract_year_columns`.

        Returns:
            Tuple ``(origin, dest, sctg2, mode, tons, value, tmiles)``,
            or None if required columns are missing or invalid.
        """
        orig = row.get("dms_orig", "").strip()
        dest = row.get("dms_dest", "").strip()
        sctg_str = row.get("sctg2", "").strip()
        mode_str = row.get("dms_mode", "").strip()

        if not orig or not dest or not sctg_str or not mode_str:
            return None

        # Normalize zero-padded zone codes: "011" → "11", "119" → "119"
        # FAF5 regional CSV uses 3-digit padding; factor files use bare integers.
        try:
            orig = str(int(orig))
            dest = str(int(dest))
        except ValueError:
            return None

        try:
            sctg2 = int(sctg_str)
            mode = int(mode_str)
        except ValueError:
            return None

        value = self._to_float(row.get(year_cols.get("value", ""), ""))
        tons = self._to_float(row.get(year_cols.get("tons", ""), ""))
        tmiles = self._to_float(row.get(year_cols.get("tmiles", ""), ""))

        return orig, dest, sctg2, mode, tons, value, tmiles

    @staticmethod
    def _to_float(value: str) -> float:
        """Convert string cell value to float, treating empty as 0.0.

        Args:
            value: String from a CSV cell.

        Returns:
            float value; 0.0 for empty, dash, or non-numeric strings.
        """
        stripped = value.strip() if value else ""
        if stripped in ("", ".", "-", "None"):
            return 0.0
        try:
            return float(stripped.replace(",", ""))
        except ValueError:
            return 0.0


class FAFLoader(DataLoader):
    """Loader for BTS FAF5 commodity flow data into 3NF schema.

    Reads FAF5 CSV data and populates:

    - ``dim_cfs_area``: CFS Area geographic zones
    - ``dim_sctg_commodity``: SCTG commodity codes
    - ``fact_faf_commodity_flow``: O-D flow records by year

    FAF5 data must be downloaded manually from https://www.bts.gov/faf
    and placed at ``data/freight/faf/FAF5.csv``.

    Args:
        config: LoaderConfig for operational settings.
        data_dir: Path to data directory. Defaults to ``data/``.

    Example:
        >>> loader = FAFLoader()
        >>> # stats = loader.load(session)  # requires FAF5.csv to be present
    """

    def __init__(
        self,
        config: LoaderConfig | None = None,
        data_dir: Path | None = None,
    ) -> None:
        """Initialize FAF loader.

        Args:
            config: LoaderConfig for operational settings.
            data_dir: Base data directory. Defaults to ``data/``.
        """
        super().__init__(config)
        self.data_dir = data_dir if data_dir is not None else DEFAULT_DATA_DIR
        self._parser = FAFCSVParser()

    def get_dimension_tables(self) -> list[type]:
        """Return dimension tables this loader populates.

        Returns:
            List containing DimCFSArea and DimSCTGCommodity.
        """
        return [DimCFSArea, DimSCTGCommodity]

    def get_fact_tables(self) -> list[type]:
        """Return fact tables this loader populates.

        Returns:
            List containing FactFAFCommodityFlow.
        """
        return [FactFAFCommodityFlow]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        """Load FAF5 commodity flow data into 3NF schema.

        Args:
            session: SQLAlchemy session.
            reset: If True, delete existing data before loading.
            verbose: If True, log progress information.
            **kwargs: Accepts ``year`` (int, default 2017) for target year.

        Returns:
            LoadStats with counts of loaded dimensions and facts.
        """
        raw_year = kwargs.get("year", 2022)
        year: int = int(raw_year) if isinstance(raw_year, (int, str)) else 2022
        stats = LoadStats(source="faf")
        csv_path = self._find_csv()

        if csv_path is None:
            msg = (
                f"FAF5 CSV not found under {self.data_dir / 'freight' / 'faf'}. "
                "Download from https://www.bts.gov/faf"
            )
            logger.warning(msg)
            stats.errors.append(msg)
            return stats

        with session.begin():
            if reset:
                self.clear_tables(session)

            source_id = self._get_or_create_data_source(
                session,
                source_code="BTS_FAF5",
                source_name="BTS Freight Analysis Framework 5",
                source_agency="Bureau of Transportation Statistics",
            )

            rows_loaded = self._process_csv(session, csv_path, source_id, year, verbose)

        stats.facts_loaded["fact_faf_commodity_flow"] = rows_loaded
        stats.files_processed = 1 if rows_loaded > 0 else 0
        return stats

    def _find_csv(self) -> Path | None:
        """Locate the FAF5 CSV file in the standard data directory.

        Search order:
        1. ``data/freight/faf/FAF5.csv`` (exact)
        2. ``data/freight/faf/FAF5*.csv`` (glob)
        3. ``data/freight/faf/region/FAF5*.csv`` (zone-level subdirectory)

        Returns:
            Path to CSV file, or None if not found.
        """
        faf_dir = self.data_dir / "freight" / "faf"
        if not faf_dir.exists():
            return None

        exact = faf_dir / "FAF5.csv"
        if exact.exists():
            return exact

        # Prefer zone-level (region/) over state-level aggregation
        region_candidates = sorted((faf_dir / "region").glob("FAF5*.csv"))
        if region_candidates:
            return region_candidates[0]

        candidates = sorted(faf_dir.glob("FAF5*.csv"))
        return candidates[0] if candidates else None

    def _process_csv(
        self,
        session: Session,
        csv_path: Path,
        source_id: int,
        year: int,
        verbose: bool,  # noqa: ARG002
    ) -> int:
        """Parse CSV and insert flow records into fact_faf_commodity_flow.

        Args:
            session: SQLAlchemy session.
            csv_path: Path to FAF5 CSV file.
            source_id: FK to dim_data_source.
            year: Target year for flow extraction.
            verbose: Enable progress logging (unused; kept for interface).

        Returns:
            Number of flow records inserted.
        """
        area_cache: dict[str, int] = {}
        sctg_cache: dict[int, int] = {}
        records: list[dict[str, object]] = []
        total = 0

        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            headers = list(reader.fieldnames or [])
            year_cols = self._parser.extract_year_columns(headers, year)

            if not year_cols:
                logger.warning("No year %d columns found in %s", year, csv_path)
                return 0

            for row in reader:
                parsed = self._parser.parse_row(row, year_cols)
                if parsed is None:
                    continue

                orig, dest, sctg2, mode, tons, value, tmiles = parsed
                orig_id = self._get_or_create_area(session, orig, area_cache)
                dest_id = self._get_or_create_area(session, dest, area_cache)
                sctg_id = self._get_or_create_sctg(session, sctg2, sctg_cache)

                records.append(
                    {
                        "origin_cfs_area_id": orig_id,
                        "dest_cfs_area_id": dest_id,
                        "sctg_id": sctg_id,
                        "source_id": source_id,
                        "year": year,
                        "value_millions": value if value != 0.0 else None,
                        "tons_thousands": tons if tons != 0.0 else None,
                        "ton_miles_millions": tmiles if tmiles != 0.0 else None,
                        "mode_code": str(mode),
                    }
                )

                if len(records) >= self.config.batch_size:
                    session.execute(sa.insert(FactFAFCommodityFlow), records)
                    session.flush()
                    total += len(records)
                    records.clear()

        if records:
            session.execute(sa.insert(FactFAFCommodityFlow), records)
            session.flush()
            total += len(records)
            records.clear()

        logger.info("Loaded %d FAF flows for year %d", total, year)
        return total

    def _get_or_create_area(self, session: Session, cfs_code: str, cache: dict[str, int]) -> int:
        """Get or create a DimCFSArea record.

        Args:
            session: SQLAlchemy session.
            cfs_code: CFS Area code string.
            cache: In-memory lookup cache (code -> cfs_area_id).

        Returns:
            cfs_area_id for the area.
        """
        if cfs_code in cache:
            return cache[cfs_code]

        existing = session.query(DimCFSArea).filter(DimCFSArea.cfs_code == cfs_code).first()
        if existing:
            cache[cfs_code] = existing.cfs_area_id
            return existing.cfs_area_id

        area = DimCFSArea(cfs_code=cfs_code, cfs_name=f"CFS Area {cfs_code}")
        session.add(area)
        session.flush()
        cache[cfs_code] = area.cfs_area_id
        return area.cfs_area_id

    def _get_or_create_sctg(self, session: Session, sctg2: int, cache: dict[int, int]) -> int:
        """Get or create a DimSCTGCommodity record.

        Args:
            session: SQLAlchemy session.
            sctg2: SCTG 2-digit code integer.
            cache: In-memory lookup cache (sctg2 int -> sctg_id).

        Returns:
            sctg_id for the commodity.
        """
        if sctg2 in cache:
            return cache[sctg2]

        sctg_code = f"{sctg2:02d}"
        existing = (
            session.query(DimSCTGCommodity).filter(DimSCTGCommodity.sctg_code == sctg_code).first()
        )
        if existing:
            cache[sctg2] = existing.sctg_id
            return existing.sctg_id

        commodity = DimSCTGCommodity(
            sctg_code=sctg_code,
            sctg_name=f"SCTG {sctg_code}",
        )
        session.add(commodity)
        session.flush()
        cache[sctg2] = commodity.sctg_id
        return commodity.sctg_id


__all__ = [
    "FAFCSVParser",
    "FAFLoader",
]
