# Research: The Wire — Design Mockup Analysis & R-NARR Compliance

**Spec**: `specs/094-the-wire/spec.md`
**Date**: 2026-07-04

## 1. Design Mockup Analysis (9 files in `design/mockups/wire/`)

### 1.1 wire-data.jsx — THE source of truth for WireFeed shape

Defines the exact data structure the NarratorProvider must produce:

- **meta**: `{tick, session, operator, freq, qth, classification, cable_id, page_of,
  timestamp_utc}` — presentation metadata for the window chrome.
- **index**: array of `{id, tick, slug, hed:{c,l,i}, coverage:["c","l","i"], pinned?,
  severity}` — the story archive. `hed` has three channel headlines (corporate/
  liberated/intel). `coverage` marks which channels have a take. `severity` is
  critical/warning/info.
- **euphemisms**: `{term_id: {c: "corporate phrase", l: "liberated phrase", filter,
  note}}` — the euphemism map. Each term links a corporate phrase to its liberated
  equivalent, tagged with a Manufacturing Consent filter and an editorial note.
- **story**: the active story with `continental`/`liberated`/`intel` sub-objects.
  Each channel has its own structure:
  - **continental**: brand, monogram, kicker, hed, dek, byline, paragraphs (array of
    runs where each run is a string or `{euph, text}` or `{sup}`), bibliography.
  - **liberated**: brand, callsign, operator, hed, pre, post, paragraphs (each with
    `body` array of runs and optional `margin` note), cursor.
  - **intel**: classification, cable_id, origin, routing, caveat, subj, fields (array
    of [key, value] pairs), assessment (array of strings), refs, distribution.
- **filters**: 5 Manufacturing Consent filters: `{id, label, desc, hits, color}`.
  IDs: ownership, advertising, sourcing, flak, ideology.

### 1.2 wire-app.jsx — Main shell

4 tabs: WIRE (triptych), INDEX, PATTERNS, CORPUS. Uses a `useTweaks` panel for layout
mode (triptych/2-up/focus), euphemism always-on toggle, citation density, intel
visibility. The `TranslationFooter` is a slim strip below the triptych showing the
active euphemism translation.

### 1.3 wire-window.jsx — App chrome

Title bar with traffic lights (laser/heat/solidarity), centered "BABYLON THE WIRE"
title, tick badge. Tab bar with dot indicators and count badges.

### 1.4 wire-corporate.jsx — Continental column

Passive voice, generous whitespace, official-source-led. Masthead with monogram,
nameplate, chrome strip (markets/weather). Story body with kicker, hed, dek, byline,
paragraphs (runs with euphemism spans and superscript citations). Bibliography drawer.

### 1.5 wire-liberated.jsx — Free Signal column

Pirate-radio phosphor terminal. Signal meter, callsign, frequency. Two-column layout:
prose | margin notes. Handwritten margin notes (Caveat font, tilted). Phosphor glow on
euphemism spans. TX markers (begin/end transmission).

### 1.6 wire-intel.jsx — Cable column

SIGINT cable. Classification bar (laser red). Cable head (SUBJ, ORIGIN, ROUTING,
CAVEAT). Structured fields grid. Assessment prose with section markers. Corpus refs
with similarity scores. Distribution/retain footer.

### 1.7 wire-pages.jsx — IndexPage, PatternsPage, CorpusPage

- **IndexPage**: severity filter (all/critical/warning/info), story cards with tick,
  slug, 3-column headline preview, coverage marks.
- **PatternsPage**: consent score (computed from filter hits), 5 filter cards with hit
  bars, euphemism table (4-column: Continental said, Free Signal said, Editorial
  intervention, Filter).
- **CorpusPage**: channel filter, chunk cards with similarity scores, note about
  Archive being observer-only (Constitution VIII).

### 1.8 wire.css — Channel textures

Cold Collapse token aliases (`--void`, `--spire`, etc.). Continental: sterile sans,
drop cap. Liberated: phosphor green, scanlines, paper grain, CRT flicker animation,
handwritten margin notes. Intel: mono, classification bar, redaction bars, confidence
bar. Euphemism highlight styles per channel. Tilt rotations for margin notes.

### 1.9 The Wire.html — Standalone HTML loader

CDN React 18 + Babel standalone. Loads wire-data, wire-corporate, wire-liberated,
wire-intel, wire-app, wire-window, wire-pages. NOT project code — reference only.

## 2. Data Shape Documentation

### 2.1 WireFeed (the NarratorProvider output)

```python
{
    "meta": {
        "tick": int,
        "session": str,        # session_id
        "operator": str,       # deterministic callsign
        "freq": str,           # "88.7 MHz"
        "qth": str,            # grid square
        "classification": str, # "TS//SI//NOFORN"
        "cable_id": str,
        "page_of": str,
        "timestamp_utc": str,  # ISO 8601
    },
    "index": [
        {
            "id": str,          # event id
            "tick": int,
            "slug": str,        # short description
            "hed": {"c": str, "l": str, "i": str},
            "coverage": ["c", "l", "i"],
            "pinned": bool,     # optional
            "severity": "critical" | "warning" | "info",
        }
    ],
    "euphemisms": {
        "term_id": {
            "c": str,   # corporate phrase
            "l": str,   # liberated phrase
            "filter": str,  # one of: ownership, advertising, sourcing, flak, ideology
            "note": str,     # editorial intervention note
        }
    },
    "story": {  # active story, or null if no events
        "id": str,
        "tick": int,
        "location": str,
        "time_local": str,
        "continental": {...},
        "liberated": {...},
        "intel": {...},
    },
    "filters": [
        {"id": str, "label": str, "desc": str, "hits": int, "color": str}
    ],
}
```

### 2.2 GameEvent (input, from spec-092)

```python
{
    "id": str,
    "type": str,          # lowercase snake_case (e.g., "uprising")
    "tick": int,
    "severity": str,      # "critical" | "warning" | "informational"
    "title": str,
    "body": str,
    "data": dict,         # event-specific payload
}
```

### 2.3 Event Type to Template Mapping

The DeterministicNarrator maps event types to templates. Key mappings:

| Event Type | Severity | Slug Template | Corporate Frame | Liberated Frame | Intel Frame |
|---|---|---|---|---|---|
| uprising | critical | UPRISING {location} | Civil disturbance | WORKERS ROSE UP | CIVIL DISTURBANCE |
| eviction_pipeline | warning | EVICTION {location} | Market correction | LANDLORDS STRIKE | EVICTION PIPELINE |
| excessive_force | critical | REPRESSION {location} | Measured response | PIGS ATTACKED | USE OF FORCE |
| solidarity_formed | warning | SOLIDARITY {org} | New alliance | COMRADES UNITE | COORDINATION DETECTED |
| consciousness_shift | info | CONSCIOUSNESS {location} | Civic engagement | THE MASS LINE HOLDS | CONSCIOUSNESS DELTA |
| heat_change | info | SURVEILLANCE {org} | Security attention | HEAT ON THE DOOR | SURVEILLANCE INTENSITY |
| rupture | critical | RUPTURE {location} | System stress | THE DAM BREAKS | RUPTURE EVENT |
| revolutionary_victory | critical | REVOLUTION {location} | Regime change | WE WIN | REGIME CHANGE |
| ecological_collapse | critical | COLLAPSE {location} | Environmental crisis | THE EARTH BETRAYED | ECOCATASTROPHE |
| fascist_consolidation | critical | FASCISM {location} | Order restored | THE FASH TAKE HOLD | AUTHORITARIAN SHIFT |

Unknown event types use a generic template derived from `event.title` and `event.body`.

## 3. R-NARR Compliance

**Ruling** (project/09 lines 119-126): The Wire ships with a DETERMINISTIC narrator.
The Workers-AI/LoRA stack is M8/Wave-6 infrastructure. Spec-094 ships the Wire on the
designed template/deterministic fallback behind a `NarratorProvider` interface.

**Compliance**:
- `DeterministicNarrator` uses ONLY template strings + event data. No LLM calls.
- The `NarratorProvider` protocol is designed for future LLM drop-in: a future
  `LLMNarrator` class can implement the same interface and replace the deterministic
  provider without frontend changes.
- The `visibility` parameter (no-op pass-through) is the hook for spec-077's hegemony
  mechanic. Currently always returns all channels.

## 4. Constitution III Compliance (AI observes, never controls)

**Structural enforcement**:
- `web/game/narrator.py` imports ZERO `babylon.*` modules. It uses only Python stdlib
  (`typing`, `logging`, `json`, `datetime`).
- The narrator function signature is `narrate(events: list[dict], meta: dict) -> dict`.
  It accepts plain dicts (not engine types) and returns plain dicts.
- The narrator has NO database access, NO graph access, NO WorldState access.
- It is called by `EngineBridge.get_wire_feed()` AFTER `resolve_tick` completes — it
  reads the already-persisted `tick_event` rows, never touches live engine state.

**Article III test**: `test_narrator_writes_no_engine_state` — (a) inspect the narrator
module's loaded `sys.modules` entries; assert none start with `babylon.engine` or
`babylon.models` or `babylon.persistence`; (b) run the narrator; assert no mutable global
state changed (idempotent re-runs).

## 5. Existing Infrastructure (spec-092, READ-ONLY reference)

- `get_journal_dashboard(session_id)` returns `{"events": [GameEvent, ...]}` from
  `tick_event` table. Newest-tick-first, capped at 200 rows.
- `query_session_events(session_id, limit=200)` on `PostgresRuntime` — the persistence
  method that backs `get_journal_dashboard`.
- `useJournal(gameId)` hook polls `GET /api/games/:id/journal/` on 2s interval.
- `GameEvent` shape: `{id, type, tick, severity, title, body, data}` — severity is
  backend-derived (critical/warning/informational).
- MSW handlers in `web/frontend/src/test/handlers.ts` already mock `/journal/` and
  `/alerts/` — we add `/wire/`.
- Cold Collapse tokens in `web/frontend/src/index.css` (spec-090) — ratified token set.

## 6. Existing NarrativeDirector (engine, READ ONLY)

`src/babylon/ai/director.py` is an LLM-based observer with dual-narrative
(corporate/liberated) support. It is NOT the `NarratorProvider` interface — spec-094
introduces that. The existing director is an LLM provider that drops in LATER (M8).
Key differences:
- `NarrativeDirector` uses `LLMProvider` for generation; `DeterministicNarrator` uses
  templates.
- `NarrativeDirector` is engine-side (`src/babylon/ai/`); `DeterministicNarrator` is
  web-side (`web/game/`).
- `NarrativeDirector` has RAG integration; `DeterministicNarrator` does not (RAG is M8).
- Both produce dual-narrative output, but `DeterministicNarrator` also produces the
  intel channel and the Manufacturing Consent filter analysis.
