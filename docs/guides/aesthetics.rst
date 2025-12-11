Visual Design Guidelines
========================

Art direction and visual design system for The Fall of Babylon.

Art Direction
-------------

Primary Influences
~~~~~~~~~~~~~~~~~~

**Constructivist/Soviet Avant-garde**
   - Bold geometric shapes and compositions
   - Dynamic diagonal lines
   - Propaganda poster-inspired elements
   - Reference artists: El Lissitzky, Alexander Rodchenko

**Brutalist/Industrial**
   - Concrete textures and industrial machinery
   - Stark contrasts and harsh angles
   - Minimalist design principles
   - Monumental scale suggestions

Color Palette
-------------

Primary Colors
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Hex
     - Name
     - Usage
   * - ``#D40000``
     - Soviet Red
     - Main accent, important alerts
   * - ``#1A1A1A``
     - Near Black
     - Primary text, backgrounds
   * - ``#F5F5F5``
     - Off White
     - Secondary text, highlights
   * - ``#FFD700``
     - Gold
     - Special elements, achievements

Secondary Colors
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Hex
     - Name
     - Usage
   * - ``#8B0000``
     - Dark Red
     - Shadows, depth
   * - ``#404040``
     - Dark Gray
     - Interface elements
   * - ``#C0C0C0``
     - Silver
     - Inactive elements

Typography
----------

Primary Fonts
~~~~~~~~~~~~~

- **Headers**: Futura or DIN
- **Body Text**: Univers or Akzidenz-Grotesk
- **Data/Technical**: Roboto Mono or Source Code Pro

Characteristics
~~~~~~~~~~~~~~~

- Geometric sans-serif for main text
- Monospace for data and statistics
- Clear hierarchy through weight and size

Icon Design
-----------

Primary Icon
~~~~~~~~~~~~

The primary icon represents the Tower of Babylon motif with dialectical
splits and the suggestion of collapse/transformation:

.. code-block:: text

      +-------------+
      |     A       |
      |    / \      |
      |   /   \     |
      |  /_____\    |
      |     |       |
      |  V  |  V    |
      +-------------+

Alternative Icons
~~~~~~~~~~~~~~~~~

**Dialectics Symbol**
   Two opposing arrows forming a circle, representing continuous
   transformation.

**Broken Industry**
   Fractured gear wheel, symbol of systemic breakdown.

**Class Struggle**
   Interlocking class symbols, unified yet contradictory.

UI Elements
-----------

Windows and Panels
~~~~~~~~~~~~~~~~~~

- Sharp corners
- Thin borders (``#404040``)
- Subtle gradients for depth
- High contrast for readability

Interactive Elements
~~~~~~~~~~~~~~~~~~~~

- Clear hover states
- Visual feedback on interaction
- Consistent click/tap targets
- Distinct active/inactive states

Data Visualization
~~~~~~~~~~~~~~~~~~

- Geometric shapes for graphs
- Strong grid systems
- Clear hierarchical organization
- Constructivist-inspired charts

Animation Guidelines
--------------------

Transitions
~~~~~~~~~~~

- Quick, purposeful movements
- Geometric paths
- Minimal easing
- Angular motion paths

Effects
~~~~~~~

- Sharp, clean particle effects
- Geometric shape transformations
- Industrial/mechanical sounds
- Minimal but impactful

Sound Design
------------

- Industrial/mechanical ambient sounds
- Soviet-era music influences
- Factory/machinery sound effects
- Alert sounds following constructivist principles
- Minimal but impactful audio cues

Environmental Design
--------------------

- Weather effects (snow, rain, fog)
- Day/night cycle influences
- Seasonal changes affecting visuals
- Industrial smog and pollution effects
- Environmental degradation visualization

Propaganda Elements
-------------------

- Dynamic poster generation system
- Period-appropriate slogans
- Statistical infographics
- Achievement certificates
- News bulletin styling

Implementation Notes
--------------------

Priority Elements
~~~~~~~~~~~~~~~~~

1. Icon and branding
2. Core UI components
3. Data visualization style
4. Typography system
5. Animation framework

Technical Considerations
~~~~~~~~~~~~~~~~~~~~~~~~

- Scalable vector graphics for icons
- Responsive design principles
- Consistent spacing system
- Performance optimization

Accessibility
~~~~~~~~~~~~~

- High contrast ratios
- Clear visual hierarchy
- Alternative text for icons
- Keyboard navigation support

See Also
--------

- :doc:`gui-development` - GUI implementation roadmap
- :doc:`/concepts/architecture` - System architecture
