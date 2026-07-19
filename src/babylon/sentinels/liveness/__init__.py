"""The liveness sentinel — declared outputs must have declared readers.

Volume III of this codebase computed correctly and changed nothing for months:
every calculator ran, every model validated, and no output reached a consumer.
No test detected it, because "it runs" and "it matters" are different claims and
only the first was ever asserted. This sentinel asserts the second.

Two error classes, one registry:

- **correct-but-inert** — a producer (a ``System``, a service) runs but *every*
  output it declares is dormant; the whole producer is decoration.
- **computed-but-never-consumed** — one declared output has no production
  reader, and no ``dormant_reason`` explaining why that is acceptable.

The registry (:mod:`babylon.sentinels.liveness.registry`) is the declared half;
the sensors (:mod:`babylon.sentinels.liveness.checks`) prove each declaration
against source, statically, via :mod:`ast`. Per the standing owner ruling both
checks are **advisory** and local/on-demand
(``poetry run python tools/sentinel_check.py liveness``) — they never gate CI.

Layer 0.5 (same rank as :mod:`babylon.config`): imports nothing above
:mod:`babylon.models`.
"""
