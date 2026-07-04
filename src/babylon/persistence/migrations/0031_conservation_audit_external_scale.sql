-- 0031_conservation_audit_external_scale.sql
-- spec-101 (Lane E, program 09) — Trade activation: boundary flows live.
--
-- FR-101-5 records the `imperial_rent_phi_week_distribution` conservation
-- invariant with ONE audit row per external bloc, using
-- scale = 'external:<node_id>' (e.g. 'external:canada') to differentiate blocs
-- within the shared (session_id, tick, scale, invariant_name) primary key. The
-- original scale CHECK (migration 0014) enumerated only the internal
-- aggregation scales (hex/county/state/national/global_phi/per_stage), so
-- persist_tick_atomic raised conservation_audit_log_scale_check on the first
-- wired tick. This migration extends the CHECK to admit the external-node
-- boundary scale namespace.
--
-- Idempotency + concurrency: the DROP/ADD (which takes ACCESS EXCLUSIVE on the
-- partitioned parent + all partitions) runs ONLY when the constraint does not
-- yet permit 'external:%'. On every subsequent migration pass the guard finds
-- the extended definition and skips the ALTER entirely — so a repeated sim
-- launch against a shared, concurrently-accessed babylon_test does NOT re-lock
-- the table (avoids deadlocks with parallel lanes). The new predicate is a
-- strict superset of the old, so existing rows validate unconditionally.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'conservation_audit_log_scale_check'
          AND pg_get_constraintdef(oid) LIKE '%external:%'
    ) THEN
        ALTER TABLE conservation_audit_log
            DROP CONSTRAINT IF EXISTS conservation_audit_log_scale_check;
        ALTER TABLE conservation_audit_log
            ADD CONSTRAINT conservation_audit_log_scale_check
            CHECK (
                scale IN ('hex', 'county', 'state', 'national', 'global_phi', 'per_stage')
                OR scale LIKE 'external:%'
            );
    END IF;
END $$;
