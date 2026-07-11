# Isolated test/runtime Postgres for Babylon (spec-087 FR-002).
#
# Base: postgis/postgis:16-3.5 — pinned to the same major/minor family the
# integration testcontainers use (tests/integration/web/conftest.py uses the
# alpine variant; debian here so pgvector installs from PGDG apt).
# spec-037 requires PostgreSQL 16+ with PostGIS, pgvector, and uuid-ossp.
FROM postgis/postgis:16-3.5

# upgrade: postgis's 16.x line ships bullseye and rebuilds irregularly —
# pulling bullseye-security at build time cures the fixable CVE set (94 of
# 184 HIGH/CRIT at 2026-07-11); the no-fix residue is upstream's. The
# alpine/PG17 base migration is an owner decision (touches the
# byte-identical qa:e2e-regression substrate).
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
