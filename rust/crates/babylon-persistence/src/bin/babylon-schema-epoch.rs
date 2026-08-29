//! Advance one `PostgreSQL` database to the exact compiled Rust schema epoch.

use std::ffi::{OsStr, OsString};
use std::process::ExitCode;

use babylon_persistence::{
    migrate_schema_epoch, validate_legacy_connection_target, LegacyAdopterError,
};
use postgres::Config;

const DSN_ENV: &str = "BABYLON_SCHEMA_EPOCH_DSN";
const VALIDATE_TARGET_ONLY_MODE: &str = "--validate-target-only";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Mode {
    Migrate,
    ValidateTargetOnly,
}

fn main() -> ExitCode {
    let Ok(mode) = parse_mode(std::env::args_os().skip(1)) else {
        eprintln!(
            "babylon-schema-epoch: unexpected arguments; expected no arguments or \
             {VALIDATE_TARGET_ONLY_MODE}"
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

    let target_validation = match mode {
        Mode::ValidateTargetOnly => validate_target_only(&config),
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

    match target_validation {
        Ok(()) => {
            println!("Rust schema target preflight complete.");
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
        (Some(argument), None) if argument == OsStr::new(VALIDATE_TARGET_ONLY_MODE) => {
            Ok(Mode::ValidateTargetOnly)
        }
        _ => Err(()),
    }
}

fn validate_target_only(config: &Config) -> Result<(), LegacyAdopterError> {
    validate_legacy_connection_target(config)
}

#[cfg(test)]
mod tests {
    use super::{parse_mode, validate_target_only, Mode, VALIDATE_TARGET_ONLY_MODE};

    #[test]
    fn mode_is_exact_and_default_migrates() {
        assert_eq!(parse_mode(Vec::new().into_iter()), Ok(Mode::Migrate));
        assert_eq!(
            parse_mode(vec![VALIDATE_TARGET_ONLY_MODE.into()].into_iter()),
            Ok(Mode::ValidateTargetOnly)
        );
        assert_eq!(parse_mode(vec!["--unknown".into()].into_iter()), Err(()));
        assert_eq!(
            parse_mode(vec![VALIDATE_TARGET_ONLY_MODE.into(), "extra".into()].into_iter()),
            Err(())
        );
    }

    #[test]
    fn target_only_validation_does_not_open_a_database_connection() {
        let config = "postgresql://test@127.0.0.1:1/babylon_test"
            .parse()
            .expect("loopback DSN is valid");

        validate_target_only(&config).expect("loopback target is admitted without connecting");
    }
}
