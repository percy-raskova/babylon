"""Persistence layer for simulation runtime state.

This module provides SQLite-based persistence for simulation runs,
implementing the unified SQLite architecture per ADR030.

Components:
    - RuntimeDatabase: Per-run SQLite database for tick-keyed state
    - RUNTIME_SCHEMA_DDL: Schema definitions for runtime tables

Architecture (ADR030/031/032/033):
    The persistence layer uses tick-keyed temporal tables where
    (tick, entity_id) forms the fundamental identity. This enables:
    - Temporal queries: state at any tick
    - Diff computation: changes between ticks
    - Deterministic replay: from seeds and mutations

See Also:
    - ai-docs/decisions/ADR030_unified_sqlite_runtime.yaml
    - ai-docs/decisions/ADR031_tick_keyed_temporal_tables.yaml
"""

from babylon.persistence.runtime_db import RuntimeDatabase
from babylon.persistence.runtime_schema import RUNTIME_SCHEMA_DDL

__all__ = [
    "RuntimeDatabase",
    "RUNTIME_SCHEMA_DDL",
]
