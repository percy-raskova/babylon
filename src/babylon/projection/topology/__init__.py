"""Topology projections — read-only orderings for The Archive's Lane T surfaces.

Each module here derives a deterministic *ordering* (never a force-directed
layout — S9 canon, ``ai/_inbox/tui/20260719archiveinterfacedesign.md``) from
declared, transport-neutral data: PAOH/Levi/incidence orderings over
hypergraph structure (WO-30/31/32), and here (WO-33) the map-room
choropleth's tier -> renderer selection and hex/county aggregate -> cell
derivation.

Like the rest of :mod:`babylon.projection`, this package is pure data and
pure functions: no Textual, no PIL, no database connection. TUI-facing
rendering (colors, bitmaps, widgets) lives in ``babylon.tui``.
"""
