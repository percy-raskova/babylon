"""Persistence layer for simulation runtime state.

This module provides both SQLite-based and PostgreSQL-based persistence
for simulation runs.

Components:
    - RuntimeDatabase: Per-run SQLite database for tick-keyed state
    - PostgresRuntime: PostgreSQL backend with session-scoped persistence
    - RuntimePersistence: Protocol for backend-agnostic access
    - TraceRecorder: Buffered in-memory trace collector
    - VectorStoreProtocol: Backend-agnostic vector search interface

Architecture (ADR030/031/032/033 + Feature 037):
    The persistence layer uses tick-keyed temporal tables where
    (session_id, tick, entity_id) forms the fundamental identity.
    Both SQLite (dev/test) and Postgres (production) implement
    the RuntimePersistence protocol.
"""

from babylon.persistence.archival import (
    export_session_to_parquet,
    purge_session,
    query_archived_session,
    upload_to_r2,
)
from babylon.persistence.pgvector_store import PgVectorStore
from babylon.persistence.postgres_runtime import PostgresRuntime
from babylon.persistence.protocols import (
    MonotonicityViolationError,
    PostgresRuntimeExtensions,
    RuntimePersistence,
    TraceCollector,
    TraceLevel,
    VectorStoreProtocol,
)
from babylon.persistence.runtime_db import RuntimeDatabase
from babylon.persistence.runtime_schema import RUNTIME_SCHEMA_DDL
from babylon.persistence.trace_recorder import TraceRecorder

__all__ = [
    "MonotonicityViolationError",
    "PgVectorStore",
    "PostgresRuntime",
    "PostgresRuntimeExtensions",
    "RUNTIME_SCHEMA_DDL",
    "RuntimeDatabase",
    "RuntimePersistence",
    "TraceCollector",
    "TraceLevel",
    "TraceRecorder",
    "VectorStoreProtocol",
    "export_session_to_parquet",
    "purge_session",
    "query_archived_session",
    "upload_to_r2",
]
