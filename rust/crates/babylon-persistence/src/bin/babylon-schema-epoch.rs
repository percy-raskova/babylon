//! Advance one `PostgreSQL` database to the exact compiled Rust schema epoch.

use std::process::ExitCode;

use babylon_persistence::migrate_schema_epoch;
use postgres::Config;

const DSN_ENV: &str = "BABYLON_SCHEMA_EPOCH_DSN";

fn main() -> ExitCode {
    let Some(raw_dsn) = std::env::var_os(DSN_ENV) else {
        eprintln!("babylon-schema-epoch: {DSN_ENV} is required");
        return ExitCode::from(2);
    };
    let Ok(dsn) = raw_dsn.into_string() else {
        eprintln!("babylon-schema-epoch: {DSN_ENV} must be valid UTF-8");
        return ExitCode::from(2);
    };
    let Ok(config) = dsn.parse::<Config>() else {
        eprintln!("babylon-schema-epoch: {DSN_ENV} is not a valid PostgreSQL DSN");
        return ExitCode::from(2);
    };

    match migrate_schema_epoch(&config) {
        Ok(report) => {
            println!(
                "Rust schema epoch complete (origin={:?}, prior={}, final={}, applied={}, reconciled={}).",
                report.origin,
                report.prior_applied,
                report.final_applied,
                report.applied_versions.len(),
                report.reconciled_versions.len(),
            );
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("babylon-schema-epoch: {error}");
            ExitCode::FAILURE
        }
    }
}
