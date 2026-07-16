"""The declared-synthetic-data sentinel — sanctioned mock/fallback registry.

Babylon's engine and web layers carry a small set of intentional synthetic or
fallback data sources (a mock API bridge, hardcoded graceful-degradation
defaults, hand-authored scenario fixtures). This sentinel turns "which fakes
are sanctioned" from tribal knowledge into a **declared, checked registry**:
every sanctioned source must name itself AND its guard in
:data:`~babylon.sentinels.synthetic.registry.SYNTHETIC_SOURCES`, and each row
must be *coherent* — both symbols must actually exist in the code.

**Scope — STATIC coherence only.** The sensor here
(:func:`~babylon.sentinels.synthetic.checks.check_sources_and_guards_exist`)
proves, statically via :mod:`ast`, that every declared source and guard symbol
is still defined at its declared module path. It never imports or runs
``web``/``babylon.engine``/``babylon.domain`` code, so it lives in the
always-on dev fast-gate. Re-verifying each guard's *runtime behavior* (e.g.
that a DEBUG check actually raises) is the job of the dynamic test named in
each row — out of scope here.

The narrative reference doc is :doc:`/reference/declared-synthetic-data`.

Layer 0.5 (same rank as :mod:`babylon.config`): imports nothing above
:mod:`babylon.models`. The declared registry is pure data; any check logic
that would need a live symbol reads the source file statically instead.
"""
