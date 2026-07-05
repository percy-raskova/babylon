# Research: Endgame Chronicle + Journal + Dialectic Screen

**Spec**: 095-endgame-chronicle

## R1 — Mockup Analysis

### EndState.jsx (`design/mockups/ui_kits/webapp/EndState.jsx`)

A 33-line component rendering a full-viewport end-state screen. Two palettes:
- **Rupture** (victory): `radial-gradient(ellipse at center, #1a1408 0%, #06070b 75%)`,
  headline "BABYLON FALLS", accent `var(--rupture)`.
- **Defeat**: `radial-gradient(ellipse at center, #1a0606 0%, #06070b 75%)`, headline
  "THE BUNKER FAILS", accent `var(--laser)`.

Stat cards: Final Tick, Consciousness, Solidarity Edges, Heat at End — each a
`var(--concrete)` box with `var(--rebar)` border, mono-font label + value.

CRT scanline overlay (`repeating-linear-gradient(0deg, rgba(0,0,0,.22)...)`).

"New Operation" button: `var(--spire)` bg, `var(--void)` text.

**Port decision**: The mockup's `outcome` prop is binary (`"rupture"` / `"defeat"`).
Babylon's `GameOutcome` has 5 terminal values. Mapping:
- `REVOLUTIONARY_VICTORY` → rupture palette ("BABYLON FALLS")
- All others (`ECOLOGICAL_COLLAPSE`, `FASCIST_CONSOLIDATION`, `RED_OGV`,
  `FRAGMENTED_COLLAPSE`) → defeat palette ("THE BUNKER FAILS")

Stat card values come from `get_endgame_state` (final tick, consciousness, solidarity
edge count, heat).

### DialecticSpread.jsx (`design/mockups/ui_kits/webapp/DialecticSpread.jsx`)

A 53-line component rendering a 2-column card grid of "active contradictions". Each card:
- Contradiction number (mono, accent color)
- Thesis (right-aligned) ↔ Antithesis (left-aligned), with `↮` glyph between
- Tension bar (0–1, accent-colored, with glow)
- Synthesis label (resolution direction)

The mockup uses 4 hardcoded cards. The real implementation reads from
`get_contradiction_snapshot` — each card is an opposition state from the
OppositionRegistry.

**Port decision**: Map mockup fields to bridge data:
- `thesis` → `spec.pole_a` (from `contradiction_frames.principal.aspect_a`)
- `antithesis` → `spec.pole_b` (from `contradiction_frames.principal.aspect_b`)
- `tension` → `state.gap` (the opposition's measured gap)
- `resolution` → `state.leading_pole` (the pole currently ahead) or the regime label
- `color` → derived from regime: `reproduction` = `var(--cadre)`,
  `crisis` = `var(--laser)`, `sublation` = `var(--rupture)`

Principal contradiction card gets a highlight border.

## R2 — EndgameDetector Priority Discrepancy

### The discrepancy

**Module docstring** (lines 18-19):
```
Priority when multiple conditions are met:
    REVOLUTIONARY_VICTORY > ECOLOGICAL_COLLAPSE > FASCIST_CONSOLIDATION
```

**on_tick docstring** (lines 196-199):
```
Checks for endgame conditions in priority order:
1. Revolutionary victory (highest priority - the people won)
2. Ecological collapse
3. Fascist consolidation (lowest priority)
```

**on_tick code** (lines 214-240):
```python
# Spec-070 FR-033 priority order: RED_OGV → FRAGMENTED_COLLAPSE →
# ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION → REVOLUTIONARY_VICTORY.
# First-match-wins (FR-033 last sentence).
if self._check_red_ogv(new_state): ...
if self._check_fragmented_collapse(new_state): ...
if self._check_ecological_collapse(new_state): ...
if self._check_fascist_consolidation(new_state): ...
if self._check_revolutionary_victory(new_state): ...
```

The docstring is from **Slice 1.6** (3 outcomes, pre-spec-070). Spec-070 added
`RED_OGV` and `FRAGMENTED_COLLAPSE` and reordered priority per **FR-033**:
`RED_OGV → FRAGMENTED_COLLAPSE → ECOLOGICAL_COLLAPSE → FASCIST_CONSOLIDATION →
REVOLUTIONARY_VICTORY`, first-match-wins.

### Resolution

The **code is correct** (follows FR-033). The **docstring is stale**. The fix is a
docstring update in `src/babylon/engine/observers/endgame_detector.py` (engine code) —
**cross-lane**, flagged not edited.

The red test (US4) constructs a state satisfying BOTH `REVOLUTIONARY_VICTORY` and
`FASCIST_CONSOLIDATION` conditions. Per FR-033, `FASCIST_CONSOLIDATION` is checked
BEFORE `REVOLUTIONARY_VICTORY`, so the outcome is `FASCIST_CONSOLIDATION` — NOT
`REVOLUTIONARY_VICTORY` as the stale docstring claims.

### Bridge-layer bug (fixed here)

`engine_bridge.py:1058`:
```python
endgame_types = {"REVOLUTIONARY_VICTORY", "ECOLOGICAL_COLLAPSE", "FASCIST_CONSOLIDATION"}
```

This misses `RED_OGV` and `FRAGMENTED_COLLAPSE`. When the engine fires either of those
endgames, the bridge's `resolve_tick` does not surface the `snapshot["endgame"]` block.
This IS in `web/game/` — fixed by expanding the set to all 5.

## R3 — Contradiction Layer (ADR051)

### contradiction_field table

DDL (`postgres_schema.py:185`):
```sql
CREATE TABLE IF NOT EXISTS contradiction_field (
    session_id UUID NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
    tick       INTEGER NOT NULL,
    node_id    VARCHAR(64) NOT NULL,   -- "global" for frame-level
    field_name VARCHAR(32) NOT NULL,   -- opposition key (capital_labor, etc.)
    value      FLOAT NOT NULL,          -- gap
    laplacian  FLOAT,                   -- NULL (Phase E)
    dt         FLOAT,                   -- rate (d(gap)/dtick)
    d2t        FLOAT,                   -- NULL (Phase E)
    PRIMARY KEY (session_id, tick, node_id, field_name)
)
```

Written by `headless_runner/bridge.py:_persist_opposition_fields` (C1.4): one row per
opposition, `node_id="global"`, `value=gap`, `dt=rate`.

No read-back query method exists on the persistence layer. The bridge reads rows
directly via SQL (same pattern as `_fetch_session_rng_seed_from_pool`).

### Graph attributes (live, per-tick)

Written by `ContradictionSystem._write_frames` and `_classify_regime`:

- **`contradiction_frames`** — `{"global": ContradictionFrame.model_dump()}` where
  `ContradictionFrame` has `principal` and `secondary`, each a `Contradiction` with:
  `id`, `type`, `aspect_a`, `aspect_b`, `principal_aspect`, `identity`, `intensity`
  (= gap), `aspect_balance` (= rate), `form_of_struggle`, `is_antagonistic`.

- **`dialectical_regime`** — the regime classification: `"reproduction"`, `"crisis"`,
  or `"sublation"` (from `classify_regime` in `dialectics/core/regime.py`).

### OppositionRegistry (dialectics/core/opposition.py)

`OppositionRegistry[I]` steps a family of oppositions and ranks the principal
contradiction. Each `OppositionState` has: `key`, `tick`, `gap`, `balance`, `rate`,
`leading_pole`, `is_principal`, `governed_by`, `successor_key`.

The registry's `step()` returns one state per binding, with exactly one
`is_principal=True`.

### Regime classification (dialectics/core/regime.py)

`classify_regime(states, lattice, field, level_index, rate_epsilon=...)` returns:
- **`"reproduction"`**: `|rate| <= rate_epsilon` (converged) OR `rate < 0` (gap falling).
- **`"crisis"`**: `rate > rate_epsilon` (rising) AND no Aufhebung resolves at a higher level.
- **`"sublation"`**: `rate > rate_epsilon` AND the level lattice's `aufhebung_of` returns
  a resolving level (the contradiction moved up: quality from quantity).

## R4 — GameOutcome enum

`src/babylon/models/enums/events.py:156`:
```python
class GameOutcome(StrEnum):
    IN_PROGRESS = "in_progress"
    REVOLUTIONARY_VICTORY = "revolutionary_victory"
    ECOLOGICAL_COLLAPSE = "ecological_collapse"
    FASCIST_CONSOLIDATION = "fascist_consolidation"
    # Spec-070 Balkanization endgames
    RED_OGV = "red_ogv"
    FRAGMENTED_COLLAPSE = "fragmented_collapse"
```

5 terminal outcomes + 1 ongoing.

## R5 — Existing bridge patterns

- `get_journal_dashboard(session_id)` — reads `tick_event` rows via optional
  `query_session_events` on the persistence layer. SQLite fallback → empty list.
- `get_wire_feed(session_id)` — calls `get_journal_dashboard`, passes through
  `DeterministicNarrator`.
- `get_map_snapshot` — reads graph directly via `hydrate_graph`, builds
  `_build_balkanization_block`.
- `_fetch_session_rng_seed_from_pool(pool, session_id)` — reads `game_session` via
  `pool.connection()` cursor. This is the SQL-read pattern for
  `get_contradiction_snapshot`.

## R6 — Cold Collapse tokens (spec-090)

Ratified in `web/frontend/src/index.css`. Key tokens for this spec:
- `--babylon-rupture: #d4a02c` (revolution — bronze-gold)
- `--babylon-laser: #ff3344` (threat — pure red)
- `--babylon-spire: #4dd9e6` (primary — cyan)
- `--babylon-solidarity: #5fbf7a` (mass-line success)
- `--babylon-cadre: #6b8fb5` (info)
- `--babylon-heat: #d97a2c` (surveillance pressure)
- `--babylon-concrete: #11141c` (surface)
- `--babylon-rebar: #1a1f2a` (elevated)
- Font: `--font-mono: "JetBrains Mono"`, `--font-sans: "Space Grotesk"`

Tailwind utilities exposed via `@theme`: `text-rupture`, `text-laser`, `text-spire`,
`bg-concrete`, `border-rebar`, `font-mono`, etc.
