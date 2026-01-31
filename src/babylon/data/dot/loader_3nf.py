"""DOT HPMS loader for 3NF schema population."""

from __future__ import annotations

import csv
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete

from babylon.data.loader_base import DataLoader, LoadStats
from babylon.data.reference.schema import (
    DimCounty,
    DimDataSource,
    DimState,
    DimTime,
    FactHpmsRoadSegment,
)
from babylon.data.utils import BatchWriter, build_county_fips, normalize_numeric_fips
from babylon.data.utils.field_parsers import parse_decimal, parse_int, parse_str

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


def _build_road_segment_row(
    row: dict[str, str | None],
    county_id: int,
    state_id: int,
    source_id: int,
    time_id: int | None,
    year_record: int | None,
) -> dict[str, Any]:
    """Build a road segment fact row dictionary from CSV data."""
    geometry_wkt = parse_str(row.get("line"))
    if geometry_wkt:
        geometry_wkt = geometry_wkt.strip('"')

    return {
        "county_id": county_id,
        "state_id": state_id,
        "source_id": source_id,
        "time_id": time_id,
        "route_id": parse_str(row.get("ROUTE_ID")),
        "route_number": parse_str(row.get("ROUTE_NUMBER")),
        "route_signing": parse_str(row.get("ROUTE_SIGNING")),
        "route_qualifier": parse_str(row.get("ROUTE_QUALIFIER")),
        "functional_system": parse_int(row.get("F_SYSTEM")),
        "facility_type": parse_int(row.get("FACILITY_TYPE")),
        "aadt": parse_int(row.get("AADT")),
        "aadt_single_unit": parse_int(row.get("AADT_SINGLE_UNIT")),
        "aadt_combination": parse_int(row.get("AADT_COMBINATION")),
        "speed_limit": parse_int(row.get("SPEED_LIMIT")),
        "through_lanes": parse_int(row.get("THROUGH_LANES")),
        "lane_width": parse_decimal(row.get("LANE_WIDTH")),
        "section_length": parse_decimal(row.get("SectionLength")),
        "nhs": parse_int(row.get("NHS")),
        "nhfn": parse_int(row.get("NHFN")),
        "urban_id": parse_str(row.get("URBAN_ID")),
        "year_record": year_record,
        "shape_id": parse_str(row.get("ShapeId")),
        "sample_id": parse_str(row.get("SAMPLE_ID")),
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
            self._clear_checkpoints(session, "dot_hpms")
            session.flush()

        # Check if this file already completed (enables resume)
        file_hash = self._get_file_hash(csv_path)
        if self._is_completed(session, "dot_hpms", 0, file_hash, "file", "T"):
            if verbose:
                logger.info("Skipping completed HPMS file: %s", csv_path.name)
            return stats

        source_id = self._get_or_create_data_source(
            session,
            source_code="DOT_HPMS",
            source_name="FHWA Highway Performance Monitoring System",
            source_url="https://www.fhwa.dot.gov/policyinformation/hpms.cfm",
            source_agency="Federal Highway Administration",
        )

        lookups = self._initialize_lookups(session, source_id)
        counts = self._process_file(session, csv_path, lookups)

        # Mark file as completed after successful processing
        self._mark_completed(session, "dot_hpms", 0, file_hash, "file", "T", counts["loaded"])

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

        # Set CSV field size limit to handle large WKT geometry fields (up to ~300KB observed)
        # Default is 131,072 bytes which is insufficient for HPMS LineString data
        csv.field_size_limit(500_000)

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

        year_record = parse_int(row.get("YEAR_RECORD"))
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

    def _get_file_hash(self, path: Path) -> str:
        """Create a short hash of file path for checkpoint key.

        Uses file path (not content) for fast, deterministic checkpointing.
        The same file at the same path will always produce the same hash.
        """
        return hashlib.md5(str(path).encode()).hexdigest()[:16]
