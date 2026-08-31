//! Live `PostgreSQL` proof for the frozen legacy H3 shadow-key backfill.

use super::{
    assert_lock_released, database_user, h3_reference_installer_postgres, legacy_epoch_fixture,
    ScratchDatabase,
};
use babylon_kernel::H3CellId;
use babylon_persistence::{
    adopt_legacy_schema, backfill_legacy_h3_shadow_keys, compiled_schema_migrations,
    migrate_schema_epoch, H3ReferenceInstallDisposition, H3ShadowBackfillDisposition,
    H3ShadowBackfillError, H3ShadowBackfillIssueKind, H3ShadowBackfillReport, H3ShadowFieldReport,
    H3ShadowRelation, H3ShadowRelationReport, SchemaEpochError, SchemaEpochOrigin,
    H3_SHADOW_FIELD_COUNT, H3_SHADOW_RELATION_COUNT, MAX_H3_SHADOW_BACKFILL_BATCH_ROWS,
    MAX_H3_SHADOW_TEXT_BYTES,
};
use postgres::{Config, IsolationLevel, NoTls};
use uuid::Uuid;

const SESSION_ID: &str = "27900000-0000-0000-0000-000000000003";
const PARITY_SESSION_ID: &str = "27900000-0000-0000-0000-000000000001";
const PARITY_OTHER_SESSION_ID: &str = "27900000-0000-0000-0000-000000000002";
const PARITY_CELL_A: i64 = 608_661_359_088_893_951;
const PARITY_CELL_B: i64 = 608_661_359_105_671_167;
const PARITY_CELL_C: i64 = 608_661_359_122_448_383;
const PARITY_CELL_D: i64 = 613_164_958_701_584_383;
const BACKEND_TERMINATION_TIMEOUT_MILLIS: i64 = 5_000;
const MULTI_BATCH_HEX_ACTIVITY_ROWS: usize = MAX_H3_SHADOW_BACKFILL_BATCH_ROWS + 1;

pub(super) fn verify_h3_shadow_backfill(base: &Config, legacy_template: &str) {
    verify_fresh_origin_is_an_exact_noop(base);
    verify_invalid_late_relation_refuses_before_any_mutation(base, legacy_template);
    verify_coarse_child_resolution_refuses_before_ancestry(base, legacy_template);
    verify_oversized_text_refuses_with_bounded_evidence(base, legacy_template);
    verify_all_governed_fields_backfill_once_and_retry_exactly(base, legacy_template);
}

fn verify_fresh_origin_is_an_exact_noop(base: &Config) {
    let database = ScratchDatabase::empty(base, "h3_shadow_fresh", database_user(base));
    let config = database.config(base);
    establish_v6_prefix(&config);

    let report = backfill_legacy_h3_shadow_keys(&config)
        .expect("fresh exact epoch must be an explicit no-legacy-estate success");
    assert_eq!(
        report.disposition,
        H3ShadowBackfillDisposition::NoLegacyEstate
    );
    assert!(report.fields.is_empty());
    assert!(report.relations.is_empty());
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_invalid_late_relation_refuses_before_any_mutation(base: &Config, template: &str) {
    let (database, config) = exact_legacy_database(base, template, "h3_shadow_refusal");
    let cell = representative_r7(&config);
    let session = session_id();
    let mut client = config.connect(NoTls).unwrap();
    insert_game_session(&mut client, session);
    client
        .execute(
            "INSERT INTO public.hex_activity (game_id, tick, h3_index) VALUES ($1, 0, $2)",
            &[&session, &cell.text],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.org_snapshot \
             (game_id, tick, org_id, org_type, home_hex, attributes) \
             VALUES ($1, 0, 'invalid-org', 'business', 'not-an-h3', '{}'::jsonb)",
            &[&session],
        )
        .unwrap();
    drop(client);

    match backfill_legacy_h3_shadow_keys(&config) {
        Err(H3ShadowBackfillError::Refused {
            issue_count,
            evidence,
        }) => {
            assert!(issue_count >= 1);
            assert!(evidence.iter().any(|issue| {
                issue.relation == H3ShadowRelation::OrgSnapshot
                    && matches!(issue.kind, H3ShadowBackfillIssueKind::InvalidText(_))
            }));
        }
        other => panic!("malformed late relation must refuse the whole estate: {other:?}"),
    }
    let mut client = config.connect(NoTls).unwrap();
    let unchanged: (i64, i64) = client
        .query_one(
            "SELECT \
                 (SELECT pg_catalog.count(*) FROM public.hex_activity WHERE cell_id IS NULL), \
                 (SELECT pg_catalog.count(*) FROM public.org_snapshot WHERE home_cell_id IS NULL)",
            &[],
        )
        .map(|row| (row.get(0), row.get(1)))
        .unwrap();
    assert_eq!(unchanged, (1, 1));
    drop(client);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_coarse_child_resolution_refuses_before_ancestry(base: &Config, template: &str) {
    let (database, config) = exact_legacy_database(base, template, "h3_shadow_coarse_child");
    let cell = representative_r7(&config);
    let coarse_child = config
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT cell_id FROM babylon_ref.h3_cell WHERE resolution = 4 ORDER BY cell_id LIMIT 1",
            &[],
        )
        .map(|row| {
            H3CellId::try_from(row.get::<_, i64>(0))
                .unwrap()
                .to_string()
        })
        .unwrap();
    let session = session_id();
    let mut client = config.connect(NoTls).unwrap();
    insert_game_session(&mut client, session);
    client
        .execute(
            "INSERT INTO public.hex_cell \
             (h3_index, county_fips, state_fips, res6_parent, res5_parent, geometry, centroid) \
             VALUES ($1, '26163', '26', $2, $3, \
                     ST_GeomFromText('POLYGON((0 0,0 1,1 1,1 0,0 0))', 4326), \
                     ST_GeomFromText('POINT(0.5 0.5)', 4326))",
            &[
                &coarse_child,
                &cell.ancestor_r6_text,
                &cell.ancestor_r5_text,
            ],
        )
        .unwrap();
    drop(client);

    match backfill_legacy_h3_shadow_keys(&config) {
        Err(H3ShadowBackfillError::Refused { evidence, .. }) => {
            assert!(evidence.iter().any(|issue| {
                issue.relation == H3ShadowRelation::HexCell
                    && issue.legacy_column == "h3_index"
                    && matches!(
                        issue.kind,
                        H3ShadowBackfillIssueKind::UnexpectedResolution {
                            expected: 7,
                            actual: 4
                        }
                    )
            }));
        }
        other => panic!("coarse child resolution must refuse without panic: {other:?}"),
    }
    let shadow_count: i64 = config
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT pg_catalog.count(*) FROM public.hex_cell WHERE cell_id IS NOT NULL",
            &[],
        )
        .unwrap()
        .get(0);
    assert_eq!(shadow_count, 0);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_oversized_text_refuses_with_bounded_evidence(base: &Config, template: &str) {
    let (database, config) = exact_legacy_database(base, template, "h3_shadow_text_bound");
    let session = session_id();
    let mut client = config.connect(NoTls).unwrap();
    insert_game_session(&mut client, session);
    let oversized_bytes = i32::try_from(MAX_H3_SHADOW_TEXT_BYTES + 1).unwrap();
    client
        .execute(
            "INSERT INTO public.immutable_reference_lodes_od_matrix \
             (session_id, year, home_hex, workplace_dest, workplace_dest_kind, s000_workers) \
             VALUES ($1, 2026, pg_catalog.repeat('x', $2), 'canada', 'external', 1)",
            &[&session, &oversized_bytes],
        )
        .unwrap();
    drop(client);

    match backfill_legacy_h3_shadow_keys(&config) {
        Err(H3ShadowBackfillError::Refused { evidence, .. }) => {
            let issue = evidence
                .iter()
                .find(|issue| {
                    issue.relation == H3ShadowRelation::ImmutableReferenceLodesOdMatrix
                        && issue.legacy_column == "home_hex"
                        && matches!(issue.kind, H3ShadowBackfillIssueKind::TextTooLong { .. })
                })
                .expect("oversized legacy text must produce bounded typed evidence");
            assert_eq!(
                issue.kind,
                H3ShadowBackfillIssueKind::TextTooLong {
                    actual: u64::try_from(oversized_bytes).unwrap(),
                    max: u64::try_from(MAX_H3_SHADOW_TEXT_BYTES).unwrap(),
                }
            );
            assert!(
                issue.legacy_value.as_ref().unwrap().len()
                    <= "hex:".len() + MAX_H3_SHADOW_TEXT_BYTES * 2
            );
        }
        other => panic!("oversized legacy H3 text must refuse with bounded evidence: {other:?}"),
    }
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_all_governed_fields_backfill_once_and_retry_exactly(base: &Config, template: &str) {
    let (database, config) = exact_legacy_database(base, template, "h3_shadow_green");
    let cohort = h3_reference_installer_postgres::representative_cohort();
    let install_retry = h3_reference_installer_postgres::install_reference_bundle(&config, &cohort)
        .expect("the installed canonical H3 cohort must be idempotent");
    assert_eq!(
        install_retry.disposition(),
        H3ReferenceInstallDisposition::AlreadyPresent
    );
    let cell = representative_r7(&config);
    insert_governed_rows(&config, &cell);
    verify_backend_crash_rolls_back_shadow_write(base, &config, &cell);
    let legacy_before = legacy_value_snapshot(&config);

    let report = backfill_legacy_h3_shadow_keys(&config)
        .expect("valid frozen legacy H3 values must backfill to canonical identity");
    assert_eq!(report.disposition, H3ShadowBackfillDisposition::Backfilled);
    assert_eq!(report.fields.len(), H3_SHADOW_FIELD_COUNT);
    assert_eq!(report.relations.len(), H3_SHADOW_RELATION_COUNT);
    assert_eq!(legacy_value_snapshot(&config), legacy_before);

    assert_field_coverage(&report.fields);
    assert_relation_coverage(&report.relations);
    assert_exact_shadow_values(&config, &cell);

    let retry = backfill_legacy_h3_shadow_keys(&config)
        .expect("the exact completed H3 shadow estate must be idempotent");
    assert_retry_receipt(&report, &retry);
    assert_eq!(legacy_value_snapshot(&config), legacy_before);

    let cutover = migrate_schema_epoch(&config)
        .expect("the fully backfilled legacy estate must advance from epoch 6 to epoch 7");
    assert_eq!(cutover.origin, SchemaEpochOrigin::ExistingRustPrefix);
    assert_eq!((cutover.prior_applied, cutover.final_applied), (6, 7));
    assert_eq!(cutover.applied_versions.len(), 1);
    assert_eq!(cutover.applied_versions[0].as_i64(), 7);
    let exact_epoch = epoch_seven_reader_snapshot(&config);
    let cutover_retry = migrate_schema_epoch(&config)
        .expect("the complete epoch-7 reader cutover must be idempotent");
    assert_eq!(
        (cutover_retry.prior_applied, cutover_retry.final_applied),
        (7, 7)
    );
    assert!(cutover_retry.applied_versions.is_empty());
    assert!(cutover_retry.reconciled_versions.is_empty());
    assert_eq!(epoch_seven_reader_snapshot(&config), exact_epoch);
    assert_eq!(
        backfill_legacy_h3_shadow_keys(&config),
        Err(H3ShadowBackfillError::ExactSchemaEpochRequired {
            expected: 6,
            actual: 7,
            origin: SchemaEpochOrigin::ExistingRustPrefix,
        })
    );
    verify_epoch_seven_view_definition_mutation_refuses(base, database.name());
    verify_epoch_seven_cell_id_mutation_refuses(base, database.name());
    verify_epoch_seven_acl_mutation_refuses(base, database.name());
    verify_epoch_seven_reader_parity_v1(&config);
    assert_lock_released(&config);
    database.cleanup();
}

fn verify_epoch_seven_reader_parity_v1(config: &Config) {
    install_epoch_seven_reader_parity_fixture(config);
    let before = epoch_seven_reader_parity_snapshot(config);
    legacy_epoch_fixture::execute_h3_reader_parity_v1(config);
    assert_eq!(
        epoch_seven_reader_parity_snapshot(config),
        before,
        "the read-only parity executor must not publish game-state writes"
    );
}

#[allow(
    clippy::too_many_lines,
    reason = "one live fixture transaction installs the exact cross-view parity witness"
)]
fn install_epoch_seven_reader_parity_fixture(config: &Config) {
    let session = Uuid::parse_str(PARITY_SESSION_ID).unwrap();
    let other_session = Uuid::parse_str(PARITY_OTHER_SESSION_ID).unwrap();
    let mut client = config.connect(NoTls).unwrap();
    let reference_count: i64 = client
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_ref.h3_cell \
             WHERE cell_id IN ($1, $2, $3, $4)",
            &[
                &PARITY_CELL_A,
                &PARITY_CELL_B,
                &PARITY_CELL_C,
                &PARITY_CELL_D,
            ],
        )
        .unwrap()
        .get(0);
    assert_eq!(
        reference_count, 4,
        "the sole canonical Michigan H3 bundle must own every parity identity"
    );
    let other_session_rows: i64 = client
        .query_one(
            "SELECT pg_catalog.count(*) FROM public.dynamic_hex_state WHERE session_id = $1",
            &[&other_session],
        )
        .unwrap()
        .get(0);
    assert_eq!(other_session_rows, 0);

    let mut transaction = client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.game_session (id, scenario) VALUES ($1, 'per280-reader-parity')",
            &[&session],
        )
        .unwrap();
    transaction
        .batch_execute(
            "CREATE TABLE public.dynamic_hex_state_p_27900000000000000000000000000001 \
             PARTITION OF public.dynamic_hex_state \
             FOR VALUES IN ('27900000-0000-0000-0000-000000000001')",
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.dynamic_hex_state \
             (session_id, tick, h3_index, county_fips, state_fips, region_id, \
              c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock, \
              internet_access_pct, surveillance_coupling, cell_id) \
             VALUES \
             ($1, 0, '872a10728ffffff', '26163', '26', 'mi', \
              1, 1, 2, 0, 0, 0, 0, 0, 0, $2), \
             ($1, 2, '870800000ffffff', '26163', '26', 'mi', \
              2, 0, 0, 0, 0, 0, 0, 0, 0, $3)",
            &[&session, &PARITY_CELL_A, &PARITY_CELL_B],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.hex_spatial_map \
             (session_id, h3_index, county_fips, state_fips, region_id, cell_id) \
             VALUES \
             ($1, '872a10728ffffff', '26163', '26', 'mi', $2), \
             ($1, '870800000ffffff', '26163', '26', 'mi', $3)",
            &[&session, &PARITY_CELL_A, &PARITY_CELL_B],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.hex_latest \
             (game_id, h3_index, tick, county_fips, county_name, state_fips, \
              center_lat, center_lng, heat, cell_id) \
             VALUES ($1, '872a10728ffffff', 2, '26163', 'Wayne', '26', \
                     42.3, -83.0, 1, $2)",
            &[&session, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.hex_map \
             (game_id, h3_index, county_fips, county_name, state_fips, \
              center_lat, center_lng, cell_id) \
             VALUES \
             ($1, '870800000ffffff', '26163', 'Wayne', '26', 42.3, -83.0, $2), \
             ($1, '871c00000ffffff', '26163', 'Wayne', '26', 42.3, -83.0, $3), \
             ($1, '872a10728ffffff', '26163', 'Wayne', '26', 42.3, -83.0, $4)",
            &[&session, &PARITY_CELL_B, &PARITY_CELL_C, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.hex_cell \
             (h3_index, county_fips, county_name, state_fips, res6_parent, res5_parent, \
              geometry, centroid, cell_id, ancestor_r5, ancestor_r6) \
             SELECT pg_catalog.to_hex(cell_id), '26163', 'Wayne', '26', \
                    pg_catalog.to_hex(ancestor_r6), pg_catalog.to_hex(ancestor_r5), \
                    ST_GeomFromText('POLYGON((0 0,0 1,1 1,1 0,0 0))', 4326), \
                    ST_GeomFromText('POINT(0.5 0.5)', 4326), \
                    cell_id, ancestor_r5, ancestor_r6 \
             FROM babylon_ref.h3_cell \
             WHERE cell_id IN ($1, $2, $3) \
             ON CONFLICT (h3_index) DO NOTHING",
            &[&PARITY_CELL_A, &PARITY_CELL_B, &PARITY_CELL_C],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.hex_r8_reference \
             (h3_index, parent_h3, county_fips, cell_id, parent_cell_id) \
             VALUES ('882a107289fffff', '872a10728ffffff', '26163', $1, $2)",
            &[&PARITY_CELL_D, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.org_snapshot \
             (game_id, tick, org_id, org_type, home_hex, attributes, home_cell_id) \
             VALUES \
             ($1, 0, 'mapped-org', 'business', '872a10728ffffff', '{}'::jsonb, $2), \
             ($1, 0, 'unplaced-org', 'business', NULL, '{}'::jsonb, NULL)",
            &[&session, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.tick_event \
             (game_id, tick, event_type, h3_index, summary, cell_id) \
             VALUES \
             ($1, 0, 'mapped', '872a10728ffffff', 'mapped', $2), \
             ($1, 0, 'unplaced', NULL, 'unplaced', NULL)",
            &[&session, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.immutable_reference_lodes_od_matrix \
             (session_id, year, home_hex, workplace_dest, workplace_dest_kind, \
              s000_workers, home_cell_id, workplace_cell_id) \
             VALUES \
             ($1, 2026, '872a10728ffffff', '872a10728ffffff', 'hex', 1, $2, $2), \
             ($1, 2026, '872a10728ffffff', 'canada', 'external', 1, $2, NULL)",
            &[&session, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.hex_state \
             (session_id, tick, h3_index, cell_id) \
             VALUES ($1, 0, '872a10728ffffff', $2)",
            &[&session, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.hex_terrain_state \
             (session_id, tick, h3_index, cell_id) \
             VALUES ($1, 0, '872a10728ffffff', $2)",
            &[&session, &PARITY_CELL_A],
        )
        .unwrap();
    transaction
        .execute(
            "INSERT INTO public.infrastructure_link_state \
             (session_id, tick, source_h3, target_h3, link_id, infra_type, \
              source_cell_id, target_cell_id) \
             VALUES ($1, 0, '872a10728ffffff', '870800000ffffff', \
                     'per280-parity-link', 'power', $2, $3)",
            &[&session, &PARITY_CELL_A, &PARITY_CELL_B],
        )
        .unwrap();
    transaction.commit().unwrap();
}

fn epoch_seven_reader_parity_snapshot(config: &Config) -> Vec<(String, String)> {
    let session = Uuid::parse_str(PARITY_SESSION_ID).unwrap();
    let rows = config
        .connect(NoTls)
        .unwrap()
        .query(
            "SELECT relation_name, payload FROM ( \
                 SELECT 'dynamic_hex_state'::text AS relation_name, \
                        pg_catalog.row_to_json(projected)::text AS payload \
                 FROM (SELECT session_id, tick, cell_id, c, v, s \
                       FROM public.dynamic_hex_state WHERE session_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'hex_spatial_map', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT session_id, cell_id, county_fips, state_fips, region_id \
                       FROM public.hex_spatial_map WHERE session_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'hex_latest', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT game_id, tick, cell_id, heat \
                       FROM public.hex_latest WHERE game_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'hex_map', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT game_id, cell_id FROM public.hex_map WHERE game_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'org_snapshot', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT game_id, org_id, home_cell_id \
                       FROM public.org_snapshot WHERE game_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'tick_event', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT game_id, event_type, cell_id \
                       FROM public.tick_event WHERE game_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'immutable_reference_lodes_od_matrix', \
                        pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT session_id, year, home_cell_id, workplace_dest_kind, \
                              workplace_dest, workplace_cell_id, s000_workers \
                       FROM public.immutable_reference_lodes_od_matrix \
                       WHERE session_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'hex_state', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT session_id, tick, cell_id \
                       FROM public.hex_state WHERE session_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'hex_terrain_state', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT session_id, tick, cell_id \
                       FROM public.hex_terrain_state WHERE session_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'infrastructure_link_state', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT session_id, tick, source_cell_id, target_cell_id \
                       FROM public.infrastructure_link_state WHERE session_id = $1) AS projected \
                 UNION ALL \
                 SELECT 'hex_r8_reference', pg_catalog.row_to_json(projected)::text \
                 FROM (SELECT cell_id, parent_cell_id FROM public.hex_r8_reference \
                       WHERE cell_id = $2) AS projected \
             ) AS parity_rows \
             ORDER BY relation_name COLLATE \"C\", payload COLLATE \"C\"",
            &[&session, &PARITY_CELL_D],
        )
        .unwrap();
    rows.iter().map(|row| (row.get(0), row.get(1))).collect()
}

fn verify_epoch_seven_view_definition_mutation_refuses(base: &Config, template: &str) {
    verify_epoch_seven_mutation_refusal(
        base,
        template,
        "h3_reader_view_definition",
        "CREATE OR REPLACE VIEW public.v_hex_heat AS \
         SELECT game_id, tick, cell_id, center_lat, center_lng, \
                heat AS heat_total, heat_delta, org_count, was_target \
         FROM public.hex_latest WHERE heat >= 0",
        SchemaEpochError::EpochCensusMismatch,
    );
}

fn verify_epoch_seven_cell_id_mutation_refuses(base: &Config, template: &str) {
    verify_epoch_seven_mutation_refusal(
        base,
        template,
        "h3_reader_cell_id",
        "ALTER VIEW public.v_hex_heat RENAME COLUMN cell_id TO h3_index",
        SchemaEpochError::EpochShapeMismatch,
    );
}

fn verify_epoch_seven_acl_mutation_refuses(base: &Config, template: &str) {
    verify_epoch_seven_mutation_refusal(
        base,
        template,
        "h3_reader_acl",
        "REVOKE SELECT ON public.v_hex_state_asof FROM PUBLIC",
        SchemaEpochError::EpochCensusMismatch,
    );
}

fn verify_epoch_seven_mutation_refusal(
    base: &Config,
    template: &str,
    label: &str,
    mutation: &str,
    expected: SchemaEpochError,
) {
    let database = ScratchDatabase::from_template(base, template, label);
    let config = database.config(base);
    let exact = epoch_seven_reader_snapshot(&config);
    config
        .connect(NoTls)
        .unwrap()
        .batch_execute(mutation)
        .unwrap();
    let mutated = epoch_seven_reader_snapshot(&config);
    assert_ne!(
        mutated, exact,
        "mutation must change the governed reader state"
    );
    assert_eq!(migrate_schema_epoch(&config), Err(expected));
    assert_eq!(
        epoch_seven_reader_snapshot(&config),
        mutated,
        "epoch refusal must not repair or rewrite the mutation"
    );
    assert_lock_released(&config);
    database.cleanup();
}

fn epoch_seven_reader_snapshot(config: &Config) -> (Vec<(i64, Vec<u8>)>, String, String, String) {
    let mut client = config.connect(NoTls).unwrap();
    let ledger = client
        .query(
            "SELECT version, checksum FROM babylon_state.schema_migration ORDER BY version",
            &[],
        )
        .unwrap()
        .iter()
        .map(|row| (row.get(0), row.get(1)))
        .collect::<Vec<_>>();
    let row = client
        .query_one(
            "SELECT pg_catalog.pg_get_viewdef('public.v_hex_heat'::pg_catalog.regclass, true), \
                    (SELECT pg_catalog.string_agg( \
                         attribute.attname || ':' || pg_catalog.format_type( \
                             attribute.atttypid, attribute.atttypmod \
                         ), ',' ORDER BY attribute.attnum \
                     ) \
                     FROM pg_catalog.pg_attribute AS attribute \
                     WHERE attribute.attrelid = \
                           'public.v_hex_heat'::pg_catalog.regclass \
                       AND attribute.attnum > 0 \
                       AND NOT attribute.attisdropped), \
                    (SELECT COALESCE(relation.relacl::pg_catalog.text, '') \
                     FROM pg_catalog.pg_class AS relation \
                     WHERE relation.oid = \
                           'public.v_hex_state_asof'::pg_catalog.regclass)",
            &[],
        )
        .unwrap();
    (ledger, row.get(0), row.get(1), row.get(2))
}

fn assert_field_coverage(fields: &[H3ShadowFieldReport]) {
    for field in fields {
        let intentionally_empty_r8 = matches!(
            field.relation,
            H3ShadowRelation::HexR8LinearFeaturesReference
                | H3ShadowRelation::HexR8Reference
                | H3ShadowRelation::HexSubstrate
        );
        if intentionally_empty_r8 {
            assert_eq!((field.row_count, field.source_value_count), (0, 0));
        } else {
            assert!(field.row_count > 0);
            assert_eq!(field.source_value_count, field.mapped_value_count);
        }
    }
    let workplace = fields
        .iter()
        .find(|field| {
            field.relation == H3ShadowRelation::ImmutableReferenceLodesOdMatrix
                && field.legacy_column == "workplace_dest"
        })
        .unwrap();
    assert_eq!(
        (
            workplace.row_count,
            workplace.source_value_count,
            workplace.mapped_value_count,
            workplace.preserved_null_or_external_count,
        ),
        (2, 1, 1, 1)
    );
}

fn assert_relation_coverage(relations: &[H3ShadowRelationReport]) {
    for relation in relations {
        let intentionally_empty_r8 = matches!(
            relation.relation,
            H3ShadowRelation::HexR8LinearFeaturesReference
                | H3ShadowRelation::HexR8Reference
                | H3ShadowRelation::HexSubstrate
        );
        if intentionally_empty_r8 {
            assert_eq!(
                (
                    relation.row_count,
                    relation.distinct_semantic_group_count,
                    relation.rows_backfilled,
                ),
                (0, 0, 0)
            );
        } else {
            assert!(relation.row_count > 0);
            assert!(relation.distinct_semantic_group_count > 0);
            assert!(relation.rows_backfilled > 0);
        }
        assert_ne!(relation.ordered_semantic_hash, [0; 32]);
    }
    let activity = relations
        .iter()
        .find(|relation| relation.relation == H3ShadowRelation::HexActivity)
        .unwrap();
    assert_eq!(
        (
            activity.row_count,
            activity.rows_backfilled,
            activity.batches_committed,
        ),
        (
            u64::try_from(MULTI_BATCH_HEX_ACTIVITY_ROWS).unwrap(),
            u64::try_from(MULTI_BATCH_HEX_ACTIVITY_ROWS).unwrap(),
            2,
        )
    );
}

fn assert_retry_receipt(initial: &H3ShadowBackfillReport, retry: &H3ShadowBackfillReport) {
    assert_eq!(
        retry.disposition,
        H3ShadowBackfillDisposition::AlreadyComplete
    );
    assert_eq!(retry.fields, initial.fields);
    assert!(retry
        .relations
        .iter()
        .all(|relation| relation.rows_backfilled == 0 && relation.batches_committed == 0));
    for (first, retried) in initial.relations.iter().zip(&retry.relations) {
        assert_eq!(first.relation, retried.relation);
        assert_eq!(first.row_count, retried.row_count);
        assert_eq!(
            first.distinct_semantic_group_count,
            retried.distinct_semantic_group_count
        );
        assert_eq!(first.ordered_semantic_hash, retried.ordered_semantic_hash);
    }
}

fn verify_backend_crash_rolls_back_shadow_write(
    admin: &Config,
    config: &Config,
    cell: &RepresentativeCell,
) {
    let mut worker = config.connect(NoTls).unwrap();
    let backend_pid: i32 = worker
        .query_one("SELECT pg_catalog.pg_backend_pid()", &[])
        .unwrap()
        .get(0);
    let mut transaction = worker
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(false)
        .start()
        .unwrap();
    assert_eq!(
        transaction
            .execute(
                "UPDATE public.hex_activity SET cell_id = $1 WHERE cell_id IS NULL",
                &[&cell.sql],
            )
            .unwrap(),
        u64::try_from(MULTI_BATCH_HEX_ACTIVITY_ROWS).unwrap()
    );
    let terminated: bool = admin
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT pg_catalog.pg_terminate_backend($1, $2)",
            &[&backend_pid, &BACKEND_TERMINATION_TIMEOUT_MILLIS],
        )
        .unwrap()
        .get(0);
    assert!(terminated);
    assert!(transaction.commit().is_err());

    let visible_shadow_count: i64 = config
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT pg_catalog.count(*) FROM public.hex_activity WHERE cell_id IS NOT NULL",
            &[],
        )
        .unwrap()
        .get(0);
    assert_eq!(visible_shadow_count, 0);
}

fn exact_legacy_database(base: &Config, template: &str, suffix: &str) -> (ScratchDatabase, Config) {
    let database = ScratchDatabase::from_template(base, template, suffix);
    let config = database.config(base);
    adopt_legacy_schema(&config).expect("frozen legacy template must adopt exactly");
    let migration = migrate_schema_epoch(&config).expect("adopted legacy template must reach v6");
    assert_eq!(migration.final_applied, 6);
    let cohort = h3_reference_installer_postgres::representative_cohort();
    h3_reference_installer_postgres::install_reference_bundle(&config, &cohort)
        .expect("representative canonical H3 identity must install before backfill");
    (database, config)
}

fn establish_v6_prefix(config: &Config) {
    let compiled = compiled_schema_migrations().expect("compiled registry must validate");
    let mut client = config.connect(NoTls).unwrap();
    let mut transaction = client.transaction().unwrap();
    for migration in compiled.iter().take(6) {
        transaction.batch_execute(migration.sql()).unwrap();
        let version = migration.version().as_i64();
        let checksum = migration.checksum();
        let checksum_bytes = checksum.as_bytes().as_slice();
        transaction
            .execute(
                "INSERT INTO babylon_state.schema_migration (version, checksum) VALUES ($1, $2)",
                &[&version, &checksum_bytes],
            )
            .unwrap();
    }
    transaction.commit().unwrap();
}

struct RepresentativeCell {
    text: String,
    sql: i64,
    ancestor_r5_text: String,
    ancestor_r5_sql: i64,
    ancestor_r6_text: String,
    ancestor_r6_sql: i64,
}

fn representative_r7(config: &Config) -> RepresentativeCell {
    let mut client = config.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "SELECT cell_id, ancestor_r5, ancestor_r6 \
             FROM babylon_ref.h3_cell WHERE resolution = 7 \
             ORDER BY cell_id LIMIT 1",
            &[],
        )
        .unwrap();
    let sql = row.get::<_, i64>(0);
    let ancestor_r5_sql = row.get::<_, i64>(1);
    let ancestor_r6_sql = row.get::<_, i64>(2);
    RepresentativeCell {
        text: H3CellId::try_from(sql).unwrap().to_string(),
        sql,
        ancestor_r5_text: H3CellId::try_from(ancestor_r5_sql).unwrap().to_string(),
        ancestor_r5_sql,
        ancestor_r6_text: H3CellId::try_from(ancestor_r6_sql).unwrap().to_string(),
        ancestor_r6_sql,
    }
}

fn session_id() -> Uuid {
    Uuid::parse_str(SESSION_ID).unwrap()
}

fn insert_game_session(client: &mut postgres::Client, session: Uuid) {
    client
        .execute(
            "INSERT INTO public.game_session (id, scenario) VALUES ($1, 'per279')",
            &[&session],
        )
        .unwrap();
}

fn insert_governed_rows(config: &Config, cell: &RepresentativeCell) {
    let session = session_id();
    let mut client = config.connect(NoTls).unwrap();
    insert_game_session(&mut client, session);
    let r7 = &cell.text;
    let r5 = &cell.ancestor_r5_text;
    let r6 = &cell.ancestor_r6_text;
    client
        .execute(
            "INSERT INTO public.dynamic_hex_state \
         (session_id, tick, h3_index, county_fips, state_fips, region_id, \
          c, v, s, k, biocapacity_stock, energy_stock, raw_material_stock, \
          internet_access_pct, surveillance_coupling) \
         VALUES ($1, 0, $2, '26163', '26', 'midwest', 1, 1, 1, 1, 1, 1, 1, 0.5, 0.5)",
            &[&session, r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.hex_activity (game_id, tick, h3_index) VALUES ($1, 0, $2)",
            &[&session, r7],
        )
        .unwrap();
    let final_tick = i32::try_from(MULTI_BATCH_HEX_ACTIVITY_ROWS - 1).unwrap();
    assert_eq!(
        client
            .execute(
                "INSERT INTO public.hex_activity (game_id, tick, h3_index) \
                 SELECT $1, tick, $2 FROM pg_catalog.generate_series(1, $3) AS ticks(tick)",
                &[&session, r7, &final_tick],
            )
            .unwrap(),
        u64::try_from(MULTI_BATCH_HEX_ACTIVITY_ROWS - 1).unwrap()
    );
    client
        .execute(
            "INSERT INTO public.hex_cell \
         (h3_index, county_fips, state_fips, res6_parent, res5_parent, geometry, centroid) \
         VALUES ($1, '26163', '26', $2, $3, \
                 ST_GeomFromText('POLYGON((0 0,0 1,1 1,1 0,0 0))', 4326), \
                 ST_GeomFromText('POINT(0.5 0.5)', 4326))",
            &[r7, r6, r5],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.hex_latest \
         (game_id, h3_index, tick, county_fips, county_name, state_fips, center_lat, center_lng) \
         VALUES ($1, $2, 0, '26163', 'Wayne', '26', 42.3, -83.0)",
            &[&session, r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.hex_map \
         (game_id, h3_index, county_fips, county_name, state_fips, center_lat, center_lng) \
         VALUES ($1, $2, '26163', 'Wayne', '26', 42.3, -83.0)",
            &[&session, r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.hex_spatial_map \
         (session_id, h3_index, county_fips, state_fips, region_id) \
         VALUES ($1, $2, '26163', '26', 'midwest')",
            &[&session, r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.hex_state (session_id, tick, h3_index) VALUES ($1, 0, $2)",
            &[&session, r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.hex_terrain_state (session_id, tick, h3_index) VALUES ($1, 0, $2)",
            &[&session, r7],
        )
        .unwrap();
    insert_nullable_and_multi_field_rows(&mut client, session, r7);
}

fn insert_nullable_and_multi_field_rows(client: &mut postgres::Client, session: Uuid, r7: &str) {
    client
        .execute(
            "INSERT INTO public.immutable_reference_lodes_od_matrix \
         (session_id, year, home_hex, workplace_dest, workplace_dest_kind, s000_workers) \
         VALUES ($1, 2026, $2, $2, 'hex', 1), \
                ($1, 2026, $2, 'canada', 'external', 1)",
            &[&session, &r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.infrastructure_link_state \
         (session_id, tick, source_h3, target_h3, link_id, infra_type) \
         VALUES ($1, 0, $2, $2, 'per279-link', 'power')",
            &[&session, &r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.org_snapshot \
         (game_id, tick, org_id, org_type, home_hex, attributes) \
         VALUES ($1, 0, 'mapped-org', 'business', $2, '{}'::jsonb), \
                ($1, 0, 'unplaced-org', 'business', NULL, '{}'::jsonb)",
            &[&session, &r7],
        )
        .unwrap();
    client
        .execute(
            "INSERT INTO public.tick_event \
         (game_id, tick, event_type, h3_index, summary) \
         VALUES ($1, 0, 'mapped', $2, 'mapped'), \
                ($1, 0, 'unplaced', NULL, 'unplaced')",
            &[&session, &r7],
        )
        .unwrap();
}

fn legacy_value_snapshot(config: &Config) -> Vec<(String, String, Option<String>)> {
    let mut client = config.connect(NoTls).unwrap();
    let rows = client.query(
        "SELECT relation_name, field_name, value FROM ( \
             SELECT 'dynamic_hex_state'::text, 'h3_index'::text, h3_index::text FROM public.dynamic_hex_state UNION ALL \
             SELECT 'hex_activity', 'h3_index', h3_index::text FROM public.hex_activity UNION ALL \
             SELECT 'hex_cell', 'h3_index', h3_index::text FROM public.hex_cell UNION ALL \
             SELECT 'hex_cell', 'res5_parent', res5_parent::text FROM public.hex_cell UNION ALL \
             SELECT 'hex_cell', 'res6_parent', res6_parent::text FROM public.hex_cell UNION ALL \
             SELECT 'hex_latest', 'h3_index', h3_index::text FROM public.hex_latest UNION ALL \
             SELECT 'hex_map', 'h3_index', h3_index::text FROM public.hex_map UNION ALL \
             SELECT 'hex_spatial_map', 'h3_index', h3_index::text FROM public.hex_spatial_map UNION ALL \
             SELECT 'hex_state', 'h3_index', h3_index::text FROM public.hex_state UNION ALL \
             SELECT 'hex_terrain_state', 'h3_index', h3_index::text FROM public.hex_terrain_state UNION ALL \
             SELECT 'immutable_reference_lodes_od_matrix', 'home_hex', home_hex::text FROM public.immutable_reference_lodes_od_matrix UNION ALL \
             SELECT 'immutable_reference_lodes_od_matrix', 'workplace_dest', workplace_dest::text FROM public.immutable_reference_lodes_od_matrix UNION ALL \
             SELECT 'infrastructure_link_state', 'source_h3', source_h3::text FROM public.infrastructure_link_state UNION ALL \
             SELECT 'infrastructure_link_state', 'target_h3', target_h3::text FROM public.infrastructure_link_state UNION ALL \
             SELECT 'org_snapshot', 'home_hex', home_hex::text FROM public.org_snapshot UNION ALL \
             SELECT 'tick_event', 'h3_index', h3_index::text FROM public.tick_event \
         ) AS values(relation_name, field_name, value) \
         ORDER BY relation_name COLLATE \"C\", field_name COLLATE \"C\", value COLLATE \"C\" NULLS FIRST",
        &[],
    ).unwrap();
    rows.iter()
        .map(|row| (row.get(0), row.get(1), row.get(2)))
        .collect()
}

fn assert_exact_shadow_values(config: &Config, cell: &RepresentativeCell) {
    let mut client = config.connect(NoTls).unwrap();
    let row = client
        .query_one(
            "SELECT \
             (SELECT cell_id FROM public.hex_cell LIMIT 1), \
             (SELECT ancestor_r5 FROM public.hex_cell LIMIT 1), \
             (SELECT ancestor_r6 FROM public.hex_cell LIMIT 1), \
             (SELECT workplace_cell_id FROM public.immutable_reference_lodes_od_matrix \
              WHERE workplace_dest_kind = 'hex' LIMIT 1), \
             (SELECT workplace_cell_id IS NULL FROM public.immutable_reference_lodes_od_matrix \
              WHERE workplace_dest_kind = 'external' LIMIT 1), \
             (SELECT pg_catalog.count(*) FROM public.hex_r8_reference), \
             (SELECT pg_catalog.count(*) FROM public.hex_substrate)",
            &[],
        )
        .unwrap();
    assert_eq!(row.get::<_, i64>(0), cell.sql);
    assert_eq!(row.get::<_, i64>(1), cell.ancestor_r5_sql);
    assert_eq!(row.get::<_, i64>(2), cell.ancestor_r6_sql);
    assert_eq!(row.get::<_, i64>(3), cell.sql);
    assert!(row.get::<_, bool>(4));
    assert_eq!(row.get::<_, i64>(5), 0);
    assert_eq!(row.get::<_, i64>(6), 0);
}
