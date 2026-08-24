# syntax=docker/dockerfile:1.6

# Isolated test/runtime Postgres for Babylon (spec-087 FR-002).
#
# Base: postgis/postgis 17-3.5 — digest-pinned (ADR176 ruling 33: the PG 17
# move + image-pin ceremony). The player ships
# PostgreSQL 17 via the flake closure (flake.nix postgresql_17.withPackages
# [postgis pgvector]); dev/CI running 16 left every config value and plan
# shape unverified against the shipping major (postgres brief, Profile 2).
# Debian variant paired with one checksum-pinned archived pgvector package.
#
# THE PIN CEREMONY: the base digest plus the archived package checksum define
# the runtime/package contract. Derived OCI metadata need not be byte-identical.
# Changing either pin is a declared change: record the old and new identities
# and re-run the applicable PostgreSQL integration gates before merging.
#
# Pinned 2026-07-29: tag 17-3.5, digest
# sha256:77e89c11c4779c394ebeeaac1099dafb77b728abc8cd45dcaf6c4695503a0c37
FROM postgis/postgis:17-3.5@sha256:77e89c11c4779c394ebeeaac1099dafb77b728abc8cd45dcaf6c4695503a0c37

ADD --checksum=sha256:ff0e10806fd87268e2dfac6b2d0aaa5fc2c24341188e7c24f3db7fd112c90f87 \
    https://apt-archive.postgresql.org/pub/repos/apt/pool/main/p/pgvector/postgresql-17-pgvector_0.8.5-1.pgdg11+1_amd64.deb \
    /tmp/postgresql-17-pgvector.deb

RUN dpkg --install /tmp/postgresql-17-pgvector.deb \
    && test "$(dpkg-query -W -f='${Version}' postgresql-17)" = "17.5-1.pgdg110+1" \
    && test "$(dpkg-query -W -f='${Version}' postgresql-17-postgis-3)" = \
        "3.5.2+dfsg-1.pgdg110+1" \
    && test "$(dpkg-query -W -f='${Version}' postgresql-17-pgvector)" = \
        "0.8.5-1.pgdg11+1" \
    && rm /tmp/postgresql-17-pgvector.deb
