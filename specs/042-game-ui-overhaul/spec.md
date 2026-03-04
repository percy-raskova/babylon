# Feature Specification: Game UI Overhaul

**Feature Branch**: `042-game-ui-overhaul`
**Created**: 2026-03-03
**Status**: Draft
**Input**: User description: "Victoria 3-inspired comprehensive UI overhaul for Babylon, informed by deep research into grand strategy UIs, classic UX design principles, and the existing codebase"

## Research Foundation

This specification is informed by extensive research across multiple domains:

- **Victoria 3 UI**: Complete analysis of Paradox's five-lens navigation, nested tooltip system, journal entries, notification architecture, and community-identified failures (information fragmentation, buried core gameplay, tooltip depth inversion)
- **Grand Strategy UIs**: Stellaris alert/outliner system, Hearts of Iron IV division designer, SimCity layered data overlays, Civilization series progressive complexity
- **UX Theory**: Tufte (data-ink ratio, chartjunk elimination, data-ink maximization), Norman (affordances, signifiers, mapping, feedback), Krug (don't make me think, scanning/satisficing), Shneiderman (direct manipulation, overview-zoom-details), Sylvester (interface as communication, metaphor vocabulary, signal vs noise, visual hierarchy, redundancy, indirect control)
- **Modern Practices**: Dark theme design (layered elevation, desaturated semantic colors, 4.5:1 contrast), progressive disclosure patterns, cognitive load theory (minimize extraneous load, enable germane load)
- **Existing Codebase**: 82-file React frontend with deck.gl map, Zustand stores, three-zone layout (TopBar, Center+Bottom, Right Sidebar), action composer, choropleth layers

## Assumptions

- The existing React 19 + Zustand 5 + deck.gl 9 + Vite 6 + Tailwind CSS v4 stack is retained
- Django 5.x backend API contracts remain stable; UI changes are frontend-only unless noted
- The target audience ranges from casual players exploring the simulation to power users conducting deep analysis
- Dark theme is the primary (and initially only) theme
- Desktop-first design; mobile/tablet is out of scope for this feature
- The existing 9 constitutional verbs (Organize, Agitate, Strike, Boycott, Demonstrate, Occupy, Expropriate, Sabotage, Liberate) and entity model remain unchanged
- Map visualization continues to use H3 hexagonal grid with deck.gl

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand Game State at a Glance (Priority: P1)

A player opens Babylon and immediately understands what is happening in the simulation. Without clicking anything, they can see the current tick number, key aggregate indicators (imperial rent extraction, national consciousness level, organization strength, repression intensity), and a color-coded map showing the most important metric. The top bar communicates urgency through color shifts — green for stable conditions, amber for rising tension, red for crisis. The player knows *where* to look and *what matters* before taking any action.

**Why this priority**: This is the foundation of all gameplay. Per Shneiderman's mantra, "Overview first" is prerequisite to all other interaction. Per Tufte, every pixel on the default screen must carry data. Per Sylvester, "that which is never communicated might as well never have occurred at all." If the player cannot read the game state, no other feature matters.

**Independent Test**: Can be fully tested by loading a game at various tick states and verifying that a new player can correctly identify whether the simulation is stable, tense, or in crisis — without clicking anything.

**Acceptance Scenarios**:

1. **Given** a game loaded at tick 1, **When** the player views the main screen, **Then** they see the tick counter, at least 4 aggregate indicators with labels and values, and a choropleth map with a visible legend explaining the color encoding
1. **Given** a game at tick 50 with rising consciousness, **When** the player views the top bar indicators, **Then** at least one indicator visually communicates urgency (color shift, icon change, or animation) reflecting the changed conditions
1. **Given** a game in crisis state (high heat, low acquiescence), **When** the player views the screen, **Then** the overall visual tone shifts to communicate danger without requiring any tooltip interaction
1. **Given** any game state, **When** the player views the default screen, **Then** no critical simulation information is hidden behind clicks, tabs, or tooltips — the essential "pulse" of the simulation is always visible

______________________________________________________________________

### User Story 2 - Drill Down from Map to Entity Detail (Priority: P1)

A player sees a bright-red hexagon on the map and wants to understand why. They hover over it and see a tooltip with territory name, key metrics (heat, rent extraction, population, biocapacity), and any active warnings. They click the hex and a detail panel opens showing the territory's full state: all organizations present, their strength, the territory's economic profile, and recent events affecting it. From the territory detail, they can click on an organization to see its full profile. This drill-down chain (Map -> Territory -> Organization -> Key Figure) follows Victoria 3's progressive disclosure pattern but avoids its failure of burying critical information 4+ clicks deep.

**Why this priority**: The map is the primary interaction surface. The drill-down from visual anomaly to root cause is the core analytical loop of the game. Without it, the map is decoration rather than a tool. Per Norman, this is the fundamental "Gulf of Evaluation" — the player must be able to evaluate system state from what they see.

**Independent Test**: Can be fully tested by clicking through the hover -> click -> detail -> sub-detail chain on any territory and verifying each layer adds meaningful information without losing context from the previous layer.

**Acceptance Scenarios**:

1. **Given** a hex on the map, **When** the player hovers over it, **Then** a tooltip appears within 100ms showing territory name and top 4-6 metrics with formatted values
1. **Given** a hovered hex, **When** the player clicks it, **Then** a detail panel opens showing the territory's complete state including all present organizations, economic data, and recent events
1. **Given** an open territory detail panel, **When** the player clicks on an organization listed within it, **Then** the panel transitions to show that organization's full profile without closing or losing breadcrumb navigation back to the territory
1. **Given** a detail panel open at any depth, **When** the player clicks the map background or presses Escape, **Then** the panel closes and map selection is cleared
1. **Given** a detail panel open, **When** the player hovers a different hex, **Then** the tooltip still appears over the new hex without closing the detail panel (tooltip and detail panel coexist)

______________________________________________________________________

### User Story 3 - Compose and Execute Strategic Actions (Priority: P1)

A player decides to organize workers in Detroit. They select an organization they control, choose the "Organize" verb from a clear verb palette, select Detroit as the target territory (either by clicking the map or from a list), and see a preview of the expected outcome before confirming. The action composer guides them through a logical sequence: Who acts? -> What do they do? -> Where? -> Confirm. After execution, immediate visual feedback shows the action was processed and the game state updates.

**Why this priority**: Actions are the player's primary agency mechanism. Per Sylvester, "the goal of input design is to achieve synchronization between a player's intent and in-game action." Per Krug, the action flow must be obvious enough that users don't have to think about *how* to act — only *what* to do. The existing 4-step ActionComposer is a strong foundation but needs clearer affordances and feedback.

**Independent Test**: Can be fully tested by walking through the complete action composition flow from organization selection to execution confirmation and verifying each step provides clear feedback and reversibility.

**Acceptance Scenarios**:

1. **Given** a game with at least one player-controlled organization, **When** the player initiates an action, **Then** the system presents a clear sequential flow: select organization -> select verb -> select target -> preview outcome
1. **Given** the player has selected an organization and verb, **When** they select a target territory, **Then** a preview panel shows the expected effects (estimated consciousness change, heat increase, resource cost) before requiring confirmation
1. **Given** the player is at any step of action composition, **When** they click "Back" or press Escape, **Then** they return to the previous step without losing prior selections
1. **Given** the player confirms an action, **When** the action is submitted, **Then** visual feedback confirms submission within 200ms and affected territories/organizations show updated state after tick resolution
1. **Given** an action that would be invalid (e.g., insufficient resources, target out of range), **When** the player attempts to select it, **Then** the system prevents the selection and explains why it is unavailable

______________________________________________________________________

### User Story 4 - Analyze Trends Over Time (Priority: P2)

A player wants to understand how imperial rent extraction has changed over the last 20 ticks. They open the analytics panel and see time-series charts showing key metrics over time. They can select which metrics to display, zoom into specific time ranges, and compare metrics side-by-side. The charts follow Tufte's principles: high data-ink ratio, no chartjunk, subtle grid lines, and data points that are directly readable.

**Why this priority**: Temporal analysis enables strategic thinking beyond the current tick. Players need to identify trends (is consciousness rising? is repression escalating?) to make informed decisions. However, this is secondary to understanding the current state (US1) and being able to act on it (US3).

**Independent Test**: Can be fully tested by loading a game with 20+ ticks of history and verifying that trend lines accurately reflect stored historical data, and that chart interactions (zoom, metric selection) function correctly.

**Acceptance Scenarios**:

1. **Given** a game with 10+ ticks of history, **When** the player opens the analytics panel, **Then** they see at least one time-series chart showing a meaningful metric over all available ticks
1. **Given** the analytics panel is open, **When** the player selects different metrics from a menu, **Then** the chart updates to show the selected metric(s) with appropriate axis labels and scales
1. **Given** a time-series chart, **When** the player hovers over a data point, **Then** a tooltip shows the exact value and tick number for that point
1. **Given** the analytics panel, **When** the player views charts, **Then** charts use high data-ink ratio: no 3D effects, no heavy grid lines, no decorative elements — only data-carrying ink and minimal reference lines

______________________________________________________________________

### User Story 5 - Navigate Between Game Lenses (Priority: P2)

A player wants to shift their analysis from economic conditions to political consciousness across the nation. They click a lens selector (inspired by Victoria 3's bottom-bar lenses) that switches the map's choropleth layer, updates the side panel's default content, and adjusts which indicators are prominent in the top bar. Each lens represents a coherent analytical perspective: Economic, Political, Social, Geographic, and Strategic. Switching lenses is a single click that recontextualizes the entire screen without navigating away.

**Why this priority**: Lenses reduce cognitive load by filtering the simulation's complexity into manageable analytical perspectives. Per Victoria 3's design philosophy, each lens is a "way of seeing" that highlights what matters for a specific type of decision. This is the progressive disclosure layer between the overview (US1) and deep drill-down (US2).

**Independent Test**: Can be fully tested by switching between all available lenses and verifying that the map layer, panel content, and indicator emphasis change coherently for each lens.

**Acceptance Scenarios**:

1. **Given** the main game screen, **When** the player clicks a lens button, **Then** the map choropleth layer changes to reflect that lens's primary metric, the right panel updates to show lens-relevant summary information, and the top bar indicators reorder to emphasize lens-relevant metrics
1. **Given** a lens is active, **When** the player switches to a different lens, **Then** the transition occurs within 300ms with a smooth visual transition (no jarring full-screen refresh)
1. **Given** any lens is active, **When** the player drills into a territory or entity, **Then** the detail panel shows information contextualized to the active lens (e.g., Economic lens shows rent/wages prominently; Political lens shows consciousness/organization prominently)
1. **Given** a lens is active, **When** the player opens the analytics panel, **Then** the default charts shown correspond to the active lens's domain

______________________________________________________________________

### User Story 6 - Monitor Notifications and Events (Priority: P2)

A player resolves a tick and several significant events occur: a territory reaches crisis heat, an organization gains enough strength to attempt a new action type, and imperial rent extraction increases nationally. The system communicates these events through a tiered notification system — critical events appear as prominent alerts that demand attention, important events appear in a notification feed, and minor events are logged but don't interrupt. The player can review the event log to understand what happened and click on any event to navigate to the relevant entity.

**Why this priority**: Events are the narrative backbone of the simulation. Per Sylvester's redundancy principle, critical events should be communicated through multiple channels (notification badge + map visual change + indicator shift). Per Victoria 3's lessons, notification volume must be managed — late-game notification flood was a top community complaint.

**Independent Test**: Can be fully tested by resolving ticks that produce events of varying severity and verifying that each severity tier is displayed appropriately, and that clicking events navigates to the relevant context.

**Acceptance Scenarios**:

1. **Given** a tick resolution produces a critical event (e.g., rupture threshold crossed), **When** the tick resolves, **Then** a prominent alert appears that requires acknowledgment before further interaction, and the relevant territory/entity is highlighted on the map
1. **Given** a tick resolution produces multiple events, **When** the player views the notification area, **Then** events are grouped by severity (critical > important > informational) and sorted by relevance
1. **Given** an event notification, **When** the player clicks on it, **Then** the view navigates to the relevant entity (territory, organization, or class) with that entity's detail panel open
1. **Given** 50+ ticks have elapsed with many events, **When** the player views notifications, **Then** only the most recent and unread events are prominently displayed, with older events accessible through a scrollable history log
1. **Given** the player has acknowledged all critical events, **When** they view the notification area, **Then** no critical alerts are present and the notification indicator reflects the remaining unread count

______________________________________________________________________

### User Story 7 - Visualize Network Relationships (Priority: P3)

A player wants to understand the solidarity network — who is connected to whom, where are the strongest bonds, and where are the structural holes that atomization has created. They open a network visualization view that shows organizations and classes as nodes, with edges representing solidarity, exploitation, and other relationship types. The player can filter by edge type, highlight specific organizations, and see how the network structure has changed over time.

**Why this priority**: The topology (NetworkX graph) is a core pillar of Babylon's architecture, but it needs visual representation to be meaningful to players. This is a power-user feature that enables deep strategic analysis. It's P3 because the map and detail panels (US1-US3) cover most analytical needs; the graph view adds a complementary structural perspective.

**Independent Test**: Can be fully tested by loading a game with established relationships and verifying that the graph visualization accurately represents the underlying NetworkX topology, with correct node/edge counts and types.

**Acceptance Scenarios**:

1. **Given** a game with multiple organizations and relationships, **When** the player opens the graph view, **Then** they see a force-directed graph with nodes representing organizations/classes and edges representing typed relationships (solidarity, exploitation, etc.)
1. **Given** the graph view is open, **When** the player filters by edge type (e.g., "show only SOLIDARITY edges"), **Then** only edges of that type are displayed, with all nodes still visible but unconnected nodes dimmed
1. **Given** the graph view is open, **When** the player clicks on a node, **Then** the entity's detail panel opens with the same information available from the map drill-down path
1. **Given** the graph view is open, **When** the player hovers over an edge, **Then** a tooltip shows the relationship type, strength value, and the two connected entities

______________________________________________________________________

### User Story 8 - Customize UI Layout and Preferences (Priority: P3)

A player finds the right panel too narrow for their analysis workflow and wants to widen it. Or they prefer the analytics panel always visible rather than collapsed. The UI allows panel resizing, remembers panel open/closed states between sessions, and lets players choose which indicators appear in the top bar's persistent display. These preferences persist across game sessions.

**Why this priority**: Per Victoria 3's patch 1.2 lessons, giving players control over their information display significantly improves satisfaction. However, this is enhancement over the core experience — the default layout must work well without customization. This is P3 because a well-designed default (US1-US6) matters more than customizability.

**Independent Test**: Can be fully tested by adjusting panel sizes and indicator preferences, refreshing the browser, and verifying all customizations persist.

**Acceptance Scenarios**:

1. **Given** the default layout, **When** the player drags a panel edge to resize it, **Then** the panel smoothly resizes within defined minimum/maximum bounds and adjacent panels adjust accordingly
1. **Given** the player has customized panel sizes and indicator selections, **When** they close and reopen the browser, **Then** all customizations are restored to their last saved state
1. **Given** the player has customized their layout, **When** they click a "Reset to Defaults" option, **Then** all panels return to their default sizes and positions
1. **Given** the top bar's persistent indicators, **When** the player opens an indicator selection menu, **Then** they can choose which 4-6 metrics are always visible from the full set of available simulation metrics

______________________________________________________________________

### Edge Cases

- What happens when a territory has no organizations present? The detail panel shows the territory's economic and geographic data with an empty organizations section and a contextual message ("No organizations have established presence here")
- How does the system handle a game with 0 ticks of history? The analytics panel shows an empty state with a message ("Resolve at least one tick to see trends") rather than broken empty charts
- What happens when 100+ events fire in a single tick? The notification system groups similar events (e.g., "12 territories reached elevated heat") rather than showing 100 individual notifications
- How does the UI handle slow API responses? Interactive elements show loading states (skeleton screens for panels, spinner for action submission) and timeout after a defined period with a retry option
- What happens when the player resizes the browser window below minimum supported width? The UI degrades gracefully — panels collapse to icon-only mode, the map fills available space, and a minimum width warning appears if the window becomes too small for usable interaction
- How does the map handle thousands of hexagons at national scale? The map uses level-of-detail rendering: zoomed out shows aggregated regional coloring, zoomed in shows individual hex boundaries and labels
- What happens if the player tries to compose an action while a tick is resolving? The action composer is disabled with a clear "Resolving tick..." indicator and re-enables automatically when resolution completes

## Requirements *(mandatory)*

### Functional Requirements

#### Layout and Navigation

- **FR-001**: System MUST provide a persistent top bar displaying: current tick number, at least 4 aggregate simulation indicators with labels and values, and a tick resolution control
- **FR-002**: System MUST provide a primary map view occupying the majority of screen space, displaying a choropleth layer over an H3 hexagonal grid
- **FR-003**: System MUST provide a collapsible right panel for entity detail inspection, displaying context-sensitive information based on the currently selected map element or entity
- **FR-004**: System MUST provide a collapsible bottom panel for time-series analytics and event history
- **FR-005**: System MUST provide a lens navigation system allowing single-click switching between at least 4 analytical perspectives that recontextualize the map layer, panel content, and indicator emphasis
- **FR-006**: System MUST maintain visual continuity during lens switches — no full-page reload or layout shift

#### Map Interaction

- **FR-007**: System MUST display an interactive choropleth map with hover tooltips showing territory name and key metrics
- **FR-008**: System MUST support click-to-select on map hexagons, opening the selected territory's detail in the right panel
- **FR-009**: System MUST provide a map legend that updates dynamically based on the active choropleth layer, showing the color scale and metric name
- **FR-010**: System MUST support at least 6 choropleth layers (heat, consciousness, wealth, rent extraction, population, biocapacity) switchable via layer controls
- **FR-011**: System MUST support simultaneous hover tooltip display while a detail panel is open (tooltip and selection are independent interactions)

#### Progressive Disclosure (Drill-Down)

- **FR-012**: System MUST support a 3-level drill-down chain: Map overview -> Territory detail -> Organization/Entity detail
- **FR-013**: System MUST provide breadcrumb navigation within the detail panel so the player can return to any previous level in the drill-down chain
- **FR-014**: System MUST show contextually relevant information at each drill-down level — territory detail shows all present organizations; organization detail shows all occupied territories, key figures, and available actions
- **FR-015**: Each drill-down level MUST be reachable in at most 2 clicks from the map (hover is 0, click is 1, sub-entity click is 2)

#### Action Composition

- **FR-016**: System MUST provide a guided action composition flow with clear sequential steps: select acting organization -> select verb -> select target -> preview and confirm
- **FR-017**: System MUST show a preview of expected action effects (estimated metric changes, resource costs) before requiring confirmation
- **FR-018**: System MUST allow backward navigation through composition steps without losing prior selections
- **FR-019**: System MUST visually indicate which verbs are available vs unavailable for the selected organization, with explanations for unavailability
- **FR-020**: System MUST disable action composition while a tick is being resolved and provide clear feedback about the blocked state

#### Indicators and Feedback

- **FR-021**: System MUST display persistent aggregate indicators in the top bar that update after each tick resolution
- **FR-022**: Indicators MUST communicate urgency through visual encoding (color shifts, icon changes) when values cross defined thresholds
- **FR-023**: System MUST provide immediate visual feedback (within 200ms) for all user interactions: clicks, hovers, selections, and action submissions
- **FR-024**: System MUST use Tufte-aligned data visualization: high data-ink ratio, no 3D effects, no decorative chartjunk, subtle reference lines, and directly readable data points

#### Notification System

- **FR-025**: System MUST categorize events into at least 3 severity tiers: critical (requires acknowledgment), important (prominently displayed), and informational (logged but not intrusive)
- **FR-026**: System MUST communicate critical events through multiple channels simultaneously (visual alert + map highlight + indicator change) per the diverse redundancy principle
- **FR-027**: System MUST group similar events (e.g., "N territories reached elevated heat") when more than a defined threshold of similar events occur in a single tick
- **FR-028**: System MUST allow players to click on any event notification to navigate directly to the relevant entity or territory
- **FR-029**: System MUST maintain an event history log accessible through the bottom panel, with events sorted chronologically and filterable by type and severity

#### Analytics and Time-Series

- **FR-030**: System MUST display time-series charts for selectable simulation metrics over the available tick history
- **FR-031**: Charts MUST support hover-to-inspect showing exact values and tick numbers for individual data points
- **FR-032**: System MUST allow players to select which metrics are displayed on charts
- **FR-033**: Charts MUST follow data-ink maximization principles: no bilateral symmetry waste, minimal non-data ink, and range-frames or equivalent techniques where appropriate

#### Network Visualization

- **FR-034**: System MUST provide a graph visualization view showing organizations, classes, and their relationships as a force-directed layout
- **FR-035**: System MUST support filtering edges by relationship type (solidarity, exploitation, etc.)
- **FR-036**: System MUST allow clicking graph nodes to open the entity detail panel with the same information available through the map drill-down path

#### Visual Design

- **FR-037**: System MUST use a dark theme as the primary visual style with layered surface elevation (not flat pure black), body text at sufficient contrast (minimum 4.5:1 ratio per WCAG AA), and desaturated semantic colors for status indicators
- **FR-038**: System MUST establish a consistent metaphor vocabulary — interactive elements must be visually distinguishable from decorative elements through consistent affordances (hover state, cursor change, visual weight)
- **FR-039**: System MUST implement a clear visual hierarchy where the most important information (current crisis level, active alerts) has the highest visual weight, and secondary information (historical stats, configuration options) recedes
- **FR-040**: System MUST communicate the simulation's ideological framework through visual design: the interface should prime players for analytical thinking about material conditions, class dynamics, and systemic forces rather than individual-hero narratives

#### Persistence and Customization

- **FR-041**: System MUST persist panel open/closed states and sizes across browser sessions
- **FR-042**: System MUST allow players to choose which metrics appear as persistent top bar indicators
- **FR-043**: System MUST provide a "Reset to Defaults" option that restores all layout customizations to their initial state

### Key Entities

- **Lens**: An analytical perspective that determines which choropleth layer is active, which indicators are emphasized, and what contextual information appears in panels. A lens has a name, a primary map metric, a set of emphasized indicators, and default panel content.
- **Notification**: A game event communicated to the player. Has severity (critical/important/informational), a message, a timestamp (tick number), a linked entity reference (territory, organization, or class), and read/unread status.
- **Indicator**: A persistent metric display element showing an aggregate simulation value. Has a label, current value, previous value (for delta display), and threshold definitions that trigger visual urgency states.
- **Panel State**: The configuration of a UI panel (right, bottom, analytics). Has open/closed state, size dimensions, active tab selection, and scroll position.
- **Breadcrumb**: A navigation state entry in the drill-down chain. Has entity type, entity ID, display name, and lens context at time of navigation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new player can identify whether the simulation is in a stable, tense, or crisis state within 10 seconds of loading the game, without clicking anything
- **SC-002**: A player can navigate from spotting a map anomaly (bright-colored hex) to understanding its root cause (specific entity details) in 3 clicks or fewer
- **SC-003**: A player can compose and submit a strategic action (organization + verb + target + confirm) in under 30 seconds
- **SC-004**: Switching between analytical lenses recontextualizes the map, indicators, and panel content within 300ms with no layout shift
- **SC-005**: The default screen displays at least 80% of the information a player needs for turn-to-turn decision making without requiring any clicks or panel openings
- **SC-006**: Critical game events (rupture thresholds, endgame conditions) are communicated through at least 2 independent visual channels simultaneously
- **SC-007**: Time-series charts achieve a data-ink ratio above 0.8 — less than 20% of chart pixels are non-data decoration
- **SC-008**: All interactive elements provide visual feedback within 200ms of user interaction
- **SC-009**: The UI supports a national-scale simulation (50 states, 3000+ counties) without perceptible lag in map rendering or panel updates during normal interaction
- **SC-010**: Panel customizations (size, open/closed state, indicator selection) persist across browser sessions with 100% reliability
- **SC-011**: The notification system never shows more than 5 individual event cards after a single tick — similar events are grouped into summary notifications
- **SC-012**: Every interactive element is visually distinguishable from non-interactive elements through consistent hover states, cursor changes, and visual affordances
