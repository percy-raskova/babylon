//! Permanent coverage, exact rebuild and capability confinement in a disposable database.
#[path = "account_directory.rs"]
mod account_directory;
#[path = "journal_snapshot.rs"]
mod journal_snapshot;
#[path = "movement_blocks.rs"]
mod movement_blocks;

use self::account_directory::PointScale;
use super::{
    CampaignId, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset, NoTls,
    ObserverEconomyReader, ObserverVisibility, Uuid,
};
use babylon_persistence::material_runtime::MaterialRuntimeFoundation;
use babylon_persistence::money_journal::{
    self as journal, FlowGroup, JournalError, JournalQueue, MoneyJournalWriter, MoneyMovement,
    MoneyPurpose, MoneyTotal,
};
use babylon_persistence::observer_reader::{CommittedMaterialReceipts, ObserverMaterialCursor};
use babylon_persistence::site_financial_statements::SiteFinancialStatements;
use postgres::{Client, Config};
use serde_json::Value;
use std::process::Command;

fn journal_cli(
    operation: &str,
    observer: &Config,
    writer: Option<&Config>,
    campaign: CampaignId,
) -> Value {
    let mut command = Command::new(env!("CARGO_BIN_EXE_babylon-money-journal"));
    command
        .args([
            operation,
            "--campaign",
            &campaign.as_uuid().to_string(),
            "--first",
            "1",
        ])
        .env(
            "BABYLON_OBSERVER_DSN",
            super::runtime_process::child_dsn(observer),
        )
        .env_remove("BABYLON_RUNTIME_DSN");
    if let Some(writer) = writer {
        command.env(
            "BABYLON_RUNTIME_DSN",
            super::runtime_process::child_dsn(writer),
        );
    }
    let output = command
        .output()
        .expect("start the actual money journal CLI");
    assert!(
        output.status.success(),
        "money journal {operation} CLI must succeed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let result: Value =
        serde_json::from_slice(&output.stdout).expect("journal CLI emits one JSON response");
    let expected_version = if operation == "flows" { 2 } else { 1 };
    assert_eq!(
        result["version"], expected_version,
        "CLI {operation} protocol version"
    );
    assert_eq!(
        result["campaign"],
        campaign.as_uuid().to_string(),
        "CLI response preserves the requested campaign"
    );
    result
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime"]
fn money_journal_retains_thirteen_periods_and_rebuilds_authenticated_history() {
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x7391));
    let mut runtime = DurableMaterialRuntime::create(
        &target.writer,
        campaign,
        MichiganContentPreset::FourWeekStandard
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation"),
    )
    .expect("the disposable database creates the campaign");
    super::install_reader_role(&target.writer).expect("reader grants");
    super::provision_observer_role(&target.writer).expect("observer grants");
    let observer_config = target.login("babylon_observer", "moneyobserver");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
            .expect("the full observer target is bounded");
    let preview_config = target.login("babylon_reader", "moneypreview");
    let preview = ObserverEconomyReader::connect(&preview_config, ObserverVisibility::KnownPreview)
        .expect("the preview target is bounded");
    for config in [&observer_config, &preview_config] {
        let mut login = config.connect(NoTls).expect("confined login");
        for sql in [
            "DELETE FROM babylon_state.money_movement_block_v1 WHERE false",
            "UPDATE babylon_state.labor_movement_block_v1 SET unknown_opening=ARRAY[true] WHERE false",
        ] {
            let error = login.execute(sql, &[]).expect_err("movement storage requires writer authority");
            assert_eq!(error.code(), Some(&postgres::error::SqlState::INSUFFICIENT_PRIVILEGE), "{sql}");
        }
    }
    let writer = MoneyJournalWriter::connect(&target.writer).expect("the owner target is bounded");
    assert!(matches!(
        JournalQueue::connect(&preview, &writer, None),
        Err(JournalError::Authority)
    ));
    let mut regional = JournalQueue::connect(&observer, &writer, None).expect("regional queue");
    assert_eq!(
        regional
            .warm_new_opening(Some(campaign))
            .expect("regional P0"),
        None
    );

    assert!(
        matches!(
            writer.publish(&preview, campaign, 1),
            Err(JournalError::Observer(_))
        ),
        "preview credentials cannot admit source receipts"
    );
    super::payment_flows::restricted(&preview, campaign);
    super::recorded_labor::restricted(&preview, campaign);
    let mut cursor = publish_fourteen_periods(&mut runtime, &writer, &observer, campaign);
    let mut preview_cursor = cursor.clone();
    let preview_frame = preview
        .snapshot_with_cursor(campaign, 1, &mut preview_cursor)
        .expect("restricted snapshot");
    assert!(
        preview_frame.production.is_none() && preview_cursor.is_none(),
        "a restricted observation cannot retain a full observer decision capability"
    );
    assert_eq!(
        observer.published_company_period_statements(campaign, 14),
        Err(JournalError::CompanyBooksNotCaptured)
    );
    let site = super::site_accounting_sql::stocks(&runtime, &observer, campaign, 14);
    let earlier = observer
        .committed_material_receipts(campaign, 1)
        .expect("period one frame of the ungrouped Michigan campaign")
        .identity;
    let ungrouped = || {
        observer.site_company_decision_for_frame(
            campaign,
            1,
            site,
            earlier.foundation_digest(),
            *earlier.tick_content_hash().as_bytes(),
        )
    };
    assert_eq!(
        ungrouped(),
        Ok(None),
        "a historical Michigan site has no captured parent company"
    );
    super::site_accounting_sql::restricted(&preview, campaign, site);
    let physical = observer
        .published_site_period(campaign, 14, site)
        .expect("physical control site");
    super::site_accounting_sql::cli(&observer_config, &physical, 14);
    let mut owner = assert_empty_retention(&observer, &preview, &writer, &target.writer, campaign);
    super::journal_queue::recover_and_follow(
        &mut runtime,
        &mut owner,
        &target.writer,
        &observer_config,
        campaign,
    );
    assert_authority_and_cursor(
        &observer_config,
        &observer,
        &writer,
        &mut owner,
        campaign,
        &mut cursor,
    );
    assert!(
        ungrouped().is_err(),
        "a known ungrouped site cannot hide a corrupted historical receipt"
    );
}

fn publish_fourteen_periods(
    runtime: &mut DurableMaterialRuntime,
    writer: &MoneyJournalWriter,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
) -> Option<ObserverMaterialCursor> {
    let mut cursor = None;
    let mut retained = None;
    for period in 1..=14 {
        super::advance_material_period(runtime);
        if period == 14 {
            let mut reports = Vec::new();
            std::thread::scope(|scope| {
                let first = scope.spawn(|| writer.publish(observer, campaign, period));
                let second = scope.spawn(|| writer.publish(observer, campaign, period));
                reports.push(
                    first
                        .join()
                        .expect("publisher thread completes")
                        .expect("first concurrent publication"),
                );
                reports.push(
                    second
                        .join()
                        .expect("publisher thread completes")
                        .expect("second concurrent publication"),
                );
            });
            assert_eq!(reports.iter().filter(|r| r.changed).count(), 1,
                "concurrent identical publishers commit one projection and observe one idempotent result");
        } else {
            writer
                .publish_with_cursor(observer, campaign, period, &mut cursor)
                .expect("authenticated publication commits");
            assert_eq!(
                cursor.as_ref().expect("receipt cursor").completed_tick(),
                period,
                "sequential publication advances the receipt-only history cursor"
            );
        }
        if period == 1 {
            retained = Some(super::recorded_labor::first_period_flows(
                observer, campaign,
            ));
        }
    }
    let expired = super::recorded_labor::first_period_flows(observer, campaign);
    assert_eq!(Some(expired),retained,"reconstructed labor has exactly the same signed totals, known hours, unresolved movement counts and page as retained detail");
    cursor
}

fn assert_empty_retention(
    observer: &ObserverEconomyReader,
    preview: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    writer_config: &Config,
    campaign: CampaignId,
) -> Client {
    assert!(
        matches!(
            observer.money_totals(campaign, 1, 15),
            Err(JournalError::CoverageAbsent)
        ),
        "an unpublished period is not a zero-money period"
    );
    assert_eq!(
        observer
            .money_totals(campaign, 1, 14)
            .expect("all empty periods are covered"),
        Vec::new(),
        "an empty aggregate remains distinct from missing coverage"
    );
    assert!(
        matches!(
            preview.money_totals(campaign, 1, 14),
            Err(JournalError::Authority)
        ),
        "preview cannot query full money facts"
    );
    let receipts = observer
        .committed_material_receipts(campaign, 1)
        .expect("source remains durable");
    let expected = journal::derive_movements(&receipts).expect("source transfers are valid");
    assert_eq!(
        observer
            .money_movements(campaign, 1)
            .expect("pruned history rebuilds"),
        expected,
        "historical query reconstructs exactly the source transfers"
    );
    writer
        .rebuild(observer, campaign, 1)
        .expect("explicit rebuild authenticates old source");
    let mut owner = writer_config.connect(NoTls).expect("owner connection");
    let retained: i64 = owner.query_one("SELECT count(*) FROM babylon_state.money_journal_period_v1 WHERE campaign_id=$1 AND detail_retained", &[campaign.as_uuid()])
        .expect("retention query").get(0);
    assert_eq!(
        retained, 13,
        "only the latest thirteen source periods retain detail"
    );
    assert_eq!(
        owner
            .query_one(
                "SELECT count(*) FROM babylon_state.money_journal_period_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .expect("coverage query")
            .get::<_, i64>(0),
        14,
        "empty periods also retain permanent coverage"
    );
    movement_blocks::retained_labor(&mut owner, campaign);
    movement_blocks::retired(&mut owner, campaign);
    super::labor_storage_sql::retention_and_repair(&mut owner, observer, writer, campaign);
    owner
}

fn assert_authority_and_cursor(
    observer_config: &Config,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    owner: &mut Client,
    campaign: CampaignId,
    cursor: &mut Option<ObserverMaterialCursor>,
) {
    assert!(
        matches!(
            MoneyJournalWriter::connect(observer_config)
                .expect("bounded target")
                .publish(observer, campaign, 14),
            Err(JournalError::Schema)
        ),
        "publication requires the current schema's database owner"
    );
    let before_failure = cursor
        .as_ref()
        .expect("prior receipt cursor")
        .completed_tick();
    assert!(
        MoneyJournalWriter::connect(observer_config)
            .expect("observer target")
            .publish_with_cursor(observer, campaign, 14, cursor)
            .is_err(),
        "failed owner admission must not publish its receipt cursor candidate"
    );
    assert_eq!(
        cursor.as_ref().expect("preserved cursor").completed_tick(),
        before_failure,
        "publication rollback preserves the caller's history"
    );
    let first = writer
        .publish_with_cursor(observer, campaign, 14, cursor)
        .expect("idempotent publication");
    assert!(
        !first.changed,
        "identical publication has no replacement write"
    );
    owner.execute("UPDATE babylon_state.material_tick_v3 SET identity_bytes=decode('00','hex') WHERE campaign_id=$1 AND resolve_tick=1", &[campaign.as_uuid()])
        .expect("disposable source corruption");
    assert!(
        writer.rebuild_with_cursor(observer, campaign, 14, cursor).is_err(),
        "receipt-only cursor freshly authenticates its prefix and refuses changed historical source"
    );
    assert_eq!(
        cursor
            .as_ref()
            .expect("preserved receipt cursor")
            .completed_tick(),
        14,
        "failed prefix authentication preserves the prior successful cursor"
    );
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and national sources"]
fn national_money_journal_matches_nonzero_source_and_sql_aggregation() {
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
    use babylon_persistence::economic_catalog::{self, CapturedEconomicCatalog};
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(0x7392));
    let foundation =
        CapturedEconomicCatalog::capture(economic_catalog::national_catalog_input(), None)
            .expect("national source capture")
            .create_foundation(
                ReplaySessionId::try_from("national-money-journal").expect("session"),
                ReplaySeed::new(319),
            )
            .expect("national observer foundation");
    super::provision_observer_role(&target.writer).expect("observer grants");
    let observer_config = target.login("babylon_observer", "nationalmoney");
    let observer =
        ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
            .expect("observer target");
    let writer = MoneyJournalWriter::connect(&target.writer).expect("owner target");
    let (runtime, site_opening) =
        advance_new_national_campaign(&target.writer, &observer, &writer, campaign, foundation);
    let source = observer
        .committed_material_receipts(campaign, 1)
        .expect("source authenticates");
    super::site_statements::period_one(&observer, campaign, &runtime, &source, &site_opening);
    let next_without_projection = super::projection_recovery::next_without_projection(&runtime);
    let expected = journal::derive_movements(&source).expect("source transfer projection");
    assert_ne!(expected.len(), 0, "actual monetary period has transfers");
    assert_published_source(
        &observer,
        &observer_config,
        &writer,
        &target.writer,
        campaign,
        &expected,
    );
    super::payment_flows::national(&observer, &observer_config, campaign, &expected);
    let cli = journal_cli("flows", &observer_config, None, campaign);
    assert_eq!(cli["request"]["group"], "location");
    assert_eq!(cli["page"]["total"]["current"]["net_micros"], "0");
    let totals = assert_source_totals(&observer, &observer_config, campaign, &source, &expected);
    let mut owner = target.writer.connect(NoTls).expect("owner connection");
    movement_blocks::retained_money(&mut owner, campaign);
    check_reserve_payer_integrity(&mut owner, &observer, &writer, campaign);
    super::labor_storage_sql::national_descriptor_sources(&mut owner, campaign);
    assert_nonzero_history(&mut owner, &observer, &writer, campaign, &expected, &totals);
    let mut returning_session = JournalQueue::connect(&observer, &writer, None)
        .expect("returning session has ordinary database-wide catchup");
    assert_eq!(
        returning_session
            .warm_reopened_campaign(campaign)
            .expect("authenticate the reopened covered national period"),
        Some(1)
    );
    assert_eq!(
        returning_session
            .warm_reopened_campaign(campaign)
            .expect("check the admitted period on repeated warmup"),
        None
    );
    super::projection_recovery::commit_after_projection(
        &target.writer,
        campaign,
        &next_without_projection,
    );
    assert_eq!(
        returning_session
            .warm_reopened_campaign(campaign)
            .expect("discover the newly committed uncovered period"),
        None,
        "a new uncovered head is left to the normal writer"
    );
    super::projection_recovery::interrupt_and_retry(
        &mut owner,
        &writer,
        &observer,
        campaign,
        &mut returning_session,
    );
    super::payment_flows::comparison(&mut owner, &observer, campaign);
    super::payment_flows::check_company_rebuild(&mut owner, &observer, &writer, campaign);
    super::site_accounting_sql::stocks(&runtime, &observer, campaign, 1);
    super::site_accounting_sql::national(
        &observer,
        &writer,
        &mut owner,
        campaign,
        site_opening.site_id,
    );
    let compact = observer
        .published_site_period(campaign, 1, site_opening.site_id)
        .expect("permanent site accounts");
    super::site_accounting_sql::cli(&observer_config, &compact, 2);
    super::recorded_labor::national(&observer, &observer_config, campaign);
    reject_incomplete_county_labor(&mut owner, &observer, campaign);
    super::site_statements::native_cli(&observer_config, campaign, &site_opening);
    account_directory::check(&mut owner, &target.writer, &observer, &writer, campaign);
    assert_source_faults(&mut owner, &observer, &writer, campaign, &expected, &totals);
}

fn advance_new_national_campaign(
    owner_config: &Config,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
    foundation: MaterialRuntimeFoundation,
) -> (DurableMaterialRuntime, SiteFinancialStatements) {
    let mut watching = JournalQueue::connect(observer, writer, None).expect("registered watcher");
    assert_eq!(
        watching
            .warm_new_opening(None)
            .expect("baseline before New"),
        None
    );
    let mut runtime = DurableMaterialRuntime::create(owner_config, campaign, foundation)
        .expect("national opening commits");
    assert!(watching
        .wait(std::time::Duration::from_secs(3))
        .expect("actual enrollment wake"));
    assert_eq!(
        watching.warm_new_opening(None).expect("discover menu New"),
        Some(campaign)
    );
    assert_eq!(
        watching.warm_new_opening(None).expect("repeated wake"),
        None
    );
    let mut late = JournalQueue::connect(observer, writer, None).expect("late session watcher");
    assert_eq!(
        late.warm_new_opening(None).expect("existing P0 stays cold"),
        None
    );
    assert_eq!(
        late.warm_new_opening(Some(campaign))
            .expect("launcher-minted initial New"),
        Some(campaign)
    );
    let rows: i64 = owner_config.connect(NoTls).expect("owner").query_one(
        "SELECT (SELECT count(*) FROM babylon_state.money_journal_period_v1 WHERE campaign_id=$1)
            + (SELECT count(*) FROM babylon_state.company_accounting_period_v1 WHERE campaign_id=$1)
            + (SELECT count(*) FROM babylon_state.company_statement_balance_v1 WHERE campaign_id=$1)
            + (SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1)",
        &[campaign.as_uuid()],
    ).expect("inspect durable parents, children and canonical periods").get(0);
    assert_eq!(
        rows, 0,
        "warming a newly founded campaign only admits its source in memory"
    );
    let site_opening = super::site_statements::opening(observer, owner_config, campaign, &runtime);
    super::advance_material_period(&mut runtime);
    assert_eq!(
        watching
            .warm_new_opening(Some(campaign))
            .expect("uncovered P1 wins"),
        None
    );
    drop(watching);
    drop(late);
    (runtime, site_opening)
}

fn reject_incomplete_county_labor(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
) {
    let row = owner
        .query_one(
            "WITH nodes AS MATERIALIZED (
                 SELECT node_ordinal,location_key FROM public.v_observer_labor_node_v1
                 WHERE campaign_id=$1 AND resolve_tick=1
             ), outside AS (
                 SELECT m.ordinal/128 AS block FROM public.v_observer_labor_movement_v1 m
                 JOIN nodes l ON l.node_ordinal=m.source_node
                 JOIN nodes r ON r.node_ordinal=m.destination_node
                 WHERE m.campaign_id=$1 AND m.resolve_tick=1 GROUP BY m.ordinal/128
                 HAVING bool_and(l.location_key IS DISTINCT FROM 'county:26163'
                             AND r.location_key IS DISTINCT FROM 'county:26163')
                 ORDER BY block LIMIT 1
             ), removed AS (
                 DELETE FROM babylon_state.labor_movement_block_v1 b USING outside
                 WHERE b.campaign_id=$1 AND b.resolve_tick=1 AND b.block_ordinal=outside.block
                 RETURNING b.*
             ) SELECT to_jsonb(removed)::text FROM removed",
            &[campaign.as_uuid()],
        )
        .expect("remove one published block containing only off-Wayne movements");
    let original: String = row.get(0);
    let request = journal::FlowQuery {
        focus_group: Some(FlowGroup::Location),
        focus: Some("county:26163".to_owned()),
        ..super::payment_flows::query(FlowGroup::Counterparty)
    };
    let incomplete = observer.recorded_labor_flows(campaign, &request);
    assert_eq!(
        owner.execute(
            "INSERT INTO babylon_state.labor_movement_block_v1
             SELECT * FROM jsonb_populate_record(NULL::babylon_state.labor_movement_block_v1,$1::text::jsonb)",
            &[&original],
        ).expect("restore the exact published movement block"),
        1
    );
    assert_eq!(incomplete, Err(JournalError::Projection));
}

fn assert_published_source(
    observer: &ObserverEconomyReader,
    observer_config: &Config,
    writer: &MoneyJournalWriter,
    writer_config: &Config,
    campaign: CampaignId,
    expected: &[MoneyMovement],
) {
    let published = journal_cli("publish", observer_config, Some(writer_config), campaign);
    assert_eq!(
        published["periods"],
        serde_json::json!([{"period":1,"movement_count":expected.len(),"changed":true}]),
        "actual CLI publishes every nonzero source transfer exactly once"
    );
    let details = journal_cli("details", observer_config, None, campaign);
    assert_eq!(details["period"], 1, "CLI detail period provenance");
    let cli_movements: Vec<MoneyMovement> = serde_json::from_value(details["movements"].clone())
        .expect("CLI movements preserve the typed journal model");
    assert_eq!(
        cli_movements, expected,
        "actual observer-only CLI returns exact source ordinals, purposes, postings and micros"
    );
    assert_eq!(
        observer
            .money_movements(campaign, 1)
            .expect("retained detail"),
        expected,
        "every typed posting and exact amount matches its source ordinal"
    );
    assert!(
        !writer
            .publish(observer, campaign, 1)
            .expect("idempotent repeat")
            .changed
    );
}

fn assert_source_totals(
    observer: &ObserverEconomyReader,
    observer_config: &Config,
    campaign: CampaignId,
    source: &CommittedMaterialReceipts,
    expected: &[MoneyMovement],
) -> Vec<MoneyTotal> {
    let totals = observer
        .money_totals(campaign, 1, 1)
        .expect("SQL aggregate");
    let aggregated = journal_cli("totals", observer_config, None, campaign);
    assert_eq!(
        aggregated["first"], 1,
        "CLI aggregate starts at the requested period"
    );
    assert_eq!(
        aggregated["last"], 1,
        "CLI aggregate ends at the requested period"
    );
    let cli_totals: Vec<MoneyTotal> = serde_json::from_value(aggregated["totals"].clone())
        .expect("CLI totals preserve exact decimal strings");
    assert_eq!(
        cli_totals, totals,
        "actual observer-only CLI preserves the SQL totals checked against authoritative transfers"
    );
    assert_eq!(
        totals.iter().map(|r| r.movement_count).sum::<u64>(),
        u64::try_from(expected.len()).expect("bounded receipt count"),
        "each source transfer appears once in SQL aggregates"
    );
    let mut sql = observer_config.connect(NoTls).expect("observer SQL");
    for total in &totals {
        let expected_amount = source
            .receipts
            .money_transfers
            .iter()
            .enumerate()
            .filter(|(i, _)| expected[*i].purpose == total.purpose)
            .try_fold(0_i128, |sum, (_, r)| {
                sum.checked_add(r.credit.delta.micro_units())
            })
            .expect("authored national per-purpose sum fits the exact reference check");
        assert_eq!(
            total.amount_micros,
            expected_amount.to_string(),
            "SQL sum equals authoritative receipts for {:?}",
            total.purpose
        );
    }
    let sales = totals
        .iter()
        .find(|r| r.purpose == MoneyPurpose::DeliverySettlement)
        .expect("settled sales");
    let reservations = totals
        .iter()
        .find(|r| r.purpose == MoneyPurpose::PurchaseReservation)
        .expect("reservations remain separate");
    assert!(
        sales.movement_count > 0 && reservations.movement_count > 0,
        "reservation must not count as another sale"
    );
    let public_update: bool = sql.query_one(
        "SELECT pg_catalog.has_column_privilege(current_user, 'public.v_observer_money_movement_v1', 'amount_micros', 'UPDATE')",
        &[],
    ).expect("inspect the observer's effective movement-view grant").get(0);
    assert!(!public_update, "observer cannot update a projected amount");
    totals
}

/// The custody debit for a delivery settlement remains its escrow. Changing
/// only the underlying payer must still cause repeat publication to refuse.
fn check_reserve_payer_integrity(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    let row = owner
        .query_one(
            "SELECT ordinal,payer_key,recipient_key FROM babylon_state.money_movement_v1
         WHERE campaign_id=$1 AND resolve_tick=1 AND purpose='delivery_settlement'
           AND payer_key<>recipient_key ORDER BY ordinal LIMIT 1",
            &[campaign.as_uuid()],
        )
        .expect("real sale between distinct cash accounts");
    let ordinal: i64 = row.get("ordinal");
    let payer: i32 = row.get("payer_key");
    let recipient: i32 = row.get("recipient_key");
    let change = "UPDATE babylon_state.money_movement_block_v1
        SET payer_key[array_position(slots,($2::bigint%128)::smallint)]=$3
        WHERE campaign_id=$1 AND resolve_tick=1 AND block_ordinal=$2::bigint/128";
    assert_eq!(
        owner
            .execute(change, &[campaign.as_uuid(), &ordinal, &recipient])
            .expect("replace the economic payer on the captured settlement"),
        1
    );
    assert_eq!(
        writer.publish(observer, campaign, 1),
        Err(JournalError::Projection)
    );
    assert_eq!(
        owner
            .execute(change, &[campaign.as_uuid(), &ordinal, &payer])
            .expect("restore the authenticated economic payer"),
        1
    );
    let change_foundation = "UPDATE babylon_state.economic_flow_account_v1
        SET foundation_sha256=set_byte(foundation_sha256,0,get_byte(foundation_sha256,0) # 1)
        WHERE campaign_id=$1 AND account_key=$2";
    assert_eq!(
        owner
            .execute(change_foundation, &[campaign.as_uuid(), &payer])
            .expect("damage the real economic payer behind the settlement"),
        1
    );
    let query = super::payment_flows::query(FlowGroup::Location);
    assert_eq!(
        observer.economic_payment_flows(campaign, &query),
        Err(JournalError::Projection),
        "settlement coverage requires the recorded payer's foundation even when the debit is a reserve"
    );
    assert_eq!(
        owner
            .execute(change_foundation, &[campaign.as_uuid(), &payer])
            .expect("restore the recorded payer's foundation"),
        1
    );
}

fn labor_parent_row_estimates(owner: &mut Client) -> Vec<i64> {
    owner
        .query(
            "SELECT reltuples::bigint FROM pg_catalog.pg_class WHERE oid IN
             ('babylon_state.labor_node_block_v1'::regclass,'babylon_state.labor_node_identity_v1'::regclass)
             ORDER BY relname",
            &[],
        )
        .expect("read both labor foreign-key parent estimates")
        .iter()
        .map(|row| row.get(0))
        .collect()
}

fn assert_nonzero_history(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
    expected: &[MoneyMovement],
    totals: &[MoneyTotal],
) {
    let grouping = super::payment_flows::query(FlowGroup::Industry);
    let warm = observer
        .economic_payment_flows(campaign, &grouping)
        .expect("retained ranked payment facts");
    let mut pruning = owner
        .transaction()
        .expect("open owner retention transaction");
    babylon_persistence::money_journal::prune_money_journal_detail(&mut pruning, campaign, 1)
        .expect("controlled expired-period pruning uses production deletions");
    pruning.commit().expect("publish retained period coverage");
    movement_blocks::retired(owner, campaign);
    owner
        .batch_execute("ANALYZE babylon_state.money_movement_block_v1")
        .expect("the statistical collector can sample an expired empty ledger");
    let population = "SELECT reltuples > 0 FROM pg_catalog.pg_class
        WHERE oid='babylon_state.money_movement_block_v1'::regclass";
    assert!(!owner
        .query_one(population, &[])
        .expect("read the sampled-empty movement estimate")
        .get::<_, bool>(0));
    let retained_rows: i64 = owner.query_one("SELECT count(*) FROM babylon_state.money_movement_v1 WHERE campaign_id=$1 AND resolve_tick=1",
        &[campaign.as_uuid()]).expect("expired detail count").get(0);
    assert_eq!(
        retained_rows, 0,
        "the nonzero source period has actually lost its stored detail"
    );
    assert_eq!(
        observer
            .money_totals(campaign, 1, 1)
            .expect("permanent expired totals"),
        totals,
        "purpose totals survive nonzero detail expiration exactly"
    );
    assert_eq!(
        observer
            .economic_payment_flows(campaign, &grouping)
            .expect("expired canonical payment facts"),
        warm
    );
    let independently_reauthenticated = observer
        .committed_material_receipts(campaign, 1)
        .expect("expired source independently reauthenticates");
    assert_eq!(
        observer
            .money_movements(campaign, 1)
            .expect("expired movements reconstruct"),
        journal::derive_movements(&independently_reauthenticated)
            .expect("independent source movements"),
        "every expired nonzero posting reconstructs from its independently authenticated source"
    );
    let point = PointScale::check_rejection(owner, observer, writer, campaign);
    assert_eq!(
        owner.execute("UPDATE babylon_state.money_movement_total_v1 SET amount_micros=amount_micros+1 WHERE campaign_id=$1 AND resolve_tick=1 AND purpose=$2",
            &[campaign.as_uuid(), &MoneyPurpose::DeliverySettlement.as_str()]).expect("confined permanent summary drift"),
        1,
        "one expired period summary is damaged without changing its movement count"
    );
    assert!(
        matches!(
            writer.publish(observer, campaign, 1),
            Err(JournalError::Projection)
        ),
        "repeat publication must detect an incorrect purpose sum even without retained detail"
    );
    // Reproduce stale empty planner estimates on the two real FK parents. The
    // rebuild must size them after staging new rows and before committing its edges.
    owner
        .batch_execute(
            "ANALYZE babylon_state.labor_node_block_v1; ANALYZE babylon_state.labor_node_identity_v1",
        )
        .expect("sample the actually empty parent relations");
    assert_eq!(labor_parent_row_estimates(owner), [0, 0]);
    point.set(owner, campaign, true);
    writer
        .rebuild(observer, campaign, 1)
        .expect("explicit authenticated rebuild restores current-window detail");
    point.require_original(owner, campaign);
    assert!(
        owner
            .query_one(population, &[])
            .expect("read the rebuilt movement estimate")
            .get::<_, bool>(0),
        "rebuilding nonempty national payments must replace the sampled-empty population estimate"
    );
    assert!(labor_parent_row_estimates(owner)
        .iter()
        .all(|count| *count > 0));
    assert_eq!(
        observer
            .money_totals(campaign, 1, 1)
            .expect("repaired permanent totals"),
        totals,
        "authenticated rebuild repairs the damaged purpose summary exactly"
    );
    assert_eq!(
        observer
            .money_movements(campaign, 1)
            .expect("rebuilt detail"),
        expected,
        "rebuild reproduces the original source ordinals and both postings"
    );
}

fn assert_source_faults(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
    expected: &[MoneyMovement],
    totals: &[MoneyTotal],
) {
    owner.execute("UPDATE babylon_state.material_tick_v3 SET receipt_storage_bytes=decode('00','hex') WHERE campaign_id=$1 AND resolve_tick=1",&[campaign.as_uuid()]).expect("confined packed source fault");
    assert_eq!(
        observer
            .money_movements(campaign, 1)
            .expect("warm retained detail uses SQL"),
        expected,
        "packed receipt decoding is absent from warm SQL query"
    );
    assert_eq!(
        observer
            .money_totals(campaign, 1, 1)
            .expect("warm aggregate uses SQL"),
        totals,
        "warm SQL aggregate does not decode packed source"
    );
    assert!(
        writer.rebuild(observer, campaign, 1).is_err(),
        "authenticated rebuild refuses corrupted source instead of reusing published facts"
    );
    owner.execute("UPDATE babylon_state.tick_commit SET tick_content_hash=decode(repeat('00',32),'hex') WHERE campaign_id=$1 AND resolve_tick=1",&[campaign.as_uuid()]).expect("confined marker fault");
    assert!(
        matches!(
            observer.money_totals(campaign, 1, 1),
            Err(JournalError::CoverageAbsent)
        ),
        "changed commit marker hides stale projected rows"
    );
    assert!(
        matches!(
            observer.money_movements(campaign, 1),
            Err(JournalError::CoverageAbsent)
        ),
        "changed marker cannot expose stale detail"
    );
}
