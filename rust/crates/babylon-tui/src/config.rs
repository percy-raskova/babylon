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
    /// Headless mode: render one frame to a test backend and return (CI path).
    #[serde(default)]
    pub headless: bool,
}

impl AppConfig {
    /// Parse a config from its FFI JSON string.
    pub fn from_json(s: &str) -> Result<Self, ConfigError> {
        Ok(serde_json::from_str(s)?)
    }
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
    fn rejects_bad_tier() {
        assert!(AppConfig::from_json(
            r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"3d",
                "tutorial_enabled":false,"narrator_enabled":false}"#
        )
        .is_err());
    }
}
