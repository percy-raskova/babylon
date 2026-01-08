"""LODES crosswalk loader for 3NF schema population."""

from __future__ import annotations

import csv
import gzip
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from sqlalchemy import delete

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.normalize.schema import BridgeLodesBlock, DimCounty
from babylon.data.utils import BatchWriter, build_county_fips, normalize_numeric_fips

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_LODES_PATH = Path("data/lodes")


def _resolve_lodes_path(data_path: object | None) -> Path | None:
    if isinstance(data_path, (str, Path)):
        path = Path(data_path)
        if path.is_file():
            return path
        if path.is_dir():
            csv_path = path / "us_xwalk.csv"
            if csv_path.exists():
                return csv_path
            gz_path = path / "us_xwalk.csv.gz"
            if gz_path.exists():
                return gz_path
    else:
        csv_path = DEFAULT_LODES_PATH / "us_xwalk.csv"
        if csv_path.exists():
            return csv_path
        gz_path = DEFAULT_LODES_PATH / "us_xwalk.csv.gz"
        if gz_path.exists():
            return gz_path
    return None


def _open_csv(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8", newline="")


def _parse_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _build_tract_geoid(
    state_fips: str | None,
    county_fips_only: str | None,
    tract: str | None,
) -> str | None:
    """Build tract GEOID from components."""
    if state_fips and county_fips_only and tract:
        return f"{state_fips}{county_fips_only}{tract}"
    return None


def _normalize_tract(tract: str | None) -> str | None:
    """Normalize tract code with zero-padding."""
    if tract and tract.isdigit():
        return tract.zfill(6)
    return tract


def _build_block_row(
    row: dict[str, str | None],
    county_id: int | None,
    state_fips: str | None,
    county_fips_only: str | None,
    tract_geoid: str | None,
) -> dict[str, Any]:
    """Build a LODES block row dictionary from CSV data."""
    return {
        "block_geoid": _parse_str(row.get("tabblk2020")),
        "county_id": county_id,
        "state_fips": state_fips,
        "county_fips": county_fips_only,
        "tract_geoid": tract_geoid,
        "block_group": _parse_str(row.get("bgrp")),
        "cbsa_code": _parse_str(row.get("cbsa")),
        "zcta": _parse_str(row.get("zcta")),
        "latitude": _parse_decimal(row.get("blklatdd")),
        "longitude": _parse_decimal(row.get("blklondd")),
    }


class LodesCrosswalkLoader(DataLoader):
    """Loader for LODES block crosswalk data."""

    def get_dimension_tables(self) -> list[type]:
        return [BridgeLodesBlock]

    def get_fact_tables(self) -> list[type]:
        return []

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        stats = LoadStats(source="lodes")
        csv_path = _resolve_lodes_path(kwargs.get("data_path"))

        if csv_path is None or not csv_path.exists():
            stats.errors.append("LODES crosswalk file not found.")
            logger.error("LODES crosswalk file not found.")
            return stats

        if reset:
            self._clear_existing_data(session, verbose)

        lookups = self._initialize_lookups(session)
        loaded, skipped = self._process_file(session, csv_path, lookups)

        session.commit()
        self._record_stats(stats, loaded, skipped, verbose)
        return stats

    def _clear_existing_data(self, session: Session, verbose: bool) -> None:
        """Clear existing LODES crosswalk data."""
        if verbose:
            logger.info("Clearing existing LODES crosswalk data...")
        session.execute(delete(BridgeLodesBlock))
        session.flush()

    def _initialize_lookups(self, session: Session) -> dict[str, Any]:
        """Initialize lookup dictionaries."""
        return {
            "county": {c.fips: c.county_id for c in session.query(DimCounty).all()},
            "state_filter": set(self.config.state_fips_list or []),
        }

    def _process_file(
        self,
        session: Session,
        csv_path: Path,
        lookups: dict[str, Any],
    ) -> tuple[int, int]:
        """Process the crosswalk file and return (loaded, skipped) counts."""
        writer = BatchWriter(session, self.config.batch_size)
        batch: list[dict[str, Any]] = []
        loaded = 0
        skipped_missing_geo = 0

        with _open_csv(csv_path) as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                result = self._process_row(row, lookups)
                if result is None:
                    continue
                if isinstance(result, str):
                    skipped_missing_geo += 1
                    continue

                batch.append(result)
                if len(batch) >= self.config.batch_size:
                    loaded += writer.write(BridgeLodesBlock, batch)
                    batch.clear()

        if batch:
            loaded += writer.write(BridgeLodesBlock, batch)

        return loaded, skipped_missing_geo

    def _process_row(
        self,
        row: dict[str, str | None],
        lookups: dict[str, Any],
    ) -> dict[str, Any] | str | None:
        """Process a single row. Returns dict, 'skip_geo', or None."""
        state_fips = normalize_numeric_fips(row.get("st"), 2, min_length=1)
        state_filter = lookups["state_filter"]
        if state_fips and state_filter and state_fips not in state_filter:
            return None

        county_fips_only = normalize_numeric_fips(row.get("cty"), 3, min_length=1)
        county_fips = build_county_fips(state_fips, county_fips_only)
        county_id = lookups["county"].get(county_fips) if county_fips else None

        if county_fips and county_id is None:
            return "skip_geo"

        tract = _normalize_tract(_parse_str(row.get("trct")))
        tract_geoid = _build_tract_geoid(state_fips, county_fips_only, tract)

        return _build_block_row(row, county_id, state_fips, county_fips_only, tract_geoid)

    def _record_stats(
        self,
        stats: LoadStats,
        loaded: int,
        skipped_missing_geo: int,
        verbose: bool,
    ) -> None:
        """Record loading statistics."""
        stats.files_processed = 1
        stats.dimensions_loaded["lodes_blocks"] = loaded
        stats.record_ingest("lodes:blocks", loaded)
        if skipped_missing_geo:
            stats.record_ingest("lodes:skipped_missing_geo", skipped_missing_geo)

        if verbose:
            logger.info("LODES crosswalk loading complete: %s blocks.", loaded)
