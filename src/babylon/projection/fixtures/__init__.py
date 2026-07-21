"""Fixture recorder — record/load projection view-models with no engine.

Program 24 P1 keel item 5 (WO-6): every downstream view-consumer task runs
against a recorded fixture, never the live engine or a database. The
architectural split (integrator ruling, binding) keeps this package pure:

- :mod:`babylon.projection.fixtures.recorder` — pure record/load. No engine
  import, no scenario knowledge, no DB. Writes/reads deterministic JSON.
- ``tools/record_projection_fixtures.py`` (outside the import-linter
  contracts, since ``tools/`` sits above ``babylon.engine``) drives the
  engine to build the recorded fixture in the first place.

This package therefore satisfies the same "``babylon.projection`` must not
import ``babylon.engine``" contract as the rest of the Hoist.
"""
