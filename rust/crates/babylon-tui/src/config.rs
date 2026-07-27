//! Client configuration crossing the FFI as a JSON string (design §4).

use serde::Deserialize;

/// Rendering tier the client runs at (design §5: glyph floor, pixel gated).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RenderTier {
    /// Universal glyph-cell tier (every terminal).
    Glyph,
    /// Pixel tier (kitty/sixel capable terminals; gated at runtime).
    Pixel,
}

/// Malformed client config crossing the FFI.
#[derive(Debug, thiserror::Error)]
#[error("invalid client config: {0}")]
pub struct ConfigError(#[from] serde_json::Error);

/// One scripted input step for headless replay (plan Task 19) — the BDD
/// harness foundation: integration tests drive full flows without a
/// terminal.
#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum ScriptStep {
    /// A key press by name: single characters (`"q"`, `"/"`, `"["`) or the
    /// named keys `enter`, `esc`, `up`, `down`, `left`, `right`, `tab`,
    /// `backspace`, `pageup`, `pagedown`, plus `ctrl-<char>` chords.
    Key {
        /// The key name.
        key: String,
    },
    /// A left-click at `[column, row]` cell coordinates.
    Mouse {
        /// `[column, row]` of the click.
        mouse: (u16, u16),
    },
}

/// Frozen per-run client configuration, parsed once at startup.
#[derive(Debug, Clone, Deserialize)]
pub struct AppConfig {
    /// Campaign primary key the session is bound to.
    pub campaign_id: String,
    /// Human title rendered in the frame chrome.
    pub campaign_name: String,
    /// Rendering tier (loud parse failure on unknown tiers — no fallback).
    pub render_tier: RenderTier,
    /// Whether the tutorial overlay arms at startup.
    pub tutorial_enabled: bool,
    /// Whether narrator beats render.
    pub narrator_enabled: bool,
    /// Headless mode: render to a test backend and return a transcript
    /// (CI path); interactive terminals never see it.
    #[serde(default)]
    pub headless: bool,
    /// Headless-only scripted inputs, applied in order after the initial
    /// frame; each step appends the resulting frame to the transcript.
    #[serde(default)]
    pub script: Vec<ScriptStep>,
    /// Headless `TestBackend` viewport size (contract
    /// `docs/superpowers/specs/2026-07-27-m3-tutorial-contracts.md` §5: the
    /// harness passes `[120, 50]`, the Python pilot's own `_PILOT_SIZE`, so
    /// frame-text checks assert against an un-clipped viewport). Defaults
    /// to the M0 `TestBackend::new(80, 24)` size so every fixture that
    /// predates this field keeps parsing unchanged.
    #[serde(default = "default_headless_size")]
    pub headless_size: (u16, u16),
}

/// [`AppConfig::headless_size`]'s default: the M0 hello-frame's own
/// `TestBackend::new(80, 24)`.
fn default_headless_size() -> (u16, u16) {
    (80, 24)
}

impl AppConfig {
    /// Parse a config from its FFI JSON string.
    ///
    /// A structurally valid payload can still be nonsense: a headless
    /// viewport of `0` in either dimension can never render a frame, and
    /// an enormous one (`> 1_000_000` cells — comfortably past any real
    /// terminal, e.g. 1000x1000) is almost certainly a malformed test
    /// fixture, not a real request (R20 fix) — both are rejected loudly
    /// here rather than let a `TestBackend::new` panic or an OOM-scale
    /// buffer allocation stand in for a config error (Constitution III.11).
    pub fn from_json(s: &str) -> Result<Self, ConfigError> {
        let cfg: Self = serde_json::from_str(s)?;
        let (width, height) = cfg.headless_size;
        if width == 0 || height == 0 {
            return Err(config_error(format!(
                "headless_size {width}x{height} has a zero dimension"
            )));
        }
        let area = u32::from(width) * u32::from(height);
        if area > 1_000_000 {
            return Err(config_error(format!(
                "headless_size {width}x{height} ({area} cells) exceeds the 1,000,000-cell ceiling"
            )));
        }
        Ok(cfg)
    }
}

/// Build a [`ConfigError`] carrying a custom message, for validation
/// failures that never touched `serde_json`'s own parser (R20) —
/// `serde_json::Error` implements [`serde::de::Error`], which supplies
/// exactly this constructor.
fn config_error(msg: impl std::fmt::Display) -> ConfigError {
    ConfigError::from(<serde_json::Error as serde::de::Error>::custom(msg))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_minimal_config() {
        let cfg = AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"Wayne","render_tier":"glyph",
                "tutorial_enabled":true,"narrator_enabled":false}"#,
        )
        .unwrap();
        assert_eq!(cfg.campaign_name, "Wayne");
        assert_eq!(cfg.render_tier, RenderTier::Glyph);
        assert!(!cfg.headless); // default false
    }

    #[test]
    fn parses_script_steps() {
        let cfg = AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"glyph",
                "tutorial_enabled":false,"narrator_enabled":false,"headless":true,
                "script":[{"key":"down"},{"key":"enter"},{"mouse":[4,2]},{"key":"q"}]}"#,
        )
        .unwrap();
        assert_eq!(cfg.script.len(), 4);
        assert!(matches!(&cfg.script[0], ScriptStep::Key { key } if key == "down"));
        assert!(matches!(
            &cfg.script[2],
            ScriptStep::Mouse { mouse: (4, 2) }
        ));
    }

    #[test]
    fn headless_size_defaults_to_80x24_and_can_be_overridden() {
        let default_cfg = AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"glyph",
                "tutorial_enabled":true,"narrator_enabled":false}"#,
        )
        .unwrap();
        assert_eq!(default_cfg.headless_size, (80, 24));

        let sized_cfg = AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"glyph",
                "tutorial_enabled":true,"narrator_enabled":false,
                "headless":true,"headless_size":[120,50]}"#,
        )
        .unwrap();
        assert_eq!(sized_cfg.headless_size, (120, 50));
    }

    #[test]
    fn rejects_bad_tier() {
        assert!(AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"3d",
                "tutorial_enabled":false,"narrator_enabled":false}"#
        )
        .is_err());
    }

    #[test]
    fn rejects_a_zero_headless_dimension() {
        assert!(AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"glyph",
                "tutorial_enabled":false,"narrator_enabled":false,
                "headless":true,"headless_size":[0,24]}"#
        )
        .is_err());
        assert!(AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"glyph",
                "tutorial_enabled":false,"narrator_enabled":false,
                "headless":true,"headless_size":[80,0]}"#
        )
        .is_err());
    }

    #[test]
    fn rejects_a_headless_area_over_one_million_cells() {
        // 2000x2000 = 4,000,000 cells, comfortably over the ceiling.
        assert!(AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"glyph",
                "tutorial_enabled":false,"narrator_enabled":false,
                "headless":true,"headless_size":[2000,2000]}"#
        )
        .is_err());
    }
}
