//! Explicit candidate intervention qualification through the current staffed replay session.
//! This writes one bounded operator report, never campaign data or authored source files.

#[path = "statewide_experiment/arguments.rs"]
mod arguments;

#[path = "statewide_experiment/facts.rs"]
mod facts;

#[path = "statewide_experiment/report.rs"]
mod report;

#[path = "statewide_experiment/run.rs"]
mod run;

#[cfg(test)]
#[path = "../tests/fixtures/statewide_synthetic.rs"]
pub mod synthetic;

#[cfg(test)]
#[path = "statewide_experiment/tests.rs"]
mod tests;

#[path = "statewide_experiment/witness.rs"]
mod witness;

use std::{error::Error, process::ExitCode};

#[path = "statewide_experiment/support.rs"]
mod support;

use support::{checked_sum, execute, hex, quantity, refused, Result};

fn main() -> ExitCode {
    match execute() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("Statewide experiment refused: {error}");
            ExitCode::FAILURE
        }
    }
}
