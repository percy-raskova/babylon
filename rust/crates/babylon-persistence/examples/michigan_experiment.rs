//! Fixed PER-309 delivery/stock comparison using the native material session.
//! This example publishes ephemeral observations, never `PostgreSQL` commits.

#[path = "michigan_experiment/artifacts.rs"]
mod artifacts;

#[path = "michigan_experiment/observe.rs"]
mod observe;

#[path = "michigan_experiment/run.rs"]
mod run;

#[cfg(test)]
#[path = "michigan_experiment/tests.rs"]
mod tests;

use std::path::PathBuf;

use std::sync::{Arc, Mutex};

use artifacts::{Output, Progress, Result, Watchdog};

use serde_json::json;

#[path = "michigan_experiment/support.rs"]
mod support;

use artifacts::Error;
use std::process::ExitCode;

fn main() -> ExitCode {
    let result = (|| {
        let directory = support::output_argument(std::env::args_os().skip(1))?;
        let mut output = Output::create(&directory)?;
        let progress = Arc::new(Mutex::new(Progress::default()));
        let watchdog = Watchdog::start(&directory, Arc::clone(&progress));
        let result = support::execute(&mut output, &progress);
        watchdog.finish()?;
        if let Err(error) = &result {
            let state = progress
                .lock()
                .map_err(|_| artifacts::contract("progress mutex poisoned"))?;
            artifacts::write_failure(&directory, &state, &error.to_string())?;
        }
        result?;
        println!("Four cases / 64 periods complete: {}", directory.display());
        Ok::<_, Error>(())
    })();
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("Michigan experiment refused: {error}");
            ExitCode::FAILURE
        }
    }
}
