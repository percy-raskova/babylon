//! P26 U6 phase 2 — trade dossier reachability in the Rust/Ratatui client
//! (contract: `specs/103-trade-surfaces/u6-archive-trade-surfaces-
//! contracts.md` Contract 3).
//!
//! **No dedicated `trade_view_json` Host method exists** (a deliberate
//! choice, recorded here per Contract 3's own "a minimal reachable
//! rendering... is acceptable" allowance): `subject_view_json`/
//! `read_page_json`/`known_subjects_json` are already generic over ANY
//! `"<kind>/<id>"` subject — `WikiView` (`wiki.rs`), `render_peek`
//! (`views/peek.rs`), and `PaletteView` (`views/palette.rs`) walk whatever
//! JSON/Markdown the host returns with no kind allowlist anywhere in this
//! crate (verified by reading `router.rs`, `wiki_render.rs`, and
//! `views/peek.rs` — none of the three names a closed kind set). The
//! Python-side seam (`babylon.game.session.GameSession.read_page`/
//! `known_subjects`/`subject_view`) already special-cases `trade/*`
//! (`babylon.tui.trade_dossier.render_trade_page`), so these three
//! generic Rust surfaces reach trade pages with ZERO new Rust code — this
//! file pins that claim directly rather than asserting it in prose only,
//! using fixture pages/JSON shaped exactly like the real Python renderer's
//! output (`tests/unit/tui/test_trade_dossier.py`'s own fixtures).

use std::collections::BTreeSet;

use babylon_tui::host::Host;
use babylon_tui::layout_registry::LayoutRegistry;
use babylon_tui::router::BabylonTarget;
use babylon_tui::views::palette::PaletteView;
use babylon_tui::views::peek::render_peek;
use babylon_tui::views::wiki::WikiView;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::crossterm::event::KeyCode;
use ratatui::Terminal;

/// The national overview page, shaped exactly like
/// `babylon.tui.trade_dossier.render_trade_page` over
/// `project_trade_overview`'s output (verified against a live interpreter
/// run of the real renderer; see this crate's own `wiki_view.rs` test for
/// the "hand-shaped fixture, not the real renderer" convention this file
/// follows — Rust cannot import the Python module under test).
const OVERVIEW_PAGE: &str = "---\n\
id: trade/overview\n\
name: Trade \u{2014} overview\n\
verified_tick: 5\n\
staleness: verified as of tick 5 \u{2014} always regenerable, never authoritative\n\
---\n\
\n\
# trade/overview \u{2014} National Trade Overview\n\
\n\
```{statblock} trade/overview\n\
phi_year_inflow: 150000000.000000\n\
phi_week_slice: 2884615.384615\n\
```\n\
\n\
## Per-bloc breakdown (\u{3a6} DESC)\n\
\n\
| bloc | phi_year_inflow |\n\
| --- | --- |\n\
| [[trade/canada]] | 100000000.000000 |\n\
| [[trade/mexico]] | 50000000.000000 |\n";

const CANADA_PAGE: &str = "---\n\
id: trade/canada\n\
name: Trade \u{2014} canada\n\
verified_tick: 5\n\
staleness: verified as of tick 5 \u{2014} always regenerable, never authoritative\n\
---\n\
\n\
# trade/canada \u{2014} Bloc Dossier \u{2014} canada\n\
\n\
```{statblock} trade/canada\n\
phi_year_inflow: 100000000.000000\n\
phi_week_slice: 1923076.923077\n\
```\n\
\n\
## Top county exposure\n\
\n\
| county_fips | weight |\n\
| --- | --- |\n\
| 26163 | 1.000000 |\n\
\n\
Back to [[trade/overview]].\n";

/// The real `TradeBlocView` JSON shape (`kind="trade"`, identity field
/// `node_id` — matching `tests/unit/tui/test_peek.py`'s
/// `TestTradeBlocViewRealKind` fixture on the Python side).
const CANADA_SUBJECT_VIEW_JSON: &str = r#"{"kind":"trade","node_id":"canada","verified_tick":5,
    "phi_year_inflow":100000000.0,"phi_week_slice":1923076.923077,
    "bilateral_trade_value":null,"bilateral_trade_tons":null,"erdi_ratio":null,
    "exposure_top":[{"county_fips":"26163","weight":1.0}],
    "last_tick_flow":1923076.923077,"breakdown":null}"#;

const KNOWN_SUBJECTS_JSON: &str = r#"["trade/canada", "trade/mexico", "trade/overview"]"#;

/// A fake host serving the two trade pages above plus the known-subjects
/// set and `trade/canada`'s live view — mirrors `wiki_view.rs`'s own
/// `FakeHost` shape (override only what the test under exercise needs; the
/// `Host` trait's own defaults cover the rest, honest-absence).
struct FakeHost;

impl Host for FakeHost {
    fn lobby_catalog_json(&self) -> String {
        "[]".to_string()
    }

    fn read_page_json(&self, subject: &str) -> String {
        let page = match subject {
            "trade/overview" => OVERVIEW_PAGE,
            "trade/canada" => CANADA_PAGE,
            _ => return "null".to_string(),
        };
        serde_json::to_string(page).expect("fixture page encodes")
    }

    fn known_subjects_json(&self) -> String {
        KNOWN_SUBJECTS_JSON.to_string()
    }

    fn subject_view_json(&self, subject: &str) -> String {
        match subject {
            "trade/canada" => CANADA_SUBJECT_VIEW_JSON.to_string(),
            _ => "null".to_string(),
        }
    }
}

fn buffer_text(buf: &Buffer) -> String {
    let area = buf.area;
    (0..area.height)
        .map(|y| {
            (0..area.width)
                .map(|x| {
                    buf.cell((area.x + x, area.y + y))
                        .map(|c| c.symbol())
                        .unwrap_or(" ")
                })
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn render_wiki(view: &mut WikiView) -> Buffer {
    let backend = TestBackend::new(70, 40);
    let mut terminal = Terminal::new(backend).unwrap();
    let known: BTreeSet<String> = BTreeSet::new();
    let mut registry = LayoutRegistry::new();
    terminal
        .draw(|frame| {
            let area = frame.area();
            view.render(frame, area, &mut registry, &known);
        })
        .unwrap();
    terminal.backend().buffer().clone()
}

#[test]
fn wiki_view_opens_the_trade_overview_page_via_kind_slash_id() {
    let mut view = WikiView::new();
    view.open(
        &BabylonTarget::Kind {
            kind: "trade".to_string(),
            id: "overview".to_string(),
        },
        &FakeHost,
    );
    assert_eq!(view.current.as_deref(), Some("trade/overview"));

    let text = buffer_text(&render_wiki(&mut view));
    assert!(
        text.contains("National Trade Overview"),
        "expected heading in:\n{text}"
    );
    assert!(
        text.contains("150000000.000000"),
        "expected the national Phi total in:\n{text}"
    );
    assert!(
        text.contains("phi_week_slice"),
        "expected the weekly slice row in:\n{text}"
    );
}

#[test]
fn wiki_view_opens_the_canada_bloc_page_with_its_own_numbers() {
    let mut view = WikiView::new();
    view.open(
        &BabylonTarget::Kind {
            kind: "trade".to_string(),
            id: "canada".to_string(),
        },
        &FakeHost,
    );
    assert_eq!(view.current.as_deref(), Some("trade/canada"));

    let text = buffer_text(&render_wiki(&mut view));
    assert!(
        text.contains("Bloc Dossier"),
        "expected the bloc-dossier heading in:\n{text}"
    );
    assert!(
        text.contains("100000000.000000"),
        "expected canada's own Phi inflow in:\n{text}"
    );
    assert!(
        text.contains("26163"),
        "expected the top county exposure row in:\n{text}"
    );
}

#[test]
fn wiki_view_reports_honest_absence_for_an_unwired_trade_subject() {
    // A campaign with no trade wiring at all serves "null" from
    // read_page_json for EVERY trade/* id (session.py's own contract) —
    // this host stands in for that unwired campaign directly.
    struct UnwiredHost;
    impl Host for UnwiredHost {
        fn lobby_catalog_json(&self) -> String {
            "[]".to_string()
        }
    }

    let mut view = WikiView::new();
    view.open(
        &BabylonTarget::Kind {
            kind: "trade".to_string(),
            id: "overview".to_string(),
        },
        &UnwiredHost,
    );
    let text = buffer_text(&render_wiki(&mut view));
    assert!(
        text.contains("No page recorded for this subject."),
        "expected the client's existing absence page, not a fabricated \
         dossier, in:\n{text}"
    );
}

#[test]
fn peek_renders_the_real_trade_bloc_view_shape_at_page_transclusion_depth() {
    let host = FakeHost;
    let subject_view_json = host.subject_view_json("trade/canada");

    let backend = TestBackend::new(60, 12);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| {
            let area = frame.area();
            render_peek(frame, area, &subject_view_json, 3);
        })
        .unwrap();
    let text = buffer_text(&terminal.backend().buffer().clone());

    // The header degrades to the bare kind ("trade @ T0005") — TradeBlocView
    // has no trade_id/trade_fips identity field (its own field is node_id),
    // mirroring peek.py's own identity-convention degrade
    // (tests/unit/tui/test_peek.py::TestTradeBlocViewRealKind).
    assert!(
        text.contains("trade @ T0005"),
        "expected header in:\n{text}"
    );
    assert!(
        text.contains("phi_year_inflow"),
        "expected a real stat row in:\n{text}"
    );
    assert!(
        text.contains("100000000.000000"),
        "expected canada's real Phi number in:\n{text}"
    );
}

#[test]
fn palette_discovers_both_trade_subjects_from_known_subjects_json() {
    let mut view = PaletteView::open(KNOWN_SUBJECTS_JSON);
    for c in "trade".chars() {
        assert!(view.handle_key(KeyCode::Char(c)).is_none());
    }
    assert!(view.matches.iter().any(|m| m == "trade/overview"));
    assert!(view.matches.iter().any(|m| m == "trade/canada"));
}
