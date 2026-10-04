//! Exact committed component access belongs exclusively to the full observer.

use super::*;
use babylon_persistence::SemanticArchiveReaderError;
use postgres::GenericClient;
use std::fmt::Write as _;

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
                .unwrap(),
        )
        .unwrap(),
    );
    target
}

fn install(target: &DisposableTarget) {
    install_reader_role(&target.writer).unwrap();
    provision_observer_role(&target.writer).unwrap();
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
        .unwrap()
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
            .unwrap(),
    )
    .unwrap();
    install(&target);
    advance_material_period(&mut runtime);
    let observer_config = target.login("babylon_observer", "components");
    let mut observer = observer_config.connect(NoTls).unwrap();
    let mut writer = target.writer.connect(NoTls).unwrap();
    let mut populated = 0;
    for (relation, view) in RELATIONS {
        let raw = format!("babylon_state.{relation}");
        let expected = rows(&mut writer, &raw, campaign);
        populated += usize::from(!expected.is_empty());
        assert_eq!(rows(&mut observer, view, campaign), expected, "{relation}");
        let raw_columns = writer.prepare(&format!("SELECT * FROM {raw}")).unwrap();
        let view_columns = observer.prepare(&format!("SELECT * FROM {view}")).unwrap();
        let describe = |statement: &postgres::Statement| {
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
    let mut tx = writer.transaction().unwrap();
    let error = tx
        .execute(
            "UPDATE babylon_state.tick_commit SET envelope_layout_version=2 WHERE campaign_id=$1::uuid",
            &[campaign.as_uuid()],
        )
        .unwrap_err();
    assert_eq!(
        error.code(),
        Some(&postgres::error::SqlState::CHECK_VIOLATION)
    );
    assert_eq!(
        error.as_db_error().unwrap().constraint(),
        Some("tick_commit_envelope_layout_v3")
    );
    tx.rollback().unwrap();
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
        let mut tx = writer.transaction().unwrap();
        tx.batch_execute("SET CONSTRAINTS ALL DEFERRED").unwrap();
        assert_eq!(tx.execute(mutation, &[campaign.as_uuid()]).unwrap(), 1);
        for (relation, view) in RELATIONS {
            assert!(
                rows(&mut tx, view, campaign).is_empty(),
                "{relation} exposed rows with a mismatched marker: {mutation}"
            );
        }
        tx.rollback().unwrap();
    }
    assert!(!rows(&mut observer, "public.v_observer_graph_node_v1", campaign).is_empty());
}

fn assert_sql_denied(config: &Config, relation: &str) {
    let error = config
        .connect(NoTls)
        .unwrap()
        .query(&format!("SELECT * FROM {relation} LIMIT 0"), &[])
        .unwrap_err();
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
    let error = archive.committed_tick_status(campaign).unwrap_err();
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
fn full_observer_requires_every_view_and_preview_refuses_all_grant_paths() {
    let mut target = prepared_target();
    install(&target);
    let observer_config = target.login("babylon_observer", "fullcomponents");
    let known_config = target.login("babylon_reader", "knowncomponents");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver).unwrap();
    let known =
        ObserverEconomyReader::connect(&known_config, ObserverVisibility::KnownPreview).unwrap();
    let archive = SemanticArchiveReader::new(&known_config).unwrap();
    let absent = CampaignId::from_uuid(Uuid::from_u128(41_002));
    let mut writer = target.writer.connect(NoTls).unwrap();
    assert_eq!(
        known.snapshot(absent, 0),
        Err(ObserverEconomyError::CampaignAbsent)
    );
    assert_eq!(
        observer.snapshot(absent, 0),
        Err(ObserverEconomyError::CampaignAbsent)
    );
    assert_eq!(archive.committed_tick_status(absent).unwrap(), None);
    for table in [
        "graph_string_lookup_v1",
        "graph_node_lookup_v1",
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
            .unwrap();
        assert_eq!(
            observer.snapshot(absent, 0),
            Err(ObserverEconomyError::Authority),
            "{view}"
        );
        writer
            .batch_execute(&format!("GRANT SELECT ON {view} TO babylon_observer"))
            .unwrap();
    }
    // Exercise all relations through each collector: direct, inherited,
    // column ACL and PUBLIC. Held reader instances must re-census each read.
    for (grantee, columns) in [
        (format!("\"{}\"", known_config.get_user().unwrap()), ""),
        ("babylon_reader".to_owned(), ""),
        (
            format!("\"{}\"", known_config.get_user().unwrap()),
            " (campaign_id)",
        ),
        ("PUBLIC".to_owned(), ""),
    ] {
        for (_, view) in RELATIONS {
            writer
                .batch_execute(&format!("GRANT SELECT{columns} ON {view} TO {grantee}"))
                .unwrap();
        }
        assert_preview_refused(&known, &archive, absent);
        for (_, view) in RELATIONS {
            writer
                .batch_execute(&format!("REVOKE SELECT{columns} ON {view} FROM {grantee}"))
                .unwrap();
        }
        assert_eq!(
            known.snapshot(absent, 0),
            Err(ObserverEconomyError::CampaignAbsent)
        );
        assert_eq!(archive.committed_tick_status(absent).unwrap(), None);
    }
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn observer_provisioning_refuses_changed_or_missing_component_views_without_repair() {
    let target = DisposableTarget::create();
    install(&target);
    let mut writer = target.writer.connect(NoTls).unwrap();
    let current_state = |writer: &mut postgres::Client| {
        let row = writer
            .query_one(
                "SELECT schema_sha256, CASE \
                 WHEN pg_catalog.to_regclass('public.v_observer_graph_node_v1') IS NULL THEN NULL \
                 ELSE pg_catalog.pg_get_viewdef( \
                     pg_catalog.to_regclass('public.v_observer_graph_node_v1'), false) END \
                 FROM babylon_meta.current_schema WHERE singleton",
                &[],
            )
            .unwrap();
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
    ).unwrap();
    let altered = current_state(&mut writer);
    assert_eq!(altered.0, admitted.0);
    assert_ne!(altered.1, admitted.1);
    assert_eq!(
        provision_observer_role(&target.writer),
        Err(ObserverEconomyError::SchemaDrift)
    );
    assert_eq!(current_state(&mut writer), altered);
    writer
        .batch_execute("DROP VIEW public.v_observer_graph_node_v1")
        .unwrap();
    let absent = current_state(&mut writer);
    assert_eq!(absent, (admitted.0, None));
    assert_eq!(
        provision_observer_role(&target.writer),
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
            .unwrap(),
    )
    .unwrap();
    advance_material_period(&mut runtime);
    (target, campaign)
}

fn clone_graph_marker(tx: &mut postgres::Transaction<'_>, campaign: CampaignId) {
    // Rollback-only SQL fault controls need the existing material-row presence
    // prerequisite. These copied packages are never read as a canonical tick or
    // committed; only the selected graph constraint is forced immediately.
    tx.execute("INSERT INTO babylon_state.material_tick_v3 SELECT campaign_id,2,identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid()]).unwrap();
    // Preserve the real admitted territory membership while faulting graph rows.
    assert_eq!(
        tx.execute("INSERT INTO babylon_state.territory_tick_manifest_v1 (campaign_id,resolve_tick,territory_count) SELECT campaign_id,2,territory_count FROM babylon_state.territory_tick_manifest_v1 WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid()]).unwrap(),
        1
    );
    tx.execute("INSERT INTO babylon_state.territory_tick_membership_v1 (campaign_id,resolve_tick,definition_id) SELECT campaign_id,2,definition_id FROM babylon_state.territory_tick_membership_v1 WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid()]).unwrap();
    tx.execute("INSERT INTO babylon_state.tick_commit SELECT campaign_id,2,envelope_layout_version,tick_content_hash,envelope_digest FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid AND resolve_tick=1", &[campaign.as_uuid()]).unwrap();
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn graph_marker_refuses_missing_mismatched_orphan_duplicate_and_gap_components() {
    let (target, campaign) = committed_graph_target();
    let mut writer = target.writer.connect(NoTls).unwrap();
    let node: i64 = writer.query_one("SELECT node_id FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=$1::uuid ORDER BY node_id LIMIT 1", &[campaign.as_uuid()]).unwrap().get(0);
    let qname: i64 = writer.query_one("SELECT string_id FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid ORDER BY string_id LIMIT 1", &[campaign.as_uuid()]).unwrap().get(0);
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
            "graph_node_reference_or_duplicate",
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
        let mut tx = writer.transaction().unwrap();
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
            .unwrap();
        }
        if let Some((ordinal, ids)) = membership {
            tx.execute(
                "INSERT INTO babylon_state.graph_node_chunk_v1 VALUES ($1,2,$2,$3)",
                &[campaign.as_uuid(), &i64::from(ordinal), &ids],
            )
            .unwrap();
        }
        if let Some(ids) = attributes {
            let bits = vec![0_i64; ids.len()];
            tx.execute(
                "INSERT INTO babylon_state.graph_node_f64_chunk_v1 VALUES ($1,2,$2,0,$3,$4)",
                &[campaign.as_uuid(), &qname, &ids, &bits],
            )
            .unwrap();
        }
        clone_graph_marker(&mut tx, campaign);
        let error = tx
            .batch_execute("SET CONSTRAINTS babylon_state.graph_node_marker_complete_v1 IMMEDIATE")
            .unwrap_err();
        assert_eq!(error.as_db_error().unwrap().message(), expected);
        tx.rollback().unwrap();
    }
    assert_eq!(
        writer
            .query_one(
                "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid",
                &[campaign.as_uuid()]
            )
            .unwrap()
            .get::<_, i64>(0),
        1
    );
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn marked_graph_rows_and_late_foundation_lookup_are_immutable() {
    let (target, campaign) = committed_graph_target();
    let mut writer = target.writer.connect(NoTls).unwrap();
    for sql in [
        "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES ($1,1,0,0,0,0) ON CONFLICT DO NOTHING",
        "INSERT INTO babylon_state.graph_node_chunk_v1 VALUES ($1,1,999999,ARRAY[0::bigint])",
        "INSERT INTO babylon_state.graph_node_f64_chunk_v1 VALUES ($1,1,0,999999,ARRAY[0::bigint],ARRAY[0::bigint])",
    ] {
        let mut tx=writer.transaction().unwrap();
        let outcome=tx.execute(sql,&[campaign.as_uuid()]);
        if sql.contains("ON CONFLICT") {
            // A no-op conflict cannot change history; the other statements must refuse.
            assert_eq!(outcome.unwrap(),0);
        } else {
            assert_eq!(outcome.unwrap_err().as_db_error().unwrap().message(),"graph_refused_marked_history_mutation");
        }
        tx.rollback().unwrap();
    }
    for relation in [
        "graph_string_lookup_v1",
        "graph_node_lookup_v1",
        "graph_node_manifest_v1",
        "graph_node_chunk_v1",
        "graph_node_f64_chunk_v1",
    ] {
        for operation in ["UPDATE", "DELETE"] {
            let mut tx = writer.transaction().unwrap();
            let sql = if operation == "UPDATE" {
                format!("UPDATE babylon_state.{relation} SET campaign_id=campaign_id WHERE campaign_id=$1::uuid")
            } else {
                format!("DELETE FROM babylon_state.{relation} WHERE campaign_id=$1::uuid")
            };
            let error = tx.execute(&sql, &[campaign.as_uuid()]).unwrap_err();
            assert_eq!(
                error.as_db_error().unwrap().message(),
                "graph_lookup_append_only"
            );
            tx.rollback().unwrap();
        }
    }
    let mut tx = writer.transaction().unwrap();
    let error=tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) SELECT $1,max(string_id)+1,0,'late foundation' FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid", &[campaign.as_uuid()]).unwrap_err();
    assert_eq!(
        error.as_db_error().unwrap().message(),
        "graph_lookup_refused_late_foundation"
    );
    tx.rollback().unwrap();
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn graph_lookup_preserves_large_exact_text_and_refuses_duplicate_value() {
    let target = prepared_target();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(FOUNDATION_CAMPAIGN));
    let mut writer = target.writer.connect(NoTls).unwrap();
    // SHA hex chunks make a valid UTF-8 value much larger than a B-tree tuple,
    // without the compressibility of a repeated literal masking the defect.
    let mut value = (0_u64..512)
        .map(|n| {
            babylon_kernel::content_digest::sha256_of(&n.to_be_bytes())
                .iter()
                .fold(String::with_capacity(64), |mut output, byte| {
                    write!(&mut output, "{byte:02x}").unwrap();
                    output
                })
        })
        .collect::<String>();
    value.push_str("\\Unicode λ漢字\\");
    assert!(value.len() > 32768);
    let mut tx = writer.transaction().unwrap();
    let id: i64 = tx
        .query_one(
            "SELECT count(*) FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid",
            &[campaign.as_uuid()],
        )
        .unwrap()
        .get(0);
    tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) VALUES ($1,$2,0,$3)", &[campaign.as_uuid(),&id,&value]).unwrap();
    assert_eq!(tx.query_one("SELECT value FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid AND string_id=$2", &[campaign.as_uuid(),&id]).unwrap().get::<_,String>(0),value);
    let error=tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) VALUES ($1,$2,0,$3)", &[campaign.as_uuid(),&(id+1),&value]).unwrap_err();
    assert_eq!(
        error.as_db_error().unwrap().message(),
        "graph_lookup_duplicate_string"
    );
    tx.rollback().unwrap();
}

#[test]
#[ignore = "requires the disposable PostgreSQL harness; independent clone ownership"]
fn origin_zero_lookup_insert_waits_for_the_marker_publication_lock() {
    let (target, campaign) = committed_graph_target();
    let mut publisher = target.writer.connect(NoTls).unwrap();
    let mut contender = target.writer.connect(NoTls).unwrap();
    let mut pending = publisher.transaction().unwrap();
    clone_graph_marker(&mut pending, campaign);
    // No synthetic tick is published: both transactions roll back. The actual
    // marker BEFORE trigger must nevertheless serialize foundation admission.
    let mut tx = contender.transaction().unwrap();
    tx.batch_execute("SET LOCAL lock_timeout='50ms'").unwrap();
    let error=tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) SELECT $1,max(string_id)+1,0,'racing foundation' FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid", &[campaign.as_uuid()]).unwrap_err();
    assert_eq!(
        error.code(),
        Some(&postgres::error::SqlState::LOCK_NOT_AVAILABLE)
    );
    tx.rollback().unwrap();
    pending.rollback().unwrap();
}
