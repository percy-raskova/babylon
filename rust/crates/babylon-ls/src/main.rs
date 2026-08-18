// Intentionally minimal: issue #652 Task 5.1's RED commit needs a
// `bsl-ls` binary to exist at all (Cargo's own target discovery — and
// this repo's `cargo fmt --check` pre-commit hook — fail on a declared
// `[[bin]]` whose source file is simply missing, which is a coarser
// failure than the protocol test itself is meant to demonstrate). This
// stub does nothing: no stdio transport, no handshake, nothing written
// or read. `tests/protocol.rs` fails against it because there is no real
// protocol implementation yet, not because the crate fails to build.
// Task 5.2/5.3 replace this with the real stdio wire-up.
fn main() {}
