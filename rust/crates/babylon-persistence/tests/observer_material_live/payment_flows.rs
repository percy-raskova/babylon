//! Real full-observer settlement, geographic scope and rank reconciliation.
#[path = "payment_registry.rs"]
mod payment_registry;

use babylon_material_circuit::CompanyId;
use babylon_persistence::company_statements::CompanyPeriodReport;
use babylon_persistence::economic_flows::EconomicPaymentPeriod;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{
    FlowAmounts, FlowDirection, FlowGroup, FlowPage, FlowPeer, FlowQuery, FlowViewport,
    JournalError, MoneyMovement, MoneyPurpose, PeriodWindow,
};
use babylon_persistence::observer_reader::{ObserverEconomyReader, ObserverMaterialCursor};
use babylon_persistence::qualification_audit::trade;
use postgres::{Client, Config, NoTls};
use std::collections::BTreeMap;

pub(super) fn query(group: FlowGroup) -> FlowQuery {
    FlowQuery {
        group,
        window: PeriodWindow { first: 1, last: 1 },
        comparison: None,
        peer: None,
        focus_group: None,
        focus: None,
        offset: 0,
        viewport_4269: None,
    }
}

pub(super) fn restricted(observer: &ObserverEconomyReader, campaign: CampaignId) {
    assert!(matches!(
        observer.company_decision_receipt(campaign, 1, CompanyId::from_bytes([0; 32])),
        Err(babylon_persistence::observer_reader::ObserverEconomyError::Authority)
    ));
    assert_eq!(
        observer.published_company_period_statements(campaign, 1),
        Err(JournalError::Authority)
    );
    assert_eq!(
        observer.economic_payment_flows(campaign, &query(FlowGroup::Location)),
        Err(JournalError::Authority)
    );
}

fn micros(value: &str) -> i128 {
    value
        .parse()
        .expect("national audit amount fits exact i128")
}

fn reconcile(page: &FlowPage) {
    assert_eq!(
        page.groups.iter().map(|r| r.groups).sum::<u64>() + page.remainder.groups,
        page.total.groups
    );
    let lines: [fn(&FlowAmounts) -> &str; 4] = [
        |v| &v.inflow_micros,
        |v| &v.outflow_micros,
        |v| &v.internal_micros,
        |v| &v.net_micros,
    ];
    for line in lines {
        assert_eq!(
            page.groups
                .iter()
                .map(|r| micros(line(&r.current)))
                .sum::<i128>()
                + micros(line(&page.remainder.current)),
            micros(line(&page.total.current))
        );
    }
}

fn check_source_rows(
    source: &EconomicPaymentPeriod,
    sql: &mut Client,
    campaign: CampaignId,
    moves: &[MoneyMovement],
) {
    let rows=sql.query("SELECT ordinal,purpose,payer_kind,payer_id,recipient_kind,recipient_id,amount_micros::text \
      FROM public.v_observer_economic_payment_v1 WHERE campaign_id=$1 AND resolve_tick=1 ORDER BY ordinal",
      &[campaign.as_uuid()]).expect("observer settlement detail");
    assert_eq!(rows.len(), source.settlements.len());
    assert!(rows.len() < moves.len(), "reserve postings are separate");
    for (row, s) in rows.iter().zip(&source.settlements) {
        let ordinal = u64::try_from(row.get::<_, i64>("ordinal")).expect("nonnegative SQL ordinal");
        assert_eq!(ordinal, s.ordinal);
        let m = &moves[usize::try_from(ordinal).expect("source ordinal fits")];
        assert_eq!(row.get::<_, &str>("purpose"), m.purpose.as_str());
        assert_eq!(row.get::<_, &str>("amount_micros"), m.amount_micros);
        assert_eq!(row.get::<_, &str>("payer_kind"), s.payer.kind.as_str());
        assert_eq!(row.get::<_, Vec<u8>>("payer_id"), s.payer.id);
        assert_eq!(
            row.get::<_, &str>("recipient_kind"),
            s.recipient.kind.as_str()
        );
        assert_eq!(row.get::<_, Vec<u8>>("recipient_id"), s.recipient.id);
    }
}

fn wayne_viewport(
    source: &EconomicPaymentPeriod,
    sql: &mut Client,
    campaign: CampaignId,
) -> FlowViewport {
    let key = "county:26163";
    let anchor = source
        .accounts
        .iter()
        .find(|a| a.location.as_deref() == Some(key))
        .and_then(|a| a.county_internal_point.as_ref())
        .expect("captured Wayne county proxy");
    let lon: f64 = anchor.longitude.parse().expect("captured longitude");
    let lat: f64 = anchor.latitude.parse().expect("captured latitude");
    let row=sql.query_one("SELECT point_basis,public.ST_SRID(county_internal_point),\
        longitude=$2::text::numeric AND latitude=$3::text::numeric AS matches_source \
        FROM public.v_observer_economic_flow_location_v1 WHERE campaign_id=$1 AND location_key='county:26163'",
        &[campaign.as_uuid(),&anchor.longitude,&anchor.latitude]).expect("Wayne county geometry");
    assert_eq!(row.get::<_, &str>(0), "tiger_county_internal_point");
    assert_eq!(row.get::<_, i32>(1), 4269);
    assert!(row.get::<_, bool>("matches_source"));
    let missing:i64=sql.query_one("SELECT count(*) FROM public.v_observer_economic_flow_account_v1 a \
        LEFT JOIN public.v_observer_economic_flow_location_v1 l USING(campaign_id,location_key) \
        WHERE a.campaign_id=$1 AND (a.location_key IS NULL OR a.location_key NOT LIKE 'county:%') AND l.location_key IS NULL",
        &[campaign.as_uuid()]).expect("unlocated accounts counted separately").get(0);
    assert!(
        missing > 0,
        "national foreign or unlocated accounts receive no synthetic point"
    );
    FlowViewport {
        west: lon - 0.000_001,
        south: lat - 0.000_001,
        east: lon + 0.000_001,
        north: lat + 0.000_001,
    }
}

fn check_location_amounts(
    source: &EconomicPaymentPeriod,
    moves: &[MoneyMovement],
    key: &str,
    page: &FlowPage,
) {
    let accounts: BTreeMap<_, _> = source
        .accounts
        .iter()
        .map(|a| {
            (
                (a.account.kind.as_str(), a.account.id),
                a.location.as_deref(),
            )
        })
        .collect();
    let (mut i, mut o, mut t) = (0_i128, 0_i128, 0_i128);
    for s in &source.settlements {
        let payer = accounts[&(s.payer.kind.as_str(), s.payer.id)] == Some(key);
        let recipient = accounts[&(s.recipient.kind.as_str(), s.recipient.id)] == Some(key);
        let amount =
            micros(&moves[usize::try_from(s.ordinal).expect("source ordinal index")].amount_micros);
        match (payer, recipient) {
            (true, true) => t += amount,
            (true, false) => o += amount,
            (false, true) => i += amount,
            (false, false) => {}
        }
    }
    assert_eq!(
        page.total.current,
        FlowAmounts {
            inflow_micros: i.to_string(),
            outflow_micros: o.to_string(),
            internal_micros: t.to_string(),
            net_micros: (i - o).to_string()
        }
    );
    assert_eq!(
        page.total.groups, 1,
        "only the captured Wayne county proxy is inside the small viewport"
    );
    assert_eq!(page.groups[0].key.as_deref(), Some(key));
}

fn unknown_industry(source: &EconomicPaymentPeriod, moves: &[MoneyMovement], page: &FlowPage) {
    let accounts: BTreeMap<_, _> = source
        .accounts
        .iter()
        .map(|a| ((a.account.kind.as_str(), a.account.id), a.industry.as_ref()))
        .collect();
    let (mut incoming, mut outgoing, mut internal, mut ambiguous) =
        (0_i128, 0_i128, 0_i128, 0_i128);
    for payment in &source.settlements {
        let payer = (payment.payer.kind.as_str(), payment.payer.id);
        let recipient = (payment.recipient.kind.as_str(), payment.recipient.id);
        let index = usize::try_from(payment.ordinal).expect("canonical ordinal");
        let amount = micros(&moves[index].amount_micros);
        let missing_payer = accounts[&payer].is_none();
        let missing_recipient = accounts[&recipient].is_none();
        if payer == recipient && missing_payer {
            internal += amount;
            continue;
        }
        if missing_payer {
            outgoing += amount;
        }
        if missing_recipient {
            incoming += amount;
        }
        if missing_payer && missing_recipient {
            ambiguous += amount;
        }
    }
    assert!(
        ambiguous > 0,
        "actual national transfers include differently owned unclassified accounts"
    );
    let row = page
        .groups
        .iter()
        .find(|r| r.key.is_none())
        .expect("explicit unknown industry group");
    assert_eq!(
        row.current,
        FlowAmounts {
            inflow_micros: incoming.to_string(),
            outflow_micros: outgoing.to_string(),
            internal_micros: internal.to_string(),
            net_micros: (incoming - outgoing).to_string()
        }
    );
}

pub(super) fn national(
    observer: &ObserverEconomyReader,
    config: &Config,
    campaign: CampaignId,
    moves: &[MoneyMovement],
) {
    let mut cursor = None;
    let source = observer
        .committed_economic_payments_with_cursor(campaign, 1, &mut cursor)
        .expect("canonical economic principals");
    let mut sql = config.connect(NoTls).expect("observer SQL");
    check_company_decision(
        config,
        campaign,
        cursor.as_ref().expect("full-observer cursor"),
        source.source.identity.tick_content_hash().as_bytes(),
    );
    check_source_rows(&source, &mut sql, campaign, moves);
    unknown_industry(
        &source,
        moves,
        &observer
            .economic_payment_flows(campaign, &query(FlowGroup::Industry))
            .expect("unknown industry postings"),
    );
    let mut q = query(FlowGroup::Account);
    q.comparison = Some(q.window);
    let page = observer
        .economic_payment_flows(campaign, &q)
        .expect("SQL account ranking");
    assert_eq!(page.groups.len(), 20);
    assert!(page.remainder.groups > 0);
    assert_eq!(
        page.total.net_change_micros.as_deref(),
        Some("0"),
        "same-period change"
    );
    assert_eq!(page.total.current.net_micros, "0");
    let gross: i128 = moves
        .iter()
        .filter(|m| {
            !matches!(
                m.purpose,
                MoneyPurpose::PurchaseReservation
                    | MoneyPurpose::PurchaseRefund
                    | MoneyPurpose::ShiftReservation
                    | MoneyPurpose::ShiftCancellation
            )
        })
        .map(|m| micros(&m.amount_micros))
        .sum();
    assert_eq!(
        gross,
        micros(&page.total.current.inflow_micros) + micros(&page.total.current.internal_micros)
    );
    reconcile(&page);
    for group in [FlowGroup::Company, FlowGroup::Counterparty] {
        let grouped = observer
            .economic_payment_flows(campaign, &query(group))
            .expect("company-aware cash endpoints");
        reconcile(&grouped);
        assert_eq!(
            gross,
            micros(&grouped.total.current.inflow_micros)
                + micros(&grouped.total.current.internal_micros)
        );
    }
    check_company_dimensions(&source, &mut sql, campaign);
    let stored = observer
        .published_company_period_statements(campaign, 1)
        .expect("durable parent and consolidated books");
    let replayed = observer
        .company_period_statements(campaign, 1)
        .expect("independent authenticated replay");
    assert_eq!(stored, replayed);
    assert_eq!(stored.companies.len(), 99);
    check_selected_company(observer, &mut sql, campaign, &stored);
    check_county_counterparties(&source, moves, observer, campaign);
    q.offset = 20;
    let next = observer
        .economic_payment_flows(campaign, &q)
        .expect("expanded remainder");
    assert_eq!(next.total, page.total);
    assert_eq!(next.groups[0].rank, Some(21));
    reconcile(&next);
    let mut spatial = query(FlowGroup::Location);
    spatial.viewport_4269 = Some(wayne_viewport(&source, &mut sql, campaign));
    let filtered = observer
        .economic_payment_flows(campaign, &spatial)
        .expect("qualified NAD83 viewport");
    check_location_amounts(&source, moves, "county:26163", &filtered);
    let missing = FlowQuery {
        window: PeriodWindow { first: 1, last: 2 },
        ..query(FlowGroup::Industry)
    };
    assert_eq!(
        observer.economic_payment_flows(campaign, &missing),
        Err(JournalError::CoverageAbsent)
    );
}

fn check_company_decision(
    config: &Config,
    campaign: CampaignId,
    cursor: &ObserverMaterialCursor,
    content_hash: &[u8; 32],
) {
    let register = cursor.current_register().expect("authenticated register");
    let evidence = register
        .company_portfolios()
        .expect("national portfolio register")
        .companies
        .iter()
        .find(|c| !c.processes.is_empty())
        .expect("company with production evidence");
    let company = trade::hex(&evidence.company.as_bytes());
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_babylon-economic-projections"))
        .env_clear()
        .env(
            "BABYLON_OBSERVER_DSN",
            super::runtime_process::child_dsn(config),
        )
        .args([
            "company-decision",
            "--campaign",
            &campaign.as_uuid().to_string(),
            "--period",
            "1",
            "--company",
            &company,
        ])
        .output()
        .expect("run full-observer decision inspection");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let decision: serde_json::Value =
        serde_json::from_slice(&output.stdout).expect("one decision report");
    assert_eq!(decision["version"], 1);
    assert_eq!(decision["campaign"], campaign.as_uuid().to_string());
    assert_eq!(decision["tick_content_hash"], trade::hex(content_hash));
    assert_eq!(decision["company"], company);
    assert_eq!(decision["resolve_tick"], 1);
    assert_eq!(
        decision["evidence"]["operating_income_micros"][0],
        evidence.history[0].micro_units().to_string()
    );
    assert_eq!(
        decision["evidence"]["processes"]
            .as_array()
            .expect("process list")
            .len(),
        evidence.processes.len()
    );
    let alternatives = decision["alternatives"]
        .as_array()
        .expect("four alternatives");
    assert_eq!(alternatives.len(), 4);
    for (i, row) in alternatives.iter().enumerate() {
        assert_eq!(row["original_weight"], evidence.original_weights[i]);
        assert_eq!(row["eligible_weight"], evidence.weights[i]);
        assert_eq!(row["feasible"], evidence.feasible[i]);
        assert_eq!(
            row["plan"].as_array().expect("process limits").len(),
            evidence.plans[i].len()
        );
    }
    let winner = alternatives
        .iter()
        .find(|r| r["member"] == decision["selected_outcome"])
        .expect("receipt selects one enumerated branch");
    assert_eq!(winner["feasible"], true);
    assert!(winner["eligible_weight"].as_u64().expect("eligible weight") > 0);
}

fn check_selected_company(
    observer: &ObserverEconomyReader,
    sql: &mut Client,
    campaign: CampaignId,
    stored: &CompanyPeriodReport,
) {
    let first = &stored.companies[0];
    let company_bytes: Vec<u8> = sql
        .query_one("SELECT decode($1,'hex')", &[&first.company])
        .expect("actual company identity")
        .get(0);
    let company = CompanyId::from_bytes(company_bytes.try_into().expect("company identifier"));
    let books = observer
        .company_accounts_for_frame(
            campaign,
            1,
            company,
            &stored.foundation_sha256,
            &stored.tick_content_hash,
        )
        .expect("selected parent and consolidated books");
    assert_eq!(books.parent, first.parent);
    assert_eq!(books.consolidated, first.consolidated);
    assert_eq!(books.eliminations, first.eliminations);
    assert_eq!(
        observer.company_accounts_for_frame(
            campaign,
            1,
            company,
            &stored.foundation_sha256,
            &"0".repeat(64)
        ),
        Err(JournalError::SourceChanged)
    );
}

fn account_nets(source: &EconomicPaymentPeriod) -> BTreeMap<String, i128> {
    let mut nets = BTreeMap::new();
    for row in &source.settlements {
        let amount = source.source.receipts.money_transfers
            [usize::try_from(row.ordinal).expect("settlement ordinal index")]
        .credit
        .delta
        .micro_units();
        let payer = format!("{}:{}", row.payer.kind.as_str(), trade::hex(&row.payer.id));
        let recipient = format!(
            "{}:{}",
            row.recipient.kind.as_str(),
            trade::hex(&row.recipient.id)
        );
        *nets.entry(payer).or_default() -= amount;
        *nets.entry(recipient).or_default() += amount;
    }
    nets
}

pub(super) fn comparison(observer: &ObserverEconomyReader, campaign: CampaignId) {
    let mut cursor = None;
    let prior = observer
        .committed_economic_payments_with_cursor(campaign, 1, &mut cursor)
        .expect("first canonical payments");
    let later = observer
        .committed_economic_payments_with_cursor(campaign, 2, &mut cursor)
        .expect("second canonical payments");
    let before = account_nets(&prior);
    let after = account_nets(&later);
    let (key, current) = after
        .iter()
        .find(|(key, value)| before.get(*key).copied().unwrap_or(0) != **value)
        .expect("two national periods have a changing account net");
    let previous = before.get(key).copied().unwrap_or(0);
    let q = FlowQuery {
        window: PeriodWindow { first: 2, last: 2 },
        comparison: Some(PeriodWindow { first: 1, last: 1 }),
        focus: Some(key.clone()),
        ..query(FlowGroup::Account)
    };
    let report = observer
        .economic_payment_flows(campaign, &q)
        .expect("focused counterparties for unequal periods");
    // A payer's outflow is the recipient's inflow; report totals sum the counterparty perspectives.
    assert_eq!(micros(&report.total.current.net_micros), -current);
    assert_eq!(
        micros(
            &report
                .total
                .comparison
                .as_ref()
                .expect("requested comparison")
                .net_micros
        ),
        -previous
    );
    assert_eq!(
        micros(
            report
                .total
                .net_change_micros
                .as_deref()
                .expect("change from prior period")
        ),
        previous - current
    );
    reconcile(&report);
}

fn check_company_dimensions(
    source: &EconomicPaymentPeriod,
    sql: &mut Client,
    campaign: CampaignId,
) {
    let mut expected = BTreeMap::new();
    for account in &source.accounts {
        let company = account
            .company
            .map(|key| (key.id().as_bytes().to_vec(), key.label()));
        expected.insert(
            (
                account.account.kind.as_str().to_owned(),
                account.account.id.to_vec(),
            ),
            company,
        );
    }
    for row in sql.query("SELECT account_kind,account_id,company_id,company_label FROM public.v_observer_economic_flow_account_v2 WHERE campaign_id=$1",&[campaign.as_uuid()]).expect("authenticated account dimensions"){
        let key=(row.get::<_,String>(0),row.get::<_,Vec<u8>>(1));
        let group=row.get::<_,Option<Vec<u8>>>(2).zip(row.get::<_,Option<String>>(3));
        if key.0=="household_cash"||key.0=="public_cash"||key.0=="organization_cash"{assert!(group.is_none());}
        assert_eq!(expected.remove(&key),Some(group));
    }
    assert!(expected.is_empty());
    let checks=sql.query_one("WITH c AS (SELECT * FROM public.v_observer_economic_company_v1 WHERE campaign_id=$1),
        m AS (SELECT company_id,count(*) AS sites,sum(opening_employed) AS employed,sum(swept_micros) AS swept,
            sum(original_capital_micros) AS capital FROM public.v_observer_economic_company_member_v1 WHERE campaign_id=$1 GROUP BY company_id),
        claims AS (SELECT * FROM public.v_observer_economic_company_claim_v1 WHERE campaign_id=$1),
        sources AS (SELECT s.company_id,s.beneficiary_kind,s.beneficiary_id,
            sum(s.capital_micros*s.original_shares*div(c.common_denominator,s.site_total_shares)) AS weight
            FROM public.v_observer_economic_company_claim_source_v1 s JOIN c USING(company_id)
            WHERE s.campaign_id=$1 GROUP BY s.company_id,s.beneficiary_kind,s.beneficiary_id)
        SELECT (SELECT count(*) FROM c),
            NOT EXISTS(SELECT FROM c LEFT JOIN m USING(company_id)
            WHERE (c.sites,c.employed,c.opening_cash_micros,c.original_capital_micros)
                IS DISTINCT FROM (m.sites,m.employed,m.swept,m.capital)),
            NOT EXISTS(SELECT FROM sources s FULL JOIN claims b USING(company_id,beneficiary_kind,beneficiary_id)
            WHERE s.weight IS DISTINCT FROM b.weight),
            NOT EXISTS(SELECT FROM c WHERE c.total_weight IS DISTINCT FROM
                (SELECT sum(claims.weight) FROM claims WHERE claims.company_id=c.company_id))",
        &[campaign.as_uuid()]).expect("source claims recombine with exact integer arithmetic");
    assert_eq!(checks.get::<_, i64>(0), 99);
    assert!(checks.get::<_, bool>(1) && checks.get::<_, bool>(2) && checks.get::<_, bool>(3));
}

fn directional_micros(amounts: &FlowAmounts) -> [i128; 3] {
    [
        micros(&amounts.inflow_micros),
        micros(&amounts.outflow_micros),
        micros(&amounts.internal_micros),
    ]
}

fn check_county_counterparties(
    source: &EconomicPaymentPeriod,
    moves: &[MoneyMovement],
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
) {
    let accounts: BTreeMap<_, _> = source
        .accounts
        .iter()
        .map(|a| ((a.account.kind.as_str(), a.account.id), a))
        .collect();
    let mut expected = BTreeMap::<String, [i128; 3]>::new();
    let mut places = BTreeMap::new();
    let home = Some("county:26163");
    for s in &source.settlements {
        let payer = accounts[&(s.payer.kind.as_str(), s.payer.id)];
        let recipient = accounts[&(s.recipient.kind.as_str(), s.recipient.id)];
        let (peer, dir) = match (
            payer.location.as_deref() == home,
            recipient.location.as_deref() == home,
        ) {
            (true, true) => (payer, 2),
            (true, false) => (recipient, 0),
            (false, true) => (payer, 1),
            (false, false) => continue,
        };
        let key = peer.company.map_or_else(
            || {
                format!(
                    "{}:{}",
                    peer.account.kind.as_str(),
                    trade::hex(&peer.account.id)
                )
            },
            |c| format!("company:{}", trade::hex(&c.identity())),
        );
        let n = micros(&moves[usize::try_from(s.ordinal).expect("ordinal")].amount_micros);
        *places
            .entry((key.clone(), dir, peer.location.clone()))
            .or_insert(0_i128) += n;
        expected.entry(key).or_default()[dir] += n;
    }
    let scoped = FlowQuery {
        focus: home.map(str::to_owned),
        focus_group: Some(FlowGroup::Location),
        ..query(FlowGroup::Counterparty)
    };
    let page = observer
        .economic_payment_flows(campaign, &scoped)
        .expect("rank counterparties of Wayne");
    let total = expected
        .values()
        .fold([0; 3], |[i, o, t], v| [i + v[0], o + v[1], t + v[2]]);
    assert_eq!(directional_micros(&page.total.current), total);
    assert!(total[2] > 0);
    assert!(expected.keys().any(|k| k.starts_with("company:")));
    assert!(expected.keys().any(|k| k.starts_with("household_cash:")));
    assert_eq!(page.total.groups, expected.len() as u64);
    for row in &page.groups {
        assert_eq!(
            directional_micros(&row.current),
            expected[row.key.as_ref().expect("actual peer")]
        );
    }
    let selected = page
        .groups
        .iter()
        .find(|r| r.key.as_deref().is_some_and(|k| k.starts_with("company:")))
        .expect("company counterparty");
    for (index, direction) in [
        FlowDirection::Inbound,
        FlowDirection::Outbound,
        FlowDirection::Within,
    ]
    .into_iter()
    .enumerate()
    {
        let constrained = FlowQuery {
            group: FlowGroup::Location,
            peer: Some(FlowPeer {
                group: FlowGroup::Counterparty,
                key: selected.key.clone(),
                direction,
            }),
            ..scoped.clone()
        };
        let legs = observer
            .economic_payment_flows(campaign, &constrained)
            .expect("actual geographic legs");
        let exact = directional_micros(&selected.current)[index];
        let mut wanted = [0; 3];
        wanted[index] = exact;
        assert_eq!(directional_micros(&legs.total.current), wanted);
        let key = selected.key.as_ref().expect("captured company");
        for location in &legs.groups {
            wanted[index] = places[&(key.clone(), index, location.key.clone())];
            assert_eq!(directional_micros(&location.current), wanted);
        }
    }
    reconcile(&page);
}

use babylon_persistence::money_journal::MoneyJournalWriter;

// A positive mutation of one original carrying amount leaves the number of claims,
// every beneficial weight and the parent's capital intact. Retry still rechecks it.
fn alter_original_holding(owner: &mut Client, campaign: CampaignId) -> (i32, String, Vec<u8>) {
    let sql = "UPDATE babylon_state.economic_company_original_share_v1 h
        SET original_carrying_micros = h.original_carrying_micros+1
        WHERE (campaign_id,site_key,beneficiary_kind,beneficiary_id) = (
            SELECT campaign_id,site_key,beneficiary_kind,beneficiary_id
            FROM babylon_state.economic_company_original_share_v1
            WHERE campaign_id=$1 AND original_carrying_micros=0
            ORDER BY site_key,beneficiary_kind,beneficiary_id LIMIT 1)
        RETURNING site_key,beneficiary_kind,beneficiary_id";
    let row = owner
        .query_one(sql, &[campaign.as_uuid()])
        .expect("one historical zero-cost holding");
    (row.get(0), row.get(1), row.get(2))
}

pub(super) fn check_company_rebuild(
    owner: &mut Client,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    let expected = observer
        .published_company_period_statements(campaign, 2)
        .expect("prior committed company statements");
    let (site_key, owner_kind, owner_id) = alter_original_holding(owner, campaign);
    assert_eq!(
        writer.publish(observer, campaign, 2),
        Err(JournalError::Projection),
        "unchanged rank and row counts must not hide an altered original holding"
    );
    let registry = payment_registry::seed(owner, campaign);
    let original:Vec<u8>=owner.query_one("SELECT checkpoint_bytes FROM babylon_state.company_accounting_checkpoint_v1 WHERE campaign_id=$1 AND resolve_tick=1",&[campaign.as_uuid()]).expect("prior basis seed").get(0);
    owner.execute("UPDATE babylon_state.company_accounting_checkpoint_v1 SET checkpoint_bytes=checkpoint_bytes||decode('ff','hex') WHERE campaign_id=$1 AND resolve_tick=1",&[campaign.as_uuid()]).expect("damage only the disposable derived seed");
    let company:Vec<u8>=owner.query_one("SELECT company_id FROM babylon_state.company_elimination_v1 WHERE campaign_id=$1 AND resolve_tick=2 ORDER BY company_id LIMIT 1",&[campaign.as_uuid()]).expect("one group").get(0);
    let id = CompanyId::from_bytes(company.as_slice().try_into().expect("captured company id"));
    let selected = || {
        observer.company_accounts_for_frame(
            campaign,
            2,
            id,
            &expected.foundation_sha256,
            &expected.tick_content_hash,
        )
    };
    let original_selected = selected().expect("verified selected company before corruption");
    assert_eq!(owner.execute(
        "UPDATE babylon_state.company_statement_income_v1 SET sales_micros=sales_micros+1,cost_of_goods_sold_micros=cost_of_goods_sold_micros+1
          WHERE campaign_id=$1 AND resolve_tick=2 AND company_id=$2 AND scope='parent'",
        &[campaign.as_uuid(), &company],
    ).expect("balanced income-line corruption in disposable projection"),1);
    assert_eq!(selected(), Err(JournalError::Projection));
    assert_eq!(owner.execute("UPDATE babylon_state.company_statement_balance_v1 SET cash_micros=cash_micros+1,assets_micros=assets_micros+1,equity_micros=equity_micros+1
        WHERE campaign_id=$1 AND resolve_tick=2 AND company_id=$2 AND scope='consolidated' AND boundary='closing'",&[campaign.as_uuid(),&company]).expect("tamper one disposable derived balance"),1);
    assert_eq!(
        observer.published_company_period_statements(campaign, 2),
        Err(JournalError::Projection)
    );
    writer
        .rebuild(observer, campaign, 2)
        .expect("replay past the rejected prior seed and replace derived rows");
    assert_eq!(
        observer
            .published_company_period_statements(campaign, 2)
            .expect("reread repaired facts"),
        expected
    );
    assert_eq!(
        selected().expect("repaired selected company"),
        original_selected
    );
    registry.check_repair(owner, campaign);
    let repaired = owner.query_one(
        "SELECT original_carrying_micros=0 FROM babylon_state.economic_company_original_share_v1
         WHERE (campaign_id,site_key,beneficiary_kind,beneficiary_id)=($1,$2,$3,$4)",
        &[campaign.as_uuid(), &site_key, &owner_kind, &owner_id],
    ).expect("reconstructed historical holding");
    assert!(repaired.get::<_, bool>(0));
    owner.execute("UPDATE babylon_state.company_accounting_checkpoint_v1 SET checkpoint_bytes=$2 WHERE campaign_id=$1 AND resolve_tick=1",&[campaign.as_uuid(),&original]).expect("restore the original fixture seed");
}
