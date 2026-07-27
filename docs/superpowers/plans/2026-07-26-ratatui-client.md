# Ratatui Client (The Raster Cutover) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Textual ArchiveApp with a Rust/Ratatui terminal client (`babylon-tui-rs`, PyO3 extension) that passes the tutorial-BDD suite and ships lobby/wiki/map/topology/stock-market views with hover popups and live data.

**Architecture:** Rust owns the terminal event loop; Python (`GameSession`) remains the single writer and serves frozen view-models as JSON strings across a thin PyO3 seam (`RustClientHost`). Full design: `docs/superpowers/specs/2026-07-26-ratatui-client-design.md` (approved 2026-07-26).

**Tech Stack:** Rust 1.91.1 (MSRV 1.85), ratatui 0.30 (+ re-exported crossterm), serde/serde_json, pulldown-cmark, pyo3 0.29, maturin ≥1.14,<2, insta; Python 3.12, uv path-source + opt-in dependency group, pytest.

## Global Constraints

Every task implicitly includes ALL of the following (verbatim from the approved spec):

- **JSON strings only across the FFI** — `model_dump_json()` on Python, serde on Rust; no Python objects cross except the single `host` handle.
- **Callbacks only on the event-loop thread with the GIL held** (`Python::with_gil`); no Rust worker thread ever touches Python.
- **Determinism sealing happens in the CLI re-exec before Rust starts** (`PYTHONHASHSEED=0`, BLAS/rayon pins, `src/babylon/cli/__init__.py`); Rust sets no Python env.
- **No engine/projection/game code changes** anywhere in this program — `mise run check` and `mise run qa:regression` (byte-identical) must stay green after every task. `tests/baselines/**` are NEVER touched (no baseline ceremony applies).
- **Honest absence (III.11):** missing data renders as a loud absence state, never a fabricated default.
- **No LLM in the input path (II.5/R4):** verbs enter only via `host.issue_verb(...)`.
- **Read-only hyperedge rendering (Amendment D):** no UI affordance implying hyperedge mutation.
- **Import-linter:** `babylon.tui` must not import `babylon.engine`, `babylon.persistence`, or django (`mise run lint:imports`).
- **Rust pins:** `rust-toolchain.toml` channel `1.91.1`; workspace `rust-version = "1.85"`; `pyo3 = "0.29"`; `ratatui = "0.30"` (default features = crossterm backend — ALWAYS use `ratatui::crossterm` re-export, never a direct crossterm dep, to avoid version skew).
- **babylon-side Rust consumption is OPT-IN:** the `tui` dependency group must NOT be in any default-groups list (mirrors the `hypergraph` group doctrine); CI materializes a metadata-only stub instead of building Rust.
- **Commit discipline (babylon repo):** `mise run commit -- "type(scope): msg"`, conventional commits, `Co-Authored-By` trailer; never to `main`/`dev` directly — branch `feature/raster-cutover-*`. Sibling repo commits are plain `git commit` on its own `main` (no remote).
- **No `test_` prefix in production code; RST docstrings on Python public API; MyPy strict.**
- **Worktree gotcha:** the uv path source `../babylon-tui-rs` resolves relative to babylon's `pyproject.toml`; in `.claude/worktrees/<name>` checkouts, `ln -s /home/user/projects/game/babylon-tui-rs .claude/worktrees/babylon-tui-rs` before `uv lock/sync --group tui`.
- **Tutorial-is-BDD is the constitutional correctness gate:** M3 must pass before the M7 cutover; until M7 the Textual client remains the playable default.

## Program Map (milestones → plans)

| Milestone | Deliverable | Gate | Plan granularity |
|---|---|---|---|
| **M0 Foundations** | Sibling repo, uv wiring, `run(host, config)` hello-frame, FFI round-trip, Amendment AC + ADR139 | `mise run check` green; FFI test green | **Fully planned below (Tasks 1–10)** |
| **M1 Read-only Archive** | Lobby → wiki view, wikilinks, jumplist, peek, palette, watchlist read | Page snapshot goldens per entity kind | **Fully planned below (Tasks 11–20)** |
| **M2 Playable** | Tick controls, chronicle, verb plate, `issue_verb`, endgame HUD | Verb round-trip test | Task-level (Tasks 21–26) |
| **M3 Tutorial gate** | Tutorial overlay + headless BDD harness; WAYNE arc passes | **PARITY GATE — cutover unblocked** | Task-level (Tasks 27–29) |
| **M4 Maps** | Choropleth, lenses value/tension/fog, zoom/pan | Canvas snapshot goldens | Task-level (Tasks 30–33) |
| **M5 Topology** | PAOH, ego-tree, incidence matrix + hypergraph-rs raster lane | Topology goldens; feature-flagged 3D | Task-level (Tasks 34–37) |
| **M6 Stock Market** | `v_national_trend` dashboards, scissors chart, endgame gauges | Trend goldens | Task-level (Tasks 38–40) |
| **M7 Cutover ceremony** | Textual lane + deps deleted; docs updated | `mise run check` + `qa:regression` green post-delete | Task-level (Tasks 41–43) |

M2–M7 are planned at task level (files, exact interfaces, test names/assertions, acceptance
commands, commits). **At each milestone kickoff, expand its tasks into bite-sized red/green steps
via writing-plans before implementing** — interfaces below are the contract those expansions must
honor. M0/M1 need no expansion; they are executable as written.

---

# M0 — Foundations

## File structure (M0)

```
../babylon-tui-rs/                          # NEW sibling git repo
├── Cargo.toml                              # workspace
├── rust-toolchain.toml                     # 1.91.1 + rustfmt + clippy
├── pyproject.toml                          # maturin target for uv path-source
├── .mise.toml                              # rust:check gate
├── python/babylon_tui/{__init__.py,_core.pyi,py.typed}
└── crates/
    ├── babylon-tui/                        # core: config, app, headless run
    │   ├── Cargo.toml
    │   └── src/{lib.rs,config.rs,app.rs}
    └── babylon-tui-python/                 # cdylib FFI shell
        ├── Cargo.toml
        └── src/lib.rs

babylon/                                    # THIS repo (branch feature/raster-cutover-m0)
├── CONSTITUTION.md                         # Amendment AC appended
├── ai/decisions/ADR139_raster_cutover.yaml + index.yaml
├── pyproject.toml                          # [tool.uv.sources] + [dependency-groups] tui
├── tools/ci_hypergraph_stub.sh             # generalized → per-sibling loop
├── uv.lock                                 # regenerated on dev box
├── src/babylon/tui/host.py                 # RustClientHost (M0 surface: lobby)
├── tests/unit/tui/test_rust_client_ffi.py  # FFI round-trip contract test
└── src/babylon/cli/play.py                 # --client textual|rust option (default textual)
```

### Task 1: Sibling repo scaffold

**Files:**
- Create: `../babylon-tui-rs/Cargo.toml`, `rust-toolchain.toml`, `.gitignore`, `.mise.toml`

**Interfaces:**
- Produces: cargo workspace `babylon-tui-rs` with members `crates/babylon-tui`, `crates/babylon-tui-python`; `mise run rust:check` task (fmt + `clippy -D warnings` + test + doc), mirroring `/home/user/projects/game/hypergraph-rs/.mise.toml`.

- [ ] **Step 1: Init the repo**

```bash
mkdir -p /home/user/projects/game/babylon-tui-rs/crates
cd /home/user/projects/game/babylon-tui-rs && git init -b main
```

- [ ] **Step 2: Write `Cargo.toml`**

```toml
[workspace]
members = ["crates/babylon-tui", "crates/babylon-tui-python"]
resolver = "2"

[workspace.package]
version = "0.1.0"
edition = "2021"
rust-version = "1.85"
license = "BSD-3-Clause"
```

- [ ] **Step 3: Write `rust-toolchain.toml`**

```toml
[toolchain]
channel = "1.91.1"
components = ["rustfmt", "clippy"]
```

- [ ] **Step 4: Write `.gitignore` (`/target`, `/dist`, `*.whl`, `__pycache__/`) and `.mise.toml` with a `rust:check` task running `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test && cargo doc --no-deps`; copy the task shape from `/home/user/projects/game/hypergraph-rs/.mise.toml`.**

- [ ] **Step 5: Commit**

```bash
cd /home/user/projects/game/babylon-tui-rs && git add -A && git commit -m "chore: workspace scaffold"
```

### Task 2: Core crate — config + headless hello app (TDD)

**Files:**
- Create: `crates/babylon-tui/Cargo.toml`, `src/lib.rs`, `src/config.rs`, `src/app.rs`, `tests/hello_frame.rs`

**Interfaces:**
- Produces (relied on by Tasks 3, 5, and all M1+ tasks):
  - `babylon_tui::config::AppConfig` — `pub struct AppConfig { pub campaign_id: String, pub campaign_name: String, pub render_tier: RenderTier, pub tutorial_enabled: bool, pub narrator_enabled: bool, pub headless: bool }`; `RenderTier { Glyph, Pixel }`; `impl AppConfig { pub fn from_json(s: &str) -> Result<Self, ConfigError> }`.
  - `babylon_tui::app::App<H: Host>` — `pub fn new(cfg: AppConfig, host: H) -> Self`; `pub fn render_frame<B: ratatui::backend::Backend>(&self, terminal: &mut Terminal<B>) -> std::io::Result<()>`.
  - `babylon_tui::host::Host` (trait) — M0 surface: `fn lobby_catalog_json(&self) -> String`.

- [ ] **Step 1: Write `crates/babylon-tui/Cargo.toml`**

```toml
[package]
name = "babylon-tui"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true

[dependencies]
ratatui = "0.30"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"

[dev-dependencies]
insta = { version = "1", features = ["filters"] }
```

- [ ] **Step 2: Write the failing config test (`src/config.rs` test module)**

```rust
#[test]
fn parses_minimal_config() {
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne","render_tier":"glyph",
            "tutorial_enabled":true,"narrator_enabled":false}"#,
    )
    .unwrap();
    assert_eq!(cfg.campaign_name, "Wayne");
    assert_eq!(cfg.render_tier, RenderTier::Glyph);
    assert!(!cfg.headless); // default false
}

#[test]
fn rejects_bad_tier() {
    assert!(AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"W","render_tier":"3d",
            "tutorial_enabled":false,"narrator_enabled":false}"#
    )
    .is_err());
}
```

- [ ] **Step 3: `cargo test -p babylon-tui` → FAIL (no such item). Implement `src/config.rs` (serde derive, `#[serde(default)]` on `headless`, `#[serde(rename_all = "lowercase")]` on `RenderTier`) and `src/lib.rs` (`pub mod app; pub mod config; pub mod host;`) + `src/host.rs` (`pub trait Host { fn lobby_catalog_json(&self) -> String; }`). `cargo test` → PASS.**

- [ ] **Step 4: Write the failing hello-frame snapshot test (`tests/hello_frame.rs`)**

```rust
use babylon_tui::{app::App, config::AppConfig, host::Host};
use ratatui::{backend::TestBackend, Terminal};

struct FakeHost;
impl Host for FakeHost {
    fn lobby_catalog_json(&self) -> String {
        r#"[{"campaign_id":"c1","name":"Wayne County","tick":0}]"#.to_string()
    }
}

#[test]
fn hello_frame_shows_campaign() {
    let cfg = AppConfig::from_json(
        r#"{"campaign_id":"c1","campaign_name":"Wayne County","render_tier":"glyph",
            "tutorial_enabled":false,"narrator_enabled":false,"headless":true}"#,
    )
    .unwrap();
    let app = App::new(cfg, FakeHost);
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();
    app.render_frame(&mut terminal).unwrap();
    let buffer = terminal.backend().buffer().clone();
    insta::assert_snapshot!(format!("{:?}", buffer));
}
```

- [ ] **Step 5: `cargo test -p babylon-tui --test hello_frame` → FAIL. Implement `src/app.rs`: parse `host.lobby_catalog_json()` (serde_json into `Vec<LobbyRow>`, honest-absence paragraph when empty), render a `Block::bordered().title("The Archive — <campaign_name>")` + the campaign list via `ratatui::widgets::List`. `cargo insta review` (or `INSTA_UPDATE=always cargo test` once) to bless, then `cargo test` → PASS.**

- [ ] **Step 6: `mise run rust:check` green. Commit:**

```bash
git add -A && git commit -m "feat(core): config + headless hello-frame with snapshot"
```

### Task 3: PyO3 binding crate — `run(host, config_json)` with headless mode

**Files:**
- Create: `crates/babylon-tui-python/Cargo.toml`, `src/lib.rs`
- Create: `python/babylon_tui/__init__.py`, `python/babylon_tui/_core.pyi`, `python/babylon_tui/py.typed`
- Create: `pyproject.toml` (repo root, maturin target)

**Interfaces:**
- Produces (relied on by babylon Tasks 8–10 and ALL later milestones):
  - Python: `babylon_tui.run(host: Any, config_json: str) -> str` — runs the client; **returns a JSON transcript string** `{"frames": [<buffer text>...], "host_calls": [<method name>...]}`. In `headless: true` configs it renders one frame to `TestBackend` and returns immediately (no terminal I/O) — this is the CI-testable path.
  - Rust side: `PyHost` implements `babylon_tui::host::Host` by calling `host.<method>()` via `Python::with_gil` and recording each call name in a `Vec<String>` that becomes `host_calls`.

- [ ] **Step 1: Write `crates/babylon-tui-python/Cargo.toml`**

```toml
[package]
name = "babylon-tui-python"
version.workspace = true
edition.workspace = true
rust-version.workspace = true
license.workspace = true

[lib]
name = "_core"
crate-type = ["cdylib"]

[dependencies]
babylon-tui = { path = "../babylon-tui" }
pyo3 = { version = "0.29", features = ["extension-module"] }
serde_json = "1"
```

- [ ] **Step 2: Write the failing Python-side round-trip test FIRST (in babylon, red phase): `tests/unit/tui/test_rust_client_ffi.py`**

```python
"""FFI contract: babylon_tui.run drives a headless frame and records host calls."""

from __future__ import annotations

import json

import babylon_tui


class _FakeHost:
    def lobby_catalog_json(self) -> str:
        return json.dumps([{"campaign_id": "c1", "name": "Wayne County", "tick": 0}])


def test_run_headless_renders_and_records_calls() -> None:
    transcript = json.loads(
        babylon_tui.run(
            _FakeHost(),
            json.dumps(
                {
                    "campaign_id": "c1",
                    "campaign_name": "Wayne County",
                    "render_tier": "glyph",
                    "tutorial_enabled": False,
                    "narrator_enabled": False,
                    "headless": True,
                }
            ),
        )
    )
    assert "lobby_catalog_json" in transcript["host_calls"]
    assert "Wayne County" in transcript["frames"][0]
```

- [ ] **Step 3: Run in babylon (`mise run test:q -- tests/unit/tui/test_rust_client_ffi.py`) → FAIL (`ModuleNotFoundError: babylon_tui`).**

- [ ] **Step 4: Implement `crates/babylon-tui-python/src/lib.rs`**

```rust
use babylon_tui::{app::App, config::AppConfig, host::Host};
use pyo3::prelude::*;
use ratatui::{backend::TestBackend, Terminal};

struct PyHost {
    obj: Py<PyAny>,
    calls: std::cell::RefCell<Vec<String>>,
}

impl Host for PyHost {
    fn lobby_catalog_json(&self) -> String {
        self.calls.borrow_mut().push("lobby_catalog_json".into());
        Python::with_gil(|py| {
            self.obj
                .call_method0(py, "lobby_catalog_json")
                .and_then(|v| v.extract::<String>(py))
                .unwrap_or_else(|_| "[]".into()) // honest absence: empty catalog
        })
    }
}

#[pyfunction]
fn run(py: Python<'_>, host: Py<PyAny>, config_json: &str) -> PyResult<String> {
    let cfg = AppConfig::from_json(config_json)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let py_host = PyHost { obj: host, calls: vec![].into() };
    let app = App::new(cfg.clone(), py_host);
    py.allow_threads(|| {
        if cfg.headless {
            let mut t = Terminal::new(TestBackend::new(80, 24)).unwrap();
            app.render_frame(&mut t).unwrap();
            let frame = format!("{:?}", t.backend().buffer());
            let calls = app.host_calls();
            Ok(serde_json::json!({"frames": [frame], "host_calls": calls}).to_string())
        } else {
            babylon_tui::app::run_interactive(app) // M0: same frame + quit on q/Esc
                .map(|calls| serde_json::json!({"frames": [], "host_calls": calls}).to_string())
                .map_err(|e| e.to_string())
        }
    })
    .map_err(pyo3::exceptions::PyRuntimeError::new_err)
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run, m)?)
}
```

(`App` gains `fn host_calls(&self) -> Vec<String>` in the core crate; `run_interactive` does crossterm init → same render → poll for `q`/`Esc` → restore → return calls. Add both with their own red/green steps.)

- [ ] **Step 5: Write the maturin `pyproject.toml` (root) and Python shell**

```toml
[build-system]
requires = ["maturin>=1.14,<2.0"]
build-backend = "maturin"

[project]
name = "babylon-tui"
dynamic = ["version"]
dependencies = []

[tool.maturin]
manifest-path = "crates/babylon-tui-python/Cargo.toml"
module-name = "babylon_tui._core"
python-source = "python"
strip = true
```

```python
# python/babylon_tui/__init__.py
"""Babylon Archive client (Rust/Ratatui). Loud-failure import doctrine."""
from babylon_tui import _core as _core

run = _core.run

__all__ = ["run"]
```

`_core.pyi`: `def run(host: object, config_json: str) -> str: ...`; empty `py.typed`.

- [ ] **Step 6: `uvx maturin develop` in `../babylon-tui-rs` (with babylon's venv active after Task 4 wiring) → build green. Re-run the Step-2 pytest → PASS. `mise run rust:check` green. Commit sibling: `feat(ffi): run(host, config_json) with headless transcript`.**

### Task 4: babylon uv wiring + CI stub generalization

**Files:**
- Modify: `pyproject.toml` (`[tool.uv.sources]`, `[dependency-groups]`)
- Modify: `tools/ci_hypergraph_stub.sh` → generalized per-sibling loop (keep filename + behavior for hypergraph; add babylon-tui-rs)
- Modify: `uv.lock` (via `uv lock` on dev box)

**Interfaces:**
- Produces: `uv sync --group tui` builds the extension into the venv; bare `uv sync` and CI never build it.

- [ ] **Step 1: Add to babylon `pyproject.toml`**

```toml
# In [tool.uv.sources], after the hypergraph-rs entry:
babylon-tui = { path = "../babylon-tui-rs" }

# In [dependency-groups], after the hypergraph group (same opt-in doctrine —
# absent from default-groups; enable with `uv sync --group tui`; after Rust
# edits run `uvx maturin develop` in ../babylon-tui-rs):
tui = [
    "babylon-tui",
]
```

- [ ] **Step 2: Generalize `tools/ci_hypergraph_stub.sh`**: loop over `hypergraph-rs babylon-tui-rs`; for each, if `../$sibling/pyproject.toml` is absent, materialize the metadata-only stub (`name` matching the dist — `hypergraph-rs` / `babylon-tui`, `dynamic = ["version"]`, hatchling). Update the script's header comment; update every CI caller only if the script path changes (it doesn't).

- [ ] **Step 3: `uv lock` (dev box, both siblings present) then `uv sync --group tui && uvx maturin develop` in the sibling; verify `python -c "import babylon_tui; print(babylon_tui.run)"` in the venv.**

- [ ] **Step 4: Run the red test from Task 3 Step 2 → now PASS. Run `mise run check` → green.**

- [ ] **Step 5: Commit (babylon): `mise run commit -- "build(tui): consume babylon-tui-rs as opt-in uv path source"`.**

### Task 5: `RustClientHost` M0 surface + contract test

**Files:**
- Create: `src/babylon/tui/host.py`
- Test: `tests/unit/tui/test_host_contract.py`

**Interfaces:**
- Consumes: `GameSession`-shaped objects and the lobby catalog (`BabylonMetaStore`), exactly as `cli/play.py` already composes them.
- Produces (THE seam; grows per milestone — signatures binding for M1–M6):
  - `RustClientHost(catalog: CampaignCatalog, *, defines_hash: str, engine_version: str)`
  - `lobby_catalog_json() -> str` (M0, real)
  - `bind_session(session: GameSession, driver: PacedDriverHandle) -> None` (M0, real)
  - M1+: `read_page(subject) -> str | None`, `known_subjects_json() -> str`, `backlinks_json(subject) -> str`, `subject_view_json(subject) -> str`
  - M2+: `advance_tick() -> str`, `issue_verb(action_id, target_id=None, target_community=None) -> str`, `verb_plate_view_json() -> str`, `endgame_status_json() -> str`, `pin_watchlist(subject, pinned) -> None`, `watchlist_json() -> str`
  - M3: `tutorial_state_json() -> str`
  - M4: `choropleth_json(tier, lens) -> str`
  - M5: `topology_json(kind, focus=None) -> str`
  - M6: `trend_json(last_n) -> str`, `dashboard_view_json() -> str`

- [ ] **Step 1: Failing test `tests/unit/tui/tui/test_host_contract.py` — construct `RustClientHost` over `InMemoryCampaignCatalog` (import from `babylon.tui.campaign_menu`), assert `json.loads(host.lobby_catalog_json())` round-trips the catalog rows and `defines_hash` appears. Run → FAIL.**

- [ ] **Step 2: Implement `src/babylon/tui/host.py` — frozen-dataclass-free thin adapter; RST docstrings; MyPy-strict; every `*_json` method returns `model_dump_json()` or `json.dumps` of primitives; honest absence = `None`/empty list, never fabricated rows. Run → PASS. `mise run check` green.**

- [ ] **Step 3: Commit: `mise run commit -- "feat(tui): RustClientHost seam (M0 lobby surface)"`.**

### Task 6: `cli/play.py --client` wiring

**Files:**
- Modify: `src/babylon/cli/play.py` (`run()` signature + ArchiveApp/Rust branch)
- Test: `tests/unit/cli/test_play.py` (extend existing patterns)

**Interfaces:**
- Produces: `babylon play --client textual|rust` (default `textual` until M7). The rust branch: build catalog + `RustClientHost`, `host.bind_session(...)` inside `campaign_loader`, then `babylon_tui.run(host, config_json)` where `ArchiveApp(...).run()` is called today. Import of `babylon_tui` is lazy (inside the branch) so the opt-in group stays opt-in.

- [ ] **Step 1: Failing test — `--client rust` without the extension installed raises a loud, actionable `RuntimeError` (red).**

- [ ] **Step 2: Implement the option + lazy import + branch (green). `--client textual` path byte-identical to today.**

- [ ] **Step 3: `mise run check` + `mise run qa:regression` green (no engine change; prove it).**

- [ ] **Step 4: Commit: `mise run commit -- "feat(cli): --client rust lane behind opt-in group"`.**

### Task 7: Amendment AC + ADR139 (governance, drafting task)

**Files:**
- Modify: `CONSTITUTION.md` (append Amendment AC; bump version note)
- Create: `ai/decisions/ADR139_raster_cutover.yaml`
- Modify: `ai/decisions/index.yaml`

**Interfaces:**
- Produces: ratified designation of the Rust client as canonical; the M3 parity gate and M7 ceremony as binding text; the AA one-line Windows-impact note ("crossterm does not foreclose native Windows; the glyph floor (ADR099) remains the portability insurance; kitty raster is absent from Windows Terminal").

- [ ] **Step 1: Draft Amendment AC text (title "The Raster Cutover"; lettering: AC proposed — AB held by the Material-Triad draft, T reserved by ADR072; final letter is the BD's call). Operative clauses: (i) the Rust/Ratatui client in `../babylon-tui-rs` is the designated successor terminal client under II.8/Amendment V's unchanged contract; (ii) the Textual implementation retires ONLY via the declared M7 ceremony, blocked on the M3 tutorial-BDD parity gate; (iii) the tutorial-BDD suite passing against the Rust client is the constitutional correctness test; (iv) clients remain disposable — this designates an implementation, not a new primitive.**

- [ ] **Step 2: Draft ADR139 YAML (status: proposed → accepted on BD ruling; context = the design doc; decisions D1–D3 verbatim; milestone table; risks R1–R5). Register in `index.yaml`.**

- [ ] **Step 3: Present both to the BD for ratification. Commit: `mise run commit -- "docs(governance): Amendment AC + ADR139 (raster cutover)"`.**

### Tasks 8–10: M0 close-out

- [ ] **Task 8:** Sibling `mise run rust:check` + babylon `mise run check` + `mise run qa:regression` all green; record outputs in the PR description. Commit any stragglers.
- [ ] **Task 9:** Update `ai/state.yaml` (program state: raster cutover M0 done); one-line `AGENTS.md` note that the Rust client lane exists behind `--client rust` + `--group tui`. Commit: `docs(state): raster cutover M0`.
- [ ] **Task 10:** Manual smoke: `babylon play --client rust` (real terminal, Postgres up via the normal runtime) → hello-frame renders the real lobby catalog; `q` quits clean. Record the transcript JSON in the milestone notes.

---

# M1 — Read-only Archive

## File structure (M1)

```
crates/babylon-tui/src/
├── markdown.rs        # pulldown-cmark -> ratatui Text, styled spans
├── wikilinks.rs       # [[target|alias]] inline pass -> LinkSpan + LinkRegistry
├── router.rs          # babylon:// URI parsing (port of tui/router.py semantics)
├── layout_registry.rs # per-frame widget id -> Rect -> entity target (hover/peek foundation)
├── views/{lobby.rs,wiki.rs,palette.rs,watchlist.rs,peek.rs}
└── app.rs             # gains: view stack, jumplist, key/mouse routing
```

### Task 11: Markdown renderer (TDD)

**Files:** Create `crates/babylon-tui/src/markdown.rs`, `tests/markdown.rs`

**Interfaces:** Produces `pub fn render_markdown(src: &str, width: u16) -> ratatui::text::Text<'static>` — headings bold, code spans cyan, **fenced blocks rendered as styled blocks** (the stack-research fence-only rule; NO container directives), honest absence for empty input (renders `"(absent)"` dim).

- [ ] Steps: failing tests (heading style, fence block, empty→absent, hard wrap at width) → implement with pulldown-cmark `Parser` → `Text`/`Line`/`Span` assembly → insta snapshots per fixture in `tests/fixtures/markdown/*.md` → `mise run rust:check` → commit `feat(core): markdown renderer`.

### Task 12: Wikilink inline pass (TDD)

**Files:** Create `crates/babylon-tui/src/wikilinks.rs`, `tests/wikilinks.rs`

**Interfaces:** Produces `pub struct LinkSpan { pub line: u16, pub start: u16, pub end: u16, pub target: String, pub alias: Option<String>, pub exists: bool }` and `pub fn extract_wikilinks(src: &str, known: &BTreeSet<String>) -> (String, Vec<LinkSpan>)` — strips `[[target|alias]]` to display text, emits spans with `exists=false` → redlink style. Semantics ported from `src/babylon/tui/wikilinks.py` (read it first; match its edge cases: bare `[[t]]`, aliased, unknown target).

- [ ] Steps: failing tests mirroring `tests/unit/tui/test_wikilinks.py` cases (port the table) → implement → commit `feat(core): wikilink inline pass (babylon:// targets, redlinks)`.

### Task 13: Router (TDD)

**Files:** Create `crates/babylon-tui/src/router.rs`, `tests/router.rs`

**Interfaces:** Produces `pub enum BabylonTarget { Entity(String), Kind { kind: String, id: String }, Redlink(String) }` and `pub fn parse_babylon_uri(uri: &str) -> Result<BabylonTarget, RouterError>` — `babylon://<kind>/<id>`, `babylon://<id>`, `babylon://redlink/<id>`. Port the case table from `tests/unit/tui/test_router.py` verbatim.

- [ ] Steps: red (ported cases) → green → commit `feat(core): babylon:// router`.

### Task 14: Layout registry + hover/peek foundation (TDD)

**Files:** Create `crates/babylon-tui/src/layout_registry.rs`, `src/views/peek.rs`, `tests/layout_registry.rs`

**Interfaces:** Produces `pub struct LayoutRegistry { rects: Vec<(WidgetId, Rect, Option<String>)> }` with `pub fn register(&mut self, id: WidgetId, area: Rect, entity: Option<String>)` and `pub fn hit(&self, col: u16, row: u16) -> Option<&(WidgetId, Rect, Option<String>)>`; `App::handle_mouse(MouseEvent)` → on `Moved`, `hit()` → set `peek_target: Option<String>`; `views/peek.rs::render_peek(frame, area, subject_view_json, depth)` rendering depths 0–3 (port depth semantics from `src/babylon/tui/peek.py`).

- [ ] Steps: failing hit-test unit tests (nested rects → innermost wins; miss → None) → implement → commit `feat(core): layout registry + hover peek foundation`.

### Task 15: WikiView (TDD)

**Files:** Create `crates/babylon-tui/src/views/wiki.rs`, `tests/wiki_view.rs`

**Interfaces:** Consumes Tasks 11–14 + host `read_page`/`known_subjects_json`. Produces `pub struct WikiView { current: Option<String>, jumplist: Vec<String>, jumplist_idx: usize }` with `pub fn open(&mut self, target: &BabylonTarget, host: &dyn Host)` — redlink target renders the honest-absence page; `Ctrl-O`/`Ctrl-I` and `[`/`]` traverse the jumplist. Rendering pipeline: `read_page` → `extract_wikilinks` → `render_markdown` → link spans registered into `LayoutRegistry` (hover/click navigates; hover peeks).

- [ ] Steps: failing snapshot tests (entity page with links; redlink page; jumplist back/forward across 3 pages) → implement → commit `feat(core): wiki view with jumplist navigation`.

### Task 16: LobbyView (TDD)

**Files:** Create `crates/babylon-tui/src/views/lobby.rs`, `tests/lobby_view.rs`

**Interfaces:** Consumes `host.lobby_catalog_json()`. Produces `pub struct LobbyView { rows: Vec<LobbyRow>, selected: usize }`; `Enter` on a row → `AppEvent::LoadCampaign(Uuid)`; `n` → `AppEvent::NewCampaign`. Empty catalog → honest-absence body. Mirrors `campaign_menu.py` display fields (name, tick, engine version, defines hash).

- [ ] Steps: failing snapshot tests (populated, empty, selection move) → implement → commit `feat(core): lobby view`.

### Task 17: Host M1 surface (Python, TDD)

**Files:** Modify `src/babylon/tui/host.py`; Test `tests/unit/tui/test_host_contract.py` (extend)

**Interfaces:** Implements `read_page(subject) -> str | None` (delegates to the vault read path `GameSession.read_page`/materializer read — read-only, never bakes), `known_subjects_json() -> str` (sorted list from `known_subjects()`), `backlinks_json(subject) -> str` (from the vault backlink index), `subject_view_json(subject) -> str` (`GameSession.subject_view` → `model_dump_json`).

- [ ] Steps: failing contract tests (round-trip a `CountyView` fixture through `subject_view_json` and assert the JSON decodes with the expected tag; unknown subject → `None`) → implement → `mise run check` → commit `feat(tui): host M1 read surface`.

### Task 18: Palette + watchlist read (TDD)

**Files:** Create `crates/babylon-tui/src/views/palette.rs`, `src/views/watchlist.rs`, tests

**Interfaces:** Palette: `/` opens fuzzy input over `known_subjects_json`; `Enter` → `open()`. Watchlist rail: renders `watchlist_json()` rows; click/`p` navigation. (Pin WRITES land in M2 Task 25.)

- [ ] Steps: failing snapshot tests → implement → commit `feat(core): palette + watchlist read view`.

### Task 19: App shell integration — view stack + key/mouse routing (TDD)

**Files:** Modify `crates/babylon-tui/src/app.rs`, `crates/babylon-tui-python/src/lib.rs`; tests

**Interfaces:** `App` gains `view_stack: Vec<View>` (Lobby root), global bindings (tab/`1`–`5` view switch scaffold, `q` back/quit, `K` peek, `/` palette), crossterm mouse capture enabled in `run_interactive`, `handle_mouse` wired to `LayoutRegistry`. Headless mode gains scripted-input replay: `config_json` accepts `"script": [{"key": "..."}, {"mouse": [c, r]}...]` so integration tests drive flows without a terminal (this is the BDD harness foundation M3 builds on).

- [ ] Steps: failing scripted-input integration test (lobby → open campaign page → back → quit; assert transcript frame count + host call order) → implement → `mise run rust:check` + babylon `mise run check` → commit `feat(core): app shell — view stack, global keys, mouse, scripted-input headless`.

### Task 20: M1 close-out

- [ ] Both gates green; manual smoke `babylon play --client rust` browses the REAL vault for a live campaign; `ai/state.yaml` updated; commit `docs(state): raster cutover M1`.

---

# M2 — Playable (task-level; expand at kickoff)

- [ ] **Task 21 — Tick controls.** Rust: `t`/`r`/`a` bindings → `host.advance_tick()` (step), run-until-paused loop flag, acknowledge. Python: `advance_tick()` delegates to the paced driver → `TickOutcome` JSON (`tick`, `paused`, `chronicle: [...]`). Tests: Rust scripted-input tick test with a fake host; Python contract test over `tests/unit/game/test_pacing.py` fixture shapes. Commit `feat(tui): tick controls`.
- [ ] **Task 22 — Chronicle rail.** Renders `TickOutcome.chronicle` (port salience/dedupe display rules from `tui/chronicle_salience.py` as DATA the host ships pre-computed — Rust stays dumb; do NOT port salience logic). Snapshot goldens. Commit `feat(core): chronicle rail`.
- [ ] **Task 23 — Verb plate + issue_verb.** Renders `verb_plate_view_json()` (9 Article-V verbs, OODA-gated disabled states); F1–F9 + click dispatch → `host.issue_verb(action_id, target_id, target_community)` → re-render. Tests: round-trip contract test (verb decrements remaining actions, mirrors `tests/integration/archive/test_verb_resolution.py` shapes at unit level); scripted-input verb dispatch test. Commit `feat(tui): verb plate + dispatch`.
- [ ] **Task 24 — Endgame HUD.** 5 terminal-outcome axis bars from `endgame_status_json()` (`Gauge`/`BarChart`); honest absence pre-game. Commit `feat(core): endgame HUD`.
- [ ] **Task 25 — Watchlist writes.** `p` pin/unpin → `pin_watchlist(subject, pinned)` → `BabylonMetaStore` persistence; rail re-renders. Contract test round-trip. Commit `feat(tui): watchlist pin writes`.
- [ ] **Task 26 — M2 close-out.** Gates green; manual smoke plays 5 real ticks with one real verb; `ai/state.yaml`. Commit `docs(state): raster cutover M2`.

# M3 — Tutorial gate (task-level; expand at kickoff) — **PARITY GATE**

- [ ] **Task 27 — Tutorial overlay.** `tutorial_state_json()` (current step id, `overlay_text`, per-predicate completion) polled per frame; `Clear`+popup render; `escape` dismiss. Python: adapter over `game/tutorial_runtime.py::TutorialRuntimeProgress` (predicates stay Python — Rust never evaluates them). Snapshot goldens per overlay fixture. Commit `feat(tui): tutorial overlay`.
- [ ] **Task 28 — Headless BDD harness.** Port `tui/shell/bdd/harness.py` semantics: a Python pytest harness (`tests/unit/tui/test_tutorial_pilot_rs.py`) that builds a real `GameSession` over `WayneCountyScenario`, wraps it in `RustClientHost`, feeds each `TutorialStep`'s `when` as scripted input through `babylon_tui.run(..., headless, script=...)`, and asserts each `then` predicate completes **in order**; records the transcript (step sequence + per-step `TestBackend` frame) to `tests/unit/tui/transcripts/wayne_opening_arc.json` (golden, regenerate-freely doctrine).
- [ ] **Task 29 — Gate run.** The full WAYNE arc passes against the Rust client; transcript blessed; results appended to ADR139 (status note: parity PROVEN, cutover unblocked). Commit `test(tutorial): WAYNE arc green against Rust client — parity gate`.

# M4 — Maps (task-level; expand at kickoff)

- [ ] **Task 30 — Choropleth host surface.** `choropleth_json(tier, lens)` over `projection/topology/choropleth_aggregation.py` (reads `v_hex_state_asof` ONLY — spec-089 discipline) + county WKT polygons from the reference read path; `MapTier = county|state`, `lens = value|tension|fog`. Contract tests with fixture cells. Commit `feat(tui): choropleth host surface`.
- [ ] **Task 31 — MapView canvas.** `Canvas` + `HalfBlock` marker; custom `Shape` impl filling WKT polygons colored by lens band (port band thresholds from `tui/map_room.py::_band_color` as host-shipped data — bands are DATA, not Rust literals); centroid dots for hexes. Snapshot goldens per lens. Commit `feat(core): map view canvas`.
- [ ] **Task 32 — Lenses + zoom/pan.** `1/2/3` lens switch; `+`/`-`/arrow pan & zoom (x/y bounds math); hover → region peek (LayoutRegistry entity = region_id). Tests. Commit `feat(core): map lenses + viewport`.
- [ ] **Task 33 — M4 close-out.** Gates; smoke on tri-county; `ai/state.yaml`.

# M5 — Topology (task-level; expand at kickoff)

- [ ] **Task 34 — Topology host surface.** `topology_json(kind, focus)` → `projection/topology/{paoh,levi,incidence}.py` payloads as JSON. Contract tests. Commit `feat(tui): topology host surface`.
- [ ] **Task 35 — 2D renderers.** PAOH bars (`BarChart`/canvas), Levi ego-tree (canvas `Line`/`Points` layout — layout computed Rust-side, deterministic), incidence matrix (cell grid). Goldens per fixture (port `test_egotree_directive.py`/`test_matrix_directive.py` fixtures). Commit `feat(core): topology 2D views`.
- [ ] **Task 36 — Hypergraph raster lane (feature `raster`).** Path-dep on hypergraph-rs core; `cells3d`/`raster` project the hypergraph → colored cell grid → blit to canvas. **Read hypergraph-rs's actual API at kickoff; if the surface isn't ready, ship Task 35 only and record the deferral in ADR139 (risk R3).** Goldens (deterministic raster = text-assertable, the rasterizer.md thesis). Commit `feat(core): hypergraph 3D raster lane`.
- [ ] **Task 37 — M5 close-out.** Gates; smoke; `ai/state.yaml`.

# M6 — Stock Market (task-level; expand at kickoff)

- [ ] **Task 38 — Trend host surface.** `trend_json(last_n)` reads declared view `v_national_trend` (NEVER raw `tick_summary` — II.11) → `NationalTrendView` rows; `dashboard_view_json()` → `EconomyView`. Contract tests over `tests/unit/projection/test_registry.py` fixture shapes. Commit `feat(tui): trend host surface`.
- [ ] **Task 39 — Market dashboards.** Stacked single-axis `Chart`s (terminal-idiomatic, per design §11): imperial rent (+Δ), price⟷value scissors (`price_log` vs `fictitious_log` + deltas), cumulative corrections counter, c/v/s + exploitation/profit rates; `Sparkline` strip; `Gauge` for O=C/B overshoot. Goldens. Commit `feat(core): stock-market dashboards`.
- [ ] **Task 40 — M6 close-out.** Gates; smoke over a 520-tick save; `ai/state.yaml`.

# M7 — Cutover ceremony (task-level; expand at kickoff; requires M3 gate + BD ruling)

- [ ] **Task 41 — Flip the default.** `--client` default becomes `rust`; textual remains available one release behind a deprecation warning. Commit `feat(cli): rust client is the default`.
- [ ] **Task 42 — The ceremony commit.** Single declared commit `test(cutover)!: retire Textual Archive lane`: delete Textual widgets/tests/`__snapshots__`, remove `textual`/`textual-image`/`textual-plotext`/related deps from `pyproject.toml` + `uv lock`, re-point the `tutorial_coverage` sentinel at Rust bindings, update `AGENTS.md`/`CLAUDE.md` (client section), `ai/architecture.yaml`, `ai/tooling.yaml`, `docs/`. Body records the parity-gate evidence (M3 transcript hash). `mise run check` + `qa:regression` MUST be green post-delete; no baselines touched.
- [ ] **Task 43 — Program close.** ADR139 status → implemented; Amendment AC lettering finalized; `ai/state.yaml` final; design + plan moved to done.

---

## Self-Review Notes (run 2026-07-26)

- **Spec coverage:** all spec sections map to tasks — governance §4→Task 7; repo §5→Tasks 1–4; FFI §6→Tasks 3, 5, 17, 21–25, 30, 34, 38; views §7→Tasks 11–20 (wiki/lobby/palette/peek), 30–33 (map), 34–37 (topology), 38–40 (market), 27 (tutorial); testing §8→Tasks 3, 5, 17, 28, 42; milestones §9→M0–M7 blocks; risks §10→R1 (Tasks 11–12), R2 (Task 14), R3 (Task 36 fallback), R4 (Task 3 GIL discipline + Task 21), R5 (milestone gates).
- **Deferred granularity:** M2–M7 tasks carry interfaces/test-intent/acceptance but expand to bite-sized steps at milestone kickoff (stated in Program Map) — deliberate, to avoid inventing unverified APIs (esp. hypergraph-rs `cells3d`).
- **Type consistency:** `lobby_catalog_json`, `read_page`, `known_subjects_json`, `backlinks_json`, `subject_view_json`, `advance_tick`, `issue_verb`, `verb_plate_view_json`, `endgame_status_json`, `pin_watchlist`, `watchlist_json`, `tutorial_state_json`, `choropleth_json`, `topology_json`, `trend_json`, `dashboard_view_json`, `bind_session`, `AppConfig::from_json`, `App::new`, `render_frame`, `host_calls`, `run_interactive`, `render_markdown`, `extract_wikilinks`, `parse_babylon_uri`, `LayoutRegistry::{register,hit}` — used consistently across tasks.
