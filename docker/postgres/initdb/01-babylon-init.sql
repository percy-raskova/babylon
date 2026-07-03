-- Babylon first-boot init (spec-087 FR-003/FR-005).
-- Runs once when the data volume is empty (docker-entrypoint-initdb.d).
--
-- Extensions are created in template1 so `clean:testdb`'s
-- DROP DATABASE / CREATE DATABASE recycle inherits them without re-running
-- this script (spec-037 requires PostGIS, pgvector, uuid-ossp).

\connect template1
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- The entrypoint created POSTGRES_DB=babylon_test *before* this script and
-- template1 changes don't apply retroactively — equip it directly too.
\connect babylon_test
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- FR-005: async commit for the sim/test role ONLY (not cluster-wide).
-- Safe: per-tick writes are idempotent (ON CONFLICT DO NOTHING, spec-056)
-- and crash-resume replays deterministically from the last committed tick
-- (Constitution III.7) — a lost async tail is re-created bit-exact.
ALTER ROLE test SET synchronous_commit = off;
