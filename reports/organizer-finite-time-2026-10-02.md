# Organizer finite time evidence

Part of PER-337. This component supplies a pure organizer resolver; the national runtime consumer is separate work.

`OrganizerPeriodTimeResources` supplies the resolving period, one nonzero physical unit, exact contributor-to-budget bindings and one capacity row per shared budget. Requests group by actor and budget. Aliases retain distinct receipt uses without duplicating shared supply. Independent partner consent and captured commitment limits still apply.

A valid shortage returns `InsufficientTime` with `InsufficientAvailableTime`, zero actual time use and no new contact product. Malformed resources and changed commitments return specific errors. The explicit fixed-time helper and wrapper use the same resolver.

The missing-API RED command was `cargo test -p babylon-practice-contract --test organizer finite_ --locked`: exit 101 with 19 absent API diagnostics. After implementation the same filter passed 12 tests (11 new finite-resource checks and one existing test matching the substring). All 31 organizer tests passed. Strict all-target Clippy with warnings and cognitive complexity denied, and workspace format checking passed.

Coverage includes shared alias overdraw, zero capacity, complete shared work, multiple aliases of one actor, one contributor funding two actors, resource order, missing/duplicate/mismatched resources, partner refusal, changed commitments and zero-spend partner shortages. Actual household debit identities must include both contributor and actor when one contributor funds multiple actors.

BSL sentinel checking passed with existing citation-drift warnings in unchanged rules.
