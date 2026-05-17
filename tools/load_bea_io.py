"""CLI entrypoint for the BEA national I-O ingest pipeline (spec-068).

Stages:
    US1: Populate fact_bea_national_industry from Supply-Use XLSX.
    US2: Populate fact_bea_io_coefficient from Make+Use IOUse and TDR XLSX.
    US3: Populate bridge_naics_bea concordance + wire hex_hydrator.
    US4: Validate per-county c/v distribution against Shaikh bands.

Modes:
    --rollback         Truncate fact_bea_national_industry and
                       fact_bea_io_coefficient to empty pre-spec-068 state.
    --dry-run          Parse + validate but do not write to DB.
    --reload-concordance
                       Re-populate bridge_naics_bea from the BEA concordance
                       bundle (default: only on first run).

Per spec-068 SC-007, the full live run targets <15 minutes wallclock for
the 2010-2024 ingest scope. The spec-067 PRAGMA work (WAL, 2 GiB cache,
12 GB mmap) on the reference DB is a prerequisite.

Audit reports land at reports/ingest/bea_io_<timestamp>.{md,json}.

Usage::

    poetry run python tools/load_bea_io.py --years 2010-2024
    poetry run python tools/load_bea_io.py --rollback
    poetry run python tools/load_bea_io.py --dry-run --years 2010-2024
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime

from babylon.reference.bea.ingest.audit_report import BEAIngestAuditReport
from babylon.reference.bea.ingest.schema_migration import ensure_vintage_columns
from babylon.reference.database import normalized_engine


def _parse_years(value: str) -> range:
    """Parse a ``--years`` argument like ``"2010-2024"`` into a ``range``.

    Args:
        value: String of form ``"START-END"`` (inclusive on both ends).

    Returns:
        ``range(START, END + 1)``.

    Raises:
        argparse.ArgumentTypeError: If the value is malformed or START > END.
    """
    try:
        start_str, end_str = value.split("-", 1)
        start, end = int(start_str), int(end_str)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--years must be of form 'START-END' (got {value!r})"
        ) from exc
    if start > end:
        raise argparse.ArgumentTypeError(f"--years START ({start}) must be <= END ({end})")
    return range(start, end + 1)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for ``load_bea_io.py``."""
    parser = argparse.ArgumentParser(
        prog="load_bea_io",
        description=(
            "Ingest BEA national I-O tables into the reference DB. "
            "Spec-068. See specs/068-bea-national-io-ingest/quickstart.md."
        ),
    )
    parser.add_argument(
        "--years",
        type=_parse_years,
        default=_parse_years("2010-2024"),
        help="Year range to ingest, inclusive (default: 2010-2024).",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help=(
            "Truncate fact_bea_national_industry and fact_bea_io_coefficient "
            "to empty pre-spec-068 state. Does NOT truncate bridge_naics_bea "
            "(shared with spec-025)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate but do not write to the reference DB.",
    )
    parser.add_argument(
        "--reload-concordance",
        action="store_true",
        help=(
            "Force re-population of bridge_naics_bea from the BEA concordance "
            "bundle (default: only on first run when the table is empty)."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Logging verbosity (default: INFO).",
    )
    return parser


def _run_rollback_stage(audit_report: BEAIngestAuditReport) -> None:
    """Truncate spec-068 fact tables to empty state (FR-009).

    Populates ``audit_report.rows_inserted`` with negative counts to
    indicate the deletion magnitude.
    """
    from sqlalchemy import text

    log = logging.getLogger("load_bea_io.rollback")
    engine = normalized_engine()
    with engine.begin() as conn:
        for table_name in (
            "fact_bea_io_coefficient",  # dependent first
            "fact_bea_national_industry",
        ):
            before = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0
            conn.execute(text(f"DELETE FROM {table_name}"))
            log.info("rollback: truncated %s (rows removed: %d)", table_name, before)
            audit_report.rows_inserted[table_name] = -int(before)
        conn.execute(text("VACUUM"))
    log.info("rollback complete; bridge_naics_bea left intact (shared with spec-025)")


def _run_us1_stage(
    audit_report: BEAIngestAuditReport,
    years: range,
    dry_run: bool,  # noqa: ARG001 — future-use; current impl is parser-only
) -> None:
    """US1: populate fact_bea_national_industry. Wired in T026."""
    log = logging.getLogger("load_bea_io.us1")
    _ = audit_report, years
    log.info("US1 stage: not yet wired (T026 — Phase 3 US1 work pending)")


def _run_us2_stage(
    audit_report: BEAIngestAuditReport,
    years: range,
    dry_run: bool,  # noqa: ARG001
) -> None:
    """US2: populate fact_bea_io_coefficient. Wired in T038."""
    log = logging.getLogger("load_bea_io.us2")
    _ = audit_report, years
    log.info("US2 stage: not yet wired (T038 — Phase 4 US2 work pending)")


def _run_us3_stage(
    audit_report: BEAIngestAuditReport,
    reload_concordance: bool,
    dry_run: bool,  # noqa: ARG001
) -> None:
    """US3: populate bridge_naics_bea + hex_hydrator wiring. Wired in T054."""
    log = logging.getLogger("load_bea_io.us3")
    _ = audit_report, reload_concordance
    log.info("US3 stage: not yet wired (T054 — Phase 5 US3 work pending)")


def _finalize_audit_report(audit_report: BEAIngestAuditReport) -> None:
    """Compute final SC pass/fail gates and the SC-007 wallclock judgement."""
    audit_report.sc_007_wallclock_seconds = audit_report.duration_seconds
    audit_report.sc_007_pass = audit_report.duration_seconds < 900.0  # 15 minutes


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint.

    Returns:
        Process exit code (0 = success, non-zero = failure).
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    log = logging.getLogger("load_bea_io")
    log.info(
        "spec-068 BEA I-O ingest starting (years=%d-%d, rollback=%s, dry_run=%s)",
        args.years.start,
        args.years.stop - 1,
        args.rollback,
        args.dry_run,
    )

    start_time = time.monotonic()
    audit_report = BEAIngestAuditReport(
        timestamp=datetime.now(UTC),
        sim_years_in_scope=tuple(args.years),
        dry_run=args.dry_run,
    )

    # Schema migration (T009) — idempotent ALTER TABLE ADD COLUMN.
    if not args.dry_run:
        engine = normalized_engine()
        migration_result = ensure_vintage_columns(engine)
        for table, was_added in migration_result.items():
            log.info(
                "schema migration: %s vintage_published_date %s",
                table,
                "ADDED" if was_added else "already present",
            )

    if args.rollback:
        _run_rollback_stage(audit_report)
    else:
        _run_us1_stage(audit_report, args.years, args.dry_run)
        _run_us2_stage(audit_report, args.years, args.dry_run)
        _run_us3_stage(audit_report, args.reload_concordance, args.dry_run)
        # US4 is operator-driven via tools/validate_bea_io_against_shaikh.py.

    audit_report.duration_seconds = time.monotonic() - start_time
    _finalize_audit_report(audit_report)
    json_path, md_path = audit_report.write_to_disk()
    log.info("audit report written: %s + %s", json_path, md_path)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
