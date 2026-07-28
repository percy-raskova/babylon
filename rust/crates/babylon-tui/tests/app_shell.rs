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
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");

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
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");

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
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");

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

#[test]
fn shift_tab_reverse_cycles_focus_and_focused_region_gets_crimson_border() {
    use ratatui::style::Color;

    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");
    render(&mut app, &mut terminal);
    press(&mut app, "enter"); // bind the campaign -> chrome exists

    // Wave 1 §4: BackTab reverse-cycles Center -> Watchlist (Tab's mirror).
    press(&mut app, "backtab");
    let buffer = render(&mut app, &mut terminal);
    let frame = buffer_text(&buffer);
    assert!(
        frame.contains("pinned) ●"),
        "backtab must focus the watchlist rail:\n{frame}"
    );
    // The focused rail's border is CRIMSON (the peek-overlay precedent);
    // the watchlist Block's top-left border cell sits at (0, 3) — first
    // row under the 3-row HUD.
    assert_eq!(
        buffer[(0u16, 3u16)].fg,
        Color::Rgb(220, 20, 60),
        "focused watchlist border must be crimson"
    );

    // And one more BackTab reaches the chronicle; its border cell is the
    // rail's own top-left at x = 100 - 24 = 76.
    press(&mut app, "backtab");
    let buffer = render(&mut app, &mut terminal);
    assert_eq!(
        buffer[(76u16, 3u16)].fg,
        Color::Rgb(220, 20, 60),
        "focused chronicle border must be crimson"
    );
    // The de-focused watchlist border returns to the default color.
    assert_ne!(
        buffer[(0u16, 3u16)].fg,
        Color::Rgb(220, 20, 60),
        "unfocused watchlist border must not stay crimson"
    );
}

#[test]
fn keybar_is_context_aware_and_cells_dispatch_on_click() {
    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");

    // Lobby surface: its own hints.
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Enter load") && frame.contains("n new"),
        "lobby keybar hints missing:\n{frame}"
    );

    // Chrome wiki surface: pane/focus hints replace the lobby's.
    press(&mut app, "enter");
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Tab focus") && frame.contains("K peek"),
        "wiki keybar hints missing:\n{frame}"
    );
    assert!(
        !frame.contains("n new"),
        "lobby hints must not leak into the chrome keybar:\n{frame}"
    );

    // Click the "Tab focus" cell on the keybar row (last row): the click
    // routes through handle_key, so focus cycles to the chronicle rail.
    let keybar_row = 29u16;
    let col = frame
        .lines()
        .nth(keybar_row as usize)
        .and_then(|line| line.find("Tab"))
        .expect("keybar shows the Tab cell") as u16;
    app.handle_mouse(MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: col,
        row: keybar_row,
        modifiers: KeyModifiers::NONE,
    });
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("CHRONICLE ●"),
        "clicking the Tab cell must cycle focus:\n{frame}"
    );
    // And the keybar itself now shows the rail surface's hints.
    assert!(
        frame.contains("Esc center"),
        "rail-focused keybar hints missing:\n{frame}"
    );
}

#[test]
fn help_overlay_opens_mode_scoped_and_closes_clean() {
    let mut app = test_app();
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");
    render(&mut app, &mut terminal);
    press(&mut app, "enter"); // into the campaign (wiki pane)

    press(&mut app, "?");
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(frame.contains("BINDINGS"), "help plate missing:\n{frame}");
    // Mode-scoped: the wiki section leads, marked as the active surface.
    assert!(
        frame.contains("WIKI PANE ◄ you are here"),
        "active-surface section must lead:\n{frame}"
    );
    // Modal: navigation keys must not leak to the wiki underneath.
    press(&mut app, "[");
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("BINDINGS"),
        "'[' must scroll/no-op inside help, never navigate under it:\n{frame}"
    );

    // Esc closes and the wiki is back untouched.
    press(&mut app, "esc");
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        !frame.contains("BINDINGS"),
        "help must close on Esc:\n{frame}"
    );
    assert!(frame.contains("Briefing"), "wiki restored:\n{frame}");
}

#[test]
fn wheel_scrolls_the_wiki_and_rail_clicks_focus_then_open() {
    struct MouseHost;
    impl Host for MouseHost {
        fn lobby_catalog_json(&self) -> String {
            r#"[{"campaign_id":"c1","name":"campaign-a3f9b2c1d0e5","codename":"Wayne County","tick":3,
                "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}]"#
                .to_string()
        }
        fn read_page_json(&self, subject: &str) -> String {
            let page = match subject {
                "briefing/c1" => {
                    // Long enough to scroll at 100x30 chrome (center ~14 rows).
                    let mut body = String::from("# Briefing\n\n");
                    for i in 0..60 {
                        body.push_str(&format!("line {i}\n\n"));
                    }
                    body
                }
                "Detroit" => "# Detroit\n\nThe motor city dossier.".to_string(),
                _ => return "null".to_string(),
            };
            serde_json::to_string(&page).expect("fixture page encodes")
        }
        fn known_subjects_json(&self) -> String {
            r#"["Detroit"]"#.to_string()
        }
        fn load_campaign(&self, campaign_id: &str) -> String {
            format!(r#"{{"ok": true, "campaign_id": "{campaign_id}"}}"#)
        }
        fn chronicle_rail_json(&self) -> String {
            r#"{"rows":[
                {"kind":"header","text":"T0003","subject":null,"tick":3,"severity":null,"actor":null},
                {"kind":"event","text":"Detroit stirs","subject":"Detroit","tick":3,"severity":"informational","actor":null}
            ],"autopause_line":null}"#
                .to_string()
        }
    }

    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,"headless":true}"#,
    )
    .expect("fixture config parses");
    let mut app = App::new(cfg, MouseHost);
    let mut terminal = Terminal::new(TestBackend::new(100, 30)).expect("backend");
    app.render_frame(&mut terminal).expect("render");
    {
        let (code, modifiers) = key_event_from_name("enter").expect("known key name");
        app.handle_key(code, modifiers);
    }
    let frame_before = {
        app.render_frame(&mut terminal).expect("render");
        let area = terminal.backend().buffer().area;
        let buf = terminal.backend().buffer().clone();
        (0..area.height)
            .map(|row| {
                (0..area.width)
                    .map(|col| buf[(col, row)].symbol())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n")
    };
    assert!(
        frame_before.contains("line 0"),
        "long page starts at the top"
    );

    // Wheel down over the CENTER region (col 50 is inside it) scrolls.
    app.handle_mouse(MouseEvent {
        kind: MouseEventKind::ScrollDown,
        column: 50,
        row: 10,
        modifiers: KeyModifiers::NONE,
    });
    app.render_frame(&mut terminal).expect("render");
    let buf = terminal.backend().buffer().clone();
    let area = buf.area;
    let frame_after = (0..area.height)
        .map(|row| {
            (0..area.width)
                .map(|col| buf[(col, row)].symbol())
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("\n");
    assert!(
        !frame_after.contains("line 0 "),
        "wheel over the center must scroll the wiki:\n{frame_after}"
    );

    // Click the chronicle's navigable row: first click focuses + selects…
    let row_y = frame_after
        .lines()
        .position(|line| line.contains("Detroit stirs"))
        .expect("chronicle row visible") as u16;
    let click = MouseEvent {
        kind: MouseEventKind::Down(MouseButton::Left),
        column: 90,
        row: row_y,
        modifiers: KeyModifiers::NONE,
    };
    app.handle_mouse(click);
    app.render_frame(&mut terminal).expect("render");
    let buf = terminal.backend().buffer().clone();
    let focused_frame = (0..buf.area.height)
        .map(|row| {
            (0..buf.area.width)
                .map(|col| buf[(col, row)].symbol())
                .collect::<String>()
                .trim_end()
                .to_string()
        })
        .collect::<Vec<_>>()
        .join("\n");
    assert!(
        focused_frame.contains("CHRONICLE ●"),
        "rail click must focus the chronicle:\n{focused_frame}"
    );

    // …the second click on the SAME row opens its subject.
    app.handle_mouse(click);
    app.render_frame(&mut terminal).expect("render");
    let buf = terminal.backend().buffer().clone();
    let opened = (0..buf.area.height)
        .map(|row| {
            (0..buf.area.width)
                .map(|col| buf[(col, row)].symbol())
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("\n");
    assert!(
        opened.contains("motor city dossier"),
        "second click on the selected row must open it:\n{opened}"
    );
}
