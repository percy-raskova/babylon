-- 0026_partition_dynamic_tables.sql
-- Spec 088 — Storage program sprint 2 (S2a, FR-001/FR-002/FR-003/FR-004).
--
-- Converts the 8 per-tick table families to PARTITION BY LIST (session_id)
-- so a finished session purges via instant DROP PARTITION (zero dead
-- tuples, no VACUUM debt) instead of a ~25M-row DELETE.
--
-- Idempotency contract (the runner re-applies every migration at every
-- start): tables already partitioned are skipped entirely. On the one
-- converting pass, existing rows are preserved by copying them into the
-- DEFAULT partition. Views bind to table OIDs, so the converting pass
-- drops the 5 dependent views; 0028_views_current.sql (the canonical view
-- file, always executed later in the same pass) recreates them.
--
-- Per-session partitions are created at initialize_session by
-- babylon.persistence.partitioning.ensure_session_partitions; the DEFAULT
-- partition catches writers that skip session init (test harnesses).

DO $partition_conversion$
DECLARE
    tbl TEXT;
    backup TEXT;
    tables TEXT[] := ARRAY[
        'dynamic_hex_state',
        'dynamic_external_node_state',
        'boundary_flow_register',
        'conservation_audit_log',
        'dynamic_consciousness_state',
        'dynamic_demographics_state',
        'dynamic_employment_state',
        'dynamic_relationship_state'
    ];
    -- Families whose original migrations enforce append-only semantics.
    append_only TEXT[] := ARRAY[
        'boundary_flow_register',
        'conservation_audit_log',
        'dynamic_consciousness_state',
        'dynamic_demographics_state',
        'dynamic_employment_state',
        'dynamic_relationship_state'
    ];
    needs_conversion BOOLEAN := FALSE;
BEGIN
    -- Detect whether this pass converts anything (steady-state fast path).
    FOREACH tbl IN ARRAY tables LOOP
        IF to_regclass(tbl) IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM pg_partitioned_table pt
            JOIN pg_class c ON c.oid = pt.partrelid
            WHERE c.relname = tbl
        ) THEN
            needs_conversion := TRUE;
        END IF;
    END LOOP;

    IF NOT needs_conversion THEN
        RETURN;
    END IF;

    -- Views bind to OIDs; they would chase the RENAME below and then block
    -- DROP of the backup table. 0028 recreates them later this pass.
    DROP VIEW IF EXISTS view_runtime_trace_emission;
    DROP VIEW IF EXISTS v_global_phi_balance;
    DROP VIEW IF EXISTS v_national_value_aggregate;
    DROP VIEW IF EXISTS v_state_value_aggregate;
    DROP VIEW IF EXISTS v_county_value_aggregate;

    FOREACH tbl IN ARRAY tables LOOP
        CONTINUE WHEN to_regclass(tbl) IS NULL;
        CONTINUE WHEN EXISTS (
            SELECT 1 FROM pg_partitioned_table pt
            JOIN pg_class c ON c.oid = pt.partrelid
            WHERE c.relname = tbl
        );

        backup := tbl || '_flat_backup';
        EXECUTE format('ALTER TABLE %I RENAME TO %I', tbl, backup);
        -- LIKE INCLUDING ALL clones columns, CHECKs, PK + secondary
        -- indexes (as partitioned indexes). Every family's PK leads with
        -- session_id, satisfying the partition-key requirement.
        EXECUTE format(
            'CREATE TABLE %I (LIKE %I INCLUDING ALL) PARTITION BY LIST (session_id)',
            tbl, backup
        );
        EXECUTE format('CREATE TABLE %I PARTITION OF %I DEFAULT', tbl || '_default', tbl);
        EXECUTE format('INSERT INTO %I SELECT * FROM %I', tbl, backup);
        EXECUTE format('DROP TABLE %I', backup);

        IF tbl = ANY (append_only) THEN
            EXECUTE format('REVOKE UPDATE, DELETE ON %I FROM PUBLIC', tbl);
        END IF;
    END LOOP;
END
$partition_conversion$;
