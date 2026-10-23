//! `bsl-lint` — the repo-relationship sentinel host for BSL content.
//!
//! Scope, Director-ruled 2026-08-18 (the BSL hygiene knock-out train, W1):
//! this binary hosts checks over things babylon-bsl's own reader/loader
//! CANNOT see from inside one content set — git tags, `ai/decisions/`, and
//! cross-crate Rust source. A check computable purely from content
//! declarations belongs in the loader as an `E-LOAD` refusal instead (Task
//! W2), not here.
//!
//! Shape mirrors `tools/sentinel_check.py`: a positional check name selects
//! one registered check (`--list` prints the registry, `all` runs every check
//! whose registry row opts into the default set), optional trailing `paths`
//! scope it. Exit contract: 0 clean, 1 a `Fail`-severity finding was printed,
//! 2 usage/infrastructure error.

use bsl_lint::finding::Severity;
use bsl_lint::repo::Repo;
use bsl_lint::{Check, CHECKS};
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        None | Some("--help" | "-h") => {
            print_usage();
            ExitCode::from(2)
        }
        Some("--list") => {
            print_registry();
            ExitCode::from(0)
        }
        Some("all") => {
            let default_checks = CHECKS
                .iter()
                .filter(|check| check.in_default_all)
                .collect::<Vec<_>>();
            run_and_report(&args[1..], &default_checks)
        }
        Some(name) => {
            if let Some(check) = CHECKS.iter().find(|check| check.name == name) {
                run_and_report(&args[1..], &[check])
            } else {
                eprintln!("bsl-lint: unknown check {name:?}");
                print_usage();
                ExitCode::from(2)
            }
        }
    }
}

fn print_usage() {
    eprintln!("usage: bsl-lint <check|all|--list> [paths...]");
}

fn print_registry() {
    for check in CHECKS {
        println!("{}", check.name);
    }
    println!("all");
}

fn run_and_report(paths: &[String], checks: &[&Check]) -> ExitCode {
    let repo = match Repo::discover() {
        Ok(repo) => repo,
        Err(error) => {
            eprintln!("bsl-lint: {error}");
            return ExitCode::from(2);
        }
    };

    let mut any_fail = false;
    for check in checks {
        match (check.run)(&repo, paths) {
            Ok(findings) => {
                for finding in findings {
                    if finding.severity == Severity::Fail {
                        any_fail = true;
                    }
                    println!("{finding}");
                }
            }
            Err(error) => {
                eprintln!("bsl-lint: {}: {error}", check.name);
                return ExitCode::from(2);
            }
        }
    }
    ExitCode::from(u8::from(any_fail))
}
