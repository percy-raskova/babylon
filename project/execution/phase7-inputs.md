# Running inputs for Phase 7 (record repair) — accumulated during execution

From 6.1 ledger sweep (merged cb959017), open questions the sweep did NOT resolve:
1. spec-059 T024/T031/T032 remain checked ("run suite / byte-equality" gates) though their
   prerequisite splits (T017-T023) are now unchecked — re-examine when Phase 4 does the splits.
2. spec-032 green-gate tasks flipped [x] on commit-as-evidence (T041/T050/T063/T071/T079/T092/
   T101/T105-T107) — revisit if a stricter no-ephemeral-evidence standard is ruled.
3. spec-002 DONE-THEN-UNDONE regressions: Ricci wiring (T043, was 29f84409) and George Jackson
   bifurcation (T035, was 1a73ced7) were implemented then dropped by the E0 opposition-layer
   repoint (3c5055ff). Left unchecked with notes. This is REGRESSION, not never-done — needs an
   owner-visible line in Phase 7's record repair (candidate for reinstatement or formal WONTFIX).
4. spec-005 ATUS layer (T004-T024, T037-T039, T049): implemented (8a87ad65), deleted in spec-037,
   rebuilt in babylon-data repo — marked [~]; a convention ruling would change 28 boxes.
5. spec-030 T031 checked but economics/reproduction.py does not exist anywhere — false check
   surviving from commit 1 scope; fix in Phase 7.
6. 040-michigan-statewide-scope has no tasks.md (supersession banner due in Phase 6.5 anyway).

From 1.1 scout (drift alert, note-only): _persist_events reads e.get("type"/"entity_id") but
SimulationEvent.model_dump() emits event_type — simulation_event.event_type column is 'UNKNOWN'
and entity_id NULL for all bridge events. Pre-existing; schedule a small fix (Phase 3.1 adjacent).

From 1.2 scout (note-only): StubEngineBridge.create_game kwargs mismatch (_config/_defines/
_rng_seed vs api.py config=/defines=/rng_seed=) — POST /api/games/ under stub bridge raises
TypeError today. Candidate: fix inside Phase 3.1 stub-visibility branch (C.7 touches stub bridge).

From 1.3 agent notes: get_map_snapshot metadata hardcodes h3_resolution 7 (wayne=6, us=3) —
cosmetic lie, unfixed; engine Territory lacks county_fips so aggregated county/bea/msa/state
zooms stay degenerate — scheduled later phase; hex_latest Marxian indicator columns stay NULL
until dormant-sim wiring (Phase 5).

From 1.5 scout (note-only): gameStore.ts:111 leftover editing artifact comment.

From the C.11 doc-reference linter prototype (first run, 2026-07-08): 169 unique broken
path references out of 768 scanned. Distribution: 116 of 169 (69%) sit in ai-docs
`state.yaml` + `entities.yaml` + `architecture.yaml` (the Phase-7 regen targets);
CLAUDE.md has 6 (incl. `simulation.py` → `simulation/_legacy.py` moves); project/README.md
has 9 — but those are the DELIBERATE old→new mapping lines in its reorganization note,
i.e. a false-positive class the linter needs an allowlist/annotation mechanism for
before it can gate CI (Phase 3.2 implementation detail).
