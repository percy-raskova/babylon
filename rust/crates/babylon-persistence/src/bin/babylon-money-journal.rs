//! Explicit owner publication and confined observer SQL queries for money facts.
use babylon_material_circuit::SiteId;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{
    FlowGroup, FlowQuery, FlowViewport, MoneyJournalWriter, PeriodWindow,
};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::process::ExitCode;
use uuid::Uuid;

enum Measure {
    Money,
    Labor,
}

struct Arguments {
    measure: Measure,
    operation: String,
    campaign: CampaignId,
    first: u64,
    last: u64,
    query: Option<FlowQuery>,
    site: Option<SiteId>,
}
fn arguments(mut args: impl Iterator<Item = String>) -> Result<Arguments, &'static str> {
    let operation = args.next().ok_or("operation_absent")?;
    if !matches!(
        operation.as_str(),
        "publish" | "rebuild" | "details" | "totals" | "flows" | "site-history"
    ) {
        return Err("operation_refused");
    }
    let mut flags = BTreeMap::new();
    while let Some(flag) = args.next() {
        let flow_option = operation == "flows"
            && matches!(
                flag.as_str(),
                "--measure"
                    | "--group"
                    | "--compare-first"
                    | "--compare-last"
                    | "--focus"
                    | "--offset"
                    | "--bbox-4269"
            );
        let site_option = operation == "site-history" && flag == "--site";
        if !flow_option
            && !site_option
            && !matches!(flag.as_str(), "--campaign" | "--first" | "--last")
        {
            return Err("arguments_refused");
        }
        let value = args.next().ok_or("arguments_refused")?;
        if flags.insert(flag, value).is_some() {
            return Err("arguments_refused");
        }
    }
    let campaign = flags.get("--campaign").ok_or("campaign_absent")?;
    let id = Uuid::parse_str(campaign).map_err(|_| "campaign_refused")?;
    if id.is_nil() || id.to_string() != *campaign {
        return Err("campaign_refused");
    }
    let parse = |value: &str| -> Result<u64, &'static str> {
        let period = value.parse::<u64>().map_err(|_| "period_refused")?;
        if period == 0 || period > i64::MAX as u64 || period.to_string() != value {
            return Err("period_refused");
        }
        Ok(period)
    };
    let first = parse(flags.get("--first").ok_or("period_absent")?)?;
    let last = match flags.get("--last") {
        Some(value) => parse(value)?,
        None => first,
    };
    if last < first || (operation == "details" && last != first) {
        return Err("period_refused");
    }
    let query = if operation == "flows" {
        Some(flow_options(&flags, PeriodWindow { first, last }, parse)?)
    } else {
        None
    };
    let site = if operation == "site-history" {
        Some(parse_site(flags.get("--site").ok_or("site_absent")?)?)
    } else {
        None
    };
    let measure = match flags.get("--measure").map(String::as_str) {
        None | Some("money") => Measure::Money,
        Some("labor") => Measure::Labor,
        Some(_) => return Err("flow_measure_refused"),
    };
    Ok(Arguments {
        measure,
        query,
        site,
        operation,
        campaign: CampaignId::from_uuid(id),
        first,
        last,
    })
}
fn parse_site(text: &str) -> Result<SiteId, &'static str> {
    if text.len() != 64
        || !text
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("site_refused");
    }
    let mut bytes = [0; 32];
    for (i, value) in bytes.iter_mut().enumerate() {
        *value = u8::from_str_radix(&text[2 * i..2 * i + 2], 16).map_err(|_| "site_refused")?;
    }
    Ok(SiteId::from_bytes(bytes))
}
fn flow_options(
    flags: &BTreeMap<String, String>,
    window: PeriodWindow,
    parse: impl Fn(&str) -> Result<u64, &'static str>,
) -> Result<FlowQuery, &'static str> {
    let comparison = match (flags.get("--compare-first"), flags.get("--compare-last")) {
        (None, None) => None,
        (Some(first), last) => Some(PeriodWindow {
            first: parse(first)?,
            last: parse(last.unwrap_or(first))?,
        }),
        _ => return Err("comparison_refused"),
    };
    let group = match flags.get("--group").map_or("location", String::as_str) {
        "location" => FlowGroup::Location,
        "account" => FlowGroup::Account,
        "catchment" => FlowGroup::Catchment,
        "industry" => FlowGroup::Industry,
        _ => return Err("group_refused"),
    };
    let viewport_4269 = flags
        .get("--bbox-4269")
        .map(|text| {
            let parts = text
                .split(',')
                .map(str::parse::<f64>)
                .collect::<Result<Vec<_>, _>>()
                .map_err(|_| "viewport_refused")?;
            let [west, south, east, north] = parts.as_slice() else {
                return Err("viewport_refused");
            };
            Ok(FlowViewport {
                west: *west,
                south: *south,
                east: *east,
                north: *north,
            })
        })
        .transpose()?;
    let offset = flags
        .get("--offset")
        .map(|n| n.parse::<u64>())
        .transpose()
        .map_err(|_| "offset_refused")?
        .unwrap_or(0);
    Ok(FlowQuery {
        window,
        comparison,
        group,
        focus: flags.get("--focus").cloned(),
        offset,
        viewport_4269,
    })
}
fn run(args: &Arguments) -> Result<Value, String> {
    let observer = ObserverEconomyReader::from_observer_env().map_err(|e| e.to_string())?;
    match args.operation.as_str() {
        "publish" | "rebuild" => {
            let config = std::env::var("BABYLON_RUNTIME_DSN")
                .map_err(|_| "writer_credential_absent")?
                .parse()
                .map_err(|_| "writer_credential_refused")?;
            let writer = MoneyJournalWriter::connect(&config).map_err(|e| e.to_string())?;
            let mut reports = Vec::new();
            let mut cursor = None;
            for period in args.first..=args.last {
                reports.push(
                    if args.operation == "rebuild" {
                        writer.rebuild_with_cursor(&observer, args.campaign, period, &mut cursor)
                    } else {
                        writer.publish_with_cursor(&observer, args.campaign, period, &mut cursor)
                    }
                    .map_err(|e| e.to_string())?,
                );
            }
            Ok(
                json!({"version":1,"campaign":args.campaign.as_uuid().to_string(),"periods":reports}),
            )
        }
        "flows" => {
            let query = args.query.as_ref().ok_or("flow_request_absent")?;
            let (unit, page) = match args.measure {
                Measure::Money => (
                    "currency_micros",
                    serde_json::to_value(
                        observer
                            .economic_payment_flows(args.campaign, query)
                            .map_err(|e| e.to_string())?,
                    ),
                ),
                Measure::Labor => (
                    "recorded_micro_hours",
                    serde_json::to_value(
                        observer
                            .recorded_labor_flows(args.campaign, query)
                            .map_err(|e| e.to_string())?,
                    ),
                ),
            };
            let page = page.map_err(|e| e.to_string())?;
            Ok(
                json!({"version":1,"campaign":args.campaign.as_uuid().to_string(),"unit":unit,"request":query,"page":page}),
            )
        }
        "site-history" => {
            let site = args.site.ok_or("site_absent")?;
            let history = observer
                .published_site_history(
                    args.campaign,
                    PeriodWindow {
                        first: args.first,
                        last: args.last,
                    },
                    site,
                )
                .map_err(|e| e.to_string())?;
            Ok(
                json!({"version":1,"campaign":args.campaign.as_uuid().to_string(),"first":args.first,
                "last":args.last,"unit":"currency_micros","periods":history}),
            )
        }
        "details" => Ok(
            json!({"version":1,"campaign":args.campaign.as_uuid().to_string(),"period":args.first,
            "movements":observer.money_movements(args.campaign,args.first).map_err(|e|e.to_string())?}),
        ),
        "totals" => Ok(
            json!({"version":1,"campaign":args.campaign.as_uuid().to_string(),"first":args.first,"last":args.last,
            "totals":observer.money_totals(args.campaign,args.first,args.last).map_err(|e|e.to_string())?}),
        ),
        _ => Err("operation_refused".to_owned()),
    }
}
fn main() -> ExitCode {
    match arguments(std::env::args().skip(1))
        .map_err(str::to_owned)
        .and_then(|args| run(&args))
    {
        Ok(result) => {
            println!("{result}");
            ExitCode::SUCCESS
        }
        Err(code) => {
            eprintln!("{}", json!({"version":1,"status":"refused","code":code}));
            ExitCode::FAILURE
        }
    }
}
