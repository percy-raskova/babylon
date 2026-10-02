# Indexed service validation

The complete admitted national material state still encodes to the same
240,132,173 bytes after replacing three repeated linear searches in service
validation. The saved state digest remains
`6cbfd8e8c671b3b2e172cac31775e037aa23f87b5a41961a3f7d7833113eb316`.
This is initialization evidence. Committed-period performance and the national
52-period qualification remain open.

The validator searches canonical site and household principals, seller offers,
and process outputs. Site, household and offer membership now use binary
search. Process-output lookup uses the first canonical matching row, preserving
the previous first-match behavior before the later duplicate-process refusal.
Canonical sorting precedes these lookups. The change does not alter coefficients,
prices, budgets, physical constraints, accounting, wire formats or row limits.

The earlier direct state decode took 18.213978240 seconds. With the indexed
lookups, decode took 4.044397876 seconds and encode took 3.604452154 seconds.
Re-encoding matched every saved byte. These are individual observations on the
development host, not a p95 committed-advance measurement.

The one-off measurement also checked 60,634 sites, 71,856 service connections,
58,785 offers, 59,208 service-input policies and 52,462 production policies. Its
first run incorrectly asserted 52,164 production-policy rows, using a different
equipment/commitment count. That measurement assertion was corrected to the
observed policy census; no engine state or baseline changed. The initial failed
measurement is retained separately from the successful exact-byte check.

The complete material and tick library/integration gate passed 846 tests across
81 suite summaries, including conformance and replay. Strict all-target Clippy
passed for both crates. The complete regression output is retained; the tool's
display truncation does not truncate that log. The temporary measurement source
is preserved outside production and the maintained test suite. Formatting and
the BSL repository checks passed; existing citation warnings remained advisory.

Evidence is under `reports/test-results/national-opening/2026-10-02/`:

- `indexed-service-validation-measurement.log`: the initial count assertion
  failure after successful state decoding.
- `indexed-service-validation-exact-bytes.log`: successful complete decode and
  byte-identical encode.
- `indexed-service-material-tick-regression.log`: the full 846-test gate.
- `indexed-service-strict-clippy.log`: strict all-target lint qualification.
- `indexed-service-bsl-sentinels.log`: successful BSL repository checks.

The original opening artifact and its baseline timings remain documented in
`reports/national-opening-admission-2026-10-02.md`. This component does not
establish the corrected national graph/foundation identity, PostgreSQL national
restart, a playable campaign, or enjoyment. Those use their own consuming paths
and qualification evidence.
