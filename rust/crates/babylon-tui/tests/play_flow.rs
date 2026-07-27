//! Scripted-flow integration tests for the M2 play screen (plan Tasks
//! 21/23/25): tick controls with the Textual pre-check ladder, F-key verb
//! dispatch with honest targeting, and watchlist pin writes — driven
//! through the same key handlers the interactive loop uses, against a
//! stateful fake host speaking the contract's exact JSON shapes
//! (`docs/superpowers/specs/2026-07-27-m2-seam-contracts.md`).

use std::cell::RefCell;

use babylon_tui::app::{key_event_from_name, App};
use babylon_tui::config::AppConfig;
use babylon_tui::host::Host;
use ratatui::backend::TestBackend;
use ratatui::buffer::Buffer;
use ratatui::Terminal;

/// A stateful M2 host double: a tick counter, a pin set, and scripted
/// pacing state, all behind `RefCell` (Host methods take `&self`).
struct PlayHost {
    tick: RefCell<u64>,
    pins: RefCell<Vec<String>>,
    locked: RefCell<bool>,
    awaiting_ack: RefCell<bool>,
    advance_calls: RefCell<u32>,
    issue_args: RefCell<Vec<String>>,
    ack_calls: RefCell<u32>,
}

impl PlayHost {
    fn new() -> Self {
        Self {
            tick: RefCell::new(3),
            pins: RefCell::new(Vec::new()),
            locked: RefCell::new(false),
            awaiting_ack: RefCell::new(false),
            advance_calls: RefCell::new(0),
            issue_args: RefCell::new(Vec::new()),
            ack_calls: RefCell::new(0),
        }
    }

    fn outcome_json(tick: u64) -> String {
        format!(
            r#"{{"tick": {tick}, "paused": false, "chronicle": [{{"tick": {tick}, "event_type": "mass_awakening", "summary": "stirring", "data": {{}}, "class_names": null, "org_names": null}}]}}"#
        )
    }
}

impl Host for PlayHost {
    fn lobby_catalog_json(&self) -> String {
        r#"[{"campaign_id":"c1","name":"campaign-a3f9b2c1d0e5","codename":"Wayne County","tick":3,
            "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}]"#
            .to_string()
    }

    fn load_campaign(&self, campaign_id: &str) -> String {
        let tick = *self.tick.borrow();
        format!(r#"{{"ok": true, "campaign_id": "{campaign_id}", "tick": {tick}}}"#)
    }

    fn read_page_json(&self, subject: &str) -> String {
        match subject {
            "briefing/c1" => serde_json::to_string("# Briefing\n\nSee [[Detroit]].").unwrap(),
            _ => "null".to_string(),
        }
    }

    fn known_subjects_json(&self) -> String {
        r#"["Detroit"]"#.to_string()
    }

    fn pacing_state_json(&self) -> String {
        format!(
            r#"{{"attached": true, "locked": {locked}, "lock_reason": {reason}, "awaiting_ack": {ack}, "pause_summary": {summary}, "busy": false}}"#,
            locked = self.locked.borrow(),
            reason = if *self.locked.borrow() {
                r#""REVOLUTIONARY_VICTORY""#
            } else {
                "null"
            },
            ack = self.awaiting_ack.borrow(),
            summary = if *self.awaiting_ack.borrow() {
                r#""1 critical event""#
            } else {
                "null"
            },
        )
    }

    fn advance_tick(&self) -> String {
        *self.advance_calls.borrow_mut() += 1;
        let tick = {
            let mut tick = self.tick.borrow_mut();
            *tick += 1;
            *tick
        };
        format!(
            r#"{{"ok": true, "outcome": {outcome}}}"#,
            outcome = Self::outcome_json(tick)
        )
    }

    fn run_until_paused(&self) -> String {
        let first = {
            let mut tick = self.tick.borrow_mut();
            *tick += 2;
            *tick - 1
        };
        *self.awaiting_ack.borrow_mut() = true;
        format!(
            r#"{{"ok": true, "outcomes": [{a}, {b}]}}"#,
            a = Self::outcome_json(first),
            b = Self::outcome_json(first + 1)
        )
    }

    fn acknowledge_pause(&self) -> String {
        *self.ack_calls.borrow_mut() += 1;
        *self.awaiting_ack.borrow_mut() = false;
        r#"{"ok": true}"#.to_string()
    }

    fn chronicle_rail_json(&self) -> String {
        let tick = *self.tick.borrow();
        format!(
            r#"{{"autopause_line": null, "rows": [{{"subject": null, "kind": "header", "tick": {tick}, "severity": null, "actor": null, "text": "T{tick:04}"}}]}}"#
        )
    }

    fn verb_plate_view_json(&self) -> String {
        // One eligible row (educate, F1) + reproduce; the other 7 verbs are
        // deliberately absent — the plate renders loud missing markers, and
        // dispatch on a present row still works.
        r#"{"kind": "verb_plate", "org_id": "org-1", "tick": 3, "verbs": [
            {"verb": "educate", "eligible": true, "reason": null, "remedy": null,
             "can_afford": true, "afford_note": null, "preview": null,
             "candidate_target_ids": ["Detroit"]},
            {"verb": "reproduce", "eligible": true, "reason": null, "remedy": null,
             "can_afford": true, "afford_note": null, "preview": null,
             "candidate_target_ids": []}
        ]}"#
        .to_string()
    }

    fn issue_verb(&self, args_json: &str) -> String {
        self.issue_args.borrow_mut().push(args_json.to_string());
        r#"{"ok": true, "turn_id": 7}"#.to_string()
    }

    fn endgame_status_json(&self) -> String {
        r#"{"pattern": null, "outcome": "unresolved", "game_over": false,
            "horizon_tick": 5200, "since_tick": null, "locked": false,
            "axes": {"revolutionary_victory": 0.1, "ecological_collapse": 0.0,
                     "fascist_consolidation": 0.0, "red_ogv": 0.0,
                     "fragmented_collapse": 0.0}}"#
            .to_string()
    }

    fn watchlist_json(&self) -> String {
        let rows: Vec<serde_json::Value> = self
            .pins
            .borrow()
            .iter()
            .map(|subject| serde_json::json!({"subject": subject}))
            .collect();
        serde_json::to_string(&rows).unwrap()
    }

    fn pin_watchlist(&self, args_json: &str) -> String {
        let value: serde_json::Value = serde_json::from_str(args_json).unwrap();
        let subject = value["subject"].as_str().unwrap().to_string();
        let pinned = value["pinned"].as_bool().unwrap();
        let mut pins = self.pins.borrow_mut();
        if pinned {
            pins.push(subject);
        } else {
            pins.retain(|s| s != &subject);
        }
        format!(r#"{{"ok": true, "pinned": {pinned}}}"#)
    }
}

fn play_app() -> App<PlayHost> {
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,"headless":true}"#,
    )
    .expect("fixture config parses");
    App::new(cfg, PlayHost::new())
}

fn press(app: &mut App<PlayHost>, name: &str) -> bool {
    let (code, modifiers) = key_event_from_name(name).expect("known key name");
    app.handle_key(code, modifiers)
}

fn render(app: &mut App<PlayHost>, terminal: &mut Terminal<TestBackend>) -> Buffer {
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

/// Bind the campaign and land on the composed play screen.
fn bound_app(terminal: &mut Terminal<TestBackend>) -> App<PlayHost> {
    let mut app = play_app();
    render(&mut app, terminal);
    assert!(!press(&mut app, "enter"));
    app
}

#[test]
fn the_play_screen_composes_all_chrome_after_bind() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(frame.contains("T+3/5200"), "HUD counter missing:\n{frame}");
    assert!(
        frame.contains("PACING: ready"),
        "pacing line missing:\n{frame}"
    );
    assert!(
        frame.contains("CHRONICLE"),
        "chronicle rail missing:\n{frame}"
    );
    assert!(frame.contains("F1 Educate"), "verb plate missing:\n{frame}");
    assert!(
        frame.contains("Briefing"),
        "center dossier missing:\n{frame}"
    );
}

#[test]
fn t_advances_one_tick_and_refreshes_the_chrome() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "t"));
    assert_eq!(*app.host_ref().advance_calls.borrow(), 1);
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("status: tick 4"),
        "tick ack missing:\n{frame}"
    );
    assert!(frame.contains("T+4/5200"), "HUD not refreshed:\n{frame}");
    assert!(frame.contains("T0004"), "chronicle not refreshed:\n{frame}");
}

#[test]
fn a_locked_driver_refuses_t_before_the_host_is_ever_asked_to_advance() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    *app.host_ref().locked.borrow_mut() = true;
    assert!(!press(&mut app, "t"));
    assert_eq!(
        *app.host_ref().advance_calls.borrow(),
        0,
        "the pre-check ladder must refuse BEFORE the advance call"
    );
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("campaign ended — REVOLUTIONARY_VICTORY"),
        "locked refusal missing:\n{frame}"
    );
}

#[test]
fn r_runs_the_batch_and_a_acknowledges_the_autopause() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "r"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("ran to tick 5 [PAUSED] (1 critical event)"),
        "run readout missing:\n{frame}"
    );
    // A second tick verb refuses while the ack is pending.
    assert!(!press(&mut app, "t"));
    assert_eq!(*app.host_ref().advance_calls.borrow(), 0);
    // Acknowledge clears it.
    assert!(!press(&mut app, "a"));
    assert_eq!(*app.host_ref().ack_calls.borrow(), 1);
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("autopause acknowledged — ready to advance"),
        "ack readout missing:\n{frame}"
    );
}

#[test]
fn f1_dispatches_educate_with_no_invented_target() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "f1"));
    let args = app.host_ref().issue_args.borrow().clone();
    assert_eq!(args.len(), 1);
    let value: serde_json::Value = serde_json::from_str(&args[0]).unwrap();
    assert_eq!(value["verb"], "educate");
    // The briefing subject's id-part ("c1") is NOT a candidate target —
    // the honest target is null, never invented.
    assert!(value["target_id"].is_null());
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("educate queued (turn #7)"),
        "queue ack missing:\n{frame}"
    );
}

#[test]
fn f3_on_a_missing_verb_slot_refuses_loudly_without_a_host_call() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "f3"));
    assert!(app.host_ref().issue_args.borrow().is_empty());
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("F3 refused — verb missing"),
        "missing-slot refusal absent:\n{frame}"
    );
}

#[test]
fn capital_p_pins_the_current_dossier_and_the_rail_rerenders() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "P"));
    assert_eq!(
        app.host_ref().pins.borrow().as_slice(),
        ["briefing/c1"],
        "pin write missing"
    );
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("status: pinned briefing/c1"),
        "pin ack missing:\n{frame}"
    );
    // A second P unpins (idempotent toggle over the rail's own rows).
    assert!(!press(&mut app, "P"));
    assert!(
        app.host_ref().pins.borrow().is_empty(),
        "unpin write missing"
    );
}
