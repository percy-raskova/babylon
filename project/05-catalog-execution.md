# 05 — Catalog Execution: Waves 2–5, Local Play, Doc Hygiene

The catalog of record is `reports/aidocs-vs-code-audit-2026-05-16.md` Part 3
(spec text) + Part 4 (dependency graph). This file adds execution order,
2026-07-02 annotations, and the non-catalog work needed for "the game works
locally". Do NOT duplicate the spec text here — read the audit section when
starting each spec. Process for every spec: `00-mission.md` working
agreements (speckit lifecycle, TDD, full-vision no-MVP).

## Wave order (after 071; interleave 098 throughout)

### Wave 2 — Player Organizational Economy (unblocks the game loop)

- **spec-072 Vanguard Economy System** — the player-org resource loop
  (cadre/sympathizer labor, budget, reputation, heat). Frontend already
  renders `OrgState.vanguard` (wired 2026-07-02 in the web sprint); the
  backend engine economy behind it is this spec.
- **spec-073 Cohesion Mechanic (Iron Law of Oligarchy)** — org-internal
  decay/discipline. Interacts with 071's chauvinism-defection path; build
  after 071 so ORGANIZATIONAL_FRACTURE has both inputs.
- **spec-074 Demographic Crisis & Resolution Pathway Selector** — note: the
  engine's demographic base (population attrition, vitality) is now REAL and
  gated (see `02-engine-truths.md` §2); this spec builds the crisis
  RESOLUTION layer on top.

### Wave 3 — Player Action Verbs (3D Conflict + 3C Information)

- **spec-075 Kinetic Warfare (ATTACK verb)** — critical path. Depends on 071.
- **spec-076 Fog of War & Intel Layer** — the Intel page (4-variant inspector,
  incl. Communities) is already live against snapshots (2026-07-02); this
  spec adds the epistemic layer (what the player is ALLOWED to see).
- **spec-077 Gramscian Hegemony System** — player narrative warfare. Pairs
  naturally with the crisis-gated consciousness machinery (§4 of
  `02-engine-truths.md`): 077 is how the PLAYER moves visibility/agitation.
- **spec-078 Repression Logic Full** (ROE tiers, COINTELPRO, Malinovsky,
  snitch budget) — StruggleSystem/state-AI deepening; keep the
  income-circuit hegemony test green when touching StruggleSystem.
- **spec-079 Panopticon Economy (Θ attention budget)** — heat/state-attention
  economy; TerritorySystem heat dynamics already exist as substrate.

### Wave 4 — Strategic Choice

- **spec-080 Doctrine Tree MVP** — depends on 072 (CL/coherence inputs), 070
  (colonial_stance filtering), 071 (NATIONALISM tag). Build only after all
  three are merged.
- **spec-081 Warlord Trajectory Branching** — end of the critical path.

### Wave 5 — Cleanup & Loop Closure

- **spec-082 Reproductive Labor Tier-1 + S_imperial explicit accounting** —
  touches the value tensor; coordinate with 098's data slices (ATUS).
- **spec-083 Political Economy of Liquidity** (Fiscal + Fundraising +
  Precarity) — closes the money loop for orgs.

### Waves 6–7

Content/polish waves — read the audit TL;DR + Part 3 tail when Wave 5
closes. Do not plan them in detail yet (demand-driven docs).

## "Game works locally" — remaining non-catalog items

Verified state 2026-07-02: backend web tests 246/246, frontend 310/310,
TopBar + Intel on live snapshots, canonical engine alive end-to-end.
Remaining, in rough order of player-visible value:

1. **Unsupported verbs**: `investigate`, `move`, `negotiate` return
   UNSUPPORTED from the engine bridge — they need engine-side handlers.
   Most of these belong INSIDE catalog specs (076 investigate/intel, 075
   move/attack, 077/negotiate) — implement them there, not as one-offs.
1. **Django `accounts` app has no `migrations/` directory** — generate the
   initial migration (`mise run web:migrate` after `makemigrations accounts`)
   and commit it.
1. **Dashboard endpoints** (`get_economy`, `get_edges`, `get_state_apparatus`,
   `get_journal`, `get_alerts` return `{}` in EngineBridge): descoped
   2026-07-02 WITH EVIDENCE — zero frontend consumers exist. Build each one
   WITH the page that consumes it (mostly Wave-3 specs). Do not build them
   speculatively.
1. **Playtest pass**: after 072 (vanguard economy) + one Wave-3 verb, do a
   real seeded-game playthrough (`mise run web:dev`, new game, ~50 ticks) and
   file what breaks as issues — that list, not intuition, drives the next
   local-play sprint.

## Doc hygiene backlog (audit Part 5 + 2026-07-02 additions)

- Audit Part 5 lists the OBSOLETE-banner and update targets; epochs/ banners
  and roadmap-authority pointers were done 2026-07-02 (commit `108a6422`).
- `ai-docs/decisions/index.yaml` was backfilled ADR030–040/048/049/050;
  keep it current with every new ADR.
- Keep `ai-docs/state.yaml` version-bumped per significant merge.
- Keep THIS kit's `01-state-of-the-world.md` current — it is the first thing
  a fresh agent reads.

## Standing verification loop (run after every engine-touching spec)

```bash
mise run check                     # lint + format + typecheck + unit
poetry run pytest tests/integration/test_bridge_income_circuit.py -q
mise run qa:e2e-regression         # 5-tick gate incl. population liveness
# and before merging anything that changes canonical dynamics:
poetry run python -m babylon.engine.headless_runner --scope michigan-canada \
  --ticks 520 --write-baseline tests/baselines/michigan-e2e.json   # ~1 h, background
# then verify: terminal_state.counties_with_population == counties_alive == 83
```
