//! The dashboard pane: national trend charts + the economy snapshot
//! (M6 Tasks 42/43, contract `docs/superpowers/specs/
//! 2026-07-28-m6-market-contracts.md` §2).
//!
//! The TopologyView shape verbatim: chrome-owned state, `ingest_*` with
//! LOUD parse-failure flags, `args_json` in pinned field order. Serde
//! structs mirror the Pydantic optionality EXACTLY (`Option<f64>` /
//! `Option<i64>`) and charts GAP-SKIP `None` points — never fabricate a
//! zero (the `EndgameSlot` precedent, Constitution III.11).
//!
//! **Gauge veto (contract §2, pre-scouted):** `ratatui::widgets::Gauge::
//! ratio()` `assert!`s `[0.0, 1.0]`, and the overshoot ratio `O = C/B` is
//! UNBOUNDED above 1.0 — O>1 IS the signal. Shares that can exceed 1 use
//! the in-crate hand-drawn bar idiom (`hud.rs::bar_glyphs`, reimplemented
//! locally: clamp for the glyphs, label carries the TRUE value).

use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::{Color, Style};
use ratatui::symbols::Marker;
use ratatui::text::{Line, Span};
use ratatui::widgets::{Axis, Block, Chart, Dataset, GraphType, Paragraph, Sparkline};
use ratatui::Frame;
use serde::Deserialize;

use crate::theme::{BONE, CRIMSON, DIM, GOLD, GREEN_DARK, ROYAL};

/// What a handled key asks the integrator to do (the `MapAction` mirror).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DashboardAction {
    /// Consumed, no data change ('c'/'m' are pure view state).
    Handled,
    /// Not a dashboard key — fall through.
    NotHandled,
}

/// The chart-page cycle (`c`, contract §2): one page rendered large,
/// keybar shows position.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum ChartPage {
    /// Φ level (Line) + per-tick delta (Bar) — the Fundamental Theorem's
    /// Imperial Rent series.
    #[default]
    ImperialRent,
    /// The Program 23 price⟷value scissors: `price_log` vs
    /// `fictitious_log`, two named datasets.
    Scissors,
    /// The correction-snap ledger: cumulative count + per-tick snaps.
    Corrections,
    /// The five 0041 playability series.
    Playability,
    /// The `national_value` + `EconomyView` snapshot panel.
    Snapshot,
}

impl ChartPage {
    /// Total pages (the keybar position readout).
    pub const COUNT: usize = 5;

    fn next(self) -> Self {
        match self {
            Self::ImperialRent => Self::Scissors,
            Self::Scissors => Self::Corrections,
            Self::Corrections => Self::Playability,
            Self::Playability => Self::Snapshot,
            Self::Snapshot => Self::ImperialRent,
        }
    }

    /// 1-based position for the pane title / keybar.
    pub fn position(self) -> usize {
        match self {
            Self::ImperialRent => 1,
            Self::Scissors => 2,
            Self::Corrections => 3,
            Self::Playability => 4,
            Self::Snapshot => 5,
        }
    }

    /// The page's display title.
    pub fn title(self) -> &'static str {
        match self {
            Self::ImperialRent => "imperial rent",
            Self::Scissors => "price⟷value scissors",
            Self::Corrections => "market corrections",
            Self::Playability => "playability series",
            Self::Snapshot => "value snapshot",
        }
    }
}

/// One `v_national_trend` row off the wire — every series `Option`
/// (honest absence; deltas are `NULL` at a session's first tick and the
/// playability levels before the first year boundary).
#[derive(Debug, Clone, Deserialize)]
pub struct TrendRow {
    /// The committed tick this row summarizes.
    pub tick: u64,
    /// Φ this tick.
    pub imperial_rent: Option<f64>,
    /// `imperial_rent - LAG(imperial_rent)`.
    pub imperial_rent_delta: Option<f64>,
    /// Market Scissors price-index log.
    pub price_log: Option<f64>,
    /// Its per-tick delta.
    pub price_log_delta: Option<f64>,
    /// Market Scissors fictitious-capitalization log.
    pub fictitious_log: Option<f64>,
    /// Its per-tick delta.
    pub fictitious_log_delta: Option<f64>,
    /// Cumulative correction-snap count.
    pub market_corrections: Option<i64>,
    /// New snaps since the prior tick.
    pub market_corrections_delta: Option<i64>,
    /// Population share of counties in an active crisis phase.
    pub crisis_pop_share: Option<f64>,
    /// Its per-tick delta.
    pub crisis_pop_share_delta: Option<f64>,
    /// Population-weighted county mean bifurcation score.
    pub bifurcation_score_mean: Option<f64>,
    /// Its per-tick delta.
    pub bifurcation_score_mean_delta: Option<f64>,
    /// Population-weighted county mean wage compression.
    pub wage_compression_mean: Option<f64>,
    /// Its per-tick delta.
    pub wage_compression_mean_delta: Option<f64>,
    /// Extensive county capital-stock sum.
    pub capital_stock_total: Option<f64>,
    /// Its per-tick delta.
    pub capital_stock_total_delta: Option<f64>,
    /// Population-weighted county mean unemployment rate.
    pub unemployment_rate_mean: Option<f64>,
    /// Its per-tick delta.
    pub unemployment_rate_mean_delta: Option<f64>,
}

/// The envelope's `national_value` snapshot (rates pre-derived host-side,
/// ratio-of-sums; `tick` is the staleness disclosure — the hex ledger is
/// hydration-time-frozen).
#[derive(Debug, Clone, Deserialize)]
pub struct NationalValueWire {
    /// The tick the hex ledger row was written at.
    pub tick: u64,
    /// Constant capital sum.
    pub c_sum: f64,
    /// Variable capital sum.
    pub v_sum: f64,
    /// Surplus sum.
    pub s_sum: f64,
    /// Capital-stock sum.
    pub k_sum: f64,
    /// `s/v`, or `None` at a zero denominator.
    pub exploitation_rate: Option<f64>,
    /// `s/(c+v)`, or `None` at a zero denominator.
    pub profit_rate: Option<f64>,
}

/// The parsed `trend_json` envelope.
#[derive(Debug, Clone, Deserialize)]
pub struct TrendPayload {
    /// The tick the window was read at.
    pub verified_tick: u64,
    /// Rows oldest→newest.
    pub rows: Vec<TrendRow>,
    /// The value-composition snapshot, or `None` (no hex hydration).
    pub national_value: Option<NationalValueWire>,
}

/// The parsed `dashboard_view_json` payload — `EconomyView`'s optionality
/// mirrored EXACTLY (every substantive field `Option`); `kind`/
/// `economy_id`/`class_phi_readings` are deliberately not modeled (serde
/// ignores unknown fields; the snapshot panel renders none of them).
#[derive(Debug, Clone, Deserialize)]
pub struct EconomyPayload {
    /// The committed tick this dossier was projected from.
    pub verified_tick: u64,
    /// The wage opposition's signed balance in `[-1, 1]`.
    pub wage_balance: Option<f64>,
    /// `wage_balance > 0` — the Fundamental Theorem verdict.
    pub labor_aristocracy_verdict: Option<bool>,
    /// Emmanuel/Amin international transfer.
    pub phi_unequal_exchange: Option<f64>,
    /// Meillassoux externalized reproduction.
    pub phi_reproduction: Option<f64>,
    /// Fortunati domestic shadow labor.
    pub phi_domestic: Option<f64>,
    /// The kernel's invisible-fraction Φ_III report.
    pub phi_iii_report: Option<f64>,
    /// Sum of the three decomposition channels.
    pub phi_decomposition_total: Option<f64>,
    /// Vol-III: total surplus produced.
    pub surplus_produced: Option<f64>,
    /// Vol-III split: profit of enterprise.
    pub profit_of_enterprise: Option<f64>,
    /// Vol-III split: interest burden.
    pub interest_burden: Option<f64>,
    /// Vol-III split: ground rent.
    pub ground_rent: Option<f64>,
    /// Vol-III split: taxes on surplus.
    pub taxes_on_surplus: Option<f64>,
    /// Rentier share of surplus (CAN exceed 1 — bar-idiom, never Gauge).
    pub rentier_share: Option<f64>,
    /// Financialization share (same unbounded caveat).
    pub financialization_share: Option<f64>,
    /// Matter book: total consumption C.
    pub total_consumption: Option<f64>,
    /// Matter book: total biocapacity B.
    pub total_biocapacity: Option<f64>,
    /// Overshoot `O = C/B` — UNBOUNDED above 1, O>1 IS the signal.
    pub overshoot_ratio: Option<f64>,
    /// The metabolic ceiling.
    pub biocapacity_ceiling: Option<f64>,
    /// Energy β_J.
    pub energy_beta_j: Option<f64>,
}

/// The dashboard pane's chrome-owned state (contract §2).
#[derive(Debug, Default)]
pub struct DashboardView {
    /// Current chart page (`c` cycles).
    pub page: ChartPage,
    /// The `m` ridgeline-3D toggle (§3; renders a declared line until the
    /// raster scene lands / on glyph-floor builds).
    pub ridgeline: bool,
    /// The last good trend envelope.
    pub trend: Option<TrendPayload>,
    /// LOUD trend wire-failure flag.
    pub trend_failed: bool,
    /// The last good economy snapshot.
    pub snapshot: Option<EconomyPayload>,
    /// LOUD snapshot wire-failure flag.
    pub snapshot_failed: bool,
}

impl DashboardView {
    /// The pinned `trend_json` args (field order IS the wire order).
    /// `last_n` is a fixed client window — 120 ticks ≈ 2.3 simulated
    /// years, enough for every chart at braille resolution.
    #[must_use]
    pub fn args_json(&self) -> String {
        r#"{"last_n": 120}"#.to_string()
    }

    /// Parse a `trend_json` reply. `"null"` is honest absence; malformed
    /// JSON sets the LOUD flag.
    pub fn ingest_trend(&mut self, raw: &str) {
        self.trend_failed = false;
        if raw == "null" {
            self.trend = None;
            return;
        }
        match serde_json::from_str::<TrendPayload>(raw) {
            Ok(payload) => self.trend = Some(payload),
            Err(_) => {
                self.trend = None;
                self.trend_failed = true;
            }
        }
    }

    /// Parse a `dashboard_view_json` reply — same contract.
    pub fn ingest_dashboard(&mut self, raw: &str) {
        self.snapshot_failed = false;
        if raw == "null" {
            self.snapshot = None;
            return;
        }
        match serde_json::from_str::<EconomyPayload>(raw) {
            Ok(payload) => self.snapshot = Some(payload),
            Err(_) => {
                self.snapshot = None;
                self.snapshot_failed = true;
            }
        }
    }

    /// The dashboard-pane key block (contract §2): `c` cycles the chart
    /// page, `m` toggles the ridgeline mode; `Esc` stays the integrator's.
    pub fn handle_key(&mut self, ch: char) -> DashboardAction {
        match ch {
            'c' => {
                self.page = self.page.next();
                DashboardAction::Handled
            }
            'm' => {
                self.ridgeline = !self.ridgeline;
                DashboardAction::Handled
            }
            _ => DashboardAction::NotHandled,
        }
    }

    /// Render the pane into `area` — per-page absence ladder: LOUD
    /// unreadable > honest absence naming the missing producer > charts.
    pub fn render(&mut self, frame: &mut Frame<'_>, area: Rect) {
        let title = format!(
            "dashboard — {} [{}/{}] (c cycles, m ridgeline)",
            self.page.title(),
            self.page.position(),
            ChartPage::COUNT,
        );
        let block = Block::bordered().title(title);
        let inner = block.inner(area);
        frame.render_widget(block, area);
        if inner.width == 0 || inner.height == 0 {
            return;
        }
        if self.ridgeline {
            self.render_ridgeline(frame, inner);
            return;
        }
        match self.page {
            ChartPage::Snapshot => self.render_snapshot(frame, inner),
            _ => self.render_trend_page(frame, inner),
        }
    }

    /// The `m` ridgeline mode (contract §3): every numeric level series
    /// as stacked 3D ridges through the raster pipeline; raster-less
    /// builds render the honest fence (the topology `render_no_raster`
    /// precedent — never shipped: the wheel forwards `raster`).
    #[cfg(feature = "raster")]
    fn render_ridgeline(&self, frame: &mut Frame<'_>, area: Rect) {
        if self.trend_failed {
            render_line(
                frame,
                area,
                "▌ trend UNREADABLE — malformed host data",
                CRIMSON,
            );
            return;
        }
        let Some(trend) = &self.trend else {
            render_line(
                frame,
                area,
                "▌ no trend recorded — no campaign bound or no committed tick yet",
                DIM,
            );
            return;
        };
        let ridges = ridgeline_series(trend);
        let scene = crate::scene3d::trend_ridgeline(&ridges);
        if scene.faces.is_empty() {
            render_line(
                frame,
                area,
                "▌ no series carries two points yet — the ridgeline needs history",
                DIM,
            );
            return;
        }
        let mut cam = crate::scene3d::CameraState::default();
        cam.step_ry(2.0);
        cam.step_rx(2.0);
        cam.step_dist(-3.0);
        let grid = hypergraph_rs::raster::rasterize(&scene, &cam.camera(), area.width, area.height);
        crate::raster_bridge::blit_rect(&grid, frame.buffer_mut(), area);
    }

    #[cfg(not(feature = "raster"))]
    fn render_ridgeline(&self, frame: &mut Frame<'_>, area: Rect) {
        render_line(
            frame,
            area,
            "▌ ridgeline needs the raster build (never shipped without it) — press 'm' for charts",
            CRIMSON,
        );
    }

    /// The four trend-chart pages share one absence ladder over the
    /// trend payload.
    fn render_trend_page(&self, frame: &mut Frame<'_>, area: Rect) {
        if self.trend_failed {
            render_line(
                frame,
                area,
                "▌ trend UNREADABLE — malformed host data",
                CRIMSON,
            );
            return;
        }
        let Some(trend) = &self.trend else {
            render_line(
                frame,
                area,
                "▌ no trend recorded — no campaign bound or no committed tick yet",
                DIM,
            );
            return;
        };
        if trend.rows.is_empty() {
            render_line(
                frame,
                area,
                "▌ no trend rows yet — tick_summary writes at the commit boundary; advance a tick",
                DIM,
            );
            return;
        }
        match self.page {
            ChartPage::ImperialRent => render_imperial_rent(frame, area, trend),
            ChartPage::Scissors => render_scissors(frame, area, trend),
            ChartPage::Corrections => render_corrections(frame, area, trend),
            ChartPage::Playability => render_playability(frame, area, trend),
            ChartPage::Snapshot => unreachable!("dispatched by render()"),
        }
    }

    /// The snapshot panel: the `EconomyView` dossier (left column) beside
    /// `national_value` + the matter book (right column) — two columns so
    /// the whole panel fits the play chrome's ~15-row center at the
    /// 100×24 floor geometry (a single column clipped its own tail, the
    /// first frame-content test's finding).
    fn render_snapshot(&self, frame: &mut Frame<'_>, area: Rect) {
        if self.snapshot_failed || self.trend_failed {
            render_line(
                frame,
                area,
                "▌ snapshot UNREADABLE — malformed host data",
                CRIMSON,
            );
            return;
        }
        let [left_area, right_area] =
            Layout::horizontal([Constraint::Percentage(52), Constraint::Min(20)]).areas(area);
        let mut left: Vec<Line<'static>> = Vec::new();
        match &self.snapshot {
            None => left.push(Line::from(Span::styled(
                "▌ no economy dossier — no campaign bound",
                Style::new().fg(DIM),
            ))),
            Some(economy) => snapshot_lines(&mut left, economy),
        }
        frame.render_widget(Paragraph::new(left), left_area);
        let mut right: Vec<Line<'static>> = Vec::new();
        national_value_lines(
            &mut right,
            self.trend.as_ref().and_then(|t| t.national_value.as_ref()),
        );
        matter_book_lines(&mut right, self.snapshot.as_ref());
        frame.render_widget(Paragraph::new(right), right_area);
    }
}

/// The eight numeric level series the ridgeline stacks, front to back
/// (contract §3) — the headline trio + the five playability series.
#[cfg(feature = "raster")]
fn ridgeline_series(trend: &TrendPayload) -> Vec<crate::scene3d::RidgeSeries> {
    let make = |name: &str, f: fn(&TrendRow) -> Option<f64>| crate::scene3d::RidgeSeries {
        name: name.to_string(),
        points: series(&trend.rows, f),
    };
    vec![
        make("imperial_rent", |r| r.imperial_rent),
        make("price_log", |r| r.price_log),
        make("fictitious_log", |r| r.fictitious_log),
        make("crisis_pop_share", |r| r.crisis_pop_share),
        make("bifurcation", |r| r.bifurcation_score_mean),
        make("wage_compression", |r| r.wage_compression_mean),
        make("capital_stock", |r| r.capital_stock_total),
        make("unemployment", |r| r.unemployment_rate_mean),
    ]
}

/// One styled line filling an absence/failure surface.
fn render_line(frame: &mut Frame<'_>, area: Rect, text: &str, color: Color) {
    frame.render_widget(
        Paragraph::new(Line::from(Span::styled(
            text.to_string(),
            Style::new().fg(color),
        ))),
        area,
    );
}

/// Gap-skipping series extraction: only ticks where the selector is
/// `Some` become points — a `None` is a HOLE, never a fabricated zero.
fn series(rows: &[TrendRow], f: impl Fn(&TrendRow) -> Option<f64>) -> Vec<(f64, f64)> {
    rows.iter()
        .filter_map(|row| f(row).map(|v| (row.tick as f64, v)))
        .collect()
}

/// `[min, max]` bounds over one axis of the collected points, padded so a
/// flat or single-point series still spans a visible window.
fn bounds(points: &[&[(f64, f64)]], axis: usize) -> [f64; 2] {
    let mut lo = f64::INFINITY;
    let mut hi = f64::NEG_INFINITY;
    for series in points {
        for point in *series {
            let v = if axis == 0 { point.0 } else { point.1 };
            lo = lo.min(v);
            hi = hi.max(v);
        }
    }
    if !lo.is_finite() || !hi.is_finite() {
        return [0.0, 1.0];
    }
    if (hi - lo).abs() < 1e-9 {
        return [lo - 1.0, hi + 1.0];
    }
    [lo, hi]
}

/// Two-label axis (contract §2: >3 labels mispositions the middle ones,
/// upstream issue 334).
fn axis(title: &'static str, range: [f64; 2]) -> Axis<'static> {
    Axis::default()
        .title(title)
        .style(Style::new().fg(DIM))
        .bounds(range)
        .labels(vec![format!("{:.1}", range[0]), format!("{:.1}", range[1])])
}

fn render_imperial_rent(frame: &mut Frame<'_>, area: Rect, trend: &TrendPayload) {
    let level = series(&trend.rows, |r| r.imperial_rent);
    let delta = series(&trend.rows, |r| r.imperial_rent_delta);
    if level.is_empty() && delta.is_empty() {
        render_line(frame, area, "▌ Φ absent every tick in the window", DIM);
        return;
    }
    let [level_area, delta_area] =
        Layout::vertical([Constraint::Percentage(60), Constraint::Min(3)]).areas(area);
    let x = bounds(&[&level, &delta], 0);
    let datasets = vec![Dataset::default()
        .name("Φ level")
        .marker(Marker::Braille)
        .graph_type(GraphType::Line)
        .style(Style::new().fg(GOLD))
        .data(&level)];
    frame.render_widget(
        Chart::new(datasets)
            .x_axis(axis("tick", x))
            .y_axis(axis("Φ", bounds(&[&level], 1))),
        level_area,
    );
    let delta_sets = vec![Dataset::default()
        .name("Φ delta")
        .marker(Marker::Braille)
        .graph_type(GraphType::Bar)
        .style(Style::new().fg(CRIMSON))
        .data(&delta)];
    frame.render_widget(
        Chart::new(delta_sets)
            .x_axis(axis("tick", x))
            .y_axis(axis("Δ", bounds(&[&delta], 1))),
        delta_area,
    );
}

fn render_scissors(frame: &mut Frame<'_>, area: Rect, trend: &TrendPayload) {
    let price = series(&trend.rows, |r| r.price_log);
    let fictitious = series(&trend.rows, |r| r.fictitious_log);
    if price.is_empty() && fictitious.is_empty() {
        render_line(
            frame,
            area,
            "▌ scissors axes absent every tick in the window",
            DIM,
        );
        return;
    }
    let datasets = vec![
        Dataset::default()
            .name("price_log")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(Style::new().fg(GOLD))
            .data(&price),
        Dataset::default()
            .name("fictitious_log")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(Style::new().fg(CRIMSON))
            .data(&fictitious),
    ];
    frame.render_widget(
        Chart::new(datasets)
            .x_axis(axis("tick", bounds(&[&price, &fictitious], 0)))
            .y_axis(axis("log", bounds(&[&price, &fictitious], 1))),
        area,
    );
}

fn render_corrections(frame: &mut Frame<'_>, area: Rect, trend: &TrendPayload) {
    // Sparkline data is u64-only (contract §2): the cumulative count and
    // its non-negative per-tick increments both fit; a (theoretically)
    // negative wire value clamps to 0 rather than panicking.
    let cumulative: Vec<u64> = trend
        .rows
        .iter()
        .filter_map(|r| r.market_corrections.map(|v| v.max(0) as u64))
        .collect();
    let deltas: Vec<u64> = trend
        .rows
        .iter()
        .filter_map(|r| r.market_corrections_delta.map(|v| v.max(0) as u64))
        .collect();
    if cumulative.is_empty() {
        render_line(
            frame,
            area,
            "▌ correction ledger absent every tick in the window",
            DIM,
        );
        return;
    }
    let [top, bottom] =
        Layout::vertical([Constraint::Percentage(50), Constraint::Min(2)]).areas(area);
    frame.render_widget(
        Sparkline::default()
            .block(Block::new().title("cumulative corrections"))
            .style(Style::new().fg(GOLD))
            .data(&cumulative),
        top,
    );
    frame.render_widget(
        Sparkline::default()
            .block(Block::new().title("snaps per tick"))
            .style(Style::new().fg(CRIMSON))
            .data(&deltas),
        bottom,
    );
}

fn render_playability(frame: &mut Frame<'_>, area: Rect, trend: &TrendPayload) {
    let crisis = series(&trend.rows, |r| r.crisis_pop_share);
    let bifurcation = series(&trend.rows, |r| r.bifurcation_score_mean);
    let compression = series(&trend.rows, |r| r.wage_compression_mean);
    let unemployment = series(&trend.rows, |r| r.unemployment_rate_mean);
    let capital = series(&trend.rows, |r| r.capital_stock_total);
    if [&crisis, &bifurcation, &compression, &unemployment, &capital]
        .iter()
        .all(|s| s.is_empty())
    {
        render_line(
            frame,
            area,
            "▌ playability series absent — they stamp at YEAR boundaries; keep playing",
            DIM,
        );
        return;
    }
    // The four intensive series share one chart; the extensive capital
    // stock gets its own scale (a shared axis would flatten the shares).
    let [left, right] =
        Layout::horizontal([Constraint::Percentage(60), Constraint::Min(10)]).areas(area);
    let intensives = vec![
        Dataset::default()
            .name("crisis")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(Style::new().fg(CRIMSON))
            .data(&crisis),
        Dataset::default()
            .name("bifurcation")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(Style::new().fg(GOLD))
            .data(&bifurcation),
        Dataset::default()
            .name("wage compr")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(Style::new().fg(ROYAL))
            .data(&compression),
        Dataset::default()
            .name("unemploy")
            .marker(Marker::Braille)
            .graph_type(GraphType::Line)
            .style(Style::new().fg(GREEN_DARK))
            .data(&unemployment),
    ];
    frame.render_widget(
        Chart::new(intensives)
            .x_axis(axis(
                "tick",
                bounds(&[&crisis, &bifurcation, &compression, &unemployment], 0),
            ))
            .y_axis(axis(
                "share",
                bounds(&[&crisis, &bifurcation, &compression, &unemployment], 1),
            )),
        left,
    );
    let capital_sets = vec![Dataset::default()
        .name("capital stock")
        .marker(Marker::Braille)
        .graph_type(GraphType::Line)
        .style(Style::new().fg(BONE))
        .data(&capital)];
    frame.render_widget(
        Chart::new(capital_sets)
            .x_axis(axis("tick", bounds(&[&capital], 0)))
            .y_axis(axis("K", bounds(&[&capital], 1))),
        right,
    );
}

/// Bar width for the hand-drawn share bars (the `hud.rs::BAR_WIDTH`
/// idiom, local copy — that const is module-private there on purpose).
const BAR_WIDTH: usize = 8;

/// One `label [####----] value` line — clamp ONLY the glyphs, the label
/// carries the true value (the Gauge veto's discipline). `None` renders
/// the honest absence marker.
fn share_bar(label: &str, value: Option<f64>) -> Line<'static> {
    let Some(v) = value else {
        return Line::from(vec![
            Span::styled(format!("{label:<14}"), Style::new().fg(BONE)),
            Span::styled("—", Style::new().fg(DIM)),
        ]);
    };
    let clamped = v.clamp(0.0, 1.0);
    let filled = (clamped * BAR_WIDTH as f64).round() as usize;
    let color = if v > 1.0 { CRIMSON } else { GOLD };
    Line::from(vec![
        Span::styled(format!("{label:<14}"), Style::new().fg(BONE)),
        Span::styled("[", Style::new().fg(DIM)),
        Span::styled("#".repeat(filled), Style::new().fg(color)),
        Span::styled("-".repeat(BAR_WIDTH - filled), Style::new().fg(DIM)),
        Span::styled("] ", Style::new().fg(DIM)),
        Span::styled(format!("{v:.3}"), Style::new().fg(color)),
    ])
}

/// `label  value-or-—` row.
fn value_row(label: &str, value: Option<f64>) -> Line<'static> {
    let body = match value {
        Some(v) => Span::styled(format!("{v:.3}"), Style::new().fg(GOLD)),
        None => Span::styled("—".to_string(), Style::new().fg(DIM)),
    };
    Line::from(vec![
        Span::styled(format!("{label:<22}"), Style::new().fg(BONE)),
        body,
    ])
}

fn snapshot_lines(lines: &mut Vec<Line<'static>>, economy: &EconomyPayload) {
    let verdict = match economy.labor_aristocracy_verdict {
        Some(true) => Span::styled(
            "LABOR ARISTOCRACY (W > V — revolution in the core impossible)",
            Style::new().fg(CRIMSON),
        ),
        Some(false) => Span::styled("W ≤ V — the theorem's gate is OPEN", Style::new().fg(GOLD)),
        None => Span::styled("verdict unattributed", Style::new().fg(DIM)),
    };
    // wage_balance rides the verdict line — the panel budgets 15 rows to
    // fit the floor geometry's center region, every row is contended.
    let balance = match economy.wage_balance {
        Some(v) => format!("[{v:+.3}] "),
        None => "[—] ".to_string(),
    };
    lines.push(Line::from(vec![
        Span::styled("FT VERDICT ", Style::new().fg(BONE)),
        Span::styled(balance, Style::new().fg(GOLD)),
        verdict,
    ]));
    lines.push(Line::from(Span::styled(
        "Φ TRI-DECOMPOSITION",
        Style::new().fg(BONE),
    )));
    lines.push(value_row(
        "  unequal exchange",
        economy.phi_unequal_exchange,
    ));
    lines.push(value_row("  reproduction", economy.phi_reproduction));
    lines.push(value_row("  domestic", economy.phi_domestic));
    lines.push(value_row("  Φ_III report", economy.phi_iii_report));
    lines.push(value_row("  total", economy.phi_decomposition_total));
    lines.push(Line::from(Span::styled(
        "VOL-III SURPLUS SPLIT",
        Style::new().fg(BONE),
    )));
    lines.push(value_row("  surplus produced", economy.surplus_produced));
    lines.push(value_row(
        "  profit of enterprise",
        economy.profit_of_enterprise,
    ));
    lines.push(value_row("  interest burden", economy.interest_burden));
    lines.push(value_row("  ground rent", economy.ground_rent));
    lines.push(value_row("  taxes on surplus", economy.taxes_on_surplus));
    lines.push(share_bar("  rentier", economy.rentier_share));
    lines.push(share_bar("  financializ.", economy.financialization_share));
}

fn national_value_lines(lines: &mut Vec<Line<'static>>, wire: Option<&NationalValueWire>) {
    lines.push(Line::from(Span::styled(
        "NATIONAL VALUE (hex ledger)",
        Style::new().fg(BONE),
    )));
    // The declared absence the harness pins (contract §1: the c/v/s
    // TIME-SERIES has no producer — tick_summary's total_* columns are
    // written as permanent None; the pin going red = producer landed).
    // Placed HIGH so the floor geometry never clips it off-screen.
    lines.push(Line::from(Span::styled(
        "▌ no c/v/s time-series — no producer yet",
        Style::new().fg(DIM),
    )));
    match wire {
        None => lines.push(Line::from(Span::styled(
            "▌ no hex ledger rows — no hydration ran this campaign",
            Style::new().fg(DIM),
        ))),
        Some(nv) => {
            lines.push(Line::from(Span::styled(
                format!("  as of tick {} (hydration snapshot)", nv.tick),
                Style::new().fg(DIM),
            )));
            lines.push(value_row("  c_sum", Some(nv.c_sum)));
            lines.push(value_row("  v_sum", Some(nv.v_sum)));
            lines.push(value_row("  s_sum", Some(nv.s_sum)));
            lines.push(value_row("  k_sum", Some(nv.k_sum)));
            lines.push(value_row("  s/v", nv.exploitation_rate));
            lines.push(value_row("  s/(c+v)", nv.profit_rate));
        }
    }
}

fn matter_book_lines(lines: &mut Vec<Line<'static>>, economy: Option<&EconomyPayload>) {
    let Some(economy) = economy else {
        return; // the left column already renders the dossier absence line
    };
    lines.push(Line::from(Span::styled(
        "MATTER BOOK",
        Style::new().fg(BONE),
    )));
    lines.push(value_row("  consumption C", economy.total_consumption));
    lines.push(value_row("  biocapacity B", economy.total_biocapacity));
    lines.push(share_bar("  overshoot O", economy.overshoot_ratio));
    lines.push(value_row("  ceiling", economy.biocapacity_ceiling));
    lines.push(value_row("  energy β_J", economy.energy_beta_j));
}

#[cfg(test)]
mod view_state_tests {
    use super::*;

    const TREND: &str = r#"{
        "verified_tick": 3,
        "rows": [
            {"session_id": "00000000-0000-0000-0000-000000000042", "tick": 2,
             "imperial_rent": 10.0, "imperial_rent_delta": null,
             "price_log": 0.1, "price_log_delta": null,
             "fictitious_log": 0.2, "fictitious_log_delta": null,
             "market_corrections": 0, "market_corrections_delta": null,
             "crisis_pop_share": null, "crisis_pop_share_delta": null,
             "bifurcation_score_mean": null, "bifurcation_score_mean_delta": null,
             "wage_compression_mean": null, "wage_compression_mean_delta": null,
             "capital_stock_total": null, "capital_stock_total_delta": null,
             "unemployment_rate_mean": null, "unemployment_rate_mean_delta": null},
            {"session_id": "00000000-0000-0000-0000-000000000042", "tick": 3,
             "imperial_rent": 12.5, "imperial_rent_delta": 2.5,
             "price_log": 0.15, "price_log_delta": 0.05,
             "fictitious_log": 0.05, "fictitious_log_delta": -0.15,
             "market_corrections": 1, "market_corrections_delta": 1,
             "crisis_pop_share": 0.25, "crisis_pop_share_delta": null,
             "bifurcation_score_mean": null, "bifurcation_score_mean_delta": null,
             "wage_compression_mean": null, "wage_compression_mean_delta": null,
             "capital_stock_total": 900.0, "capital_stock_total_delta": null,
             "unemployment_rate_mean": null, "unemployment_rate_mean_delta": null}
        ],
        "national_value": {"tick": 0, "c_sum": 100.0, "v_sum": 50.0, "s_sum": 75.0,
                           "k_sum": 10.0, "exploitation_rate": 1.5, "profit_rate": 0.5}
    }"#;

    #[test]
    fn args_json_is_the_pinned_window() {
        assert_eq!(DashboardView::default().args_json(), r#"{"last_n": 120}"#);
    }

    #[test]
    fn c_cycles_all_five_pages_and_m_toggles_ridgeline() {
        let mut view = DashboardView::default();
        assert_eq!(view.page, ChartPage::ImperialRent);
        let mut seen = vec![view.page];
        for _ in 0..4 {
            assert_eq!(view.handle_key('c'), DashboardAction::Handled);
            seen.push(view.page);
        }
        assert_eq!(seen.len(), ChartPage::COUNT);
        view.handle_key('c');
        assert_eq!(view.page, ChartPage::ImperialRent);
        assert_eq!(view.handle_key('m'), DashboardAction::Handled);
        assert!(view.ridgeline);
        assert_eq!(view.handle_key('q'), DashboardAction::NotHandled);
    }

    #[test]
    fn ingest_parses_rows_and_the_national_value() {
        let mut view = DashboardView::default();
        view.ingest_trend(TREND);
        assert!(!view.trend_failed);
        let trend = view.trend.as_ref().expect("payload");
        assert_eq!(trend.rows.len(), 2);
        assert_eq!(trend.rows[0].imperial_rent_delta, None);
        assert_eq!(trend.rows[1].imperial_rent_delta, Some(2.5));
        assert_eq!(trend.national_value.as_ref().map(|nv| nv.tick), Some(0));
    }

    #[test]
    fn null_is_honest_absence_and_malformed_is_loud_on_both_surfaces() {
        let mut view = DashboardView::default();
        view.ingest_trend("null");
        assert!(view.trend.is_none() && !view.trend_failed);
        view.ingest_trend("{not json");
        assert!(view.trend.is_none() && view.trend_failed);
        view.ingest_dashboard("null");
        assert!(view.snapshot.is_none() && !view.snapshot_failed);
        view.ingest_dashboard("{not json");
        assert!(view.snapshot.is_none() && view.snapshot_failed);
    }

    #[test]
    fn series_gap_skips_none_points_never_fabricates_zero() {
        let mut view = DashboardView::default();
        view.ingest_trend(TREND);
        let rows = &view.trend.as_ref().expect("payload").rows;
        let crisis = series(rows, |r| r.crisis_pop_share);
        assert_eq!(crisis, vec![(3.0, 0.25)]); // tick 2's None is a HOLE
    }

    #[test]
    fn bounds_pads_flat_series_into_a_visible_window() {
        let flat = vec![(1.0, 5.0), (2.0, 5.0)];
        assert_eq!(bounds(&[&flat], 1), [4.0, 6.0]);
        let empty: Vec<(f64, f64)> = Vec::new();
        assert_eq!(bounds(&[&empty], 1), [0.0, 1.0]);
    }
}
