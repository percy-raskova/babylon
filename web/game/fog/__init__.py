"""Track 1 — The Organizer's Map (2026-07-18, spec-117 §5a).

Fog-of-war lives at the serialization boundary, not the engine: visibility
is a pure function of ``(graph, intel_ledger)``, computed here in the
bridge/session layer and never fed back into the simulation. See
``docs/superpowers/plans/2026-07-18-track1-organizers-map.md``.

- :mod:`game.fog.reach` — the organizing-reach primitive (Task 2): which
  node ids are within the player org's PRESENCE ∪ SOLIDARITY neighborhood.
- :mod:`game.fog.ledger` — the intel ledger (Task 3): a session-scoped,
  append-only, event-sourced record of INVESTIGATE resolutions, and the
  pure aging function that renders a snapshot exact/approximate/unknown.

Both modules are deliberately free of any ``babylon.engine`` /
``babylon.models`` / ``babylon.config`` import — the web import-boundary
test (``tests/unit/web/test_import_boundary.py``) reserves those to
``engine_bridge.py`` (+ a short allowlist). Coefficients (reach radius,
aging thresholds) and graph/edge-type identifiers are passed in explicitly
by callers that already hold them, keeping this package a pure function of
its inputs — no engine coupling, no hidden state.
"""
