//! The exact predecessor survives transport unchanged and current admission stays strict.
use super::{
    CampaignId, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset, NoTls, Uuid,
};
use babylon_persistence::inspection_copy::{self, InspectionCopyError};
use babylon_persistence::CurrentSchemaError;
use postgres::Client;

fn markers(client: &mut Client, id: CampaignId) -> Vec<Vec<u8>> {
    client.query("SELECT pg_catalog.sha256(t.tick_content_hash||t.envelope_digest||m.identity_bytes||pg_catalog.sha256(m.register_storage_bytes)||pg_catalog.sha256(m.receipt_storage_bytes)||pg_catalog.sha256(m.lookup_delta_bytes)||a.action_batch_digest) FROM babylon_state.tick_commit t JOIN babylon_state.material_tick_v3 m USING(campaign_id,resolve_tick) JOIN babylon_state.tick_action_batch_v1 a USING(campaign_id,resolve_tick) WHERE t.campaign_id=$1 ORDER BY resolve_tick",&[id.as_uuid()]).expect("captured tick evidence").into_iter().map(|r|r.get(0)).collect()
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn predecessor_inspection_copies_only_the_named_campaign_without_adopting_its_database() {
    let from = DisposableTarget::create();
    let to = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x29355));
    let extra = CampaignId::from_uuid(Uuid::from_u128(0x29356));
    let input = || {
        MichiganContentPreset::FourWeekStandard
            .create_foundation(&crate::test_support::catalog())
            .expect("captured Michigan foundation")
    };
    let mut run =
        DurableMaterialRuntime::create(&from.writer, campaign, input()).expect("fund the source");
    super::advance_material_period(&mut run);
    super::advance_material_period(&mut run);
    drop(run);
    DurableMaterialRuntime::create(&from.writer, extra, input()).expect("unrelated campaign");
    let mut source = from.writer.connect(NoTls).expect("disposable source");
    let raw = markers(&mut source, campaign);
    assert_eq!(raw.len(), 2);
    // Remove only the new derived relations from this freshly created disposable fixture.
    // The inspector still independently checks every actual predecessor catalog object.
    source.batch_execute("DROP TABLE babylon_state.labor_position_v1,babylon_state.labor_movement_v1,babylon_state.labor_node_v1,babylon_state.labor_checkpoint_v1,babylon_state.labor_period_v1,babylon_state.site_stock_balance_v1,babylon_state.site_statement_v1,babylon_state.economic_payment_v1,babylon_state.economic_flow_account_v1,babylon_state.economic_flow_location_v1,babylon_state.money_movement_total_v1,babylon_state.money_movement_v1,babylon_state.money_journal_period_v1 CASCADE; UPDATE babylon_meta.current_schema SET schema_sha256=decode('f984e7ee59fa650fc470f884b4663a6fc773c44ed4494254727273e50093d071','hex')").expect("exact predecessor fixture");
    assert!(matches!(
        babylon_persistence::preflight_current_schema(&from.writer),
        Err(CurrentSchemaError::CurrentCensusMismatch)
    ));
    let report = inspection_copy::copy_campaign(&from.writer, &to.writer, campaign)
        .expect("row-only inspection copy");
    assert_eq!(report.committed_periods, 2);
    let mut target = to.writer.connect(NoTls).expect("destination");
    assert_eq!(markers(&mut target, campaign), raw);
    assert_eq!(markers(&mut source, campaign), raw);
    let count: i64 = target
        .query_one("SELECT count(*) FROM babylon_state.campaign", &[])
        .expect("one campaign")
        .get(0);
    assert_eq!(count, 1);
    assert_eq!(
        inspection_copy::copy_campaign(&from.writer, &to.writer, campaign)
            .expect_err("an occupied target refuses another import"),
        InspectionCopyError::DestinationOccupied
    );
    source
        .batch_execute("CREATE TABLE public.unrecognized(x bigint)")
        .expect("incompatible neighboring schema");
    assert_eq!(
        inspection_copy::copy_campaign(&from.writer, &to.writer, campaign)
            .expect_err("the source schema differs from the recorded predecessor"),
        InspectionCopyError::SourceSchema
    );
}
