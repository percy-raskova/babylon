//! Client configuration crossing the FFI as a JSON string (design §4).

use serde::Deserialize;

/// Rendering tier the client runs at (design §5: glyph floor, pixel gated).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RenderTier {
    /// Universal glyph-cell tier (every terminal).
    #[default]
    Glyph,
    /// Pixel tier (kitty-capable terminals; gated at runtime — Task 35).
    Pixel,
}

/// The recorded `[render]` verdict, fetched ONCE from the host at boot via
/// `render_config_json` (Task 35, contract §7). `babylon doctor` probes;
/// the client honors the record and NEVER re-probes (ADR097 D4 — the
/// `Picker::from_query_stdio*` path is sentinel-banned). Defaults are the
/// glyph floor: honest absence of a probe is a glyph session.
#[derive(Debug, Clone, PartialEq, Eq, Default, Deserialize)]
pub struct RenderSettings {
    /// The persisted tier verdict.
    #[serde(default)]
    pub tier: RenderTier,
    /// The probed pixel protocol (`"kitty"`/`"sixel"`), if any. Only
    /// `"kitty"` can engage the pixel path (ADR099: sixel is not a target).
    #[serde(default)]
    pub pixel_protocol: Option<String>,
    /// Terminal cell width in pixels — `StatefulProtocol`'s FontSize.
    #[serde(default)]
    pub cell_width: Option<u16>,
    /// Terminal cell height in pixels.
    #[serde(default)]
    pub cell_height: Option<u16>,
    /// Whether the probe ran inside tmux (threaded into the kitty
    /// protocol's tmux passthrough mode).
    #[serde(default)]
    pub in_tmux: bool,
}

impl RenderSettings {
    /// Parse a `render_config_json` reply. `"null"` (a host with no
    /// recorded probe — the trait default) is the glyph floor; malformed
    /// non-null JSON is a protocol bug and fails LOUDLY (the
    /// `AppConfig::from_json` precedent — no fallback that would silently
    /// masquerade a seam defect as a glyph session, III.11).
    pub fn from_json(raw: &str) -> Self {
        serde_json::from_str::<Option<Self>>(raw)
            .expect("render_config_json returned malformed JSON — host/client seam defect")
            .unwrap_or_default()
    }
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
    /// to the DECLARED FLOOR (Wave 1 contract §1, Director ruling 1:
    /// 100×30) — the old M0 `80×24` default sits BELOW the floor and
    /// would render every defaulted fixture the too-small notice.
    #[serde(default = "default_headless_size")]
    pub headless_size: (u16, u16),
}

/// [`AppConfig::headless_size`]'s default: the declared 100×30 floor
/// (`babylon_tui::app::{FLOOR_WIDTH, FLOOR_HEIGHT}` — kept in lockstep by
/// `floor_guard.rs`'s at-floor test rendering with a defaulted config).
fn default_headless_size() -> (u16, u16) {
    (100, 30)
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
    fn headless_size_defaults_to_the_declared_floor_and_can_be_overridden() {
        // Wave 1 contract §1 (ruling 1): the default IS the 100×30 floor —
        // a below-floor default would render every defaulted fixture the
        // too-small notice instead of its actual surface.
        let default_cfg = AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"glyph",
                "tutorial_enabled":true,"narrator_enabled":false}"#,
        )
        .unwrap();
        assert_eq!(default_cfg.headless_size, (100, 30));

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

    // --- Task 35 (contract §7): the recorded [render] verdict crossing
    // the seam as `render_config_json`.

    #[test]
    fn render_settings_null_is_the_glyph_floor() {
        // The Host trait default ("no probe recorded") parses to defaults.
        assert_eq!(RenderSettings::from_json("null"), RenderSettings::default());
        assert_eq!(RenderSettings::default().tier, RenderTier::Glyph);
    }

    #[test]
    fn render_settings_full_payload_round_trips() {
        let settings = RenderSettings::from_json(
            r#"{"tier":"pixel","palette":"truecolor","pixel_protocol":"kitty",
                "cell_width":9,"cell_height":18,"in_tmux":false}"#,
        );
        assert_eq!(settings.tier, RenderTier::Pixel);
        assert_eq!(settings.pixel_protocol.as_deref(), Some("kitty"));
        assert_eq!(
            (settings.cell_width, settings.cell_height),
            (Some(9), Some(18))
        );
        assert!(!settings.in_tmux);
    }

    #[test]
    fn render_settings_honest_absence_fields_parse_as_none() {
        // The Python host serializes null for unknown facts — never zero.
        let settings = RenderSettings::from_json(
            r#"{"tier":"glyph","palette":"256","pixel_protocol":null,
                "cell_width":null,"cell_height":null,"in_tmux":false}"#,
        );
        assert_eq!(settings.pixel_protocol, None);
        assert_eq!((settings.cell_width, settings.cell_height), (None, None));
    }

    #[test]
    #[should_panic(expected = "seam defect")]
    fn render_settings_malformed_reply_fails_loud() {
        // III.11: a malformed seam reply is a defect, never silently a
        // glyph session (the AppConfig loud-parse precedent).
        let _ = RenderSettings::from_json("not json");
    }
}
