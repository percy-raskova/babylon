"""Schema drift detection for the normalized database."""

from __future__ import annotations

import pprint
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from alembic.autogenerate import compare_metadata
from alembic.ddl import impl as alembic_impl
from alembic.migration import MigrationContext
from sqlalchemy import Sequence as SaSequence
from sqlalchemy import String, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.schema import CreateColumn
from sqlalchemy.sql.functions import next_value

from babylon.data.exceptions import SchemaCheckError
from babylon.data.normalize import schema as _schema  # noqa: F401
from babylon.data.normalize.database import (
    NORMALIZED_DB_PATH,
    NormalizedBase,
    get_normalized_engine,
    init_normalized_db,
)

# DuckDB reflection is limited; focus drift checks on tables/columns.
_EXCLUDED_OBJECT_TYPES = {
    "check_constraint",
    "foreign_key_constraint",
    "index",
    "unique_constraint",
}

SchemaRepairStatus = Literal["applied", "failed", "skipped"]


@dataclass(frozen=True)
class SchemaRepairAction:
    """Record a single schema repair action."""

    op: str
    table: str | None = None
    column: str | None = None
    status: SchemaRepairStatus = "applied"
    details: dict[str, object] = field(default_factory=dict)

    def short_label(self) -> str:
        target = self.table or "<unknown>"
        if self.column:
            target = f"{target}.{self.column}"
        return f"{self.op} {target}".strip()

    def to_dict(self) -> dict[str, object]:
        return {
            "op": self.op,
            "table": self.table,
            "column": self.column,
            "status": self.status,
            "details": self.details,
        }


@dataclass
class SchemaRepairReport:
    """Aggregated schema repair results."""

    initial_diffs: list[Any] = field(default_factory=list)
    applied: list[SchemaRepairAction] = field(default_factory=list)
    failed: list[SchemaRepairAction] = field(default_factory=list)
    skipped: list[SchemaRepairAction] = field(default_factory=list)
    remaining_diffs: list[Any] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.applied or self.failed or self.skipped)

    def to_dict(self) -> dict[str, object]:
        return {
            "initial_diffs": list(self.initial_diffs),
            "applied": [action.to_dict() for action in self.applied],
            "failed": [action.to_dict() for action in self.failed],
            "skipped": [action.to_dict() for action in self.skipped],
            "remaining_diffs": list(self.remaining_diffs),
        }


def _types_equivalent(inspected_type: object, metadata_type: object) -> bool:
    if isinstance(inspected_type, String) and isinstance(metadata_type, String):
        inspected_len: int | None = inspected_type.length
        metadata_len: int | None = metadata_type.length
        if inspected_len is not None and metadata_len is not None:
            return bool(inspected_len == metadata_len)
        return True
    return False


def _ensure_duckdb_impl() -> None:
    """Register a fallback Alembic impl for DuckDB."""
    if "duckdb" not in alembic_impl._impls:
        alembic_impl._impls["duckdb"] = alembic_impl.DefaultImpl


def _include_object(
    _object: object,
    name: str | None,
    type_: str,
    _reflected: bool,
    _compare_to: object | None,
) -> bool:
    if type_ == "table" and name == "alembic_version":
        return False
    return type_ not in _EXCLUDED_OBJECT_TYPES


def collect_schema_diffs(engine: Engine | None = None) -> list[Any]:
    """Return Alembic autogenerate diffs between DB and model metadata."""
    resolved_engine = engine or get_normalized_engine()
    with resolved_engine.connect() as connection:
        _ensure_duckdb_impl()

        def _compare_type(
            _context: object,
            _inspected_column: object,
            _metadata_column: object,
            inspected_type: object,
            metadata_type: object,
        ) -> bool | None:
            if _types_equivalent(inspected_type, metadata_type):
                return False
            return None

        context = MigrationContext.configure(
            connection,
            opts={
                "compare_type": _compare_type,
                "compare_server_default": True,
                "include_object": _include_object,
            },
        )
        result = compare_metadata(context, NormalizedBase.metadata)
        # compare_metadata returns list but alembic lacks type stubs
        return list(result) if result else []


def format_schema_diffs(diffs: Sequence[Any]) -> str:
    """Render schema diffs for CLI output."""
    return pprint.pformat(list(diffs), width=120, sort_dicts=False)


def _quote_identifier(engine: Engine, name: str) -> str:
    preparer = engine.dialect.identifier_preparer
    return ".".join(preparer.quote(part) for part in name.split("."))


def _diff_target(diff: Sequence[Any]) -> tuple[str | None, str | None]:
    if not diff:
        return None, None
    op = diff[0]
    if op in {"add_table", "remove_table"}:
        table = diff[1]
        return getattr(table, "name", None), None
    if op in {"add_column", "remove_column"}:
        if len(diff) >= 4:
            schema_name = diff[1]
            table_name = diff[2]
            column = diff[3]
            table_ref = f"{schema_name}.{table_name}" if schema_name else table_name
            return table_ref, getattr(column, "name", None)
        table_name = diff[1] if len(diff) > 1 else None
        column = diff[2] if len(diff) > 2 else None
        return table_name, getattr(column, "name", None)
    table_name = diff[1] if len(diff) > 1 and isinstance(diff[1], str) else None
    column = diff[2] if len(diff) > 2 else None
    return table_name, getattr(column, "name", None)


def _classify_diffs(diffs: Sequence[Any]) -> tuple[list[Any], list[Any]]:
    additive: list[Any] = []
    blocking: list[Any] = []
    for diff in diffs:
        op = diff[0] if diff else None
        if op in {"add_table", "add_column"}:
            additive.append(diff)
        else:
            blocking.append(diff)
    return additive, blocking


def _ensure_table_sequences(table: object, connection: Connection) -> None:
    """Ensure sequences referenced by table defaults exist before creating."""
    sequences: list[SaSequence] = []
    for column in getattr(table, "columns", []):
        default = getattr(column, "server_default", None)
        if default is None:
            continue
        arg = getattr(default, "arg", None)
        if isinstance(arg, next_value) and hasattr(arg, "sequence"):
            seq = arg.sequence
            if isinstance(seq, SaSequence):
                sequences.append(seq)

    for sequence in sequences:
        try:
            sequence.create(bind=connection, checkfirst=True)
        except Exception:
            # Allow table creation to surface detailed errors if sequence creation fails.
            raise


def _merge_reports(base: SchemaRepairReport, other: SchemaRepairReport) -> SchemaRepairReport:
    base.initial_diffs.extend(other.initial_diffs)
    base.applied.extend(other.applied)
    base.failed.extend(other.failed)
    base.skipped.extend(other.skipped)
    base.remaining_diffs = list(other.remaining_diffs)
    return base


def apply_schema_repairs(
    engine: Engine | None = None,
    diffs: Sequence[Any] | None = None,
    recheck: bool = True,
) -> SchemaRepairReport:
    """Apply additive schema repairs (tables/columns) for drift diffs."""
    resolved_engine = engine or get_normalized_engine()
    target_diffs = list(diffs) if diffs is not None else collect_schema_diffs(resolved_engine)
    report = SchemaRepairReport(initial_diffs=list(target_diffs))

    additive, blocking = _classify_diffs(target_diffs)
    for diff in blocking:
        table_name, column_name = _diff_target(diff)
        report.skipped.append(
            SchemaRepairAction(
                op=diff[0] if diff else "unknown",
                table=table_name,
                column=column_name,
                status="skipped",
                details={"reason": "non_additive", "diff": diff},
            )
        )

    failed_diffs: list[Any] = []
    for diff in additive:
        op = diff[0]
        if op == "add_table":
            table = diff[1]
            table_name = getattr(table, "name", None)
            action = SchemaRepairAction(
                op=op,
                table=table_name,
                status="applied",
                details={"columns": [col.name for col in getattr(table, "columns", [])]},
            )
            try:
                with resolved_engine.begin() as connection:
                    _ensure_table_sequences(table, connection)
                    table.create(bind=connection, checkfirst=True)
                report.applied.append(action)
            except Exception as exc:  # pragma: no cover - engine-specific failures
                report.failed.append(
                    SchemaRepairAction(
                        op=op,
                        table=table_name,
                        status="failed",
                        details={"error": str(exc), "diff": diff},
                    )
                )
                failed_diffs.append(diff)
        elif op == "add_column":
            if len(diff) >= 4:
                schema_name = diff[1]
                table_name = diff[2]
                column = diff[3]
                table_ref = f"{schema_name}.{table_name}" if schema_name else table_name
            else:
                table_ref = diff[1]
                column = diff[2]
            column_name = getattr(column, "name", None)
            ddl = str(CreateColumn(column).compile(dialect=resolved_engine.dialect))
            statement = (
                f"ALTER TABLE {_quote_identifier(resolved_engine, table_ref)} ADD COLUMN {ddl}"
            )
            try:
                with resolved_engine.begin() as connection:
                    connection.execute(text(statement))
                report.applied.append(
                    SchemaRepairAction(
                        op=op,
                        table=table_ref,
                        column=column_name,
                        status="applied",
                        details={
                            "ddl": statement,
                            "nullable": getattr(column, "nullable", None),
                            "type": str(getattr(column, "type", "")),
                        },
                    )
                )
            except Exception as exc:  # pragma: no cover - engine-specific failures
                report.failed.append(
                    SchemaRepairAction(
                        op=op,
                        table=table_name,
                        column=column_name,
                        status="failed",
                        details={"ddl": statement, "error": str(exc), "diff": diff},
                    )
                )
                failed_diffs.append(diff)

    if recheck:
        report.remaining_diffs = collect_schema_diffs(resolved_engine)
    else:
        report.remaining_diffs = list(blocking) + failed_diffs

    return report


def get_schema_repair_report(
    engine: Engine | None = None,
    repair: bool = True,
    recheck: bool = True,
) -> SchemaRepairReport:
    """Collect schema diffs and optionally apply additive repairs."""
    report = SchemaRepairReport()

    if engine is None and not NORMALIZED_DB_PATH.exists():
        if repair:
            init_normalized_db()
            report.applied.append(
                SchemaRepairAction(
                    op="init_schema",
                    status="applied",
                    details={"path": str(NORMALIZED_DB_PATH)},
                )
            )
        else:
            raise SchemaCheckError(
                f"Normalized database not found at {NORMALIZED_DB_PATH}",
                hint="Run `mise run data:load` to build the normalized database.",
                details={"path": str(NORMALIZED_DB_PATH)},
            )

    resolved_engine = engine or get_normalized_engine()
    try:
        diffs = collect_schema_diffs(resolved_engine)
    except KeyError as exc:
        if str(exc).strip("'\"") == "duckdb":
            raise SchemaCheckError(
                "Alembic has no migration implementation for the 'duckdb' dialect.",
                hint=(
                    "Ensure `duckdb-engine` is installed and the DuckDB Alembic "
                    "fallback impl is registered before schema checks."
                ),
                details={"dialect": "duckdb"},
            ) from exc
        raise
    except Exception as exc:  # pragma: no cover - defensive catch
        raise SchemaCheckError(
            f"Schema check failed: {exc}",
            hint="Review the stack trace and verify database connectivity.",
        ) from exc

    if diffs:
        if repair:
            diff_report = apply_schema_repairs(
                engine=resolved_engine,
                diffs=diffs,
                recheck=recheck,
            )
            report = _merge_reports(report, diff_report)
        else:
            report.initial_diffs = list(diffs)
            report.remaining_diffs = list(diffs)

    return report


def check_normalized_schema(engine: Engine | None = None) -> str:
    """Check normalized DB schema against SQLAlchemy models.

    Returns:
        Success message if schema matches.

    Raises:
        SchemaCheckError: When schema drift or setup issues are detected.
    """
    report = get_schema_repair_report(engine=engine, repair=False)
    if report.remaining_diffs:
        details = format_schema_diffs(report.remaining_diffs)
        raise SchemaCheckError(
            "Schema drift detected between database and models.",
            hint=(
                f"Rebuild {NORMALIZED_DB_PATH} if the schema change is intentional, "
                "or update the SQLAlchemy models to match the database."
            ),
            details={"diffs": details},
        )

    return "Schema matches SQLAlchemy models."
