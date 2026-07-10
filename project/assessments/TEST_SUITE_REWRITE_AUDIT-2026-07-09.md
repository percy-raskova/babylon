# Test-Suite Rewrite Audit — 2026-07-09

**Question (Percy):** "If we hypothetically rewrote the codebase in Rust or something like
that, would it still work?" — i.e. how much of the suite is a durable behavioral spec vs
Python-implementation-coupled scaffolding.

**Method:** direct sweep of `tests/` (counts via `rg`/`find`), keystone files read
(`tests/README.md`, `tests/baselines/README.md`, `tools/regression_test.py`, sampled
`property/invariants/` + `contract/` files). Doctrinal frame: Fowler, "The Generative
Stack" (evaluations as behavioral contracts that outlive implementations; redundant
verification) and Majors, "AI demands more engineering discipline" (code as a
materialized view of understanding, disposable when stale).

**Outcome:** Amendment Q (Constitution v2.9.0, III.12 + VIII.13) + program 13
(`project/programs/13-behavioral-contracts.md`). Owner approved same day.

## Verdict

A rewrite would be **recoverable** — and the reason is the determinism constitution, not
the test count. The knowledge needed to regenerate the engine mostly lives outside the
Python already. The suite's job in a rewrite is to validate, and it can, with three gaps
(below).

## Measured proportions (2026-07-09, dev @ c5c19e21)

| Layer | Test funcs | Py LOC | Rewrite fate |
| --- | --- | --- | --- |
| `unit/` | 8,968 | 165,944 | mostly dies with the Python (correctly — regenerable scaffolding) |
| `integration/` | 1,098 | 41,505 | mixed; DB-schema- and HTTP-contract-shaped parts survive in spirit |
| `contract/` | 157 | 3,728 | ports in spirit (per-verb Article-V contracts, persistence contracts) |
| `property/` | 105 (55 Hypothesis files) | 7,316 | ports mechanically (laws stated abstractly → proptest/quickcheck) |
| `scenarios/` | 27 | 2,023 | ports in spirit (run N ticks, assert emergent outcome) |
| `benchmark/` | 11 | 536 | dies happily |

## Three strata

**Survives byte-for-byte (language-agnostic artifacts):** `tests/baselines/*.json`
(semantic checkpoint trajectories + `defines_hash`), `src/babylon/data/defines.yaml` (the
whole coefficient space — and `tests/constants.py` makes test EXPECTATIONS trace to it,
not to magic numbers), seed JSONs, the read-only SQLite reference DB, the Postgres schema
(`tick_summary`, `hex_latest`, `tick_commit` chain), the HTTP `/map/`–`/timeseries/`
contracts + MSW fixtures + Playwright specs, the Constitution's math, and written
predicate specs (e.g. `specs/053-conservation-invariants/contracts/value_conservation.md`,
which `test_value_conservation.py` merely implements — tolerance derivation included).

**Ports in spirit (the assertion is the spec; the harness is throwaway):** the property
layer is the best code in the suite by this metric — `test_material_base_ordering.py`
tests the LAW that the material base precedes the action phase (with a permutation test
proving the check catches inversions); conservation, numeraire invariance, probability
bounds, round-trip identity, the dialectics composition/Galois laws. Plus
`contract/state_ai/` (one contract per verb), `scenarios/` emergence tests, and the ~58
formula golden-value tests (the numbers are the spec).

**Dies, and should:** the bulk of the 8,968 unit funcs — Pydantic shape checks,
`MagicMock(spec=)` choreography, frozen-model discipline, import structure. Under the
code-is-cheap theory these are scaffolding for THIS materialization. 74% of test LOC
being disposable is the ratio working as intended, not a defect.

Babylon already has Fowler's redundant verification layers — six: baselines (replay),
properties (laws), scenarios (emergence), contracts (boundaries),
`mutation_baseline.json` (test-quality meta-check), benchmarks.

## The three real gaps

1. **Hashes are implementation-defined.** `defines_hash` = sha256 over Python
   `json.dumps` of a Pydantic dump (`tools/regression_test.py:131`); the `tick_commit`
   chain has the same property. The MANDATE is constitutional (III.7); the byte layout is
   specified nowhere except the code that computes it. A rewrite could not reproduce one
   hash without reverse-engineering. → Amendment Q corollary (a); program 13 item 1.
2. **Byte-identical is Python-identical.** IEEE-754 add/mul reproduce across languages;
   libm transcendentals (`exp` in every sigmoid) do not. Cross-implementation validation
   needs explicit tolerance policies with written derivations (the conservation specs
   already model this: `tol(N) = max(1e-10, 1e-11·N)` with derivation). → corollary (b).
3. **Golden density.** `imperial_circuit.json` pins ~9 variables at every-10th-tick
   checkpoints — ~54 numbers for a 52-tick world; a plausible-but-wrong engine could
   thread that needle. The tri-county bundle (full `trace.csv`, byte-compared) is the
   right density; the five unit scenarios deserve the same. → program 13 item 2.

## Recommendation (approved → program 13)

(a) `docs/reference/determinism-contract.rst` specifying canonical byte serialization for
both hashes + the cross-implementation float policy; (b) dense full-trace goldens for all
five regression scenarios; (c) keep the contract-test-per-boundary discipline Phase A
established (now constitutional per III.12).
