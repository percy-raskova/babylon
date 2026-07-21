"""The Hoist — transport-neutral projection layer (Program 24, The Archive).

This package is the single seam between the engine's persisted state and
every client: the ``observe()`` contract chartered by Amendment V (II.8)
and the subsystem boundary discipline of Constitution II.11. Cross-subsystem
reads go through declared interfaces only — SQL views with explicit
contracts, frozen Pydantic view-models, and pure projection functions.

Layering (enforced by import-linter, ``mise run lint:imports``):

* ``babylon.projection`` reads *downward* — persistence typed facades,
  topology, domain, models, kernel.
* ``babylon.projection`` never imports ``babylon.engine``; the engine
  imports ``babylon.projection.vault`` downward at tick commit.
* Clients (``babylon.tui``, the legacy web bridge) consume view-models;
  they never reach past this package into persistence.

See ``docs/reference/projection-registry.rst`` for the declared-view
registry — the II.11 table-ownership spec this package discharges.
"""
