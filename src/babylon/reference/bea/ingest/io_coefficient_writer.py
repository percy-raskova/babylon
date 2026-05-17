"""UPSERT writer for ``fact_bea_io_coefficient`` (spec-068 US2).

Same vintage-supersession semantics as ``national_writer`` (research.md R7).
Keys on the existing unique constraint
``(time_id, table_type_id, source_industry_id, target_industry_id)``.
Bulk-inserts in 10K-row batches per research.md R6.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from babylon.reference.bea.ingest.audit_report import VintageSupersession
from babylon.reference.bea.ingest.national_writer import WriterStats
from babylon.reference.bea.models import BEAIOCoefficientRecord
from babylon.reference.schema import (
    DimBEAIOTableType,
    DimTime,
    FactBEAIOCoefficient,
)

log = logging.getLogger(__name__)

_BATCH_SIZE = 10_000


def _build_year_to_time_id(session: Session) -> dict[int, int]:
    rows = session.execute(
        select(DimTime.year, DimTime.time_id).where(DimTime.is_annual.is_(True))
    ).all()
    return {year: tid for year, tid in rows}  # noqa: C416


def _ensure_table_types(session: Session) -> dict[str, int]:
    """Return ``table_type -> table_type_id``, inserting missing rows.

    Spec-068 only writes ``USE`` and ``TOTAL_REQ`` records. Other table
    types (MAKE, SUPPLY) are conceptually allowed by the DB CHECK
    constraint but not used by this spec; they are inserted lazily by
    future ingest specs.
    """
    rows = session.execute(select(DimBEAIOTableType.table_type, DimBEAIOTableType.id)).all()
    existing = {tt: tid for tt, tid in rows}  # noqa: C416
    descriptions = {
        "USE": "Make+Use direct-requirements coefficients (a_ij)",
        "TOTAL_REQ": "Total Domestic Requirements (Leontief inverse)",
    }
    inserted_any = False
    for table_type, desc in descriptions.items():
        if table_type not in existing:
            session.execute(
                sqlite_insert(DimBEAIOTableType).values(table_type=table_type, description=desc)
            )
            inserted_any = True
    if inserted_any:
        session.commit()
        # Re-query to capture the new ids issued by SQLite autoincrement.
        rows = session.execute(select(DimBEAIOTableType.table_type, DimBEAIOTableType.id)).all()
        existing = {tt: tid for tt, tid in rows}  # noqa: C416
    return existing


def _fetch_existing_vintages(
    session: Session,
    keys: set[tuple[int, int, int, int]],
) -> dict[tuple[int, int, int, int], date | None]:
    """Return ``(time_id, table_type_id, source, target) -> vintage``."""
    if not keys:
        return {}
    existing: dict[tuple[int, int, int, int], date | None] = {}
    rows = session.execute(
        select(
            FactBEAIOCoefficient.time_id,
            FactBEAIOCoefficient.table_type_id,
            FactBEAIOCoefficient.source_industry_id,
            FactBEAIOCoefficient.target_industry_id,
            FactBEAIOCoefficient.vintage_published_date,
        )
    ).all()
    for tid, ttid, src, tgt, vintage in rows:
        key = (tid, ttid, src, tgt)
        if key in keys:
            existing[key] = vintage
    return existing


def upsert_io_coefficient_records(
    session: Session,
    records: Iterable[BEAIOCoefficientRecord],
) -> WriterStats:
    """UPSERT records into ``fact_bea_io_coefficient`` (FR-007 vintage-aware)."""
    year_to_time = _build_year_to_time_id(session)
    table_type_to_id = _ensure_table_types(session)
    stats = WriterStats()

    record_list = list(records)
    keys: set[tuple[int, int, int, int]] = set()
    for r in record_list:
        tid = year_to_time.get(r.year)
        ttid = table_type_to_id.get(r.table_type)
        if tid is None or ttid is None:
            continue
        keys.add((tid, ttid, r.source_industry_id, r.target_industry_id))

    existing_vintages = _fetch_existing_vintages(session, keys)

    rows_to_write: list[dict[str, object]] = []
    for record in record_list:
        tid = year_to_time.get(record.year)
        ttid = table_type_to_id.get(record.table_type)
        if tid is None or ttid is None:
            log.warning(
                "writer: skipping record with unmapped year=%d or table_type=%s",
                record.year,
                record.table_type,
            )
            continue

        key = (tid, ttid, record.source_industry_id, record.target_industry_id)
        existing_vintage = existing_vintages.get(key)
        incoming_vintage = record.vintage_published_date

        if (
            existing_vintage is not None
            and incoming_vintage is not None
            and existing_vintage >= incoming_vintage
        ):
            stats.rows_unchanged += 1
            continue

        if existing_vintage is not None and incoming_vintage is not None:
            stats.supersessions.append(
                VintageSupersession(
                    table_name="fact_bea_io_coefficient",
                    bea_industry_id=record.target_industry_id,
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
                "time_id": tid,
                "table_type_id": ttid,
                "source_industry_id": record.source_industry_id,
                "target_industry_id": record.target_industry_id,
                "coefficient": record.coefficient,
                "vintage_published_date": record.vintage_published_date,
            }
        )

    for batch_start in range(0, len(rows_to_write), _BATCH_SIZE):
        batch = rows_to_write[batch_start : batch_start + _BATCH_SIZE]
        if not batch:
            continue
        stmt = sqlite_insert(FactBEAIOCoefficient).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "time_id",
                "table_type_id",
                "source_industry_id",
                "target_industry_id",
            ],
            set_={
                "coefficient": stmt.excluded.coefficient,
                "vintage_published_date": stmt.excluded.vintage_published_date,
            },
        )
        session.execute(stmt)

    session.commit()
    return stats
