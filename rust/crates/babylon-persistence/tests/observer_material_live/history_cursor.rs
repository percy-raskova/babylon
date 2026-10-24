//! A warm read cannot hide corrupt material outside its two current endpoints.
use super::{
    CampaignId, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset,
    MichiganDeliveryPreset, NoTls, ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
    Uuid,
};
use babylon_persistence::michigan_material::MichiganMaterialCatalog;
use babylon_persistence::observer_reader::{
    CommittedMaterialObservation, ObserverEconomySnapshot, ObserverMaterialCursor,
};
use babylon_tick::material_world::MaterialWorldRegister;

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed material ticks"]
fn cached_history_refuses_earlier_receipt_corruption_and_preserves_the_cursor() {
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x0034_3261_6344));
    let catalog = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .unwrap();
    let foundation = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
        .create_foundation(&catalog)
        .unwrap();
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation).unwrap();
    super::provision_observer_role(&target.writer).unwrap();
    let observer_config = target.login("babylon_observer", "prefix");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver).unwrap();
    for _ in 0..4 {
        super::advance_material_period(&mut runtime);
    }
    let mut cursor = None;
    let healthy = observer
        .snapshot_with_cursor(campaign, 4, &mut cursor)
        .unwrap();
    let mut complete_cursor = None;
    let complete = observer
        .committed_material_observation_with_cursor(campaign, 4, &mut complete_cursor)
        .unwrap();
    assert_owned_register(complete_cursor.as_ref(), runtime.session().material());
    let owned_register_address = register_address(complete_cursor.as_ref());
    let repeated = observer
        .committed_material_observation_with_cursor(campaign, 4, &mut complete_cursor)
        .unwrap();
    assert_complete_observations_equal(&complete, &repeated);
    assert_eq!(
        owned_register_address,
        register_address(complete_cursor.as_ref())
    );
    assert!(std::sync::Arc::ptr_eq(
        &complete.accounting.receipts,
        &repeated.accounting.receipts
    ));
    // Retained history must survive expiry of its weak foundation owner. The
    // new capability captures and admits the foundation again before reuse.
    drop(observer);
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver).unwrap();
    assert_eq!(cursor.as_ref().unwrap().completed_tick(), 4);
    let mut writer = target.writer.connect(NoTls).unwrap();
    let original: Vec<u8> = writer.query_one(
        "SELECT receipt_storage_bytes FROM babylon_state.material_tick_v3 WHERE campaign_id=$1 AND resolve_tick=1",
        &[campaign.as_uuid()],
    ).unwrap().get(0);
    let mut corrupted = original.clone();
    corrupted.push(0);
    let update = "UPDATE babylon_state.material_tick_v3 SET receipt_storage_bytes=$2 WHERE campaign_id=$1 AND resolve_tick=1";
    assert_eq!(
        writer
            .execute(update, &[campaign.as_uuid(), &corrupted])
            .unwrap(),
        1
    );
    let cold = observer.snapshot(campaign, 4);
    let warm = observer.snapshot_with_cursor(campaign, 4, &mut cursor);
    let complete_refusal =
        observer.committed_material_observation_with_cursor(campaign, 4, &mut complete_cursor);
    // Restore exact owned bytes before any assertion or cleanup can stop the test.
    assert_eq!(
        writer
            .execute(update, &[campaign.as_uuid(), &original])
            .unwrap(),
        1
    );
    assert_eq!(cursor.as_ref().unwrap().completed_tick(), 4);
    assert_eq!(complete_cursor.as_ref().unwrap().completed_tick(), 4);
    assert_eq!(
        owned_register_address,
        register_address(complete_cursor.as_ref())
    );
    let restored = observer
        .snapshot_with_cursor(campaign, 4, &mut cursor)
        .unwrap();
    assert_eq!(restored, healthy);
    super::advance_material_period(&mut runtime);
    let next = observer
        .snapshot_with_cursor(campaign, 5, &mut cursor)
        .unwrap();
    assert_eq!(next, observer.snapshot(campaign, 5).unwrap());
    let next_complete = observer
        .committed_material_observation_with_cursor(campaign, 5, &mut complete_cursor)
        .unwrap();
    let cold_complete = observer
        .committed_material_observation(campaign, 5)
        .unwrap();
    assert_complete_observations_equal(&next_complete, &cold_complete);
    assert_owned_register(complete_cursor.as_ref(), runtime.session().material());
    assert_eq!(cursor.as_ref().unwrap().completed_tick(), 5);
    drop(writer);
    drop(observer);
    drop(runtime);
    drop(target);
    assert_history_refusals(&cold, &warm, &complete_refusal);
}

fn assert_history_refusals(
    cold: &Result<ObserverEconomySnapshot, ObserverEconomyError>,
    warm: &Result<ObserverEconomySnapshot, ObserverEconomyError>,
    complete_refusal: &Result<CommittedMaterialObservation, ObserverEconomyError>,
) {
    assert!(
        matches!(cold, Err(ObserverEconomyError::InvalidProjection)),
        "the same earlier corrupt receipt must refuse cold admission"
    );
    assert!(
        matches!(warm, Err(ObserverEconomyError::InvalidProjection)),
        "cached P4 must freshly authenticate P1 outside its current/prior endpoints"
    );
    assert!(matches!(
        complete_refusal,
        Err(ObserverEconomyError::InvalidProjection)
    ));
}

fn assert_complete_observations_equal(
    left: &CommittedMaterialObservation,
    right: &CommittedMaterialObservation,
) {
    assert_eq!(left.snapshot, right.snapshot);
    assert_eq!(left.accounting, right.accounting);
    assert_eq!(left.production_evidence, right.production_evidence);
}

fn assert_owned_register(
    cursor: Option<&ObserverMaterialCursor>,
    expected: &MaterialWorldRegister,
) {
    assert_eq!(cursor.unwrap().current_register().unwrap(), expected);
}

fn register_address(cursor: Option<&ObserverMaterialCursor>) -> *const MaterialWorldRegister {
    std::ptr::from_ref(cursor.unwrap().current_register().unwrap())
}
