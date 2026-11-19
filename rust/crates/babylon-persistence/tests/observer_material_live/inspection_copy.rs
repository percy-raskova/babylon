//! The exact predecessor survives transport unchanged and current admission stays strict.
use super::{
    CampaignId, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset, NoTls, Uuid,
};
use babylon_material_circuit::SiteId;
use babylon_persistence::inspection_copy::{self, InspectionCopyError};
use babylon_persistence::money_journal::{JournalError, MoneyJournalWriter};
use babylon_persistence::observer_reader::{self, ObserverEconomyReader, ObserverVisibility};
use babylon_persistence::CurrentSchemaError;
use postgres::Client;

fn markers(client: &mut Client, id: CampaignId) -> Vec<Vec<u8>> {
    client.query("SELECT pg_catalog.sha256(t.tick_content_hash||t.envelope_digest||m.identity_bytes||pg_catalog.sha256(m.register_storage_bytes)||pg_catalog.sha256(m.receipt_storage_bytes)||pg_catalog.sha256(m.lookup_delta_bytes)||a.action_batch_digest) FROM babylon_state.tick_commit t JOIN babylon_state.material_tick_v3 m USING(campaign_id,resolve_tick) JOIN babylon_state.tick_action_batch_v1 a USING(campaign_id,resolve_tick) WHERE t.campaign_id=$1 ORDER BY resolve_tick",&[id.as_uuid()]).expect("captured tick evidence").into_iter().map(|r|r.get(0)).collect()
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn predecessor_inspection_copies_only_the_named_campaign_without_adopting_its_database() {
    let from = DisposableTarget::create();
    let mut to = DisposableTarget::create();
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
    let site = run
        .session()
        .material()
        .state()
        .inventory
        .first()
        .expect("physical control closing stock")
        .site_id;
    drop(run);
    DurableMaterialRuntime::create(&from.writer, extra, input()).expect("unrelated campaign");
    let mut source = from.writer.connect(NoTls).expect("disposable source");
    let raw = markers(&mut source, campaign);
    assert_eq!(raw.len(), 2);
    check_predecessor_labor_indexes(&from, &mut source, campaign, &raw);
    source
        .batch_execute(include_str!("predecessor_2824cf38e.sql"))
        .expect("restore exact predecessor in the disposable clone");
    assert!(matches!(
        babylon_persistence::preflight_current_schema(&from.writer),
        Err(CurrentSchemaError::CurrentCensusMismatch)
    ));
    let report = inspection_copy::copy_campaign(&from.writer, &to.writer, campaign)
        .expect("row-only inspection copy");
    assert_eq!(
        report.source_schema,
        "f984e7ee59fa650fc470f884b4663a6fc773c44ed4494254727273e50093d071"
    );
    assert_eq!(report.committed_periods, 2);
    let mut target = to.writer.connect(NoTls).expect("destination");
    assert_eq!(markers(&mut target, campaign), raw);
    assert_eq!(markers(&mut source, campaign), raw);
    let count: i64 = target
        .query_one("SELECT count(*) FROM babylon_state.campaign", &[])
        .expect("one campaign")
        .get(0);
    assert_eq!(count, 1);
    inspect_copied_history(&mut to, campaign, site);
    assert_eq!(markers(&mut source, campaign), raw);
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

/// The preceding layout differs only in the physical indexes over derived labor rows.
fn check_predecessor_labor_indexes(
    source_db: &DisposableTarget,
    source: &mut Client,
    campaign: CampaignId,
    expected: &[Vec<u8>],
) {
    let marker = "85346ef39af0c28ce6455ab60fb2f2abb2f39b7f23bbbf07ad5ab4afd1013ba3";
    source.batch_execute("ALTER TABLE babylon_state.labor_node_identity_v1
        DROP CONSTRAINT labor_node_campaign_digest_v1, ADD UNIQUE (campaign_id,descriptor_sha256);
        CREATE INDEX labor_node_block_descriptors_v1 ON babylon_state.labor_node_block_v1 USING gin(descriptor_keys) WITH (fastupdate=off)")
        .expect("restore the preceding physical indexes in the private source");
    source
        .execute(
            "UPDATE babylon_meta.current_schema SET schema_sha256=decode($1,'hex')",
            &[&marker],
        )
        .expect("restore the preceding marker");
    let target = DisposableTarget::create();
    let report = inspection_copy::copy_campaign(&source_db.writer, &target.writer, campaign)
        .expect("copy original committed rows from the preceding catalog");
    assert_eq!(report.source_schema, marker);
    assert_eq!(report.committed_periods, 2);
    let mut copied = target.writer.connect(NoTls).expect("copied campaign");
    assert_eq!(markers(&mut copied, campaign), expected);
    assert_eq!(markers(source, campaign), expected);
}

fn inspect_copied_history(to: &mut DisposableTarget, campaign: CampaignId, site: SiteId) {
    observer_reader::provision_observer_role(&to.writer)
        .expect("grant full observer on the destination");
    let reader = ObserverEconomyReader::connect(
        &to.login("babylon_observer", "inspection"),
        ObserverVisibility::FullObserver,
    )
    .expect("copied campaign observer");
    let journal = MoneyJournalWriter::connect(&to.writer).expect("destination publisher");
    for tick in 1..=2 {
        let admitted = reader
            .committed_material_receipts(campaign, tick)
            .expect("original material period");
        journal
            .publish(&reader, campaign, tick)
            .expect("derive journal on destination");
        let site = reader
            .published_site_period(campaign, tick, site)
            .expect("original stock owner");
        assert_eq!(
            &site.tick_content_hash,
            admitted.identity.tick_content_hash().as_bytes()
        );
        assert!(site.statement.is_none());
        assert_eq!(
            reader.published_company_period_statements(campaign, tick),
            Err(JournalError::CompanyBooksNotCaptured)
        );
    }
}
