use babylon_tui::{app::App, config::AppConfig, host::Host};
use ratatui::{backend::TestBackend, Terminal};

struct FakeHost;
impl Host for FakeHost {
    fn lobby_catalog_json(&self) -> String {
        // The FULL row shape RustClientHost emits (host.py) — LobbyRow is
        // deliberately strict, so a fake omitting fields renders an empty
        // catalog (the M0 three-field fake did exactly that, silently).
        r#"[{"campaign_id":"c1","name":"Wayne County","tick":0,
            "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}]"#
            .to_string()
    }
}

#[test]
fn hello_frame_shows_campaign() {
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,"headless":true}"#,
    )
    .unwrap();
    let mut app = App::new(cfg, FakeHost);
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();
    app.render_frame(&mut terminal).unwrap();
    let buffer = terminal.backend().buffer().clone();
    insta::assert_snapshot!(format!("{:?}", buffer));
}
