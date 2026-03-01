"""Simulation database (ephemeral SQLite per-run).

The simulation database provides:
1. Fast row-based storage for time-series analysis
2. Ephemeral storage (each run creates fresh database)
3. Full tick-keyed temporal snapshots (ADR031)

This module replaces the previous DuckDB implementation per ADR030
(Unified SQLite Runtime Architecture).

Usage:
    from babylon.engine.simdb import SimulationDB

    # In-memory for tests
    with SimulationDB(in_memory=True) as sim:
        sim.con.execute("INSERT INTO tick_summary VALUES (...)")

    # File-based for production
    with SimulationDB(run_id="2024-01-01_scenario_A") as sim:
        sim.record_tick_summary(tick=0, total_c=100.0, ...)
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Paths relative to repository root
_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
RUNS_DIR = _REPO_ROOT / "data" / "runs"
REFERENCE_DB_PATH = _REPO_ROOT / "data" / "sqlite" / "marxist-data-3NF.sqlite"


class SimulationDB:
    """Ephemeral SQLite database for simulation state.

    Each simulation run creates a fresh database (or uses in-memory).
    Implements ADR030 (Unified SQLite Runtime) and ADR031 (Tick-Keyed
    Temporal Tables).

    Attributes:
        run_id: Unique identifier for this simulation run.
        db_path: Path to the SQLite file (None for in-memory).
        con: sqlite3 connection handle.
    """

    def __init__(
        self,
        run_id: str | None = None,
        in_memory: bool = False,
        attach_reference: bool = True,  # Kept for API compatibility, now a no-op
    ) -> None:
        """Initialize simulation database.

        Args:
            run_id: Unique run identifier. Defaults to timestamp-based ID.
            in_memory: If True, use :memory: database (no persistence).
            attach_reference: Deprecated. Previously used for DuckDB ATTACH.
                Now a no-op - reference data should be queried separately.
        """
        self.run_id = run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.in_memory = in_memory
        self._attach_reference = attach_reference  # Stored but unused

        if in_memory:
            self.db_path: Path | None = None
            self.con = sqlite3.connect(":memory:")
        else:
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            self.db_path = RUNS_DIR / f"{self.run_id}.sqlite"
            self.con = sqlite3.connect(str(self.db_path))

        # Enable foreign key enforcement
        self.con.execute("PRAGMA foreign_keys = ON")
        # Enable WAL mode for better concurrent read performance (file-based only)
        if not in_memory:
            self.con.execute("PRAGMA journal_mode = WAL")

        self._init_schema()

    def _init_schema(self) -> None:
        """Create simulation state tables."""
        from .schema import SIMULATION_SCHEMA_DDL

        for ddl in SIMULATION_SCHEMA_DDL:
            self.con.execute(ddl)
        self.con.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for explicit transactions.

        Usage:
            with sim.transaction() as con:
                con.execute("INSERT INTO ...")
                con.execute("UPDATE ...")

        Yields:
            sqlite3 connection within an active transaction.
        """
        self.con.execute("BEGIN TRANSACTION")
        try:
            yield self.con
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise

    def record_tick_summary(
        self,
        tick: int,
        total_c: float,
        total_v: float,
        total_s: float,
        avg_consciousness: float,
        uprising_count: int,
    ) -> None:
        """Record aggregate metrics for a simulation tick.

        Args:
            tick: Simulation tick number.
            total_c: Total constant capital (c).
            total_v: Total variable capital/wages (v).
            total_s: Total surplus value (s).
            avg_consciousness: Average class consciousness [0,1].
            uprising_count: Number of uprising events this tick.
        """
        exploitation_rate = total_s / total_v if total_v > 0 else 0.0
        profit_rate = total_s / (total_c + total_v) if (total_c + total_v) > 0 else 0.0

        self.con.execute(
            """
            INSERT OR REPLACE INTO tick_summary
            (tick, total_c, total_v, total_s, exploitation_rate,
             profit_rate, avg_consciousness, uprising_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tick,
                total_c,
                total_v,
                total_s,
                exploitation_rate,
                profit_rate,
                avg_consciousness,
                uprising_count,
            ),
        )
        self.con.commit()

    def set_metadata(self, key: str, value: str) -> None:
        """Store simulation metadata.

        Args:
            key: Metadata key (e.g., 'scenario_name', 'config_hash').
            value: Metadata value.
        """
        self.con.execute(
            """
            INSERT OR REPLACE INTO simulation_metadata (key, value)
            VALUES (?, ?)
            """,
            (key, value),
        )
        self.con.commit()

    def get_metadata(self, key: str) -> str | None:
        """Retrieve simulation metadata.

        Args:
            key: Metadata key.

        Returns:
            Metadata value or None if not found.
        """
        result = self.con.execute(
            "SELECT value FROM simulation_metadata WHERE key = ?",
            (key,),
        ).fetchone()
        return result[0] if result else None

    def close(self) -> None:
        """Close the database connection."""
        self.con.close()

    def __enter__(self) -> SimulationDB:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        location = ":memory:" if self.in_memory else str(self.db_path)
        return f"SimulationDB(run_id={self.run_id!r}, path={location})"
