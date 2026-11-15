//! Explicit owner publication and confined observer SQL queries for money facts.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::MoneyJournalWriter;
use babylon_persistence::observer_reader::ObserverEconomyReader;
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::process::ExitCode;
use uuid::Uuid;

struct Arguments {
    operation: String,
    campaign: CampaignId,
    first: u64,
    last: u64,
}
fn arguments(mut args: impl Iterator<Item = String>) -> Result<Arguments, &'static str> {
    let operation = args.next().ok_or("operation_absent")?;
    if !matches!(
        operation.as_str(),
        "publish" | "rebuild" | "details" | "totals"
    ) {
        return Err("operation_refused");
    }
    let mut flags = BTreeMap::new();
    while let Some(flag) = args.next() {
        if !matches!(flag.as_str(), "--campaign" | "--first" | "--last") {
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
    Ok(Arguments {
        operation,
        campaign: CampaignId::from_uuid(id),
        first,
        last,
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
