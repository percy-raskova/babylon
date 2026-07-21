"""The vault materializer — deterministic page baking (Constitution III.13).

Bakes Archive pages (markdown with frontmatter stat blocks, staleness
stamps, and loud absence blocks) from projection view-models at tick
commit, and records them as dulwich commits stamped with *sim time*
(``babylon.kernel.sim_clock.sim_datetime``), never wall-clock.

Determinism contract: identical ``(state, intel ledger, defines,
templates)`` yield byte-identical artifacts and identical commit shas.
Templates run in a Jinja2 ``ImmutableSandboxedEnvironment`` with
``StrictUndefined`` — a missing field raises, it never renders silence.

This subpackage is imported *by* the engine's runner after
``persist_tick_atomic`` returns (a legal downward import; the materializer
observes committed envelope data and mutates nothing). Heavy dependencies
(jinja2, dulwich) are imported lazily inside modules, never at package
import time, so ``babylon.projection`` stays light for read-only clients.
"""
