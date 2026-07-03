# Isolated test/runtime Postgres for Babylon (spec-087 FR-002).
#
# Base: postgis/postgis:16-3.4 — pinned to the same major/minor family the
# integration testcontainers use (tests/integration/web/conftest.py uses the
# alpine variant; debian here so pgvector installs from PGDG apt).
# spec-037 requires PostgreSQL 16+ with PostGIS, pgvector, and uuid-ossp.
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
