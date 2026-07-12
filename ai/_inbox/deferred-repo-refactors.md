# Deferred repository refactors — notes to a future maintainer

**Context (2026-07-12).** Owner authorized subrepositories (overruling ADR063's finer-grained
rejection). Program 18's 3-critic workflow recommended **only** extracting `src/frontend` →
`babylon-cockpit` (public submodule at `src/frontend`), keeping `web/` + `src/babylon` together.
That extraction is being executed now (ADR068). The owner's steer: *minimum refactoring restrained to
this issue; address the rest soon.* This file specs the "rest" so it isn't lost.

Priority order for the future you: **(1) reference-DB reproducibility is a real blocker to the
lit-Φ goal — do it first**; (2) the two-tier web↔engine contract mechanism; (3) the `poetry build`
defect; (4) `babylon_data` as a 2nd submodule (only after 3); (5) `web/` split — likely never.

---

## 1. ⚠️ CRITICAL — make the IMPORT_USE reference-DB load reproducible (NOT a subrepo issue)

Program 17 1a-unblock loaded 31,688 BEA IMPORT_USE io-coefficients into the **local** 5.7 GB reference
DB (`data/sqlite/marxist-data-3NF.sqlite`) via the fixed `tools/ingest_bea_imports.py`. **This mutation
is local-only.** CI fetches its reference DB via `./.github/actions/fetch-reference-db` (a pre-built
"ci-data-v1 subset"); the `@requires_reference_db` crown test (`tests/integration/economics/tick/
test_imperial_rent_real_wiring.py`) runs against it in `main.yml`/`nightly.yml`. So **lit Φ reproduces
nowhere but this machine** — CI, other devs, and the Hetzner deploy all still see blank Φ.
**Spec:** wire `ingest_bea_imports.py` into whatever builds+publishes the reference-DB artifact (the
`fetch-reference-db` source + the `ci-data-v1` subset builder), regenerate + republish the artifact,
and confirm the crown test passes in CI. This is spec-086/097/098 (reference-DB remediation) territory.
Until then, the crown test is effectively local-only and the "map lights up" claim is unshipped.

## 2. The two-tier web↔engine contract mechanism (the real seam fix)

Program 18's contract-seam critic proved the recent bugs (blank Φ, `float+=Decimal`, event whitelist,
`None` consciousness) were **web↔ENGINE / value-population** bugs, not web↔frontend *shape* bugs — so a
frontend split doesn't address them, and schema codegen alone wouldn't have caught 3 of 4. Do BOTH tiers
**in the single babylon repo** (web never leaves it), gated in CI:
- **Tier 1 (shape):** a Pydantic wire-model layer `web/game/contracts.py`, built incrementally from the
  highest-traffic endpoints (`state/`, `resolve/`, per-verb actions). Generate OpenAPI from
  `model_json_schema()` (NOT DRF introspection — only ~11 of 45 `_envelope()` sites pass through a
  serializer). `openapi-typescript` → a versioned `@babylon/api-types` npm package published from
  babylon CI, pinned+bumped by `babylon-cockpit`. `oasdiff` CI gate on breaking changes. `game.ts`
  survives as a thin presentation layer over the generated types (tsc becomes the drift detector).
- **Tier 2 (value/behavior):** fix `tests/unit/test_contract_parity.py` (its docstring claims to read
  `src/frontend/src/test/fixtures.ts` but never does) — make it a golden-response suite snapshotting the
  ACTUAL field values a real deterministic tick produces. This is the tier that catches "honestly-typed
  but always-`None`" bugs (blank Φ) that schema tools can't see.
- **`babylon-cockpit` pin-freshness canary:** warn/fail if its pinned `@babylon/api-types` falls N
  releases behind — the one new drift risk the frontend submodule introduces.

## 3. `poetry build` is broken today (pre-existing, independent)

`[tool.poetry] packages` declares `babylon_data` `from = "src"`, but `src/babylon_data` is a symlink
whose realpath escapes the project root (`/media/user/data/babylon-data/`); poetry-core ≥2.2 refuses to
package it → `poetry build` fails reproducibly. Harmless today (babylon is never built as a wheel), but
it **blocks any future engine-wheel** — which a `web/`↔engine split (candidate 5) would require. Triage
on its own terms (e.g. exclude `babylon_data` from the built package, or make it a proper dependency).

## 4. `babylon_data` as a second submodule (only after #3)

`src/babylon_data` already behaves like an external dependency (symlink to an off-repo trove, different
cadence, no code coupling to the web/frontend split). Plausible 2nd submodule. NOT run through the
3-critic gauntlet, and blocked by #3. Spec: fix #3, then evaluate `babylon_data` (and possibly the
reference-DB build from #1) as a `babylon-data` subrepo with its own cadence.

## 5. Splitting `web/` from `src/babylon` — likely NEVER (documented anti-recommendation)

The cleanest *import* cut in the repo (web→engine funnels through `engine_bridge.py`, AST-enforced by
`tests/unit/web/test_import_boundary.py`; zero backward deps) — but Program 18's three critics converged
that splitting it is **net-negative**: it removes the same-repo/same-PR/same-CI safety net from the exact
web↔engine seam that produced 3 of the 4 recent bugs, loses whole-stack `git bisect`, and adds a
cross-repo staleness window to `qa:regression`. Reconsider ONLY with: #3 fixed (engine wheel-able), the
#2 contract mechanism fully in place, and a **measured** (not estimated) cost/benefit — Program 18's own
recon mis-stated its headline "43-of-45 bypass serializers" (~4×) and the EventType enum size three
different ways, so any bigger cut needs verified numbers first. Requires its own constitutional amendment.

## 6. From the ai/_inbox (parsed 2026-07-12)

- **Protocolize the `getattr`-by-string persistence calls** (`protocolization.md`). ~8 sites in
  `engine_bridge.py` do `q = getattr(self._persistence, "query_tick_events", None); if callable(q): ...`
  because `_persistence` is either `PostgresRuntime` (has the method) or SQLite `RuntimeDatabase` (doesn't).
  Pyright flags it (`object|None`), mypy tolerates it — **not a bug, but the exact implicit, drift-silent
  coupling the seam discipline targets** (a rename silently no-ops). Fix: a `TickQueryCapable` Protocol
  next to the existing `RuntimePersistence`/`TraceCollector` in `persistence/protocols.py`; call sites
  become `if isinstance(self._persistence, TickQueryCapable):` → typed + checked. Small self-contained
  refactor; **bundle with the #2 contract-mechanism work**, especially post-split (it becomes the
  published interface across the boundary). Not urgent; discipline not defect.
- **Datasette guardrail for Waves 2–3** (`datesette-developer-view.md`). Datasette fits the **dev /
  Observatory** layer (point it at the reference SQLite / a Postgres read replica) — but it is the WRONG
  tool for the in-game UI: it IS the generic table/facet "spreadsheet overlay" the redesign is escaping,
  and it opens a **parallel raw-table read path** that bypasses `EngineBridge` (would happily surface the
  raw NULL `imperial_rent` or let a chart relabel `extraction_intensity` as Φ — undercutting honest-Φ).
  **Rule: player-facing charts stay native (recharts/DeckGL) reading THROUGH the bridge.** The in-game
  "charts" gap is data-wiring, not a rendering-tool gap. Datasette only ever behind the dev flag.

---
_See ADR068 (repository topology) and [[program-17-living-engine]]. Governance: ADR063 rejected a
DIFFERENT (kernel/topology/domain/engine) split — not reopened by any of the above._
