# Program 14 — Correspondence

**Status: COMPLETE 2026-07-11** · Ratified 2026-07-10 (plan-mode approval) · ADR063 · no
constitutional amendment (the program *enforces* existing principles; no primitive changed,
no constitutionally named path moved)

**One sentence:** the repo's structure now states the constitution — `kernel < models/formulas
< topology < domain < persistence < engine`, with `intelligence` observing — and import-linter,
the repo-hygiene gate, and the byte-identical regression rail enforce it permanently.

## Origin

Percy brought an external structural analysis (layering schema + hygiene audit) and two
escalations: subrepositories per package, and a Rust kernel rewrite. Verification confirmed
the coupling diagnosis (economics→engine 15×, engine→economics 39×, persistence↔engine,
54 tracked-but-ignored files, 70MB in `reports/`), refuted several prescriptions (dense-golden
LFS exemption was deliberate; `setup.cfg` is a documented doc8 workaround; the pack was 57.7MB
so no history rewrite; `simdb/` was orphaned), and found the load-bearing fact: **the cycles
were thin** — ~6 engine-owned abstractions plus type-only imports.

## Owner rulings (2026-07-10)

1. **Full restructure; Rust deferred.** Trigger: a measured national-scale CPU profile.
   Method: PyO3 strangler per module behind the dense goldens under III.12(b) tolerance.
   This program is itself the Rust preparation — the kernel boundary is now real.
2. **Subrepos rejected.** One determinism contract spans the sim; boundaries enforced
   in-monorepo by import-linter instead.
3. **Fork-ledger rows F2/F7/F9/F10/F11/F12 ratified** for execution (the byte-identical set).
4. **`michigan-e2e.json` (35MB) → LFS** (fails III.12's "small, diffable" test; the dense
   goldens' never-LFS exemption untouched).
5. **Root knowledge-tree design delegated**: `ai/` = Claude's tree (+ gitignored `ai/scratch/`),
   `project/notes/` absorbs `thoughts/` + `datagaps/`, `sources/` holds Percy's theory texts.

## Execution record

| Phase | Landed | Substance |
| --- | --- | --- |
| 0 hygiene | `b91f8ffd`…`4ac109d0` | 53 ignored-tracked untracked (index-only); dead lockfiles/husks deleted; michigan→LFS (hash-verified, QA 5/5); `ai-docs/`→`ai/` (135 live refs); `project/notes/`, `sources/`, `design/ui_kits/`; **repo-hygiene gate** (allowlist / tracked-ignored=0 / >1MiB non-LFS) wired into `mise check` + CI — caught two live violations while being built |
| 1 kernel + cycles | `ae7912b1`…`c836463a` | import-linter contracts landed **RED**; `babylon.kernel` (event bus, interceptor, SystemBase/System, GraphProtocol, ServicesProtocol, DatabaseProtocol); `babylon.topology` (BabylonGraph + adapters + algorithms, 188 importers); database impl → persistence; `simdb/` deleted; contracts **green** and wired into pre-commit/mise/CI |
| 2 fork deletions | `bc28e1e0`…`f325b1a7` | F9 derivations/, F12 Marx reference formulas (the TRPF law kept, arithmetic inlined), F7 consciousness trio (`tendency_modifier` kept), F2 InterpolatingBEASource (salvage **deferred** per ledger), F10+F11 trace cluster + PersistenceObserver (SessionRecorder canonical; JsonlSessionRecorder untouched, owner-queued); ledger rows stamped EXECUTED; ~2,300 LOC; QA 5/5 byte-identical |
| 3 re-layering | `6a86669b`…`e34ad0f1` | kernel smalls **by purity audit** (log/math/retry/exceptions/schema_registry/sim_clock/metrics-protocol; `protocol_kit` exposed as economics, `protocols/` stays models-layer, JSONL recorder → engine/observers); `intelligence/` = ai+rag; `domain/` = economics+dialectics+organizations+institution+bifurcation+**geography** (né infrastructure); **3e rejected by its own verify-first clause** (reference/ is self-contained and imported BY domain — stays top-level); architecture.yaml `directory_map` rewritten + ChromaDB/DearPyGui staleness fixed; CLAUDE.md layering paragraph |
| 4 records | this branch | ADR063, this file, state.yaml banner, owner-queue entry, memory; fresh-clone sanity; push + CI watch |

## The three literal classes the seds could not see (hard-won)

1. **Attribute-style imports** — `from babylon.engine import graph_algorithms as ga`
   (sparrow.py; caught by the full-suite gate).
2. **`Path(__file__)` anchors** — persona loader, economics validation seed, department mapper
   (each gained a parent with its move).
3. **Segment-wise path builders** — `/ "babylon" / "economics" / …` (naics fixture, four
   engine hydration sites, spec-112's old lesson repeated).

Plus the loudest III.11 lesson of the program: a **skip-if-absent guard converted 19 path
breakages into silent skips** — found only by diffing skip counts between full runs.

## Verification

Every phase: `mise run check` true-exit 0 (the composite grew `check:hygiene` + `lint:imports`)
and `qa:regression` **5/5 byte-identical** — the engine never moved numerically through ~900
touched files. Heavy boundaries additionally ran the full unit suite (9,390–9,468 passed,
17-skip baseline restored) and Phase-3 close ran `qa:e2e-regression` + `web:check` (green) +
`docs:strict` — which ran for the **first time** and exposed a pre-existing ~2.4k
duplicate-object warning wall (owner-queued; zero rename-class warnings).

## Owner follow-ups spawned

- **F2 interpolation salvage** into `DefaultBEAShareLookupService` + `GLOBAL_FALLBACK_SHARE`
  define — baseline-moving, needs its own ruling (the ledger's explicit deferral).
- **JsonlSessionRecorder** — keep-or-delete ruling (F11 left it as a separate item).
- **docs:strict structural wall** — autosummary × handwritten `api/*.rst` duplicate every
  symbol; needs a docs-architecture ruling.
- **Fork ledger** — 9 rows still awaiting rulings (F1/F3/F4/F5/F6/F8/F13/F14/F15).
- **Rust trigger** — revisit only on a measured national-scale CPU profile.
