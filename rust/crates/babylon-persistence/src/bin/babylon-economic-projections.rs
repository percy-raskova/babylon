//! Independent local observer-session publisher for committed economic projections.
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{JournalQueue, JournalQueueError, MoneyJournalWriter};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use serde_json::json;
use std::io::{self, Read as _};
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
    WatchDatabase,
    WatchSession,
}

fn arguments(args: &[String]) -> Result<Command, &'static str> {
    match args {
        [watch] if watch == "watch-database" => Ok(Command::WatchDatabase),
        [watch, pipe] if watch == "watch-database" && pipe == "--session-stdin" => {
            Ok(Command::WatchSession)
        }
        [sweep, campaign, value] if sweep == "sweep" && campaign == "--campaign" => {
            let id = Uuid::parse_str(value).map_err(|_| "campaign_refused")?;
            if id.is_nil() || id.to_string() != *value {
                return Err("campaign_refused");
            }
            Ok(Command::Sweep(CampaignId::from_uuid(id)))
        }
        _ => Err("use watch-database or sweep --campaign <uuid>"),
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

fn run(command: Command) -> Result<(), String> {
    let observer = ObserverEconomyReader::from_observer_env().map_err(|e| e.to_string())?;
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
    loop {
        match watch_connection(&observer, &writer, stopped) {
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
