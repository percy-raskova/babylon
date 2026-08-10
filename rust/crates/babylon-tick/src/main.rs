//! `babylon-tick` — the Phase 2 Slice 1 driver.
//!
//! ```text
//! babylon-tick <scenario.bscn> <rule.bsl>
//! ```
//!
//! Loads a world, loads a rule through every gate, runs one tick, and prints
//! the state hash. Running it twice on the same inputs must print the same
//! hash; that is Constitution III.7 made observable from a shell rather than
//! only from a test.
//!
//! # Where the content lives
//!
//! `content/` **inside this crate**, not at the repo root. §2.2 of the
//! language spec says a content set is "the union of all files under the
//! declared content roots" — *declared*, and plural, so the durable content
//! root is configuration and choosing one is an architecture decision this
//! slice has no standing to make. Until it is declared, this crate's example
//! content is scoped to this crate, where it is unambiguously the driver's
//! demonstration data rather than a claim about where game content belongs.
//!
//! **This is not `babylon-engine`.** The engine — anchor total-order
//! resolution, the system registry, a tick *sequence* — is Phase 3, and
//! naming this binary as though it were would be claiming ground that has
//! not been taken. It drives ONE rule over ONE scenario for ONE tick. When
//! Phase 3 charters the engine, this either becomes its first command or is
//! absorbed and deleted; either way the slice's evidence survives in
//! `babylon-bsl`'s tests, which do not depend on this binary existing.
//!
//! Exit status is 0 on a completed tick and 1 on any failure, with the
//! reason on stderr — a driver that printed a hash for a failed run would be
//! worse than one that printed nothing.
//!
//! The tick flow itself (scenario load -> rule load -> one tick -> state
//! hash) lives in `babylon_tick::run_once` (Program 28 B0) — this binary is
//! now only argument parsing, calling that seam, and printing. The same
//! `run_once` is what `babylon-client`'s engine link calls in-process.

use babylon_tick::{hex, run_once};
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let [_, scenario_path, rule_path] = args.as_slice() else {
        eprintln!("usage: babylon-tick <scenario.bscn> <rule.bsl>");
        return ExitCode::FAILURE;
    };

    match run(scenario_path, rule_path) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("babylon-tick: {message}");
            ExitCode::FAILURE
        }
    }
}

fn run(scenario_path: &str, rule_path: &str) -> Result<(), String> {
    let scenario_src = std::fs::read_to_string(scenario_path)
        .map_err(|e| format!("cannot read scenario {scenario_path}: {e}"))?;
    let rule_src = std::fs::read_to_string(rule_path)
        .map_err(|e| format!("cannot read rule {rule_path}: {e}"))?;

    let report = run_once(&scenario_src, &rule_src)?;

    println!("tick 1    {} subjects fired", report.fired);
    println!("before    {}", hex(&report.before));
    println!("after     {}", hex(&report.after));
    if report.before == report.after {
        // Not an error — a tick where no guard passed is a real outcome, and
        // saying so beats leaving the reader to compare 64 hex digits.
        println!("note      state unchanged: no subject passed the guard");
    }
    Ok(())
}
