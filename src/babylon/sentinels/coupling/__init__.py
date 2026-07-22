"""The coupling sentinel — declared edges must match real dependencies, both ways.

``_DEFAULT_COUPLINGS`` in the dialectics catalog is not vocabulary; it is a claim
about the code. ``Coupling(source="surplus_distribution", target="debt_spiral",
kind="transforms")`` asserts that whatever computes the debt reading reads
whatever computes the distribution reading. A hand-authored graph drifts from the
dependencies it describes the moment either side changes — which is exactly how
four reserved edges sat dormant and undetected for months, and how
``momentum_coupling`` stayed a real dependency nobody had declared.

So this sensor checks BOTH directions:

- **declared-but-absent** — an edge whose target's producer does not in fact read
  any symbol the source's producer publishes;
- **present-but-undeclared** — a producer that DOES read another opposition's
  published symbol, with no edge declaring it.

Advisory and local/on-demand:
``uv run python tools/sentinel_check.py coupling``.

Layer 0.5: reads the catalog statically via :mod:`ast` — it may not import
``babylon.domain`` (import-linter contract, ``pyproject.toml``).
"""
