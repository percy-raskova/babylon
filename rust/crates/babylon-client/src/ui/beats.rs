//! The narrative beat feed + latch card (B3 wave-1 Task 4, plan
//! `docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md`
//! §2.2/§2.4/§3.6/C2): drains `EngineSession.sink` every tick into a
//! bounded [`BeatLog`] (closing #503's unbounded-growth item), classifies
//! each drained event through `crate::severity`, collapses same-tick FLOW
//! events into one line, and renders each surviving beat through
//! `crate::narration`. `TERMINAL_DECISION` renders the latch card instead
//! of an ordinary beat — a system latch, never an end card, never a
//! verdict, never the five-outcome vocabulary (§3.6).
//!
//! RED (this commit): none of the production items `tests/beats.rs`/
//! `tests/autopause.rs` reference exist yet — `pub mod beats;` above
//! parses (the file exists), but every call site resolving through it
//! fails, mirroring the `d4f353d9` "module absent" RED-commit precedent.
