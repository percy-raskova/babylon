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
    /// Set by `new_campaign()` (contract §2) — `lobby_catalog_json` grows a
    /// second row once this flips.
    minted: RefCell<bool>,
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
            minted: RefCell::new(false),
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
        let base = r#"{"campaign_id":"c1","name":"campaign-a3f9b2c1d0e5","codename":"Wayne County","tick":3,
            "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}"#;
        if *self.minted.borrow() {
            format!(
                r#"[{base}, {{"campaign_id":"c2","name":"campaign-b1e2c3d4e5f6",
                "codename":"Backfire","tick":0,"status":"ACTIVE",
                "defines_hash":"dh1","engine_version":"ev1"}}]"#
            )
        } else {
            format!("[{base}]")
        }
    }

    fn load_campaign(&self, campaign_id: &str) -> String {
        let tick = *self.tick.borrow();
        format!(
            r#"{{"ok": true, "campaign_id": "{campaign_id}", "tick": {tick}, "home_subject": "county/26163"}}"#
        )
    }

    fn read_page_json(&self, subject: &str) -> String {
        match subject {
            "briefing/c1" => serde_json::to_string("# Briefing\n\nSee [[Detroit]].").unwrap(),
            "county/26163" => serde_json::to_string("# Wayne County\n\nHome dossier.").unwrap(),
            _ => "null".to_string(),
        }
    }

    fn new_campaign(&self) -> String {
        *self.minted.borrow_mut() = true;
        // `codename` is the bare operation codeword (mirrors the pre-existing
        // "Wayne County" fixture row, and `LobbyView::render`'s own
        // undecorated display) — the `"minted Operation {codename}"` status
        // template supplies the word "Operation" itself.
        r#"{"ok": true, "campaign_id": "c2", "codename": "Backfire"}"#.to_string()
    }

    fn tutorial_state_json(&self, _view_state_json: &str) -> String {
        r#"{"active": true, "finished": false, "step_index": 0, "total": 1,
            "step_id": "s", "heading": "Step 1/1: h", "patches": "p", "body": "b"}"#
            .to_string()
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
        // A non-navigable header row PLUS a navigable event row (R7:
        // exercises the shell-level chronicle-rail Enter arm) — "Detroit"
        // is a `known_subjects_json` member but carries no `read_page_json`
        // case, so navigating to it renders the honest not-found page
        // (distinctively titled "Detroit"), never a fabricated one.
        format!(
            r#"{{"autopause_line": null, "rows": [
                {{"subject": null, "kind": "header", "tick": {tick}, "severity": null, "actor": null, "text": "T{tick:04}"}},
                {{"subject": "Detroit", "kind": "event", "tick": {tick}, "severity": "informational", "actor": null, "text": "reports in"}}
            ]}}"#
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

/// A minimal M3 host double for the "minted row absent from the re-pulled
/// catalog" contract violation (R15 verify-panel finding): `new_campaign`
/// succeeds, but `lobby_catalog_json` never grows the row — a host bug the
/// client must refuse to paper over by guessing a selection. Every other
/// method rides the `Host` trait's own honest-absence default, none of
/// which this test exercises.
struct MintWithoutRowHost;

impl Host for MintWithoutRowHost {
    fn lobby_catalog_json(&self) -> String {
        r#"[{"campaign_id":"c1","name":"campaign-a3f9b2c1d0e5","codename":"Wayne County","tick":0,
            "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}]"#
            .to_string()
    }

    fn new_campaign(&self) -> String {
        r#"{"ok": true, "campaign_id": "c2", "codename": "Backfire"}"#.to_string()
    }
}

/// A minimal M3 host double whose chronicle rail carries ONLY a
/// non-navigable header row (R7 verify-panel finding (b): Enter with no
/// navigable cursor must be consumed without changing the open subject).
/// Every other method rides the `Host` trait's own honest-absence
/// default, sufficient to bind and land on the play screen.
struct NoNavigableChronicleHost;

impl Host for NoNavigableChronicleHost {
    fn lobby_catalog_json(&self) -> String {
        r#"[{"campaign_id":"c1","name":"campaign-a3f9b2c1d0e5","codename":"Wayne County","tick":3,
            "status":"ACTIVE","defines_hash":"dh1","engine_version":"ev1"}]"#
            .to_string()
    }

    fn load_campaign(&self, campaign_id: &str) -> String {
        format!(
            r#"{{"ok": true, "campaign_id": "{campaign_id}", "tick": 3, "home_subject": "county/26163"}}"#
        )
    }

    fn read_page_json(&self, subject: &str) -> String {
        match subject {
            "briefing/c1" => serde_json::to_string("# Briefing\n\nSee [[Detroit]].").unwrap(),
            _ => "null".to_string(),
        }
    }

    fn chronicle_rail_json(&self) -> String {
        r#"{"autopause_line": null, "rows": [
            {"subject": null, "kind": "header", "tick": 3, "severity": null, "actor": null, "text": "T0003"}
        ]}"#
        .to_string()
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

/// Same as [`play_app`], with the tutorial armed (contract §1) — isolated
/// to its own constructor so every other test's fixture stays
/// `tutorial_enabled: false` and its host-call pins stay untouched.
fn tutorial_app() -> App<PlayHost> {
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":true,"narrator_enabled":false,"headless":true}"#,
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
        frame.contains("status: autopause acknowledged — ready to advance"),
        "ack readout missing:\n{frame}"
    );
    // The HUD's PACING line must agree with the status line — a strip
    // still claiming a pending autopause after the ack would be two
    // contradictory readings of the same driver state (verify panel).
    assert!(
        !frame.contains("autopause pending"),
        "HUD kept a stale pending-autopause claim:\n{frame}"
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

#[test]
fn n_mints_a_campaign_and_highlights_the_new_row() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = play_app();
    render(&mut app, &mut terminal); // the lobby root, one row (c1)
    assert!(!press(&mut app, "n"));
    assert!(
        *app.host_ref().minted.borrow(),
        "new_campaign was never called"
    );
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("minted Operation Backfire — press Enter to load"),
        "mint status missing:\n{frame}"
    );
    let highlighted_line = frame
        .lines()
        .find(|line| line.contains("Backfire"))
        .unwrap_or_else(|| panic!("minted row not in the refreshed catalog:\n{frame}"));
    assert!(
        highlighted_line.contains("> Backfire"),
        "minted row not highlighted:\n{highlighted_line}"
    );
}

#[test]
fn pane_keys_switch_the_center_pane_and_refocus_center() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    // Focus the chronicle rail first — switching a pane must ALSO return
    // focus to Center (contract §3), not merely change what's drawn there.
    assert!(!press(&mut app, "tab"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("CHRONICLE ●"),
        "tab did not focus the chronicle rail:\n{frame}"
    );
    assert!(!press(&mut app, "2"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    // M5: the map pane is REAL now — the PlayHost's default
    // choropleth_json is "null", so the pane renders its own honest
    // tier-absence line (the M3-era "not yet ported" fence is retired).
    assert!(
        frame.contains("no county map"),
        "map pane honest-absence line missing:\n{frame}"
    );
    assert!(
        !frame.contains("CHRONICLE ●"),
        "the chronicle rail kept focus after a pane switch:\n{frame}"
    );
    // '3' is the wiki pane's own key: it restores the center dossier.
    assert!(!press(&mut app, "3"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Briefing"),
        "'3' did not restore the wiki pane:\n{frame}"
    );
}

#[test]
fn map_pane_fetches_on_entry_cycles_on_lens_and_escapes_to_wiki() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    // Pane entry pulls the envelope (M5 contract §3) with the default
    // county/value args.
    assert!(!press(&mut app, "2"));
    let calls = app.host_calls();
    assert_eq!(
        calls.iter().filter(|c| *c == "choropleth_json").count(),
        1,
        "pane entry must fetch the choropleth exactly once: {calls:?}"
    );
    // The keybar shows the map surface's own hints.
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("l lens") && frame.contains("y tier"),
        "map keybar hints missing:\n{frame}"
    );
    // 'l' cycles the lens and re-fetches; 'y' cycles the tier likewise.
    assert!(!press(&mut app, "l"));
    assert!(!press(&mut app, "y"));
    let calls = app.host_calls();
    assert_eq!(
        calls.iter().filter(|c| *c == "choropleth_json").count(),
        3,
        "each lens/tier cycle must re-fetch: {calls:?}"
    );
    // Esc leaves the pane back to the wiki, never tearing the campaign.
    assert!(!press(&mut app, "esc"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Briefing"),
        "Esc did not return to the wiki pane:\n{frame}"
    );
}

#[test]
fn dashboard_pane_fetches_on_entry_cycles_locally_and_escapes_to_wiki() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    // Pane entry pulls BOTH payloads (M6 contract §2).
    assert!(!press(&mut app, "1"));
    let calls = app.host_calls();
    assert_eq!(
        calls.iter().filter(|c| *c == "trend_json").count(),
        1,
        "pane entry must fetch the trend exactly once: {calls:?}"
    );
    assert_eq!(
        calls.iter().filter(|c| *c == "dashboard_view_json").count(),
        1,
        "pane entry must fetch the snapshot exactly once: {calls:?}"
    );
    // The PlayHost default is "null" — the pane renders its own honest
    // absence line, never the retired M3 fence.
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("no trend recorded"),
        "dashboard honest-absence line missing:\n{frame}"
    );
    assert!(
        frame.contains("c chart") && frame.contains("m 3D"),
        "dashboard keybar hints missing:\n{frame}"
    );
    // 'c' cycles the chart page LOCALLY — pure view state, no refetch.
    assert!(!press(&mut app, "c"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("price⟷value scissors [2/5]"),
        "'c' did not advance to the scissors page:\n{frame}"
    );
    let calls = app.host_calls();
    assert_eq!(
        calls.iter().filter(|c| *c == "trend_json").count(),
        1,
        "'c' must not refetch: {calls:?}"
    );
    // Esc leaves the pane back to the wiki, never tearing the campaign.
    assert!(!press(&mut app, "esc"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Briefing"),
        "Esc did not return to the wiki pane:\n{frame}"
    );
}

#[test]
fn briefing_enter_with_no_link_focused_navigates_to_home_subject() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    // `bound_app` already lands on `briefing/c1` with no link cursor moved.
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "enter"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Wayne County") && frame.contains("Home dossier"),
        "Enter with no link focused did not navigate to home_subject:\n{frame}"
    );
}

#[test]
fn k_with_no_peek_target_refuses_and_logs_the_dispatch_once() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "K"));
    assert!(!press(&mut app, "K"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("status: no wikilinks to peek on this page"),
        "K refusal missing:\n{frame}"
    );
    assert_eq!(
        app.chrome_verbs(),
        ["peek_wikilink"],
        "peek_wikilink must append exactly once despite two K presses"
    );
}

#[test]
fn the_tutorial_strip_polls_after_bind_and_esc_dismisses_it_for_the_session() {
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = tutorial_app();
    render(&mut app, &mut terminal); // the lobby root
    assert!(!press(&mut app, "enter")); // bind + land on the briefing
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("Patches: p"),
        "tutorial strip missing after bind:\n{frame}"
    );
    assert!(!press(&mut app, "esc"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        !frame.contains("Patches: p"),
        "Esc did not dismiss the tutorial strip:\n{frame}"
    );
    // The strip's precedence over the rail/view fallthrough: Esc must not
    // have also popped the wiki view back to the lobby.
    assert!(
        frame.contains("Briefing"),
        "Esc fell through and left the campaign instead of only dismissing the strip:\n{frame}"
    );
}

#[test]
fn esc_defocuses_a_rail_instead_of_leaving_the_campaign() {
    // The arm the M2 contract promised and the rails' own doc comments
    // assert ("Esc never reaches this handler — the app shell defocuses
    // the rail itself") — missing until M3's port found the gap. With a
    // rail focused, Esc must return focus to Center and be consumed; it
    // must NOT fall through to the wiki's own Esc=Back arm (which pops
    // the view and reads as campaign teardown).
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "tab")); // Center -> Chronicle
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(frame.contains("●"), "Tab never focused a rail:\n{frame}");
    assert!(!press(&mut app, "esc"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        !frame.contains("●"),
        "Esc did not defocus the rail back to Center:\n{frame}"
    );
    assert!(
        frame.contains("Watchlist ("),
        "Esc fell through and tore down the play chrome:\n{frame}"
    );
}

#[test]
fn n_mint_whose_row_never_lands_in_the_catalog_refuses_to_guess_a_selection() {
    // R15 fix (verify-panel finding): `MintWithoutRowHost::new_campaign`
    // succeeds, but its `lobby_catalog_json` never grows the minted row —
    // a host contract violation the client must refuse to paper over.
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,"headless":true}"#,
    )
    .expect("fixture config parses");
    let mut app = App::new(cfg, MintWithoutRowHost);
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    app.render_frame(&mut terminal).expect("frame renders"); // the lobby root
    let (code, modifiers) = key_event_from_name("n").expect("known key name");
    assert!(!app.handle_key(code, modifiers));
    app.render_frame(&mut terminal).expect("frame renders");
    let frame = buffer_text(terminal.backend().buffer());
    assert!(
        frame.contains(
            "minted Operation Backfire, but the catalog did not return it — refusing to \
             guess a row"
        ),
        "loud missing-row refusal missing:\n{frame}"
    );
    // The refusal message itself names the codename ("Operation Backfire")
    // — the thing that must never happen is a CATALOG ROW rendering (and
    // being highlighted) for a campaign the re-pulled catalog never
    // actually returned, so check the row listing specifically rather
    // than the whole frame.
    assert!(
        !frame.contains("> Backfire"),
        "a row the catalog never returned must never render as selected:\n{frame}"
    );
    assert!(
        frame.contains("Wayne County"),
        "the pre-existing catalog row must still render:\n{frame}"
    );
}

#[test]
fn chronicle_enter_on_a_navigable_row_routes_and_refocuses_center() {
    // R7(a): focus the rail, Enter on a NAVIGABLE row -> routes to the
    // subject and focus returns to Center. `PlayHost::chronicle_rail_json`
    // now ships a "Detroit" event row alongside the header, and the rail's
    // cursor starts on the first navigable row automatically.
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    let mut app = bound_app(&mut terminal);
    assert!(!press(&mut app, "tab")); // Center -> Chronicle
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        frame.contains("CHRONICLE ●"),
        "tab did not focus the chronicle rail:\n{frame}"
    );
    assert!(!press(&mut app, "enter"));
    let frame = buffer_text(&render(&mut app, &mut terminal));
    assert!(
        !frame.contains("CHRONICLE ●"),
        "Enter on a navigable row did not return focus to Center:\n{frame}"
    );
    assert!(
        frame.contains("Detroit") && frame.contains("No page recorded for this subject."),
        "Enter did not navigate to the chronicle row's subject:\n{frame}"
    );
}

#[test]
fn chronicle_enter_with_no_navigable_cursor_is_consumed_without_changing_the_subject() {
    // R7(b): Enter with no navigable cursor -> consumed, subject unchanged.
    // `NoNavigableChronicleHost`'s rail carries only the header row, so
    // `ChronicleRail::cursor` stays `None` and `handle_key(Enter)` returns
    // no event to route.
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,"headless":true}"#,
    )
    .expect("fixture config parses");
    let mut app = App::new(cfg, NoNavigableChronicleHost);
    let mut terminal = Terminal::new(TestBackend::new(100, 32)).expect("backend");
    app.render_frame(&mut terminal).expect("frame renders"); // the lobby root
    let (enter_code, enter_mods) = key_event_from_name("enter").expect("known key name");
    assert!(!app.handle_key(enter_code, enter_mods)); // bind + land on the briefing
    app.render_frame(&mut terminal).expect("frame renders");
    let (tab_code, tab_mods) = key_event_from_name("tab").expect("known key name");
    assert!(!app.handle_key(tab_code, tab_mods)); // Center -> Chronicle
    app.render_frame(&mut terminal).expect("frame renders");
    assert!(!app.handle_key(enter_code, enter_mods)); // no navigable cursor
    let frame = buffer_text(terminal.backend().buffer());
    assert!(
        frame.contains("Briefing"),
        "Enter with no navigable cursor must not change the open subject:\n{frame}"
    );
    assert!(
        !frame.contains("No page recorded for this subject."),
        "the open subject must not have changed at all:\n{frame}"
    );
}
