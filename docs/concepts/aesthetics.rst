Visual Design Guidelines
========================

**Bunker Constructivism**: "Damp Basement Cyberinsurgency"

Art direction and visual design system for Babylon: The Fall of America.

Conceptual Foundation
---------------------

The Shift from Poster to Terminal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We move from "Museum Poster" constructivism to something rawer:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Old Aesthetic
     - New Aesthetic
   * - Clean geometric lines
     - Corroded edges
   * - Bright propaganda colors
     - Phosphor burn, flickering
   * - Flat surfaces
     - Depth, humidity, texture
   * - Authoritative
     - Conspiratorial
   * - Public declaration
     - Private revelation

Colors as Light Sources
~~~~~~~~~~~~~~~~~~~~~~~

Colors are not paint on surfaces. They are **light emissions** in a dark room.
The UI is not a webpage. It is a **CRT monitor in a concrete room**.

- The walls sweat. Humidity is visible in the vignette effect.
- The screen flickers. Not broken---struggling against interference.
- Dust particles float in the light cone from the monitor.
- Cables snake along the floor (implied in border treatments).

The Narrative Frame
~~~~~~~~~~~~~~~~~~~

You operate from a scavenged terminal in a damp concrete bunker. The year is
uncertain. The American empire is in its terminal phase. Your mission:
**Decode reality**.

The terminal is not neutral infrastructure. It is a comrade---a piece of
resistance technology cobbled together from surveillance equipment turned
against its makers.

Art Direction
-------------

Scavenged Soviet Hardware
~~~~~~~~~~~~~~~~~~~~~~~~~

**Primary Influence**: Operating overheating machines in dark rooms.

- Bold Constructivist geometry remains, but rendered as **wireframes on CRT
  monitors** instead of ink on paper
- Dynamic diagonal lines traced by electron beams
- Reference: Aging hardware, phosphor burn, electron beam aesthetics
- El Lissitzky and Rodchenko, but viewed through a dirty glass screen

**Brutalist/Industrial**

- Concrete textures visible in the darkness
- Stark contrasts from monitor glow against void
- The Chassis: server racks, inactive panels, cold metal
- Monumental scale suggested by the unseen infrastructure

Color Palette
-------------

Primary Colors (Light Emissions)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Hex
     - Name
     - Role
   * - ``#D40000``
     - **Phosphor Burn / The Laser**
     - Active elements with bloom effect. Alert states, ruptured contradiction
       edges, critical thresholds, cursor blink. Used sparingly---when red
       appears, it *burns*. Slightly uncomfortable to look at.
   * - ``#1A1A1A``
     - **Wet Concrete / The Void**
     - The Room itself. Backgrounds with noise texture, film grain at 2-5%
       opacity. The darkness is information.
   * - ``#F5F5F5``
     - **Terminal Glare**
     - High intensity text, but rendered at lower opacity (60-80%) to simulate
       phosphor glow rather than paper white. Never pure white.
   * - ``#FFD700``
     - **Exposed Circuitry / The Circuit**
     - Edges, connectors, truth data. Verified data connections, solidarity
       edges (the real infrastructure), exposed mechanics (what the Prism
       reveals).

Secondary Colors
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Hex
     - Name
     - Role
   * - ``#8B0000``
     - **Thermal Warning**
     - Overheating indicators, system stress, deep shadows on red elements.
   * - ``#404040``
     - **The Chassis**
     - Inactive panels, server racks, unlit portions of the interface. The
       cold metal of the machine.
   * - ``#C0C0C0``
     - **The Dust / Silver**
     - Terminal prompts, secondary text, inactive elements. The dust that
       settles on everything in the bunker.

Necropolis Codex (PDF Palette)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The PDF output uses a distinct "Necropolis Codex" palette---leaked documents
from the collapsing apparatus. Institutional, archival, stained with historical
violence. :hope:`Hope appears only where organization is discussed.`

**Primary Colors (The Machinery of Death)**

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Hex
     - Name
     - Role
   * - ``#0A0707``
     - **AbsoluteVoid**
     - Cover top gradient. Deepest darkness, the death camp night.
   * - ``#4A1818``
     - **DriedBlood**
     - Chapter headings, cover bottom. Oxidized, historical violence.
   * - ``#6B4A3A``
     - **Rust**
     - Section headings, internal links. Decaying infrastructure.
   * - ``#D4C9B8``
     - **AshPaper**
     - Page backgrounds. Cold institutional archive under fluorescent light.
   * - ``#8B7B6B``
     - **Bone**
     - Cover title, page numbers. Grave markers, monuments.
   * - ``#3D3A36``
     - **AshInk**
     - Body text. Charcoal with slight warmth for readability.

**Accent Colors (Buried Hope)**

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Hex
     - Name
     - Role
   * - ``#1A3A1A``
     - **BuriedHope**
     - Cover decorative line. Barely visible---the seed underground.
   * - ``#2A6B2A``
     - **ForestDim**
     - Revolutionary section headings. Hope emerging from darkness.
   * - ``#39FF14``
     - **PhosphorGreen**
     - Key phrases only: "Organization is the difference." Conditional hope.

**When Green Appears**

Green illuminates only content about revolutionary organization:

- The mantra: :hope:`Organization is the difference.`
- P(S|R) > P(S|A) / Warsaw Ghetto Dynamic
- Solidarity transmission, critical window, enforcer radicalization
- Trajectory C: Revolutionary Rupture

This creates a reading experience where most of the document feels oppressive,
but specific sections light up with possibility.

Textures & Lighting
-------------------

The interface is layered with atmospheric effects that simulate hardware decay:

.. mermaid::

   flowchart TB
       subgraph L4["LAYER 4: Vignette (damp glass)"]
           subgraph L3["LAYER 3: Scanlines (CRT)"]
               subgraph L2["LAYER 2: Film grain"]
                   L1["LAYER 1: Content<br/>(text, graphs, data)"]
               end
           end
       end

   %% Necropolis Codex styling - layers from outer to inner
   style L4 fill:#0A0707,stroke:#4A1818,color:#D4C9B8
   style L3 fill:#1A1A1A,stroke:#404040,color:#C0C0C0
   style L2 fill:#2D2A26,stroke:#6B4A3A,color:#D4C9B8
   style L1 fill:#1A1A1A,stroke:#D40000,color:#F5F5F5

Scanlines
~~~~~~~~~

- 1px horizontal lines every 3-4px
- Opacity: 3-8%
- Simulates CRT electron gun scan pattern
- Subtle but present---the eye should feel them more than see them

Bloom Effect
~~~~~~~~~~~~

- Gaussian blur applied to Phosphor Burn (``#D40000``) and Exposed Circuitry
  (``#FFD700``) elements
- Creates light bleed at edges
- Simulates phosphor overload on aging CRT
- More intense on critical/alert elements

Film Grain / Noise
~~~~~~~~~~~~~~~~~~

- ISO grain overlay on Wet Concrete (``#1A1A1A``) backgrounds
- Opacity: 2-5%
- Constant subtle animation (not static)
- Creates texture in the darkness

Flicker
~~~~~~~

- Border opacity oscillates +/-5% at 0.5-2Hz
- Applied to active panels and windows
- Simulates unstable power or signal interference
- Increases during high system load (contradiction accumulation)

Vignette
~~~~~~~~

- Radial gradient darkening edges
- Simulates curved CRT glass
- Creates focus toward center of attention
- Enhances "looking through a screen" effect

Typography
----------

Hierarchy (Monospace-First)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Primary: Roboto Mono or Source Code Pro**
   Data streams, most UI content, statistics, graph labels, narrative text.
   The terminal speaks in monospace.

**Secondary: Futura or DIN**
   System alerts only. Hardware labels. Rare emphasis moments.
   The machine's voice for critical warnings.

Characteristics
~~~~~~~~~~~~~~~

- Monospace dominates---this is a terminal, not a brochure
- Sans-serif reserved for system-level alerts and hardware identifiers
- Clear hierarchy through opacity and size, not font variation
- Text rendered with subtle glow (1-2px blur at low opacity)

Icon Design
-----------

Vector Traces on Screen
~~~~~~~~~~~~~~~~~~~~~~~

Icons are not ink on paper. They are **vector traces rendered on a CRT
screen**, phosphor-burned into the display.

The primary icon represents the Tower of Babylon motif with dialectical
splits and the suggestion of collapse/transformation:

.. mermaid::

   flowchart TB
       A["▲<br/>Tower Summit"]
       A --> SPLIT
       SPLIT{"│<br/>Dialectical<br/>Split"}
       SPLIT --> V1["▼<br/>Collapse"]
       SPLIT --> V2["▼<br/>Transform"]

   %% Necropolis Codex styling - vector traces on CRT
   style A fill:#0A0707,stroke:#FFD700,color:#FFD700
   style SPLIT fill:#0A0707,stroke:#D40000,color:#D40000
   style V1 fill:#0A0707,stroke:#FFD700,color:#FFD700
   style V2 fill:#0A0707,stroke:#39FF14,color:#39FF14

Rendered as glowing lines against The Void, with subtle bloom on vertices.

Alternative Icons
~~~~~~~~~~~~~~~~~

**Dialectics Symbol**
   Two opposing arrows forming a circle, representing continuous
   transformation. Traced in Exposed Circuitry (``#FFD700``).

**Broken Industry**
   Fractured gear wheel, symbol of systemic breakdown. Rendered with
   intentional pixel artifacts suggesting data corruption.

**Class Struggle**
   Interlocking class symbols, unified yet contradictory. Pulsing between
   Phosphor Burn and The Dust states.

UI Elements
-----------

Windows and Panels
~~~~~~~~~~~~~~~~~~

- Sharp corners (keep the Constructivist geometry)
- **Glowing borders** instead of thin lines---phosphor effect with subtle bloom
- Borders pulse subtly (flicker effect) to simulate hardware activity
- No gradients---light comes from the content, not the chrome
- High contrast for readability against The Void

Interactive Elements
~~~~~~~~~~~~~~~~~~~~

- Hover states increase glow intensity (phosphor brightening)
- Click feedback: brief flicker + intensity spike
- Consistent click/tap targets with visible bounds
- Active elements glow; inactive elements fade to The Chassis

Data Visualization
~~~~~~~~~~~~~~~~~~

- Geometric shapes rendered as wireframes
- Strong grid systems in The Dust (``#C0C0C0``) at low opacity
- Data points as light sources (bloom on nodes)
- Constructivist-inspired charts, but rendered as oscilloscope traces

Animation Guidelines
--------------------

Hardware-Inspired Motion
~~~~~~~~~~~~~~~~~~~~~~~~

- Quick, purposeful movements---electrons don't meander
- Geometric paths traced by electron beams
- Minimal easing---hardware doesn't smooth, it switches
- Angular motion paths following Constructivist diagonals

Effects
~~~~~~~

- Particle effects as static discharge or data fragments
- Geometric shape transformations with trace trails
- Flicker and pulse on state changes
- Screen tearing on heavy load (contradiction accumulation)

Sound Design
------------

- Industrial/mechanical ambient: fan hum, drive spin, relay clicks
- Soviet-era music influences filtered through degraded speakers
- Static and interference that rises with system stress
- Alert sounds: sharp electronic tones, phosphor buzz
- Minimal but impactful audio cues that feel like hardware feedback

Environmental Design
--------------------

The Bunker
~~~~~~~~~~

- Implied concrete walls beyond the screen edge
- Humidity visible in vignette and occasional condensation effects
- Cables and infrastructure suggested in border treatments
- The sense of operating hidden equipment in a forgotten space

Signal Conditions
~~~~~~~~~~~~~~~~~

- Weather/environmental effects manifest as signal degradation
- Day/night cycle affects baseline noise levels
- High repression periods increase static and interference
- Environmental factors visualized through signal quality, not graphics

Implementation Notes
--------------------

Priority Elements
~~~~~~~~~~~~~~~~~

1. Texture layers (scanlines, grain, vignette)
2. Glow/bloom system for light-emitting elements
3. Flicker animation system
4. Typography with monospace dominance
5. Color semantics as light sources

Technical Considerations
~~~~~~~~~~~~~~~~~~~~~~~~

- Texture overlays via CSS pseudo-elements or canvas layers
- Bloom effects via CSS filter: blur() or WebGL
- Flicker via CSS animation on opacity/brightness
- Performance: texture layers should be GPU-accelerated
- Consider reduced-motion preferences for flicker effects

Accessibility
~~~~~~~~~~~~~

- High contrast ratios maintained (glowing text on void)
- Flicker effects respect ``prefers-reduced-motion``
- Alternative text for all icons
- Keyboard navigation with visible focus glow
- Scanlines and grain subtle enough to not impair readability

See Also
--------

- :doc:`/how-to/gui-development` - GUI implementation roadmap
- :doc:`/reference/design-system` - Complete design tokens and constants
- :doc:`/concepts/architecture` - System architecture
