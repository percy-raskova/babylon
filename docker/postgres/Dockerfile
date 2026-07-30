# Isolated test/runtime Postgres for Babylon (spec-087 FR-002).
#
# Base: postgis/postgis 17-3.5 — DIGEST-PINNED (ADR176 ruling 33: the PG 17
# move + "the postgres image digest-pin (as a ceremony)"). The player ships
# PostgreSQL 17 via the flake closure (flake.nix postgresql_17.withPackages
# [postgis pgvector]); dev/CI running 16 left every config value and plan
# shape unverified against the shipping major (postgres brief, Profile 2).
# Debian variant so pgvector installs from PGDG apt.
#
# THE PIN CEREMONY: the tag names the intent, the digest IS the contract —
# a re-tagged upstream image can never silently change what CI builds on.
# Bumping the digest is a DECLARED change: pull the new tag, record
# `docker inspect --format='{{index .RepoDigests 0}}'`, update BOTH lines
# below in one commit whose message states the old and new digests, and
# re-run the qa byte-gates + test:integration-pg before merging.
#
# Pinned 2026-07-29: tag 17-3.5, digest
# sha256:77e89c11c4779c394ebeeaac1099dafb77b728abc8cd45dcaf6c4695503a0c37
FROM postgis/postgis:17-3.5@sha256:77e89c11c4779c394ebeeaac1099dafb77b728abc8cd45dcaf6c4695503a0c37

# upgrade: pulling the base's security channel at build time cures the
# fixable CVE set; the no-fix residue is upstream's. pgvector from PGDG,
# matched to the major (postgresql-17-pgvector).
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/*
