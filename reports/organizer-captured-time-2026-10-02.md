# Captured organizer time binding evidence

Part of PER-337. Organizer config requires explicit `FixedTimeControl` or `Household` time binding. Household rows exactly match the canonical contributor roster; opaque principal identities must be nonzero. Shared principals are permitted. Supplied aliases must share a budget exactly when their captured principals match. Fixed-time controls refuse household content.

Config uses schema 2 and the v2 config domain. State retains its existing framing but requires schema 2. Missing fields and older formats are refused without defaults or migration.

The absent-API RED for `cargo test -p babylon-practice-contract --test organizer captured_time_binding_ --locked` exited 101 with seven missing type/field errors. GREEN passed all five captured-binding checks and all 36 organizer tests. Strict all-target Clippy denied warnings and cognitive complexity violations. Workspace format checking passed.

Tests cover shared-principal roundtrip and changed identity, missing/duplicate/zero/unrostered/unsorted rows, required fields, old config framing and schema-1 config/state refusal, fixed-control fallback refusal and budget identity sharing. Runtime account existence, native units, capacities, outside-crate constructors and atomic material debits remain separate bridge work.

BSL sentinel checking passed with existing citation-drift warnings in unchanged rules.
