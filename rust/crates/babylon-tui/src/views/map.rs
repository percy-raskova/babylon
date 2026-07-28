//! The map pane: nationwide choropleth over `choropleth_json` (M5 Tasks 38/40).
//!
//! The TopologyView shape verbatim (contract §2): chrome-owned state,
//! `ingest_choropleth` with the LOUD parse-failure flag, `args_json` in
//! pinned field order, pure viewport math. Cells carry WKT polygons
//! (EPSG:4269 lon/lat treated as plain x/y — equirectangular, honest at
//! county scale); the value channel is lens-typed (numbers for
//! value/tension, status strings for fog, `"inf"` for the bled-dry limit
//! — JSON has no Infinity) and bands arrive AS DATA, resolved to the
//! parity-guarded theme constants by §9b role name at ingest, loudly.

use ratatui::style::Color;
use serde::Deserialize;

/// What a handled key asks the integrator to do (the `TopologyAction`
/// mirror, contract §3).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MapAction {
    /// Consumed, no data change.
    Handled,
    /// Consumed AND the args changed — re-fetch `choropleth_json`.
    NeedsRefresh,
    /// Not a map key — fall through.
    NotHandled,
}

/// The lens cycle (`l`, contract §3): value → tension → fog → value.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Lens {
    /// Exploitation rate `s/v`.
    #[default]
    Value,
    /// The ADR170 diverging witness `w`.
    Tension,
    /// The epistemic fog tier.
    Fog,
}

impl Lens {
    fn next(self) -> Self {
        match self {
            Self::Value => Self::Tension,
            Self::Tension => Self::Fog,
            Self::Fog => Self::Value,
        }
    }

    /// The wire name (`args_json` + envelope echo).
    pub fn wire(self) -> &'static str {
        match self {
            Self::Value => "value",
            Self::Tension => "tension",
            Self::Fog => "fog",
        }
    }
}

/// The tier cycle (`y`, contract §3): county → state (ea SKIPPED until a
/// producer exists, contract §1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Tier {
    /// One cell per county FIPS.
    #[default]
    County,
    /// One cell per 2-digit state prefix.
    State,
}

impl Tier {
    fn next(self) -> Self {
        match self {
            Self::County => Self::State,
            Self::State => Self::County,
        }
    }

    /// The wire name.
    pub fn wire(self) -> &'static str {
        match self {
            Self::County => "county",
            Self::State => "state",
        }
    }
}

/// A cell's lens-typed value off the wire.
#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(untagged)]
pub enum CellValue {
    /// value/tension lenses.
    Num(f64),
    /// fog statuses + the `"inf"` encoding.
    Text(String),
}

/// One wire cell (contract §1's pinned shape).
#[derive(Debug, Clone, Deserialize)]
pub struct WireCell {
    /// County FIPS or state prefix.
    pub region_id: String,
    /// Lens value, honest-absent as `None`.
    pub value: Option<CellValue>,
    /// Exterior-ring WKT, or `None` (geometry absence).
    pub wkt: Option<String>,
    /// Unused this milestone (labels derive from polygon bboxes).
    pub centroid: Option<(f64, f64)>,
}

/// The parsed envelope.
#[derive(Debug, Clone, Deserialize)]
pub struct ChoroplethPayload {
    /// Echoed tier.
    pub tier: String,
    /// Echoed lens.
    pub lens: String,
    /// The tick the fold ran at.
    pub verified_tick: u64,
    /// `[threshold-or-status, role]` rows, resolved at ingest.
    pub bands: Vec<(serde_json::Value, String)>,
    /// Whole-lens absence (tension without a norm; the dead fog
    /// `approximate` tier note).
    #[serde(default)]
    pub lens_absent_reason: Option<String>,
    /// The ADR171 national-overlay absence string (drops when the Phase-0
    /// artifact lands — the pin-goes-red flip).
    #[serde(default)]
    pub overlay_absent: Option<String>,
    /// The cells.
    pub cells: Vec<WireCell>,
}

/// Resolve a §9b role token to its parity-guarded theme constant.
/// Unknown roles are a PROTOCOL failure (loud), never a default color.
fn role_color(role: &str) -> Option<Color> {
    match role {
        "panel" => Some(crate::theme::MUTED_DARK),
        "dim" => Some(crate::theme::DIM),
        "gold" => Some(crate::theme::GOLD),
        "crimson" => Some(crate::theme::CRIMSON),
        _ => None,
    }
}

/// A polygon ready to paint: exterior ring + bbox.
#[derive(Debug, Clone)]
pub struct Ring {
    /// `(x, y)` vertices (closed or open — the scanline closes it).
    pub points: Vec<(f64, f64)>,
}

/// Parse the exterior ring(s) out of `POLYGON`/`MULTIPOLYGON` WKT
/// (exterior-ring-only for v1.0, contract §2 — county holes are
/// negligible at cell resolution). Returns `None` on malformed text
/// (the caller flags the payload loud, never silently skips).
pub fn wkt_exterior_rings(wkt: &str) -> Option<Vec<Ring>> {
    let trimmed = wkt.trim();
    let body = if let Some(rest) = trimmed.strip_prefix("MULTIPOLYGON") {
        rest.trim()
    } else if let Some(rest) = trimmed.strip_prefix("POLYGON") {
        rest.trim()
    } else {
        return None;
    };
    // Every '(' opens a group; the FIRST ring inside each polygon group is
    // the exterior. Split on "((" groups then take text up to the first ')'.
    let mut rings = Vec::new();
    let mut rest = body;
    while let Some(start) = rest.find("((") {
        // MULTIPOLYGON nests one paren deeper: "(((ring)), ((ring)))".
        let after = rest[start + 2..].trim_start_matches('(');
        let end = after.find(')')?;
        rings.push(parse_ring(&after[..end])?);
        rest = &after[end..];
    }
    if rings.is_empty() {
        return None;
    }
    Some(rings)
}

fn parse_ring(text: &str) -> Option<Ring> {
    let mut points = Vec::new();
    for pair in text.split(',') {
        let mut nums = pair.split_whitespace();
        let x: f64 = nums.next()?.parse().ok()?;
        let y: f64 = nums.next()?.parse().ok()?;
        points.push((x, y));
    }
    if points.len() < 3 {
        return None;
    }
    Some(Ring { points })
}

/// The pan/zoom window over data space (Task 40's pure math).
#[derive(Debug, Clone, PartialEq)]
pub struct Viewport {
    /// Current x window.
    pub x_bounds: [f64; 2],
    /// Current y window.
    pub y_bounds: [f64; 2],
    /// The fitted data bbox `0` restores (and the clamp anchor).
    pub fitted: ([f64; 2], [f64; 2]),
}

impl Viewport {
    /// Fit to a data bbox (plus a 5% margin so border cells breathe).
    #[must_use]
    pub fn fitted_to(min_x: f64, min_y: f64, max_x: f64, max_y: f64) -> Self {
        let mx = ((max_x - min_x) * 0.05).max(0.5);
        let my = ((max_y - min_y) * 0.05).max(0.5);
        let x = [min_x - mx, max_x + mx];
        let y = [min_y - my, max_y + my];
        Self {
            x_bounds: x,
            y_bounds: y,
            fitted: (x, y),
        }
    }

    /// Pan by 10% of the current span (contract §3).
    pub fn pan(&mut self, dx: i8, dy: i8) {
        let sx = (self.x_bounds[1] - self.x_bounds[0]) * 0.10 * f64::from(dx);
        let sy = (self.y_bounds[1] - self.y_bounds[0]) * 0.10 * f64::from(dy);
        self.x_bounds = [self.x_bounds[0] + sx, self.x_bounds[1] + sx];
        self.y_bounds = [self.y_bounds[0] + sy, self.y_bounds[1] + sy];
        self.clamp();
    }

    /// Zoom about the center: `×0.8` in, `×1.25` out (contract §3).
    pub fn zoom(&mut self, zoom_in: bool) {
        let factor = if zoom_in { 0.8 } else { 1.25 };
        for (bounds, fit) in [
            (&mut self.x_bounds, self.fitted.0),
            (&mut self.y_bounds, self.fitted.1),
        ] {
            let center = (bounds[0] + bounds[1]) / 2.0;
            let half = (bounds[1] - bounds[0]) / 2.0 * factor;
            // Never zoom out past the fitted span + one span of slack.
            let max_half = fit[1] - fit[0];
            let half = half.min(max_half);
            *bounds = [center - half, center + half];
        }
        self.clamp();
    }

    /// `0`: restore the fitted bbox.
    pub fn reset(&mut self) {
        self.x_bounds = self.fitted.0;
        self.y_bounds = self.fitted.1;
    }

    /// Keep the window inside the fitted bbox ± one span (contract §3's
    /// clamp — the map can never be panned into empty infinity).
    fn clamp(&mut self) {
        for (bounds, fit) in [
            (&mut self.x_bounds, self.fitted.0),
            (&mut self.y_bounds, self.fitted.1),
        ] {
            let span = fit[1] - fit[0];
            let lo = fit[0] - span;
            let hi = fit[1] + span;
            let width = bounds[1] - bounds[0];
            if bounds[0] < lo {
                *bounds = [lo, lo + width];
            }
            if bounds[1] > hi {
                *bounds = [hi - width, hi];
            }
        }
    }
}

/// The map pane's chrome-owned state (contract §2).
#[derive(Debug, Default)]
pub struct MapView {
    /// Current tier (`y` cycles).
    pub tier: Tier,
    /// Current lens (`l` cycles).
    pub lens: Lens,
    /// The last good payload.
    pub payload: Option<ChoroplethPayload>,
    /// LOUD wire-failure flag (malformed JSON or an unknown band role) —
    /// renders the UNREADABLE line, never a stale or fabricated map.
    pub payload_failed: bool,
    /// Pan/zoom window; rebuilt on ingest when geometry exists.
    pub viewport: Option<Viewport>,
}

impl MapView {
    /// The pinned `choropleth_json` args (field order IS the wire order).
    #[must_use]
    pub fn args_json(&self) -> String {
        format!(
            r#"{{"tier": "{}", "lens": "{}"}}"#,
            self.tier.wire(),
            self.lens.wire()
        )
    }

    /// Parse a `choropleth_json` reply. `"null"` is honest absence (the
    /// tier has nothing — the render shows the absence line); malformed
    /// JSON or an unknown band role sets the LOUD flag.
    pub fn ingest_choropleth(&mut self, raw: &str) {
        self.payload_failed = false;
        if raw == "null" {
            self.payload = None;
            return;
        }
        match serde_json::from_str::<ChoroplethPayload>(raw) {
            Ok(payload) => {
                if payload
                    .bands
                    .iter()
                    .any(|(_, role)| role_color(role).is_none())
                {
                    self.payload = None;
                    self.payload_failed = true;
                    return;
                }
                self.rebuild_viewport(&payload);
                self.payload = Some(payload);
            }
            Err(_) => {
                self.payload = None;
                self.payload_failed = true;
            }
        }
    }

    fn rebuild_viewport(&mut self, payload: &ChoroplethPayload) {
        let mut bbox: Option<(f64, f64, f64, f64)> = None;
        for cell in &payload.cells {
            let Some(wkt) = cell.wkt.as_deref() else {
                continue;
            };
            let Some(rings) = wkt_exterior_rings(wkt) else {
                continue;
            };
            for ring in rings {
                for (x, y) in ring.points {
                    bbox = Some(match bbox {
                        None => (x, y, x, y),
                        Some((ax, ay, bx, by)) => (x.min(ax), y.min(ay), x.max(bx), y.max(by)),
                    });
                }
            }
        }
        self.viewport = bbox
            .map(|(min_x, min_y, max_x, max_y)| Viewport::fitted_to(min_x, min_y, max_x, max_y));
    }

    /// The map-pane key block (contract §3); `Esc` stays the
    /// integrator's (pane exit is chrome routing, not view state).
    pub fn handle_key(&mut self, ch: char) -> MapAction {
        match ch {
            'l' => {
                self.lens = self.lens.next();
                MapAction::NeedsRefresh
            }
            'y' => {
                self.tier = self.tier.next();
                MapAction::NeedsRefresh
            }
            '+' | '=' => self.with_viewport(|v| v.zoom(true)),
            '-' => self.with_viewport(|v| v.zoom(false)),
            '0' => self.with_viewport(Viewport::reset),
            _ => MapAction::NotHandled,
        }
    }

    /// Arrow-key pan (named keys arrive separately from chars).
    pub fn handle_arrow(&mut self, dx: i8, dy: i8) -> MapAction {
        self.with_viewport(|v| v.pan(dx, dy))
    }

    fn with_viewport(&mut self, f: impl FnOnce(&mut Viewport)) -> MapAction {
        match self.viewport.as_mut() {
            Some(viewport) => {
                f(viewport);
                MapAction::Handled
            }
            // No geometry on screen: the key is consumed (it IS a map
            // key) but there is nothing to move.
            None => MapAction::Handled,
        }
    }
}

#[cfg(test)]
mod view_state_tests {
    use super::*;

    const ENVELOPE: &str = r#"{
        "tier": "county", "lens": "value", "verified_tick": 3,
        "bands": [[null, "panel"], [1.0, "dim"], [2.0, "gold"], [null, "crimson"]],
        "overlay_absent": "national overlay ruled (ADR171); Phase-0 incidence artifact not yet built",
        "cells": [
            {"region_id": "26163", "value": 2.5,
             "wkt": "POLYGON((0 0, 4 0, 4 4, 0 4, 0 0))", "centroid": null},
            {"region_id": "01001", "value": "inf", "wkt": null, "centroid": null},
            {"region_id": "02002", "value": null, "wkt": null, "centroid": null}
        ]
    }"#;

    #[test]
    fn args_json_is_pinned_field_order() {
        let mut view = MapView::default();
        assert_eq!(view.args_json(), r#"{"tier": "county", "lens": "value"}"#);
        view.handle_key('l');
        view.handle_key('y');
        assert_eq!(view.args_json(), r#"{"tier": "state", "lens": "tension"}"#);
    }

    #[test]
    fn lens_cycles_value_tension_fog_and_tier_skips_ea() {
        let mut view = MapView::default();
        assert_eq!(view.handle_key('l'), MapAction::NeedsRefresh);
        assert_eq!(view.lens, Lens::Tension);
        view.handle_key('l');
        assert_eq!(view.lens, Lens::Fog);
        view.handle_key('l');
        assert_eq!(view.lens, Lens::Value);
        view.handle_key('y');
        assert_eq!(view.tier, Tier::State);
        view.handle_key('y');
        assert_eq!(view.tier, Tier::County);
    }

    #[test]
    fn ingest_parses_cells_and_builds_the_viewport_from_wkt() {
        let mut view = MapView::default();
        view.ingest_choropleth(ENVELOPE);
        assert!(!view.payload_failed);
        let payload = view.payload.as_ref().expect("payload");
        assert_eq!(payload.cells.len(), 3);
        assert_eq!(payload.cells[1].value, Some(CellValue::Text("inf".into())));
        assert_eq!(payload.cells[2].value, None);
        let viewport = view.viewport.as_ref().expect("viewport from WKT bbox");
        assert!(viewport.x_bounds[0] < 0.0 && viewport.x_bounds[1] > 4.0);
    }

    #[test]
    fn null_is_honest_absence_and_malformed_is_loud() {
        let mut view = MapView::default();
        view.ingest_choropleth("null");
        assert!(view.payload.is_none() && !view.payload_failed);
        view.ingest_choropleth("{not json");
        assert!(view.payload.is_none() && view.payload_failed);
    }

    #[test]
    fn unknown_band_role_is_a_loud_protocol_failure() {
        let mut view = MapView::default();
        let bad = ENVELOPE.replace("\"crimson\"", "\"chartreuse\"");
        view.ingest_choropleth(&bad);
        assert!(view.payload.is_none() && view.payload_failed);
    }

    #[test]
    fn wkt_parser_handles_polygon_and_multipolygon_and_rejects_junk() {
        let rings = wkt_exterior_rings("POLYGON((0 0, 1 0, 1 1, 0 0))").expect("polygon");
        assert_eq!(rings.len(), 1);
        assert_eq!(rings[0].points.len(), 4);
        let multi =
            wkt_exterior_rings("MULTIPOLYGON(((0 0, 1 0, 1 1, 0 0)), ((2 2, 3 2, 3 3, 2 2)))")
                .expect("multipolygon");
        assert_eq!(multi.len(), 2);
        assert!(wkt_exterior_rings("LINESTRING(0 0, 1 1)").is_none());
        assert!(wkt_exterior_rings("POLYGON((0 0, 1 0))").is_none());
    }

    #[test]
    fn viewport_math_is_the_pinned_contract() {
        let mut viewport = Viewport::fitted_to(0.0, 0.0, 10.0, 10.0);
        let fitted = viewport.clone();
        viewport.pan(1, 0);
        let span = fitted.x_bounds[1] - fitted.x_bounds[0];
        assert!((viewport.x_bounds[0] - (fitted.x_bounds[0] + span * 0.10)).abs() < 1e-9);
        viewport.zoom(true);
        let new_span = viewport.x_bounds[1] - viewport.x_bounds[0];
        assert!((new_span - span * 0.8).abs() < 1e-9);
        viewport.reset();
        assert_eq!(viewport.x_bounds, fitted.x_bounds);
        // The clamp: 40 pans right never escape fitted + one span.
        for _ in 0..40 {
            viewport.pan(1, 0);
        }
        let hi_limit = fitted.fitted.0[1] + (fitted.fitted.0[1] - fitted.fitted.0[0]);
        assert!(viewport.x_bounds[1] <= hi_limit + 1e-9);
    }

    #[test]
    fn keys_without_geometry_are_consumed_not_fallthrough() {
        let mut view = MapView::default();
        assert_eq!(view.handle_key('+'), MapAction::Handled);
        assert_eq!(view.handle_arrow(0, 1), MapAction::Handled);
        assert_eq!(view.handle_key('q'), MapAction::NotHandled);
    }
}
