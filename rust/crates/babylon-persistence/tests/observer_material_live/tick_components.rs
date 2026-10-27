//! Exact committed component access belongs exclusively to the full observer.

use super::support;
use super::support::DisposableTarget;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::DurableMaterialRuntime;
use babylon_persistence::michigan_content::MichiganContentPreset;
use babylon_persistence::michigan_material::MichiganDeliveryPreset;
use babylon_persistence::observer_reader;
use babylon_persistence::observer_reader::{
    ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
};
use babylon_persistence::SemanticArchiveReader;
use babylon_persistence::SemanticArchiveReaderError;
use postgres::Client;
use postgres::GenericClient;
use postgres::Statement;
use postgres::Transaction;
use postgres::{Config, NoTls};
use std::fmt::Write as _;
use std::time::Instant;
use uuid::Uuid;

const RELATIONS: [(&str, &str); 24] = [
    ("graph_node_v1", "public.v_observer_graph_node_v1"),
    ("graph_node_f64_v1", "public.v_observer_graph_node_f64_v1"),
    ("graph_edge_v1", "public.v_observer_graph_edge_v1"),
    ("graph_hyperedge_v1", "public.v_observer_graph_hyperedge_v1"),
    (
        "graph_hyperedge_member_v1",
        "public.v_observer_graph_hyperedge_member_v1",
    ),
    ("graph_edge_f64_v1", "public.v_observer_graph_edge_f64_v1"),
    (
        "graph_node_currency_v1",
        "public.v_observer_graph_node_currency_v1",
    ),
    (
        "graph_hyperedge_f64_v1",
        "public.v_observer_graph_hyperedge_f64_v1",
    ),
    ("world_register_v1", "public.v_observer_world_register_v1"),
    ("hex_state_delta_v1", "public.v_observer_hex_state_delta_v1"),
    ("territory_state_v1", "public.v_observer_territory_state_v1"),
    (
        "territory_state_field_v1",
        "public.v_observer_territory_state_field_v1",
    ),
    (
        "organization_state_v1",
        "public.v_observer_organization_state_v1",
    ),
    (
        "organization_state_field_v1",
        "public.v_observer_organization_state_field_v1",
    ),
    (
        "organization_territory_v1",
        "public.v_observer_organization_territory_v1",
    ),
    ("tick_event_v2", "public.v_observer_tick_event_v2"),
    (
        "tick_event_field_v2",
        "public.v_observer_tick_event_field_v2",
    ),
    (
        "tick_choice_receipt_v1",
        "public.v_observer_tick_choice_receipt_v1",
    ),
    (
        "tick_choice_receipt_branch_v1",
        "public.v_observer_tick_choice_receipt_branch_v1",
    ),
    (
        "tick_choice_receipt_carrier_element_v1",
        "public.v_observer_tick_choice_receipt_carrier_element_v1",
    ),
    (
        "checkpoint_manifest",
        "public.v_observer_checkpoint_manifest",
    ),
    (
        "checkpoint_section_v1",
        "public.v_observer_checkpoint_section_v1",
    ),
    (
        "archive_dirty_receipt_v1",
        "public.v_observer_archive_dirty_receipt_v1",
    ),
    (
        "tick_action_batch_v1",
        "public.v_observer_tick_action_batch_v1",
    ),
];

const FOUNDATION_CAMPAIGN: u128 = 41_003;

fn prepared_target() -> DisposableTarget {
    let target = DisposableTarget::create();
    // Keep a second admitted campaign available for the marker-scope mutation.
    drop(
        DurableMaterialRuntime::create(
            &target.writer,
            CampaignId::from_uuid(Uuid::from_u128(FOUNDATION_CAMPAIGN)),
            MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
                .create_foundation(&crate::test_support::catalog())
                .expect("the authored catalog builds the foundation"),
        )
        .expect("the test database creates the fixture campaign"),
    );
    target
}

fn install(target: &DisposableTarget) {
    babylon_persistence::install_reader_role(&target.writer)
        .expect("the test database installs the reader role");
    observer_reader::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
}

fn rows(client: &mut impl GenericClient, relation: &str, campaign: CampaignId) -> Vec<String> {
    client
        .query(
            &format!(
                "SELECT pg_catalog.row_to_json(component)::text FROM {relation} component \
                 WHERE campaign_id=$1::uuid ORDER BY 1"
            ),
            &[campaign.as_uuid()],
        )
        .expect("the seeded rows are readable")
        .iter()
        .map(|row| row.get(0))
        .collect()
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn exact_rows_require_the_matching_commit_marker() {
    let mut target = prepared_target();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(41_001));
    let mut runtime = DurableMaterialRuntime::create(
        &target.writer,
        campaign,
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation"),
    )
    .expect("the test database creates the fixture campaign");
    install(&target);
    support::advance_material_period(&mut runtime);
    let observer_config = target.login("babylon_observer", "components");
    let mut observer = observer_config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut populated = 0;
    for (relation, view) in RELATIONS {
        let raw = format!("babylon_state.{relation}");
        let expected = rows(&mut writer, &raw, campaign);
        populated += usize::from(!expected.is_empty());
        assert_eq!(rows(&mut observer, view, campaign), expected, "{relation}");
        let raw_columns = writer
            .prepare(&format!("SELECT * FROM {raw}"))
            .expect("the fixture call `prepare` succeeds for the authored inputs");
        let view_columns = observer
            .prepare(&format!("SELECT * FROM {view}"))
            .expect("the fixture call `prepare` succeeds for the authored inputs");
        let describe = |statement: &Statement| {
            statement
                .columns()
                .iter()
                .map(|column| (column.name().to_owned(), column.type_().clone()))
                .collect::<Vec<_>>()
        };
        assert_eq!(
            describe(&view_columns),
            describe(&raw_columns),
            "{relation}"
        );
    }
    assert!(
        populated >= 12,
        "real replay must exercise multiple row families"
    );
    // Unsupported layouts are refused by the current schema before a view can
    // observe them. The failed write and rollback preserve the exact marker.
    let marker_before = rows(&mut writer, "babylon_state.tick_commit", campaign);
    let mut tx = writer
        .transaction()
        .expect("the test database opens a transaction");
    let error = tx
        .execute(
            "UPDATE babylon_state.tick_commit SET envelope_layout_version=2 WHERE campaign_id=$1::uuid",
            &[campaign.as_uuid()],
        )
        .expect_err("the test database refuses the invalid statement");
    assert_eq!(
        error.code(),
        Some(&postgres::error::SqlState::CHECK_VIOLATION)
    );
    assert_eq!(
        error
            .as_db_error()
            .expect("the runtime error is a database error")
            .constraint(),
        Some("tick_commit_envelope_layout_v3")
    );
    tx.rollback().expect("the open transaction rolls back");
    assert_eq!(
        rows(&mut writer, "babylon_state.tick_commit", campaign),
        marker_before
    );
    // These remaining corruptions exist only in rolled-back fixture transactions.
    // They isolate each reachable SQL marker predicate without changing saves.
    let wrong_campaign = format!(
        "UPDATE babylon_state.tick_commit SET campaign_id='{}'::uuid WHERE campaign_id=$1::uuid",
        Uuid::from_u128(FOUNDATION_CAMPAIGN)
    );
    for mutation in [
        "DELETE FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid",
        "UPDATE babylon_state.tick_commit SET resolve_tick=resolve_tick+1 WHERE campaign_id=$1::uuid",
        wrong_campaign.as_str(),
    ] {
        let mut tx = writer.transaction().expect("the test database opens a transaction");
        tx.batch_execute("SET CONSTRAINTS ALL DEFERRED").expect("the test database applies the schema statements");
        assert_eq!(tx.execute(mutation, &[campaign.as_uuid()]).expect("the test database applies the setup statement"), 1);
        for (relation, view) in RELATIONS {
            assert!(
                rows(&mut tx, view, campaign).is_empty(),
                "{relation} exposed rows with a mismatched marker: {mutation}"
            );
        }
        tx.rollback().expect("the open transaction rolls back");
    }
    assert_ne!(
        rows(&mut observer, "public.v_observer_graph_node_v1", campaign).len(),
        0
    );
}

fn assert_sql_denied(config: &Config, relation: &str) {
    let error = config
        .connect(NoTls)
        .expect("the test database accepts the connection")
        .query(&format!("SELECT * FROM {relation} LIMIT 0"), &[])
        .expect_err("the fixture call `query` fails for the authored inputs");
    assert_eq!(
        error.code(),
        Some(&postgres::error::SqlState::INSUFFICIENT_PRIVILEGE),
        "{relation}"
    );
}

fn assert_preview_refused(
    known: &ObserverEconomyReader,
    archive: &SemanticArchiveReader,
    campaign: CampaignId,
) {
    assert_eq!(
        known.snapshot(campaign, 0),
        Err(ObserverEconomyError::Authority)
    );
    let error = archive
        .committed_tick_status(campaign)
        .expect_err("the fixture call `committed_tick_status` fails for the authored inputs");
    let SemanticArchiveReaderError::WriterAuthorityRefused(held) = error else {
        panic!("expected exact Archive privilege refusal, got {error:?}");
    };
    for (relation, view) in RELATIONS {
        assert!(
            held.contains(&format!("{view}:SELECT")),
            "Archive census missed {relation}"
        );
    }
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
#[allow(
    clippy::too_many_lines,
    reason = "`full_observer_requires_every_view_and_preview_refuses_all_grant_paths` keeps one authored boundary's fixture and assertions together"
)]
fn full_observer_requires_every_view_and_preview_refuses_all_grant_paths() {
    let mut target = prepared_target();
    install(&target);
    let observer_config = target.login("babylon_observer", "fullcomponents");
    let known_config = target.login("babylon_reader", "knowncomponents");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
            .expect("the test database accepts the connection");
    let known = ObserverEconomyReader::connect(&known_config, ObserverVisibility::KnownPreview)
        .expect("the test database accepts the connection");
    let archive = SemanticArchiveReader::new(&known_config)
        .expect("the constructor accepts the authored fixture arguments");
    let absent = CampaignId::from_uuid(Uuid::from_u128(41_002));
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    assert_eq!(
        known.snapshot(absent, 0),
        Err(ObserverEconomyError::CampaignAbsent)
    );
    assert_eq!(
        observer.snapshot(absent, 0),
        Err(ObserverEconomyError::CampaignAbsent)
    );
    assert_eq!(
        archive
            .committed_tick_status(absent)
            .expect("the fixture call `committed_tick_status` succeeds for the authored inputs"),
        None
    );
    for table in [
        "graph_string_lookup_v1",
        "graph_node_lookup_v1",
        "graph_node_vector_v1",
        "graph_node_manifest_v1",
        "graph_node_chunk_v1",
        "graph_node_f64_chunk_v1",
        "event_text_lookup_v1",
        "event_key_lookup_v1",
        "event_manifest_v1",
        "event_parent_chunk_v1",
        "event_field_chunk_v1",
        "territory_definition_v1",
        "territory_definition_field_v1",
        "territory_tick_manifest_v1",
        "territory_tick_membership_v1",
        "event_parent_expanded_v1",
        "event_field_expanded_v1",
    ] {
        let raw = format!("babylon_state.{table}");
        assert_sql_denied(&observer_config, &raw);
        assert_sql_denied(&known_config, &raw);
    }
    for (relation, view) in RELATIONS {
        let raw = format!("babylon_state.{relation}");
        assert_sql_denied(&observer_config, &raw);
        assert_sql_denied(&known_config, &raw);
        assert_sql_denied(&known_config, view);
        writer
            .batch_execute(&format!("REVOKE SELECT ON {view} FROM babylon_observer"))
            .expect("the test database applies the schema statements");
        assert_eq!(
            observer.snapshot(absent, 0),
            Err(ObserverEconomyError::Authority),
            "{view}"
        );
        writer
            .batch_execute(&format!("GRANT SELECT ON {view} TO babylon_observer"))
            .expect("the test database applies the schema statements");
    }
    // Exercise all relations through each collector: direct, inherited,
    // column ACL and PUBLIC. Held reader instances must re-census each read.
    for (grantee, columns) in [
        (
            format!(
                "\"{}\"",
                known_config
                    .get_user()
                    .expect("the fixture call `get_user` succeeds for the authored inputs")
            ),
            "",
        ),
        ("babylon_reader".to_owned(), ""),
        (
            format!(
                "\"{}\"",
                known_config
                    .get_user()
                    .expect("the fixture call `get_user` succeeds for the authored inputs")
            ),
            " (campaign_id)",
        ),
        ("PUBLIC".to_owned(), ""),
    ] {
        for (_, view) in RELATIONS {
            writer
                .batch_execute(&format!("GRANT SELECT{columns} ON {view} TO {grantee}"))
                .expect("the test database applies the schema statements");
        }
        assert_preview_refused(&known, &archive, absent);
        for (_, view) in RELATIONS {
            writer
                .batch_execute(&format!("REVOKE SELECT{columns} ON {view} FROM {grantee}"))
                .expect("the test database applies the schema statements");
        }
        assert_eq!(
            known.snapshot(absent, 0),
            Err(ObserverEconomyError::CampaignAbsent)
        );
        assert_eq!(
            archive.committed_tick_status(absent).expect(
                "the fixture call `committed_tick_status` succeeds for the authored inputs"
            ),
            None
        );
    }
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn observer_provisioning_refuses_changed_or_missing_component_views_without_repair() {
    let target = DisposableTarget::create();
    install(&target);
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let current_state = |writer: &mut Client| {
        let row = writer
            .query_one(
                "SELECT schema_sha256, CASE \
                 WHEN pg_catalog.to_regclass('public.v_observer_graph_node_v1') IS NULL THEN NULL \
                 ELSE pg_catalog.pg_get_viewdef( \
                     pg_catalog.to_regclass('public.v_observer_graph_node_v1'), false) END \
                 FROM babylon_meta.current_schema WHERE singleton",
                &[],
            )
            .expect("the seeded row is present exactly once");
        (row.get::<_, Vec<u8>>(0), row.get::<_, Option<String>>(1))
    };
    let admitted = current_state(&mut writer);
    assert_eq!(
        admitted.0,
        babylon_persistence::current_schema_sha256().to_vec()
    );
    assert!(admitted.1.is_some());
    writer.batch_execute(
        "CREATE OR REPLACE VIEW public.v_observer_graph_node_v1 AS SELECT component.* FROM babylon_state.graph_node_v1 component WHERE false",
    ).expect("the test database applies the schema statements");
    let altered = current_state(&mut writer);
    assert_eq!(altered.0, admitted.0);
    assert_ne!(altered.1, admitted.1);
    assert_eq!(
        observer_reader::provision_observer_role(&target.writer),
        Err(ObserverEconomyError::SchemaDrift)
    );
    assert_eq!(current_state(&mut writer), altered);
    writer
        .batch_execute("DROP VIEW public.v_observer_graph_node_v1")
        .expect("the test database applies the schema statements");
    let absent = current_state(&mut writer);
    assert_eq!(absent, (admitted.0, None));
    assert_eq!(
        observer_reader::provision_observer_role(&target.writer),
        Err(ObserverEconomyError::SchemaDrift)
    );
    assert_eq!(current_state(&mut writer), absent);
}

fn committed_graph_target() -> (DisposableTarget, CampaignId) {
    let target = prepared_target();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(41_011));
    let mut runtime = DurableMaterialRuntime::create(
        &target.writer,
        campaign,
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation"),
    )
    .expect("the test database creates the fixture campaign");
    support::advance_material_period(&mut runtime);
    (target, campaign)
}

fn graph_fault_vector(tx: &mut Transaction<'_>, campaign: CampaignId, ids: &[i64]) -> i64 {
    // A nonexistent vector is the independently authored missing-reference case.
    if ids.iter().any(|id| *id < 0) {
        return i64::MAX;
    }
    if let Some(row) = tx.query_opt("SELECT vector_id FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=$1 AND node_ids=$2::bigint[]", &[campaign.as_uuid(), &ids]).expect("the seeded row is present at most once") {
        return row.get(0);
    }
    let id: i64 = tx.query_one("SELECT coalesce(max(vector_id),-1)+1 FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=$1", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
    tx.execute("INSERT INTO babylon_state.graph_node_vector_v1(campaign_id,vector_id,first_tick,node_ids) VALUES($1,$2,2,$3)", &[campaign.as_uuid(), &id, &ids]).expect("the test database applies the setup statement");
    id
}

fn clone_graph_marker(tx: &mut Transaction<'_>, campaign: CampaignId) {
    clone_graph_marker_at(tx, campaign, 2);
}

fn clone_graph_marker_at(tx: &mut Transaction<'_>, campaign: CampaignId, tick: i64) {
    // Rollback-only SQL fault controls need the existing material-row presence
    // prerequisite. These copied packages are never read as a canonical tick or
    // committed; only the selected graph constraint is forced immediately.
    tx.execute("INSERT INTO babylon_state.material_tick_v3 SELECT campaign_id,$2,identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid(), &tick]).expect("the test database applies the setup statement");
    // Preserve the real admitted territory membership while faulting graph rows.
    assert_eq!(
        tx.execute("INSERT INTO babylon_state.territory_tick_manifest_v1 (campaign_id,resolve_tick,territory_count) SELECT campaign_id,$2,territory_count FROM babylon_state.territory_tick_manifest_v1 WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid(), &tick]).expect("the test database applies the setup statement"),
        1
    );
    tx.execute("INSERT INTO babylon_state.territory_tick_membership_v1 (campaign_id,resolve_tick,definition_id) SELECT campaign_id,$2,definition_id FROM babylon_state.territory_tick_membership_v1 WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid(), &tick]).expect("the test database applies the setup statement");
    tx.execute("INSERT INTO babylon_state.tick_commit SELECT campaign_id,$2,envelope_layout_version,tick_content_hash,envelope_digest FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid(), &tick]).expect("the test database applies the setup statement");
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
#[allow(
    clippy::too_many_lines,
    reason = "`graph_marker_refuses_missing_mismatched_orphan_duplicate_and_gap_components` keeps one authored boundary's fixture and assertions together"
)]
fn graph_marker_refuses_missing_mismatched_orphan_duplicate_and_gap_components() {
    let (target, campaign) = committed_graph_target();
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let node: i64 = writer.query_one("SELECT node_id FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=$1::uuid ORDER BY node_id LIMIT 1", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
    let qname: i64 = writer.query_one("SELECT string_id FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid ORDER BY string_id LIMIT 1", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
    for (counts, membership, attributes, expected) in [
        (None, None, None, "graph_node_manifest_missing"),
        (
            Some((1, 0, 0, 0)),
            None,
            None,
            "graph_node_chunk_gap_or_count",
        ),
        (
            Some((1, 0, 1, 0)),
            Some((0, vec![-1_i64])),
            None,
            "graph_vector_reference",
        ),
        (
            Some((2, 0, 1, 0)),
            Some((0, vec![node, node])),
            None,
            "graph_node_reference_or_duplicate",
        ),
        (
            Some((1, 0, 1, 0)),
            Some((1, vec![node])),
            None,
            "graph_node_chunk_gap_or_count",
        ),
        (
            Some((0, 1, 0, 1)),
            None,
            Some(vec![node]),
            "graph_f64_reference_or_duplicate",
        ),
        (
            Some((1, 2, 1, 1)),
            Some((0, vec![node])),
            Some(vec![node, node]),
            "graph_f64_reference_or_duplicate",
        ),
    ] {
        let mut tx = writer
            .transaction()
            .expect("the test database opens a transaction");
        if let Some((nodes, f64s, node_chunks, f64_chunks)) = counts {
            tx.execute(
                "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES ($1,2,$2,$3,$4,$5)",
                &[
                    campaign.as_uuid(),
                    &i64::from(nodes),
                    &i64::from(f64s),
                    &i64::from(node_chunks),
                    &i64::from(f64_chunks),
                ],
            )
            .expect("the test database applies the setup statement");
        }
        if let Some((ordinal, ids)) = membership {
            let vector = graph_fault_vector(&mut tx, campaign, &ids);
            tx.execute(
                "INSERT INTO babylon_state.graph_node_chunk_v1 VALUES ($1,2,$2,$3)",
                &[campaign.as_uuid(), &i64::from(ordinal), &vector],
            )
            .expect("the test database applies the setup statement");
        }
        if let Some(ids) = attributes {
            let bits = vec![0_i64; ids.len()];
            let vector = graph_fault_vector(&mut tx, campaign, &ids);
            tx.execute(
                "INSERT INTO babylon_state.graph_node_f64_chunk_v1 VALUES ($1,2,$2,0,$3,$4)",
                &[campaign.as_uuid(), &qname, &vector, &bits],
            )
            .expect("the test database applies the setup statement");
        }
        clone_graph_marker(&mut tx, campaign);
        let error = tx
            .batch_execute("SET CONSTRAINTS babylon_state.graph_node_marker_complete_v1 IMMEDIATE")
            .expect_err("the fixture call `batch_execute` fails for the authored inputs");
        assert_eq!(
            error
                .as_db_error()
                .expect("the runtime error is a database error")
                .message(),
            expected
        );
        tx.rollback().expect("the open transaction rolls back");
    }
    assert_eq!(
        writer
            .query_one(
                "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid",
                &[campaign.as_uuid()]
            )
            .expect("the seeded row is present exactly once")
            .get::<_, i64>(0),
        1
    );
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn marked_graph_rows_and_late_foundation_lookup_are_immutable() {
    let (target, campaign) = committed_graph_target();
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    for sql in [
        "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES ($1,1,0,0,0,0) ON CONFLICT DO NOTHING",
        "INSERT INTO babylon_state.graph_node_chunk_v1 VALUES ($1,1,999999,0)",
        "INSERT INTO babylon_state.graph_node_f64_chunk_v1 VALUES ($1,1,0,999999,0,ARRAY[0::bigint])",
    ] {
        let mut tx=writer.transaction().expect("the test database opens a transaction");
        let outcome=tx.execute(sql,&[campaign.as_uuid()]);
        if sql.contains("ON CONFLICT") {
            // A no-op conflict cannot change history; the other statements must refuse.
            assert_eq!(outcome.expect("the fixture audit returns its outcome"),0);
        } else {
            assert_eq!(outcome.expect_err("the fixture audit returns its outcome").as_db_error().expect("the runtime error is a database error").message(),"graph_refused_marked_history_mutation");
        }
        tx.rollback().expect("the open transaction rolls back");
    }
    for relation in [
        "graph_string_lookup_v1",
        "graph_node_lookup_v1",
        "graph_node_vector_v1",
        "graph_node_manifest_v1",
        "graph_node_chunk_v1",
        "graph_node_f64_chunk_v1",
    ] {
        for operation in ["UPDATE", "DELETE"] {
            let mut tx = writer
                .transaction()
                .expect("the test database opens a transaction");
            let sql = if operation == "UPDATE" {
                format!("UPDATE babylon_state.{relation} SET campaign_id=campaign_id WHERE campaign_id=$1::uuid")
            } else {
                format!("DELETE FROM babylon_state.{relation} WHERE campaign_id=$1::uuid")
            };
            let error = tx
                .execute(&sql, &[campaign.as_uuid()])
                .expect_err("the test database refuses the invalid statement");
            assert_eq!(
                error
                    .as_db_error()
                    .expect("the runtime error is a database error")
                    .message(),
                "graph_lookup_append_only"
            );
            tx.rollback().expect("the open transaction rolls back");
        }
    }
    let mut tx = writer
        .transaction()
        .expect("the test database opens a transaction");
    let error=tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) SELECT $1,max(string_id)+1,0,'late foundation' FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid", &[campaign.as_uuid()]).expect_err("the test database refuses the invalid statement");
    assert_eq!(
        error
            .as_db_error()
            .expect("the runtime error is a database error")
            .message(),
        "graph_lookup_refused_late_foundation"
    );
    tx.rollback().expect("the open transaction rolls back");
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn graph_lookup_preserves_large_exact_text_and_refuses_duplicate_value() {
    let target = prepared_target();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(FOUNDATION_CAMPAIGN));
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    // SHA hex chunks make a valid UTF-8 value much larger than a B-tree tuple,
    // without the compressibility of a repeated literal masking the defect.
    let mut value = (0_u64..512)
        .map(|n| {
            babylon_kernel::content_digest::sha256_of(&n.to_be_bytes())
                .iter()
                .fold(String::with_capacity(64), |mut output, byte| {
                    write!(&mut output, "{byte:02x}")
                        .expect("the in-memory formatter accepts the written text");
                    output
                })
        })
        .collect::<String>();
    value.push_str("\\Unicode λ漢字\\");
    assert!(value.len() > 32768);
    let mut tx = writer
        .transaction()
        .expect("the test database opens a transaction");
    let id: i64 = tx
        .query_one(
            "SELECT count(*) FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid",
            &[campaign.as_uuid()],
        )
        .expect("the seeded row is present exactly once")
        .get(0);
    tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) VALUES ($1,$2,0,$3)", &[campaign.as_uuid(),&id,&value]).expect("the test database applies the setup statement");
    assert_eq!(tx.query_one("SELECT value FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid AND string_id=$2", &[campaign.as_uuid(),&id]).expect("the seeded row is present exactly once").get::<_,String>(0),value);
    let error=tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) VALUES ($1,$2,0,$3)", &[campaign.as_uuid(),&(id+1),&value]).expect_err("the test database refuses the invalid statement");
    assert_eq!(
        error
            .as_db_error()
            .expect("the runtime error is a database error")
            .message(),
        "graph_lookup_duplicate_string"
    );
    tx.rollback().expect("the open transaction rolls back");
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn origin_zero_lookup_insert_waits_for_the_marker_publication_lock() {
    let (target, campaign) = committed_graph_target();
    let mut publisher = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut contender = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut pending = publisher
        .transaction()
        .expect("the test database opens a transaction");
    clone_graph_marker(&mut pending, campaign);
    // No synthetic tick is published: both transactions roll back. The actual
    // marker BEFORE trigger must nevertheless serialize foundation admission.
    let mut tx = contender
        .transaction()
        .expect("the test database opens a transaction");
    tx.batch_execute("SET LOCAL lock_timeout='50ms'")
        .expect("the test database applies the schema statements");
    let error=tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) SELECT $1,max(string_id)+1,0,'racing foundation' FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid", &[campaign.as_uuid()]).expect_err("the test database refuses the invalid statement");
    assert_eq!(
        error.code(),
        Some(&postgres::error::SqlState::LOCK_NOT_AVAILABLE)
    );
    tx.rollback().expect("the open transaction rolls back");
    pending.rollback().expect("the open transaction rolls back");
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn graph_vectors_reuse_exact_memberships_and_preserve_history() {
    let target = prepared_target();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(41_012));
    let mut runtime = DurableMaterialRuntime::create(
        &target.writer,
        campaign,
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation"),
    )
    .expect("the test database creates the fixture campaign");
    support::advance_material_period(&mut runtime);
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let before: Vec<(String, String, i64)> = writer.query(
        "SELECT local_name,qname,value_bits FROM babylon_state.graph_node_f64_v1 WHERE campaign_id=$1 AND resolve_tick=1 ORDER BY local_name,qname",
        &[campaign.as_uuid()],
    ).expect("the seeded rows are readable").into_iter().map(|r| (r.get(0), r.get(1), r.get(2))).collect();
    support::advance_material_period(&mut runtime);
    assert_eq!(writer.query_one(
        "SELECT count(*) FROM babylon_state.graph_node_vector_v1 a JOIN babylon_state.graph_node_vector_v1 b ON a.campaign_id=b.campaign_id AND a.node_ids=b.node_ids AND a.vector_id<>b.vector_id WHERE a.campaign_id=$1",
        &[campaign.as_uuid()],
    ).expect("the seeded row is present exactly once").get::<_, i64>(0), 0);
    assert!(writer.query_one(
        "SELECT count(*) FROM babylon_state.graph_node_chunk_v1 a JOIN babylon_state.graph_node_chunk_v1 b USING(campaign_id,vector_id) WHERE a.campaign_id=$1 AND a.resolve_tick=1 AND b.resolve_tick=2",
        &[campaign.as_uuid()],
    ).expect("the seeded row is present exactly once").get::<_, i64>(0) > 0);
    let after: Vec<(String, String, i64)> = writer.query(
        "SELECT local_name,qname,value_bits FROM babylon_state.graph_node_f64_v1 WHERE campaign_id=$1 AND resolve_tick=1 ORDER BY local_name,qname",
        &[campaign.as_uuid()],
    ).expect("the seeded rows are readable").into_iter().map(|r| (r.get(0), r.get(1), r.get(2))).collect();
    assert_eq!(after, before);
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn graph_reads_resolve_exact_ids_with_prior_campaign_statistics() {
    let mut target = DisposableTarget::create();
    let create = |id, preset| {
        DurableMaterialRuntime::create(
            &target.writer,
            CampaignId::from_uuid(Uuid::from_u128(id)),
            MichiganContentPreset::new_campaign(preset)
                .create_foundation(&crate::test_support::catalog())
                .expect("the authored catalog builds the foundation"),
        )
        .expect("the test database creates the fixture campaign")
    };
    let mut original = create(343_101, MichiganDeliveryPreset::Standard);
    support::advance_material_period(&mut original);
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    writer
        .batch_execute(
            "ANALYZE babylon_state.graph_node_lookup_v1, babylon_state.graph_string_lookup_v1",
        )
        .expect("the test database applies the schema statements");
    // Keep the prior campaign's statistics stable while creating a new one.
    // This test-owned lock allows inserts and reads, but excludes background
    // ANALYZE. It changes no schema, grants, data, or production planner setting.
    let mut statistics_guard = writer
        .transaction()
        .expect("the test database opens a transaction");
    statistics_guard.batch_execute("SET LOCAL lock_timeout='5s'; LOCK TABLE babylon_state.graph_node_lookup_v1, babylon_state.graph_string_lookup_v1, babylon_state.graph_node_vector_v1, babylon_state.graph_node_chunk_v1, babylon_state.tick_commit IN SHARE UPDATE EXCLUSIVE MODE").expect("the test database applies the schema statements");
    let mut fresh = create(343_102, MichiganDeliveryPreset::Delayed);
    support::advance_material_period(&mut fresh);
    let expected = fresh
        .session()
        .graph_session()
        .stable_graph_state()
        .expect("the fixture graph has a stable state");
    install(&target);
    let config = target.login("babylon_observer", "graphstatistics");
    let mut observer = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut read = observer
        .build_transaction()
        .read_only(true)
        .start()
        .expect("the fixture starts the authored period");
    // A Designed fixture ceiling catches Cartesian lookup expansion promptly;
    // the committed rows must still equal the independent live graph exactly.
    read.batch_execute("SET LOCAL statement_timeout='5s'; SET LOCAL idle_in_transaction_session_timeout='5s'; SET LOCAL jit=off; SET LOCAL search_path=pg_catalog").expect("the test database applies the schema statements");
    let campaign = fresh.campaign_id();
    let began = Instant::now();
    let nodes: Vec<(String, String)> = read.query("SELECT local_name,node_type FROM public.v_observer_graph_node_v1 WHERE campaign_id=$1::uuid AND resolve_tick=1 ORDER BY local_name", &[campaign.as_uuid()]).expect("the seeded rows are readable").into_iter().map(|row| (row.get(0), row.get(1))).collect();
    assert_eq!(nodes, expected.rows().nodes());
    let nodes_elapsed = began.elapsed();
    let began = Instant::now();
    let attributes: Vec<(String, String, u64)> = read.query("SELECT local_name,qname,value_bits FROM public.v_observer_graph_node_f64_v1 WHERE campaign_id=$1::uuid AND resolve_tick=1 ORDER BY local_name,qname", &[campaign.as_uuid()]).expect("the seeded rows are readable").into_iter().map(|row| (row.get(0), row.get(1), u64::from_ne_bytes(row.get::<_, i64>(2).to_ne_bytes()))).collect();
    assert_eq!(attributes, expected.rows().node_f64());
    eprintln!("exact graph lookup stale-statistics control: nodes={} node_read_ms={} attributes={} attribute_read_ms={}", nodes.len(), nodes_elapsed.as_millis(), attributes.len(), began.elapsed().as_millis());
    read.commit().expect("the fixture transaction commits");
    statistics_guard
        .rollback()
        .expect("the open transaction rolls back");
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn graph_vector_missing_future_foreign_and_wrong_length_refuse_marker() {
    let (target, campaign) = committed_graph_target();
    let mut writer = target
        .writer
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let existing: i64 = writer.query_one("SELECT vector_id FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=$1 ORDER BY vector_id LIMIT 1", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
    let node: i64 = writer.query_one("SELECT node_id FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=$1 ORDER BY node_id LIMIT 1", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
    let qname: i64 = writer.query_one("SELECT string_id FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1 ORDER BY string_id LIMIT 1", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
    for case in ["missing", "future", "uncommitted", "foreign", "length"] {
        let mut tx = writer
            .transaction()
            .expect("the test database opens a transaction");
        let tick = if case == "uncommitted" { 3_i64 } else { 2_i64 };
        let vector = if matches!(case, "future" | "uncommitted") {
            let id: i64 = tx.query_one("SELECT max(vector_id)+1 FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=$1", &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
            // Full arrays differ from admitted vectors; origin tick 3 is future.
            tx.execute("INSERT INTO babylon_state.graph_node_vector_v1(campaign_id,vector_id,first_tick,node_ids) VALUES($1,$2,$3,$4)", &[campaign.as_uuid(), &id, &if case == "future" { 3_i64 } else { 2_i64 }, &vec![node; 4096]]).expect("the test database applies the setup statement");
            id
        } else if case == "length" {
            existing
        } else {
            i64::MAX
        };
        if case == "foreign" {
            // prepared_target owns a second genuinely admitted foundation and
            // its opening node dictionary. No absent campaign or copied names
            // should reject this independently authored reference first.
            let foreign = CampaignId::from_uuid(Uuid::from_u128(FOUNDATION_CAMPAIGN));
            let foreign_node: i64 = tx.query_one("SELECT node_id FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=$1 ORDER BY node_id LIMIT 1", &[foreign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
            tx.execute("INSERT INTO babylon_state.graph_node_vector_v1(campaign_id,vector_id,first_tick,node_ids) VALUES($1,$2,2,$3)", &[foreign.as_uuid(), &vector, &vec![foreign_node]]).expect("the test database applies the setup statement");
        }
        let nodes: i64 = if case == "length" {
            tx.query_one("SELECT cardinality(node_ids)::bigint FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=$1 AND vector_id=$2", &[campaign.as_uuid(), &vector]).expect("the seeded row is present exactly once").get(0)
        } else {
            1
        };
        tx.execute(
            "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES($1,$2,$3,$4,1,$4)",
            &[
                campaign.as_uuid(),
                &tick,
                &nodes,
                &i64::from(case == "length"),
            ],
        )
        .expect("the test database applies the setup statement");
        tx.execute(
            "INSERT INTO babylon_state.graph_node_chunk_v1 VALUES($1,$2,0,$3)",
            &[campaign.as_uuid(), &tick, &vector],
        )
        .expect("the test database applies the setup statement");
        if case == "length" {
            let bits = vec![
                0_i64;
                if nodes > 1 {
                    usize::try_from(nodes - 1).expect("the fixture value fits the target range")
                } else {
                    2
                }
            ];
            tx.execute(
                "INSERT INTO babylon_state.graph_node_f64_chunk_v1 VALUES($1,$2,$3,0,$4,$5)",
                &[campaign.as_uuid(), &tick, &qname, &vector, &bits],
            )
            .expect("the test database applies the setup statement");
        }
        clone_graph_marker_at(&mut tx, campaign, tick);
        let error = tx
            .batch_execute("SET CONSTRAINTS babylon_state.graph_node_marker_complete_v1 IMMEDIATE")
            .expect_err("the fixture call `batch_execute` fails for the authored inputs");
        assert_eq!(
            error
                .as_db_error()
                .expect("the runtime error is a database error")
                .message(),
            if case == "length" {
                "graph_f64_vector_length"
            } else {
                "graph_vector_reference"
            }
        );
        tx.rollback().expect("the open transaction rolls back");
    }
}
