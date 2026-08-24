# syntax=docker/dockerfile:1.6

# Isolated test/runtime Postgres for Babylon (spec-087 FR-002).
#
# Base: postgis/postgis 17-3.5 — digest-pinned (ADR176 ruling 33: the PG 17
# move + image-pin ceremony). The player ships
# PostgreSQL 17 via the flake closure (flake.nix postgresql_17.withPackages
# [postgis pgvector]); dev/CI running 16 left every config value and plan
# shape unverified against the shipping major (postgres brief, Profile 2).
# Debian variant paired with checksum-pinned pgvector, h3-pg, and H3 core inputs.
#
# THE PIN CEREMONY: the image digests plus all five archive checksums define the
# runtime/package contract. Derived OCI metadata need not be byte-identical.
# Changing an input pin is a declared change: record the old and new identities
# and re-run the applicable PostgreSQL integration gates before merging.
#
# Pinned 2026-07-29: tag 17-3.5, digest
# sha256:77e89c11c4779c394ebeeaac1099dafb77b728abc8cd45dcaf6c4695503a0c37
FROM postgis/postgis:17-3.5@sha256:77e89c11c4779c394ebeeaac1099dafb77b728abc8cd45dcaf6c4695503a0c37 AS postgres-runtime

FROM gcc:12.2.0-bullseye@sha256:a3e091325c0af43bc9c1c576ddd155351d5b16438124421188bb4b4fcacc1452 AS h3-builder

ADD --checksum=sha256:0dc2e9a6860f06bf10bd8fadc03e35d9eeb4df46e33763a7e480e987758f385c \
    https://github.com/Kitware/CMake/releases/download/v3.31.12/cmake-3.31.12-linux-x86_64.tar.gz \
    /tmp/cmake.tar.gz
ADD --checksum=sha256:9f43e428d4145d3212b68a70970cc5b736ce544b4bec2f1d6f010225787ddef4 \
    https://apt-archive.postgresql.org/pub/repos/apt/pool/main/p/postgresql-17/postgresql-server-dev-17_17.5-1.pgdg110+1_amd64.deb \
    /tmp/postgresql-server-dev-17.deb

ADD --checksum=sha256:b7e56fb90d486897be3ccd4fdc007c724fc48abe1ff9bbe24bf351d3b8accc57 \
    https://github.com/zachasme/h3-pg/archive/ed9a09c834787abb5952318bccef1c4fee119f1d.tar.gz \
    /tmp/h3-pg.tar.gz
ADD --checksum=sha256:0da8a392a6ff77e76b60e6a331a49497d0935b6b7b6899da7a3e2786139b0441 \
    https://github.com/uber/h3/archive/refs/tags/v4.5.0.tar.gz \
    /tmp/h3-core.tar.gz

COPY --from=postgres-runtime /usr/lib/postgresql/17/bin/pg_config /usr/lib/postgresql/17/bin/pg_config

RUN mkdir /opt/cmake /tmp/h3-pg-source /tmp/h3-core-source \
    && tar --extract --gzip --file=/tmp/cmake.tar.gz \
        --directory=/opt/cmake --strip-components=1 \
    && dpkg-deb --extract /tmp/postgresql-server-dev-17.deb / \
    && test "$(/usr/lib/postgresql/17/bin/pg_config --version)" = \
        "PostgreSQL 17.5 (Debian 17.5-1.pgdg110+1)" \
    && tar --extract --gzip --file=/tmp/h3-pg.tar.gz \
        --directory=/tmp/h3-pg-source --strip-components=1 \
    && tar --extract --gzip --file=/tmp/h3-core.tar.gz \
        --directory=/tmp/h3-core-source --strip-components=1 \
    && /opt/cmake/bin/cmake -S /tmp/h3-pg-source -B /tmp/h3-pg-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DFETCHCONTENT_SOURCE_DIR_H3=/tmp/h3-core-source \
        -DPOSTGRESQL_VERSION=17 \
    && /opt/cmake/bin/cmake --build /tmp/h3-pg-build --parallel 2 \
    && DESTDIR=/tmp/h3-pg-install \
        /opt/cmake/bin/cmake --install /tmp/h3-pg-build --component h3-pg \
    && test -f /tmp/h3-pg-install/usr/lib/postgresql/17/lib/h3.so \
    && test -f /tmp/h3-pg-install/usr/share/postgresql/17/extension/h3.control \
    && test -f /tmp/h3-pg-install/usr/share/postgresql/17/extension/h3--4.5.0.sql

FROM postgis/postgis:17-3.5@sha256:77e89c11c4779c394ebeeaac1099dafb77b728abc8cd45dcaf6c4695503a0c37

ADD --checksum=sha256:ff0e10806fd87268e2dfac6b2d0aaa5fc2c24341188e7c24f3db7fd112c90f87 \
    https://apt-archive.postgresql.org/pub/repos/apt/pool/main/p/pgvector/postgresql-17-pgvector_0.8.5-1.pgdg11+1_amd64.deb \
    /tmp/postgresql-17-pgvector.deb

COPY --from=h3-builder /tmp/h3-pg-install/usr/ /usr/

RUN dpkg --install /tmp/postgresql-17-pgvector.deb \
    && test "$(dpkg-query -W -f='${Version}' postgresql-17)" = "17.5-1.pgdg110+1" \
    && test "$(dpkg-query -W -f='${Version}' postgresql-17-postgis-3)" = \
        "3.5.2+dfsg-1.pgdg110+1" \
    && test "$(dpkg-query -W -f='${Version}' postgresql-17-pgvector)" = \
        "0.8.5-1.pgdg11+1" \
    && grep --fixed-strings --line-regexp "default_version = '4.5.0'" \
        /usr/share/postgresql/17/extension/h3.control \
    && rm /tmp/postgresql-17-pgvector.deb
