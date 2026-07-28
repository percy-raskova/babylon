//! The 100×30 declared-floor guard (Wave 1 contract §1, Director ruling 1).
//!
//! Below the floor the client renders ONLY the too-small notice — the recon
//! arithmetic of record shows the 11-line verb plate clips three Article-V
//! verbs at 80×24 under the tutorial strip's 40% clamp, and the ruled fix
//! is the floor, not plate pagination. The guard swallows every key except
//! the quit set (no hidden state mutation against an invisible UI) and
//! lifts with all state intact on the next at-floor render.

use babylon_tui::app::App;
use babylon_tui::config::AppConfig;
use babylon_tui::host::Host;
use ratatui::backend::TestBackend;
use ratatui::Terminal;

/// Trait defaults everywhere: the guard renders before any host data
/// matters, so honest-absence replies are all these tests need.
struct FakeHost;

impl Host for FakeHost {
    fn lobby_catalog_json(&self) -> String {
        r#"[{"campaign_id":"c1","name":"campaign-a3f9b2c1d0e5","codename":"Wayne County","tick":3,
            "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}]"#
            .to_string()
    }
}

fn test_app() -> App<FakeHost> {
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"","campaign_name":"Lobby","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,
            "headless":true}"#,
    )
    .expect("valid config");
    App::new(cfg, FakeHost)
}

fn buffer_text(terminal: &Terminal<TestBackend>) -> String {
    format!("{:?}", terminal.backend().buffer())
}

fn render(app: &mut App<FakeHost>, terminal: &mut Terminal<TestBackend>) {
    app.render_frame(terminal).expect("render");
}

#[test]
fn below_floor_renders_only_the_too_small_notice() {
    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(80, 24)).expect("backend");
    render(&mut app, &mut terminal);
    let frame = buffer_text(&terminal);
    assert!(
        frame.contains("terminal too small"),
        "the notice must name the condition:\n{frame}"
    );
    assert!(
        frame.contains("100x30") && frame.contains("80x24"),
        "the notice must name the floor AND the current size:\n{frame}"
    );
    assert!(
        !frame.contains("CAMPAIGNS"),
        "the lobby must NOT render under the guard:\n{frame}"
    );
}

#[test]
fn at_floor_renders_the_normal_surface() {
    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");
    render(&mut app, &mut terminal);
    let frame = buffer_text(&terminal);
    assert!(
        frame.contains("CAMPAIGNS"),
        "at exactly the floor the lobby renders normally:\n{frame}"
    );
    assert!(
        !frame.contains("terminal too small"),
        "no notice at the floor:\n{frame}"
    );
}

#[test]
fn guard_swallows_keys_except_the_quit_set_and_lifts_on_resize() {
    let mut app = test_app();
    let mut small = Terminal::new(TestBackend::new(80, 24)).expect("backend");
    render(&mut app, &mut small);
    // Swallowed: 'n' would dispatch NewCampaign and stamp a "status: "
    // line if it reached the lobby — under the guard it must not.
    assert!(!app.handle_key(
        ratatui::crossterm::event::KeyCode::Down,
        ratatui::crossterm::event::KeyModifiers::NONE
    ));
    assert!(!app.handle_key(
        ratatui::crossterm::event::KeyCode::Char('n'),
        ratatui::crossterm::event::KeyModifiers::NONE
    ));
    // The guard lifts on an at-floor render with state intact — and the
    // swallowed 'n' left NO status line behind.
    let mut big = Terminal::new(TestBackend::new(100, 30)).expect("backend");
    render(&mut app, &mut big);
    let frame = buffer_text(&big);
    assert!(frame.contains("CAMPAIGNS"), "guard did not lift:\n{frame}");
    assert!(
        !frame.contains("status:"),
        "'n' was applied under the guard instead of swallowed:\n{frame}"
    );
    // Quit still works from under the guard.
    render(&mut app, &mut small);
    assert!(app.handle_key(
        ratatui::crossterm::event::KeyCode::Char('q'),
        ratatui::crossterm::event::KeyModifiers::NONE
    ));
}
