//! The Python↔Rust seam: every read crosses as a JSON string (design §4).

/// Host surface the Python side implements (M1: lobby + read-only Archive).
///
/// Every method returns a JSON string; absence is JSON `null` or `[]`, never
/// a fabricated value (Constitution III.11 — honest absence). The M1 methods
/// carry default implementations returning the honest-absence encoding so
/// milestone-earlier fakes keep compiling; the production Python host
/// overrides every method.
pub trait Host {
    /// The lobby campaign catalog as a JSON array string.
    fn lobby_catalog_json(&self) -> String;

    /// Bind the chosen campaign's session on the Python side (the M1
    /// composition root's load verb — plan Task 7's `bind_session`).
    /// Returns `{"ok": true, "campaign_id": "..."}` on success; the
    /// default is a LOUD not-implemented failure so a host that forgot to
    /// wire loading can never masquerade as an empty world.
    fn load_campaign(&self, _campaign_id: &str) -> String {
        r#"{"ok": false, "error": "load_campaign not implemented by this host"}"#.to_string()
    }

    /// The rendered Archive page for `subject` as JSON: a Markdown string,
    /// or `null` when the vault has no page for it (plan Task 17).
    fn read_page_json(&self, _subject: &str) -> String {
        "null".to_string()
    }

    /// Every known page subject, sorted, as a JSON array of strings.
    fn known_subjects_json(&self) -> String {
        "[]".to_string()
    }

    /// Subjects whose pages link to `subject`, as a JSON array of strings.
    fn backlinks_json(&self, _subject: &str) -> String {
        "[]".to_string()
    }

    /// The frozen view-model for `subject` as a JSON object, or `null`
    /// (feeds the peek overlay's depth rendering).
    fn subject_view_json(&self, _subject: &str) -> String {
        "null".to_string()
    }

    /// Watchlist rows as a JSON array (M1 reads; pin writes land in M2).
    fn watchlist_json(&self) -> String {
        "[]".to_string()
    }

    // --- M2 "Playable" surface (contracts: docs/superpowers/specs/
    // 2026-07-27-m2-seam-contracts.md). Write/tick verbs return an
    // `{"ok": ...}` envelope mirroring `load_campaign`; multi-parameter
    // verbs take ONE JSON object argument so every method fits the
    // existing call0/call1 FFI helpers.

    /// Paced-driver state for pre-checks + the HUD PACING line.
    /// `attached=false` (all else false/null) = no campaign bound.
    fn pacing_state_json(&self) -> String {
        concat!(
            r#"{"attached": false, "locked": false, "lock_reason": null,"#,
            r#" "awaiting_ack": false, "pause_summary": null, "busy": false}"#
        )
        .to_string()
    }

    /// Advance one tick: `{"ok": true, "outcome": {tick, paused,
    /// chronicle}}` or a loud refusal envelope. The default is
    /// not-implemented so a host that forgot the tick surface can never
    /// masquerade as a paused world.
    fn advance_tick(&self) -> String {
        r#"{"ok": false, "error": "advance_tick not implemented by this host"}"#.to_string()
    }

    /// Run until autopause/lock/limit: `{"ok": true, "outcomes": [...]}`.
    /// BLOCKS for the whole batch (Textual ground truth: no streaming).
    fn run_until_paused(&self) -> String {
        r#"{"ok": false, "error": "run_until_paused not implemented by this host"}"#.to_string()
    }

    /// Clear a pending autopause: `{"ok": true}` / refusal envelope.
    fn acknowledge_pause(&self) -> String {
        r#"{"ok": false, "error": "acknowledge_pause not implemented by this host"}"#.to_string()
    }

    /// The render-ready chronicle rail (salience pre-computed host-side —
    /// Rust renders, never ranks): `{"autopause_line": str|null,
    /// "rows": [...]}`. Empty rows = honest absence.
    fn chronicle_rail_json(&self) -> String {
        r#"{"autopause_line": null, "rows": []}"#.to_string()
    }

    /// `VerbPlateView.model_dump_json()` or `null` (no session/org).
    fn verb_plate_view_json(&self) -> String {
        "null".to_string()
    }

    /// Queue a verb. Arg `{"verb", "target_id", "target_community"}`;
    /// returns `{"ok": true, "turn_id": N}` or a refusal envelope
    /// (player-reachable refusals never panic; system failures do).
    fn issue_verb(&self, _args_json: &str) -> String {
        r#"{"ok": false, "error": "issue_verb not implemented by this host"}"#.to_string()
    }

    /// `EndgameStatus.model_dump_json()` or `null` ONLY when no session
    /// is bound (tick 0's all-zero axes payload is NOT absence).
    fn endgame_status_json(&self) -> String {
        "null".to_string()
    }

    /// Pin/unpin. Arg `{"subject", "pinned"}`; `{"ok": true, "pinned":
    /// bool}` or a refusal envelope (capacity is player-reachable).
    fn pin_watchlist(&self, _args_json: &str) -> String {
        r#"{"ok": false, "error": "pin_watchlist not implemented by this host"}"#.to_string()
    }

    /// Persisted nav state `{"jumplist": [...], "breadcrumbs": [...]}`;
    /// pulled after `load_campaign` (nav is campaign-scoped — never via
    /// config_json, which predates selection).
    fn nav_state_json(&self) -> String {
        r#"{"jumplist": [], "breadcrumbs": []}"#.to_string()
    }

    /// Persist nav state (same shape as [`Self::nav_state_json`]);
    /// called on leaving the campaign and on quit.
    fn save_nav_state(&self, _nav_json: &str) -> String {
        r#"{"ok": false, "error": "save_nav_state not implemented by this host"}"#.to_string()
    }

    // --- M3 "Tutorial gate" surface (contracts: docs/superpowers/specs/
    // 2026-07-27-m3-tutorial-contracts.md §1, §2, §7).

    /// The tutorial overlay's current state, given the client's OWN display
    /// state (contract §1: the `OnPage`/`PaneShowing` predicates ground on
    /// the CLIENT's `current_subject`/`current_pane`, which the host has no
    /// way to observe independently — the client reports what it shows each
    /// poll; predicates still evaluate Python-side only). Arg (field order
    /// pinned): `{"subject": str|null, "pane": str, "chrome_verbs":
    /// [str, ...]}`. `{"active": false}` — the default — when no tutorial
    /// is armed for this session, so a host that forgot to wire the
    /// tutorial surface renders no strip rather than a fabricated one.
    fn tutorial_state_json(&self, _view_state_json: &str) -> String {
        r#"{"active": false}"#.to_string()
    }

    /// Mint a fresh campaign (the lobby `n` verb, contract §2). Returns
    /// `{"ok": true, "campaign_id": "...", "codename": "..."}` — catalog
    /// failures are system-level and RAISE in the real host, so no
    /// `ok: false` branch exists there by design; the default here is the
    /// LOUD not-implemented refusal, mirroring every other M1/M2 write-verb
    /// default (`load_campaign`, `advance_tick`, ...).
    fn new_campaign(&self) -> String {
        r#"{"ok": false, "error": "new_campaign not implemented by this host"}"#.to_string()
    }
}
