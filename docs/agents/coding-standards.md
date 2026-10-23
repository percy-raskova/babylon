# Coding Standards

Use the owning Rust crate's typed contracts for game state and mechanics.
Keep one canonical implementation path and explicit errors. Determinism
requires checked arithmetic, finite values, canonical ordering, and equal
output bytes for equal inputs. Readers must authenticate committed state.

Rust code follows the Google Rust Style Guide. Read
[rust-style.md](rust-style.md) for the rule summary and the EXC-01 to EXC-05
exception register. `AGENTS.md` is the canonical repository rule file.

Retained Python data tools use explicit types and typed immutable models
where a schema exists. Check external input before a database mutation and
pass dependencies explicitly. Use specific type-ignore codes.

Choose regression tests for real failure modes. Use RED/GREEN when a lasting
test earns its maintenance cost, and check simple scripts directly.
Do not add tests that only repeat implementation text.

Keep production names free of the `test_` prefix. Use conventional commits
and the required co-author trailer through `mise run commit`. The formatting
tools and linters own mechanical style.
