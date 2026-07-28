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

use ratatui::layout::Rect;
use ratatui::style::{Color, Style};
use ratatui::symbols::Marker;
use ratatui::text::{Line, Span};
use ratatui::widgets::canvas::{Canvas, Painter, Shape};
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;
use serde::Deserialize;

use super::topology::PANEL;
use crate::theme::{BONE, CRIMSON, DIM};

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
    /// The no-WKT fallback anchor: a cell without geometry renders as a
    /// labeled dot here (contract §2). Polygon labels derive from bboxes
    /// instead; the host sends `null` for every cell this milestone.
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
        // The absence fill: the Textual client's `map_room._band_color`
        // returns `theme.PANEL` ("#200404") for absence — mapped to the
        // module-local parity constant [`PANEL`] in `views::topology`,
        // NOT `theme::MUTED_DARK` (a §9b token with a different value).
        "panel" => Some(PANEL),
        "dim" => Some(crate::theme::DIM),
        "gold" => Some(crate::theme::GOLD),
        "crimson" => Some(crate::theme::CRIMSON),
        _ => None,
    }
}

/// Resolve one cell's lens value to its band color (the envelope's
/// `bands` rows — contract §1: bands are DATA, never Rust literals).
///
/// Numeric lenses (value/tension): the FIRST row's `null` threshold is
/// the absence band; middle rows are ascending thresholds matched with
/// `<=` (the Textual `map_room._band_color` precedent); the LAST row's
/// `null` threshold is the open top band, which also catches the `"inf"`
/// bled-dry encoding (JSON has no Infinity). The fog lens is categorical:
/// every threshold is a status string matched by equality; an absent or
/// unmatched status falls to the absence fill.
///
/// Roles were validated at ingest ([`MapView::ingest_choropleth`] flags
/// unknown roles LOUD), so a `role_color` miss here is unreachable off
/// the wire and resolves to the absence fill.
pub fn band_color_for(bands: &[(serde_json::Value, String)], value: Option<&CellValue>) -> Color {
    let color = |role: &str| role_color(role).unwrap_or(PANEL);
    if bands.iter().all(|(threshold, _)| threshold.is_string()) {
        // Categorical (fog).
        if let Some(CellValue::Text(status)) = value {
            for (threshold, role) in bands {
                if threshold.as_str() == Some(status) {
                    return color(role);
                }
            }
        }
        return PANEL;
    }
    match value {
        None => bands
            .iter()
            .find(|(threshold, _)| threshold.is_null())
            .map_or(PANEL, |(_, role)| color(role)),
        // The only Text a numeric lens emits is "inf": the open top band.
        Some(CellValue::Text(_)) => bands.last().map_or(PANEL, |(_, role)| color(role)),
        Some(CellValue::Num(v)) => {
            for (threshold, role) in bands {
                if let Some(limit) = threshold.as_f64() {
                    if *v <= limit {
                        return color(role);
                    }
                }
            }
            bands.last().map_or(PANEL, |(_, role)| color(role))
        }
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

/// One render-ready cell: parsed geometry + the label anchor inputs,
/// built once at ingest (parse once, render many — and a malformed WKT
/// is flagged LOUD at the ingest seam, never discovered mid-frame).
#[derive(Debug, Clone)]
struct PlottedCell {
    region_id: String,
    value: Option<CellValue>,
    rings: Vec<Ring>,
    /// `(min_x, min_y, max_x, max_y)` over the rings; `None` without WKT.
    bbox: Option<(f64, f64, f64, f64)>,
    centroid: Option<(f64, f64)>,
}

/// Parse every cell's geometry, or `None` on the first malformed WKT —
/// the caller sets the LOUD flag (contract §2: never silently skip).
fn build_plotted(payload: &ChoroplethPayload) -> Option<Vec<PlottedCell>> {
    let mut plotted = Vec::with_capacity(payload.cells.len());
    for cell in &payload.cells {
        let rings = match cell.wkt.as_deref() {
            Some(wkt) => wkt_exterior_rings(wkt)?,
            None => Vec::new(),
        };
        let mut bbox: Option<(f64, f64, f64, f64)> = None;
        for ring in &rings {
            for &(x, y) in &ring.points {
                bbox = Some(extend_bbox(bbox, x, y));
            }
        }
        plotted.push(PlottedCell {
            region_id: cell.region_id.clone(),
            value: cell.value.clone(),
            rings,
            bbox,
            centroid: cell.centroid,
        });
    }
    Some(plotted)
}

fn extend_bbox(bbox: Option<(f64, f64, f64, f64)>, x: f64, y: f64) -> (f64, f64, f64, f64) {
    match bbox {
        None => (x, y, x, y),
        Some((ax, ay, bx, by)) => (x.min(ax), y.min(ay), x.max(bx), y.max(by)),
    }
}

/// Fit a viewport over every plotted bbox and centroid, or `None` when
/// no cell carries geometry at all (the honest-absence render case).
fn viewport_over(plotted: &[PlottedCell]) -> Option<Viewport> {
    let mut bbox: Option<(f64, f64, f64, f64)> = None;
    for cell in plotted {
        if let Some((ax, ay, bx, by)) = cell.bbox {
            bbox = Some(extend_bbox(bbox, ax, ay));
            bbox = Some(extend_bbox(bbox, bx, by));
        }
        if let Some((x, y)) = cell.centroid {
            bbox = Some(extend_bbox(bbox, x, y));
        }
    }
    bbox.map(|(min_x, min_y, max_x, max_y)| Viewport::fitted_to(min_x, min_y, max_x, max_y))
}

/// A polygon exterior ring filled by grid-space scanline (contract §2's
/// hand-written [`Shape`] — recon: NO built-in polygon fill exists in
/// ratatui 0.30).
struct FilledRing<'a> {
    points: &'a [(f64, f64)],
    color: Color,
}

impl Shape for FilledRing<'_> {
    fn draw(&self, painter: &mut Painter) {
        let (xb, yb) = painter.bounds();
        let (left, right, bottom, top) = (xb[0], xb[1], yb[0], yb[1]);
        let (width, height) = (right - left, top - bottom);
        if width <= 0.0 || height <= 0.0 {
            return;
        }
        // Recover the grid resolution from the corner projections —
        // `Painter::get_point`'s own affine, so fills land on the same
        // cells every other shape's points do.
        let Some((_, gy_max)) = painter.get_point(left, bottom) else {
            return;
        };
        let Some((gx_max, _)) = painter.get_point(right, top) else {
            return;
        };
        let (res_w, res_h) = (gx_max + 1, gy_max + 1);
        for gy in 0..res_h {
            let y = if res_h > 1 {
                top - (gy as f64) * height / ((res_h - 1) as f64)
            } else {
                (top + bottom) / 2.0
            };
            self.fill_row(painter, y, gy, left, width, res_w);
        }
    }
}

impl FilledRing<'_> {
    /// Paint one grid row: even-odd x-crossings of the ring against the
    /// horizontal line at data-space `y`, filled pairwise.
    fn fill_row(
        &self,
        painter: &mut Painter,
        y: f64,
        gy: usize,
        left: f64,
        width: f64,
        res_w: usize,
    ) {
        let n = self.points.len();
        let mut crossings: Vec<f64> = Vec::new();
        for i in 0..n {
            let (x1, y1) = self.points[i];
            // `% n` closes an open ring; a closed ring's duplicate final
            // edge is zero-length (`y1 == y2`) and contributes nothing.
            let (x2, y2) = self.points[(i + 1) % n];
            if (y1 > y) != (y2 > y) {
                crossings.push(x1 + (y - y1) * (x2 - x1) / (y2 - y1));
            }
        }
        crossings.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        for pair in crossings.chunks_exact(2) {
            let x0 = pair[0].max(left);
            let x1 = pair[1].min(left + width);
            if x1 < x0 {
                continue;
            }
            let g0 = ((x0 - left) * ((res_w - 1) as f64) / width).round() as usize;
            let g1 = ((x1 - left) * ((res_w - 1) as f64) / width).round() as usize;
            for gx in g0..=g1.min(res_w - 1) {
                painter.paint(gx, gy, self.color);
            }
        }
    }
}

/// The no-WKT fallback: a single painted point at the wire centroid
/// (contract §2's "labeled centroid dot").
struct CentroidDot {
    x: f64,
    y: f64,
    color: Color,
}

impl Shape for CentroidDot {
    fn draw(&self, painter: &mut Painter) {
        if let Some((gx, gy)) = painter.get_point(self.x, self.y) {
            painter.paint(gx, gy, self.color);
        }
    }
}

/// Where a cell's region-id label anchors, or `None` when it would not
/// fit: a WKT cell labels at its bbox center once the bbox is wide
/// enough (in canvas columns) to hold the id and at least one text row
/// tall — labels appear as the player zooms in, instead of 3,000+
/// county ids shredding the nationwide fit into noise. A centroid-dot
/// cell (no WKT) is ALWAYS labeled — the dot alone is unreadable
/// (contract §2's "labeled centroid dot").
///
/// An in-window anchor whose text would overflow the right bound shifts
/// left to fit (the canvas clips labels at the area edge — a clipped
/// region id reads as the WRONG id, worse than a shifted one); an
/// out-of-window anchor passes through untouched so the canvas's own
/// bounds filter drops it with its region.
fn label_anchor(
    cell: &PlottedCell,
    units_per_col: f64,
    units_per_row: f64,
    x_bounds: [f64; 2],
) -> Option<(f64, f64)> {
    let chars = cell.region_id.chars().count() as f64;
    let half_width = units_per_col * chars / 2.0;
    let anchor = match (cell.bbox, cell.centroid) {
        (Some((min_x, min_y, max_x, max_y)), _) => {
            let fits = (max_x - min_x) >= units_per_col * chars && (max_y - min_y) >= units_per_row;
            fits.then(|| ((min_x + max_x) / 2.0 - half_width, (min_y + max_y) / 2.0))
        }
        (None, Some((x, y))) => Some((x - half_width, y)),
        (None, None) => None,
    };
    anchor.map(|(x, y)| {
        let (left, right) = (x_bounds[0], x_bounds[1]);
        if x >= left && x <= right {
            (x.min(right - units_per_col * chars).max(left), y)
        } else {
            (x, y)
        }
    })
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
    /// Render-ready cells (parsed WKT + label inputs), rebuilt on ingest.
    plotted: Vec<PlottedCell>,
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
    /// JSON, an unknown band role, or malformed cell WKT sets the LOUD
    /// flag (all three are PROTOCOL failures, never a partial map).
    pub fn ingest_choropleth(&mut self, raw: &str) {
        self.payload_failed = false;
        if raw == "null" {
            self.payload = None;
            self.plotted.clear();
            self.viewport = None;
            return;
        }
        match serde_json::from_str::<ChoroplethPayload>(raw) {
            Ok(payload) => {
                let roles_ok = payload
                    .bands
                    .iter()
                    .all(|(_, role)| role_color(role).is_some());
                match build_plotted(&payload) {
                    Some(plotted) if roles_ok => {
                        self.viewport = viewport_over(&plotted);
                        self.plotted = plotted;
                        self.payload = Some(payload);
                    }
                    _ => self.fail_loud(),
                }
            }
            Err(_) => self.fail_loud(),
        }
    }

    fn fail_loud(&mut self) {
        self.payload = None;
        self.plotted.clear();
        self.viewport = None;
        self.payload_failed = true;
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

    /// Render the pane into `area` — contract §2's absence ladder: LOUD
    /// unreadable > honest tier absence > the lens banner > geometry
    /// absence > the band-colored canvas.
    pub fn render(&mut self, frame: &mut Frame<'_>, area: Rect) {
        let title = format!("map — {}/{}", self.tier.wire(), self.lens.wire());
        let block = Block::bordered().title(title);
        let inner = block.inner(area);
        frame.render_widget(block, area);
        if self.payload_failed {
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    "▌ map UNREADABLE — malformed host data",
                    Style::new().fg(CRIMSON),
                ))),
                inner,
            );
            return;
        }
        let Some(payload) = &self.payload else {
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    format!(
                        "▌ no {} map — no county-bearing territories in this campaign's graph",
                        self.tier.wire()
                    ),
                    Style::new().fg(DIM),
                ))),
                inner,
            );
            return;
        };
        let mut canvas_area = inner;
        if let Some(reason) = &payload.lens_absent_reason {
            // The one-line CRIMSON banner over the canvas (contract §2,
            // the pixel-degradation precedent).
            let banner = Rect {
                height: inner.height.min(1),
                ..inner
            };
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    format!("▌ {reason}"),
                    Style::new().fg(CRIMSON),
                ))),
                banner,
            );
            canvas_area = Rect {
                y: inner.y.saturating_add(1),
                height: inner.height.saturating_sub(1),
                ..inner
            };
        }
        if payload.cells.is_empty() || canvas_area.height == 0 || canvas_area.width == 0 {
            return;
        }
        let has_geometry = self
            .plotted
            .iter()
            .any(|cell| cell.bbox.is_some() || cell.centroid.is_some());
        if !has_geometry {
            frame.render_widget(
                Paragraph::new(Line::from(Span::styled(
                    "▌ cells present but no geometry on the wire — county WKT source unavailable",
                    Style::new().fg(DIM),
                ))),
                canvas_area,
            );
            return;
        }
        let Some(viewport) = &self.viewport else {
            return; // Unreachable with geometry present; typed guard.
        };
        self.render_canvas(frame, canvas_area, payload, viewport);
    }

    /// The band-colored canvas + labels (labels always draw on top —
    /// `Context::print` renders after every layer, contract §2 recon).
    fn render_canvas(
        &self,
        frame: &mut Frame<'_>,
        area: Rect,
        payload: &ChoroplethPayload,
        viewport: &Viewport,
    ) {
        let x_span = viewport.x_bounds[1] - viewport.x_bounds[0];
        let y_span = viewport.y_bounds[1] - viewport.y_bounds[0];
        let units_per_col = x_span / f64::from(area.width.max(1));
        let units_per_row = y_span / f64::from(area.height.max(1));
        let canvas = Canvas::default()
            .marker(Marker::HalfBlock)
            .x_bounds(viewport.x_bounds)
            .y_bounds(viewport.y_bounds)
            .paint(|ctx| {
                for cell in &self.plotted {
                    let color = band_color_for(&payload.bands, cell.value.as_ref());
                    for ring in &cell.rings {
                        ctx.draw(&FilledRing {
                            points: &ring.points,
                            color,
                        });
                    }
                    if cell.rings.is_empty() {
                        if let Some((x, y)) = cell.centroid {
                            ctx.draw(&CentroidDot { x, y, color });
                        }
                    }
                    if let Some((x, y)) =
                        label_anchor(cell, units_per_col, units_per_row, viewport.x_bounds)
                    {
                        ctx.print(
                            x,
                            y,
                            Line::from(Span::styled(cell.region_id.clone(), Style::new().fg(BONE))),
                        );
                    }
                }
            });
        frame.render_widget(canvas, area);
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

    #[test]
    fn malformed_cell_wkt_is_a_loud_protocol_failure() {
        let mut view = MapView::default();
        let bad = ENVELOPE.replace("POLYGON((0 0, 4 0, 4 4, 0 4, 0 0))", "POLYGON((junk");
        view.ingest_choropleth(&bad);
        assert!(view.payload.is_none() && view.payload_failed);
    }

    #[test]
    fn value_band_resolution_is_the_textual_precedent() {
        let bands: Vec<(serde_json::Value, String)> = vec![
            (serde_json::Value::Null, "panel".into()),
            (1.0.into(), "dim".into()),
            (2.0.into(), "gold".into()),
            (serde_json::Value::Null, "crimson".into()),
        ];
        assert_eq!(band_color_for(&bands, None), PANEL);
        let num = |v: f64| CellValue::Num(v);
        assert_eq!(band_color_for(&bands, Some(&num(1.0))), crate::theme::DIM);
        assert_eq!(band_color_for(&bands, Some(&num(1.5))), crate::theme::GOLD);
        assert_eq!(
            band_color_for(&bands, Some(&num(2.5))),
            crate::theme::CRIMSON
        );
        let inf = CellValue::Text("inf".into());
        assert_eq!(band_color_for(&bands, Some(&inf)), crate::theme::CRIMSON);
    }

    #[test]
    fn tension_band_resolution_is_the_diverging_channel() {
        let bands: Vec<(serde_json::Value, String)> = vec![
            (serde_json::Value::Null, "panel".into()),
            ((-0.15).into(), "crimson".into()),
            (0.15.into(), "dim".into()),
            (serde_json::Value::Null, "gold".into()),
        ];
        let num = |v: f64| CellValue::Num(v);
        assert_eq!(
            band_color_for(&bands, Some(&num(-0.5))),
            crate::theme::CRIMSON
        );
        assert_eq!(band_color_for(&bands, Some(&num(0.0))), crate::theme::DIM);
        assert_eq!(band_color_for(&bands, Some(&num(0.5))), crate::theme::GOLD);
    }

    #[test]
    fn fog_band_resolution_is_categorical() {
        let bands: Vec<(serde_json::Value, String)> = vec![
            ("exact".into(), "gold".into()),
            ("approximate".into(), "dim".into()),
            ("unknown".into(), "panel".into()),
        ];
        let status = |s: &str| CellValue::Text(s.into());
        assert_eq!(
            band_color_for(&bands, Some(&status("exact"))),
            crate::theme::GOLD
        );
        assert_eq!(band_color_for(&bands, Some(&status("mystery"))), PANEL);
        assert_eq!(band_color_for(&bands, None), PANEL);
    }
}
