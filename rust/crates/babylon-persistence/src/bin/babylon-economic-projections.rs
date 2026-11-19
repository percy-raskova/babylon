//! Independent local observer-session publisher for committed economic projections.
use babylon_material_circuit::{CompanyId, FinalDemandPrincipalId};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{JournalQueue, JournalQueueError, MoneyJournalWriter};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use babylon_persistence::qualification_audit::policy;
use serde_json::json;
use std::collections::BTreeMap;
use std::io::{self, BufWriter, Read as _, Write as _};
use std::process::{self, ExitCode};
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::thread;
use std::time::{Duration, Instant};
use uuid::Uuid;

// A periodic reconciliation also discovers deleted cache rows that emit no tick wakeup.
const RESCAN: Duration = Duration::from_secs(60);
const RETRY: Duration = Duration::from_secs(5);

#[derive(Clone, Copy)]
enum Command {
    Sweep(CampaignId),
    CompanyOpening(CampaignId),
    HouseholdPeriod(CampaignId, u64, FinalDemandPrincipalId),
    CompanyDecision(CampaignId, u64, CompanyId),
    CompanyPeriod(CampaignId, u64),
    PublishedCompanyPeriod(CampaignId, u64),
    LaborTrace {
        campaign: CampaignId,
        first: u64,
        last: u64,
    },
    WatchDatabase,
    WatchSession,
}

fn campaign(value: &str) -> Result<CampaignId, &'static str> {
    let id = Uuid::parse_str(value).map_err(|_| "campaign_refused")?;
    if id.is_nil() || id.to_string() != value {
        return Err("campaign_refused");
    }
    Ok(CampaignId::from_uuid(id))
}

fn labor_arguments(args: &[String]) -> Result<Command, &'static str> {
    let mut flags = BTreeMap::new();
    let (pairs, remainder) = args.as_chunks::<2>();
    if !remainder.is_empty() {
        return Err("labor_trace_flag_requires_value");
    }
    for pair in pairs {
        if !matches!(pair[0].as_str(), "--campaign" | "--first" | "--last")
            || flags.insert(pair[0].as_str(), pair[1].as_str()).is_some()
        {
            return Err("labor_trace_flag_refused");
        }
    }
    let id = campaign(flags.get("--campaign").ok_or("campaign_required")?)?;
    let first: u64 = flags
        .get("--first")
        .ok_or("first_period_required")?
        .parse()
        .map_err(|_| "period_refused")?;
    let last = flags
        .get("--last")
        .map(|value| value.parse::<u64>())
        .transpose()
        .map_err(|_| "period_refused")?
        .unwrap_or(first);
    Ok(Command::LaborTrace {
        campaign: id,
        first,
        last,
    })
}

fn arguments(args: &[String]) -> Result<Command, &'static str> {
    match args {
        [watch] if watch == "watch-database" => Ok(Command::WatchDatabase),
        [watch, pipe] if watch == "watch-database" && pipe == "--session-stdin" => {
            Ok(Command::WatchSession)
        }
        [command, campaign_flag, id, period_flag, period, household_flag, household]
            if command == "household-period" && campaign_flag == "--campaign"
                && period_flag == "--period" && household_flag == "--household" =>
        {
            let tick: u64 = period.parse().map_err(|_| "period_refused")?;
            if tick == 0 || i64::try_from(tick).is_err() { return Err("positive_period_required"); }
            let household = policy::canonical_digest(household).map_err(|_| "household_refused")?;
            Ok(Command::HouseholdPeriod(campaign(id)?, tick, FinalDemandPrincipalId::from_bytes(household)))
        }
        [command, campaign_flag, id, period_flag, period, company_flag, company]
            if command == "company-decision" && campaign_flag == "--campaign"
                && period_flag == "--period" && company_flag == "--company" =>
        {
            let tick: u64 = period.parse().map_err(|_| "period_refused")?;
            if tick == 0 || i64::try_from(tick).is_err() {
                return Err("positive_period_required");
            }
            let company = policy::canonical_digest(company).map_err(|_| "company_refused")?;
            Ok(Command::CompanyDecision(
                campaign(id)?, tick, CompanyId::from_bytes(company),
            ))
        }
        [command, flag, id, at, value, flags @ ..]
            if command == "company-period" && flag == "--campaign" && at == "--period" =>
        {
            let period = value.parse().map_err(|_| "period_refused")?;
            if period == 0 {return Err("positive_period_required");}
            match flags {
                [] => Ok(Command::CompanyPeriod(campaign(id)?, period)),
                [stored] if stored == "--published" => Ok(Command::PublishedCompanyPeriod(campaign(id)?,period)),
                _ => Err("company_statement_flag_refused"),
            }
        }
        [company, flag, value] if company == "company-opening" && flag == "--campaign" => {
            Ok(Command::CompanyOpening(campaign(value)?))
        }
        [sweep, flag, value] if sweep == "sweep" && flag == "--campaign" => {
            Ok(Command::Sweep(campaign(value)?))
        }
        [trace, options @ ..] if trace == "labor-trace" => labor_arguments(options),
        _ => Err("use household-period --campaign <uuid> --period <n> --household <hex>, company-decision --campaign <uuid> --period <n> --company <hex>, company-opening --campaign <uuid>, company-period --campaign <uuid> --period <n> [--published], watch-database, sweep --campaign <uuid>, or labor-trace --campaign <uuid> --first <period> [--last <period>]"),

    }
}

fn session_shutdown() -> Receiver<()> {
    let (lifetime, stopped) = mpsc::channel();
    thread::spawn(move || {
        let mut byte = [0];
        if io::stdin().lock().read_exact(&mut byte).is_ok() && byte == *b"Q" {
            drop(lifetime);
        } else {
            // Loss of the owning launcher's pipe must not leave a background publisher.
            // An unfinished database transaction rolls back when the connection closes.
            process::exit(0);
        }
    });
    stopped
}

fn shutdown_requested(stopped: Option<&Receiver<()>>) -> bool {
    stopped.is_some_and(|signal| matches!(signal.try_recv(), Err(TryRecvError::Disconnected)))
}

fn watch_connection(
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    stopped: Option<&Receiver<()>>,
    reopen: &mut Option<CampaignId>,
    new: &mut Option<CampaignId>,
) -> Result<(), JournalQueueError> {
    let mut queue =
        JournalQueue::connect(observer, writer, None).map_err(JournalQueueError::Discovery)?;
    let mut final_pass = false;
    loop {
        match queue.publish_batch() {
            Ok(0) => {}
            Ok(_) => continue,
            Err(error @ JournalQueueError::Publication { .. }) => {
                eprintln!("{error}");
                continue;
            }
            Err(error) => return Err(error),
        }
        if final_pass {
            return Ok(());
        }
        if shutdown_requested(stopped) {
            // Take a fresh discovery snapshot after the launcher has reaped the runtime.
            final_pass = true;
            continue;
        }
        if let Some(campaign) = reopen.take() {
            if let Err(cause) = queue.warm_reopened_campaign(campaign) {
                eprintln!(
                    "economic projections: reopening {}: {cause}",
                    campaign.as_uuid()
                );
            }
            // Recheck durable gaps after this bounded, read-only operation.
            continue;
        }
        if stopped.is_some() {
            match queue.warm_new_opening(new.take()) {
                Ok(Some(_)) => continue,
                Ok(None) => {}
                Err(cause) => eprintln!("economic projections: new opening: {cause}"),
            }
        }
        let started = Instant::now();
        while started.elapsed() < RESCAN && !shutdown_requested(stopped) {
            if queue
                .wait(Duration::from_secs(1))
                .map_err(JournalQueueError::Discovery)?
            {
                break;
            }
        }
    }
}

fn emit_labor_trace(
    observer: &ObserverEconomyReader,
    campaign: CampaignId,
    first: u64,
    last: u64,
) -> Result<(), String> {
    let window = observer
        .recorded_labor_window(campaign, first, last)
        .map_err(|error| error.to_string())?;
    let mut output = BufWriter::new(io::stdout().lock());
    for period in window {
        let report = period.map_err(|error| error.to_string())?;
        serde_json::to_writer(&mut output, &report).map_err(|error| error.to_string())?;
        output.write_all(b"\n").map_err(|error| error.to_string())?;
    }
    let end = json!({
        "record": "labor_trace_complete",
        "version": 1,
        "campaign": campaign.as_uuid().to_string(),
        "first": first,
        "last": last,
    });
    writeln!(output, "{end}")
        .and_then(|()| output.flush())
        .map_err(|error| error.to_string())
}

fn write_report(report: &impl serde::Serialize) -> Result<(), String> {
    let mut output = BufWriter::new(io::stdout().lock());
    serde_json::to_writer(&mut output, report).map_err(|e| e.to_string())?;
    output
        .write_all(b"\n")
        .and_then(|()| output.flush())
        .map_err(|e| e.to_string())
}

fn run(command: Command) -> Result<(), String> {
    let observer = ObserverEconomyReader::from_observer_env().map_err(|e| e.to_string())?;
    if let Command::LaborTrace {
        campaign,
        first,
        last,
    } = command
    {
        return emit_labor_trace(&observer, campaign, first, last);
    }
    match command {
        Command::HouseholdPeriod(campaign, period, household) => {
            return write_report(
                &observer
                    .household_period(campaign, period, household)
                    .map_err(|error| error.to_string())?,
            )
        }
        Command::CompanyDecision(campaign, period, company) => {
            return write_report(
                &observer
                    .company_decision_receipt(campaign, period, company)
                    .map_err(|error| error.to_string())?,
            )
        }
        Command::CompanyOpening(campaign) => {
            return write_report(
                &observer
                    .company_opening_statements(campaign)
                    .map_err(|e| e.to_string())?,
            )
        }
        Command::PublishedCompanyPeriod(campaign, period) => {
            return write_report(
                &observer
                    .published_company_period_statements(campaign, period)
                    .map_err(|e| e.to_string())?,
            )
        }
        Command::CompanyPeriod(campaign, period) => {
            return write_report(
                &observer
                    .company_period_statements(campaign, period)
                    .map_err(|e| e.to_string())?,
            )
        }
        _ => {}
    }
    let config = std::env::var("BABYLON_RUNTIME_DSN")
        .map_err(|_| "writer_credential_absent")?
        .parse()
        .map_err(|_| "writer_credential_refused")?;
    let writer = MoneyJournalWriter::connect(&config).map_err(|e| e.to_string())?;
    if let Command::Sweep(campaign) = command {
        let mut queue =
            JournalQueue::connect(&observer, &writer, Some(campaign)).map_err(|e| e.to_string())?;
        let count = queue.publish_batch().map_err(|e| e.to_string())?;
        println!(
            "{}",
            json!({"version":1,"campaign":campaign.as_uuid().to_string(),"covered":count})
        );
        return Ok(());
    }
    let shutdown = matches!(command, Command::WatchSession).then(session_shutdown);
    let stopped = shutdown.as_ref();
    let selected = |name: &str| {
        stopped
            .and_then(|_| std::env::var_os(name))
            .map(|id| campaign(id.to_str().ok_or("campaign_refused")?))
            .transpose()
    };
    let mut reopen = selected("BABYLON_REOPEN_CAMPAIGN")?;
    let mut new = selected("BABYLON_NEW_CAMPAIGN")?;
    loop {
        match watch_connection(&observer, &writer, stopped, &mut reopen, &mut new) {
            Ok(()) => return Ok(()),
            Err(error) if shutdown_requested(stopped) => return Err(error.to_string()),
            Err(error) => eprintln!("{error}; retrying"),
        }
        thread::sleep(RETRY);
    }
}

fn main() -> ExitCode {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    match arguments(&args).map_err(str::to_owned).and_then(run) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("economic projections: {error}");
            ExitCode::FAILURE
        }
    }
}
