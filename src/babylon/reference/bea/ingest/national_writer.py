"""UPSERT writer for ``fact_bea_national_industry`` (spec-068 US1).

Implements the vintage-supersession-aware UPSERT described in
research.md R7: a row with a strictly-newer ``vintage_published_date``
replaces the existing row; a row with an older-or-equal vintage is a
no-op (skipped). Idempotency target: epsilon-determinism ≤ 10⁻¹²
across two consecutive runs against the same source XLSX (FR-007).

Uses SQLAlchemy 2.x Core ``insert(...).on_conflict_do_update(...)``
batched at 10K rows per ``execute()`` per research.md R6.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from babylon.reference.bea.ingest.audit_report import VintageSupersession
from babylon.reference.bea.models import BEAIndustryAnnualRecord
from babylon.reference.schema import DimTime, FactBEANationalIndustry

log = logging.getLogger(__name__)

_BATCH_SIZE = 10_000


@dataclass
class WriterStats:
    """Per-run stats returned by ``upsert_national_records``."""

    rows_inserted: int = 0
    rows_superseded: int = 0
    rows_unchanged: int = 0
    supersessions: list[VintageSupersession] = field(default_factory=list)


def _build_year_to_time_id(session: Session) -> dict[int, int]:
    rows = session.execute(
        select(DimTime.year, DimTime.time_id).where(DimTime.is_annual.is_(True))
    ).all()
    return {year: tid for year, tid in rows}  # noqa: C416  # Row[tuple] is not a tuple per mypy


def _fetch_existing_vintages(
    session: Session,
    keys: list[tuple[int, int]],
) -> dict[tuple[int, int], date | None]:
    """Return ``(bea_industry_id, time_id) -> vintage_published_date`` for matches.

    Strategy: ``fact_bea_national_industry`` is at most ~1500 rows (spec-068
    cardinality target), so just SELECT the whole table once and filter
    in-memory rather than building a chunked IN clause.
    """
    if not keys:
        return {}
    keys_set = set(keys)
    existing: dict[tuple[int, int], date | None] = {}
    rows = session.execute(
        select(
            FactBEANationalIndustry.bea_industry_id,
            FactBEANationalIndustry.time_id,
            FactBEANationalIndustry.vintage_published_date,
        )
    ).all()
    for bea_id, tid, vintage in rows:
        if (bea_id, tid) in keys_set:
            existing[(bea_id, tid)] = vintage
    return existing


def upsert_national_records(
    session: Session,
    records: Iterable[BEAIndustryAnnualRecord],
) -> WriterStats:
    """UPSERT records into ``fact_bea_national_industry``.

    Vintage-supersession-aware: a record with a strictly-newer
    ``vintage_published_date`` than the existing DB row replaces it;
    a record with an older-or-equal vintage is a no-op skip.

    Args:
        session: SQLAlchemy session bound to the reference DB.
        records: Iterable of parsed ``BEAIndustryAnnualRecord``.

    Returns:
        :class:`WriterStats` summarizing how many rows landed in each
        bucket (inserted, superseded, unchanged).
    """
    year_to_time = _build_year_to_time_id(session)
    stats = WriterStats()

    # Materialize records once so we can both build the key list and write.
    record_list = list(records)
    keys = [
        (r.bea_industry_id, year_to_time[r.year]) for r in record_list if r.year in year_to_time
    ]
    existing_vintages = _fetch_existing_vintages(session, keys)

    rows_to_write: list[dict[str, object]] = []
    for record in record_list:
        tid = year_to_time.get(record.year)
        if tid is None:
            log.warning(
                "writer: year %d has no time_id mapping — skipping (bea_id=%d)",
                record.year,
                record.bea_industry_id,
            )
            continue

        existing_vintage = existing_vintages.get((record.bea_industry_id, tid))
        incoming_vintage = record.vintage_published_date

        if (
            existing_vintage is not None
            and incoming_vintage is not None
            and existing_vintage >= incoming_vintage
        ):
            # Older-or-equal vintage — skip (FR-007 + Clarification Q2).
            stats.rows_unchanged += 1
            continue

        if existing_vintage is not None and incoming_vintage is not None:
            stats.supersessions.append(
                VintageSupersession(
                    table_name="fact_bea_national_industry",
                    bea_industry_id=record.bea_industry_id,
                    year=record.year,
                    old_vintage=existing_vintage,
                    new_vintage=incoming_vintage,
                )
            )
            stats.rows_superseded += 1
        else:
            stats.rows_inserted += 1

        rows_to_write.append(
            {
                "bea_industry_id": record.bea_industry_id,
                "time_id": tid,
                "gross_output_millions": record.gross_output_millions,
                "intermediate_inputs_millions": record.intermediate_inputs_millions,
                "value_added_millions": record.value_added_millions,
                "vintage_published_date": record.vintage_published_date,
            }
        )

    # Batched UPSERT
    for batch_start in range(0, len(rows_to_write), _BATCH_SIZE):
        batch = rows_to_write[batch_start : batch_start + _BATCH_SIZE]
        if not batch:
            continue
        stmt = sqlite_insert(FactBEANationalIndustry).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["bea_industry_id", "time_id"],
            set_={
                "gross_output_millions": stmt.excluded.gross_output_millions,
                "intermediate_inputs_millions": stmt.excluded.intermediate_inputs_millions,
                "value_added_millions": stmt.excluded.value_added_millions,
                "vintage_published_date": stmt.excluded.vintage_published_date,
            },
        )
        session.execute(stmt)

    session.commit()
    return stats
