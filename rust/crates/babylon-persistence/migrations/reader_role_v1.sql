-- Additive client-owned read-only reader schema; not a persistence-authority epoch.
-- The view lives in the public schema because PostgreSQL grants schema USAGE on
-- public to PUBLIC, while babylon_meta is revoked from PUBLIC. A schema-level
-- GRANT USAGE on babylon_meta would change the digest-pinned babylon_meta
-- schema-grant census row, so the view stays where the reader can already reach.
-- babylon_reader is NOLOGIN by design: a deployment provisions one confined
-- LOGIN role as a member of babylon_reader (NOSUPERUSER NOCREATEDB
-- NOCREATEROLE) and points BABYLON_READER_DSN at that credential. The reader
-- handle refuses to operate unless the session privilege census is exactly
-- SELECT on this view.
CREATE VIEW public.v_committed_tick_status_v1 AS
SELECT
    campaign_id,
    resolve_tick,
    envelope_layout_version,
    tick_content_hash,
    envelope_digest
FROM babylon_state.tick_commit;

GRANT SELECT ON public.v_committed_tick_status_v1 TO babylon_reader;

-- Defense in depth: these tables are already revoked from PUBLIC, and the role
-- inherits nothing, but pin the refusal explicitly when the Archive schema is
-- present. The guard keeps this file installable before the Archive schema.
DO $$
BEGIN
    IF pg_catalog.to_regclass('babylon_meta.archive_page_v1') IS NOT NULL THEN
        REVOKE ALL ON TABLE babylon_meta.archive_page_v1 FROM babylon_reader;
    END IF;
    IF pg_catalog.to_regclass('babylon_meta.archive_knowledge_grant_v1') IS NOT NULL THEN
        REVOKE ALL ON TABLE babylon_meta.archive_knowledge_grant_v1 FROM babylon_reader;
    END IF;
    IF pg_catalog.to_regclass('babylon_meta.archive_receipt_consumption_v1') IS NOT NULL THEN
        REVOKE ALL ON TABLE babylon_meta.archive_receipt_consumption_v1 FROM babylon_reader;
    END IF;
END
$$;
