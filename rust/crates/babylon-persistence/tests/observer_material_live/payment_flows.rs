//! Real full-observer settlement, geographic scope and rank reconciliation.
use babylon_persistence::economic_flows::EconomicPaymentPeriod;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{
    FlowAmounts, FlowGroup, FlowPage, FlowQuery, FlowViewport, JournalError, MoneyMovement,
    MoneyPurpose, PeriodWindow,
};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use babylon_persistence::qualification_audit::trade;
use postgres::{Client, Config, NoTls};
use std::collections::BTreeMap;

pub(super) fn query(group: FlowGroup) -> FlowQuery {
    FlowQuery {
        group,
        window: PeriodWindow { first: 1, last: 1 },
        comparison: None,
        focus: None,
        offset: 0,
        viewport_4269: None,
    }
}

pub(super) fn restricted(observer: &ObserverEconomyReader, campaign: CampaignId) {
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
    let source = observer
        .committed_economic_payments_with_cursor(campaign, 1, &mut None)
        .expect("canonical economic principals");
    let mut sql = config.connect(NoTls).expect("observer SQL");
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
