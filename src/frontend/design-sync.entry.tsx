/**
 * design-sync entry — the curated export surface for the Claude Design sync
 * (claude.ai/design "Babylon Cockpit" project; config in `.design-sync/`).
 *
 * This file is NOT part of the app build: tsconfig `include` covers only
 * `src/` + `vitest.config.ts`, vite bundles from `index.html` → `src/main.tsx`,
 * and the unit/e2e suites never import it. The design-sync converter (esbuild)
 * bundles from here into `window.BabylonCockpit`, so every export below is
 * what the claude.ai/design agent composes with. Route machinery is
 * deliberately absent (main.tsx, App, routes/, mocks/, ObservatoryRoute) —
 * previews must never mount the router or MSW.
 *
 * `useStore` is exported so authored previews can seed realistic world state
 * via `useStore.setState(...)` before rendering store-coupled components.
 */

// action — Article-V verb composer family
export * from "@/components/action/ActionComposer";
export * from "@/components/action/ParamFields";
export * from "@/components/action/TargetPicker";
export * from "@/components/action/VerbForm";
export * from "@/components/action/VerbGrid";

// bbl — CRT/terminal primitives
export * from "@/components/bbl/BblData";
export * from "@/components/bbl/BblLabel";
export * from "@/components/bbl/Sparkline";

// events
export * from "@/components/events/EventsFeed";

// inspector
export * from "@/components/inspector/ConsciousnessBreakdown";
export * from "@/components/inspector/InspectorPanel";
export * from "@/components/inspector/Stat";

// map furniture
export * from "@/components/map/DeckGLMap";
export * from "@/components/map/HexTooltip";
export * from "@/components/map/MapLegend";
export * from "@/components/map/MapModeSelector";

// objectives
export * from "@/components/objectives/ObjectivesTracker";

// shell — the cockpit chrome
export * from "@/components/shell/AppShell";
export * from "@/components/shell/BottomStrip";
export * from "@/components/shell/MapPanel";
export * from "@/components/shell/Outliner";
export * from "@/components/shell/OutlinerRow";
export * from "@/components/shell/OutlinerSection";
export * from "@/components/shell/RightDock";
export * from "@/components/shell/StatChip";
export * from "@/components/shell/StatusBar";
export * from "@/components/shell/TimeControls";

// takeovers — full-screen overlays over the persistent shell
export * from "@/components/takeovers/TakeoverOverlay";
export * from "@/components/takeovers/chronicle/ChronicleTakeover";
export * from "@/components/takeovers/chronicle/EndStateScreen";
export * from "@/components/takeovers/dialectic/DialecticSpread";
export * from "@/components/takeovers/dialectic/DialecticTakeover";
export * from "@/components/takeovers/wire/BlocFlowLines";
export * from "@/components/takeovers/wire/ContinentalColumn";
export * from "@/components/takeovers/wire/CorpusPage";
export * from "@/components/takeovers/wire/IndexPage";
export * from "@/components/takeovers/wire/IntelColumn";
export * from "@/components/takeovers/wire/LiberatedColumn";
export * from "@/components/takeovers/wire/PatternsPage";
export * from "@/components/takeovers/wire/TranslationFooter";
export * from "@/components/takeovers/wire/WireApp";
export * from "@/components/takeovers/wire/WireTakeover";
export * from "@/components/takeovers/wire/WireWindow";

// timeseries
export * from "@/components/timeseries/TimeseriesChart";

// observatory — determinism/telemetry UI (ObservatoryRoute stays out: route machinery)
export * from "@/observatory/DeepPanes";
export * from "@/observatory/ObservatoryChart";
export { default as ObservatoryPage } from "@/observatory/ObservatoryPage";
export * from "@/observatory/SeriesBrowser";
export * from "@/observatory/SessionPicker";

// store — preview seeding surface (not a component; never gets a card)
export { useStore } from "@/store";
