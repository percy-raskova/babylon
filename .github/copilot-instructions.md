# Babylon code review

Read `AGENTS.md` for current boundaries. `CONSTITUTION.md` governs game law.
`NORTH_STAR.md` describes intended play. Linear owns current scope.

Review changed behavior from its real input through authoritative Rust state,
committed Postgres rows, observer projection, and visible result. Report a
defect only when you can identify its trigger and consequence. State a precise
code location and a small reproducer or concrete example.

- Equal input bytes must produce equal output bytes and hashes. Check
  ordering, finite values, checked arithmetic, errors, and replay identity.
- Rust owns mechanics and game-managed Postgres writes. An observation,
  narrator, or Bevy display must not create a second authority path.
- Check transaction boundaries, exact commit markers, failed-write rollback,
  restart behavior, reader privileges, visibility, and campaign isolation.
- Trace allocations, repeated serialization, database round trips, and query
  plans when a change affects tick or observer latency.
- Authored Michigan values live in `content/scenarios/michigan/defines.toml`.
  Check units, one 28-day tick, and the saved campaign identity.
- An edit to that file must keep an existing campaign unchanged.
- BSL rules need material causes and governed evidence. Flag a new primitive,
  fixed response curve, or imposed downstream result.
- Delete obsolete implementations and their coupled tests. Keep something
  for a current consumer or a unique contract. Git preserves history.
- The frozen Python tag supplies old citations, not current game authority.
- For CI, check changed-input selection, deleted paths, failure propagation,
  trusted cache publication, and complete release qualification.
- A skipped prerequisite must not turn the required result green.
- A public download needs a qualified main release and exact source evidence.
  Check launcher, saved-state reopen, notices, checksums, provenance.
- A development push must not publish a release. The commit hook validates
  new messages. Development versions derive from Git history.

Skip formatting, naming preferences, speculative abstractions, compatibility
layers, and requests to restore deleted code without a current consumer.
Do not repeat lint output or treat missing Copilot feedback as a merge blocker.
Do not claim that passing tests proves a human understood the game surface.

One actionable defect per comment. If a concern lacks evidence, state the
uncertainty instead of presenting it as a confirmed fault.
