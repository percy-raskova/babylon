//! File-only client logging (Director directive 2026-07-28).
//!
//! The Python half of the client already logs the way the Director asked
//! for — `babylon.config.logging_config`: JSON-lines, DEBUG, 10 MB
//! size-rotation with capped archives. This module is the Rust half's
//! equivalent, built on `log4rs` (the Rust log4j: programmatic config,
//! size-triggered rolling, fixed-window archives), sinking into the SAME
//! player log directory the Python side owns
//! (`babylon.config.base.BaseConfig.LOG_DIR`, threaded across the FFI as
//! `AppConfig::log_dir`).
//!
//! **File-only, never the terminal.** A console appender here would be
//! exactly the frame-corruption class the terminal-takeover fix killed
//! (PR #318): the client paints the alternate screen and repaints only on
//! input, so one stray line wrecks the frame until the next keypress.
//!
//! **Off in the harness.** The headless BDD harness passes no `log_dir`,
//! so the global logger is never installed and every `log::debug!` in the
//! client compiles to a no-op behind `max_level = Off` — transcript
//! goldens cannot drift, and the interactive lane loses nothing.
//!
//! **No wall-clock in client source.** Timestamps come from log4rs's own
//! pattern encoder inside the appender; this crate's source stays free of
//! `Instant`/`SystemTime` (the raster-lane discipline).

use std::path::Path;
use std::sync::OnceLock;

use log::LevelFilter;
use log4rs::append::rolling_file::policy::compound::roll::fixed_window::FixedWindowRoller;
use log4rs::append::rolling_file::policy::compound::trigger::size::SizeTrigger;
use log4rs::append::rolling_file::policy::compound::CompoundPolicy;
use log4rs::append::rolling_file::RollingFileAppender;
use log4rs::config::{Appender, Config, Root};
use log4rs::encode::pattern::PatternEncoder;

/// Rotation trigger: matches the Python estate's `MAIN_LOG_MAX_BYTES`
/// discipline (10 MB per file).
const LOG_MAX_BYTES: u64 = 10 * 1024 * 1024;

/// Archive window: `rust-client.1.log` .. `rust-client.5.log`, oldest
/// dropped (matches the Python estate's `backupCount`).
const LOG_ARCHIVES: u32 = 5;

/// One-shot guard: the `log` crate's global logger can only ever be
/// installed once per process; a second `init_file_logging` call (a
/// relaunch through the same interpreter) is a no-op success.
static INIT: OnceLock<()> = OnceLock::new();

/// Install the rolling-file logger writing `rust-client.log` under
/// `log_dir`.
///
/// `level` is one of `error|warn|info|debug|trace` — anything else is a
/// config defect and fails loudly BEFORE touching global state (validated
/// even on the idempotent path, so a bad level never rides in silently
/// behind an earlier successful init).
pub fn init_file_logging(log_dir: &Path, level: &str) -> Result<(), String> {
    let level_filter = parse_level(level)?;
    if INIT.get().is_some() {
        return Ok(());
    }
    let roll_pattern = log_dir.join("rust-client.{}.log");
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
        .build(log_dir.join("rust-client.log"), Box::new(policy))
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

/// Parse the level string; unknown levels are a loud config defect.
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

/// Log a panic before it unwinds — the crash itself must reach the sink
/// (the FFI turns the unwind into a Python `PanicException` after the
/// terminal restores; this line is the client-side flight record of it).
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
        // Validation precedes the idempotency check, so this holds no
        // matter which test installed the global logger first.
        let err = init_file_logging(Path::new("/nonexistent"), "loudest").unwrap_err();
        assert!(err.contains("unknown log_level"));
    }

    #[test]
    fn init_writes_the_sink_and_reinit_is_a_noop_success() {
        let dir = std::env::temp_dir().join(format!("babylon-tui-logtest-{}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("test log dir");
        init_file_logging(&dir, "debug").expect("first init");
        log::debug!(target: "test", "sink probe line");
        log::logger().flush();
        let sink = dir.join("rust-client.log");
        let written = std::fs::read_to_string(&sink).expect("sink exists");
        assert!(written.contains("sink probe line"));
        // Second init: the global logger is already installed — Ok, not Err.
        init_file_logging(&dir, "debug").expect("re-init is a no-op success");
        std::fs::remove_dir_all(&dir).ok();
    }
}
