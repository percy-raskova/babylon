//! Frame-content tests for `babylon_tui::views::dashboard` (M6 contract
//! §2/§4 — the RULED golden split: 2D charts use explicit substring/field
//! asserts over `buffer_text` + style lookups, exactly like
//! `hud_view.rs`/`topology_2d.rs`; `insta` cannot assert color).

use babylon_tui::theme::{CRIMSON, DIM, GOLD};
use babylon_tui::views::dashboard::DashboardView;
use ratatui::backend::TestBackend;
use ratatui::style::Color;
use ratatui::Terminal;

fn draw(view: &mut DashboardView, width: u16, height: u16) -> Terminal<TestBackend> {
    let backend = TestBackend::new(width, height);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| view.render(frame, frame.area()))
        .unwrap();
    terminal
}

fn buffer_text(terminal: &Terminal<TestBackend>) -> String {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    (area.top()..area.bottom())
        .map(|y| {
            (area.left()..area.right())
                .map(|x| buffer[(x, y)].symbol())
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn any_cell_colored(terminal: &Terminal<TestBackend>, color: Color) -> bool {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    (area.top()..area.bottom()).any(|y| {
        (area.left()..area.right()).any(|x| {
            let cell = &buffer[(x, y)];
            cell.fg == color || cell.bg == color
        })
    })
}

/// A 3-tick trend with every headline series present (deltas NULL at the
/// first row — the LAG contract) + a national_value snapshot.
fn trend_envelope() -> String {
    let row = |tick: u64, phi: f64, delta: &str, price: f64, fict: f64, corr: i64| {
        format!(
            r#"{{"session_id": "00000000-0000-0000-0000-000000000042", "tick": {tick},
            "imperial_rent": {phi}, "imperial_rent_delta": {delta},
            "price_log": {price}, "price_log_delta": null,
            "fictitious_log": {fict}, "fictitious_log_delta": null,
            "market_corrections": {corr}, "market_corrections_delta": null,
            "crisis_pop_share": 0.25, "crisis_pop_share_delta": null,
            "bifurcation_score_mean": 0.4, "bifurcation_score_mean_delta": null,
            "wage_compression_mean": 0.6, "wage_compression_mean_delta": null,
            "capital_stock_total": 900.0, "capital_stock_total_delta": null,
            "unemployment_rate_mean": 0.07, "unemployment_rate_mean_delta": null}}"#
        )
    };
    format!(
        r#"{{"verified_tick": 3, "rows": [{}, {}, {}],
        "national_value": {{"tick": 0, "c_sum": 100.0, "v_sum": 50.0, "s_sum": 75.0,
                            "k_sum": 10.0, "exploitation_rate": 1.5, "profit_rate": 0.5}}}}"#,
        row(1, 10.0, "null", 0.10, 0.20, 0),
        row(2, 11.0, "1.0", 0.12, 0.15, 0),
        row(3, 12.5, "1.5", 0.15, 0.05, 1),
    )
}

/// An EconomyView dump with the FT verdict TRUE and an overshoot > 1.
const ECONOMY: &str = r#"{
    "kind": "economy", "economy_id": "USA", "verified_tick": 3,
    "wage_balance": 0.42, "labor_aristocracy_verdict": true,
    "class_phi_readings": null,
    "phi_unequal_exchange": null, "phi_reproduction": null,
    "phi_domestic": null, "phi_iii_report": null, "phi_decomposition_total": null,
    "surplus_produced": 500.0, "profit_of_enterprise": 200.0,
    "interest_burden": 100.0, "ground_rent": 50.0, "taxes_on_surplus": 25.0,
    "rentier_share": 1.35, "financialization_share": 0.3,
    "total_consumption": 1200.0, "total_biocapacity": 800.0,
    "overshoot_ratio": 1.5, "biocapacity_ceiling": 900.0, "energy_beta_j": 0.8
}"#;

#[test]
fn imperial_rent_page_renders_braille_series() {
    let mut view = DashboardView::default();
    view.ingest_trend(&trend_envelope());
    let terminal = draw(&mut view, 90, 28);
    let text = buffer_text(&terminal);
    assert!(text.contains("imperial rent [1/5]"), "{text}");
    assert!(
        text.chars().any(|c| ('\u{2800}'..='\u{28FF}').contains(&c)),
        "no braille chart content:\n{text}"
    );
    assert!(any_cell_colored(&terminal, GOLD), "Φ level series not gold");
}

#[test]
fn scissors_page_renders_both_named_datasets() {
    let mut view = DashboardView::default();
    view.ingest_trend(&trend_envelope());
    view.handle_key('c');
    let terminal = draw(&mut view, 90, 28);
    let text = buffer_text(&terminal);
    assert!(text.contains("price⟷value scissors [2/5]"), "{text}");
    assert!(
        any_cell_colored(&terminal, GOLD),
        "price_log series not gold"
    );
    assert!(
        any_cell_colored(&terminal, CRIMSON),
        "fictitious_log series not crimson"
    );
}

#[test]
fn snapshot_page_renders_verdict_bars_and_the_declared_absence() {
    let mut view = DashboardView::default();
    view.ingest_trend(&trend_envelope());
    view.ingest_dashboard(ECONOMY);
    for _ in 0..4 {
        view.handle_key('c');
    }
    let terminal = draw(&mut view, 100, 32);
    let text = buffer_text(&terminal);
    assert!(text.contains("value snapshot [5/5]"), "{text}");
    assert!(
        text.contains("LABOR ARISTOCRACY"),
        "FT verdict missing:\n{text}"
    );
    // The Φ tri-decomposition is honestly all-None today.
    assert!(text.contains("unequal exchange"), "{text}");
    // Unbounded shares use the bar idiom with the TRUE value in the label
    // (the Gauge veto): rentier 1.35 and overshoot 1.5 both exceed 1.
    assert!(
        text.contains("1.350"),
        "rentier true value missing:\n{text}"
    );
    assert!(
        text.contains("1.500"),
        "overshoot true value missing:\n{text}"
    );
    // national_value block with its staleness disclosure.
    assert!(text.contains("as of tick 0"), "{text}");
    assert!(text.contains("s/(c+v)"), "{text}");
    // The harness-pinned declared absence (contract §1).
    assert!(
        text.contains("no c/v/s time-series"),
        "declared-absence line missing:\n{text}"
    );
}

#[test]
fn absent_trend_renders_the_honest_line_and_unreadable_is_loud() {
    let mut view = DashboardView::default();
    view.ingest_trend("null");
    let terminal = draw(&mut view, 90, 12);
    assert!(
        buffer_text(&terminal).contains("no trend recorded"),
        "absence line missing"
    );
    view.ingest_trend("{not json");
    let terminal = draw(&mut view, 90, 12);
    let text = buffer_text(&terminal);
    assert!(text.contains("trend UNREADABLE"), "{text}");
    assert!(any_cell_colored(&terminal, CRIMSON));
}

#[test]
fn playability_page_names_the_year_boundary_when_series_are_absent() {
    let mut view = DashboardView::default();
    // Rows exist but every playability series is null (pre-first-boundary).
    let envelope = trend_envelope()
        .replace("\"crisis_pop_share\": 0.25", "\"crisis_pop_share\": null")
        .replace(
            "\"bifurcation_score_mean\": 0.4",
            "\"bifurcation_score_mean\": null",
        )
        .replace(
            "\"wage_compression_mean\": 0.6",
            "\"wage_compression_mean\": null",
        )
        .replace(
            "\"capital_stock_total\": 900.0",
            "\"capital_stock_total\": null",
        )
        .replace(
            "\"unemployment_rate_mean\": 0.07",
            "\"unemployment_rate_mean\": null",
        );
    view.ingest_trend(&envelope);
    for _ in 0..3 {
        view.handle_key('c');
    }
    let terminal = draw(&mut view, 90, 20);
    let text = buffer_text(&terminal);
    assert!(text.contains("playability series [4/5]"), "{text}");
    assert!(
        text.contains("YEAR boundaries"),
        "the absence line must name the stamping cadence:\n{text}"
    );
    let _ = DIM; // color asserted implicitly via the absence line style elsewhere
}
