//! Scripted-flow integration tests for the M1 app shell (plan Task 19):
//! lobby → campaign briefing → link navigation → back → quit, driven
//! entirely through the same key/mouse handlers the interactive loop and
//! the headless script replay use.

use babylon_tui::app::{key_event_from_name, App};
use babylon_tui::config::AppConfig;
use babylon_tui::host::Host;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::crossterm::event::{KeyModifiers, MouseButton, MouseEvent, MouseEventKind};
use ratatui::Terminal;

struct FakeHost;

impl Host for FakeHost {
    fn lobby_catalog_json(&self) -> String {
        r#"[{"campaign_id":"c1","name":"campaign-a3f9b2c1d0e5","codename":"Wayne County","tick":3,
            "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}]"#
            .to_string()
    }

    fn read_page_json(&self, subject: &str) -> String {
        let page = match subject {
            "briefing/c1" => "# Briefing\n\nSee [[Detroit]].",
            "Detroit" => "# Detroit\n\nThe motor city dossier.",
            _ => return "null".to_string(),
        };
        serde_json::to_string(page).expect("fixture page encodes")
    }

    fn known_subjects_json(&self) -> String {
        r#"["Detroit"]"#.to_string()
    }

    fn load_campaign(&self, campaign_id: &str) -> String {
        format!(r#"{{"ok": true, "campaign_id": "{campaign_id}"}}"#)
    }
}

fn test_app() -> App<FakeHost> {
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,"headless":true}"#,
    )
    .expect("fixture config parses");
    App::new(cfg, FakeHost)
}

fn render(app: &mut App<FakeHost>, terminal: &mut Terminal<TestBackend>) -> Buffer {
    app.render_frame(terminal).expect("frame renders");
    terminal.backend().buffer().clone()
}

fn buffer_text(buffer: &Buffer) -> String {
    let area = buffer.area;
    (0..area.height)
        .map(|row| {
            (0..area.width)
                .map(|col| buffer[(col, row)].symbol())
                .collect::<String>()
                .trim_end()
                .to_string()
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn press(app: &mut App<FakeHost>, name: &str) -> bool {
    let (code, modifiers) = key_event_from_name(name).expect("known key name");
    app.handle_key(code, modifiers)
}

#[test]
fn lobby_to_briefing_to_back_to_quit() {
    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(80, 24)).expect("backend");

    // Frame 1: the lobby root.
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Wayne County"),
        "lobby row missing:\n{frame}"
    );

    // Enter loads the selected campaign → the briefing page (Textual
    // parity: briefing/<campaign_id> is the first page after selection).
    assert!(!press(&mut app, "enter"), "enter must not quit");
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Briefing"),
        "briefing page missing:\n{frame}"
    );
    assert!(
        frame.contains("Detroit"),
        "briefing wikilink missing:\n{frame}"
    );

    // q pops back to the lobby (stack depth 2 → 1), not quit.
    assert!(!press(&mut app, "q"), "q above the root pops, not quits");
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(frame.contains("CAMPAIGNS"), "lobby not restored:\n{frame}");

    // q at the root quits.
    assert!(press(&mut app, "q"), "q at the lobby root quits");

    // Host-call order is the seam contract: catalog once (root build),
    // the campaign BIND (the composition-root verb), known-subjects after
    // the bind, the M2 nav restore, the briefing page read + backlinks,
    // the recorded-[render] read at chrome build (Task 35 §7 — once per
    // bind, never a re-probe), then the chrome's five post-bind pulls
    // (contract §§1-5), and the nav save on leaving the campaign (q →
    // lobby).
    assert_eq!(
        app.host_calls(),
        vec![
            "lobby_catalog_json".to_string(),
            "load_campaign".to_string(),
            "known_subjects_json".to_string(),
            "nav_state_json".to_string(),
            "read_page_json".to_string(),
            "backlinks_json".to_string(),
            "render_config_json".to_string(),
            "endgame_status_json".to_string(),
            "pacing_state_json".to_string(),
            "verb_plate_view_json".to_string(),
            "chronicle_rail_json".to_string(),
            "watchlist_json".to_string(),
            "save_nav_state".to_string(),
        ]
    );
}

#[test]
fn clicking_a_wikilink_navigates_to_its_page() {
    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(80, 24)).expect("backend");

    render(&mut app, &mut terminal);
    press(&mut app, "enter");
    let frame = buffer_text(&render(&mut app, &mut terminal));

    // Find "Detroit" on the rendered briefing page and click it. Hunting
    // the coordinates from the frame keeps the test honest about where the
    // registry actually placed the hit rect.
    let (row, col) = frame
        .lines()
        .enumerate()
        .find_map(|(row, line)| line.find("Detroit").map(|col| (row as u16, col as u16)))
        .expect("briefing page shows the Detroit link");
    let quit = app.handle_mouse(MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: col,
        row,
        modifiers: KeyModifiers::NONE,
    });
    assert!(!quit);

    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("motor city dossier"),
        "click did not open the Detroit page:\n{frame}"
    );

    // Two page reads crossed the seam: briefing, then Detroit.
    let reads = app
        .host_calls()
        .iter()
        .filter(|c| c.as_str() == "read_page_json")
        .count();
    assert_eq!(reads, 2);
}

#[test]
fn palette_opens_filters_and_navigates() {
    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(80, 24)).expect("backend");

    render(&mut app, &mut terminal);
    press(&mut app, "enter"); // into the campaign
    press(&mut app, "/"); // palette over the wiki
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Detroit"),
        "palette lists subjects:\n{frame}"
    );

    press(&mut app, "enter"); // accept the selected match
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("motor city dossier"),
        "palette enter did not navigate:\n{frame}"
    );
}
