"""Reconcile the ``document_chunk`` table with the actual ``PgVectorStore`` code.

Spec 061 FR-001 (Real Backend Wire-Up):
    The DDL in ``babylon.persistence.postgres_schema`` and the SQL in
    ``babylon.persistence.pgvector_store`` had diverged. The DDL declared
    columns ``id``, ``session_id``, ``source_file``, ``chunk_index``,
    ``content``, ``embedding``, ``metadata``, ``created_at``. The code
    inserted into ``chunk_id``, ``collection``, ``content``, ``embedding``,
    ``metadata``, ``source``, ``chunk_index`` — a six-column gap that
    raised ``UndefinedColumn`` on every ingest.

    The corrected schema follows the code: a single canonical embedding
    store keyed by ``(chunk_id)`` with a logical ``collection`` namespace
    instead of per-session scoping. ``session_id`` is removed — embeddings
    are never bound to a single game session.

This migration drops the broken table and re-creates it with the
corrected DDL. After migration ``0007`` purges all sessions, there are
no embeddings worth preserving (the table was unusable anyway).
"""

from __future__ import annotations

from django.db import migrations

DOCUMENT_CHUNK_DDL_NEW = """
CREATE TABLE document_chunk (
    chunk_id        VARCHAR(128) PRIMARY KEY,
    collection      VARCHAR(64) NOT NULL DEFAULT 'default',
    content         TEXT NOT NULL,
    embedding       vector(768) NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    source          VARCHAR(256),
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def forwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TABLE IF EXISTS document_chunk CASCADE;")
    schema_editor.execute(DOCUMENT_CHUNK_DDL_NEW)
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunk_collection ON document_chunk(collection);"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunk_embedding "
        "ON document_chunk USING hnsw (embedding vector_cosine_ops);"
    )


def backwards(apps, schema_editor):  # type: ignore[no-untyped-def]
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS idx_document_chunk_embedding;")
    schema_editor.execute("DROP INDEX IF EXISTS idx_document_chunk_collection;")
    schema_editor.execute("DROP TABLE IF EXISTS document_chunk;")


class Migration(migrations.Migration):
    dependencies = [
        ("game", "0009_action_result_unique"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
