//! Current schema admission and durable replay composition.

#[path = "runtime/session.rs"]
mod session;

#[cfg(test)]
pub(crate) use session::BslSqlValue;
pub(crate) use session::{
    bytea_copy_text, capture_campaign_foundation, finish_csv_copy, insert_campaign_foundation_rows,
    insert_typed_tick_pre_marker_rows, reconstruct_graph_foundation_session,
    verify_captured_foundation_components, verify_runtime_schema, verify_runtime_schema_client,
    write_bsl_csv_row, write_csv_row, CapturedCampaignFoundation,
};
pub use session::{
    hydrate_campaign_foundation, prepare_committed_tick, CommittedTickReceipt,
    PreparedCommittedTick, RustPersistenceRuntimeError,
};

#[cfg(test)]
use crate::identity::CampaignId;
#[cfg(test)]
use babylon_bsl::identity_codec::StableBslValue;
#[cfg(test)]
use babylon_bsl::structural_verbs::CollectingSink;
#[cfg(test)]
use babylon_practice_contract::OrderedPracticeActionBatch;
#[cfg(test)]
use babylon_tick::replay_session::{IdentifiedTickReport, ReplayCommitDisposition};
#[cfg(test)]
use postgres::types::ToSql;
#[cfg(test)]
use postgres::GenericClient;

#[cfg(test)]
mod live_tests {
    #[path = "material_open.rs"]
    mod material_open;
    #[path = "territory_controls/controls.rs"]
    mod territory_controls;
    use super::super::postgres_catalog;
    use super::*;
    use crate::material_storage::LookupAnchor;
    use crate::michigan_content::MichiganContentPreset;
    use crate::michigan_material::MichiganDeliveryPreset;
    use crate::michigan_material::MichiganMaterialCatalog;
    use babylon_kernel::content_digest;
    use babylon_tick::material_world::MaterialWorldRegister;
    use postgres::Client;
    use postgres::{Config, NoTls};
    use std::str::FromStr;
    use uuid::Uuid;
    const DSN_ENV: &str = "BABYLON_POSTGRES_TEST_DSN";
    const ACK_ENV: &str = "BABYLON_POSTGRES_DISPOSABLE_ACK";
    const ACK: &str = "I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES";
    const CANARY_ENV: &str = "BABYLON_POSTGRES_DISPOSABLE_CANARY";
    const TEMPLATE_DB_ENV: &str = "BABYLON_RUNTIME_TEMPLATE_DB";
    fn valid_changed_material_receipt(
        owner: &mut Client,
        campaign: CampaignId,
        base: &[u8],
    ) -> Vec<u8> {
        let opening =
            crate::material_storage::seed(base).expect("the fixture seeds the authored rows");
        let mut chain = crate::material_storage::initial_lookup_chain(&opening)
            .expect("the opening register builds its first lookup chain");
        let mut loaded = None;
        let rows=owner.query("SELECT resolve_tick,lookup_delta_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid AND resolve_tick<=2 ORDER BY resolve_tick",&[campaign.as_uuid()]).expect("the seeded rows are readable");
        assert_eq!(rows.len(), 2);
        for (index, row) in rows.iter().enumerate() {
            assert_eq!(
                row.get::<_, i64>(0),
                i64::try_from(index + 1).expect("the fixture value fits the target range")
            );
            loaded = Some(
                crate::material_storage::read_period_lookup(
                    &opening,
                    u64::try_from(index + 1).expect("the fixture value fits the target range"),
                    row.get::<_, &[u8]>(1),
                    LookupAnchor::Previous(chain),
                )
                .expect("the committed lookup table reads"),
            );
            chain = loaded
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .chain;
        }
        let lookup = loaded.expect("the fixture carries the loaded value");
        let row=owner.query_one("SELECT register_storage_bytes,receipt_storage_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid AND resolve_tick=2",&[campaign.as_uuid()]).expect("the seeded row is present exactly once");
        let (register, mut receipts) = crate::material_storage::decode(
            &opening,
            2,
            row.get::<_, &[u8]>(0),
            row.get::<_, &[u8]>(1),
            &lookup.lookup,
            lookup.chain,
        )
        .expect("the committed canonical bytes decode");
        let original_digest = content_digest::sha256_of(&receipts);
        let decoded = babylon_tick::material_world::decode_material_receipts(&receipts)
            .expect("the canonical bytes decode into the declared type");
        // Family1 retains exact planned batches; increasing the first plan keeps
        // produced<=planned and all physical quantities/identity joins admissible.
        let planned = decoded
            .production
            .first()
            .expect("the fixture sequence is non-empty")
            .planned_batches
            .checked_add(1)
            .expect("the fixture arithmetic stays in range");
        let offset = b"babylon.material-tick-receipts.v16\0".len() + 4 + 8 + 1 + 8 + 32 + 32;
        receipts[offset..offset + 8].copy_from_slice(&planned.to_be_bytes());
        assert_ne!(content_digest::sha256_of(&receipts), original_digest);
        babylon_tick::material_world::decode_material_receipts(&receipts)
            .expect("the canonical bytes decode into the declared type");
        let register =
            MaterialWorldRegister::decode(&register).expect("the committed canonical bytes decode");
        let encoded =
            crate::material_storage::encode(&register, &receipts, &opening, lookup.previous_chain)
                .expect("the fixture value encodes canonically");
        assert_eq!(encoded.lookup.entries(), lookup.lookup.entries());
        assert_eq!(
            crate::material_storage::decode(
                &opening,
                2,
                &encoded.register_storage_bytes,
                &encoded.receipt_storage_bytes,
                &encoded.lookup,
                encoded.lookup_chain,
            )
            .expect("the committed canonical bytes decode")
            .1,
            receipts
        );
        encoded.receipt_storage_bytes
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_material_commit_loss_reconciles_only_the_complete_persisted_candidate() {
        use crate::material_runtime::{CommitFault, DurableMaterialRuntime, COMMIT_FAULT};
        let base = validated_base_config();
        let database = TestDatabase::create_from_template(
            &base,
            &validated_template_name(),
            "materialcommitloss",
        );
        let config = database.config(&base);
        let catalog = MichiganMaterialCatalog::from_defines_toml(include_str!(
            "../../../../content/scenarios/michigan/defines.toml"
        ))
        .expect("the authored input admits the derived value");
        let foundation = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&catalog)
            .expect("the authored catalog builds the foundation");
        let digest = foundation.digest();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0033_0c01_1055));
        let mut runtime = DurableMaterialRuntime::create(&config, campaign, foundation)
            .expect("the test database creates the fixture campaign");
        let before = runtime.session().material().canonical_bytes().to_vec();
        let mut sink = CollectingSink::default();
        let actions = OrderedPracticeActionBatch::empty(
            runtime.session().graph_session().session_identity().clone(),
            1,
        )
        .expect("the empty authored batch constructs");
        COMMIT_FAULT.with(|slot| slot.set(Some(CommitFault::BeforeCommit)));
        assert!(runtime.advance_and_commit(&mut sink, &actions).is_err());
        assert_eq!(runtime.session().completed_tick(), 0);
        assert_eq!(runtime.session().material().canonical_bytes(), before);
        assert!(runtime.diagnostic_receipt().is_none());
        assert!(sink.events.is_empty());
        let mut owner = config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let count: i64 = owner
            .query_one(
                "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid",
                &[campaign.as_uuid()],
            )
            .expect("the seeded row is present exactly once")
            .get(0);
        assert_eq!(count, 0);
        // Retry the exact action after rollback, then lose the next COMMIT acknowledgement.
        runtime
            .advance_and_commit(&mut sink, &actions)
            .expect("the prepared tick advances and commits");
        let mut stale = DurableMaterialRuntime::open(&config, campaign, digest)
            .expect("the fixture opens the authored source");
        let actions = OrderedPracticeActionBatch::empty(
            runtime.session().graph_session().session_identity().clone(),
            2,
        )
        .expect("the empty authored batch constructs");
        COMMIT_FAULT.with(|slot| slot.set(Some(CommitFault::AfterCommit)));
        let identity = runtime
            .advance_and_commit(&mut sink, &actions)
            .expect("the prepared tick advances and commits");
        assert_eq!(
            runtime
                .diagnostic_receipt()
                .expect("the fixture call `diagnostic_receipt` succeeds for the authored inputs")
                .commit_disposition(),
            ReplayCommitDisposition::ReconciledAfterAmbiguousCommit
        );
        let reopened = DurableMaterialRuntime::open(&config, campaign, digest)
            .expect("the fixture opens the authored source");
        assert_eq!(reopened.tail(), Some(&identity));
        assert_eq!(
            reopened.session().material().canonical_bytes(),
            runtime.session().material().canonical_bytes()
        );
        let count: i64 = owner
            .query_one(
                "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid",
                &[campaign.as_uuid()],
            )
            .expect("the seeded row is present exactly once")
            .get(0);
        assert_eq!(count, 2);
        let original:Vec<u8>=owner.query_one("SELECT receipt_storage_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid AND resolve_tick=2",&[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0);
        let corrupt = valid_changed_material_receipt(&mut owner, campaign, &before);
        owner.execute("UPDATE babylon_state.material_tick_v3 SET receipt_storage_bytes=$2 WHERE campaign_id=$1::uuid AND resolve_tick=2",&[campaign.as_uuid(),&corrupt]).expect("the test database applies the setup statement");
        let mut refused_sink = CollectingSink::default();
        assert!(stale
            .advance_and_commit(&mut refused_sink, &actions)
            .is_err());
        assert_eq!(stale.session().completed_tick(), 1);
        assert!(refused_sink.events.is_empty());
        owner.execute("UPDATE babylon_state.material_tick_v3 SET receipt_storage_bytes=$2 WHERE campaign_id=$1::uuid AND resolve_tick=2", &[campaign.as_uuid(), &original]).expect("the test database applies the setup statement");
        assert_eq!(
            stale
                .advance_and_commit(&mut refused_sink, &actions)
                .expect("the prepared tick advances and commits"),
            identity
        );
        drop(owner);
        drop(reopened);
        drop(stale);
        drop(runtime);
        database.cleanup();
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    #[allow(
        clippy::too_many_lines,
        reason = "`live_bsl_csv_copy_preserves_numeric_extremes_nulls_and_stable_keys` keeps one authored boundary's fixture and assertions together"
    )]
    fn live_bsl_csv_copy_preserves_numeric_extremes_nulls_and_stable_keys() {
        use babylon_graph::stable_element::StableElementKey;
        let base = validated_base_config();
        let database =
            TestDatabase::create_from_template(&base, &validated_template_name(), "copyvalues");
        let config = database.config(&base);
        let node = StableElementKey::Node {
            scenario: "production/copy".to_owned(),
            local_name: "source".to_owned(),
        };
        let values = [
            StableBslValue::Int(i64::MIN),
            StableBslValue::Int(i64::MAX),
            StableBslValue::CurrencyMicroUnits(i128::MIN),
            StableBslValue::CurrencyMicroUnits(i128::MAX),
            StableBslValue::RealBits((-0.25_f64).to_bits()),
            StableBslValue::RatioBits {
                value: 0.5_f64.to_bits(),
                floor: None,
                cap: Some(1.0_f64.to_bits()),
            },
            StableBslValue::RatioBits {
                value: 0.5_f64.to_bits(),
                floor: Some(0.0_f64.to_bits()),
                cap: None,
            },
            StableBslValue::Bool(false),
            StableBslValue::Bool(true),
            StableBslValue::Enum {
                enum_type: "OrganizationKind".to_owned(),
                member: "COLLECTIVE".to_owned(),
            },
            StableBslValue::Node(node),
            StableBslValue::Hyperedge(StableElementKey::Hyperedge {
                scenario: "production/copy".to_owned(),
                local_name: "assembly".to_owned(),
            }),
            StableBslValue::Edge(StableElementKey::Edge {
                scenario: "production/copy".to_owned(),
                edge_type: "production/links".to_owned(),
                source_local_name: "source".to_owned(),
                target_local_name: "target".to_owned(),
            }),
        ];
        let mut client = config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let mut tx = client
            .transaction()
            .expect("the test database opens a transaction");
        let mut writer = tx.copy_in(
            "COPY babylon_state.organization_state_v1 \
             (campaign_id,resolve_tick,organization_id,organization_kind_tag,organization_kind_int, \
              organization_kind_currency,organization_kind_real_bits,organization_kind_ratio_bits, \
              organization_kind_ratio_min_bits,organization_kind_ratio_max_bits,organization_kind_bool, \
              organization_kind_enum_type,organization_kind_enum_member,organization_kind_stable_key) \
             FROM STDIN WITH (FORMAT csv)",
        ).expect("the fixture call `copy_in` succeeds for the authored inputs");
        for (index, value) in values.iter().enumerate() {
            let id = session::bytea_copy_text(&index.to_be_bytes());
            session::write_bsl_csv_row(
                &mut writer,
                &["00000000-0000-0000-0000-000000000001", "1", &id],
                value,
                "copy value proof",
            )
            .expect("the fixture sink accepts the authored bytes");
        }
        session::finish_csv_copy(writer, values.len(), "finish value proof")
            .expect("the fixture call `finish_csv_copy` succeeds for the authored inputs");
        for (index, value) in values.iter().enumerate() {
            let row = tx.query_one(
                "SELECT organization_kind_tag,organization_kind_int,organization_kind_currency::text, \
                 organization_kind_real_bits,organization_kind_ratio_bits,organization_kind_ratio_min_bits, \
                 organization_kind_ratio_max_bits,organization_kind_bool,organization_kind_enum_type, \
                 organization_kind_enum_member,organization_kind_stable_key \
                 FROM babylon_state.organization_state_v1 WHERE organization_id=$1", &[&&index.to_be_bytes()[..]],
            ).expect("the seeded row is present exactly once");
            let expected = BslSqlValue::from_stable(value)
                .expect("the authored input admits the derived value");
            assert_eq!(row.get::<_, i16>(0), expected.tag);
            assert_eq!(row.get::<_, Option<i64>>(1), expected.int_value);
            assert_eq!(row.get::<_, Option<String>>(2), expected.currency_value);
            assert_eq!(row.get::<_, Option<i64>>(3), expected.real_bits);
            assert_eq!(row.get::<_, Option<i64>>(4), expected.ratio_bits);
            assert_eq!(row.get::<_, Option<i64>>(5), expected.ratio_min_bits);
            assert_eq!(row.get::<_, Option<i64>>(6), expected.ratio_max_bits);
            assert_eq!(row.get::<_, Option<bool>>(7), expected.bool_value);
            assert_eq!(row.get::<_, Option<String>>(8), expected.enum_type);
            assert_eq!(row.get::<_, Option<String>>(9), expected.enum_member);
            assert_eq!(row.get::<_, Option<Vec<u8>>>(10), expected.stable_key);
        }
        tx.rollback().expect("the open transaction rolls back");
        let count: i64 = client
            .query_one(
                "SELECT count(*) FROM babylon_state.organization_state_v1",
                &[],
            )
            .expect("the seeded row is present exactly once")
            .get(0);
        assert_eq!(
            count, 0,
            "COPY rows retain the enclosing transaction's rollback boundary"
        );
        database.cleanup();
    }
    fn event_control_config() -> Config {
        let mut config = validated_base_config();
        let database =
            std::env::var("BABYLON_EVENT_COPY_DATABASE").expect("the fixture variable is bound");
        assert!(database.starts_with("per337_event_continuity_"));
        config.dbname(&database);
        config
    }

    fn event_control_runtime(
        config: &Config,
        suffix: u128,
    ) -> crate::material_runtime::DurableMaterialRuntime {
        let foundation = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation");
        let campaign = CampaignId::from_uuid(Uuid::from_u128(
            (u128::from(std::process::id()) << 64) | suffix,
        ));
        crate::material_runtime::DurableMaterialRuntime::create(config, campaign, foundation)
            .expect("the test database creates the fixture campaign")
    }

    const EVENT_RAW_TABLES: [&str; 10] = [
        "event_text_lookup_v1",
        "event_key_lookup_v1",
        "event_manifest_v1",
        "event_parent_chunk_v1",
        "event_field_chunk_v1",
        "tick_commit",
        "material_tick_v3",
        "graph_node_manifest_v1",
        "territory_tick_manifest_v1",
        "territory_tick_membership_v1",
    ];

    fn event_raw_counts(client: &mut impl GenericClient, campaign: CampaignId) -> Vec<i64> {
        EVENT_RAW_TABLES
            .iter()
            .map(|relation| {
                client
                    .query_one(
                        &format!(
                            "SELECT count(*) FROM babylon_state.{relation} WHERE campaign_id=$1"
                        ),
                        &[campaign.as_uuid()],
                    )
                    .expect("the seeded row is present exactly once")
                    .get(0)
            })
            .collect()
    }

    fn event_snapshot(
        client: &mut impl GenericClient,
        campaign: CampaignId,
        relations: [&str; 2],
    ) -> [String; 2] {
        std::array::from_fn(|index| {
            let ordering = if index == 0 {
                "ordinal"
            } else {
                "ordinal,position"
            };
            client.query_one(&format!("SELECT coalesce(jsonb_agg(to_jsonb(e) ORDER BY {ordering}),'[]'::jsonb)::text FROM {} e WHERE campaign_id=$1", relations[index]),
                &[campaign.as_uuid()]).expect("the seeded row is present exactly once").get(0)
        })
    }

    fn event_reference_tables(client: &mut impl GenericClient) {
        client.batch_execute("CREATE TEMP TABLE event_parent_reference (
            campaign_id uuid,resolve_tick bigint,ordinal bigint,event_type text COLLATE pg_catalog.\"C\",emitting_rule text COLLATE pg_catalog.\"C\",choice_receipt_ordinal bigint
        ) ON COMMIT DROP;
        CREATE TEMP TABLE event_field_reference (
            campaign_id uuid,resolve_tick bigint,ordinal bigint,position bigint,field_name text COLLATE pg_catalog.\"C\",value_tag smallint,int_value bigint,
            currency_value numeric(39,0),real_bits bigint,ratio_bits bigint,ratio_min_bits bigint,ratio_max_bits bigint,bool_value boolean,
            enum_type text COLLATE pg_catalog.\"C\",enum_member text COLLATE pg_catalog.\"C\",stable_key bytea
        ) ON COMMIT DROP").expect("the test database applies the schema statements");
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_event_copy_matches_reference_rows_and_rolls_back() {
        let config = event_control_config();
        let mut runtime = event_control_runtime(&config, 0x337_c0f1);
        let campaign = runtime.campaign_id();
        let actions = OrderedPracticeActionBatch::empty(
            runtime.session().graph_session().session_identity().clone(),
            1,
        )
        .expect("the empty authored batch constructs");
        let mut client = config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let before = event_raw_counts(&mut client, campaign);
        let expected = {
            let candidate = runtime
                .session()
                .prepare_advance(&actions)
                .expect("the session prepares the authored advance");
            let report = candidate.graph_report();
            assert!(!report.successful_event_batch().events().is_empty());
            let mut reference = client
                .transaction()
                .expect("the test database opens a transaction");
            event_reference_tables(&mut reference);
            insert_event_rows_reference(&mut reference, campaign, 1, report)
                .expect("the test database accepts the authored row");
            let expected = event_snapshot(
                &mut reference,
                campaign,
                [
                    "pg_temp.event_parent_reference",
                    "pg_temp.event_field_reference",
                ],
            );
            reference
                .rollback()
                .expect("the open transaction rolls back");
            let mut copied = client
                .transaction()
                .expect("the test database opens a transaction");
            session::insert_choice_receipt_rows(&mut copied, campaign, 1, report)
                .expect("the test database accepts the authored row");
            session::insert_typed_event_rows(&mut copied, campaign, 1, report)
                .expect("the test database accepts the authored row");
            assert_eq!(
                event_snapshot(
                    &mut copied,
                    campaign,
                    [
                        "babylon_state.event_parent_expanded_v1",
                        "babylon_state.event_field_expanded_v1"
                    ]
                ),
                expected
            );
            assert_eq!(
                event_snapshot(
                    &mut copied,
                    campaign,
                    [
                        "babylon_state.tick_event_v2",
                        "babylon_state.tick_event_field_v2"
                    ]
                ),
                ["[]".to_owned(), "[]".to_owned()]
            );
            copied.rollback().expect("the open transaction rolls back");
            expected
        };
        assert_eq!(event_raw_counts(&mut client, campaign), before);
        let mut sink = CollectingSink::default();
        runtime
            .advance_and_commit(&mut sink, &actions)
            .expect("the prepared tick advances and commits");
        assert_eq!(runtime.session().completed_tick(), 1);
        assert_eq!(
            event_snapshot(
                &mut client,
                campaign,
                [
                    "babylon_state.tick_event_v2",
                    "babylon_state.tick_event_field_v2"
                ]
            ),
            expected
        );
    }

    fn insert_event_fixture(
        client: &mut impl GenericClient,
        campaign: CampaignId,
        event_ordinal: i64,
        field_position: Option<i64>,
    ) {
        let text_id: i64 = client
            .query_one(
                "SELECT count(*) FROM babylon_state.event_text_lookup_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()],
            )
            .expect("the seeded row is present exactly once")
            .get(0);
        client.execute("INSERT INTO babylon_state.event_text_lookup_v1(campaign_id,text_id,first_tick,value) VALUES($1,$2,1,'continuity-proof'),($1,$3,1,'proof')", &[campaign.as_uuid(),&text_id,&(text_id+1)]).expect("the test database applies the setup statement");
        let fields = i64::from(field_position.is_some());
        client
            .execute(
                "INSERT INTO babylon_state.event_manifest_v1 VALUES($1,1,1,$2,1,$2)",
                &[campaign.as_uuid(), &fields],
            )
            .expect("the test database applies the setup statement");
        client.execute("INSERT INTO babylon_state.event_parent_chunk_v1 VALUES($1,1,0,ARRAY[$2::bigint],ARRAY[$3::bigint],ARRAY[$3::bigint],ARRAY[NULL::bigint])", &[campaign.as_uuid(),&event_ordinal,&text_id]).expect("the test database applies the setup statement");
        if let Some(position) = field_position {
            client.execute("INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values) VALUES($1,1,0,1,ARRAY[$2::bigint],ARRAY[$3::bigint],ARRAY[$4::bigint],ARRAY[7::bigint])", &[campaign.as_uuid(),&event_ordinal,&position,&(text_id+1)]).expect("the test database applies the setup statement");
        }
    }

    fn insert_event_test_marker(client: &mut impl GenericClient, campaign: CampaignId) {
        // This rollback-only event fixture deliberately has no territory rows.
        client
            .execute(
                "INSERT INTO babylon_state.territory_tick_manifest_v1 (campaign_id,resolve_tick,territory_count) VALUES($1,1,0)",
                &[campaign.as_uuid()],
            )
            .expect("the test database applies the setup statement");
        client.execute("INSERT INTO babylon_state.material_tick_v3(campaign_id,resolve_tick,identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes) VALUES($1,1,$2,$2,$2,$2)", &[campaign.as_uuid(),&&[1_u8;32][..]]).expect("the test database applies the setup statement");
        client
            .execute(
                "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES($1,1,0,0,0,0)",
                &[campaign.as_uuid()],
            )
            .expect("the test database applies the setup statement");
        client
            .execute(
                "INSERT INTO babylon_state.tick_commit VALUES($1,1,3,$2,$2)",
                &[campaign.as_uuid(), &&[1_u8; 32][..]],
            )
            .expect("the test database applies the setup statement");
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_event_marker_continuity_is_atomic_and_immutable() {
        let config = event_control_config();
        let mut runtime = event_control_runtime(&config, 0x337_ce11);
        let campaign = runtime.campaign_id();
        let mut client = config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let before = event_raw_counts(&mut client, campaign);
        for (ordinal, position) in [(1, Some(0)), (0, Some(1))] {
            let mut tx = client
                .transaction()
                .expect("the test database opens a transaction");
            insert_event_fixture(&mut tx, campaign, ordinal, position);
            insert_event_test_marker(&mut tx, campaign);
            let error = tx
                .commit()
                .expect_err("the fixture call `commit` fails for the authored inputs");
            assert_eq!(
                error
                    .as_db_error()
                    .expect("the runtime error is a database error")
                    .message(),
                "event_storage_parent_field_choice_or_order"
            );
            assert_eq!(event_raw_counts(&mut client, campaign), before);
        }
        // The SQL-only empty-field parent is checked, then rolled back; its
        // placeholder material bytes never become a durable engine publication.
        let mut valid = client
            .transaction()
            .expect("the test database opens a transaction");
        insert_event_fixture(&mut valid, campaign, 0, None);
        insert_event_test_marker(&mut valid, campaign);
        valid
            .batch_execute("SET CONSTRAINTS ALL IMMEDIATE")
            .expect("the test database applies the schema statements");
        valid.rollback().expect("the open transaction rolls back");
        assert_eq!(event_raw_counts(&mut client, campaign), before);
        let actions = OrderedPracticeActionBatch::empty(
            runtime.session().graph_session().session_identity().clone(),
            1,
        )
        .expect("the empty authored batch constructs");
        runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .expect("the prepared tick advances and commits");
        assert_event_raw_history_immutable(&mut client, campaign);
    }

    fn assert_event_raw_history_immutable(client: &mut Client, campaign: CampaignId) {
        let before = event_raw_counts(client, campaign);
        for relation in &EVENT_RAW_TABLES[..5] {
            for operation in ["UPDATE", "DELETE"] {
                let mut tx = client
                    .transaction()
                    .expect("the test database opens a transaction");
                let sql = if operation == "UPDATE" {
                    format!("UPDATE babylon_state.{relation} SET campaign_id=campaign_id WHERE campaign_id=$1")
                } else {
                    format!("DELETE FROM babylon_state.{relation} WHERE campaign_id=$1")
                };
                let error = tx
                    .execute(&sql, &[campaign.as_uuid()])
                    .expect_err("the test database refuses the invalid statement");
                assert_eq!(
                    error
                        .as_db_error()
                        .expect("the runtime error is a database error")
                        .message(),
                    "event_storage_append_only"
                );
                tx.rollback().expect("the open transaction rolls back");
            }
        }
        let mut tx = client
            .transaction()
            .expect("the test database opens a transaction");
        let error=tx.execute("INSERT INTO babylon_state.event_parent_chunk_v1 VALUES($1,1,999999,ARRAY[0::bigint],ARRAY[0::bigint],ARRAY[0::bigint],ARRAY[NULL::bigint])", &[campaign.as_uuid()]).expect_err("the test database refuses the invalid statement");
        assert_eq!(
            error
                .as_db_error()
                .expect("the runtime error is a database error")
                .message(),
            "tick_event_v2_refused_marked_history_mutation"
        );
        tx.rollback().expect("the open transaction rolls back");
        assert_eq!(event_raw_counts(client, campaign), before);
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_event_arrays_refuse_shape_null_and_inactive_lanes_atomically() {
        let config = event_control_config();
        let runtime = event_control_runtime(&config, 0x337_a221);
        let campaign = runtime.campaign_id();
        let mut client = config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let before = event_raw_counts(&mut client, campaign);
        for statement in [
            "INSERT INTO babylon_state.event_parent_chunk_v1 VALUES($1,1,0,ARRAY[0::bigint],'{}'::bigint[],ARRAY[$2::bigint],ARRAY[NULL::bigint])",
            "INSERT INTO babylon_state.event_parent_chunk_v1 VALUES($1,1,0,'[0:0]={0}'::bigint[],ARRAY[$2::bigint],ARRAY[$2::bigint],ARRAY[NULL::bigint])",
            "INSERT INTO babylon_state.event_parent_chunk_v1 VALUES($1,1,0,ARRAY[NULL::bigint],ARRAY[$2::bigint],ARRAY[$2::bigint],ARRAY[NULL::bigint])",
            "INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values) VALUES($1,1,0,1,ARRAY[0::bigint],ARRAY[0::bigint],ARRAY[$2::bigint],ARRAY[NULL::bigint])",
            "INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values,currency_values) VALUES($1,1,0,1,ARRAY[0::bigint],ARRAY[0::bigint],ARRAY[$2::bigint],ARRAY[7::bigint],ARRAY[7::numeric])",
        ] {
            let mut tx=client.transaction().expect("the test database opens a transaction");
            let error=tx.execute(statement,&[campaign.as_uuid(),&0_i64]).expect_err("the test database refuses the invalid statement");
            assert_eq!(error.code(),Some(&postgres::error::SqlState::CHECK_VIOLATION));
            tx.rollback().expect("the open transaction rolls back");
            assert_eq!(event_raw_counts(&mut client,campaign),before);
        }
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_event_marker_refuses_chunk_gap_missing_choice_and_orphan_field() {
        let config = event_control_config();
        let runtime = event_control_runtime(&config, 0x337_a222);
        let campaign = runtime.campaign_id();
        let mut client = config
            .connect(NoTls)
            .expect("the test database accepts the connection");
        let before = event_raw_counts(&mut client, campaign);
        for (chunk, choice, field_ordinal, expected) in [
            (1, None, 0, "event_storage_parent_chunk_count_or_gap"),
            (
                0,
                Some(0_i64),
                0,
                "event_storage_parent_field_choice_or_order",
            ),
            (0, None, 1, "event_storage_parent_field_choice_or_order"),
        ] {
            let mut tx = client
                .transaction()
                .expect("the test database opens a transaction");
            let text_id: i64 = tx
                .query_one(
                    "SELECT count(*) FROM babylon_state.event_text_lookup_v1 WHERE campaign_id=$1",
                    &[campaign.as_uuid()],
                )
                .expect("the seeded row is present exactly once")
                .get(0);
            tx.execute("INSERT INTO babylon_state.event_text_lookup_v1(campaign_id,text_id,first_tick,value) VALUES($1,$2,1,'guard-proof')", &[campaign.as_uuid(),&text_id]).expect("the test database applies the setup statement");
            tx.execute(
                "INSERT INTO babylon_state.event_manifest_v1 VALUES($1,1,1,1,1,1)",
                &[campaign.as_uuid()],
            )
            .expect("the test database applies the setup statement");
            tx.execute("INSERT INTO babylon_state.event_parent_chunk_v1 VALUES($1,1,$2,ARRAY[0::bigint],ARRAY[$3::bigint],ARRAY[$3::bigint],ARRAY[$4::bigint])", &[campaign.as_uuid(),&i64::from(chunk),&text_id,&choice]).expect("the test database applies the setup statement");
            tx.execute("INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values) VALUES($1,1,0,1,ARRAY[$2::bigint],ARRAY[0::bigint],ARRAY[$3::bigint],ARRAY[7::bigint])", &[campaign.as_uuid(),&i64::from(field_ordinal),&text_id]).expect("the test database applies the setup statement");
            insert_event_test_marker(&mut tx, campaign);
            let error = tx
                .commit()
                .expect_err("the fixture call `commit` fails for the authored inputs");
            assert_eq!(
                error
                    .as_db_error()
                    .expect("the runtime error is a database error")
                    .message(),
                expected
            );
            assert_eq!(event_raw_counts(&mut client, campaign), before);
        }
    }

    fn insert_event_rows_reference(
        client: &mut impl GenericClient,
        campaign_id: CampaignId,
        resolve_tick: i64,
        report: &IdentifiedTickReport,
    ) -> Result<(), RustPersistenceRuntimeError> {
        for (ordinal, event) in report.successful_event_batch().events().iter().enumerate() {
            let ordinal = i64::try_from(ordinal).map_err(|_| {
                RustPersistenceRuntimeError::IntegerConversion {
                    field: "successful event ordinal",
                    value: ordinal,
                }
            })?;
            let choice_receipt_ordinal = event
                .choice_receipt()
                .map(|reference| i64::from(reference.encounter_ordinal()));
            session::require_single_insert(
                client.execute(
                    "INSERT INTO pg_temp.event_parent_reference \
                 (campaign_id, resolve_tick, ordinal, event_type, emitting_rule, \
                  choice_receipt_ordinal) VALUES ($1::uuid, $2, $3, $4, $5, $6)",
                    &[
                        campaign_id.as_uuid(),
                        &resolve_tick,
                        &ordinal,
                        &event.event_type(),
                        &event.emitting_rule(),
                        &choice_receipt_ordinal,
                    ],
                ),
                "insert tick event",
            )?;
            for (position, (field_name, value)) in event.fields().iter().enumerate() {
                let position = i64::from(session::checked_u32_position(position)?);
                let prefix: [&(dyn ToSql + Sync); 5] = [
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    &ordinal,
                    &position,
                    field_name,
                ];
                session::insert_bsl_value_row(
                client,
                "INSERT INTO pg_temp.event_field_reference \
                 (campaign_id, resolve_tick, ordinal, position, field_name, value_tag, int_value, \
                  currency_value, real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, \
                  enum_type, enum_member, stable_key) \
                 VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::text::numeric, $9, $10, $11, $12, $13, $14, $15, $16)",
                &prefix,
                value,
                "insert tick event field",
            )?;
            }
        }
        Ok(())
    }

    fn validated_base_config() -> Config {
        assert_eq!(std::env::var(ACK_ENV).as_deref(), Ok(ACK));
        let canary = std::env::var(CANARY_ENV).expect("runner supplies the disposable canary");
        assert_eq!(canary.len(), 32);
        let dsn = std::env::var(DSN_ENV).expect("runner supplies the disposable DSN");
        let config = Config::from_str(&dsn).expect("runner DSN parses");
        postgres_catalog::validate_connection_target(&config).expect("loopback target");
        assert_eq!(config.get_user(), Some("test"));
        assert_eq!(config.get_dbname(), Some("postgres"));
        let actual: Option<String> = config
            .connect(NoTls)
            .expect("canary connection")
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.disposable_runtime', true)",
                &[],
            )
            .expect("canary query")
            .try_get(0)
            .expect("canary decode");
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        config
    }
    fn validated_template_name() -> String {
        let template = std::env::var(TEMPLATE_DB_ENV)
            .expect("runner supplies the validated Rust-active template database");
        let suffix = template
            .strip_prefix("per281_runtime_template_")
            .expect("runtime template uses the task-owned prefix");
        assert_eq!(suffix.len(), 12);
        assert!(suffix
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte)));
        assert!(template
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_'));
        template
    }
    struct TestDatabase {
        name: String,
        admin: Config,
        active: bool,
    }

    impl TestDatabase {
        fn config(&self, base: &Config) -> Config {
            let mut config = base.clone();
            config.dbname(&self.name);
            config
        }

        fn create_from_template(base: &Config, template: &str, label: &str) -> Self {
            assert!(label.bytes().all(|byte| byte.is_ascii_lowercase()));
            assert!(template
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_'));
            let name = format!("per281_runtime_{label}_{}", std::process::id());
            let mut admin = base.clone();
            admin.dbname("postgres");
            let sql = format!("CREATE DATABASE \"{name}\" OWNER test TEMPLATE \"{template}\"");
            admin
                .connect(NoTls)
                .expect("admin connection")
                .batch_execute(&sql)
                .expect("runtime clone creation");
            let database = Self {
                name,
                admin,
                active: true,
            };
            session::verify_runtime_schema(&database.config(base))
                .expect("current schema authority");
            database
        }

        fn cleanup(mut self) {
            self.try_drop_database()
                .expect("runtime test database cleanup");
            self.active = false;
        }

        fn try_drop_database(&self) -> Result<(), ()> {
            let sql = format!("DROP DATABASE IF EXISTS \"{}\" WITH (FORCE)", self.name);
            self.admin
                .connect(NoTls)
                .map_err(|_| ())?
                .batch_execute(&sql)
                .map_err(|_| ())
        }
    }

    impl Drop for TestDatabase {
        fn drop(&mut self) {
            if !self.active {
                return;
            }
            if std::thread::panicking() {
                let _cleanup = self.try_drop_database();
                return;
            }
            self.try_drop_database()
                .expect("runtime test database cleanup");
            self.active = false;
        }
    }
}
