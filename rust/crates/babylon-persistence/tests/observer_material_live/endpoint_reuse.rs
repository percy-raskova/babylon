//! Prior endpoint reuse retains independent marker, component and action proofs.

use super::{
    CampaignId, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset,
    MichiganDeliveryPreset, NoTls, ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
    Uuid,
};
use babylon_persistence::michigan_material::MichiganMaterialCatalog;
use std::path::Path;

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and qualified statewide sources"]
fn organizer_combined_observation_refuses_corrupt_prior_endpoint_proofs() {
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x343_26163));
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../content/scenarios/michigan/defines.toml");
    let catalog =
        MichiganMaterialCatalog::load_for_preset(&path, MichiganDeliveryPreset::OrganizeInWayne)
            .unwrap();
    let foundation = MichiganContentPreset::OrganizeInWayne
        .create_foundation_for_campaign(&catalog, campaign)
        .unwrap();
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation).unwrap();
    super::install_reader_role(&target.writer).unwrap();
    super::provision_observer_role(&target.writer).unwrap();
    let observer = ObserverEconomyReader::connect(
        &target.login("babylon_observer", "endpoints"),
        ObserverVisibility::FullObserver,
    )
    .unwrap();
    super::advance_material_period(&mut runtime);
    super::advance_material_period(&mut runtime);
    let healthy = observer
        .committed_material_observation(campaign, 2)
        .unwrap();
    assert_eq!(healthy.accounting.identity, *runtime.tail().unwrap());
    let mut writer = target.writer.connect(NoTls).unwrap();
    for (table, column) in [
        ("tick_commit", "envelope_digest"),
        ("checkpoint_manifest", "manifest_bytes"),
        ("tick_action_batch_v1", "exact_action_batch_bytes"),
        ("tick_action_batch_v1", "action_batch_digest"),
    ] {
        let original: Vec<u8> = writer
            .query_one(
                &format!(
                    "SELECT {column} FROM babylon_state.{table} \
                     WHERE campaign_id=$1::uuid AND resolve_tick=1"
                ),
                &[campaign.as_uuid()],
            )
            .unwrap()
            .get(0);
        let mut changed = original.clone();
        changed[0] ^= 1;
        let update = format!(
            "UPDATE babylon_state.{table} SET {column}=$2 \
             WHERE campaign_id=$1::uuid AND resolve_tick=1"
        );
        assert_eq!(
            writer
                .execute(&update, &[campaign.as_uuid(), &changed])
                .unwrap(),
            1
        );
        let refused = observer.committed_material_observation(campaign, 2);
        // Restore the exact owned row before checking the refusal.
        assert_eq!(
            writer
                .execute(&update, &[campaign.as_uuid(), &original])
                .unwrap(),
            1
        );
        assert!(
            matches!(refused, Err(ObserverEconomyError::InvalidProjection)),
            "prior {table}.{column} must be authenticated before reuse"
        );
    }
    let restored = observer
        .committed_material_observation(campaign, 2)
        .unwrap();
    assert_eq!(restored.accounting, healthy.accounting);
    assert_eq!(restored.snapshot, healthy.snapshot);
    assert_eq!(restored.production_evidence, healthy.production_evidence);
    assert_eq!(runtime.tail(), Some(&healthy.accounting.identity));
}
