//! Live `PostgreSQL` proof for the frozen legacy H3 shadow-key backfill.

use super::{
    assert_lock_released, database_user, h3_reference_installer_postgres, ScratchDatabase,
};
use babylon_persistence::{
    adopt_legacy_schema, backfill_legacy_h3_shadow_keys, install_representative_h3_cohort,
    migrate_schema_epoch, H3CellId, H3ShadowBackfillDisposition, H3ShadowBackfillError,
    H3ShadowBackfillIssueKind, H3ShadowBackfillReport, H3ShadowFieldReport, H3ShadowRelation,
    H3ShadowRelationReport, H3_SHADOW_FIELD_COUNT, H3_SHADOW_RELATION_COUNT,
};
use postgres::{Config, IsolationLevel, NoTls};
use uuid::Uuid;

const SESSION_ID: &str = "27900000-0000-0000-0000-000000000001";
const BACKEND_TERMINATION_TIMEOUT_MILLIS: i64 = 5_000;

pub(super) fn verify_h3_shadow_backfill(base: &Config, legacy_template: &str) {
    verify_fresh_origin_is_an_exact_noop(base);
    verify_invalid_late_relation_refuses_before_any_mutation(base, legacy_template);
    verify_coarse_child_resolution_refuses_before_ancestry(base, legacy_template);
    verify_all_governed_fields_backfill_once_and_retry_exactly(base, legacy_template);
}

fn verify_fresh_origin_is_an_exact_noop(base: &Config) {
    let database = ScratchDatabase::empty(base, "h3_shadow_fresh", database_user(base));
    let config = database.config(base);
    let migration = migrate_schema_epoch(&config).expect("fresh database must reach epoch 6");
    assert_eq!(migration.final_applied, 6);

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
            }))
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

fn verify_all_governed_fields_backfill_once_and_retry_exactly(base: &Config, template: &str) {
    let (database, config) = exact_legacy_database(base, template, "h3_shadow_green");
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
    assert_lock_released(&config);
    database.cleanup();
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
        1
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
    install_representative_h3_cohort(&config, &cohort)
        .expect("representative canonical H3 identity must install before backfill");
    (database, config)
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
