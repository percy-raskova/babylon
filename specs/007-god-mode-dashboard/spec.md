# Feature Specification: God Mode Dashboard (Phase 1)

**Feature Branch**: `007-god-mode-dashboard`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Claude, implement Phase 1 of the God Mode Dashboard (Feature 007). Build the main window using PyQt6 with a 'Bunker Constructivism' theme. Implement the Detroit H3 map using pydeck and QWebEngineView. Connect the map to the simulation via the SimulationState protocol. Use QWebChannel so clicking a hex updates the Inspector. Create the Inspector panel to show the real-time Value Tensor of the selected node. Ensure the GUI registers as an observer via register_observer to update on every tick."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Detroit Region Map (Priority: P1)

As a simulation operator, I want to see a real-time visualization of the Detroit region as a hexagonal grid map, so that I can observe the spatial distribution of simulation state at a glance.

**Why this priority**: The map is the central visualization component. Without it, there is no "God Mode" - the user cannot see the simulation state spatially. This is the foundation upon which all other features depend.

**Independent Test**: Can be fully tested by launching the dashboard and verifying that hexagons render in the correct geographic positions for Detroit. Delivers immediate visual feedback of simulation geography.

**Acceptance Scenarios**:

1. **Given** the dashboard is launched with a valid simulation, **When** the main window renders, **Then** an H3 hexagonal map of the Detroit metropolitan region is visible in the central panel.
1. **Given** the map is rendered, **When** the user examines the map, **Then** hexagons are color-coded by profit_rate values from the simulation (red = low, green = high).
1. **Given** the map is displayed, **When** the user hovers over a hexagon, **Then** a tooltip shows the territory ID and current profit_rate.

______________________________________________________________________

### User Story 2 - Inspect Selected Territory (Priority: P2)

As a simulation operator, I want to click on any hexagon in the map and see detailed simulation state for that territory in an Inspector panel, so that I can examine the "Value Tensor" (all numeric properties) of individual territories.

**Why this priority**: Selection and inspection are core to "God Mode" - the ability to drill down into any node. This depends on US1 (the map must exist to click on it) but is essential for meaningful analysis.

**Independent Test**: Can be tested by clicking a hexagon and verifying the Inspector panel updates to show the selected territory's properties. Delivers the ability to examine individual simulation nodes.

**Acceptance Scenarios**:

1. **Given** the map is displayed, **When** the user clicks on a hexagon, **Then** the Inspector panel updates to show the TerritoryState for that territory.
1. **Given** a territory is selected, **When** the Inspector panel displays, **Then** it shows: territory_id, controlling_polity, tick, profit_rate, equilibrium_r, and hex count.
1. **Given** a hexagon is clicked that belongs to no territory (unclaimed), **When** the Inspector panel updates, **Then** it displays a "No territory claims this hex" message.
1. **Given** a territory is already selected, **When** the user clicks a different hexagon, **Then** the Inspector panel updates to show the newly selected territory.

______________________________________________________________________

### User Story 3 - Observe Real-Time Tick Updates (Priority: P3)

As a simulation operator, I want the map and Inspector to update automatically whenever the simulation advances, so that I can observe state changes in real-time without manual refresh.

**Why this priority**: Real-time updates transform the dashboard from a static viewer into a live monitoring tool. However, the dashboard is still useful without this (manual refresh possible), making it P3.

**Independent Test**: Can be tested by stepping the simulation and verifying both the map colors and Inspector values update automatically. Delivers real-time observation capability.

**Acceptance Scenarios**:

1. **Given** the dashboard is connected to a running simulation, **When** the simulation advances one tick (step()), **Then** the map hexagon colors update to reflect new profit_rate values.
1. **Given** a territory is selected in the Inspector, **When** the simulation advances, **Then** the Inspector values update to show the new tick and profit_rate.
1. **Given** the dashboard is connected via register_observer(), **When** multiple ticks are stepped (step(10)), **Then** the display updates after each tick without requiring user interaction.

______________________________________________________________________

### User Story 4 - Launch Dashboard with Themed UI (Priority: P4)

As a simulation operator, I want the dashboard to have a distinctive "Bunker Constructivism" visual theme, so that the interface conveys the gravity and aesthetic of the simulation subject matter.

**Why this priority**: Visual theming is polish - the dashboard is fully functional without it. However, it establishes the project identity and makes the tool distinctive.

**Independent Test**: Can be tested by visually inspecting the launched dashboard against theme requirements (color palette, typography style). Delivers aesthetic identity.

**Acceptance Scenarios**:

1. **Given** the dashboard launches, **When** the main window appears, **Then** it uses a dark background (near-black or deep gray) as the base.
1. **Given** the dashboard is displayed, **When** examining UI elements, **Then** accent colors are industrial (red, amber, steel gray) consistent with constructivist aesthetics.
1. **Given** the dashboard is displayed, **When** examining text, **Then** fonts are sans-serif with a utilitarian appearance.

______________________________________________________________________

### Edge Cases

- What happens when the simulation has no territories loaded? The map displays but with no colored hexes; the Inspector shows "No territories in simulation".
- What happens when the user clicks outside all hexagons (on the background)? The selection is cleared; the Inspector shows "No territory selected".
- What happens when profit_rate is exactly 0.0 or 1.0 (boundary values)? Colors render correctly at extremes (solid red or solid green).
- What happens when the simulation connection is lost mid-session? The dashboard displays a connection status indicator showing "Disconnected", freezes the last known state, and automatically reconnects when the simulation becomes available again.
- How does the system handle rapid tick updates (100+ per second)? The GUI throttles visual updates to 30 FPS (33ms minimum interval), coalescing intermediate states to always display the most recent snapshot.
- What state is preserved during auto-reconnect? The currently selected territory (if any) MUST be preserved; the Inspector continues showing the last known values until new data arrives.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display an H3 hexagonal map of the Detroit metropolitan region using geographic coordinates from the simulation.
- **FR-002**: System MUST color hexagons based on profit_rate values using a color gradient (low=red, high=green).
- **FR-003**: System MUST allow users to select a territory by clicking on any hexagon belonging to that territory.
- **FR-004**: System MUST display an Inspector panel showing all TerritoryState properties for the selected territory.
- **FR-005**: System MUST register as a simulation observer via the SimulationControl.register_observer() method.
- **FR-006**: System MUST update the map visualization after each simulation tick notification.
- **FR-007**: System MUST update the Inspector panel after each simulation tick if a territory is selected.
- **FR-008**: System MUST communicate hex click events from the map component to the main application for territory lookup.
- **FR-009**: System MUST use the SimulationState.get_node_by_spatial_index() method to resolve clicked H3 indices to territories.
- **FR-010**: System MUST apply a "Bunker Constructivism" visual theme with dark backgrounds and industrial accent colors.
- **FR-011**: System MUST NOT regenerate the full map visualization on every tick; updates MUST be incremental (JSON data push pattern).
- **FR-012**: System MUST unregister its observer callback when the dashboard window is closed.
- **FR-013**: System MUST log errors and connection state changes (connected, disconnected, reconnected) at DEBUG level.
- **FR-014**: System MUST display a visible highlight (border or color shift) on hexagons belonging to the currently selected territory.
- **FR-015**: System MUST handle SimulationState method exceptions gracefully by logging the error and displaying an error indicator, without crashing.

### Key Entities *(include if feature involves data)*

- **Dashboard Window**: The main application window containing the map viewport and inspector panel.
- **Map Viewport**: The central visualization area displaying the H3 hexagonal grid map.
- **Inspector Panel**: A side panel on the right edge of the window, displaying detailed properties of the currently selected territory.
- **Selection State**: The currently selected territory (if any), updated by user clicks or cleared when clicking empty space.
- **Theme Configuration**: Color palette, fonts, and styling rules for the Bunker Constructivism aesthetic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify the geographic distribution of profit rates across the Detroit region within 5 seconds of launching the dashboard.
- **SC-002**: Users can select any territory and view its properties within 2 clicks (one to click hex, details appear within 100ms).
- **SC-003**: Map and Inspector updates are visually apparent within 100ms of simulation tick completion (perceived as "instant").
- **SC-004**: Dashboard remains responsive (no individual frame exceeds 100ms render time) during continuous simulation runs of 1000+ ticks.
- **SC-005**: Users unfamiliar with the system can identify high and low profit rate territories by color within 10 seconds.
- **SC-006**: Memory usage remains stable (growth less than 50MB over baseline) during extended sessions of 10,000+ ticks.

## Clarifications

### Session 2026-01-31

- Q: What should the GUI update throttle rate be for rapid tick updates? → A: 30 FPS (33ms)
- Q: What should happen when connection is restored after loss? → A: Auto-reconnect (automatically resume updates)
- Q: What observability requirements are needed for MVP? → A: Debug logging only (errors and connection state changes)

## Assumptions

- The Detroit region H3 indices are available from the simulation's TerritoryState.hex_claims data.
- The simulation engine is already implemented and exposes SimulationState and SimulationControl protocols (Feature 006).
- The "Bunker Constructivism" theme consists of: dark backgrounds (#1a1a1a to #2d2d2d), red/amber/steel accent colors (#c41e3a, #ff8c00, #708090), and sans-serif typography.
- The "Value Tensor" refers to all numeric properties of TerritoryState: tick, profit_rate, equilibrium_r, plus derived values like hex_claims count.
- Initial map rendering uses the full hex list from the simulation; only color/property updates use the incremental JSON pattern.
- The dashboard runs in the same process as the simulation (no network communication required for MVP).
- Observer callbacks from SimulationControl.register_observer() are invoked on the main thread; no cross-thread marshalling is required in the dashboard.

## Out of Scope

- Simulation playback controls (play/pause/step buttons) - this spec covers visualization only.
- Multiple map layers or overlays (e.g., showing edges, social classes).
- Map zoom/pan controls beyond default behavior.
- Saving or exporting visualizations.
- Configuration of theme or color gradients.
- Territory comparison or multi-select features.
