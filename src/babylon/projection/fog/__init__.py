"""Track 1 — The Organizer's Map (2026-07-18, spec-117 §5a).

Relocated from ``web.game.fog`` to ``babylon.projection.fog`` by Program 24
P1 WO-1 (the Hoist, part A): this package was already transport-neutral —
zero ``django``/``babylon.engine`` coupling — so the move is a pure
relocation with no behavior change. ``web/game/fog/__init__.py`` is now a
thin re-export shim over this package, kept until P4's cutover.

Fog-of-war lives at the serialization boundary, not the engine: visibility
is a pure function of ``(graph, intel_ledger)``, computed here in the
projection layer and never fed back into the simulation. See
``docs/superpowers/plans/2026-07-18-track1-organizers-map.md``.

- :mod:`babylon.projection.fog.reach` — the organizing-reach primitive
  (Task 2): which node ids are within the player org's PRESENCE ∪
  SOLIDARITY neighborhood.
- :mod:`babylon.projection.fog.ledger` — the intel ledger (Task 3): a
  session-scoped, append-only, event-sourced record of INVESTIGATE
  resolutions, and the pure aging function that renders a snapshot
  exact/approximate/unknown.
- :mod:`babylon.projection.fog.filter` — ``apply_fog`` (Task 4): redacts a
  composer's political fields outside ``reach``/uncovered by the ledger,
  always returning a new dict. ``engine_bridge.py`` (via the ``web/game/fog``
  shim) wires this into ``_serialize_territory``/``_state_to_snapshot``/
  ``_build_org_network`` and ``get_inspector_node``/``get_inspector_org``
  — never the reverse.

All modules are deliberately free of any ``babylon.engine`` /
``babylon.models`` / ``babylon.config`` import — the web import-boundary
test (``tests/unit/web/test_import_boundary.py``) reserves those to
``engine_bridge.py`` (+ a short allowlist); this package sits outside that
restricted prefix list entirely. Coefficients (reach radius, aging
thresholds) and graph/edge-type identifiers are passed in explicitly by
callers that already hold them, keeping this package a pure function of
its inputs — no engine coupling, no hidden state.
"""
