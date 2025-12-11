Design System Reference
=======================

Complete specification of visual design tokens for the Babylon user interface.
Implements "Bunker Constructivism" aesthetic - see :doc:`/concepts/aesthetics`
for conceptual rationale.

Color Palette
-------------

Primary Colors
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Hex
     - Name
     - Usage
   * - ``#D40000``
     - Phosphor Burn (Soviet Red)
     - Active elements with bloom. Alerts, ruptured contradictions,
       critical thresholds, cursor blink. Use sparingly.
   * - ``#1A1A1A``
     - Wet Concrete (Near Black)
     - Primary backgrounds with noise texture. The darkness is information.
   * - ``#F5F5F5``
     - Terminal Glare (Off White)
     - High intensity text at 60-80% opacity. Never pure white.
   * - ``#FFD700``
     - Exposed Circuitry (Gold)
     - Verified data, solidarity edges, connectors, achievements.

Secondary Colors
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Hex
     - Name
     - Usage
   * - ``#8B0000``
     - Thermal Warning (Dark Red)
     - Overheating indicators, system stress, shadows on red elements.
   * - ``#404040``
     - The Chassis (Dark Gray)
     - Inactive panels, server racks, interface borders.
   * - ``#C0C0C0``
     - The Dust (Silver)
     - Terminal prompts, secondary text, inactive elements.

Python Constants
~~~~~~~~~~~~~~~~

.. code-block:: python

   PRIMARY_COLORS = {
       "soviet_red": "#D40000",    # Phosphor Burn
       "near_black": "#1A1A1A",    # Wet Concrete
       "off_white": "#F5F5F5",     # Terminal Glare
       "gold": "#FFD700",          # Exposed Circuitry
   }

   SECONDARY_COLORS = {
       "dark_red": "#8B0000",      # Thermal Warning
       "dark_gray": "#404040",     # The Chassis
       "silver": "#C0C0C0",        # The Dust
   }

Typography
----------

Font Stack
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Role
     - Font
     - Usage
   * - Primary
     - Roboto Mono / Source Code Pro
     - Data streams, UI content, statistics, graph labels, narrative
   * - Secondary
     - Futura / DIN
     - System alerts, hardware labels, rare emphasis only
   * - Fallback
     - Any monospace
     - Terminal aesthetic requires monospace dominance

Python Constants
~~~~~~~~~~~~~~~~

.. code-block:: python

   FONTS = {
       "header": ("Futura", 14, "bold"),
       "body": ("Univers", 11),
       "mono": ("Roboto Mono", 10),
   }

Styling Constants
-----------------

Base Styling
~~~~~~~~~~~~

.. code-block:: python

   STYLE = {
       "bg": "#1A1A1A",          # Wet Concrete
       "fg": "#F5F5F5",          # Terminal Glare
       "accent": "#D40000",      # Phosphor Burn
       "border_width": 1,
       "padding": 10,
   }

Text Rendering
~~~~~~~~~~~~~~

- Text opacity: 60-80% (not full white)
- Text glow: 1-2px blur at low opacity
- Line height: 1.4 for readability on CRT effect

Panel Layout
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Panel
     - Purpose
   * - Left
     - Contradiction Map (network visualization)
   * - Center
     - Detail View (primary information)
   * - Right
     - Status Indicators (metrics display)
   * - Bottom
     - Event Log & Command Line (console)

Texture Layers
--------------

Layer Order (bottom to top)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Content** - Text, graphs, data
2. **Film Grain** - ISO grain at 2-5% opacity, subtle animation
3. **Scanlines** - 1px horizontal lines every 3-4px at 3-8% opacity
4. **Vignette** - Radial gradient darkening edges

Scanlines
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Line thickness
     - 1px
   * - Line spacing
     - Every 3-4px
   * - Opacity
     - 3-8%
   * - Purpose
     - Simulates CRT electron gun scan pattern

Film Grain
~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Type
     - ISO grain overlay
   * - Opacity
     - 2-5%
   * - Animation
     - Constant subtle movement (not static)
   * - Target
     - Wet Concrete backgrounds only

Bloom Effect
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Filter
     - Gaussian blur
   * - Targets
     - Phosphor Burn (``#D40000``), Exposed Circuitry (``#FFD700``)
   * - Purpose
     - Light bleed at edges, phosphor overload simulation
   * - Intensity
     - Increases on critical/alert elements

Flicker Animation
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Property
     - Value
   * - Target
     - Active panels and windows (border opacity)
   * - Range
     - +/-5% opacity
   * - Frequency
     - 0.5-2Hz
   * - Trigger
     - Increases during high contradiction accumulation

Animation Guidelines
--------------------

Motion Principles
~~~~~~~~~~~~~~~~~

- Quick, purposeful movements (electrons don't meander)
- Geometric paths following Constructivist diagonals
- Minimal easing (hardware switches, doesn't smooth)
- Angular motion paths

State Transitions
~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - State
     - Effect
   * - Hover
     - Increase glow intensity (phosphor brightening)
   * - Click
     - Brief flicker + intensity spike
   * - Active
     - Continuous glow
   * - Inactive
     - Fade to Chassis gray

Accessibility
-------------

Required Accommodations
~~~~~~~~~~~~~~~~~~~~~~~

- High contrast ratios (glowing text on void)
- Flicker effects respect ``prefers-reduced-motion``
- Alternative text for all icons
- Keyboard navigation with visible focus glow
- Scanlines/grain subtle enough for readability

Color Contrast
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Foreground
     - Background
     - Ratio
   * - ``#F5F5F5`` (80%)
     - ``#1A1A1A``
     - > 12:1
   * - ``#D40000``
     - ``#1A1A1A``
     - > 5:1
   * - ``#FFD700``
     - ``#1A1A1A``
     - > 10:1

Implementation
--------------

CSS Techniques
~~~~~~~~~~~~~~

.. code-block:: css

   /* Bloom effect */
   .phosphor-burn {
       color: #D40000;
       filter: blur(1px);
       text-shadow: 0 0 10px #D40000;
   }

   /* Scanlines via pseudo-element */
   .crt-overlay::after {
       content: "";
       position: absolute;
       background: repeating-linear-gradient(
           0deg,
           rgba(0, 0, 0, 0.05),
           rgba(0, 0, 0, 0.05) 1px,
           transparent 1px,
           transparent 4px
       );
   }

   /* Flicker animation */
   @keyframes flicker {
       0%, 100% { opacity: 1; }
       50% { opacity: 0.95; }
   }

See Also
--------

- :doc:`/concepts/aesthetics` - Visual design philosophy (Bunker Constructivism)
- :doc:`/how-to/gui-development` - GUI implementation roadmap
- :doc:`/reference/configuration` - System configuration
