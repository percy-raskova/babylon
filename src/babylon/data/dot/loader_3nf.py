"""DOT HPMS loader for 3NF schema population."""

from __future__ import annotations

import csv
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.normalize.schema import (
    DimCounty,
    DimDataSource,
    DimState,
    DimTime,
    FactHpmsRoadSegment,
)
from babylon.data.utils import BatchWriter, build_county_fips, normalize_numeric_fips

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

DEFAULT_HPMS_PATH = Path("data/dot")
DEFAULT_HPMS_FILENAME = "HPMS_Spatial_All_Sections_-_2024.csv"


def _resolve_hpms_path(data_path: object | None) -> Path | None:
    if isinstance(data_path, (str, Path)):
        path = Path(data_path)
        if path.is_file():
            return path
        if path.is_dir():
            explicit = path / DEFAULT_HPMS_FILENAME
            if explicit.exists():
                return explicit
            matches = sorted(path.glob("HPMS_Spatial*Sections*.csv"))
            if matches:
                return matches[0]
    else:
        default_path = DEFAULT_HPMS_PATH / DEFAULT_HPMS_FILENAME
        if default_path.exists():
            return default_path
        matches = sorted(DEFAULT_HPMS_PATH.glob("HPMS_Spatial*Sections*.csv"))
        if matches:
            return matches[0]
    return None


def _parse_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _parse_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


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


def _build_road_segment_row(
    row: dict[str, str | None],
    county_id: int,
    state_id: int,
    source_id: int,
    time_id: int | None,
    year_record: int | None,
) -> dict[str, Any]:
    """Build a road segment fact row dictionary from CSV data."""
    geometry_wkt = _parse_str(row.get("line"))
    if geometry_wkt:
        geometry_wkt = geometry_wkt.strip('"')

    return {
        "county_id": county_id,
        "state_id": state_id,
        "source_id": source_id,
        "time_id": time_id,
        "route_id": _parse_str(row.get("ROUTE_ID")),
        "route_number": _parse_str(row.get("ROUTE_NUMBER")),
        "route_signing": _parse_str(row.get("ROUTE_SIGNING")),
        "route_qualifier": _parse_str(row.get("ROUTE_QUALIFIER")),
        "functional_system": _parse_int(row.get("F_SYSTEM")),
        "facility_type": _parse_int(row.get("FACILITY_TYPE")),
        "aadt": _parse_int(row.get("AADT")),
        "aadt_single_unit": _parse_int(row.get("AADT_SINGLE_UNIT")),
        "aadt_combination": _parse_int(row.get("AADT_COMBINATION")),
        "speed_limit": _parse_int(row.get("SPEED_LIMIT")),
        "through_lanes": _parse_int(row.get("THROUGH_LANES")),
        "lane_width": _parse_decimal(row.get("LANE_WIDTH")),
        "section_length": _parse_decimal(row.get("SectionLength")),
        "nhs": _parse_int(row.get("NHS")),
        "nhfn": _parse_int(row.get("NHFN")),
        "urban_id": _parse_str(row.get("URBAN_ID")),
        "year_record": year_record,
        "shape_id": _parse_str(row.get("ShapeId")),
        "sample_id": _parse_str(row.get("SAMPLE_ID")),
        "geometry_wkt": geometry_wkt,
    }


class DotHpmsLoader(DataLoader):
    """Loader for DOT HPMS spatial roadway segments."""

    def get_dimension_tables(self) -> list[type]:
        return [DimDataSource, DimTime]

    def get_fact_tables(self) -> list[type]:
        return [FactHpmsRoadSegment]

    def load(
        self,
        session: Session,
        reset: bool = True,
        verbose: bool = True,
        **kwargs: object,
    ) -> LoadStats:
        stats = LoadStats(source="dot_hpms")
        csv_path = _resolve_hpms_path(kwargs.get("data_path"))

        if csv_path is None or not csv_path.exists():
            stats.errors.append("DOT HPMS CSV file not found.")
            logger.error("DOT HPMS CSV file not found.")
            return stats

        if reset:
            self._clear_existing_data(session, verbose)

        source_id = self._get_or_create_data_source(
            session,
            source_code="DOT_HPMS",
            source_name="FHWA Highway Performance Monitoring System",
            source_url="https://www.fhwa.dot.gov/policyinformation/hpms.cfm",
            source_agency="Federal Highway Administration",
        )

        lookups = self._initialize_lookups(session, source_id)
        counts = self._process_file(session, csv_path, lookups)

        session.commit()
        self._record_stats(stats, counts, verbose)
        return stats

    def _clear_existing_data(self, session: Session, verbose: bool) -> None:
        """Clear existing HPMS road segment data."""
        if verbose:
            logger.info("Clearing existing HPMS road segments...")
        session.execute(delete(FactHpmsRoadSegment))
        session.flush()

    def _initialize_lookups(self, session: Session, source_id: int) -> dict[str, Any]:
        """Initialize lookup dictionaries."""
        return {
            "state": {s.state_fips: s.state_id for s in session.query(DimState).all()},
            "county": {c.fips: c.county_id for c in session.query(DimCounty).all()},
            "state_filter": set(self.config.state_fips_list or []),
            "source_id": source_id,
        }

    def _process_file(
        self,
        session: Session,
        csv_path: Path,
        lookups: dict[str, Any],
    ) -> dict[str, int]:
        """Process the CSV file and return load counts."""
        writer = BatchWriter(session, self.config.batch_size)
        batch: list[dict[str, Any]] = []
        loaded = 0
        skipped_no_fips = 0
        skipped_missing_geo = 0

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                result = self._process_row(session, row, lookups)
                if result is None:
                    continue
                if isinstance(result, str):
                    if result == "no_fips":
                        skipped_no_fips += 1
                    else:  # "missing_geo"
                        skipped_missing_geo += 1
                    continue

                batch.append(result)
                if len(batch) >= self.config.batch_size:
                    loaded += writer.write(FactHpmsRoadSegment, batch)
                    batch.clear()

        if batch:
            loaded += writer.write(FactHpmsRoadSegment, batch)

        return {
            "loaded": loaded,
            "skipped_no_fips": skipped_no_fips,
            "skipped_missing_geo": skipped_missing_geo,
        }

    def _process_row(
        self,
        session: Session,
        row: dict[str, str | None],
        lookups: dict[str, Any],
    ) -> dict[str, Any] | str | None:
        """Process a single row. Returns dict, 'no_fips', 'missing_geo', or None."""
        state_fips = normalize_numeric_fips(row.get("StateID"), 2, min_length=1)
        if not state_fips:
            return "no_fips"

        state_filter = lookups["state_filter"]
        if state_filter and state_fips not in state_filter:
            return None

        county_fips = build_county_fips(state_fips, row.get("COUNTY_ID"))
        if not county_fips:
            return "no_fips"

        county_id = lookups["county"].get(county_fips)
        state_id = lookups["state"].get(state_fips)
        if county_id is None or state_id is None:
            return "missing_geo"

        year_record = _parse_int(row.get("YEAR_RECORD"))
        time_id = self._get_or_create_time(session, year_record) if year_record else None

        return _build_road_segment_row(
            row, county_id, state_id, lookups["source_id"], time_id, year_record
        )

    def _record_stats(
        self,
        stats: LoadStats,
        counts: dict[str, int],
        verbose: bool,
    ) -> None:
        """Record loading statistics."""
        loaded = counts["loaded"]
        skipped_no_fips = counts["skipped_no_fips"]
        skipped_missing_geo = counts["skipped_missing_geo"]

        stats.files_processed = 1
        stats.facts_loaded["hpms_road_segments"] = loaded
        stats.record_ingest("hpms:road_segments", loaded)
        if skipped_no_fips:
            stats.record_ingest("hpms:skipped_missing_fips", skipped_no_fips)
        if skipped_missing_geo:
            stats.record_ingest("hpms:skipped_missing_geo", skipped_missing_geo)

        if verbose:
            logger.info(
                "HPMS loading complete: %s segments (%s missing fips, %s missing geo).",
                loaded,
                skipped_no_fips,
                skipped_missing_geo,
            )
