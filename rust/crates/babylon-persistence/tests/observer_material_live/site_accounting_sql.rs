//! SQL statement and stock parity against the authenticated site reader.
use babylon_material_circuit::{AccountId, CircuitAccounting, SiteId};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::material_runtime::DurableMaterialRuntime;
use babylon_persistence::money_journal::{
    JournalError, MoneyJournalWriter, PeriodWindow, PublishedSitePeriod,
};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use babylon_persistence::qualification_audit::trade;
use postgres::types::ToSql;
use postgres::{Client, Config};
use serde_json::Value;
use std::collections::BTreeMap;
use std::process::Command;

pub(super) fn national(
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    owner: &mut Client,
    campaign: CampaignId,
    site: SiteId,
) {
    let source = observer
        .site_financial_statements(campaign, 1, site)
        .expect("source site");
    let saved = observer
        .published_site_period(campaign, 1, site)
        .expect("stored site");
    county_accounts(observer, owner, &saved);
    let summary = saved.statement.as_ref().expect("monetary site");
    let activity = source.books.activity.as_ref().expect("period activity");
    assert_eq!(source.books.opening.as_ref(), Some(&summary.opening));
    assert_eq!(source.books.closing, summary.closing);
    assert_eq!(activity.income, summary.income);
    assert_eq!(activity.change_in_equity, summary.change_in_equity);
    assert_eq!(activity.cash_flow.operating, summary.cash_flow.operating);
    assert_eq!(activity.cash_flow.investing, summary.cash_flow.investing);
    assert_eq!(activity.cash_flow.financing, summary.cash_flow.financing);
    assert_eq!(
        activity.cash_flow.reserve_reclassification,
        summary.cash_flow.reserve_reclassification
    );
    assert_eq!(Some(saved.receipt_sha256), source.receipt_digest);
    let history = observer
        .published_site_history(campaign, PeriodWindow { first: 1, last: 2 }, site)
        .expect("retained history across expired and warm movement periods");
    assert_eq!(history.len(), 2);
    assert_eq!(history[0], saved);
    assert_eq!(history[1].resolve_tick, 2);
    assert_eq!(
        history[1]
            .statement
            .as_ref()
            .expect("next monetary site")
            .opening,
        summary.closing
    );
    assert_eq!(
        observer.published_site_history(campaign, PeriodWindow { first: 1, last: 3 }, site),
        Err(JournalError::CoverageAbsent)
    );
    assert_eq!(
        observer.published_site_period(campaign, 1, SiteId::from_bytes([0xff; 32])),
        Err(JournalError::SiteAbsent)
    );
    assert_eq!(owner.execute("UPDATE babylon_state.site_statement_v1 SET income_productive_labor_capitalized_micros=income_productive_labor_capitalized_micros+1 WHERE campaign_id=$1 AND resolve_tick=1 AND site_id=$2", &[campaign.as_uuid(), &site.as_bytes().as_slice()]).expect("alter book disclosure"), 1);
    assert_eq!(
        observer.published_site_period(campaign, 1, site),
        Err(JournalError::Projection)
    );
    let stock_owner = corrupt_stock(owner, observer, campaign, site);
    assert_eq!(owner.execute("DELETE FROM babylon_state.site_statement_v1 WHERE campaign_id=$1 AND resolve_tick=1 AND site_id=$2", &[campaign.as_uuid(), &site.as_bytes().as_slice()]).expect("one disposable damaged statement"), 1);
    assert_eq!(
        observer.published_site_period(campaign, 1, site),
        Err(JournalError::Projection)
    );
    assert_eq!(
        writer.publish(observer, campaign, 1),
        Err(JournalError::Projection)
    );
    assert!(
        writer
            .rebuild(observer, campaign, 1)
            .expect("rebuild completes")
            .changed
    );
    assert_eq!(
        observer
            .published_site_period(campaign, 1, site)
            .expect("rebuilt site"),
        saved
    );
    assert_eq!(
        observer
            .published_site_period(campaign, 1, stock_owner.site_id)
            .expect("restored source stock"),
        stock_owner
    );
}

fn corrupt_stock(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    different_site: SiteId,
) -> PublishedSitePeriod {
    let row=owner.query_one("SELECT site_id, good_id, unit_id FROM babylon_state.site_stock_balance_v1 WHERE campaign_id=$1 AND resolve_tick=1 AND site_id<>$2 AND closing_quantity < 18446744073709551615 ORDER BY site_id,good_id,unit_id LIMIT 1",&[campaign.as_uuid(),&different_site.as_bytes().as_slice()]).expect("real national stock");
    let site = row.get::<_, Vec<u8>>("site_id");
    let good = row.get::<_, Vec<u8>>("good_id");
    let unit = row.get::<_, Vec<u8>>("unit_id");
    let id = SiteId::from_bytes(site.as_slice().try_into().expect("stock identity"));
    let saved = observer
        .published_site_period(campaign, 1, id)
        .expect("validated source stock");
    let params: &[&(dyn ToSql + Sync)] = &[campaign.as_uuid(), &site, &good, &unit];
    assert_eq!(owner.execute("UPDATE babylon_state.site_stock_balance_v1 SET closing_quantity=closing_quantity+1 WHERE campaign_id=$1 AND resolve_tick=1 AND site_id=$2 AND good_id=$3 AND unit_id=$4",params).expect("change one stock quantity"),1);
    assert_eq!(
        observer.published_site_period(campaign, 1, id),
        Err(JournalError::Projection)
    );
    assert_eq!(owner.execute("DELETE FROM babylon_state.site_stock_balance_v1 WHERE campaign_id=$1 AND resolve_tick=1 AND site_id=$2 AND good_id=$3 AND unit_id=$4",params).expect("remove one selected stock"),1);
    assert_eq!(
        observer.published_site_period(campaign, 1, id),
        Err(JournalError::Projection)
    );
    saved
}

pub(super) fn stocks(
    runtime: &DurableMaterialRuntime,
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    tick: u64,
) -> SiteId {
    let state = runtime.session().material().state();
    let first = state.inventory.first().expect("actual material stock");
    let saved = observer
        .published_site_period(campaign, tick, first.site_id)
        .expect("covered stock owner");
    let actual: BTreeMap<_, _> = saved
        .stocks
        .iter()
        .filter_map(|r| r.closing.map(|p| ((r.good_id, r.unit_id), p)))
        .collect();
    let costs = match &state.accounting {
        CircuitAccounting::Monetary(books) => Some(books.costs.snapshot()),
        CircuitAccounting::PhysicalControl => None,
    };
    assert_eq!(saved.statement.is_some(), costs.is_some());
    if costs.is_none() {
        assert_eq!(
            observer
                .county_site_accounts_for_frame(
                    campaign,
                    tick,
                    "26163".try_into().expect("Wayne"),
                    &trade::hex(&saved.foundation_sha256),
                    &trade::hex(&saved.tick_content_hash),
                    0,
                )
                .expect("authenticated physical period"),
            babylon_persistence::money_journal::CountySiteAccounts::PhysicalOnly
        );
    }
    let mut count = 0;
    for row in state
        .inventory
        .iter()
        .filter(|r| r.site_id == first.site_id)
    {
        let position = actual
            .get(&(row.good_id, row.unit_id))
            .expect("stock principal in native units");
        assert_eq!(position.quantity, row.quantity);
        let basis = costs.as_ref().map(|book| {
            book.stocks
                .iter()
                .find(|stock| {
                    stock.owner == AccountId::Site(row.site_id)
                        && stock.good_id == row.good_id
                        && stock.unit_id == row.unit_id
                })
                .expect("source carrying value")
                .amount
        });
        assert_eq!(position.carrying_cost, basis);
        count += 1;
    }
    assert_eq!(actual.len(), count);
    first.site_id
}

pub(super) fn restricted(observer: &ObserverEconomyReader, campaign: CampaignId, site: SiteId) {
    assert_eq!(
        observer.county_site_accounts_for_frame(
            campaign,
            1,
            "26163".try_into().expect("Wayne"),
            "",
            "",
            0
        ),
        Err(JournalError::Authority)
    );
    assert_eq!(
        observer.published_site_period(campaign, 1, site),
        Err(JournalError::Authority)
    );
}

pub(super) fn cli(config: &Config, expected: &PublishedSitePeriod, last: u64) {
    let campaign = expected.campaign_id.as_uuid().to_string();
    let site = trade::hex(&expected.site_id.as_bytes());
    let output = Command::new(env!("CARGO_BIN_EXE_babylon-money-journal"))
        .args([
            "site-history",
            "--campaign",
            &campaign,
            "--site",
            &site,
            "--first",
            &expected.resolve_tick.to_string(),
            "--last",
            &last.to_string(),
        ])
        .env(
            "BABYLON_OBSERVER_DSN",
            super::runtime_process::child_dsn(config),
        )
        .env_remove("BABYLON_RUNTIME_DSN")
        .output()
        .expect("start actual compact history command");
    assert!(
        output.status.success(),
        "site-history refused: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let json: Value = serde_json::from_slice(&output.stdout).expect("versioned journal JSON");
    assert_eq!(json["campaign"], campaign);
    assert_eq!(json["unit"], "currency_micros");
    let periods = json["periods"].as_array().expect("period rows");
    assert_eq!(
        u64::try_from(periods.len()).expect("period count fits u64"),
        last - expected.resolve_tick + 1
    );
    assert_eq!(periods[0]["site_id"], site);
    assert_eq!(
        periods[0]["receipt_sha256"],
        trade::hex(&expected.receipt_sha256)
    );
    if let Some(summary) = &expected.statement {
        assert_eq!(
            periods[0]["statement"]["net_income_micros"],
            summary.income.net_income.micro_units().to_string()
        );
    } else {
        assert!(periods[0]["statement"].is_null());
        let stocks = periods[0]["stocks"]
            .as_array()
            .expect("physical stock rows");
        assert!(stocks
            .iter()
            .any(|row| row["closing"]["quantity"].is_string()));
        assert!(stocks
            .iter()
            .all(|row| row["closing"]["carrying_cost_micros"].is_null()));
    }
}

fn county_accounts(
    observer: &ObserverEconomyReader,
    owner: &mut Client,
    frame: &PublishedSitePeriod,
) {
    use babylon_persistence::money_journal::CountySiteAccounts;
    let campaign = frame.campaign_id;
    let county = "26163".try_into().expect("Wayne");
    let foundation = trade::hex(&frame.foundation_sha256);
    let tick_hash = trade::hex(&frame.tick_content_hash);
    let expected = owner.query(
        "SELECT s.site_id, s.closing_cash_micros::text, s.opening_cash_micros::text, s.net_income_micros::text,
                s.closing_retained_earnings_micros::text FROM babylon_state.site_statement_v1 s
          WHERE s.campaign_id=$1 AND s.resolve_tick=1 AND EXISTS
                (SELECT 1 FROM babylon_state.economic_flow_account_v1 a WHERE a.campaign_id=s.campaign_id
                 AND a.account_kind='site_cash' AND a.account_id=s.site_id AND a.location_key='county:26163')
          ORDER BY s.site_id", &[campaign.as_uuid()]).expect("independent actual-site rows");
    assert!(
        expected.len() > 6,
        "national Wayne fixture exercises paging"
    );
    let mut totals = [0_i128; 3];
    let mut members = Vec::new();
    for row in &expected {
        let num = |index: usize| {
            row.get::<_, &str>(index)
                .parse::<i128>()
                .expect("exact micros")
        };
        totals[0] += num(1) - num(2);
        totals[1] += num(3);
        totals[2] += num(4);
        members.push(SiteId::from_bytes(
            row.get::<_, &[u8]>(0).try_into().expect("site"),
        ));
    }
    let mut read = Vec::new();
    for pos in (0..members.len()).step_by(6) {
        let CountySiteAccounts::Monetary(page) = observer
            .county_site_accounts_for_frame(
                campaign,
                1,
                county,
                &foundation,
                &tick_hash,
                u64::try_from(pos).expect("site index"),
            )
            .expect("county accounts")
        else {
            panic!("national books are monetary")
        };
        assert_eq!(
            usize::try_from(page.site_count).expect("site count"),
            members.len()
        );
        assert_eq!(
            [
                page.cash_change_micros,
                page.period_profit_micros,
                page.closing_retained_earnings_micros
            ],
            totals.map(|value| value.to_string())
        );
        read.extend(page.sites);
    }
    assert_eq!(read, members);
    assert_eq!(
        observer.county_site_accounts_for_frame(
            campaign,
            1,
            county,
            &foundation,
            &"00".repeat(32),
            0
        ),
        Err(JournalError::SourceChanged)
    );
}
