"""Bootstrap the Postgres database with Feature 037 DDL.

Usage:
    PGHOST=/path/.pgsocket PGPORT=5433 python tools/bootstrap_postgres.py

Reads DDL from src/babylon/persistence/postgres_schema.py and applies
each statement to the 'babylon' database.
"""

from __future__ import annotations

import os
import sys

# Add src to path so we can import babylon
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import psycopg

from babylon.persistence.postgres_schema import POSTGRES_SCHEMA_DDL


def main() -> None:
    host = os.environ.get("PGHOST", "/tmp")
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ.get("PGDATABASE", "babylon")
    user = os.environ.get("PGUSER", os.getenv("USER", "user"))

    conninfo = f"host={host} port={port} dbname={dbname} user={user}"
    print(f"Connecting: {conninfo}")

    with psycopg.connect(conninfo, autocommit=True) as conn:
        for i, stmt in enumerate(POSTGRES_SCHEMA_DDL):
            stmt_stripped = stmt.strip()
            # Extract a short label from the DDL
            if "CREATE TABLE" in stmt_stripped:
                tbl = stmt_stripped.split("(")[0].split()[-1]
                label = f"TABLE {tbl}"
            elif "CREATE INDEX" in stmt_stripped:
                parts = stmt_stripped.split()
                idx_pos = next((j for j, p in enumerate(parts) if p.upper() == "ON"), 6)
                label = f"INDEX → {parts[idx_pos + 1] if idx_pos + 1 < len(parts) else '?'}"
            elif "CREATE EXTENSION" in stmt_stripped:
                label = f"EXTENSION {stmt_stripped.split()[-1]}"
            elif "CREATE UNLOGGED" in stmt_stripped:
                tbl = stmt_stripped.split("(")[0].split()[-1]
                label = f"UNLOGGED {tbl}"
            else:
                label = stmt_stripped[:60]

            try:
                conn.execute(stmt_stripped)
                print(f"  [{i + 1:2d}/{len(POSTGRES_SCHEMA_DDL)}] ✅ {label}")
            except Exception as e:
                print(f"  [{i + 1:2d}/{len(POSTGRES_SCHEMA_DDL)}] ❌ {label}: {e}")

    # Verify
    with psycopg.connect(conninfo) as conn:
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        ).fetchall()
        print(f"\n✅ {len(tables)} tables in 'public' schema:")
        for (t,) in tables:
            print(f"   - {t}")


if __name__ == "__main__":
    main()
