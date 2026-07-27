# The Raster Cutover — Rust/Ratatui Archive Client (Design)

**Date:** 2026-07-26 · **Status:** Approved design (pre-plan) · **Scope:** full replacement of the
Textual ArchiveApp with a Rust/Ratatui client consumed as a Python extension module.

## 1. Purpose

Replace the Textual terminal client (`src/babylon/tui/`, "The Archive", ~4.5k LOC) with a Rust
client built on **Ratatui 0.30**, imported into Python as a maturin/PyO3 extension and launched
from the existing composition root (`babylon play`). The end state: a coherent, live-data terminal
client with a playable tutorial touching every player option, geographic maps with lens filters, a
topology page with real rasterization (including hypergraph 3D rasterization via hypergraph-rs), a
"stock market" economics dashboard suite, and the wiki view — with hover popups and full
keyboard+mouse navigation. The existing test suite stays green throughout; the Textual lane is
retired only in a declared cutover ceremony after parity is proven.

## 2. Binding context (what this design must honor)

- **CONSTITUTION.md II.8 / Amendment V:** a client is a presentation-only viewport over the
  `observe()` projection contract; shapes are JSON-serializable; transport is independent
  (in-process call, HTTP, or file materialization all legal); clients are disposable. A Rust client
  is legal by construction.
- **II.5 / R4:** no LLM in the input path; verbs enter only via the deterministic verb registry
  (nine Article-V verbs).
- **II.11:** cross-subsystem reads only through declared SQL views — never raw tables.
- **II.6:** no DB I/O during tick; the read side is post-commit.
- **III.7:** determinism — the CLI re-exec seals `PYTHONHASHSEED=0` + thread pins before any client
  starts; the tick hash chain must not diverge.
- **III.11:** honest absence — absence renders loud, never fabricated.
- **III.12/III.13:** behavioral contracts (baselines, golden vault) are the durable spec;
  materializations are regenerable, never authoritative.
- **Amendment D caution:** hyperedge rendering is read-only; no affordances implying hyperedge
  mutation.
- **Amendment AA disclosure duty:** this ADR/amendment records a one-line Windows-impact note
  (see §10).
- **`ai/_inbox/post-v1.0.0/rasterizer.md` (pre-blessed port analysis):** "A ratatui client is
  correct iff the tutorial suite passes against it and the playthrough transcripts match." The
  vault bake stays Python-side; the Rust client reads baked markdown. Textual snapshot SVGs die
  with the client ("regenerate freely, never ceremony", ADR099).
- **Import-linter contracts** (`pyproject.toml`): `babylon.tui` must not import
  `babylon.engine`/`babylon.persistence`/django. The composition root (`cli/play.py`) is the only
  place all layers meet.
- **2026-07-22 extraction ruling:** Rust lives outside the babylon tree (sibling repos consumed as
  uv path-sources), per the hypergraph-rs precedent.

## 3. Decisions (owner-approved 2026-07-26)

| # | Question | Decision |
|---|----------|----------|
| D1 | Coexistence vs. replacement | **Full replacement with a constitutional amendment.** The Ratatui client becomes the designated terminal client; the Textual lane (app + ~100 Pilot tests + ~27 SVG snapshot goldens + Textual deps) is deleted in a declared cutover ceremony after parity. |
| D2 | Crate location | **New sibling repo `../babylon-tui-rs`** — own Cargo workspace, rust-toolchain pin 1.91.1 (matches hypergraph-rs), maturin root pyproject, own `mise run rust:check` gate. Consumed via `babylon-tui = { path = "../babylon-tui-rs" }` + opt-in dependency group. |
| D3 | FFI runtime shape | **Rust owns the loop.** Python builds `GameSession` as today, then calls `babylon_tui.run(host, config_json)`; Rust runs its native ratatui event loop, pulls frozen view-models across the FFI as JSON, and calls back into Python for `advance_tick()` / `issue_verb()` / view pulls. Python remains the single writer. |

Fact-check recorded during design: Ratatui has **no built-in 3D rasterizer**. The topology
rasterization effect is delivered via the sibling hypergraph-rs crate's `raster`/`cells3d`/
`raster-png` features (Rust-side 3D projection → colored cell grid) blitted onto a ratatui
`Canvas` (Braille/half-block/quadrant markers). This matches the rasterizer.md vision: "It could
even live inside hypergraph-rs as its rendering feature — graph layout *and* rasterization in one
deterministic Rust pass."

## 4. Governance artifacts (M0 deliverables)

- **Amendment AC — "The Raster Cutover"** (lettering subject to BD confirmation; AA ratified, AB
  held by the Material-Triad draft, T reserved by ADR072): designates the Rust/Ratatui client as
  the canonical terminal Archive client; retires the Textual implementation via the declared
  ceremony below; states the parity gate (tutorial-BDD suite + transcripts) as the blocking
  condition; carries the AA one-line Windows-impact note.
- **ADR139** — the recording ADR: context (this design), the three decisions, the FFI contract,
  milestone plan, risks, the cutover ceremony definition, and the Windows-impact line.
- The `tutorial_coverage` sentinel is re-pointed: every Rust binding must be exercised by a
  `TutorialStep` or carry a cited exemption (same law, new client).
- No engine/projection/game code changes → `mise run check` and `qa:regression` remain
  byte-identical for the entire program. Deletions land only in the M7 ceremony commit.

## 5. Repository layout (`../babylon-tui-rs`)

```
babylon-tui-rs/
├── Cargo.toml                  # workspace, resolver 2, rust-version = "1.85"
├── rust-toolchain.toml         # channel = "1.91.1", components rustfmt, clippy
├── pyproject.toml              # maturin backend; [tool.maturin] module-name = "babylon_tui._core",
│                               #   manifest-path = "crates/babylon-tui-python/Cargo.toml", python-source = "python"
├── python/babylon_tui/         # thin shell: loud-failure `from babylon_tui import _core`,
│                               #   re-exports, hand-written _core.pyi, py.typed
├── crates/
│   ├── babylon-tui/            # pure-Rust core: app state, views, markdown/wikilink parsing,
│   │                           #   JSON view-model types (serde), layout registry, reducers.
│   │                           #   Headless-testable; no pyo3, no terminal I/O above crossterm.
│   └── babylon-tui-python/     # cdylib, pyo3 0.29 extension-module — THIN FFI shell only:
│                               #   run(host, config_json), host-call bridges, GIL discipline.
└── .mise.toml                  # rust:check = fmt + clippy -D warnings + test + doc
```

Core dependencies (kept minimal): `ratatui = "0.30"`, `crossterm`, `serde`, `serde_json`,
`pulldown-cmark` (wiki markdown), `pyo3 = "0.29"` (binding crate only), `insta` (dev, snapshot
tests). Optional topology-raster lane: depend on hypergraph-rs's core crate (path dep) behind a
`raster` feature once its `cells3d` surface is confirmed (see §11 risk R3).

babylon-side wiring:

- `pyproject.toml`: `babylon-tui = { path = "../babylon-tui-rs" }` in `[tool.uv.sources]`; new
  opt-in `[dependency-groups] tui = ["babylon-tui"]` — **absent from default groups** (mirrors the
  `hypergraph` group doctrine: bare `uv sync`, CI, and the uv2nix player closure never build it).
- `tools/ci_hypergraph_stub.sh` generalized into per-sibling stubs (loop over siblings) so CI's
  frozen `uv lock --check` passes without the real checkout; stub metadata drift = loud failure.
- `uv lock` re-resolution run on the dev box (needs both siblings present).
- `flake.nix` unchanged (rustc/cargo already in the default devshell). The uv2nix `projectSrc`
  fileset exclusion pattern is extended to `babylon-tui-rs` if needed.
- Dev loop: `uv sync --group tui` builds once; after Rust edits, `uvx maturin develop` inside
  `../babylon-tui-rs` (uv does not rebuild path-source native modules on edit).
- Windows-impact note (Amendment AA duty): crossterm is the cross-platform backend and does not
  foreclose native Windows; kitty/TGP raster is absent from Windows Terminal, so the glyph floor
  (ADR099) remains the portability insurance — unchanged.

## 6. The FFI seam — `src/babylon/tui/` shrinks to a host adapter

The Python package keeps its name (so `cli/play.py` wiring, the import-linter contract, and the
WO-37 structural-typing trick survive), but all Textual widgets are replaced by one module:

```python
# src/babylon/tui/host.py — the only Python surface the Rust client ever sees.
# Structural mirror of CampaignHandle + PacedDriverHandle (tui/app.py today).
# Every pull returns a JSON STRING of a frozen view-model (II.8 shapes); no objects cross.
class RustClientHost:
    # --- lobby ---
    def lobby_catalog_json(self) -> str: ...          # CampaignCatalog rows
    # --- wiki / pages ---
    def read_page(self, subject: str) -> str | None: ...        # baked vault markdown; None = redlink
    def known_subjects_json(self) -> str: ...                   # frozenset[str] -> sorted list
    def backlinks_json(self, subject: str) -> str: ...
    # --- views ---
    def dashboard_view_json(self) -> str: ...           # EconomyView
    def subject_view_json(self, subject: str) -> str: ...       # ProjectionRecord (tagged union)
    def trend_json(self, last_n: int) -> str: ...               # v_national_trend rows (NationalTrendView)
    def choropleth_json(self, tier: str, lens: str) -> str: ... # ChoroplethCell[] (value|tension|fog)
    def topology_json(self, kind: str, focus: str | None) -> str: ...  # paoh|levi|incidence payloads
    def endgame_status_json(self) -> str: ...           # EndgameStatus (5 terminal-outcome axes)
    def verb_plate_view_json(self) -> str: ...          # VerbPlateView (9 Article-V verbs, OODA-gated)
    def tutorial_state_json(self) -> str: ...           # current step id, overlay_text, completion flags
    def watchlist_json(self) -> str: ...
    # --- verbs (Rust -> Python) ---
    def advance_tick(self) -> str: ...                  # TickOutcome JSON (tick, paused, chronicle)
    def issue_verb(self, action_id: str, target_id: str | None,
                   target_community: str | None) -> str: ...    # remaining actions / outcome JSON
    def pin_watchlist(self, subject: str, pinned: bool) -> None: ...
```

Entry point: `babylon_tui.run(host, config_json) -> None`, called from
`cli/play.py::run()` exactly where `ArchiveApp(...).run()` is called today. `config_json` carries:
campaign id, vault root, render tier (`glyph|pixel`, from the existing `--render` option), tutorial
enabled (tri-state resolved), narrator enabled, and the defines-hash/engine-version strings the
lobby displays today.

Rules of the seam:

- **JSON strings only across the FFI** (serde on the Rust side into typed view-models). The frozen
  Pydantic shapes are the contract; `model_dump_json()` on the Python side.
- **Callbacks only on the event-loop thread; GIL held** for every `host.*` call (pyo3
  `Python::with_gil`). No Rust worker threads touch Python.
- **Pull-on-render, not push:** each frame pulls only the visible view's data; `trend_json` pulls
  once per tick commit, not per frame.
- Determinism sealing (`PYTHONHASHSEED=0`, BLAS/rayon pins) happens in the CLI re-exec before Rust
  starts; Rust sets no Python env.
- The engine is never re-entered during a tick: `advance_tick()` runs the paced driver to the next
  pause/commit, then the read side unlocks (II.6).

## 7. Views (all live-data, all navigable, hover popups everywhere)

Global chrome: top bar with view tabs (Lobby/Wiki/Map/Topology/Market + page pane), chronicle
rail (right), watchlist rail, verb plate (bottom), fuzzy palette (`/`), tick controls
(`t` = step, `r` = run, `a` = acknowledge), jumplist (`Ctrl-O`/`Ctrl-I`, `[`/`]`), peek (`K` or
hover). Victoria-3 nested-view doctrine (R7); mouse + keyboard first-class (R3); honest absence
(III.11).

| View | Content & data source | Ratatui machinery |
|---|---|---|
| **Lobby** | Campaign catalog (BabylonMetaStore rows via host), new/resume | `List`, `Block`, `Clear` modal |
| **Wiki** | Baked vault markdown per known entity; `[[target\|alias]]` wikilinks → `babylon://` targets; redlinks; backlinks; concept cards; narrator blocks | `pulldown-cmark` + custom inline pass porting `tui/wikilinks.py` semantics; `Paragraph` with styled spans; link hit-registry for hover/click |
| **Map** | Live choropleth: county/state tiers from `v_hex_state_asof` (never raw `dynamic_hex_state` — spec-089 sparse-delta discipline); lenses **value \| tension \| fog**; zoom/pan; county WKT polygons from reference data via host | `Canvas` with `HalfBlock`/`Braille` markers; custom `Shape` impls for polygon fill + hex centroids; lens switcher keybindings |
| **Topology** | PAOH bars, Levi ego-tree, incidence matrix (existing `projection/topology/{paoh,levi,incidence}.py` payloads via host); **hypergraph 3D rasterization** — hypergraph-rs `cells3d`/`raster` projects the hypergraph to a colored cell grid, blitted to canvas; read-only (Amendment D) | `Canvas` custom `Shape`s; raster lane behind a feature flag with a 2D canvas fallback |
| **Stock Market** | `v_national_trend` series: imperial rent (+Δ), price⟷value scissors (price_log/fictitious_log + deltas), cumulative market corrections, total c/v/s, exploitation rate, profit rate; endgame axis bars (5 terminal outcomes) | `Chart` (Braille line datasets, dual-axis where needed), `Sparkline` strip, `BarChart`, `Gauge` for O=C/B overshoot |
| **Tutorial overlay** | `WAYNE_OPENING_ARC` steps verbatim; predicates polled via `tutorial_state_json()`; `escape` dismiss | `Clear` + bordered popup; predicate evaluation stays Python-side (`game/tutorial_runtime.py`) |
| **Hover popups** | Peek plates (depth 0–3, port of `peek.py` semantics) on mouse hover over any link/entity glyph; `K` keyboard equivalent | crossterm SGR mouse capture (`EnableMouseCapture`, motion events); per-frame retained layout-rect registry for hit-testing; `Clear` overlay |

## 8. Testing strategy

- **Rust core (headless):** unit tests for markdown/wikilink parsing, JSON view-model decoding,
  reducers, layout registry, hit-testing. `insta` snapshot tests over ratatui's `TestBackend`
  buffer → terminal-frame goldens (text-native, diffable — the rasterizer.md
  text-as-assertion-medium doctrine). Regenerate freely; never ceremony.
- **Tutorial-BDD harness (the constitutional rewrite test):** ported from
  `tui/shell/bdd/harness.py` + `tests/unit/tui/test_tutorial_pilot.py`; drives the Rust client
  headless (TestBackend + scripted input events) against a real `GameSession` over
  `WayneCountyScenario` through the actual PyO3 boundary. Parity condition (explicit): every
  `TutorialStep` predicate in the WAYNE arc evaluates complete in order under scripted input, and
  the recorded transcript (step sequence + per-step rendered frame captured from `TestBackend`)
  matches step-for-step — frame text is golden-tested per step, not byte-compared against the old
  Textual SVGs (those die with the client per ADR099 doctrine).
- **Python FFI contract tests (new lane `tests/unit/tui/`):** host adapter JSON shape per method
  (round-trip through `model_dump_json` → serde decode on a Rust test harness, or golden JSON
  files), verb round-trip (`issue_verb` decrements/actions), fog gating through the seam,
  `cli/play` wiring (mirrors today's `test_play.py`), `tutorial_runtime` predicate tests
  (unchanged).
- **Untouched lanes:** engine, projection, game, archive-integration goldens (vault byte-gate),
  `qa:regression` 6-scenario byte-identity, `check:gate-coverage` — all stay green; no engine-side
  change exists to move them.
- **Cutover ceremony (M7):** one declared commit — `test(cutover): retire Textual Archive lane` —
  deleting the Textual test files, `__snapshots__/`, Textual/textual-image/textual-plotext deps,
  and re-pointing the tutorial_coverage sentinel. Subject-to and body per the repo's ceremony
  discipline; baselines (`tests/baselines/**`) are NOT touched (no baseline ceremony needed).

## 9. Milestones (each leaves `mise run check` green)

- **M0 — Foundations.** Amendment AC + ADR139 drafted and ratified; sibling repo scaffold;
  rust-toolchain + mise gate green; uv path-source + dependency group + CI stub generalization +
  `uv lock`; `babylon_tui.run(host, config)` renders a hello-frame and exits clean; FFI round-trip
  test (host method ↔ JSON) green.
- **M1 — Read-only Archive.** Lobby → wiki view: markdown + wikilinks + redlinks, jumplist,
  backlinks, peek plates, palette, watchlist read. Snapshot goldens for each entity-kind page.
- **M2 — Playable.** Tick controls wired to the paced driver, chronicle rail, verb plate +
  `issue_verb` round-trip, watchlist pin writes, endgame HUD bars.
- **M3 — Tutorial gate.** Tutorial overlay + headless BDD harness; WAYNE arc passes against the
  Rust client; transcripts recorded. **← parity proven here; cutover unblocked.**
- **M4 — Maps.** Choropleth (county/state), three lenses, zoom/pan, hover peek on regions.
- **M5 — Topology.** PAOH, ego-tree, incidence matrix on canvas; hypergraph-rs `cells3d`/`raster`
  lane (feature-flagged, 2D fallback).
- **M6 — Stock Market.** Trend dashboards from `v_national_trend`; scissors chart; corrections
  counter; c/v/s + rates; endgame gauges.
- **M7 — Cutover ceremony.** Declared commit deleting the Textual lane + deps; sentinel re-pointed;
  `AGENTS.md`/`CLAUDE.md`, `ai/architecture.yaml`, `ai/state.yaml`, `ai/tooling.yaml` updated;
  docs (how-to + reference) revised; `mise run check` + `qa:regression` green post-delete.

Milestone ordering rationale: the constitutional correctness gate (M3) is placed **before** the
visual-heavy views so the cutover decision is de-risked early; M4–M6 are independently schedulable
and could be reordered without touching the gate.

## 10. Risks & mitigations

- **R1 — Markdown/wiki parity is the heaviest workstream.** The markdown-it-py fenced-directive
  pipeline dies with Textual and must be rebuilt in Rust. Mitigation: `pulldown-cmark` + a single
  custom inline pass for `[[wikilinks]]` + rendering directives as styled fenced blocks (the stack
  research already found container directives break terminal walkers — we keep fence-only);
  snapshot goldens per entity kind pin parity.
- **R2 — Hover hit-testing needs a retained layout registry.** Ratatui is immediate-mode; nothing
  retains rects. Mitigation: the core crate keeps a per-frame `LayoutRegistry` (widget id → rect →
  entity target); mouse motion events hit-test against it; keyboard `K` uses the same registry via
  focus. Standard pattern, but budget the fiddliness.
- **R3 — hypergraph-rs `cells3d`/`raster` maturity.** The 3D raster lane depends on the sibling's
  feature surface. Mitigation: feature-flag it; ship M5 with the 2D canvas renderers first (PAOH/
  ego-tree/matrix are 2D-native); the 3D raster is progressive enhancement, and hypergraph-rs is
  BD-owned so un-pausing is a one-line ruling (rasterizer.md governance note).
- **R4 — GIL/event-loop integration bugs** (callbacks off-thread, re-entrancy during tick).
  Mitigation: single-threaded event loop discipline in the binding crate; `advance_tick` is the
  only mutating call and is strictly serialized; FFI contract tests include a tick-under-render
  interleaving test.
- **R5 — Scope.** This is a multi-week program. Mitigation: milestone gates; M3 is the go/no-go;
  the Textual client remains the playable client until M7.

## 11. Open questions for the plan phase (none blocking)

- Exact `cells3d`/`raster` API surface in hypergraph-rs (to be read during M5 planning; fallback
  defined in R3).
- Whether the stock-market view wants dual-axis charts in-terminal or stacked single-axis
  (ratatui `Chart` supports one axis pair per widget; stacked is the terminal-idiomatic answer —
  default to stacked, revisit in M6).

## 12. References

- `CONSTITUTION.md` (v2.16.0; II.5/II.6/II.8/II.11/III.7/III.11/III.12/III.13; Amendments D, V, AA)
- `ai/_inbox/post-v1.0.0/rasterizer.md` — the pre-blessed port analysis (correctness gate quote)
- `ai/_inbox/tui/20260719archiveinterfacedesign.md` — R1–R8, S1–S11 (the Archive charter)
- `ai/_inbox/tui/20260719archivestackresearch.md` — stack research (fenced-directive finding)
- `src/babylon/tui/app.py` — `CampaignHandle`/`PacedDriverHandle` Protocols (the seam being mirrored)
- `src/babylon/cli/play.py` — composition root (`run()`, `_load_campaign`, `_driver_factory`)
- `src/babylon/game/session.py` — `GameSession` (host-side composer: `dashboard_view`,
  `subject_view`, `verb_plate_view`, `issue_verb`, `advance_tick`)
- `src/babylon/projection/` — view-models (`ProjectionRecord`, `NationalTrendView`),
  `registry.py` declared views (`v_national_trend`, `v_hex_state_asof`), `topology/{paoh,levi,
  incidence,choropleth}.py`, `epistemic_search.py`
- `src/babylon/game/tutorial.py`, `game/tutorial_runtime.py`, `tui/shell/bdd/harness.py` —
  tutorial-is-BDD machinery (the rewrite test)
- `pyproject.toml` `[tool.uv.sources]` + `hypergraph` dependency group — the Rust consumption
  precedent; `tools/ci_hypergraph_stub.sh` — the CI stub to generalize
- `/home/user/projects/game/hypergraph-rs` — workspace precedent; `raster`/`cells3d`/`raster-png`
  features for the topology raster lane
- Ratatui 0.30 docs (via context7): `Canvas`/`Shape`, `Chart`/`Sparkline`/`BarChart`/`Gauge`,
  `Tabs`, `Clear` (popups), crossterm mouse capture
