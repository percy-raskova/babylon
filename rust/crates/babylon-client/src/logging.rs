//! File-only client logging (Director directive 2026-07-28; resurrected
//! for the Bevy client at Program 28 B2, per CLAUDE.md: "the Bevy client's
//! file sink lands at milestone B2"). Built on `log4rs` — the same crate
//! and the same rotation policy the deleted Ratatui client's
//! `babylon-tui::logging` used, transcribed here rather than reinvented.
//!
//! **Independent of Bevy's own logging.** `bevy::log::LogPlugin` runs on
//! `tracing` and keeps printing to stderr exactly as `DefaultPlugins`
//! wires it — untouched by this module. `log4rs` listens on the separate
//! `log` facade; this crate's OWN `log::debug!`/`log::info!` calls (never
//! `bevy::log::info!`, which is `tracing`) are what land in the file.
//!
//! **No wall-clock in client source.** Timestamps come from `log4rs`'s own
//! pattern encoder inside the appender.

use std::path::Path;
use std::sync::OnceLock;

use log::LevelFilter;
use log4rs::append::rolling_file::policy::compound::roll::fixed_window::FixedWindowRoller;
use log4rs::append::rolling_file::policy::compound::trigger::size::SizeTrigger;
use log4rs::append::rolling_file::policy::compound::CompoundPolicy;
use log4rs::append::rolling_file::RollingFileAppender;
use log4rs::config::{Appender, Config, Root};
use log4rs::encode::pattern::PatternEncoder;

const LOG_MAX_BYTES: u64 = 10 * 1024 * 1024;
const LOG_ARCHIVES: u32 = 5;

static INIT: OnceLock<()> = OnceLock::new();

/// `$XDG_DATA_HOME/babylon/logs` else `~/.local/share/babylon/logs` —
/// mirrors `src/babylon/config/paths.py::player_data_dir()` /
/// `src/babylon/config/base.py::LOG_DIR` exactly, transcribed rather than
/// re-derived (no PyO3 in the play path, Amendment AF, so this cannot call
/// the Python function — it reproduces its two-line rule instead).
#[must_use]
pub fn log_dir() -> std::path::PathBuf {
    log_dir_from(
        std::env::var_os("XDG_DATA_HOME").map(std::path::PathBuf::from),
        std::env::var_os("HOME").map(std::path::PathBuf::from),
    )
}

/// The pure resolution rule behind [`log_dir`], with both environment
/// inputs injected — the test exercises this directly, so it never mutates
/// process-global env vars (cargo runs tests in parallel; a `set_var` in
/// one test races every other test's threads).
fn log_dir_from(
    xdg_data_home: Option<std::path::PathBuf>,
    home: Option<std::path::PathBuf>,
) -> std::path::PathBuf {
    let base = xdg_data_home
        .unwrap_or_else(|| home.expect("HOME must be set").join(".local").join("share"));
    base.join("babylon").join("logs")
}

/// Install the rolling-file logger writing `babylon-client.log` under
/// `log_dir`. `level` is one of `error|warn|info|debug|trace`.
///
/// # Errors
/// A config defect (bad level, non-UTF-8 log dir, log4rs init failure).
pub fn init_file_logging(log_dir: &Path, level: &str) -> Result<(), String> {
    let level_filter = parse_level(level)?;
    if INIT.get().is_some() {
        return Ok(());
    }
    let roll_pattern = log_dir.join("babylon-client.{}.log");
    let roller = FixedWindowRoller::builder()
        .build(
            roll_pattern
                .to_str()
                .ok_or_else(|| format!("log dir is not valid UTF-8: {}", log_dir.display()))?,
            LOG_ARCHIVES,
        )
        .map_err(|e| format!("log roller config: {e}"))?;
    let policy = CompoundPolicy::new(Box::new(SizeTrigger::new(LOG_MAX_BYTES)), Box::new(roller));
    let appender = RollingFileAppender::builder()
        .encoder(Box::new(PatternEncoder::new(
            "{d(%Y-%m-%dT%H:%M:%S%.3f)} [{l}] {t} — {m}{n}",
        )))
        .build(log_dir.join("babylon-client.log"), Box::new(policy))
        .map_err(|e| format!("log appender: {e}"))?;
    let config = Config::builder()
        .appender(Appender::builder().build("file", Box::new(appender)))
        .build(Root::builder().appender("file").build(level_filter))
        .map_err(|e| format!("log config: {e}"))?;
    log4rs::init_config(config).map_err(|e| format!("log init: {e}"))?;
    let _ = INIT.set(());
    install_panic_hook();
    Ok(())
}

fn parse_level(level: &str) -> Result<LevelFilter, String> {
    match level {
        "error" => Ok(LevelFilter::Error),
        "warn" => Ok(LevelFilter::Warn),
        "info" => Ok(LevelFilter::Info),
        "debug" => Ok(LevelFilter::Debug),
        "trace" => Ok(LevelFilter::Trace),
        other => Err(format!(
            "unknown log_level {other:?} (expected error|warn|info|debug|trace)"
        )),
    }
}

fn install_panic_hook() {
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        log::error!(target: "panic", "client panic: {info}");
        log::logger().flush();
        previous(info);
    }));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_unknown_level_fails_loudly_even_after_init() {
        let err = init_file_logging(Path::new("/nonexistent"), "loudest").unwrap_err();
        assert!(err.contains("unknown log_level"));
    }

    #[test]
    fn init_writes_the_sink_and_reinit_is_a_noop_success() {
        let dir =
            std::env::temp_dir().join(format!("babylon-client-logtest-{}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("test log dir");
        init_file_logging(&dir, "debug").expect("first init");
        log::debug!(target: "test", "sink probe line");
        log::logger().flush();
        let sink = dir.join("babylon-client.log");
        let written = std::fs::read_to_string(&sink).expect("sink exists");
        assert!(written.contains("sink probe line"));
        init_file_logging(&dir, "debug").expect("re-init is a no-op success");
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn log_dir_honors_xdg_data_home() {
        // Injected inputs, no env mutation — parallel-safe by construction
        // (the deleted TUI module's test set XDG_DATA_HOME process-globally
        // and leaned on a single-threaded assumption; not transcribed).
        let xdg = log_dir_from(Some(std::path::PathBuf::from("/tmp/xdg-probe")), None);
        assert_eq!(xdg, std::path::PathBuf::from("/tmp/xdg-probe/babylon/logs"));
        let fallback = log_dir_from(None, Some(std::path::PathBuf::from("/home/probe")));
        assert_eq!(
            fallback,
            std::path::PathBuf::from("/home/probe/.local/share/babylon/logs")
        );
    }
}
