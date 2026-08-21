//! End-to-end determinism guard through the client's OWN composed seam —
//! `EngineSession::start` + repeated `advance()` — the actual path a
//! player's key presses drive. `babylon-tick`'s own `session.rs` test
//! (`two_independent_sessions_over_the_same_content_hash_identically`)
//! proves the same property at the `TickSession` level; this test proves
//! it again through the client's own composed seam.
use babylon_client::engine_link::EngineSession;
use babylon_client::story;

#[test]
fn same_content_same_tick_count_yields_the_same_hash() {
    let mut a = EngineSession::start(story::counties()).expect("session a");
    let mut b = EngineSession::start(story::counties()).expect("session b");
    for tick in 1..=5 {
        let ra = a.advance().expect("a advances");
        let rb = b.advance().expect("b advances");
        assert_eq!(
            ra.after, rb.after,
            "tick {tick}: two independent EngineSessions over the same content must hash identically"
        );
        assert_eq!(
            ra.per_rule_fired, rb.per_rule_fired,
            "tick {tick}: per-rule detail must also match — the order proof, not just the hash"
        );
    }
}

#[test]
fn five_ticks_produce_five_distinct_hashes() {
    // Regression guard against a driver that silently re-runs tick 1 —
    // exactly the bug TickSession's own tick-numbering exists to prevent;
    // this test watches for it at the client's seam too.
    let mut session = EngineSession::start(story::counties()).expect("session");
    let mut hashes = std::collections::HashSet::new();
    for _ in 0..5 {
        let report = session.advance().expect("advance");
        hashes.insert(report.after);
    }
    assert_eq!(
        hashes.len(),
        5,
        "each tick must produce a distinct state hash"
    );
}
