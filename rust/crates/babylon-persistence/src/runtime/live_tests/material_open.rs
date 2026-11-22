//! Open must release its SQL snapshot before reconstructing material authority.
use super::{CampaignId, CollectingSink, NoTls, OrderedPracticeActionBatch, TestDatabase};
use crate::material_runtime;
use crate::material_runtime::{DurableMaterialRuntime, FoundationReadSource, MaterialRuntimeError};
use crate::michigan_content::MichiganContentPreset;
use postgres::{Config, Row};
use std::time::Duration;
use uuid::Uuid;

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn live_material_open_reconstructs_after_releasing_its_snapshot() {
    let base = super::validated_base_config();
    let database = TestDatabase::create_from_template(
        &base,
        &super::validated_template_name(),
        "materialopen",
    );
    let mut config = database.config(&base);
    let application = format!("material-open-control-{}", std::process::id());
    config.application_name(&application);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x342_0fe0));
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation_for_campaign(&crate::test_support::catalog(), campaign)
        .expect("the authored catalog builds the campaign foundation");
    let digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(&config, campaign, foundation)
        .expect("the test database creates the fixture campaign");
    for tick in 0..=2 {
        let reopened = DurableMaterialRuntime::open_with_foundation_admission(
            &config,
            campaign,
            |snapshot| {
                snapshot.batch_execute("SET LOCAL idle_in_transaction_session_timeout='100ms'")?;
                let captured = material_runtime::capture_material_foundation_components(
                    snapshot,
                    campaign,
                    digest,
                    FoundationReadSource::Runtime,
                )?;
                Ok((captured, ()))
            },
            |captured, ()| {
                let mut observer = config
                    .connect(NoTls)
                    .expect("the test database accepts the connection");
                let state = observer
                    .query_one(
                        "SELECT count(*),bool_and(state='idle' AND xact_start IS NULL) \
                     FROM pg_catalog.pg_stat_activity WHERE datname=pg_catalog.current_database() \
                     AND application_name=$1 AND pid<>pg_catalog.pg_backend_pid()",
                        &[&application],
                    )
                    .expect("the seeded row is present exactly once");
                assert_eq!(state.get::<_, i64>(0), 1);
                assert!(
                    state.get::<_, bool>(1),
                    "Open reconstruction still owns a SQL snapshot"
                );
                std::thread::sleep(Duration::from_millis(250));
                captured.admit()
            },
        )
        .expect("the fixture opens the admitted foundation");
        assert_eq!(reopened.session().completed_tick(), tick);
        assert_eq!(reopened.tail(), runtime.tail());
        assert_eq!(
            reopened
                .session()
                .current_world_hash()
                .expect("the committed session publishes a world hash"),
            runtime
                .session()
                .current_world_hash()
                .expect("the committed session publishes a world hash")
        );
        assert_eq!(
            reopened.session().material().canonical_bytes(),
            runtime.session().material().canonical_bytes()
        );
        drop(reopened);
        if tick < 2 {
            let actions = OrderedPracticeActionBatch::empty(
                runtime.session().graph_session().session_identity().clone(),
                tick + 1,
            )
            .expect("the empty authored batch constructs");
            runtime
                .advance_and_commit(&mut CollectingSink::default(), &actions)
                .expect("the prepared tick advances and commits");
        }
    }
    drop(runtime);
    database.cleanup();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn live_material_open_refuses_a_changed_foundation_or_committed_tail() {
    let base = super::validated_base_config();
    let database =
        TestDatabase::create_from_template(&base, &super::validated_template_name(), "opendrift");
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x342_0fe1));
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation_for_campaign(&crate::test_support::catalog(), campaign)
        .expect("the authored catalog builds the campaign foundation");
    let digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(&config, campaign, foundation)
        .expect("the test database creates the fixture campaign");
    for field in ["rng_seed", "geography_scope", "tail"] {
        let result = DurableMaterialRuntime::open_with_foundation_admission(
            &config,
            campaign,
            |snapshot| {
                material_runtime::capture_material_foundation_components(
                    snapshot,
                    campaign,
                    digest,
                    FoundationReadSource::Runtime,
                )
                .map(|captured| (captured, ()))
            },
            |captured, ()| {
                let admitted = captured.admit()?;
                let mut writer = config
                    .connect(NoTls)
                    .expect("the test database accepts the connection");
                match field {
                    "rng_seed" => {
                        writer.execute("UPDATE babylon_state.campaign_foundation SET rng_seed=rng_seed+1 WHERE campaign_id=$1", &[campaign.as_uuid()]).expect("the test database applies the setup statement");
                    }
                    "geography_scope" => {
                        writer.execute("UPDATE babylon_state.campaign SET geography_scope='national-counties' WHERE campaign_id=$1", &[campaign.as_uuid()]).expect("the test database applies the setup statement");
                    }
                    "tail" => {
                        let actions = OrderedPracticeActionBatch::empty(
                            runtime.session().graph_session().session_identity().clone(),
                            1,
                        )
                        .expect("the empty authored batch constructs");
                        runtime
                            .advance_and_commit(&mut CollectingSink::default(), &actions)
                            .expect("the prepared tick advances and commits");
                    }
                    _ => unreachable!(),
                }
                Ok(admitted)
            },
        );
        if field == "tail" {
            assert!(matches!(result, Err(MaterialRuntimeError::TailConflict)));
        } else {
            assert!(matches!(
                result,
                Err(MaterialRuntimeError::FoundationMismatch)
            ));
            let mut writer = config
                .connect(NoTls)
                .expect("the test database accepts the connection");
            if field == "rng_seed" {
                writer.execute("UPDATE babylon_state.campaign_foundation SET rng_seed=rng_seed-1 WHERE campaign_id=$1", &[campaign.as_uuid()]).expect("the test database applies the setup statement");
            } else {
                writer.execute("UPDATE babylon_state.campaign SET geography_scope='michigan-control' WHERE campaign_id=$1", &[campaign.as_uuid()]).expect("the test database applies the setup statement");
            }
            assert_eq!(runtime.session().completed_tick(), 0);
        }
    }
    assert_eq!(runtime.session().completed_tick(), 1);
    drop(runtime);
    database.cleanup();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn live_capture_fingerprint_distinguishes_raw_values_types_nulls_and_order() {
    let config = super::validated_base_config();
    let mut client = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let first = client
        .query_one("SELECT 1::int4 AS value", &[])
        .expect("the seeded row is present exactly once");
    let equal = client
        .query_one("SELECT 1::int4 AS value", &[])
        .expect("the seeded row is present exactly once");
    let changed = client
        .query_one("SELECT 2::int4 AS value", &[])
        .expect("the seeded row is present exactly once");
    let changed_type = client
        .query_one("SELECT 1::int8 AS value", &[])
        .expect("the seeded row is present exactly once");
    let changed_name = client
        .query_one("SELECT 1::int4 AS other", &[])
        .expect("the seeded row is present exactly once");
    let null = client
        .query_one("SELECT NULL::bytea AS value", &[])
        .expect("the seeded row is present exactly once");
    let empty = client
        .query_one("SELECT ''::bytea AS value", &[])
        .expect("the seeded row is present exactly once");
    let digest = |rows: &[&Row]| crate::material_runtime::capture_rows_digest(rows.iter().copied());
    assert_eq!(
        digest(&[&first]).expect("the fixture value has a canonical digest"),
        digest(&[&equal]).expect("the fixture value has a canonical digest")
    );
    for row in [&changed, &changed_type, &changed_name, &null, &empty] {
        assert_ne!(
            digest(&[&first]).expect("the fixture value has a canonical digest"),
            digest(&[row]).expect("the fixture value has a canonical digest")
        );
    }
    assert_ne!(
        digest(&[&null]).expect("the fixture value has a canonical digest"),
        digest(&[&empty]).expect("the fixture value has a canonical digest")
    );
    assert_ne!(
        digest(&[&first, &changed]).expect("the fixture value has a canonical digest"),
        digest(&[&changed, &first]).expect("the fixture value has a canonical digest")
    );
    assert_ne!(
        digest(&[&first]).expect("the fixture value has a canonical digest"),
        digest(&[&first, &equal]).expect("the fixture value has a canonical digest")
    );
}

/// One stored value row: hyperedge, member, qname, value bits.
type MemberRow = (String, String, String, i64);

/// A campaign whose opening graph carries membership values, with one period
/// committed through the product's own call. Returns the runtime and the
/// expected `(hyperedge, member, qname, value_bits)` rows, sorted.
fn campaign_with_membership_values_committed(
    config: &Config,
    campaign: CampaignId,
) -> (
    material_runtime::DurableMaterialRuntime,
    Vec<MemberRow>,
    [u8; 32],
) {
    use crate::test_support::{MEMBERSHIP_COUNTIES, MEMBERSHIP_QNAME};
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation_for_campaign(
            &crate::test_support::catalog_with_membership_values(),
            campaign,
        )
        .expect("the catalog admits an authored membership field and its values");
    let digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(config, campaign, foundation)
        .expect("the test database creates the fixture campaign");
    let actions = OrderedPracticeActionBatch::empty(
        runtime.session().graph_session().session_identity().clone(),
        1,
    )
    .expect("the empty authored batch constructs");
    runtime
        .advance_and_commit(&mut CollectingSink::default(), &actions)
        .expect("the prepared tick advances and commits");
    assert_eq!(runtime.session().completed_tick(), 1);
    let mut expected: Vec<MemberRow> = [
        (MEMBERSHIP_COUNTIES[0], 7.0_f64),
        (MEMBERSHIP_COUNTIES[1], -3.0),
    ]
    .into_iter()
    .map(|(member, value)| {
        (
            "membership-proof".to_owned(),
            member.to_owned(),
            MEMBERSHIP_QNAME.to_owned(),
            i64::from_ne_bytes(value.to_bits().to_ne_bytes()),
        )
    })
    .collect();
    expected.sort();
    (runtime, expected, digest)
}

fn stored_membership_rows(config: &Config, campaign: CampaignId, tick: i64) -> Vec<MemberRow> {
    let mut client = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    let mut rows: Vec<_> = client
        .query(
            "SELECT local_name, member, qname, value_bits \
             FROM babylon_state.graph_hyperedge_member_f64_v1 \
             WHERE campaign_id=$1::uuid AND resolve_tick=$2",
            &[campaign.as_uuid(), &tick],
        )
        .expect("the stored value rows are readable")
        .iter()
        .map(|row| (row.get(0), row.get(1), row.get(2), row.get(3)))
        .collect();
    rows.sort();
    rows
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn a_campaign_with_membership_values_restores_them() {
    let base = super::validated_base_config();
    let database = TestDatabase::create_from_template(
        &base,
        &super::validated_template_name(),
        "membervalrestore",
    );
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x653_0a02));
    let (runtime, expected, digest) = campaign_with_membership_values_committed(&config, campaign);
    let stored = runtime
        .session()
        .graph_session()
        .stable_graph_state()
        .expect("the committed session has a stable graph state");
    assert_eq!(stored.rows().membership_f64().len(), 2);
    let bytes = stored.canonical_bytes().to_vec();
    let world_hash = runtime
        .session()
        .current_world_hash()
        .expect("the committed session publishes a world hash");
    let tail = runtime.tail().copied();
    drop(runtime);

    // An empty table cannot pass: the rows are exactly the seeded values.
    assert_eq!(stored_membership_rows(&config, campaign, 1), expected);

    let reopened = DurableMaterialRuntime::open(&config, campaign, digest)
        .expect("the committed campaign reopens");
    let restored = reopened
        .session()
        .graph_session()
        .stable_graph_state()
        .expect("the reopened session has a stable graph state");
    assert_eq!(restored.canonical_bytes(), bytes.as_slice());
    assert_eq!(
        restored.rows().membership_f64(),
        stored.rows().membership_f64()
    );
    assert_eq!(
        reopened
            .session()
            .current_world_hash()
            .expect("the reopened session publishes a world hash"),
        world_hash
    );
    assert_eq!(reopened.tail().copied(), tail);
    drop(reopened);
    database.cleanup();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn a_lost_membership_value_row_refuses_the_reopen() {
    let base = super::validated_base_config();
    let database = TestDatabase::create_from_template(
        &base,
        &super::validated_template_name(),
        "membervallost",
    );
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x653_0a03));
    let (runtime, expected, digest) = campaign_with_membership_values_committed(&config, campaign);
    drop(runtime);
    assert_eq!(stored_membership_rows(&config, campaign, 1), expected);

    let mut writer = config
        .connect(NoTls)
        .expect("the test database accepts the connection");
    writer
        .execute(
            "DELETE FROM babylon_state.graph_hyperedge_member_f64_v1 \
             WHERE campaign_id=$1::uuid AND resolve_tick=1 AND member=$2",
            &[campaign.as_uuid(), &expected[0].1],
        )
        .expect("the test database applies the setup statement");
    drop(writer);
    assert_eq!(stored_membership_rows(&config, campaign, 1).len(), 1);

    // The database accepts the deletion of the committed row; the reopen then
    // refuses the campaign (the stored rows no longer match what was committed)
    // instead of reading the lost value as zero. The refusal is the stored
    // checkpoint's admission (`StoredCheckpointSections::admit`): its graph section
    // is bound to the graph's canonical bytes by length and digest.
    let result = DurableMaterialRuntime::open(&config, campaign, digest);
    assert!(
        matches!(
            &result,
            Err(MaterialRuntimeError::Graph(
                crate::runtime::RustPersistenceRuntimeError::CampaignConflict
            ))
        ),
        "a lost value row must refuse the reopen, got {:?}",
        result.as_ref().err()
    );
    database.cleanup();
}
