use postgres::error::SqlState;

const CASES: &[(&str, &str)] = &[
    ("missing_manifest", "territory_manifest_missing"),
    ("missing_reference", ""),
    (
        "future_reference",
        "territory_membership_count_identity_or_time",
    ),
    (
        "uncommitted_past",
        "territory_membership_count_identity_or_time",
    ),
    ("definition_gap", "territory_definition_id_gap"),
    ("missing_field", "territory_definition_field_count_or_order"),
    ("same_transaction_overfill", "territory_definition_field_count_or_order"),
    (
        "field_position_gap",
        "territory_definition_field_count_or_order",
    ),
    (
        "field_name_order",
        "territory_definition_field_count_or_order",
    ),
    ("sealed_fields", "territory_definition_fields_sealed"),
    (
        "late_membership",
        "territory_refused_marked_history_mutation",
    ),
    (
        "late_current_definition",
        "territory_refused_marked_history_mutation",
    ),
    (
        "late_opening_definition",
        "territory_late_opening_definition",
    ),
    ("mutate_definition", "territory_append_only"),
    ("mutate_field", "territory_append_only"),
    ("mutate_manifest", "territory_append_only"),
    ("mutate_membership", "territory_append_only"),
];

fn header(tx: &mut Transaction<'_>, campaign: CampaignId, id: i64, tick: i64, count: i32) {
    let key = babylon_graph::stable_element::StableElementKey::Node {
        scenario: "proof".into(),
        local_name: "fault".into(),
    }
    .canonical_bytes()
    .unwrap();
    tx.execute("INSERT INTO babylon_state.territory_definition_v1(campaign_id,definition_id,first_tick,territory_id,field_count,canonical_sha256) VALUES($1,$2,$3,$4,$5,$6)", &[campaign.as_uuid(),&id,&tick,&key,&count,&&[1_u8;32][..]]).unwrap();
}

fn manifest(tx: &mut Transaction<'_>, campaign: CampaignId, tick: i64, count: i64) {
    tx.execute(
        "INSERT INTO babylon_state.territory_tick_manifest_v1 VALUES($1,$2,$3)",
        &[campaign.as_uuid(), &tick, &count],
    )
    .unwrap();
}

fn membership(tx: &mut Transaction<'_>, campaign: CampaignId, tick: i64, id: i64) {
    tx.execute(
        "INSERT INTO babylon_state.territory_tick_membership_v1 VALUES($1,$2,$3)",
        &[campaign.as_uuid(), &tick, &id],
    )
    .unwrap();
}

fn field(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    id: i64,
    position: i32,
    name: &str,
) -> Result<u64, postgres::Error> {
    tx.execute("INSERT INTO babylon_state.territory_definition_field_v1(campaign_id,definition_id,position,field_name,value_tag,int_value) VALUES($1,$2,$3,$4,1,1)", &[campaign.as_uuid(),&id,&position,&name])
}

fn marker_result(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    tick: i64,
) -> Result<u64, postgres::Error> {
    // Marker guard is BEFORE INSERT, unlike deferred field completeness.
    marker_components(tx, campaign, tick);
    tx.execute(
        "INSERT INTO babylon_state.tick_commit VALUES($1,$2,3,$3,$3)",
        &[campaign.as_uuid(), &tick, &&[1_u8; 32][..]],
    )
}

fn definition_case(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    id: i64,
    case: &str,
) -> Result<u64, postgres::Error> {
    match case {
        "same_transaction_overfill" => {
            header(tx, campaign, id, 0, 0);
            tx.batch_execute("SET CONSTRAINTS babylon_state.territory_definition_complete_v1 IMMEDIATE").unwrap();
            return field(tx, campaign, id, 0, "late");
        }
        "missing_field" => header(tx, campaign, id, 1, 1),
        "field_position_gap" => {
            header(tx, campaign, id, 1, 1);
            field(tx, campaign, id, 1, "a").unwrap();
        }
        "field_name_order" => {
            header(tx, campaign, id, 1, 2);
            field(tx, campaign, id, 0, "z").unwrap();
            field(tx, campaign, id, 1, "a").unwrap();
        }
        "sealed_fields" => return field(tx, campaign, 0, i32::MAX, "sealed-extra"),
        _ => unreachable!(),
    }
    tx.batch_execute("SET CONSTRAINTS babylon_state.territory_definition_complete_v1 IMMEDIATE")
        .map(|()| 0)
}

fn marker_case(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    id: i64,
    case: &str,
) -> Result<u64, postgres::Error> {
    match case {
        "missing_manifest" => {}
        "missing_reference" => {
            manifest(tx, campaign, 1, 1);
            return tx.execute(
                "INSERT INTO babylon_state.territory_tick_membership_v1 VALUES($1,1,$2)",
                &[campaign.as_uuid(), &i64::MAX],
            );
        }
        "future_reference" => {
            header(tx, campaign, id, 2, 0);
            manifest(tx, campaign, 1, 1);
            membership(tx, campaign, 1, id);
        }
        "uncommitted_past" => {
            header(tx, campaign, id, 1, 0);
            manifest(tx, campaign, 2, 1);
            membership(tx, campaign, 2, id);
            return marker_result(tx, campaign, 2);
        }
        "definition_gap" => {
            header(tx, campaign, id + 1, 1, 0);
            manifest(tx, campaign, 1, 0);
        }
        _ => unreachable!(),
    }
    marker_result(tx, campaign, 1)
}

fn sealed_case(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    id: i64,
    case: &str,
) -> Result<u64, postgres::Error> {
    if case.starts_with("mutate_") {
        let sql = match case {
            "mutate_definition" => "UPDATE babylon_state.territory_definition_v1 SET field_count=field_count WHERE campaign_id=$1",
            "mutate_field" => "UPDATE babylon_state.territory_definition_field_v1 SET position=position WHERE campaign_id=$1",
            "mutate_manifest" => "DELETE FROM babylon_state.territory_tick_manifest_v1 WHERE campaign_id=$1",
            "mutate_membership" => "DELETE FROM babylon_state.territory_tick_membership_v1 WHERE campaign_id=$1",
            _ => unreachable!(),
        };
        return tx.execute(sql, &[campaign.as_uuid()]);
    }
    manifest(tx, campaign, 1, 0);
    marker_result(tx, campaign, 1).unwrap();
    match case {
        "late_membership" => tx.execute(
            "INSERT INTO babylon_state.territory_tick_membership_v1 VALUES($1,1,0)",
            &[campaign.as_uuid()],
        ),
        "late_current_definition" | "late_opening_definition" => {
            let tick = i64::from(case == "late_current_definition");
            let key = babylon_graph::stable_element::StableElementKey::Node {
                scenario: "proof".into(),
                local_name: "late".into(),
            }
            .canonical_bytes()
            .unwrap();
            tx.execute("INSERT INTO babylon_state.territory_definition_v1(campaign_id,definition_id,first_tick,territory_id,field_count,canonical_sha256) VALUES($1,$2,$3,$4,0,$5)", &[campaign.as_uuid(),&id,&tick,&key,&&[1_u8;32][..]])
        }
        _ => unreachable!(),
    }
}

fn fault_result(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    id: i64,
    case: &str,
) -> Result<u64, postgres::Error> {
    if matches!(
        case,
        "missing_field" | "field_position_gap" | "field_name_order" | "sealed_fields" | "same_transaction_overfill"
    ) {
        definition_case(tx, campaign, id, case)
    } else if case.starts_with("late_") || case.starts_with("mutate_") {
        sealed_case(tx, campaign, id, case)
    } else {
        marker_case(tx, campaign, id, case)
    }
}

fn raw_counts(client: &mut impl GenericClient, campaign: CampaignId) -> Vec<i64> {
    [
        "territory_definition_v1",
        "territory_definition_field_v1",
        "territory_tick_manifest_v1",
        "territory_tick_membership_v1",
        "tick_commit",
        "material_tick_v3",
        "graph_node_manifest_v1",
        "event_manifest_v1",
        "world_register_v1",
    ]
    .into_iter()
    .map(|table| {
        client
            .query_one(
                &format!("SELECT count(*) FROM babylon_state.{table} WHERE campaign_id=$1"),
                &[campaign.as_uuid()],
            )
            .unwrap()
            .try_get(0)
            .unwrap()
    })
    .collect()
}

#[test]
#[ignore = "requires task-owned disposable PostgreSQL current schema"]
fn live_territory_sql_guards_refuse_faults_without_durable_changes() {
    let (database, config) = disposable_config("territoryfault");
    let campaign = foundation(&config, 0x40_7e12);
    let mut client = config.connect(NoTls).unwrap();
    let before = raw_counts(&mut client, campaign);
    assert!(
        before[0] > 0,
        "actual foundation seeds admitted territory definitions"
    );
    for &(case, message) in CASES {
        let mut tx = client.transaction().unwrap();
        let error = fault_result(&mut tx, campaign, before[0], case).expect_err(case);
        let database = error.as_db_error().expect("actual PostgreSQL refusal");
        if case == "missing_reference" {
            assert_eq!(database.code(), &SqlState::FOREIGN_KEY_VIOLATION);
            assert_eq!(
                database.constraint(),
                Some("territory_tick_membership_v1_campaign_id_definition_id_fkey")
            );
        } else {
            assert_eq!(database.code(), &SqlState::RAISE_EXCEPTION, "{case}");
            assert_eq!(database.message(), message, "{case}");
        }
        tx.rollback().unwrap();
        assert_eq!(
            raw_counts(&mut client, campaign),
            before,
            "{case} rolled back all new rows"
        );
    }
    drop(client);
    database.cleanup();
}
