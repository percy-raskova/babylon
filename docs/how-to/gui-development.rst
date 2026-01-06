GUI Development Guide
=====================

This guide outlines the development standards and architecture for Babylon's
graphical user interface, "The Cockpit."

The interface is built using **Dear PyGui** (DPG), a GPU-accelerated Python
GUI framework that allows for high-performance real-time visualization of
simulation state.

Design Philosophy: Bunker Constructivism
----------------------------------------

The UI follows the "Bunker Constructivism" aesthetic—a blend of Soviet
Constructivism, brutalist industrial design, and Cold War bunker interfaces.
It conveys a sense of surveillance, decay, and urgency.

Visual Language
~~~~~~~~~~~~~~~

- **Metaphor**: A dark-mode engineering dashboard ("The Cockpit") for observing
  systemic collapse.
- **Palette**: High-contrast phosphor colors against absolute black.
- **Typography**: Monospace and industrial sans-serifs.
- **feel**: Mechanical, precise, and foreboding.

Color Palette
~~~~~~~~~~~~~

The design system is centrally defined in :py:class:`babylon.ui.design_system.BunkerPalette`
and :py:class:`babylon.ui.design_system.DPGColors`.

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Color Name
     - Hex / RGB
     - Semantic Usage
   * - **VOID**
     - ``#050505``
     - Background darkness. The canvas.
   * - **DATA_GREEN**
     - ``#39FF14``
     - Positive metrics, healthy systems, logs (INFO).
   * - **PHOSPHOR_RED**
     - ``#D40000``
     - Critical failures, alarms, logs (ERROR), Bourgeoisie class.
   * - **EXPOSED_COPPER**
     - ``#FFD700``
     - Warnings, degraded states, logs (WARN).
   * - **SILVER_DUST**
     - ``#C0C0C0``
     - Neutral text, labels, inactive elements.
   * - **DARK_METAL**
     - ``#404040``
     - Borders, grid lines, structural elements.
   * - **ROYAL_BLUE**
     - ``#4169E1``
     - Labor Aristocracy class indicator.

Architecture
------------

The UI is decoupled from the simulation engine. It acts as a passive observer
and controller, running in the main thread while the simulation can tick
independently.

Entry Point
~~~~~~~~~~~

The dashboard is launched via ``src/babylon/ui/dpg_runner.py``:

.. code-block:: bash

   poetry run python -m babylon.ui.dpg_runner

Or via mise:

.. code-block:: bash

   mise run ui

Core Components
~~~~~~~~~~~~~~~

1. **Narrative Feed**: A scrolling log window displaying semantic events from the
   ``NarrativeDirector``.
2. **Telemetry Plots**: Time-series graphs tracking key contradictions (e.g.,
   Imperial Rent vs. Stability).
3. **Control Panel**: Play/Pause/Step controls for the simulation loop.
4. **Topology Monitor**: (Planned) Network visualization of class/territory relations.

Development Standards
---------------------

1. **GPU Acceleration**: DPG uses the GPU. Avoid blocking the main thread with heavy
   CPU computations. Use async patterns where necessary.
2. **Type Safety**: All UI code must be strictly typed.
3. **Design System**: Do not hardcode colors. Always import from ``babylon.ui.design_system``.

.. code-block:: python

   from babylon.ui.design_system import DPGColors

   # GOOD
   dpg.add_text("System Critical", color=DPGColors.PHOSPHOR_RED)

   # BAD
   dpg.add_text("System Critical", color=(255, 0, 0, 255))

4. **Context Managers**: Use DPG's context managers for nesting items.

.. code-block:: python

   with dpg.window(label="Main Window"):
       with dpg.group(horizontal=True):
           dpg.add_button(label="Play")
           dpg.add_button(label="Pause")

Reference
---------

- :py:mod:`babylon.ui.dpg_runner` - Main runner and layout.
- :py:mod:`babylon.ui.design_system` - Color constants and style tokens.
- `Dear PyGui Documentation <https://dearpygui.readthedocs.io/>`_
