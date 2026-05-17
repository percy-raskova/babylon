-- ============================================================================
-- spec-067 — QCEW Ownership and NAICS Hierarchy Normalization
--
-- This is the canonical SQL contract for the migration. The executable
-- form in tools/normalize_qcew_rollups.py wraps these statements in a
-- backup/transaction/audit-report harness, but the SQL itself is authoritative.
--
-- Per Constitution II.11 (Subsystem Table Ownership), all DELETE
-- statements target tables owned by the reference-data subsystem
-- (src/babylon/reference/) and run inside that subsystem's
-- SQLAlchemy session.
--
-- Per Constitution III.7 (Determinism Hash and Replayability), the
-- migration is idempotent: re-running this script after a successful
-- first run produces zero affected rows.
--
-- Per Constitution III.8 (Aleksandrov Test), the predicate values
-- (naics_level = 6 for canonical NAICS detail; own_code = '0' for the
-- BLS Total-covered rollup) trace to the BLS QCEW publication
-- specification, not to arbitrary constants (Constitution III.1).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Step 0: Pre-flight assertions (run as SELECTs, not DDL).
-- ----------------------------------------------------------------------------

-- A0: dim_industry MUST have at least one row at every naics_level 0..6,
--     else the predicate is operating against an empty population.
SELECT
    naics_level,
    COUNT(*) AS industries_at_level
FROM dim_industry
GROUP BY naics_level
ORDER BY naics_level;

-- A1: dim_ownership MUST have exactly one row with own_code = '0' (the rollup).
SELECT COUNT(*) AS total_covered_rows
FROM dim_ownership
WHERE own_code = '0';
-- expected: 1

-- A2: dim_ownership MUST have exactly four rows with own_code IN ('1','2','3','5').
SELECT COUNT(*) AS canonical_ownership_rows
FROM dim_ownership
WHERE own_code IN ('1', '2', '3', '5');
-- expected: 4

-- A3: Row count pre-migration (capture for audit report).
SELECT COUNT(*) AS fact_qcew_annual_pre FROM fact_qcew_annual;

-- ----------------------------------------------------------------------------
-- Step 1: Create backup table for recovery.
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fact_qcew_annual__pre_067 AS
SELECT * FROM fact_qcew_annual;

-- ----------------------------------------------------------------------------
-- Step 2: Capture row counts by rollup class (for audit report and integrity check).
-- ----------------------------------------------------------------------------

-- Count rows on the NAICS axis only (industry is rollup, ownership is canonical).
SELECT COUNT(*) AS naics_only_excluded
FROM fact_qcew_annual fq
JOIN dim_industry i ON fq.industry_id = i.industry_id
JOIN dim_ownership o ON fq.ownership_id = o.ownership_id
WHERE i.naics_level != 6 AND o.own_code != '0';

-- Count rows on the ownership axis only (industry is canonical, ownership is rollup).
SELECT COUNT(*) AS ownership_only_excluded
FROM fact_qcew_annual fq
JOIN dim_industry i ON fq.industry_id = i.industry_id
JOIN dim_ownership o ON fq.ownership_id = o.ownership_id
WHERE i.naics_level = 6 AND o.own_code = '0';

-- Count rows on both axes (rollup industry AND rollup ownership).
SELECT COUNT(*) AS both_axes_excluded
FROM fact_qcew_annual fq
JOIN dim_industry i ON fq.industry_id = i.industry_id
JOIN dim_ownership o ON fq.ownership_id = o.ownership_id
WHERE i.naics_level != 6 AND o.own_code = '0';

-- Count rows that are canonical on BOTH axes (these SURVIVE post-migration).
SELECT COUNT(*) AS canonical_rows
FROM fact_qcew_annual fq
JOIN dim_industry i ON fq.industry_id = i.industry_id
JOIN dim_ownership o ON fq.ownership_id = o.ownership_id
WHERE i.naics_level = 6 AND o.own_code != '0';

-- ----------------------------------------------------------------------------
-- Step 3: Atomic delete of rollup rows.
-- ----------------------------------------------------------------------------

BEGIN TRANSACTION;

-- 3a: Drop NAICS-hierarchy rollups (preserves only naics_level = 6 rows).
DELETE FROM fact_qcew_annual
WHERE industry_id IN (
    SELECT industry_id FROM dim_industry WHERE naics_level != 6
);

-- 3b: Drop the Total-covered ownership rollup (preserves Federal/State/Local/Private).
DELETE FROM fact_qcew_annual
WHERE ownership_id IN (
    SELECT ownership_id FROM dim_ownership WHERE own_code = '0'
);

-- 3c: Post-migration row count (capture for audit report).
SELECT COUNT(*) AS fact_qcew_annual_post FROM fact_qcew_annual;

-- 3d: Integrity assertion. Executed in application code; iff it FAILS the
--     application performs ROLLBACK rather than COMMIT.
--
-- Required identity (asserted in Python):
--   fact_qcew_annual_pre - fact_qcew_annual_post == naics_only_excluded
--                                                 + ownership_only_excluded
--                                                 + both_axes_excluded

-- 3e: COMMIT iff the integrity assertion above passed. Else ROLLBACK and abort.
COMMIT;

-- ----------------------------------------------------------------------------
-- Step 4: Post-migration validation (run as SELECTs after COMMIT).
-- ----------------------------------------------------------------------------

-- B0: Every surviving row MUST satisfy the canonical predicate (no rollups left).
SELECT COUNT(*) AS canonical_violation_count
FROM fact_qcew_annual fq
JOIN dim_industry i ON fq.industry_id = i.industry_id
JOIN dim_ownership o ON fq.ownership_id = o.ownership_id
WHERE NOT (i.naics_level = 6 AND o.own_code != '0');
-- expected: 0

-- B1: Wayne County 2010 BLS-agreement check (SC-001).
--     Uses dim_county.fips (the actual 5-digit FIPS column; the schema uses
--     `fips` for the 5-digit code and `county_fips` for the 3-digit county
--     portion — verified by T001 pre-flight 2026-05-16).
SELECT SUM(fq.employment) AS wayne_2010_employment_sum
FROM fact_qcew_annual fq
JOIN dim_county c ON fq.county_id = c.county_id
JOIN dim_time t ON fq.time_id = t.time_id
WHERE c.fips = '26163' AND t.year = 2010;
-- expected: ~660,000 ± 5%  (BLS-published Wayne County 2010 private + government employment)

-- ----------------------------------------------------------------------------
-- Step 5: Optional cleanup (operator-invoked, NOT part of the migration commit).
-- ----------------------------------------------------------------------------

-- After qa:e2e-regression passes against the regenerated michigan-e2e baseline,
-- the operator may drop the backup table to reclaim ~3 GB of disk:
--
--   DROP TABLE fact_qcew_annual__pre_067;
--   VACUUM;
--
-- Until then, the backup remains as the rollback surface.

-- ============================================================================
-- End of spec-067 migration contract.
-- ============================================================================
