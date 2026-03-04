# Implementation Plan: Game UI Overhaul

**Branch**: `042-game-ui-overhaul` | **Date**: 2026-03-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/042-game-ui-overhaul/spec.md`

## Summary

Comprehensive overhaul of the Babylon React frontend to implement a Victoria 3-inspired information architecture with lens-based navigation, progressive drill-down, tiered notifications, Tufte-aligned analytics, and constitutional visual design compliance. The overhaul restructures the existing 82-file frontend around a lens-centric layout, adds breadcrumb navigation to the detail panel, implements a notification system with event severity classification, and enhances the action composer with outcome previews. All changes are frontend-only except one new backend endpoint for action preview estimation.

## Technical Context

**Language/Version**: TypeScript 5.7 (frontend), Python 3.12+ (backend — minimal changes)
**Primary Dependencies**: React 19, Zustand 5, deck.gl 9, MapLibre GL 5, Recharts 2, Sigma.js 3, Tailwind CSS v4, Vite 6, lucide-react, react-router-dom 7
**Storage**: PostgreSQL 16+ (runtime state via Django), localStorage (UI preferences)
**Testing**: Vitest 4 + Testing Library + MSW 2 + Playwright (frontend), pytest (backend)
**Target Platform**: Desktop browsers (Chrome, Firefox, Safari, Edge), minimum 1280x720
**Project Type**: Web application (Django backend + React frontend)
**Performance Goals**: 60fps map interaction with 3000+ hexagons, <300ms lens switch, <200ms interaction feedback, <100ms tooltip appearance
**Constraints**: Dark theme only, desktop-first, existing 9 verbs unchanged, Django REST API is the durable contract per II.8
**Scale/Scope**: 50 states, 3000+ county-level territories, ~20 organizations, ~50 institutions, ~200 edges

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|---|---|---|
| II.8 Client as Presentation Layer | PASS | Frontend receives JSON, renders it, emits intents. No simulation logic in browser. |
| VII.1 UI Observes, Never Controls | PASS | All state changes go through Django API → engine. UI never mutates state directly. |
| VII.2 Color as Data | PASS | Spec FR-037-040 align with constitutional palette. Colors encode meaning, not decoration. |
| VII.3 Data-Ink Maximization | PASS | Spec FR-024, FR-033, SC-007 explicitly require Tufte-aligned visualization. |
| VII.4 Graph Is Primary | PASS | Graph view (US7) maintained. Map is a spatial projection of the topology. |
| VII.5 Signifier Legibility | PASS | Spec FR-038, SC-012 require consistent affordances on all interactive elements. |
| VII.6 Semantic Invariance | PASS | Spec references constitutional color semantics. No context-dependent color. |
| VII.7 Smallest Effective Difference | PASS | Spec FR-039 requires visual hierarchy with minimal effective distinction. |
| VII.8 Feedback/Feedforward | PASS | Spec FR-017 (action preview), FR-023 (immediate feedback), SC-008 (200ms). |
| VII.9 Typography | PASS | Existing Roboto Mono + Inter (sans-serif) pairing in index.css. Max two families. |
| VII.10 Prohibitions | PASS | Spec explicitly forbids chartjunk, 3D effects, decorative elements. |
| VIII.8 Decorative Visualization | PASS | Every visual element must encode data per VII.3. |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/042-game-ui-overhaul/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Technical decisions
├── data-model.md        # Phase 1: Frontend type definitions
├── quickstart.md        # Phase 1: Developer onboarding
├── contracts/           # Phase 1: API contract additions
│   └── action-preview.yaml  # New preview endpoint
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
web/frontend/src/
├── main.tsx
├── App.tsx
├── index.css                    # Tailwind v4 @theme tokens (update palette)
├── types/
│   └── game.ts                  # Extended with Lens, Notification, Breadcrumb types
├── api/
│   └── client.ts                # Unchanged
├── stores/
│   ├── gameStore.ts             # Extended: event accumulation, notification state
│   ├── uiStore.ts               # Extended: lens, breadcrumbs, panel persistence
│   └── mapStore.ts              # Extended: lens-driven layer selection
├── hooks/
│   ├── useGameState.ts          # Unchanged
│   ├── usePersistentUI.ts       # NEW: localStorage sync for panel preferences
│   └── useLens.ts               # NEW: lens switching coordination
├── theme/
│   └── colors.ts                # Unchanged (deck.gl color scales)
├── lib/
│   ├── utils.ts                 # Unchanged
│   ├── eventClassifier.ts       # NEW: event type → severity mapping
│   └── lensDefinitions.ts       # NEW: lens configs (layer, indicators, panel content)
├── components/
│   ├── layout/
│   │   ├── GameShell.tsx         # UPDATED: lens context, notification overlay
│   │   ├── TopBar.tsx            # UPDATED: dynamic indicators, lens-aware
│   │   ├── RightPanel.tsx        # UPDATED: breadcrumbs, resizable
│   │   ├── BottomPanel.tsx       # UPDATED: notifications tab, resizable
│   │   ├── EndgameOverlay.tsx    # Unchanged
│   │   └── LensBar.tsx           # NEW: bottom lens navigation
│   ├── map/
│   │   ├── DeckGLMap.tsx         # Unchanged (lens drives mapStore)
│   │   ├── LayerControls.tsx     # Unchanged
│   │   ├── MapLegend.tsx         # Unchanged
│   │   └── HexTooltip.tsx        # UPDATED: lens-contextual metrics
│   ├── inspector/
│   │   ├── Inspector.tsx         # UPDATED: breadcrumb-aware routing
│   │   ├── NodeInspector.tsx     # UPDATED: lens-contextual fields
│   │   ├── HexInspector.tsx      # UPDATED: lens-contextual fields, org links
│   │   └── Breadcrumbs.tsx       # NEW: navigation breadcrumb trail
│   ├── action/
│   │   ├── ActionComposer.tsx    # UPDATED: preview step enhancement
│   │   ├── VerbSelector.tsx      # UPDATED: unavailability explanations
│   │   ├── TargetSelector.tsx    # Unchanged
│   │   └── ActionPreview.tsx     # UPDATED: estimated effects display
│   ├── charts/
│   │   ├── TimeSeries.tsx        # UPDATED: Tufte-aligned styling, metric selector
│   │   └── PersistentIndicators.tsx  # UPDATED: dynamic indicator selection, urgency colors
│   ├── graph/
│   │   └── GraphView.tsx         # UPDATED: edge type filtering
│   ├── events/
│   │   ├── EventLog.tsx          # UPDATED: severity tiers, grouping, navigation
│   │   └── NotificationToast.tsx # NEW: critical event alert overlay
│   └── ui/
│       └── IndicatorChip.tsx     # NEW: reusable metric display with urgency
└── __tests__/
    └── integration/
        ├── lens-switching.test.tsx     # NEW
        ├── breadcrumb-navigation.test.tsx  # NEW
        ├── notification-flow.test.tsx  # NEW
        └── panel-persistence.test.tsx  # NEW

web/game/
├── api.py               # UPDATED: add action preview endpoint
├── engine_bridge.py     # UPDATED: add preview_action method
└── urls.py              # UPDATED: add preview URL pattern
```

**Structure Decision**: Extends existing web application structure (Django backend + React frontend). No new top-level directories. Changes are additive to existing component tree with 7 new files and ~15 updated files.

## Complexity Tracking

No constitution violations — table not needed.
