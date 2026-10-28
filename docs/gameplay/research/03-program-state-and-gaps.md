<!-- vale off -->
<!-- Research briefing: dated evidence with literal identifiers preserved.
     Not governed prose. Same disposition as project/README.md. -->

# Program state and gaps — what was planned, built, and buried

Read-only familiarization sweep, 2026-10-25. Scope: `project/programs/05`,
`07`, `09`; `reports/epochs-vision-gap-audit.md`; `ai/state.yaml` as index;
`docs/concepts/{organization-model,ooda-loop-system,infrastructure-topology}.rst`.
Brainstorms and surfaces are covered by siblings (`01-*`, `02-*`) and are cited,
not repeated.

The one fact that governs this page: the corpus in scope is dated evidence, not
a control surface. `project/README.md` says so in its own header — "programs,
plans, notes, and audits preserve why earlier work made sense. They are dated
evidence, not a control surface for current status." Linear owns status;
`NORTH_STAR.md` and `docs/architecture-reset/` carry the live plan. Everything
below is therefore archaeology with a live moral.

---

## (a) Built vs planned vs dead

### Built and live today

- Rust workspace, 13 crates; live play path
  `babylon-kernel` → `babylon-graph` → `babylon-bsl` → `babylon-tick` → `babylon-client`,
  with `babylon-material-circuit`, `-persistence`, `-rtd`, `-evidence`,
  `-practice-contract`, `-ls`, `bsl-lint`, `bsl-test` alongside.
- **Gate 2 complete in checkout** (`ai/state.yaml`): executable phase order
  (ADR222/PER-17), whole-tick atomicity + world hash (ADR223/PER-18), governed
  causal attribution (ADR224/PER-19), role-sensitive authority, audit receipts.
- Material circuit v1/v2 (ADR238/239), recurring national economy (ADR263),
  shared freight capacity (ADR259), statewide commodity circulation (ADR260),
  household budgets/time (ADR269/270), captured catalog (ADR265), bounded Wayne
  organizer cycle (ADR262).
- Archive worker + restricted reader + attested membership and page bodies
  (ADR281/282/284). Persistence: Rust owns the Postgres boundary (ADR220/PER-48);
  ADR287/PER-354 is retiring it for one embedded SQLite campaign DB, whose
  ratified 3.53.1 link "no crate consumes … yet" (`AGENTS.md`).
- Bevy client (Amendment AF/ADR186): observer campaigns, county choropleth,
  economy/network/material/3D/history panes, audio suites (ADR152/153).

### Planned and explicitly unfinished

- **Gate 3** durable campaign/H3/Archive decision loop (label renamed in
  `docs/architecture-reset/09-acceptance-and-governance.md`); then **Gates 4–6**
  — circuit, player agency, COVID. `NORTH_STAR` says "broader G4 observer and G5
  player-agency acceptance remain incomplete."
- `babylon-graph` Lane A (`capacity`, `dossier`, `exposure`, `backfire`,
  `induced`): real, tested, reached by nothing outside the crate — ADR184 says
  so itself, "the whole Lane A estate still has ZERO external callers."
- `AGENTS.md`: every game display must answer a decision question. Nothing built
  so far claims a milestone on display grounds.

### Dead — code, program, or both

- **Python engine**, recoverable at tag `p27-python-freeze`; every
  `src/babylon/engine/**` path cited by the catalog, audit, and concept pages.
- **Django/React product** (`web/`, then `src/frontend/`), deleted by `spec-112`
  (ADR061 Phase D); then the **Ratatui client** (Amendment AC/ADR150), superseded
  by Bevy with "no deprecation window, no dual-client period."
- **Program 09 Lane W**: `090`–`096`, `099`, `103` carry DONE prose and no
  artifacts; `specs/094-the-wire/tasks.md` is 29/29 for a deleted Wire; `095` is
  7/43, spec'd and unbuildable. **Observatory**: `rg observatory rust/crates` empty.
- **Synopticon**: mockups only (`design/mockups/synopticon/`), parked behind
  catalog 078/079 — never specced, never built.
- **Catalog Waves 2–5** (`specs/072`–`085`): never authored; fourteen numbers
  skipped between `071` and `086`. Vanguard economy, cohesion, kinetic warfare,
  fog of war, hegemony, repression logic, panopticon, doctrine tree, warlord
  trajectory, reproductive labor, liquidity — the whole political-agency half of
  the 27-spec "COMPLETE GAME" has no spec, code, or test.
- **`098`** absorbed into `109-data-spine`; **`design/mockups/`** (66 files, Cold
  Collapse canon, 13-screen kit) orphaned — nothing outside `project/` prose and
  `LICENSING.md` points at it.

### Died twice, quietly

The vision did not die; its host did. Attention threads, the digital dossier,
risk scoring, and fog-of-war premise re-founded in `babylon-graph`: `capacity.rs`
budgets an actor's means against yield per unit spent, `dossier.rs` holds what an
actor believes, `exposure.rs` prices replaceability, and yield is "computed on
`L`, never on truth" — "fish in water" as a type. Missing is only the wire into
tick and screen: the gap the 2026-07 audit named and the 2026-10 gates still name.

---

## (b) Gap-audit verdicts that still bite

`EG` = `reports/epochs-vision-gap-audit.md` (2026-07-14, 373 items: ~12% BUILT,
~47% PARTIAL, ~37% MISSING, ~4% SUPERSEDED). `SP` = `reports/seam-wiring-punchlist.md`.

| Gap | Source | Status today |
|---|---|---|
| "Engine computes it, the player never sees it" — the PARTIAL 47% | EG §1, §4 | **Still the headline.** Not fixed; re-expressed as Gate 4 circuit + Gate 5 agency. The 47% itself is void — the Python half it measured is gone. |
| Bridge drops named drama (34-of-79 event whitelist); George Jackson bifurcation, dispossession, ecological overshoot vanish silently | EG §4 | **Mechanism dead, question alive.** Rust uses typed effects, exact-allowlist, default-deny. Which events earn narration is a BSL authoring choice now, not a hand-written if/elif ladder. |
| Gap 1 — 26 per-tick `tick_*` economics attrs unregistered (`SEAM_REGISTRY`), "richest untapped signal" | SP Gap 1 | **Rail dead, successor live.** RTD dossiers carry `PRESENT/ABSENT/UNKNOWN/NOT_COMPUTED/REDACTED`; the audit's one BUILT row ("honest missing-data representation") is the bar that survived. |
| Gap 2b untyped endpoints, Gap 3 phantom TS fields | SP | **Dead** with the TypeScript client. Keep only as a cautionary pattern. |
| CLAIMS-edge seeding bug — "highest-leverage engine fix in this audit" | EG Wave 1 #5 | **Moot.** No `balkaniz`/sovereignty/CLAIMS layer in Rust; the four subsystems it unblocked (faction influence, sovereign collapse, colonial-stance endgames, extraction→habitability) were never ported. |
| Orphaned DI: `RuleBasedStateAI`, `ThreadManager.allocate_threads`, `compute_disproportionality`, `stationary_distribution`, counter-tendency calculator — constructed, never called | EG §4 | **Reproduced in Rust.** Five `babylon-graph` modules with zero external refs; ADR184 acknowledges it rather than hiding it. Same failure mode, new language. |
| Attention Threads / Digital Dossier / Lavender / Gospel | EG epoch3-presentation | **Re-founded, unwired.** `capacity` + `dossier` + `exposure` (ADR180/184). No player surface, no tick invocation. |
| Doctrine Tree, Theoretical Labor, four trunks — "single largest coherent MISSING cluster" | EG §1, epoch3-player | **Still missing.** No spec number, no Rust trace, no content. Nothing has replaced it. |
| Fog of war / Epistemic Horizon (Desert–Mud–Water), three vision states | EG Wave 5 | **Half re-founded.** RTD `PLAYER_KNOWLEDGE` vs `ADMIN_MATERIAL` audience; no player-facing fog, no falsification buckets. |
| 13 Census ACS demographic tables orphaned; race-blind readers | EG epoch2-data | **Still orphaned (loaders exist, no live consumer verified):** `src/babylon_data/census/` ships; no race disaggregation reaches play. |
| FAF5 freight loader "never built"; bilateral value flow blocked | EG epoch2-data, §3c | **Closed.** `src/babylon_data/bts/faf_loader.py` ships; ADR259 gives Michigan supply chains one shared Designed freight account. |
| Soundtrack: "assets exist, zero playback code" | EG epoch3-presentation | **Closed.** 13 tracks + 39 interface sounds, deterministic, ADR152/153. |
| Synopticon as the face of repression; hegemony narrative-control resource | EG epoch3-presentation; `07` X9 | **Dead surface, absent mechanic.** No hegemony scalar anywhere, then or now. |
| Five named endgames, colonial-stance gating, balkanization overlay | EG epoch3-political | **Dead with Python.** Also contradicted by the owner's own "emergence over scripted conclusions" ruling (EG §5) — see (c). |

---

## (c) Contradictions

1. **Three authorities, one plan.** `05-catalog-execution.md:3` names
   `reports/aidocs-vs-code-audit-2026-05-16.md` "the catalog of record"; `09:28`
   names the 27-spec catalog *plus* `07`'s M1–M12/X1–X9 as the destination;
   `project/README.md` says the whole tree is dated evidence and Linear is sole
   authority. Only the newest statement is true, and it invalidates the other two.
2. **Postgres vs SQLite.** `07` §1 decision 5 records Percy's verbatim ruling
   "Lets try to keep it all in postgres." ADR287 ratifies one embedded SQLite
   campaign owner, and PER-354 is executing it. A Director ruling was reversed
   by a later Director ruling; the `07` file cannot be cited for storage.
3. **Narrator.** `07` §1 decision 3: "We are using Workers-AI/LoRA narrator."
   `09` R-NARR: deterministic provider first, Workers-AI later, inside a
   `NarratorProvider` seam. Live: neither — the Bevy client has no narrator
   surface, and the Wire that would host it is deleted.
4. **Endings.** `09` spec-095 builds a chronicle on the five-outcome enum; the
   gap audit's owner ruling (2026-07-14) directs *unwinding* adjudicated endings
   toward "a game is a century, it ends when it ends." Both are ratified text.
   The live gate list is silent, which is the only reason this is not yet a
   blocking conflict.
5. **Status layer is self-contradicting.** `09` marks 096 DONE in prose while
   `specs/096/tasks.md` is 0 checked / 22 open; 092 and 103 are fully checked for
   code that no longer exists; 090's tasks file has no checkboxes at all. Any
   program-state claim sourced from these files is unreliable in both directions.
6. **`ai/state.yaml` contradicts itself across time.** `meta.role` is
   `historical_implementation_ledger` with a 2026-08-23 governance snapshot at the
   top, while `not_implemented` still lists a "phase 3 / sprint 3.3" LLM provider
   and `planned` lists `vanguard_economy` as a brainstorm that was later built and
   then deleted. It is a ledger with no single timestamp.
7. **`docs/concepts/` speaks in the present tense about a deleted engine.**
   `organization-model.rst` asserts "four frozen Pydantic subtypes";
   `ooda-loop-system.rst` documents 67 `OODADefines` coefficients and a
   five-factor initiative formula; `infrastructure-topology.rst` describes
   Feature-036 capacity ceilings, junction cascade, and `SEVER`/`THROTTLE`
   internet modes. None has a live counterpart as described: the substrate is generic
   (`node`/`organization`/`institution`/`sovereign` vocabulary per ADR184), the
   live tick has a *phase* named `ooda` hosting organizer rules but no initiative
   or cycle-time model, and no scenario defines contains OODA coefficients. The
   pages carry no per-page banner — only a site-level caveat in
   `docs/concepts/index.rst`.

---

## (d) Stale and superseded

- **Program 09 as a plan.** Superseded twice: Program 27 Refoundation
  (`docs/superpowers/specs/2026-07-28-program-27-refoundation-design.md`)
  declares "**Supersedes:** the current v1.0 critical path (Director ruling
  R2)"; Program 28 (2026-08-10) then replaced the client. Program 09's four
  lanes describe an estate — Django, React, Postgres-per-tick, DuckDB archive
  reads, Workers-AI — of which only the data lane's output survives.
- **`05`'s wave order** is a queue for specs that were never written. Its
  standing verification loop (`mise run sim:e2e-bg`, `poetry run pytest`) is
  Python-era and the mise tasks no longer mean what it says.
- **`07`'s M-items** are the best surviving record of *intent*: M1 commodity
  routing became ADR260 (finite statewide commodities over captured physical
  paths), M5's physical-units ledger is nearest ADR265's captured catalog —
  but no MWh/tons/GPU-hours ledger exists; M6
  modding became BSL + `.bscn` + `mods/` (`docs/architecture-reset/03`), M8
  deployment survives as a Nix/packaging train (ADR094–097). M2 (prose→stance
  vector), M3 (verb sub-modes), M9 (blocs as Layer-0), M10 (federation), M11
  (liberated zones), M12 (speed controls) have no live implementation.
- **`ai/epochs/overview.md`'s banner** points readers at "the living roadmap":
  the May audit plus `ai/state.yaml`. Both have since been demoted to dated
  evidence. The banner is now a stale pointer inside a stale document.
- **`reports/seam-wiring-punchlist.md` and `wave2/wave3-*-implementation-map.md`**
  describe sentinels, serializers, and lenses on a stack that no longer exists.
  ADR186 clause (vii) records the sentinel disposition; the punch-list's *method*
  (prove every computed quantity reaches a consumer) is the part worth keeping.
- **`docs/concepts/` Python mechanics** (organization, OODA, infrastructure,
  institution, community hypergraph, state-apparatus-ai, carceral geography,
  consciousness taxonomy) are frozen rationale. Read for why, never for what.
- **`design/mockups/`** — including `synopticon/` and the Cold Collapse token
  canon — is unbuilt reference material. The Article VII palette amendment it
  required (R-VII) went with the client that needed it.
- **File-name trap**: `babylon-material-circuit/src/wire/` is a financial payment
  wire, not the Gramscian Wire. Any `rg wire` hit there is unrelated to `07` X2.

<!-- vale on -->
