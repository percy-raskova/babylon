"""Non-authoritative Python persistence periphery.

Authoritative campaign PostgreSQL persistence is owned solely by the Rust
``babylon-runtime`` composition root. Python retains the deterministic local
runtime database and dedicated periphery stores.

Components:
    - RuntimeDatabase: Per-run SQLite database for tick-keyed state
    - RuntimePersistence: Frozen local SQLite protocol
    - TraceRecorder: Buffered in-memory trace collector
    - VectorStoreProtocol: Backend-agnostic vector search interface

Architecture (ADR030/031/032/033 + Feature 037):
    The persistence layer uses tick-keyed temporal tables where
    (session_id, tick, entity_id) forms the fundamental identity.
    The SQLite runtime remains a frozen reference and test/periphery store.
"""

from babylon.persistence.pgvector_store import PgVectorStore
from babylon.persistence.protocols import (
    MonotonicityViolationError,
    ReadOnlyPostgres,
    RuntimePersistence,
    TraceLevel,
    VectorStoreProtocol,
)
from babylon.persistence.runtime_db import RuntimeDatabase
from babylon.persistence.runtime_schema import RUNTIME_SCHEMA_DDL

__all__ = [
    "MonotonicityViolationError",
    "PgVectorStore",
    "ReadOnlyPostgres",
    "RUNTIME_SCHEMA_DDL",
    "RuntimeDatabase",
    "RuntimePersistence",
    "TraceLevel",
    "VectorStoreProtocol",
]
