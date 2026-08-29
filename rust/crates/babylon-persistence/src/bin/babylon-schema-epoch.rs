//! Advance one `PostgreSQL` database to the exact compiled Rust schema epoch.

use std::ffi::{OsStr, OsString};
use std::process::ExitCode;

use babylon_persistence::{migrate_schema_epoch, preflight_schema_epoch};
use postgres::Config;

const DSN_ENV: &str = "BABYLON_SCHEMA_EPOCH_DSN";
const PREFLIGHT_MODE: &str = "--preflight";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Mode {
    Migrate,
    Preflight,
}

fn main() -> ExitCode {
    let Ok(mode) = parse_mode(std::env::args_os().skip(1)) else {
        eprintln!(
            "babylon-schema-epoch: unexpected arguments; expected no arguments or \
             {PREFLIGHT_MODE}"
        );
        return ExitCode::from(2);
    };
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

    let preflight = match mode {
        Mode::Preflight => preflight_schema_epoch(&config),
        Mode::Migrate => {
            return match migrate_schema_epoch(&config) {
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
            };
        }
    };

    match preflight {
        Ok(()) => {
            println!("Rust schema target and owner preflight complete.");
            ExitCode::SUCCESS
        }
        Err(error) => {
            eprintln!("babylon-schema-epoch: {error}");
            ExitCode::FAILURE
        }
    }
}

fn parse_mode(mut args: impl Iterator<Item = OsString>) -> Result<Mode, ()> {
    match (args.next(), args.next()) {
        (None, None) => Ok(Mode::Migrate),
        (Some(argument), None) if argument == OsStr::new(PREFLIGHT_MODE) => Ok(Mode::Preflight),
        _ => Err(()),
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_mode, Mode, PREFLIGHT_MODE};
    use babylon_persistence::{
        preflight_schema_epoch, LegacyAdopterError, LegacyConnectionTargetRejection,
        SchemaEpochError,
    };

    #[test]
    fn mode_is_exact_and_default_migrates() {
        assert_eq!(parse_mode(Vec::new().into_iter()), Ok(Mode::Migrate));
        assert_eq!(
            parse_mode(vec![PREFLIGHT_MODE.into()].into_iter()),
            Ok(Mode::Preflight)
        );
        assert_eq!(parse_mode(vec!["--unknown".into()].into_iter()), Err(()));
        assert_eq!(
            parse_mode(vec![PREFLIGHT_MODE.into(), "extra".into()].into_iter()),
            Err(())
        );
    }

    #[test]
    fn preflight_rejects_a_nonlocal_target_before_connecting() {
        let config = "postgresql://test@203.0.113.1:1/babylon_test"
            .parse()
            .expect("nonlocal DSN is syntactically valid");

        assert_eq!(
            preflight_schema_epoch(&config),
            Err(SchemaEpochError::ConnectionTarget(
                LegacyAdopterError::UnsupportedConnectionTarget {
                    reason: LegacyConnectionTargetRejection::NonLoopbackTcp,
                }
            ))
        );
    }
}
