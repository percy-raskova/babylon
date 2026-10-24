//! Open must release its SQL snapshot before reconstructing material authority.
use super::{CampaignId, CollectingSink, NoTls, OrderedPracticeActionBatch, TestDatabase};
use crate::material_runtime;
use crate::material_runtime::{DurableMaterialRuntime, FoundationReadSource, MaterialRuntimeError};
use crate::michigan_content::MichiganContentPreset;
use postgres::Row;
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
