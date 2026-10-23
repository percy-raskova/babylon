//! Open must release its SQL snapshot before reconstructing material authority.
use super::*;
use crate::material_runtime::{
    capture_material_foundation_components, DurableMaterialRuntime, FoundationReadSource,
    MaterialRuntimeError,
};
use std::time::Duration;

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn live_material_open_reconstructs_after_releasing_its_snapshot() {
    let base = validated_base_config();
    let database =
        TestDatabase::create_from_template(&base, &validated_template_name(), "materialopen");
    let mut config = database.config(&base);
    let application = format!("material-open-control-{}", std::process::id());
    config.application_name(&application);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x342_0fe0));
    let foundation = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation_for_campaign(&crate::test_support::catalog(), campaign)
        .unwrap();
    let digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(&config, campaign, foundation).unwrap();
    for tick in 0..=2 {
        let reopened = DurableMaterialRuntime::open_with_foundation_admission(
            &config,
            campaign,
            |snapshot| {
                snapshot.batch_execute("SET LOCAL idle_in_transaction_session_timeout='100ms'")?;
                let captured = capture_material_foundation_components(
                    snapshot,
                    campaign,
                    digest,
                    FoundationReadSource::Runtime,
                )?;
                Ok((captured, ()))
            },
            |captured, ()| {
                let mut observer = config.connect(NoTls).unwrap();
                let state = observer
                    .query_one(
                        "SELECT count(*),bool_and(state='idle' AND xact_start IS NULL) \
                     FROM pg_catalog.pg_stat_activity WHERE datname=pg_catalog.current_database() \
                     AND application_name=$1 AND pid<>pg_catalog.pg_backend_pid()",
                        &[&application],
                    )
                    .unwrap();
                assert_eq!(state.get::<_, i64>(0), 1);
                assert!(
                    state.get::<_, bool>(1),
                    "Open reconstruction still owns a SQL snapshot"
                );
                std::thread::sleep(Duration::from_millis(250));
                captured.admit()
            },
        )
        .unwrap();
        assert_eq!(reopened.session().completed_tick(), tick);
        assert_eq!(reopened.tail(), runtime.tail());
        assert_eq!(
            reopened.session().current_world_hash().unwrap(),
            runtime.session().current_world_hash().unwrap()
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
            .unwrap();
            runtime
                .advance_and_commit(&mut CollectingSink::default(), &actions)
                .unwrap();
        }
    }
    drop(runtime);
    database.cleanup();
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn live_material_open_refuses_a_changed_foundation_or_committed_tail() {
    let base = validated_base_config();
    let database =
        TestDatabase::create_from_template(&base, &validated_template_name(), "opendrift");
    let config = database.config(&base);
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x342_0fe1));
    let foundation = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation_for_campaign(&crate::test_support::catalog(), campaign)
        .unwrap();
    let digest = foundation.digest();
    let mut runtime = DurableMaterialRuntime::create(&config, campaign, foundation).unwrap();
    for field in ["rng_seed", "geography_scope", "tail"] {
        let result = DurableMaterialRuntime::open_with_foundation_admission(
            &config,
            campaign,
            |snapshot| {
                capture_material_foundation_components(
                    snapshot,
                    campaign,
                    digest,
                    FoundationReadSource::Runtime,
                )
                .map(|captured| (captured, ()))
            },
            |captured, ()| {
                let admitted = captured.admit()?;
                let mut writer = config.connect(NoTls).unwrap();
                match field {
                    "rng_seed" => {
                        writer.execute("UPDATE babylon_state.campaign_foundation SET rng_seed=rng_seed+1 WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
                    }
                    "geography_scope" => {
                        writer.execute("UPDATE babylon_state.campaign SET geography_scope='national-counties' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
                    }
                    "tail" => {
                        let actions = OrderedPracticeActionBatch::empty(
                            runtime.session().graph_session().session_identity().clone(),
                            1,
                        )
                        .unwrap();
                        runtime
                            .advance_and_commit(&mut CollectingSink::default(), &actions)
                            .unwrap();
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
            let mut writer = config.connect(NoTls).unwrap();
            if field == "rng_seed" {
                writer.execute("UPDATE babylon_state.campaign_foundation SET rng_seed=rng_seed-1 WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
            } else {
                writer.execute("UPDATE babylon_state.campaign SET geography_scope='michigan-control' WHERE campaign_id=$1", &[campaign.as_uuid()]).unwrap();
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
    let config = validated_base_config();
    let mut client = config.connect(NoTls).unwrap();
    let first = client.query_one("SELECT 1::int4 AS value", &[]).unwrap();
    let equal = client.query_one("SELECT 1::int4 AS value", &[]).unwrap();
    let changed = client.query_one("SELECT 2::int4 AS value", &[]).unwrap();
    let changed_type = client.query_one("SELECT 1::int8 AS value", &[]).unwrap();
    let changed_name = client.query_one("SELECT 1::int4 AS other", &[]).unwrap();
    let null = client
        .query_one("SELECT NULL::bytea AS value", &[])
        .unwrap();
    let empty = client.query_one("SELECT ''::bytea AS value", &[]).unwrap();
    let digest = |rows: &[&postgres::Row]| {
        crate::material_runtime::capture_rows_digest(rows.iter().copied())
    };
    assert_eq!(digest(&[&first]).unwrap(), digest(&[&equal]).unwrap());
    for row in [&changed, &changed_type, &changed_name, &null, &empty] {
        assert_ne!(digest(&[&first]).unwrap(), digest(&[row]).unwrap());
    }
    assert_ne!(digest(&[&null]).unwrap(), digest(&[&empty]).unwrap());
    assert_ne!(
        digest(&[&first, &changed]).unwrap(),
        digest(&[&changed, &first]).unwrap()
    );
    assert_ne!(
        digest(&[&first]).unwrap(),
        digest(&[&first, &equal]).unwrap()
    );
}
