//! Full-observer labor windows authenticate the entire prefix and expose actual performed work.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::LaborFlowPage;
use babylon_persistence::observer_reader::{ObserverEconomyError, ObserverEconomyReader};
use babylon_persistence::qualification_audit::trade;
use babylon_persistence::recorded_labor::RecordedLaborPeriod;
use postgres::Config;
use serde::Deserialize;
use serde_json::Deserializer;
use std::io::BufReader;
use std::process::{Command, Stdio};

pub(super) fn restricted(reader: &ObserverEconomyReader, campaign: CampaignId) {
    use babylon_persistence::money_journal::{FlowGroup, JournalError};
    let request = super::payment_flows::query(FlowGroup::Location);
    assert_eq!(
        reader.recorded_labor_flows(campaign, &request),
        Err(JournalError::Authority)
    );
    assert!(matches!(
        reader.recorded_labor_window(campaign, 1, 2),
        Err(ObserverEconomyError::Authority)
    ));
}

#[derive(Deserialize)]
struct PeriodTotals {
    #[serde(rename = "opening_recorded_micro_hours")]
    opening: String,
    #[serde(rename = "closing_recorded_micro_hours")]
    closing: String,
    #[serde(rename = "direct_micro_hours")]
    direct: String,
}

#[derive(Deserialize)]
struct TraceOutput {
    campaign: String,
    tick: Option<u64>,
    tick_content_hash: Option<String>,
    receipt_sha256: Option<String>,
    labor: Option<PeriodTotals>,
    record: Option<String>,
    first: Option<u64>,
    last: Option<u64>,
}

fn immediate_totals(period: &RecordedLaborPeriod) -> (u128, u128, u128) {
    (
        period
            .edges
            .iter()
            .map(|edge| edge.basis.recorded_micro_hours)
            .sum::<u128>(),
        period
            .edges
            .iter()
            .filter(|edge| edge.basis.unknown_opening)
            .count() as u128,
        period.edges.len() as u128,
    )
}

pub(super) fn national(reader: &ObserverEconomyReader, config: &Config, campaign: CampaignId) {
    let mut window = reader
        .recorded_labor_window(campaign, 1, 2)
        .expect("full observer");
    let mut previous = 0;
    let mut expected = None;
    let mut movement_totals = Vec::new();
    for tick in 1..=2 {
        let report = window
            .next()
            .expect("complete window")
            .expect("authenticated material period");
        let source = reader
            .committed_material_receipts(campaign, tick)
            .expect("independent material audit");
        assert_eq!(report.tick, tick);
        assert_eq!(
            report.receipt_sha256,
            trade::hex(&source.identity.receipt_digest())
        );
        let period = report.labor;
        let attended: u128 = period
            .attendance
            .iter()
            .map(|row| u128::from(row.attended_hours))
            .sum();
        let source_attended: u128 = source
            .receipts
            .member_labor_use
            .iter()
            .map(|row| u128::from(row.attended_hours))
            .sum();
        assert_eq!(attended, source_attended);
        assert!(attended > 0 && period.direct_micro_hours > 0 && !period.edges.is_empty());
        assert_eq!(period.opening_recorded_micro_hours, previous);
        assert_eq!(
            previous + period.direct_micro_hours,
            period.closing_recorded_micro_hours + period.released_micro_hours
        );
        movement_totals.push(immediate_totals(&period));
        previous = period.closing_recorded_micro_hours;
        expected = Some((
            report.tick_content_hash,
            report.receipt_sha256,
            period.opening_recorded_micro_hours,
            period.closing_recorded_micro_hours,
            period.direct_micro_hours,
        ));
    }
    assert!(window.next().is_none());
    drop(window);
    compare_sql(reader, config, campaign, &movement_totals);
    let (tick_hash, receipt_hash, opening, closing, direct) =
        expected.expect("second committed period");
    assert!(
        opening > 0,
        "earlier recorded labor is carried into period two"
    );
    let id = campaign.as_uuid().to_string();
    let mut child = Command::new(env!("CARGO_BIN_EXE_babylon-economic-projections"))
        .args(["labor-trace", "--first", "2", "--campaign", &id])
        .env_clear()
        .env(
            "BABYLON_OBSERVER_DSN",
            super::runtime_process::child_dsn(config),
        )
        .stdout(Stdio::piped())
        .spawn()
        .expect("start read-only labor command");
    let records = BufReader::new(child.stdout.take().expect("piped trace"));
    let mut stream = Deserializer::from_reader(records).into_iter::<TraceOutput>();
    let row = stream
        .next()
        .expect("one selected period")
        .expect("typed trace");
    assert_eq!(row.campaign, id);
    assert_eq!(row.tick, Some(2));
    assert_eq!(row.tick_content_hash, Some(tick_hash));
    assert_eq!(row.receipt_sha256, Some(receipt_hash));
    let totals = row.labor.expect("carried second period");
    assert_eq!(totals.opening, opening.to_string());
    assert_eq!(totals.closing, closing.to_string());
    assert_eq!(totals.direct, direct.to_string());
    let end = stream
        .next()
        .expect("window completed")
        .expect("typed completion");
    assert_eq!(end.campaign, id);
    assert_eq!(end.record.as_deref(), Some("labor_trace_complete"));
    assert_eq!((end.first, end.last), (Some(2), Some(2)));
    assert!(stream.next().is_none());
    assert!(child.wait().expect("exit status").success());
}

fn compare_sql(
    reader: &ObserverEconomyReader,
    config: &Config,
    campaign: CampaignId,
    expected: &[(u128, u128, u128)],
) {
    use babylon_persistence::money_journal::{
        FlowGroup, FlowQuery, LaborAmount, LaborDirections, PeriodWindow,
    };
    let query = FlowQuery {
        window: PeriodWindow { first: 2, last: 2 },
        comparison: Some(PeriodWindow { first: 1, last: 1 }),
        group: FlowGroup::Location,
        focus: None,
        offset: 0,
        viewport_4269: None,
    };
    let page = query_labor_cli(config, campaign);
    assert_eq!(
        page.groups.len() as u64 + page.remainder.groups,
        page.total.groups
    );
    assert!(page.groups.len() <= 20);
    let number = |s: &str| s.parse::<u128>().expect("exact nonnegative integer");
    let measures = |a: &LaborAmount| {
        [
            number(&a.recorded_micro_hours),
            number(&a.unknown_basis_movements),
            number(&a.movement_count),
        ]
    };
    let check = |directions: &LaborDirections, (hours, unknown, movements): (u128, u128, u128)| {
        let wanted = [hours, unknown, movements];
        let inside = measures(&directions.within);
        for side in [&directions.inbound, &directions.outbound] {
            let external = measures(side);
            assert_eq!(
                [
                    external[0] + inside[0],
                    external[1] + inside[1],
                    external[2] + inside[2]
                ],
                wanted,
                "each immediate transfer counts once across its directed boundary"
            );
        }
        assert_eq!(directions.net_recorded_micro_hours, "0");
    };
    check(&page.total.current, expected[1]);
    check(
        page.total.comparison.as_ref().expect("prior period"),
        expected[0],
    );
    assert_eq!(
        page.total.net_change_recorded_micro_hours.as_deref(),
        Some("0")
    );
    let mut included = [0_u128; 3];
    for group in page.groups.iter().chain([&page.remainder]) {
        let amounts = measures(&group.current.outbound);
        for (sum, quantity) in included.iter_mut().zip(amounts) {
            *sum += quantity;
        }
    }
    assert_eq!(included,measures(&page.total.current.outbound),"top groups plus remainder conserve observed hours, attributed records and missing-basis counts");
    let last = reader
        .committed_material_receipts(campaign, 2)
        .expect("P2 source");
    let foundation = trade::hex(&last.identity.foundation_digest());
    assert!(reader
        .recorded_labor_flows_for_frame(campaign, &query, &foundation, &"0".repeat(64))
        .is_err());
}

pub(super) fn first_period_flows(
    reader: &ObserverEconomyReader,
    campaign: CampaignId,
) -> LaborFlowPage {
    use babylon_persistence::money_journal::{FlowGroup, FlowQuery, PeriodWindow};
    let request = FlowQuery {
        window: PeriodWindow { first: 1, last: 1 },
        comparison: None,
        group: FlowGroup::Location,
        focus: None,
        offset: 0,
        viewport_4269: None,
    };
    let page = reader
        .recorded_labor_flows(campaign, &request)
        .expect("first completed physical period");
    assert!(
        page.total.current.within.movement_count != "0"
            || page.total.current.outbound.movement_count != "0",
        "real physical movements exist in the control"
    );
    page
}

fn query_labor_cli(config: &Config, campaign: CampaignId) -> LaborFlowPage {
    #[derive(Deserialize)]
    struct Response {
        version: u32,
        campaign: String,
        unit: String,
        page: LaborFlowPage,
    }
    let id = campaign.as_uuid().to_string();
    let output = Command::new(env!("CARGO_BIN_EXE_babylon-money-journal"))
        .args([
            "flows",
            "--measure",
            "labor",
            "--campaign",
            &id,
            "--first",
            "2",
            "--compare-first",
            "1",
            "--group",
            "location",
        ])
        .env_clear()
        .env(
            "BABYLON_OBSERVER_DSN",
            super::runtime_process::child_dsn(config),
        )
        .output()
        .expect("run the ranked labor query with observer-only access");
    assert!(
        output.status.success(),
        "ranked labor query: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let response: Response =
        serde_json::from_slice(&output.stdout).expect("versioned ranked labor data");
    assert_eq!(response.version, 1);
    assert_eq!(response.campaign, id);
    assert_eq!(response.unit, "recorded_micro_hours");
    response.page
}
