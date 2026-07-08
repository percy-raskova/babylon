-- 0032_widen_tick_event_severity.sql
-- (renumbered from 0031 — the prefix collided with
--  0031_conservation_audit_external_scale.sql; sorted-glob order between
--  same-prefix files is a lexical accident)
-- Spec 092 review fix — Defect A (the never-done spec-061 T047).
--
-- tick_event.severity was declared VARCHAR(12) in the original spec-037
-- schema (postgres_schema.py TICK_EVENT_DDL), but the serialization
-- boundary's default severity string is "informational" (13 chars) —
-- see web/game/engine_bridge.py's `_classify_event` (spec 061 FR-012:
-- unmapped EventTypes, which is most of the ~70-member enum, fall through
-- to this default). Every real Postgres write of a tick containing an
-- unmapped-severity event raised StringDataRightTruncation (22001) and,
-- because `persist_tick_events` writes a tick's events in one batch,
-- silently rolled back ALL of that tick's tick_event rows — the Event
-- Log / Alerts dashboards (spec 092) had zero real history to read back.
-- This landmine was already documented as a known gap in
-- tests/integration/test_persist_tick_atomic.py (spec 061 T023) predicting
-- exactly this T047 widening; spec-092 is the first feature to actually
-- feed real severities through and trip it.
--
-- Widening a VARCHAR(n) to a larger VARCHAR(m) is a metadata-only change
-- in Postgres (no table rewrite, no lock beyond ACCESS EXCLUSIVE for the
-- catalog update) — safe to apply to a live table. VARCHAR(32) gives
-- generous headroom over the three canonical severity strings
-- ("critical" / "warning" / "informational") without going fully
-- unbounded (TEXT).
--
-- postgres_schema.py's TICK_EVENT_DDL is updated in the same commit so
-- fresh databases get VARCHAR(32) directly; this migration is for
-- existing databases (including the product 5432 DB) created before
-- that change.

-- Guarded: (a) tick_event is created by the spec-037 bootstrap
-- (postgres_schema.py TICK_EVENT_DDL), not by any migration, so a database
-- that only ran migrations must not hard-fail here; (b) the runner
-- re-applies every migration each start, and an unguarded ALTER takes
-- ACCESS EXCLUSIVE on tick_event every single run — skip once widened.
DO $widen_severity$
BEGIN
    IF to_regclass('tick_event') IS NOT NULL
       AND (SELECT atttypmod - 4
            FROM pg_attribute
            WHERE attrelid = to_regclass('tick_event')
              AND attname = 'severity') < 32 THEN
        ALTER TABLE tick_event ALTER COLUMN severity TYPE VARCHAR(32);
    END IF;
END
$widen_severity$;
